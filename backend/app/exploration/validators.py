"""Cross-artifact integrity gates for v6 analysis and projections."""
from __future__ import annotations

from typing import Iterable, Literal, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from .contracts import EpistemicLayer
from .passes import AnalysisArtifacts

if TYPE_CHECKING:
    from .projections import ProjectionBundle


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1, max_length=120)
    severity: Literal["error", "warning"]
    artifact_type: str = Field(min_length=1, max_length=120)
    artifact_id: str = Field(min_length=1, max_length=240)
    detail: str = Field(min_length=1, max_length=2_000)


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(issue.severity == "error" for issue in self.issues)


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return duplicate


def _issue(
    code: str,
    artifact_type: str,
    artifact_id: str,
    detail: str,
    *,
    severity: Literal["error", "warning"] = "error",
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        severity=severity,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        detail=detail,
    )


def validate_analysis_artifacts(
    artifacts: AnalysisArtifacts,
    *,
    available_anchor_ids: set[str] | None = None,
) -> ValidationReport:
    """Validate references and epistemic boundaries across pass outputs."""

    issues: list[ValidationIssue] = []
    collections = {
        "claim": [item.id for item in artifacts.claims],
        "temporal_ref": [item.id for item in artifacts.temporal_refs],
        "location_ref": [item.id for item in artifacts.location_refs],
        "event": [item.id for item in artifacts.events],
        "evidence_relation": [item.id for item in artifacts.evidence_relations],
        "gap": [item.id for item in artifacts.gaps],
    }
    all_ids = [item_id for values in collections.values() for item_id in values]
    for duplicate in sorted(_duplicates(all_ids)):
        issues.append(
            _issue(
                "duplicate_artifact_id",
                "artifact",
                duplicate,
                "Artifact IDs must be unique across the complete analysis bundle.",
            )
        )

    claim_ids = set(collections["claim"])
    temporal_ids = set(collections["temporal_ref"])
    location_ids = set(collections["location_ref"])

    for claim in artifacts.claims:
        if claim.kind in {
            EpistemicLayer.SOURCE_STATEMENT,
            EpistemicLayer.AUTHOR_JUDGMENT,
        } and not claim.source_anchor_ids:
            issues.append(
                _issue(
                    "claim_missing_anchor",
                    "claim",
                    claim.id,
                    "Book-source and author claims require at least one anchor.",
                )
            )
        if (
            available_anchor_ids is not None
            and not set(claim.source_anchor_ids).issubset(available_anchor_ids)
        ):
            issues.append(
                _issue(
                    "unknown_anchor",
                    "claim",
                    claim.id,
                    "Claim references an anchor absent from the source index.",
                )
            )
        if claim.kind == EpistemicLayer.AUTHOR_JUDGMENT and not claim.speaker:
            issues.append(
                _issue(
                    "author_speaker_missing",
                    "claim",
                    claim.id,
                    "Author judgment must retain its speaker.",
                )
            )
        if claim.kind == EpistemicLayer.PLATFORM_INFERENCE:
            if not set(claim.derived_from_claim_ids).issubset(claim_ids):
                issues.append(
                    _issue(
                        "unknown_derivation",
                        "claim",
                        claim.id,
                        "Platform inference has a dangling derived claim ID.",
                    )
                )
            if claim.id in claim.derived_from_claim_ids:
                issues.append(
                    _issue(
                        "cyclic_derivation",
                        "claim",
                        claim.id,
                        "A platform inference cannot derive from itself.",
                    )
                )
            if not claim.limitations:
                issues.append(
                    _issue(
                        "inference_limitation_missing",
                        "claim",
                        claim.id,
                        "Platform inference requires an explicit limitation.",
                    )
                )
        if (
            claim.kind == EpistemicLayer.EXTERNAL_EVIDENCE
            and not claim.external_source_ids
        ):
            issues.append(
                _issue(
                    "external_source_missing",
                    "claim",
                    claim.id,
                    "External evidence requires an independent source ID.",
                )
            )

    for temporal_ref in artifacts.temporal_refs:
        if (
            available_anchor_ids is not None
            and not set(temporal_ref.source_anchor_ids).issubset(
                available_anchor_ids
            )
        ):
            issues.append(
                _issue(
                    "unknown_anchor",
                    "temporal_ref",
                    temporal_ref.id,
                    "Temporal reference uses an unknown source anchor.",
                )
            )

    for location_ref in artifacts.location_refs:
        if (
            available_anchor_ids is not None
            and not set(location_ref.source_anchor_ids).issubset(
                available_anchor_ids
            )
        ):
            issues.append(
                _issue(
                    "unknown_anchor",
                    "location_ref",
                    location_ref.id,
                    "Location reference uses an unknown source anchor.",
                )
            )
        has_geometry = any(
            value is not None
            for value in (
                location_ref.longitude,
                location_ref.latitude,
                location_ref.coordinate_source_id,
            )
        )
        if location_ref.geometry_status != "verified" and has_geometry:
            issues.append(
                _issue(
                    "unverified_geometry",
                    "location_ref",
                    location_ref.id,
                    "Only verified locations may carry geometry.",
                )
            )

    for event in artifacts.events:
        for code, values, known in (
            ("unknown_event_claim", event.claim_ids, claim_ids),
            ("unknown_event_time", event.temporal_ref_ids, temporal_ids),
            ("unknown_event_location", event.location_ref_ids, location_ids),
        ):
            if not set(values).issubset(known):
                issues.append(
                    _issue(
                        code,
                        "event",
                        event.id,
                        "Event references an artifact absent from this bundle.",
                    )
                )
        if (
            available_anchor_ids is not None
            and not set(event.source_anchor_ids).issubset(available_anchor_ids)
        ):
            issues.append(
                _issue(
                    "unknown_anchor",
                    "event",
                    event.id,
                    "Event references an unknown source anchor.",
                )
            )

    for relation in artifacts.evidence_relations:
        if (
            relation.from_claim_id not in claim_ids
            or relation.to_claim_id not in claim_ids
        ):
            issues.append(
                _issue(
                    "unknown_relation_claim",
                    "evidence_relation",
                    relation.id,
                    "Evidence relation references an unknown claim.",
                )
            )
        if relation.relation == "contradicts" and not relation.comparison_scope:
            issues.append(
                _issue(
                    "unscoped_contradiction",
                    "evidence_relation",
                    relation.id,
                    "Contradiction is allowed only for an explicit comparable scope.",
                )
            )
        if (
            available_anchor_ids is not None
            and not set(relation.source_anchor_ids).issubset(available_anchor_ids)
        ):
            issues.append(
                _issue(
                    "unknown_anchor",
                    "evidence_relation",
                    relation.id,
                    "Evidence relation references an unknown source anchor.",
                )
            )

    derivations = {
        claim.id: set(claim.derived_from_claim_ids)
        for claim in artifacts.claims
        if claim.kind == EpistemicLayer.PLATFORM_INFERENCE
    }

    def has_derivation_cycle(start: str) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(claim_id: str) -> bool:
            if claim_id in visiting:
                return True
            if claim_id in visited:
                return False
            visiting.add(claim_id)
            if any(visit(child) for child in derivations.get(claim_id, set())):
                return True
            visiting.remove(claim_id)
            visited.add(claim_id)
            return False

        return visit(start)

    for claim_id in sorted(derivations):
        if has_derivation_cycle(claim_id):
            issues.append(
                _issue(
                    "cyclic_derivation",
                    "claim",
                    claim_id,
                    "Platform inference derivations must form an acyclic graph.",
                )
            )

    return ValidationReport(issues=tuple(issues))


def validate_projection_bundle(
    bundle: ProjectionBundle,
    artifacts: AnalysisArtifacts,
) -> ValidationReport:
    """Prove that projections did not create a second truth layer."""

    issues: list[ValidationIssue] = []
    claim_ids = {claim.id for claim in artifacts.claims}
    event_ids = {event.id for event in artifacts.events}
    temporal_ids = {item.id for item in artifacts.temporal_refs}
    location_ids = {item.id for item in artifacts.location_refs}
    verified_location_ids = {
        item.id
        for item in artifacts.location_refs
        if item.geometry_status == "verified"
    }

    for node in bundle.argument.nodes:
        if node.claim_id not in claim_ids:
            issues.append(
                _issue(
                    "projection_invented_claim",
                    "argument_node",
                    node.id,
                    "Argument projection must reference an existing claim.",
                )
            )
    for item in bundle.timeline.items:
        if item.event_id not in event_ids or not set(item.temporal_ref_ids).issubset(
            temporal_ids
        ):
            issues.append(
                _issue(
                    "projection_dangling_timeline",
                    "timeline_item",
                    item.id,
                    "Timeline projection has a dangling event or time reference.",
                )
            )
    for point in bundle.map.points:
        if point.location_ref_id not in verified_location_ids:
            issues.append(
                _issue(
                    "projection_unverified_geometry",
                    "map_point",
                    point.id,
                    "Map projection may consume only verified LocationRef geometry.",
                )
            )
    for insight in bundle.insights.items:
        if insight.claim_id not in claim_ids or not set(
            insight.derived_from_claim_ids
        ).issubset(claim_ids):
            issues.append(
                _issue(
                    "projection_dangling_insight",
                    "insight",
                    insight.id,
                    "Insight must retain its platform claim and lower-level derivations.",
                )
            )
        if not insight.limitations:
            issues.append(
                _issue(
                    "projection_missing_limitation",
                    "insight",
                    insight.id,
                    "A visible platform insight requires an explicit limitation.",
                )
            )
    for scene in bundle.scenes:
        if scene.truth_owner:
            issues.append(
                _issue(
                    "scene_became_truth_owner",
                    "scene",
                    scene.id,
                    "Scene must remain an aggregate over domain artifact IDs.",
                )
            )
        if (
            scene.event_id not in event_ids
            or not set(scene.claim_ids).issubset(claim_ids)
            or not set(scene.temporal_ref_ids).issubset(temporal_ids)
            or not set(scene.location_ref_ids).issubset(location_ids)
        ):
            issues.append(
                _issue(
                    "projection_dangling_scene",
                    "scene",
                    scene.id,
                    "Scene aggregate contains a dangling domain reference.",
                )
            )
    return ValidationReport(issues=tuple(issues))


__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "validate_analysis_artifacts",
    "validate_projection_bundle",
]
