"""Source-safe acceptance runner for the private book-analysis control plane.

The runner deliberately uses ``NoModelGateway``.  It verifies the durable,
review-gated workflow against a real parsed source without pretending that an
unconfigured model has produced historical analysis.  Returned metrics contain
no source passages and are therefore suitable for an execution report.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import shutil
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.exploration import (
    ExplorationBrief,
    ImportExplorationRequest,
    SourceFormat,
)
from app.services.exploration_service import ExplorationStore

from .control_plane import AnalysisReviewRequest
from .model_gateway import NoModelGateway
from .worker import ExplorationWorker


class AcceptanceCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    status: Literal["pass", "fail", "not_run"]
    detail: str


class BookBackendAcceptanceResult(BaseModel):
    """A source-free record of one acceptance execution."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, protected_namespaces=()
    )

    contract_version: str = "book_backend_acceptance.v1"
    source_checksum: str
    source_format: str
    model_mode: Literal["forced_no_model"] = "forced_no_model"
    worker_execution_mode: Literal["in_process_harness"] = "in_process_harness"
    section_count: int = Field(ge=0)
    paragraph_count: int = Field(ge=0)
    character_count: int = Field(ge=0)
    primary_book_type: str
    classification_confidence: float = Field(ge=0, le=1)
    type_scores: dict[str, float]
    routing_uncertainties: list[str]
    selected_passes: dict[str, int]
    skipped_passes: dict[str, str]
    planned_work_item_count: int = Field(ge=0)
    state_sequence: list[str]
    processing_duration_ms: float = Field(ge=0)
    gap_counts: dict[str, int]
    claim_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    published_argument_nodes: int = Field(ge=0)
    published_timeline_items: int = Field(ge=0)
    checks: list[AcceptanceCheck]

    @property
    def check_map(self) -> dict[str, AcceptanceCheck]:
        return {item.code: item for item in self.checks}


def acceptance_verdict(
    result: BookBackendAcceptanceResult, *, routing_failed: bool
) -> Literal["pass", "conditional", "failed"]:
    """Derive the report verdict; never let a failed safety check look green."""

    if any(item.status == "fail" for item in result.checks):
        return "failed"
    if routing_failed or any(item.status == "not_run" for item in result.checks):
        return "conditional"
    return "pass"


def _remove_private_workspace_vault(
    state_root: Path, exploration_id: str
) -> None:
    """Remove only the exact generated workspace vault after a failed run."""

    vault_root = state_root / "vault"
    target = vault_root / exploration_id
    if target.parent != vault_root:
        raise ValueError("invalid exploration vault target")
    if target.exists():
        shutil.rmtree(target)


def run_book_backend_acceptance(
    *,
    content: str,
    state_dir: str | Path,
    title: str,
    author: str,
    version_label: str,
    brief: ExplorationBrief,
) -> BookBackendAcceptanceResult:
    """Run the durable no-model lane and erase the private workspace afterward.

    The expected content result is empty.  That is an explicit acceptance
    signal: no configured model means no fabricated claims, events or product
    projections.  Content-quality evaluation belongs to a separately
    configured model lane.
    """

    state_root = Path(state_dir)
    gateway = NoModelGateway()
    first_store = ExplorationStore(state_dir=state_root, model_gateway=gateway)
    snapshot = None
    first_phase_complete = False
    try:
        snapshot = first_store.create(
            ImportExplorationRequest(
                source_format=SourceFormat.MARKDOWN,
                content=content,
                title=title,
                author=author,
                version_label=version_label,
                brief=brief,
            )
        )
        run = first_store.create_analysis_run(
            snapshot.id,
            base_revision=snapshot.revision,
        )
        document = snapshot.document
        assert document is not None
        source_checksum = document.checksum_sha256
        source_fragments: list[bytes] = []
        for section in document.sections:
            for paragraph in section.paragraphs:
                text = paragraph.text.strip()
                for offset in range(0, len(text), 32):
                    fragment = text[offset : offset + 32]
                    if len(fragment) >= 16:
                        source_fragments.append(fragment.encode("utf-8"))
        first_phase_complete = True
    finally:
        if not first_phase_complete and snapshot is not None:
            try:
                first_store.delete(snapshot.id)
            except Exception:
                _remove_private_workspace_vault(state_root, snapshot.id)
        try:
            first_store.close()
        except BaseException:
            if snapshot is not None:
                _remove_private_workspace_vault(state_root, snapshot.id)
            raise

    # Reopen before work starts: this exercises snapshot/vault recovery rather
    # than succeeding from the process-local cache created during import.
    gateway = NoModelGateway()
    vault_workspace = state_root / "vault" / snapshot.id
    try:
        store = ExplorationStore(state_dir=state_root, model_gateway=gateway)
    except BaseException:
        _remove_private_workspace_vault(state_root, snapshot.id)
        raise
    deletion_ok = False
    try:
        recovered = store.get(snapshot.id)
        recovery_ok = bool(
            recovered.document
            and recovered.document.checksum_sha256 == source_checksum
            and recovered.document.paragraph_count == document.paragraph_count
        )

        worker = ExplorationWorker(store.control_plane, gateway)
        started = perf_counter()
        waiting = worker.process_run(run.id)
        waiting_result = store.get_analysis_result(snapshot.id, run.id)
        review_gate_ok = bool(
            waiting.state == "waiting_review"
            and waiting_result.review_required
            and not waiting_result.review_submitted
        )
        store.submit_analysis_review(
            snapshot.id,
            run.id,
            AnalysisReviewRequest(
                review_token=waiting_result.review_token,
                decisions=(),
            ),
        )
        completed = worker.process_run(run.id)
        final = store.get_analysis_result(snapshot.id, run.id)
        duration_ms = (perf_counter() - started) * 1000
        no_runnable_run = worker.process_next() is None

        database_bytes = b"".join(
            path.read_bytes()
            for path in state_root.glob("explorations.sqlite3*")
            if path.is_file()
        )
        database_excludes_source = all(
            fragment not in database_bytes for fragment in source_fragments
        )
        database_excludes_path = (
            str(state_root).encode("utf-8") not in database_bytes
        )

        profile = waiting.profile
        plan = waiting.plan
        selected_passes = Counter(item.pass_type.value for item in plan.work_items)
        skipped_passes = {
            item.pass_type.value: item.reason_code for item in plan.skipped_passes
        }
        gap_counts = Counter(item.code for item in final.artifacts.gaps)

        store.delete(snapshot.id)
        deletion_ok = not vault_workspace.exists()
    finally:
        if not deletion_ok:
            try:
                store.delete(snapshot.id)
            except Exception:
                _remove_private_workspace_vault(state_root, snapshot.id)
        store.close()

    content_empty_ok = bool(
        not final.artifacts.claims
        and not final.artifacts.events
        and not final.published_projections.argument.nodes
        and not final.published_projections.timeline.items
        and gap_counts.get("model_not_called", 0) > 0
    )
    completed_ok = bool(
        completed.state == "completed" and final.status.state == "completed"
    )

    checks = [
        AcceptanceCheck(
            code="durable_recovery",
            status="pass" if recovery_ok else "fail",
            detail="进程重开后通过私有保险库恢复相同校验和与段落计数。",
        ),
        AcceptanceCheck(
            code="human_review_gate",
            status="pass" if review_gate_ok else "fail",
            detail="候选输出在人工复核前停于 waiting_review。",
        ),
        AcceptanceCheck(
            code="explicit_no_model",
            status="pass" if content_empty_ok else "fail",
            detail="强制 NoModel 模式只记录缺口，不生成历史主张或投影。",
        ),
        AcceptanceCheck(
            code="durable_completion",
            status="pass" if completed_ok else "fail",
            detail="提交空复核后由 worker 边界恢复并完成。",
        ),
        AcceptanceCheck(
            code="no_runnable_run_after_completion",
            status="pass" if no_runnable_run else "fail",
            detail="完成后再次轮询没有可领取运行；未声称覆盖重复入队。",
        ),
        AcceptanceCheck(
            code="sqlite_source_isolation",
            status=(
                "pass"
                if database_excludes_source and database_excludes_path
                else "fail"
            ),
            detail="SQLite 未发现逐段非重叠的 16—32 字来源抽样片段或本机状态目录。",
        ),
        AcceptanceCheck(
            code="private_vault_deletion",
            status="pass" if deletion_ok else "fail",
            detail="删除探索后对应私有保险库目录消失。",
        ),
        AcceptanceCheck(
            code="live_content_quality",
            status="not_run",
            detail="本轮强制 NoModel，仅验控制面；不得把它冒充真实内容分析。",
        ),
        AcceptanceCheck(
            code="cross_process_worker",
            status="not_run",
            detail="本 runner 在同一进程调用 worker 边界，未验证跨进程恢复。",
        ),
    ]

    return BookBackendAcceptanceResult(
        source_checksum=source_checksum,
        source_format=document.source_format.value,
        section_count=document.section_count,
        paragraph_count=document.paragraph_count,
        character_count=document.char_count,
        primary_book_type=profile.primary_type.value,
        classification_confidence=profile.classification_confidence,
        type_scores={item.book_type.value: item.score for item in profile.type_scores},
        routing_uncertainties=[item.code for item in profile.uncertainties],
        selected_passes=dict(sorted(selected_passes.items())),
        skipped_passes=dict(sorted(skipped_passes.items())),
        planned_work_item_count=plan.estimated_work_item_count,
        state_sequence=[run.state, waiting.state, completed.state],
        processing_duration_ms=round(duration_ms, 3),
        gap_counts=dict(sorted(gap_counts.items())),
        claim_count=len(final.artifacts.claims),
        event_count=len(final.artifacts.events),
        published_argument_nodes=len(final.published_projections.argument.nodes),
        published_timeline_items=len(final.published_projections.timeline.items),
        checks=checks,
    )
