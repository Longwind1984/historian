"""Durable control plane for private exploration workspaces and analysis runs.

SQLite stores only opaque identifiers, redacted snapshot metadata, plans, and
runtime state. Original uploads and complete parser/UI snapshots are written to
the filesystem vault. This separation is intentional: the database must never
become a second copy of a user's book or pasted research question.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..schemas.exploration import (
    AnalysisRunList,
    AnalysisRunStatus,
    AnalysisWorkItemStatus,
    ExplorationSnapshot,
)
from .contracts import (
    AnalysisPass,
    AnalysisPlan,
    BookProfile,
    SourcePolicy,
)
from .planning import compile_analysis_plan
from .model_gateway import ModelGateway, NoModelGateway
from .passes import AnalysisArtifacts
from .pipeline import (
    QualityReport,
    adapt_work_item_spec,
    build_quality_report,
    rehydrate_analysis_artifacts,
)
from .profiling import build_book_profile
from .projections import ProjectionBundle, build_projection_bundle
from .runtime import ExplorationRuntime
from .signals import derive_document_signals
from .storage import (
    ExplorationRepository,
    RunNotFound,
    RunRecord,
    RunState,
    StorageInvariantError,
    WorkspaceNotFound,
)


class SnapshotRevisionConflict(StorageInvariantError):
    def __init__(self, expected: int, actual: int):
        super().__init__(
            f"Exploration revision conflict: expected {expected}, current {actual}"
        )
        self.expected = expected
        self.actual = actual


class AnalysisReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_type: Literal["claim", "event"]
    artifact_id: str = Field(min_length=1, max_length=240)
    decision: Literal["accepted", "rejected"]


class AnalysisReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_token: str = Field(pattern=r"^[a-f0-9]{64}$")
    decisions: tuple[AnalysisReviewDecision, ...] = Field(
        default=(), max_length=10_000
    )

    @model_validator(mode="after")
    def _decisions_are_unique(self) -> "AnalysisReviewRequest":
        keys = [(item.artifact_type, item.artifact_id) for item in self.decisions]
        if len(keys) != len(set(keys)):
            raise ValueError("review decisions must be unique")
        return self


class AnalysisRunResult(BaseModel):
    """Private, source-free review/read model for one durable run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AnalysisRunStatus
    review_token: str = Field(pattern=r"^[a-f0-9]{64}$")
    review_required: bool
    review_submitted: bool
    artifacts: AnalysisArtifacts
    quality_report: QualityReport
    candidate_projections: ProjectionBundle
    published_projections: ProjectionBundle


class AnalysisPlanningAdapter(Protocol):
    """Replaceable hook between parsed documents and the v6 workflow DAG."""

    def build(self, snapshot: ExplorationSnapshot) -> tuple[BookProfile, AnalysisPlan]:
        ...


class DeterministicPlanningAdapter:
    """Profile parsed shape signals and compile a source-bounded plan.

    This adapter emits no historical claims. It reads source text only while
    deriving numeric routing signals; neither text nor excerpts are returned in
    the profile or plan persisted by the control plane.
    """

    anchor_batch_size = 24

    def build(self, snapshot: ExplorationSnapshot) -> tuple[BookProfile, AnalysisPlan]:
        document = snapshot.document
        if document is None:
            raise StorageInvariantError(
                "analysis runs require a parsed book source"
            )
        signals = derive_document_signals(
            document, anchor_batch_size=self.anchor_batch_size
        )
        profile = build_book_profile(
            source_checksum=document.checksum_sha256,
            metadata=signals.metadata,
            structure=signals.structure,
            section_signals=signals.sections,
            profile_revision=snapshot.revision,
        )
        plan = compile_analysis_plan(
            profile,
            source_policy=SourcePolicy(),
            planning_scope=signals.planning_scope,
        )
        return profile, plan


@dataclass(frozen=True)
class ExplorationControlRecord:
    exploration_id: str
    source_id: str
    revision: int
    entry_mode: str


class ExplorationControlPlane:
    """Persistence facade shared by the compatibility API and v6 runtime."""

    def __init__(
        self,
        repository: ExplorationRepository,
        *,
        planning_adapter: AnalysisPlanningAdapter | None = None,
        model_gateway: ModelGateway | None = None,
    ) -> None:
        self.repository = repository
        self.runtime = ExplorationRuntime(repository)
        self.planning_adapter = planning_adapter or DeterministicPlanningAdapter()
        self.model_gateway = model_gateway or NoModelGateway()
        self._create_schema()

    def _create_schema(self) -> None:
        # ExplorationRepository owns the connection/transaction discipline.
        # These are control-plane extension tables, never private-source tables.
        schema = """
        CREATE TABLE IF NOT EXISTS exploration_control (
            exploration_id TEXT PRIMARY KEY
                REFERENCES workspaces(id) ON DELETE CASCADE,
            source_id TEXT NOT NULL UNIQUE
                REFERENCES sources(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            entry_mode TEXT NOT NULL,
            redacted_snapshot_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS exploration_analysis_runs (
            run_id TEXT PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE,
            exploration_id TEXT NOT NULL
                REFERENCES exploration_control(exploration_id) ON DELETE CASCADE,
            plan_id TEXT NOT NULL,
            primary_book_type TEXT NOT NULL,
            profile_json TEXT NOT NULL,
            plan_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS exploration_analysis_reviews (
            run_id TEXT PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE,
            review_token TEXT NOT NULL,
            decisions_json TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            applied_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_exploration_runs_workspace
            ON exploration_analysis_runs(exploration_id, created_at);
        """
        with self.repository._lock:  # noqa: SLF001 - same storage boundary
            self.repository._connection.executescript(schema)  # noqa: SLF001

    @staticmethod
    def _snapshot_bytes(snapshot: ExplorationSnapshot) -> bytes:
        return snapshot.model_dump_json().encode("utf-8")

    @staticmethod
    def _redacted_snapshot(snapshot: ExplorationSnapshot, source_id: str) -> str:
        document = snapshot.document
        payload = {
            "contract": "exploration_control.v1",
            "exploration_id": snapshot.id,
            "source_id": source_id,
            "revision": snapshot.revision,
            "entry_mode": snapshot.entry_mode,
            "created_at": snapshot.created_at.isoformat(),
            "updated_at": snapshot.updated_at.isoformat(),
            "document": (
                {
                    "document_id": document.id,
                    "source_format": document.source_format.value,
                    "checksum_sha256": document.checksum_sha256,
                    "char_count": document.char_count,
                    "section_count": document.section_count,
                    "paragraph_count": document.paragraph_count,
                }
                if document is not None
                else None
            ),
            "state_counts": {
                "scenes": len(snapshot.scenes),
                "claims": len(snapshot.claims),
                "evidence": len(snapshot.evidence),
                "argument_graphs": len(snapshot.argument_graphs),
                "composer_entries": len(snapshot.composer_entries),
                "analysis_queue": len(snapshot.analysis_queue),
            },
        }
        return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))

    def register_exploration(
        self,
        snapshot: ExplorationSnapshot,
        *,
        source_bytes: bytes,
        media_type: str,
    ) -> ExplorationSnapshot:
        self.repository.create_workspace(snapshot.id)
        try:
            source = self.repository.store_source(
                snapshot.id, source_bytes, media_type=media_type
            )
            self.repository.store_source_snapshot(
                source.id, snapshot.revision, self._snapshot_bytes(snapshot)
            )
            with self.repository._transaction() as connection:  # noqa: SLF001
                connection.execute(
                    """
                    INSERT INTO exploration_control
                        (exploration_id, source_id, revision, entry_mode,
                         redacted_snapshot_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.id,
                        source.id,
                        snapshot.revision,
                        snapshot.entry_mode,
                        self._redacted_snapshot(snapshot, source.id),
                        snapshot.created_at.isoformat(),
                        snapshot.updated_at.isoformat(),
                    ),
                )
        except BaseException:
            if self.repository.workspace_exists(snapshot.id):
                self.repository.delete_workspace(snapshot.id)
            raise
        return snapshot.model_copy(deep=True)

    def _control_record(self, exploration_id: str) -> ExplorationControlRecord:
        with self.repository._lock:  # noqa: SLF001
            row = self.repository._connection.execute(  # noqa: SLF001
                "SELECT * FROM exploration_control WHERE exploration_id = ?",
                (exploration_id,),
            ).fetchone()
        if row is None:
            raise WorkspaceNotFound(exploration_id)
        return ExplorationControlRecord(
            exploration_id=row["exploration_id"],
            source_id=row["source_id"],
            revision=int(row["revision"]),
            entry_mode=row["entry_mode"],
        )

    def load_snapshot(self, exploration_id: str) -> ExplorationSnapshot:
        record = self._control_record(exploration_id)
        data = self.repository.read_source_snapshot(record.source_id, record.revision)
        snapshot = ExplorationSnapshot.model_validate_json(data)
        if snapshot.id != exploration_id or snapshot.revision != record.revision:
            raise StorageInvariantError("vault snapshot does not match control metadata")
        return snapshot

    def save_snapshot(
        self,
        snapshot: ExplorationSnapshot,
        *,
        expected_revision: int,
    ) -> ExplorationSnapshot:
        record = self._control_record(snapshot.id)
        if record.revision != expected_revision:
            raise SnapshotRevisionConflict(expected_revision, record.revision)
        if snapshot.revision != expected_revision + 1:
            raise StorageInvariantError("snapshot revision must advance exactly once")

        self.repository.store_source_snapshot(
            record.source_id, snapshot.revision, self._snapshot_bytes(snapshot)
        )
        with self.repository._transaction() as connection:  # noqa: SLF001
            current = connection.execute(
                "SELECT revision FROM exploration_control WHERE exploration_id = ?",
                (snapshot.id,),
            ).fetchone()
            if current is None:
                raise WorkspaceNotFound(snapshot.id)
            actual = int(current["revision"])
            if actual != expected_revision:
                raise SnapshotRevisionConflict(expected_revision, actual)
            connection.execute(
                """
                UPDATE exploration_control
                SET revision = ?, redacted_snapshot_json = ?, updated_at = ?
                WHERE exploration_id = ?
                """,
                (
                    snapshot.revision,
                    self._redacted_snapshot(snapshot, record.source_id),
                    snapshot.updated_at.isoformat(),
                    snapshot.id,
                ),
            )
        return snapshot.model_copy(deep=True)

    def delete_exploration(self, exploration_id: str) -> None:
        self._control_record(exploration_id)
        self.repository.delete_workspace(exploration_id)

    def clear(self) -> None:
        with self.repository._lock:  # noqa: SLF001
            rows = self.repository._connection.execute(  # noqa: SLF001
                "SELECT exploration_id FROM exploration_control"
            ).fetchall()
        for row in rows:
            exploration_id = str(row["exploration_id"])
            if self.repository.workspace_exists(exploration_id):
                self.repository.delete_workspace(exploration_id)

    def _analysis_control(self, exploration_id: str, run_id: str):
        with self.repository._lock:  # noqa: SLF001
            row = self.repository._connection.execute(  # noqa: SLF001
                """
                SELECT * FROM exploration_analysis_runs
                WHERE exploration_id = ? AND run_id = ?
                """,
                (exploration_id, run_id),
            ).fetchone()
        if row is None:
            raise RunNotFound(run_id)
        return row

    def create_analysis_run(
        self, exploration_id: str, *, expected_revision: int
    ) -> AnalysisRunStatus:
        snapshot = self.load_snapshot(exploration_id)
        if snapshot.revision != expected_revision:
            raise SnapshotRevisionConflict(expected_revision, snapshot.revision)
        profile, plan = self.planning_adapter.build(snapshot)
        source_id = self._control_record(exploration_id).source_id
        run = self.runtime.create_run(
            exploration_id, plan_revision=snapshot.revision
        )
        now = datetime.fromisoformat(run.created_at)
        with self.repository._transaction() as connection:  # noqa: SLF001
            connection.execute(
                """
                INSERT INTO exploration_analysis_runs
                    (run_id, exploration_id, plan_id, primary_book_type,
                     profile_json, plan_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    exploration_id,
                    plan.id,
                    profile.primary_type.value,
                    profile.model_dump_json(),
                    plan.model_dump_json(),
                    now.isoformat(),
                ),
            )
        try:
            if snapshot.document is None:
                raise StorageInvariantError(
                    "analysis runs require a parsed book source"
                )
            signals = derive_document_signals(
                snapshot.document,
                anchor_batch_size=DeterministicPlanningAdapter.anchor_batch_size,
            )
            for item in plan.work_items:
                if item.pass_type is AnalysisPass.HUMAN_REVIEW:
                    break
                self.runtime.enqueue(
                    run.id,
                    adapt_work_item_spec(
                        plan=plan,
                        item=item,
                        signals=signals,
                        source_id=source_id,
                        gateway=self.model_gateway,
                        input_revision=snapshot.revision,
                    ),
                )
        except BaseException:
            self.repository.request_cancel(run.id)
            raise
        return self.get_analysis_run(exploration_id, run.id)

    def _run_status(self, control_row, run: RunRecord) -> AnalysisRunStatus:
        work_items = self.repository.list_run_work_items(run.id)
        return AnalysisRunStatus(
            id=run.id,
            exploration_id=run.workspace_id,
            plan_id=control_row["plan_id"],
            plan_revision=run.plan_revision,
            primary_book_type=control_row["primary_book_type"],
            state=run.state.value,
            cancel_requested=run.cancel_requested,
            created_at=datetime.fromisoformat(run.created_at),
            updated_at=datetime.fromisoformat(run.updated_at),
            work_items=[
                AnalysisWorkItemStatus(
                    id=item.id,
                    pass_type=item.pass_type,
                    state=item.state.value,
                    attempt_count=item.attempt_count,
                    max_attempts=item.max_attempts,
                    last_error_code=item.last_error_code,
                )
                for item in work_items
            ],
        )

    def get_analysis_run(
        self, exploration_id: str, run_id: str
    ) -> AnalysisRunStatus:
        control = self._analysis_control(exploration_id, run_id)
        run = self.repository.get_run(run_id)
        if run.workspace_id != exploration_id:
            raise RunNotFound(run_id)
        return self._run_status(control, run)

    def list_analysis_runs(self, exploration_id: str) -> AnalysisRunList:
        self._control_record(exploration_id)
        with self.repository._lock:  # noqa: SLF001
            rows = self.repository._connection.execute(  # noqa: SLF001
                """
                SELECT * FROM exploration_analysis_runs
                WHERE exploration_id = ? ORDER BY created_at, run_id
                """,
                (exploration_id,),
            ).fetchall()
        return AnalysisRunList(
            items=[self._run_status(row, self.repository.get_run(row["run_id"])) for row in rows]
        )

    @staticmethod
    def _review_token(artifacts: AnalysisArtifacts) -> str:
        payload = artifacts.model_dump(mode="json")
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def _review_row(self, run_id: str):
        with self.repository._lock:  # noqa: SLF001
            return self.repository._connection.execute(  # noqa: SLF001
                "SELECT * FROM exploration_analysis_reviews WHERE run_id = ?",
                (run_id,),
            ).fetchone()

    def get_analysis_result(
        self, exploration_id: str, run_id: str
    ) -> AnalysisRunResult:
        control = self._analysis_control(exploration_id, run_id)
        run = self.repository.get_run(run_id)
        artifacts, _ = rehydrate_analysis_artifacts(self.repository, run_id)
        snapshot = self.load_snapshot(exploration_id)
        anchor_ids = {
            paragraph.id
            for section in (snapshot.document.sections if snapshot.document else [])
            for paragraph in section.paragraphs
        }
        review_row = self._review_row(run_id)
        reviewed = bool(review_row and review_row["applied_at"])
        return AnalysisRunResult(
            status=self._run_status(control, run),
            review_token=self._review_token(artifacts),
            review_required=not reviewed,
            review_submitted=review_row is not None,
            artifacts=artifacts,
            quality_report=build_quality_report(
                artifacts,
                available_anchor_ids=anchor_ids,
                reviewed=reviewed,
            ),
            candidate_projections=build_projection_bundle(
                artifacts,
                available_anchor_ids=anchor_ids,
                include_pending=True,
            ),
            published_projections=build_projection_bundle(
                artifacts,
                available_anchor_ids=anchor_ids,
                include_pending=False,
            ),
        )

    @staticmethod
    def _decision_map(
        request: AnalysisReviewRequest,
    ) -> dict[tuple[str, str], str]:
        return {
            (item.artifact_type, item.artifact_id): item.decision
            for item in request.decisions
        }

    def _validate_review_request(
        self,
        artifacts: AnalysisArtifacts,
        request: AnalysisReviewRequest,
    ) -> None:
        expected = {
            *(("claim", item.id) for item in artifacts.claims),
            *(("event", item.id) for item in artifacts.events),
        }
        decisions = self._decision_map(request)
        if set(decisions) != expected:
            missing = len(expected - set(decisions))
            unknown = len(set(decisions) - expected)
            raise StorageInvariantError(
                f"review must decide every candidate (missing={missing}, unknown={unknown})"
            )

        accepted_claims = {
            artifact_id
            for (kind, artifact_id), decision in decisions.items()
            if kind == "claim" and decision == "accepted"
        }
        for claim in artifacts.claims:
            if (
                decisions[("claim", claim.id)] == "accepted"
                and claim.derived_from_claim_ids
                and not set(claim.derived_from_claim_ids).issubset(accepted_claims)
            ):
                raise StorageInvariantError(
                    "an accepted derived claim requires all parent claims to be accepted"
                )
        for event in artifacts.events:
            if (
                decisions[("event", event.id)] == "accepted"
                and not set(event.claim_ids).issubset(accepted_claims)
            ):
                raise StorageInvariantError(
                    "an accepted event requires all referenced claims to be accepted"
                )

    def submit_analysis_review(
        self,
        exploration_id: str,
        run_id: str,
        request: AnalysisReviewRequest,
    ) -> AnalysisRunResult:
        self._analysis_control(exploration_id, run_id)
        run = self.repository.get_run(run_id)
        if run.state is not RunState.WAITING_REVIEW:
            raise StorageInvariantError("analysis run is not waiting for review")
        artifacts, _ = rehydrate_analysis_artifacts(self.repository, run_id)
        if request.review_token != self._review_token(artifacts):
            raise StorageInvariantError("review token does not match current candidates")
        self._validate_review_request(artifacts, request)
        decisions_json = json.dumps(
            [item.model_dump(mode="json") for item in request.decisions],
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        now = datetime.now(timezone.utc).isoformat()
        with self.repository._transaction() as connection:  # noqa: SLF001
            existing = connection.execute(
                "SELECT * FROM exploration_analysis_reviews WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if existing is not None:
                if (
                    existing["review_token"] != request.review_token
                    or existing["decisions_json"] != decisions_json
                ):
                    raise StorageInvariantError(
                        "a different review has already been submitted"
                    )
            else:
                connection.execute(
                    """
                    INSERT INTO exploration_analysis_reviews
                        (run_id, review_token, decisions_json, submitted_at, applied_at)
                    VALUES (?, ?, ?, ?, NULL)
                    """,
                    (run_id, request.review_token, decisions_json, now),
                )
        return self.get_analysis_result(exploration_id, run_id)

    def reviewer_for_run(self, run_id: str):
        """Return a source-free reviewer callback only after explicit submission."""

        row = self._review_row(run_id)
        if row is None:
            return None
        decisions = {
            (item["artifact_type"], item["artifact_id"]): item["decision"]
            for item in json.loads(row["decisions_json"])
        }

        def reviewer(artifacts: AnalysisArtifacts) -> AnalysisArtifacts:
            claims = [
                item.model_copy(
                    update={"review_status": decisions[("claim", item.id)]}
                )
                for item in artifacts.claims
            ]
            events = [
                item.model_copy(
                    update={"review_status": decisions[("event", item.id)]}
                )
                for item in artifacts.events
            ]
            return artifacts.model_copy(update={"claims": claims, "events": events})

        return reviewer

    def mark_review_applied(self, run_id: str) -> None:
        run = self.repository.get_run(run_id)
        if run.state is not RunState.COMPLETED:
            raise StorageInvariantError("review can be applied only after projections complete")
        with self.repository._transaction() as connection:  # noqa: SLF001
            cursor = connection.execute(
                """
                UPDATE exploration_analysis_reviews
                SET applied_at = COALESCE(applied_at, ?)
                WHERE run_id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), run_id),
            )
            if cursor.rowcount != 1:
                raise StorageInvariantError("review submission does not exist")

    def cancel_analysis_run(
        self, exploration_id: str, run_id: str
    ) -> AnalysisRunStatus:
        self._analysis_control(exploration_id, run_id)
        self.runtime.cancel(run_id)
        return self.get_analysis_run(exploration_id, run_id)

    def resume_analysis_run(
        self, exploration_id: str, run_id: str
    ) -> AnalysisRunStatus:
        self._analysis_control(exploration_id, run_id)
        self.runtime.resume(run_id)
        return self.get_analysis_run(exploration_id, run_id)


__all__ = [
    "AnalysisReviewDecision",
    "AnalysisReviewRequest",
    "AnalysisRunResult",
    "AnalysisPlanningAdapter",
    "DeterministicPlanningAdapter",
    "ExplorationControlPlane",
    "ExplorationControlRecord",
    "SnapshotRevisionConflict",
]
