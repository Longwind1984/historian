"""Recoverable execution facade for exploration v6 work items.

This module intentionally knows nothing about model providers.  A worker is a
plain callable that receives a typed, source-free work specification and
returns a structured artifact.  That keeps crash/retry/idempotency behavior
testable with deterministic workers before any LLM is connected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any, Callable, Mapping, Sequence

from .storage import (
    ArtifactRevisionRecord,
    AttemptRecord,
    EnsuredWorkItem,
    ExplorationRepository,
    RunRecord,
    RunState,
    StorageInvariantError,
    WorkItemRecord,
    WorkItemState,
)


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PASS_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{0,79}$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:+-]{0,79}$")
_ERROR_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_idempotency_key(
    *,
    source_checksum: str,
    anchor_ids: Sequence[str],
    pass_type: str,
    input_revision: int,
    pipeline_version: str,
    prompt_bundle_version: str,
    model_route: str,
    source_policy: str,
    parameters: Mapping[str, Any] | None = None,
) -> str:
    """Build the stable identity of one semantic unit of work.

    JSON framing avoids ambiguous string concatenation.  Anchor order is
    retained because it can affect narrative synthesis; dictionary order does
    not affect the result.  A changed source, upstream artifact, prompt,
    pipeline, model route, source policy, or pass parameter produces a new key.
    """

    if not _SHA256.fullmatch(source_checksum):
        raise ValueError("source_checksum must be a SHA-256 hex digest")
    if input_revision < 0:
        raise ValueError("input_revision cannot be negative")
    if not _PASS_TYPE.fullmatch(pass_type):
        raise ValueError("pass_type must be a stable machine identifier")
    for label, value in (
        ("pipeline_version", pipeline_version),
        ("prompt_bundle_version", prompt_bundle_version),
        ("model_route", model_route),
        ("source_policy", source_policy),
    ):
        if not _VERSION.fullmatch(value):
            raise ValueError(f"{label} must be a bounded stable identifier")
    normalized_anchors = []
    for anchor_id in anchor_ids:
        if not isinstance(anchor_id, str) or not anchor_id or len(anchor_id) > 256:
            raise ValueError("anchor_ids must contain bounded non-empty strings")
        normalized_anchors.append(anchor_id)
    parameter_object = json.loads(_canonical_json(parameters or {}))
    framed = {
        "anchor_ids": normalized_anchors,
        "input_revision": input_revision,
        "model_route": model_route,
        "parameters": parameter_object,
        "pass_type": pass_type,
        "pipeline_version": pipeline_version,
        "prompt_bundle_version": prompt_bundle_version,
        "source_checksum": source_checksum,
        "source_policy": source_policy,
    }
    return hashlib.sha256(_canonical_json(framed).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WorkItemSpec:
    source_checksum: str
    anchor_ids: tuple[str, ...]
    pass_type: str
    input_revision: int
    pipeline_version: str
    prompt_bundle_version: str
    model_route: str
    source_policy: str
    source_id: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    max_attempts: int = 3

    @property
    def idempotency_key(self) -> str:
        return build_idempotency_key(
            source_checksum=self.source_checksum,
            anchor_ids=self.anchor_ids,
            pass_type=self.pass_type,
            input_revision=self.input_revision,
            pipeline_version=self.pipeline_version,
            prompt_bundle_version=self.prompt_bundle_version,
            model_route=self.model_route,
            source_policy=self.source_policy,
            parameters=self.parameters,
        )

    def storage_payload(self) -> dict[str, Any]:
        # This is intentionally locator/control metadata only.  It must never
        # include paragraph contents or source excerpts.
        return {
            "anchor_ids": list(self.anchor_ids),
            "model_route": self.model_route,
            "parameters": json.loads(_canonical_json(self.parameters)),
            "pipeline_version": self.pipeline_version,
            "prompt_bundle_version": self.prompt_bundle_version,
            "source_checksum": self.source_checksum,
            "source_id": self.source_id,
            "source_policy": self.source_policy,
        }


@dataclass(frozen=True)
class WorkResult:
    artifact_kind: str
    artifact_payload: Mapping[str, Any]
    checkpoint_state: Mapping[str, Any] = field(default_factory=dict)
    trace: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionOutcome:
    item: WorkItemRecord
    attempt: AttemptRecord
    artifact: ArtifactRevisionRecord | None
    run: RunRecord


class RetryableWorkError(RuntimeError):
    """A bounded transient failure such as timeout, 429, or worker loss."""

    def __init__(self, error_code: str):
        if not _ERROR_CODE.fullmatch(error_code):
            raise ValueError("error_code must be a bounded, non-sensitive code")
        super().__init__(error_code)
        self.error_code = error_code


class PermanentWorkError(RuntimeError):
    """A deterministic failure that must not be retried unchanged."""

    def __init__(self, error_code: str):
        if not _ERROR_CODE.fullmatch(error_code):
            raise ValueError("error_code must be a bounded, non-sensitive code")
        super().__init__(error_code)
        self.error_code = error_code


Worker = Callable[[WorkItemRecord], WorkResult]


class ExplorationRuntime:
    """Small deterministic supervisor around the durable repository."""

    def __init__(self, repository: ExplorationRepository):
        self.repository = repository

    def create_run(self, workspace_id: str, *, plan_revision: int) -> RunRecord:
        return self.repository.create_run(
            workspace_id, plan_revision=plan_revision
        )

    def enqueue(self, run_id: str, spec: WorkItemSpec) -> EnsuredWorkItem:
        return self.repository.ensure_work_item(
            run_id,
            idempotency_key=spec.idempotency_key,
            pass_type=spec.pass_type,
            input_revision=spec.input_revision,
            spec=spec.storage_payload(),
            max_attempts=spec.max_attempts,
        )

    def execute_next(
        self,
        run_id: str,
        worker: Worker,
        *,
        trace: Mapping[str, Any] | None = None,
    ) -> ExecutionOutcome | None:
        claimed = self.repository.claim_next_work_item(run_id, trace=trace)
        if claimed is None:
            return None

        artifact: ArtifactRevisionRecord | None = None
        try:
            result = worker(claimed.item)
            if not isinstance(result, WorkResult):
                raise PermanentWorkError("INVALID_WORK_RESULT")
            # Cancellation can race a long worker.  request_cancel() marks the
            # attempt cancelled; completing it then fails closed instead of
            # publishing a late artifact.
            if self.repository.get_run(run_id).cancel_requested:
                current_item = self.repository.get_work_item(claimed.item.id)
                return ExecutionOutcome(
                    item=current_item,
                    attempt=self.repository.get_attempt(claimed.attempt.id),
                    artifact=None,
                    run=self.repository.get_run(run_id),
                )
            artifact = self.repository.complete_attempt(
                claimed.attempt.id,
                artifact_kind=result.artifact_kind,
                artifact_payload=result.artifact_payload,
                checkpoint_state=result.checkpoint_state,
                trace_update=result.trace,
            )
        except RetryableWorkError as error:
            self.repository.fail_attempt(
                claimed.attempt.id,
                error_code=error.error_code,
                retryable=True,
            )
        except PermanentWorkError as error:
            self.repository.fail_attempt(
                claimed.attempt.id,
                error_code=error.error_code,
                retryable=False,
            )
        except StorageInvariantError:
            # State transitions (especially concurrent cancellation) have
            # already been persisted; do not turn them into a second failure.
            raise
        except Exception:
            # Exception messages may contain source material, URLs, or provider
            # payloads.  Persist only a stable category and let the caller keep
            # the process-local exception for diagnostics.
            self.repository.fail_attempt(
                claimed.attempt.id,
                error_code="WORKER_EXCEPTION",
                retryable=True,
            )

        return ExecutionOutcome(
            item=self.repository.get_work_item(claimed.item.id),
            attempt=self.repository.get_attempt(claimed.attempt.id),
            artifact=artifact,
            run=self.repository.get_run(run_id),
        )

    def execute_until_idle(
        self,
        run_id: str,
        worker: Worker,
        *,
        max_items: int | None = None,
    ) -> list[ExecutionOutcome]:
        if max_items is not None and max_items < 1:
            raise ValueError("max_items must be positive")
        outcomes: list[ExecutionOutcome] = []
        while max_items is None or len(outcomes) < max_items:
            outcome = self.execute_next(run_id, worker)
            if outcome is None:
                break
            outcomes.append(outcome)
            # A deterministic failure or cancellation must not busy-loop.
            if outcome.run.state in (
                RunState.FAILED,
                RunState.CANCELLED,
            ):
                break
        return outcomes

    def cancel(self, run_id: str) -> RunRecord:
        return self.repository.request_cancel(run_id)

    def resume(self, run_id: str) -> RunRecord:
        return self.repository.resume_run(run_id)


__all__ = [
    "ExecutionOutcome",
    "ExplorationRuntime",
    "PermanentWorkError",
    "RetryableWorkError",
    "RunState",
    "WorkItemSpec",
    "WorkItemState",
    "WorkResult",
    "build_idempotency_key",
]
