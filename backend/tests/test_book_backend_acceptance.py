"""Acceptance-runner coverage with a synthetic private source."""

from __future__ import annotations

import pytest

from app.exploration.acceptance import (
    acceptance_verdict,
    run_book_backend_acceptance,
)
from app.exploration.worker import ExplorationWorker
from app.schemas.exploration import ExplorationBrief
from app.services.exploration_service import ExplorationStore


def test_book_acceptance_is_source_safe_recoverable_and_honest_without_model(
    tmp_path,
):
    private_marker = "PRIVATE-ACCEPTANCE-MARKER-不得进入机器报告或数据库"
    content = "\n\n".join(
        [
            "# 测试书",
            f"## 第一章\n\n755 年，{private_marker}，作者提出一个解释问题。",
            "## 第二章\n\n756 年，相关行动延伸到另一地点，材料仍需人工复核。",
        ]
    )

    result = run_book_backend_acceptance(
        content=content,
        state_dir=tmp_path / "state",
        title="测试书",
        author="测试作者",
        version_label="合成测试来源",
        brief=ExplorationBrief(
            question="事件如何变化？",
            time_range="755—756",
            geography=["测试地点"],
            threads=["事件过程", "作者解释"],
            status="confirmed",
        ),
    )

    assert result.state_sequence == ["queued", "waiting_review", "completed"]
    assert result.claim_count == 0
    assert result.event_count == 0
    assert result.published_argument_nodes == 0
    assert result.published_timeline_items == 0
    assert result.gap_counts["model_not_called"] > 0
    assert result.check_map["durable_recovery"].status == "pass"
    assert result.check_map["human_review_gate"].status == "pass"
    assert result.check_map["explicit_no_model"].status == "pass"
    assert result.check_map["no_runnable_run_after_completion"].status == "pass"
    assert result.check_map["sqlite_source_isolation"].status == "pass"
    assert result.check_map["private_vault_deletion"].status == "pass"
    assert result.check_map["live_content_quality"].status == "not_run"
    assert result.check_map["cross_process_worker"].status == "not_run"
    assert acceptance_verdict(result, routing_failed=True) == "conditional"

    failed_checks = [
        item.model_copy(update={"status": "fail"})
        if item.code == "durable_recovery"
        else item
        for item in result.checks
    ]
    failed = result.model_copy(update={"checks": failed_checks})
    assert acceptance_verdict(failed, routing_failed=False) == "failed"
    assert private_marker not in result.model_dump_json()


def test_book_acceptance_erases_private_vault_when_worker_raises(
    tmp_path, monkeypatch
):
    state_dir = tmp_path / "state"
    private_marker = "PRIVATE-FAILURE-MARKER-异常时也必须清理"

    def fail_worker(_self, _run_id):
        raise RuntimeError("synthetic worker failure")

    monkeypatch.setattr(ExplorationWorker, "process_run", fail_worker)
    with pytest.raises(RuntimeError, match="synthetic worker failure"):
        run_book_backend_acceptance(
            content=f"# 测试书\n\n{private_marker}，这是一段足够长的测试来源。",
            state_dir=state_dir,
            title="测试书",
            author="测试作者",
            version_label="异常清理测试",
            brief=ExplorationBrief(question="失败时是否清理？"),
        )

    vault = state_dir / "vault"
    assert not vault.exists() or not any(vault.iterdir())
    database_family = b"".join(
        path.read_bytes()
        for path in state_dir.glob("explorations.sqlite3*")
        if path.is_file()
    )
    assert private_marker.encode("utf-8") not in database_family


def test_book_acceptance_erases_private_vault_when_store_cannot_reopen(
    tmp_path, monkeypatch
):
    state_dir = tmp_path / "state"
    original_init = ExplorationStore.__init__
    call_count = 0

    def fail_second_init(self, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("synthetic reopen failure")
        return original_init(self, *args, **kwargs)

    monkeypatch.setattr(ExplorationStore, "__init__", fail_second_init)
    with pytest.raises(RuntimeError, match="synthetic reopen failure"):
        run_book_backend_acceptance(
            content="# 测试书\n\nPRIVATE-REOPEN-MARKER-重开失败仍须删除来源。",
            state_dir=state_dir,
            title="测试书",
            author="测试作者",
            version_label="重开失败测试",
            brief=ExplorationBrief(question="重开失败时是否清理？"),
        )

    vault = state_dir / "vault"
    assert not vault.exists() or not any(vault.iterdir())
