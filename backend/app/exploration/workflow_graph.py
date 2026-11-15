"""LangGraph orchestration shell for exploration v6.

The graph is deliberately a control plane, not a shadow artifact store. Its
checkpoint state contains stable IDs and bounded control metadata only. Every
operation that can write, call a model, or mutate runtime state is delegated
to an idempotent runtime adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Literal, Mapping, Protocol, TypedDict, runtime_checkable

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field


WorkflowStep = Literal[
    "profile",
    "plan",
    "dispatch",
    "quality",
    "human_review",
    "projection",
]
ReviewDecision = Literal["approved", "changes_requested", "rejected"]
ControlScalar = str | int | float | bool | None

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@+-]{0,255}$")
_CHECKSUM = re.compile(r"^[a-f0-9]{64}$")
_FORBIDDEN_STATE_PARTS = ("source_text", "raw_text", "excerpt", "content", "body")


class WorkflowState(TypedDict, total=False):
    """Checkpoint-safe state. No source bytes, excerpts, or model payloads."""

    workflow_id: str
    run_id: str
    source_id: str
    source_checksum: str
    profile_id: str
    plan_id: str
    dispatched_work_item_ids: list[str]
    quality_report_id: str
    review_decision: ReviewDecision
    review_record_id: str
    projection_bundle_id: str
    last_step: WorkflowStep
    status: Literal[
        "queued",
        "profiled",
        "planned",
        "dispatched",
        "quality_checked",
        "reviewed",
        "completed",
        "completed_without_projection",
    ]


class WorkflowInput(BaseModel):
    """Strict ingress schema preventing unknown private fields from checkpointing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_id: str = Field(min_length=1, max_length=256)
    run_id: str = Field(min_length=1, max_length=256)
    source_id: str = Field(min_length=1, max_length=256)
    source_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: Literal["queued"] = "queued"


@dataclass(frozen=True)
class WorkflowStepResult:
    """IDs returned by one adapter transaction.

    ``execute_once`` must return the same IDs for the same idempotency key.
    Artifact payloads remain in the durable repository, never graph state.
    """

    output_artifact_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.output_artifact_ids:
            raise ValueError("workflow steps must return at least one artifact ID")
        if any(not _ID.fullmatch(item) for item in self.output_artifact_ids):
            raise ValueError("workflow adapter returned an invalid artifact ID")
        if len(set(self.output_artifact_ids)) != len(self.output_artifact_ids):
            raise ValueError("workflow adapter returned duplicate artifact IDs")


class SafeCompiledWorkflow:
    """Narrow proxy that validates user input before LangGraph checkpoints it.

    LangGraph's channel schemas select known fields but do not reject unknown
    input keys. That is insufficient for private books: an unknown raw-text key
    can appear in low-level checkpoint writes even when it is absent from the
    visible state. This proxy makes strict ingress validation unavoidable for
    synchronous and asynchronous entry points while delegating graph controls.
    """

    def __init__(self, compiled: Any) -> None:
        self._compiled = compiled

    @staticmethod
    def _safe_input(input_state: object) -> object:
        if input_state is None:
            return None
        return WorkflowInput.model_validate(input_state).model_dump()

    def invoke(self, input_state: object, config: object = None, **kwargs: object):
        return self._compiled.invoke(self._safe_input(input_state), config, **kwargs)

    def stream(self, input_state: object, config: object = None, **kwargs: object):
        return self._compiled.stream(self._safe_input(input_state), config, **kwargs)

    async def ainvoke(
        self, input_state: object, config: object = None, **kwargs: object
    ):
        return await self._compiled.ainvoke(
            self._safe_input(input_state), config, **kwargs
        )

    async def astream(
        self, input_state: object, config: object = None, **kwargs: object
    ):
        async for item in self._compiled.astream(
            self._safe_input(input_state), config, **kwargs
        ):
            yield item

    def __getattr__(self, name: str) -> Any:
        return getattr(self._compiled, name)


@runtime_checkable
class IdempotentWorkflowRuntimeAdapter(Protocol):
    """Only boundary through which graph nodes may perform side effects."""

    def execute_once(
        self,
        *,
        idempotency_key: str,
        step: WorkflowStep,
        run_id: str,
        input_artifact_ids: tuple[str, ...],
        control_metadata: Mapping[str, ControlScalar],
    ) -> WorkflowStepResult:
        ...


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _step_key(
    *,
    state: WorkflowState,
    step: WorkflowStep,
    input_artifact_ids: tuple[str, ...],
    control_metadata: Mapping[str, ControlScalar],
) -> str:
    framed = {
        "control_metadata": dict(control_metadata),
        "input_artifact_ids": list(input_artifact_ids),
        "run_id": state["run_id"],
        "step": step,
        "workflow_id": state["workflow_id"],
    }
    return sha256(_canonical_json(framed).encode("utf-8")).hexdigest()


def _validate_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{label} must be a bounded stable identifier")
    return value


def _validate_state(state: WorkflowState) -> None:
    """Fail closed if caller input attempts to enter private text into state."""

    allowed = set(WorkflowState.__annotations__)
    unknown = set(state) - allowed
    if unknown:
        raise ValueError("workflow state contains unsupported fields")
    if any(part in key.lower() for key in state for part in _FORBIDDEN_STATE_PARTS):
        raise ValueError("workflow state cannot contain private source fields")
    for key in ("workflow_id", "run_id", "source_id"):
        _validate_id(state.get(key), key)
    checksum = state.get("source_checksum")
    if not isinstance(checksum, str) or not _CHECKSUM.fullmatch(checksum):
        raise ValueError("source_checksum must be a SHA-256 hex digest")
    for key in (
        "profile_id",
        "plan_id",
        "quality_report_id",
        "review_record_id",
        "projection_bundle_id",
    ):
        value = state.get(key)
        if value is not None:
            _validate_id(value, key)
    work_ids = state.get("dispatched_work_item_ids", [])
    if not isinstance(work_ids, list):
        raise ValueError("dispatched_work_item_ids must be a list")
    for value in work_ids:
        _validate_id(value, "dispatched_work_item_id")


def initial_workflow_state(
    *,
    workflow_id: str,
    run_id: str,
    source_id: str,
    source_checksum: str,
) -> WorkflowState:
    state: WorkflowState = {
        "workflow_id": workflow_id,
        "run_id": run_id,
        "source_id": source_id,
        "source_checksum": source_checksum,
        "status": "queued",
    }
    _validate_state(state)
    return state


def workflow_config(thread_id: str) -> dict[str, dict[str, str]]:
    """Return the stable LangGraph checkpoint namespace for one workflow."""

    return {"configurable": {"thread_id": _validate_id(thread_id, "thread_id")}}


def sqlite_checkpointer(database_path: str | Path) -> SqliteSaver:
    """Create a local durable checkpointer; caller owns its process lifetime."""

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    return SqliteSaver(connection)


def build_exploration_workflow(
    adapter: IdempotentWorkflowRuntimeAdapter,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    interrupt_before_human_review: bool = True,
):
    """Compile the v6 control graph around an injected durable runtime.

    Resume protocol when review interruption is enabled:

    1. invoke initial state with :func:`workflow_config`;
    2. inspect checkpoint and present the quality report to a human;
    3. update ``review_decision`` on that checkpoint;
    4. invoke ``None`` with the same config to resume.
    """

    if not isinstance(adapter, IdempotentWorkflowRuntimeAdapter):
        raise TypeError("adapter must implement IdempotentWorkflowRuntimeAdapter")

    def execute(
        state: WorkflowState,
        *,
        step: WorkflowStep,
        input_ids: tuple[str, ...],
        control: Mapping[str, ControlScalar],
    ) -> tuple[str, ...]:
        _validate_state(state)
        result = adapter.execute_once(
            idempotency_key=_step_key(
                state=state,
                step=step,
                input_artifact_ids=input_ids,
                control_metadata=control,
            ),
            step=step,
            run_id=state["run_id"],
            input_artifact_ids=input_ids,
            control_metadata=control,
        )
        if not isinstance(result, WorkflowStepResult):
            raise TypeError("adapter must return WorkflowStepResult")
        return result.output_artifact_ids

    def profile(state: WorkflowState) -> WorkflowState:
        outputs = execute(
            state,
            step="profile",
            input_ids=(state["source_id"],),
            control={"source_checksum": state["source_checksum"]},
        )
        if len(outputs) != 1:
            raise ValueError("profile step must return exactly one profile ID")
        return {"profile_id": outputs[0], "last_step": "profile", "status": "profiled"}

    def plan(state: WorkflowState) -> WorkflowState:
        outputs = execute(
            state,
            step="plan",
            input_ids=(state["profile_id"],),
            control={},
        )
        if len(outputs) != 1:
            raise ValueError("plan step must return exactly one plan ID")
        return {"plan_id": outputs[0], "last_step": "plan", "status": "planned"}

    def dispatch(state: WorkflowState) -> WorkflowState:
        outputs = execute(
            state,
            step="dispatch",
            input_ids=(state["plan_id"],),
            control={},
        )
        return {
            "dispatched_work_item_ids": list(outputs),
            "last_step": "dispatch",
            "status": "dispatched",
        }

    def quality(state: WorkflowState) -> WorkflowState:
        outputs = execute(
            state,
            step="quality",
            input_ids=tuple(state["dispatched_work_item_ids"]),
            control={},
        )
        if len(outputs) != 1:
            raise ValueError("quality step must return exactly one report ID")
        return {
            "quality_report_id": outputs[0],
            "last_step": "quality",
            "status": "quality_checked",
        }

    def human_review(state: WorkflowState) -> WorkflowState:
        decision = state.get("review_decision")
        if decision not in ("approved", "changes_requested", "rejected"):
            raise ValueError("review_decision is required to resume human_review")
        outputs = execute(
            state,
            step="human_review",
            input_ids=(state["quality_report_id"],),
            control={"decision": decision},
        )
        if len(outputs) != 1:
            raise ValueError("human_review must return exactly one review record ID")
        status: Literal["reviewed", "completed_without_projection"] = (
            "reviewed" if decision == "approved" else "completed_without_projection"
        )
        return {
            "review_record_id": outputs[0],
            "last_step": "human_review",
            "status": status,
        }

    def after_review(state: WorkflowState) -> str:
        return "projection" if state.get("review_decision") == "approved" else END

    def projection(state: WorkflowState) -> WorkflowState:
        outputs = execute(
            state,
            step="projection",
            input_ids=(
                state["plan_id"],
                state["quality_report_id"],
                state["review_record_id"],
            ),
            control={},
        )
        if len(outputs) != 1:
            raise ValueError("projection step must return exactly one bundle ID")
        return {
            "projection_bundle_id": outputs[0],
            "last_step": "projection",
            "status": "completed",
        }

    builder = StateGraph(WorkflowState, input_schema=WorkflowInput)
    builder.add_node("profile", profile)
    builder.add_node("plan", plan)
    builder.add_node("dispatch", dispatch)
    builder.add_node("quality", quality)
    builder.add_node("human_review", human_review)
    builder.add_node("projection", projection)
    builder.add_edge(START, "profile")
    builder.add_edge("profile", "plan")
    builder.add_edge("plan", "dispatch")
    builder.add_edge("dispatch", "quality")
    builder.add_edge("quality", "human_review")
    builder.add_conditional_edges(
        "human_review",
        after_review,
        {"projection": "projection", END: END},
    )
    builder.add_edge("projection", END)
    interrupts = ["human_review"] if interrupt_before_human_review else []
    return SafeCompiledWorkflow(
        builder.compile(
            checkpointer=checkpointer,
            interrupt_before=interrupts,
        )
    )


__all__ = [
    "ControlScalar",
    "IdempotentWorkflowRuntimeAdapter",
    "ReviewDecision",
    "SafeCompiledWorkflow",
    "WorkflowInput",
    "WorkflowState",
    "WorkflowStep",
    "WorkflowStepResult",
    "build_exploration_workflow",
    "initial_workflow_state",
    "sqlite_checkpointer",
    "workflow_config",
]
