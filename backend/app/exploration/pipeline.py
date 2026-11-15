"""End-to-end adapter from a parsed private document to v6 read models.

This is intentionally an orchestration layer, not a second analysis engine.
It connects deterministic profiling/planning, the durable runtime, bounded
passes and accepted-only projections while keeping private paragraphs out of
runtime specs, artifacts, traces and checkpoints.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from hashlib import sha256
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.exploration import PrivateDocument

from .contracts import (
    AnalysisPass,
    AnalysisPlan,
    BookProfile,
    EpistemicLayer,
    ExecutorKind,
    InputUnit,
    SourcePolicy,
    WorkItemSpec as PlannedWorkItemSpec,
)
from .model_gateway import ModelGateway, NoModelGateway
from .passes import (
    AnalysisArtifacts,
    Gap,
    PassageUnit,
    SourceAnchorInput,
    VerifiedLocation,
    run_cross_unit_synthesis_pass,
    run_evidence_judge_pass,
    run_structured_extract_pass,
)
from .planning import compile_analysis_plan
from .profiling import build_book_profile
from .projections import ProjectionBundle, build_projection_bundle
from .runtime import (
    ExplorationRuntime,
    PermanentWorkError,
    WorkItemSpec as RuntimeWorkItemSpec,
    WorkResult,
)
from .signals import DocumentSignalBundle, derive_document_signals
from .storage import ExplorationRepository, RunState, WorkItemRecord, WorkItemState
from .validators import ValidationIssue, validate_analysis_artifacts


PipelineState = Literal[
    "planned",
    "queued",
    "running",
    "retry_wait",
    "waiting_review",
    "failed",
    "cancelled",
    "completed",
]


class PipelineModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, protected_namespaces=()
    )


class QualityGateResult(PipelineModel):
    code: str
    passed: bool
    blocking: bool = True
    detail: str


class QualityReport(PipelineModel):
    contract_version: Literal["quality_report.v1"] = "quality_report.v1"
    validation_issues: tuple[ValidationIssue, ...] = ()
    gates: tuple[QualityGateResult, ...]
    claim_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    model_not_called_count: int = Field(ge=0)
    accepted_claim_count: int = Field(ge=0)
    accepted_event_count: int = Field(ge=0)

    @property
    def blocking_gate_failures(self) -> tuple[str, ...]:
        return tuple(gate.code for gate in self.gates if gate.blocking and not gate.passed)


class PipelineResult(PipelineModel):
    contract_version: Literal["exploration_pipeline_result.v1"] = (
        "exploration_pipeline_result.v1"
    )
    run_id: str
    state: PipelineState
    profile: BookProfile
    plan: AnalysisPlan
    artifacts: AnalysisArtifacts
    quality_report: QualityReport
    projections: ProjectionBundle
    completed_plan_work_item_ids: tuple[str, ...] = ()


Reviewer = Callable[[AnalysisArtifacts], AnalysisArtifacts]


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _source_policy_id(policy: SourcePolicy) -> str:
    values = "-".join(source.value for source in policy.allowed_source_sets)
    flags = f"e{int(policy.enable_external_evidence)}n{int(policy.allow_external_network)}"
    return f"{values}-{flags}"[:80]


def _safe_route(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.:+-]", "-", value).strip("-.")
    return (clean or "unknown")[:80]


def _gateway_route(gateway: ModelGateway) -> str:
    provider = _safe_route(str(getattr(gateway, "provider", "gateway")))
    model = _safe_route(str(getattr(gateway, "model", "unknown")))
    return _safe_route(f"{provider}.{model}")


def _scope_anchor_ids(
    item: PlannedWorkItemSpec,
    signals: DocumentSignalBundle,
) -> tuple[str, ...]:
    if item.input_unit is InputUnit.ANCHOR_BATCH:
        for batch in signals.planning_scope.anchor_batches:
            if item.scope_key.endswith(f":batch:{batch.id}"):
                return batch.anchor_ids
        raise ValueError(f"plan item {item.id} has no matching anchor batch")
    if item.input_unit is InputUnit.CHAPTER_CANDIDATES:
        for chapter_id in signals.planning_scope.chapter_ids:
            if item.scope_key.endswith(f":chapter:{chapter_id}"):
                return tuple(
                    anchor_id
                    for batch in signals.planning_scope.anchor_batches
                    if batch.chapter_id == chapter_id
                    for anchor_id in batch.anchor_ids
                )
        raise ValueError(f"plan item {item.id} has no matching chapter")
    # Book/document/review units are content-addressed by checksum as well as
    # the full ordered anchor locator sequence.  No paragraph body is copied.
    return signals.anchor_ids


def adapt_work_item_spec(
    *,
    plan: AnalysisPlan,
    item: PlannedWorkItemSpec,
    signals: DocumentSignalBundle,
    source_id: str | None,
    gateway: ModelGateway,
    input_revision: int = 1,
) -> RuntimeWorkItemSpec:
    """Adapt a planned item without losing its semantic/idempotency identity."""

    if item.id not in {candidate.id for candidate in plan.work_items}:
        raise ValueError("work item does not belong to the supplied plan")
    if item.executor is ExecutorKind.DETERMINISTIC:
        model_route = "deterministic.local"
    elif item.executor is ExecutorKind.HUMAN_GATE:
        model_route = "human.review"
    else:
        model_route = _gateway_route(gateway)
    return RuntimeWorkItemSpec(
        source_checksum=plan.source_checksum,
        source_id=source_id,
        anchor_ids=_scope_anchor_ids(item, signals),
        pass_type=item.pass_type.value,
        input_revision=input_revision,
        pipeline_version=plan.pipeline_version,
        prompt_bundle_version=plan.prompt_bundle_version,
        model_route=model_route,
        source_policy=_source_policy_id(plan.source_policy),
        parameters={
            "plan_id": plan.id,
            "plan_work_item_id": item.id,
            "depends_on": list(item.depends_on),
            "executor": item.executor.value,
            "worker": item.worker.value,
            "input_unit": item.input_unit.value,
            "scope_key": item.scope_key,
            "output_artifact_kinds": [kind.value for kind in item.output.artifact_kinds],
        },
        max_attempts=item.max_attempts,
    )


def _merge_by_id(left: list, right: list) -> list:
    merged = {item.id: item for item in left}
    for item in right:
        merged[item.id] = item
    return list(merged.values())


def merge_artifacts(
    left: AnalysisArtifacts,
    right: AnalysisArtifacts,
) -> AnalysisArtifacts:
    """Stable merge; later reviewed revisions replace candidates with the same ID."""

    return AnalysisArtifacts(
        claims=_merge_by_id(left.claims, right.claims),
        temporal_refs=_merge_by_id(left.temporal_refs, right.temporal_refs),
        location_refs=_merge_by_id(left.location_refs, right.location_refs),
        events=_merge_by_id(left.events, right.events),
        evidence_relations=_merge_by_id(
            left.evidence_relations, right.evidence_relations
        ),
        gaps=_merge_by_id(left.gaps, right.gaps),
    )


def _artifact_delta(
    before: AnalysisArtifacts,
    after: AnalysisArtifacts,
) -> AnalysisArtifacts:
    return AnalysisArtifacts(
        claims=[item for item in after.claims if item.id not in {v.id for v in before.claims}],
        temporal_refs=[
            item for item in after.temporal_refs if item.id not in {v.id for v in before.temporal_refs}
        ],
        location_refs=[
            item for item in after.location_refs if item.id not in {v.id for v in before.location_refs}
        ],
        events=[item for item in after.events if item.id not in {v.id for v in before.events}],
        evidence_relations=[
            item
            for item in after.evidence_relations
            if item.id not in {v.id for v in before.evidence_relations}
        ],
        gaps=[item for item in after.gaps if item.id not in {v.id for v in before.gaps}],
    )


def _subset_for_anchors(
    artifacts: AnalysisArtifacts,
    anchor_ids: set[str],
) -> AnalysisArtifacts:
    claims = [
        claim
        for claim in artifacts.claims
        if set(claim.source_anchor_ids).intersection(anchor_ids)
    ]
    claim_ids = {claim.id for claim in claims}
    return AnalysisArtifacts(
        claims=claims,
        temporal_refs=[
            item
            for item in artifacts.temporal_refs
            if set(item.source_anchor_ids).intersection(anchor_ids)
        ],
        location_refs=[
            item
            for item in artifacts.location_refs
            if set(item.source_anchor_ids).intersection(anchor_ids)
        ],
        events=[
            event
            for event in artifacts.events
            if set(event.claim_ids).intersection(claim_ids)
            or set(event.source_anchor_ids).intersection(anchor_ids)
        ],
        evidence_relations=[
            relation
            for relation in artifacts.evidence_relations
            if relation.from_claim_id in claim_ids and relation.to_claim_id in claim_ids
        ],
        gaps=[],
    )


def _not_called_gap(item: PlannedWorkItemSpec, detail: str) -> AnalysisArtifacts:
    digest = sha256(f"{item.id}\0{detail}".encode()).hexdigest()[:20]
    return AnalysisArtifacts(
        gaps=[
            Gap(
                id=f"gap_{digest}",
                code="model_not_called",
                target_type="passage_unit",
                target_id=item.id,
                detail=detail,
            )
        ]
    )


class WorkerRegistry:
    """Dispatch runtime work to bounded deterministic or gateway passes."""

    def __init__(
        self,
        *,
        document: PrivateDocument,
        plan: AnalysisPlan,
        gateway: ModelGateway,
        initial_artifacts: AnalysisArtifacts | None = None,
        location_resolver: Callable[[str], VerifiedLocation | None] | None = None,
    ) -> None:
        self.plan = plan
        self.gateway = gateway
        self.artifacts = initial_artifacts or AnalysisArtifacts()
        self.reviewed_artifacts: AnalysisArtifacts | None = None
        self.location_resolver = location_resolver
        self._plan_items = {item.id: item for item in plan.work_items}
        self._anchors = {
            paragraph.id: paragraph.text
            for section in document.sections
            for paragraph in section.paragraphs
        }

    def merge(self, artifacts: AnalysisArtifacts) -> None:
        self.artifacts = merge_artifacts(self.artifacts, artifacts)

    def _plan_item(self, item: WorkItemRecord) -> PlannedWorkItemSpec:
        plan_item_id = item.spec.get("parameters", {}).get("plan_work_item_id")
        try:
            return self._plan_items[str(plan_item_id)]
        except KeyError as exc:
            raise PermanentWorkError("PLAN_ITEM_NOT_FOUND") from exc

    def _structured(self, item: WorkItemRecord, plan_item: PlannedWorkItemSpec) -> AnalysisArtifacts:
        anchors = []
        for anchor_id in item.spec.get("anchor_ids", []):
            text = self._anchors.get(str(anchor_id))
            if text is None:
                raise PermanentWorkError("SOURCE_ANCHOR_NOT_FOUND")
            anchors.append(SourceAnchorInput(id=str(anchor_id), text=text))
        if not anchors:
            return _not_called_gap(plan_item, "Model pass has no bounded source packet.")
        if len(anchors) > 80:
            return _not_called_gap(plan_item, "Model source packet exceeds the bounded pass limit.")
        if sum(len(anchor.text) for anchor in anchors) > 40_000:
            return _not_called_gap(
                plan_item,
                "Model source packet exceeds the 40,000-character runtime limit.",
            )
        requested_outputs = {
            AnalysisPass.PASSAGE_ANALYSIS: ("claims", "temporal_refs", "location_refs"),
            AnalysisPass.EVENT_EXTRACTION: (
                "claims",
                "temporal_refs",
                "location_refs",
                "events",
            ),
            AnalysisPass.LIFE_EVENT_EXTRACTION: (
                "claims",
                "temporal_refs",
                "location_refs",
                "events",
            ),
            AnalysisPass.SOURCE_DATE_ATTRIBUTION: ("claims", "temporal_refs"),
        }.get(plan_item.pass_type, ("claims",))
        allowed_claim_kinds = None
        if plan_item.pass_type in {
            AnalysisPass.ARGUMENT_EXTRACTION,
            AnalysisPass.LIMITATION_EXTRACTION,
        }:
            allowed_claim_kinds = {EpistemicLayer.AUTHOR_JUDGMENT}
        elif plan_item.pass_type in {
            AnalysisPass.SPEAKER_ATTRIBUTION,
            AnalysisPass.SOURCE_DATE_ATTRIBUTION,
        }:
            allowed_claim_kinds = {EpistemicLayer.SOURCE_STATEMENT}
        return run_structured_extract_pass(
            self.gateway,
            PassageUnit(id=plan_item.id, anchors=anchors),
            requested_outputs=requested_outputs,
            analysis_focus=plan_item.pass_type.value,
            allowed_claim_kinds=allowed_claim_kinds,
            location_resolver=self.location_resolver,
        )

    def _execute(self, item: WorkItemRecord, plan_item: PlannedWorkItemSpec) -> AnalysisArtifacts:
        pass_type = plan_item.pass_type
        if plan_item.executor is ExecutorKind.DETERMINISTIC:
            return AnalysisArtifacts()
        if pass_type is AnalysisPass.HUMAN_REVIEW:
            if self.reviewed_artifacts is None:
                raise PermanentWorkError("HUMAN_REVIEW_REQUIRED")
            return self.reviewed_artifacts
        if plan_item.input_unit is InputUnit.ANCHOR_BATCH:
            return self._structured(item, plan_item)
        if pass_type in {
            AnalysisPass.CHAPTER_DIGEST,
            AnalysisPass.CROSS_CHAPTER_SYNTHESIS,
            AnalysisPass.PERIOD_COMPARISON,
        }:
            base = self.artifacts
            if plan_item.input_unit is InputUnit.CHAPTER_CANDIDATES:
                base = _subset_for_anchors(
                    base, set(str(value) for value in item.spec.get("anchor_ids", []))
                )
            after = run_cross_unit_synthesis_pass(
                self.gateway, base, synthesis_id=plan_item.id
            )
            return _artifact_delta(base, after)
        if pass_type in {AnalysisPass.CRITIC_AUDIT, AnalysisPass.EXTERNAL_EVIDENCE}:
            after = run_evidence_judge_pass(
                self.gateway, self.artifacts, judgment_id=plan_item.id
            )
            return _artifact_delta(self.artifacts, after)
        return _not_called_gap(
            plan_item,
            f"No bounded gateway adapter exists for {pass_type.value}.",
        )

    def __call__(self, item: WorkItemRecord) -> WorkResult:
        plan_item = self._plan_item(item)
        if plan_item.pass_type is AnalysisPass.BUILD_PROJECTIONS:
            reviewed = self.reviewed_artifacts or self.artifacts
            bundle = build_projection_bundle(
                reviewed,
                available_anchor_ids=set(self._anchors),
                include_pending=False,
            )
            return WorkResult(
                artifact_kind="projection_bundle.v1",
                artifact_payload={
                    "plan_work_item_id": plan_item.id,
                    "projection": bundle.model_dump(mode="json"),
                },
                checkpoint_state={
                    "plan_work_item_id": plan_item.id,
                    "accepted_only": True,
                },
            )
        produced = self._execute(item, plan_item)
        self.merge(produced)
        return WorkResult(
            artifact_kind="analysis_artifacts.v1",
            artifact_payload={
                "plan_work_item_id": plan_item.id,
                "artifacts": produced.model_dump(mode="json"),
            },
            checkpoint_state={
                "plan_work_item_id": plan_item.id,
                "completed_anchor_ids": list(item.spec.get("anchor_ids", [])),
                "artifact_counts": {
                    "claims": len(produced.claims),
                    "events": len(produced.events),
                    "gaps": len(produced.gaps),
                },
            },
            trace={
                "plan_work_item_id": plan_item.id,
                "pass_type": plan_item.pass_type.value,
            },
        )


def build_quality_report(
    artifacts: AnalysisArtifacts,
    *,
    available_anchor_ids: set[str],
    reviewed: bool,
) -> QualityReport:
    validation = validate_analysis_artifacts(
        artifacts, available_anchor_ids=available_anchor_ids
    )
    claims_with_required_provenance = all(
        claim.source_anchor_ids
        or claim.derived_from_claim_ids
        or claim.external_source_ids
        for claim in artifacts.claims
    )
    accepted_claims = sum(claim.review_status == "accepted" for claim in artifacts.claims)
    accepted_events = sum(event.review_status == "accepted" for event in artifacts.events)
    gates = (
        QualityGateResult(
            code="all_references_resolve",
            passed=validation.is_valid,
            detail="Cross-artifact references and source anchors resolve."
            if validation.is_valid
            else "One or more cross-artifact references do not resolve.",
        ),
        QualityGateResult(
            code="all_claims_have_provenance",
            passed=claims_with_required_provenance,
            detail="Every claim retains an anchor, derivation, or external source ID.",
        ),
        QualityGateResult(
            code="epistemic_layers_preserved",
            passed=validation.is_valid,
            detail="Typed claim layers remain separate and validated.",
        ),
        QualityGateResult(
            code="human_review_required",
            passed=reviewed,
            detail="Human review has accepted or rejected candidates."
            if reviewed
            else "Candidates remain pending human review.",
        ),
        QualityGateResult(
            code="projection_uses_reviewed_candidates",
            passed=reviewed,
            detail="Projection builder is configured for accepted candidates only.",
        ),
    )
    return QualityReport(
        validation_issues=validation.issues,
        gates=gates,
        claim_count=len(artifacts.claims),
        event_count=len(artifacts.events),
        gap_count=len(artifacts.gaps),
        model_not_called_count=sum(gap.code == "model_not_called" for gap in artifacts.gaps),
        accepted_claim_count=accepted_claims,
        accepted_event_count=accepted_events,
    )


def rehydrate_analysis_artifacts(
    repository: ExplorationRepository,
    run_id: str,
) -> tuple[AnalysisArtifacts, tuple[str, ...]]:
    artifacts = AnalysisArtifacts()
    completed: list[str] = []
    for item in repository.list_run_work_items(run_id):
        if item.state is not WorkItemState.SUCCEEDED or item.output_revision is None:
            continue
        revision = repository.get_artifact_revision(item.workspace_id, item.output_revision)
        plan_item_id = revision.payload.get("plan_work_item_id")
        if isinstance(plan_item_id, str):
            completed.append(plan_item_id)
        payload = revision.payload.get("artifacts")
        if isinstance(payload, Mapping):
            artifacts = merge_artifacts(
                artifacts, AnalysisArtifacts.model_validate(dict(payload))
            )
    return artifacts, tuple(dict.fromkeys(completed))


def review_revision(artifacts: AnalysisArtifacts) -> int:
    payload = {
        "claims": [(item.id, item.review_status) for item in artifacts.claims],
        "events": [(item.id, item.review_status) for item in artifacts.events],
    }
    return int(sha256(_canonical(payload).encode()).hexdigest()[:8], 16)


def run_exploration_pipeline(
    document: PrivateDocument,
    *,
    repository: ExplorationRepository,
    workspace_id: str,
    source_id: str | None = None,
    gateway: ModelGateway | None = None,
    source_policy: SourcePolicy | None = None,
    reviewer: Reviewer | None = None,
    run_id: str | None = None,
    anchor_batch_size: int = 24,
    max_items: int | None = None,
    location_resolver: Callable[[str], VerifiedLocation | None] | None = None,
) -> PipelineResult:
    """Run or resume one durable, evidence-bounded analysis plan.

    Without ``reviewer`` the pipeline deliberately stops at
    ``waiting_review``.  Its returned projection is still built, but contains
    accepted candidates only (normally empty); pending model output never
    leaks into the product read model.
    """

    active_gateway = gateway or NoModelGateway()
    effective_source_id = source_id or document.id
    existing_run = repository.get_run(run_id) if run_id is not None else None
    profile_revision = existing_run.plan_revision if existing_run is not None else 1
    signals = derive_document_signals(document, anchor_batch_size=anchor_batch_size)
    profile = build_book_profile(
        source_checksum=document.checksum_sha256,
        metadata=signals.metadata,
        structure=signals.structure,
        section_signals=signals.sections,
        profile_revision=profile_revision,
    )
    plan = compile_analysis_plan(
        profile,
        source_policy=source_policy,
        planning_scope=signals.planning_scope,
    )
    runtime = ExplorationRuntime(repository)
    if run_id is None:
        run = runtime.create_run(workspace_id, plan_revision=profile.profile_revision)
        run_id = run.id
    else:
        run = existing_run
        assert run is not None
        if run.workspace_id != workspace_id:
            raise ValueError("run belongs to a different workspace")

    pre_review = []
    post_review = []
    reached_review = False
    for item in plan.work_items:
        if item.pass_type is AnalysisPass.HUMAN_REVIEW:
            reached_review = True
        (post_review if reached_review else pre_review).append(item)

    for item in pre_review:
        runtime.enqueue(
            run_id,
            adapt_work_item_spec(
                plan=plan,
                item=item,
                signals=signals,
                source_id=effective_source_id,
                gateway=active_gateway,
                input_revision=profile.profile_revision,
            ),
        )
    persisted, completed = rehydrate_analysis_artifacts(repository, run_id)
    registry = WorkerRegistry(
        document=document,
        plan=plan,
        gateway=active_gateway,
        initial_artifacts=persisted,
        location_resolver=location_resolver,
    )
    runtime.execute_until_idle(run_id, registry, max_items=max_items)
    artifacts, completed = rehydrate_analysis_artifacts(repository, run_id)
    registry.artifacts = artifacts
    durable_state = repository.get_run(run_id).state
    completed_ids = set(completed)
    pre_review_complete = all(item.id in completed_ids for item in pre_review)
    post_review_complete = all(item.id in completed_ids for item in post_review)

    if post_review_complete:
        projections = build_projection_bundle(
            artifacts,
            available_anchor_ids=set(signals.anchor_ids),
            include_pending=False,
        )
        return PipelineResult(
            run_id=run_id,
            state=durable_state.value,
            profile=profile,
            plan=plan,
            artifacts=artifacts,
            quality_report=build_quality_report(
                artifacts,
                available_anchor_ids=set(signals.anchor_ids),
                reviewed=True,
            ),
            projections=projections,
            completed_plan_work_item_ids=completed,
        )

    if not pre_review_complete or durable_state in {
        RunState.PLANNED,
        RunState.QUEUED,
        RunState.RUNNING,
        RunState.RETRY_WAIT,
        RunState.FAILED,
        RunState.CANCELLED,
    }:
        projections = build_projection_bundle(
            artifacts,
            available_anchor_ids=set(signals.anchor_ids),
            include_pending=False,
        )
        return PipelineResult(
            run_id=run_id,
            state=durable_state.value,
            profile=profile,
            plan=plan,
            artifacts=artifacts,
            quality_report=build_quality_report(
                artifacts,
                available_anchor_ids=set(signals.anchor_ids),
                reviewed=False,
            ),
            projections=projections,
            completed_plan_work_item_ids=completed,
        )

    # Pre-review work has drained successfully.  Persist the gate before
    # returning or invoking a process-local reviewer so a restart cannot turn
    # an unreviewed run into a completed product artifact.
    durable_state = repository.mark_waiting_review(run_id).state
    if reviewer is None:
        projections = build_projection_bundle(
            artifacts,
            available_anchor_ids=set(signals.anchor_ids),
            include_pending=False,
        )
        return PipelineResult(
            run_id=run_id,
            state="waiting_review",
            profile=profile,
            plan=plan,
            artifacts=artifacts,
            quality_report=build_quality_report(
                artifacts,
                available_anchor_ids=set(signals.anchor_ids),
                reviewed=False,
            ),
            projections=projections,
            completed_plan_work_item_ids=completed,
        )

    reviewed = reviewer(artifacts)
    if not isinstance(reviewed, AnalysisArtifacts):
        raise TypeError("reviewer must return AnalysisArtifacts")
    review_validation = validate_analysis_artifacts(
        reviewed, available_anchor_ids=set(signals.anchor_ids)
    )
    if not review_validation.is_valid:
        codes = ", ".join(issue.code for issue in review_validation.issues)
        raise ValueError(f"reviewed artifacts failed validation: {codes}")
    registry.reviewed_artifacts = reviewed
    registry.artifacts = reviewed
    revision = review_revision(reviewed)
    for item in post_review:
        runtime.enqueue(
            run_id,
            adapt_work_item_spec(
                plan=plan,
                item=item,
                signals=signals,
                source_id=effective_source_id,
                gateway=active_gateway,
                input_revision=revision,
            ),
        )
    # Enqueue remains held while WAITING_REVIEW; only this explicit transition
    # permits workers to claim post-review items.  Repeated calls are safe when
    # all post-review items were already reused by idempotency key.
    repository.release_waiting_review(run_id)
    runtime.execute_until_idle(run_id, registry)
    completed_artifacts, completed = rehydrate_analysis_artifacts(repository, run_id)
    # The review gate artifact contains the reviewed candidates and therefore
    # rehydrates as the final accepted domain revision.
    artifacts = merge_artifacts(completed_artifacts, reviewed)
    projections = build_projection_bundle(
        artifacts,
        available_anchor_ids=set(signals.anchor_ids),
        include_pending=False,
    )
    final_state = repository.get_run(run_id).state
    return PipelineResult(
        run_id=run_id,
        state=final_state.value,
        profile=profile,
        plan=plan,
        artifacts=artifacts,
        quality_report=build_quality_report(
            artifacts,
            available_anchor_ids=set(signals.anchor_ids),
            reviewed=True,
        ),
        projections=projections,
        completed_plan_work_item_ids=completed,
    )


__all__ = [
    "PipelineResult",
    "QualityGateResult",
    "QualityReport",
    "WorkerRegistry",
    "adapt_work_item_spec",
    "build_quality_report",
    "merge_artifacts",
    "rehydrate_analysis_artifacts",
    "review_revision",
    "run_exploration_pipeline",
]
