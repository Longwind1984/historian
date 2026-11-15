"""Durability, privacy, and idempotency tests for the v6 local runtime."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.exploration.runtime import (
    ExplorationRuntime,
    RetryableWorkError,
    WorkItemSpec,
    WorkResult,
    build_idempotency_key,
)
from app.exploration.storage import (
    AttemptState,
    ExplorationRepository,
    RunState,
    StorageInvariantError,
    WorkItemState,
)


PRIVATE_BODY = "只可留在来源保险库的正文-7d96e9ef-不应进入数据库".encode()


def _repository(tmp_path: Path) -> ExplorationRepository:
    return ExplorationRepository(tmp_path / "exploration.sqlite3", tmp_path / "vault")


def _spec(source_checksum: str, *, max_attempts: int = 3) -> WorkItemSpec:
    return WorkItemSpec(
        source_checksum=source_checksum,
        anchor_ids=("anchor_ch1_p3", "anchor_ch1_p4"),
        pass_type="passage.claim_extract",
        input_revision=1,
        pipeline_version="v6.1",
        prompt_bundle_version="claim.v1",
        model_route="deterministic.fake",
        source_policy="local_only",
        parameters={"schema": "claim_candidate.v1", "temperature": 0},
        max_attempts=max_attempts,
    )


def _scan_sqlite_files(database_path: Path) -> bytes:
    chunks = []
    for path in database_path.parent.glob(database_path.name + "*"):
        if path.is_file():
            chunks.append(path.read_bytes())
    return b"".join(chunks)


def test_private_source_lives_only_in_vault_and_explicit_delete_cleans_all(
    tmp_path: Path,
):
    repository = _repository(tmp_path)
    workspace = repository.create_workspace("ws_private")
    source = repository.store_source(
        workspace.id, PRIVATE_BODY, media_type="application/epub+zip"
    )
    private_snapshot = b'{"anchors":[{"id":"a1","source_text":"' + PRIVATE_BODY + b'"}]}'
    repository.store_source_snapshot(source.id, 1, private_snapshot)

    assert repository.journal_mode == "wal"
    assert repository.read_source(source.id) == PRIVATE_BODY
    assert repository.read_source_snapshot(source.id, 1) == private_snapshot
    assert repository.vault.exists(workspace.id, source.id)
    assert PRIVATE_BODY not in _scan_sqlite_files(repository.database_path)

    # Runtime metadata/artifacts also reject the common accidental raw-text
    # fields instead of silently serializing them into SQLite or trace JSON.
    runtime = ExplorationRuntime(repository)
    run = runtime.create_run(workspace.id, plan_revision=1)
    ensured = runtime.enqueue(run.id, _spec(source.checksum))
    claimed = repository.claim_next_work_item(
        run.id, trace={"worker": "fake", "anchor_count": 2}
    )
    assert claimed is not None
    with pytest.raises(ValueError, match="private source field"):
        repository.complete_attempt(
            claimed.attempt.id,
            artifact_kind="claim_candidates.v1",
            artifact_payload={"content": PRIVATE_BODY.decode()},
        )
    repository.fail_attempt(
        claimed.attempt.id,
        error_code="PRIVATE_FIELD_REJECTED",
        retryable=False,
    )
    assert repository.get_work_item(ensured.item.id).state is WorkItemState.FAILED
    assert PRIVATE_BODY not in _scan_sqlite_files(repository.database_path)

    repository.delete_workspace(workspace.id)
    assert not repository.workspace_exists(workspace.id)
    assert not repository.vault.exists(workspace.id, source.id)
    assert not repository.vault.snapshot_exists(workspace.id, source.id, 1)
    assert not (tmp_path / "vault" / workspace.id).exists()
    repository.close()


def test_successful_item_is_reused_after_repository_reopen_without_execution(
    tmp_path: Path,
):
    calls = 0
    repository = _repository(tmp_path)
    workspace = repository.create_workspace("ws_reuse")
    source = repository.store_source(workspace.id, b"private book bytes")
    runtime = ExplorationRuntime(repository)
    first_run = runtime.create_run(workspace.id, plan_revision=1)
    spec = _spec(source.checksum)
    first_item = runtime.enqueue(first_run.id, spec)

    def worker(_item):
        nonlocal calls
        calls += 1
        return WorkResult(
            artifact_kind="claim_candidates.v1",
            artifact_payload={"claims": [{"id": "claim_1", "anchor_id": "anchor_ch1_p3"}]},
            checkpoint_state={"completed_anchor_ids": ["anchor_ch1_p3", "anchor_ch1_p4"]},
            trace={"candidate_count": 1},
        )

    outcome = runtime.execute_next(first_run.id, worker)
    assert outcome is not None
    assert outcome.run.state is RunState.COMPLETED
    assert outcome.item.state is WorkItemState.SUCCEEDED
    assert outcome.artifact is not None
    assert calls == 1
    output_revision = outcome.artifact.revision
    repository.close()

    reopened = _repository(tmp_path)
    reopened_runtime = ExplorationRuntime(reopened)
    second_run = reopened_runtime.create_run(workspace.id, plan_revision=1)
    reused = reopened_runtime.enqueue(second_run.id, spec)

    assert reused.reused_success is True
    assert reused.item.id == first_item.item.id
    assert reused.item.output_revision == output_revision
    assert reopened.get_run(second_run.id).state is RunState.COMPLETED
    assert reopened_runtime.execute_next(second_run.id, worker) is None
    assert calls == 1
    assert len(reopened.list_attempts(reused.item.id)) == 1
    assert len(reopened.list_checkpoints(first_run.id)) == 1
    reopened.close()


def test_running_attempt_is_recovered_and_only_interrupted_item_retries(
    tmp_path: Path,
):
    repository = _repository(tmp_path)
    workspace = repository.create_workspace("ws_recovery")
    source = repository.store_source(workspace.id, b"another private source")
    runtime = ExplorationRuntime(repository)
    run = runtime.create_run(workspace.id, plan_revision=1)
    item = runtime.enqueue(run.id, _spec(source.checksum)).item
    claimed = repository.claim_next_work_item(
        run.id, trace={"worker_id": "worker_before_crash"}
    )
    assert claimed is not None
    assert repository.get_work_item(item.id).state is WorkItemState.RUNNING
    repository.close()  # process died before complete/fail was recorded

    reopened = _repository(tmp_path)  # recover_on_open performs crash recovery
    assert reopened.get_work_item(item.id).state is WorkItemState.RETRY_WAIT
    assert reopened.get_run(run.id).state is RunState.RETRY_WAIT
    first_attempt = reopened.list_attempts(item.id)[0]
    assert first_attempt.state is AttemptState.INTERRUPTED
    assert first_attempt.error_code == "WORKER_INTERRUPTED"

    resumed_runtime = ExplorationRuntime(reopened)
    outcome = resumed_runtime.execute_next(
        run.id,
        lambda _item: WorkResult(
            artifact_kind="claim_candidates.v1",
            artifact_payload={"claims": []},
            checkpoint_state={"resume_from": "anchor_ch1_p3"},
        ),
    )
    assert outcome is not None
    assert outcome.item.state is WorkItemState.SUCCEEDED
    assert outcome.run.state is RunState.COMPLETED
    attempts = reopened.list_attempts(item.id)
    assert [attempt.number for attempt in attempts] == [1, 2]
    assert [attempt.state for attempt in attempts] == [
        AttemptState.INTERRUPTED,
        AttemptState.SUCCEEDED,
    ]
    reopened.close()


def test_retry_and_cancel_resume_have_explicit_durable_states(tmp_path: Path):
    repository = _repository(tmp_path)
    workspace = repository.create_workspace("ws_state")
    source = repository.store_source(workspace.id, b"source")
    runtime = ExplorationRuntime(repository)

    retry_run = runtime.create_run(workspace.id, plan_revision=1)
    retry_item = runtime.enqueue(retry_run.id, _spec(source.checksum)).item
    worker_calls = 0

    def flaky_worker(_item):
        nonlocal worker_calls
        worker_calls += 1
        if worker_calls == 1:
            raise RetryableWorkError("MODEL_TIMEOUT")
        return WorkResult(
            artifact_kind="claim_candidates.v1",
            artifact_payload={"claims": []},
        )

    first = runtime.execute_next(retry_run.id, flaky_worker)
    assert first is not None
    assert first.item.state is WorkItemState.RETRY_WAIT
    assert first.run.state is RunState.RETRY_WAIT
    second = runtime.execute_next(retry_run.id, flaky_worker)
    assert second is not None
    assert second.item.state is WorkItemState.SUCCEEDED
    assert second.run.state is RunState.COMPLETED
    assert len(repository.list_attempts(retry_item.id)) == 2

    # Change the upstream revision so this is intentionally a new item rather
    # than an attempt to bypass the successful item's idempotency protection.
    cancel_spec = WorkItemSpec(
        **{**_spec(source.checksum).__dict__, "input_revision": 2}
    )
    cancel_run = runtime.create_run(workspace.id, plan_revision=2)
    cancelled_item = runtime.enqueue(cancel_run.id, cancel_spec).item
    cancelled = runtime.cancel(cancel_run.id)
    assert cancelled.state is RunState.CANCELLED
    assert cancelled.cancel_requested is True
    assert repository.get_work_item(cancelled_item.id).state is WorkItemState.CANCELLED
    assert runtime.execute_next(cancel_run.id, flaky_worker) is None

    resumed = runtime.resume(cancel_run.id)
    assert resumed.state is RunState.QUEUED
    assert resumed.cancel_requested is False
    final = runtime.execute_next(
        cancel_run.id,
        lambda _item: WorkResult(
            artifact_kind="claim_candidates.v1",
            artifact_payload={"claims": []},
        ),
    )
    assert final is not None
    assert final.run.state is RunState.COMPLETED
    repository.close()


def test_review_hold_is_explicit_durable_and_resumes_without_state_regression(
    tmp_path: Path,
):
    repository = _repository(tmp_path)
    workspace = repository.create_workspace("ws_review_state")
    source = repository.store_source(workspace.id, PRIVATE_BODY)
    runtime = ExplorationRuntime(repository)
    run = runtime.create_run(workspace.id, plan_revision=1)

    with pytest.raises(StorageInvariantError, match="successfully drained"):
        repository.mark_waiting_review(run.id)

    runtime.enqueue(run.id, _spec(source.checksum))
    completed = runtime.execute_next(
        run.id,
        lambda _item: WorkResult(
            artifact_kind="claim_candidates.v1",
            artifact_payload={"claims": []},
        ),
    )
    assert completed is not None
    assert completed.run.state is RunState.COMPLETED

    waiting = repository.mark_waiting_review(run.id)
    assert waiting.state is RunState.WAITING_REVIEW
    assert repository.mark_waiting_review(run.id).state is RunState.WAITING_REVIEW

    post_review = WorkItemSpec(
        **{**_spec(source.checksum).__dict__, "input_revision": 2}
    )
    runtime.enqueue(run.id, post_review)
    assert repository.get_run(run.id).state is RunState.WAITING_REVIEW
    assert runtime.execute_next(run.id, lambda _item: pytest.fail("review hold leaked")) is None

    repository.close()
    repository = _repository(tmp_path)
    runtime = ExplorationRuntime(repository)
    assert repository.get_run(run.id).state is RunState.WAITING_REVIEW

    cancelled = runtime.cancel(run.id)
    assert cancelled.state is RunState.CANCELLED
    assert cancelled.resume_state is RunState.WAITING_REVIEW
    resumed = runtime.resume(run.id)
    assert resumed.state is RunState.WAITING_REVIEW
    assert resumed.resume_state is None

    released = repository.release_waiting_review(run.id)
    assert released.state is RunState.QUEUED
    final = runtime.execute_next(
        run.id,
        lambda _item: WorkResult(
            artifact_kind="projection_bundle.v1",
            artifact_payload={"projection": {}},
        ),
    )
    assert final is not None
    assert final.run.state is RunState.COMPLETED
    assert repository.release_waiting_review(run.id).state is RunState.COMPLETED
    with pytest.raises(StorageInvariantError, match="terminal run"):
        runtime.cancel(run.id)
    assert repository.get_run(run.id).state is RunState.COMPLETED
    assert PRIVATE_BODY not in _scan_sqlite_files(repository.database_path)
    repository.close()


def test_idempotency_key_and_concurrent_enqueue_are_stable(tmp_path: Path):
    checksum = "a" * 64
    first = build_idempotency_key(
        source_checksum=checksum,
        anchor_ids=("a1", "a2"),
        pass_type="passage.claim_extract",
        input_revision=3,
        pipeline_version="v6.1",
        prompt_bundle_version="p1",
        model_route="fake",
        source_policy="local_only",
        parameters={"b": 2, "a": 1},
    )
    second = build_idempotency_key(
        source_checksum=checksum,
        anchor_ids=("a1", "a2"),
        pass_type="passage.claim_extract",
        input_revision=3,
        pipeline_version="v6.1",
        prompt_bundle_version="p1",
        model_route="fake",
        source_policy="local_only",
        parameters={"a": 1, "b": 2},
    )
    assert first == second
    assert first != build_idempotency_key(
        source_checksum=checksum,
        anchor_ids=("a2", "a1"),
        pass_type="passage.claim_extract",
        input_revision=3,
        pipeline_version="v6.1",
        prompt_bundle_version="p1",
        model_route="fake",
        source_policy="local_only",
        parameters={"a": 1, "b": 2},
    )

    repository = _repository(tmp_path)
    workspace = repository.create_workspace("ws_threads")
    with ThreadPoolExecutor(max_workers=8) as executor:
        sources = list(
            executor.map(
                lambda _index: repository.store_source(
                    workspace.id, b"threaded source"
                ),
                range(24),
            )
        )
    assert len({source.id for source in sources}) == 1
    source = sources[0]
    runtime = ExplorationRuntime(repository)
    run = runtime.create_run(workspace.id, plan_revision=1)
    spec = _spec(source.checksum)

    with ThreadPoolExecutor(max_workers=8) as executor:
        ensured = list(executor.map(lambda _index: runtime.enqueue(run.id, spec), range(24)))

    assert len({result.item.id for result in ensured}) == 1
    assert len(repository.list_run_work_items(run.id)) == 1
    repository.close()
