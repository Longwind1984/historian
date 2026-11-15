"""Bounded analysis passes and typed candidate artifacts for v6.

Model output enters the system only through these passes.  Each pass converts
untrusted JSON into typed candidates, resolves every source reference against
its allowed input set, and records a ``Gap`` instead of repairing missing
evidence with model memory.
"""
from __future__ import annotations

from hashlib import sha256
from collections.abc import Callable
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .contracts import EpistemicLayer
from .model_gateway import (
    CrossUnitSynthesisRequest,
    EvidenceJudgeRequest,
    ModelGateway,
    StructuredExtractRequest,
)


ClaimKind = EpistemicLayer
GapCode = Literal[
    "model_not_called",
    "invalid_model_output",
    "claim_missing_provenance",
    "unknown_anchor",
    "unknown_derivation",
    "unverified_location",
    "dangling_reference",
    "counterevidence_not_found",
    "no_source_content",
]
GapTarget = Literal[
    "passage_unit",
    "claim",
    "location_ref",
    "event",
    "evidence_relation",
    "synthesis",
]


def _stable_id(prefix: str, *parts: str) -> str:
    digest = sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"{prefix}_{digest}"


class SourceAnchorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=240)
    text: str = Field(min_length=1, exclude=True, repr=False)


class VerifiedLocation(BaseModel):
    """Coordinate assertion supplied by a reviewed KB or explicit source."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str = Field(min_length=1, max_length=240)
    label: str = Field(min_length=1, max_length=300)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    coordinate_source_id: str = Field(min_length=1, max_length=500)


class PassageUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=200)
    anchors: list[SourceAnchorInput] = Field(min_length=1, max_length=80)
    verified_locations: list[VerifiedLocation] = Field(
        default_factory=list, max_length=200
    )
    input_artifact_ids: list[str] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> PassageUnit:
        anchor_ids = [anchor.id for anchor in self.anchors]
        if len(set(anchor_ids)) != len(anchor_ids):
            raise ValueError("PassageUnit anchor IDs must be unique")
        location_ids = [location.entity_id for location in self.verified_locations]
        if len(set(location_ids)) != len(location_ids):
            raise ValueError("Verified location entity IDs must be unique")
        return self


class ClaimCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=240)
    statement: str = Field(min_length=1, max_length=8_000)
    kind: EpistemicLayer
    speaker: str | None = Field(default=None, max_length=300)
    source_anchor_ids: list[str] = Field(default_factory=list, max_length=80)
    derived_from_claim_ids: list[str] = Field(default_factory=list, max_length=500)
    external_source_ids: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    review_status: Literal["pending_review", "accepted", "rejected"] = (
        "pending_review"
    )

    @model_validator(mode="after")
    def _epistemic_provenance(self) -> ClaimCandidate:
        for field_name, values in (
            ("source_anchor_ids", self.source_anchor_ids),
            ("derived_from_claim_ids", self.derived_from_claim_ids),
            ("external_source_ids", self.external_source_ids),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must be unique")
        if self.kind in {
            EpistemicLayer.SOURCE_STATEMENT,
            EpistemicLayer.AUTHOR_JUDGMENT,
        }:
            if not self.source_anchor_ids:
                raise ValueError(f"{self.kind} requires source_anchor_ids")
        if self.kind == EpistemicLayer.AUTHOR_JUDGMENT and not self.speaker:
            raise ValueError("author_judgment requires a speaker")
        if self.kind == EpistemicLayer.PLATFORM_INFERENCE:
            if not self.derived_from_claim_ids:
                raise ValueError("platform_inference requires derived claim IDs")
            if not self.limitations:
                raise ValueError("platform_inference requires a limitation")
        if (
            self.kind == EpistemicLayer.EXTERNAL_EVIDENCE
            and not self.external_source_ids
        ):
            raise ValueError("external_evidence requires an independent source ID")
        return self


class TemporalRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=240)
    original_label: str = Field(min_length=1, max_length=500)
    source_anchor_ids: list[str] = Field(min_length=1, max_length=80)
    normalization_status: Literal["verbatim", "candidate", "verified"] = "verbatim"
    normalized_start: str | None = Field(default=None, max_length=100)
    normalized_end: str | None = Field(default=None, max_length=100)
    precision: Literal[
        "exact_day",
        "month",
        "year",
        "range",
        "relative",
        "unknown",
    ] = "unknown"

    @model_validator(mode="after")
    def _do_not_promote_unverified_dates(self) -> TemporalRef:
        if self.normalization_status != "verified" and (
            self.normalized_start is not None or self.normalized_end is not None
        ):
            raise ValueError("Only verified temporal refs may carry normalized values")
        return self


class LocationRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=240)
    original_label: str = Field(min_length=1, max_length=500)
    source_anchor_ids: list[str] = Field(min_length=1, max_length=80)
    resolved_entity_id: str | None = Field(default=None, max_length=240)
    geometry_status: Literal["verified", "candidate", "ambiguous", "none"]
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    coordinate_source_id: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _coordinates_require_reviewed_source(self) -> LocationRef:
        coordinate_fields = (
            self.longitude,
            self.latitude,
            self.coordinate_source_id,
        )
        if self.geometry_status == "verified":
            if self.resolved_entity_id is None or any(
                value is None for value in coordinate_fields
            ):
                raise ValueError(
                    "verified locations require entity, coordinates, and source"
                )
        elif any(value is not None for value in coordinate_fields):
            raise ValueError("Unverified locations cannot carry coordinates")
        return self


class EventCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=240)
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=4_000)
    claim_ids: list[str] = Field(min_length=1, max_length=200)
    source_anchor_ids: list[str] = Field(default_factory=list, max_length=80)
    temporal_ref_ids: list[str] = Field(default_factory=list, max_length=100)
    location_ref_ids: list[str] = Field(default_factory=list, max_length=100)
    person_ids: list[str] = Field(default_factory=list, max_length=100)
    review_status: Literal["pending_review", "accepted", "rejected"] = (
        "pending_review"
    )


class EvidenceRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=240)
    from_claim_id: str = Field(min_length=1, max_length=240)
    to_claim_id: str = Field(min_length=1, max_length=240)
    relation: Literal[
        "supports",
        "corroborates",
        "supplements",
        "different_scope",
        "method_difference",
        "narrows",
        "contradicts",
        "causal_proposal",
        "author_interprets",
        "model_infers",
    ]
    source_anchor_ids: list[str] = Field(default_factory=list, max_length=160)
    external_source_ids: list[str] = Field(default_factory=list, max_length=100)
    comparison_scope: str | None = Field(default=None, max_length=1_000)

    @model_validator(mode="after")
    def _contradiction_needs_comparable_evidence(self) -> EvidenceRelation:
        if self.from_claim_id == self.to_claim_id:
            raise ValueError("Evidence relations require two distinct claims")
        if self.relation == "contradicts" and (
            not self.comparison_scope
            or not (self.source_anchor_ids or self.external_source_ids)
        ):
            raise ValueError(
                "contradicts requires a comparable scope and material evidence"
            )
        return self


class Gap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=240)
    code: GapCode
    target_type: GapTarget
    target_id: str
    detail: str = Field(min_length=1, max_length=2_000)


class AnalysisArtifacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[ClaimCandidate] = Field(default_factory=list)
    temporal_refs: list[TemporalRef] = Field(default_factory=list)
    location_refs: list[LocationRef] = Field(default_factory=list)
    events: list[EventCandidate] = Field(default_factory=list)
    evidence_relations: list[EvidenceRelation] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)

    def merged(self, other: AnalysisArtifacts) -> AnalysisArtifacts:
        return AnalysisArtifacts(
            claims=[*self.claims, *other.claims],
            temporal_refs=[*self.temporal_refs, *other.temporal_refs],
            location_refs=[*self.location_refs, *other.location_refs],
            events=[*self.events, *other.events],
            evidence_relations=[*self.evidence_relations, *other.evidence_relations],
            gaps=[*self.gaps, *other.gaps],
        )


def _gap(
    code: GapCode,
    target_type: GapTarget,
    target_id: str,
    detail: str,
) -> Gap:
    return Gap(
        id=_stable_id("gap", str(code), str(target_type), target_id, detail),
        code=code,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )


def _as_records(output: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = output.get(key, [])
    if not isinstance(value, list):
        return []
    return [record for record in value if isinstance(record, dict)]


def _anchors_are_allowed(values: Sequence[str], allowed: set[str]) -> bool:
    return bool(values) and set(values).issubset(allowed)


def _parse_claims(
    raw_claims: list[dict[str, Any]],
    *,
    allowed_anchor_ids: set[str],
    known_claim_ids: set[str],
    allowed_kinds: set[EpistemicLayer] | None = None,
) -> tuple[list[ClaimCandidate], list[Gap]]:
    claims: list[ClaimCandidate] = []
    gaps: list[Gap] = []
    for index, raw in enumerate(raw_claims):
        target_id = str(raw.get("id") or f"claim_at_{index}")
        try:
            candidate_payload = dict(raw)
            # A model is never its own reviewer.  Promotion is a separate
            # human-gate mutation even if provider output says "accepted".
            candidate_payload["review_status"] = "pending_review"
            claim = ClaimCandidate.model_validate(candidate_payload)
        except ValidationError as exc:
            message = str(exc)
            code = (
                "claim_missing_provenance"
                if "requires source_anchor_ids" in message
                or "requires derived claim IDs" in message
                or "requires an independent source ID" in message
                else "invalid_model_output"
            )
            gaps.append(_gap(code, "claim", target_id, message))
            continue
        if allowed_kinds is not None and claim.kind not in allowed_kinds:
            gaps.append(
                _gap(
                    "invalid_model_output",
                    "claim",
                    claim.id,
                    f"Claim kind {claim.kind} is not allowed in this pass.",
                )
            )
            continue
        if claim.source_anchor_ids and not set(claim.source_anchor_ids).issubset(
            allowed_anchor_ids
        ):
            gaps.append(
                _gap(
                    "unknown_anchor",
                    "claim",
                    claim.id,
                    "Claim references an anchor outside the authorised source packet.",
                )
            )
            continue
        if claim.derived_from_claim_ids and not set(
            claim.derived_from_claim_ids
        ).issubset(known_claim_ids | {item.id for item in claims}):
            gaps.append(
                _gap(
                    "unknown_derivation",
                    "claim",
                    claim.id,
                    "Claim derivation references an unknown lower-level claim.",
                )
            )
            continue
        claims.append(claim)
    return claims, gaps


def run_structured_extract_pass(
    gateway: ModelGateway,
    unit: PassageUnit,
    *,
    requested_outputs: Sequence[str] | None = None,
    analysis_focus: str = "passage_analysis",
    allowed_claim_kinds: set[EpistemicLayer] | None = None,
    location_resolver: Callable[[str], VerifiedLocation | None] | None = None,
) -> AnalysisArtifacts:
    """Extract local candidates without accepting invented locators/geometry."""

    anchor_ids = [anchor.id for anchor in unit.anchors]
    request = StructuredExtractRequest(
        unit_id=unit.id,
        source_anchor_ids=anchor_ids,
        input_artifact_ids=unit.input_artifact_ids,
        requested_outputs=list(
            requested_outputs
            or ("claims", "temporal_refs", "location_refs", "events")
        ),
        analysis_focus=analysis_focus,
        source_text_by_anchor_id={anchor.id: anchor.text for anchor in unit.anchors},
    )
    result = gateway.structured_extract(request)
    if result.status != "succeeded" or result.output is None:
        return AnalysisArtifacts(
            gaps=[
                _gap(
                    "model_not_called",
                    "passage_unit",
                    unit.id,
                    result.error_code or "No extraction model result was available.",
                )
            ]
        )

    allowed_anchor_ids = set(anchor_ids)
    claims, gaps = _parse_claims(
        _as_records(result.output, "claims"),
        allowed_anchor_ids=allowed_anchor_ids,
        known_claim_ids=set(),
        allowed_kinds=allowed_claim_kinds,
    )
    known_claim_ids = {claim.id for claim in claims}

    temporal_refs: list[TemporalRef] = []
    for index, raw in enumerate(_as_records(result.output, "temporal_refs")):
        target_id = str(raw.get("id") or f"temporal_ref_at_{index}")
        try:
            temporal_ref = TemporalRef.model_validate(raw)
        except ValidationError as exc:
            gaps.append(_gap("invalid_model_output", "claim", target_id, str(exc)))
            continue
        if not set(temporal_ref.source_anchor_ids).issubset(allowed_anchor_ids):
            gaps.append(
                _gap(
                    "unknown_anchor",
                    "claim",
                    temporal_ref.id,
                    "Temporal reference uses an anchor outside the source packet.",
                )
            )
            continue
        temporal_refs.append(temporal_ref)

    verified_locations = {
        location.entity_id: location for location in unit.verified_locations
    }
    location_refs: list[LocationRef] = []
    for index, raw in enumerate(_as_records(result.output, "location_refs")):
        target_id = str(raw.get("id") or f"location_ref_at_{index}")
        raw_anchor_ids = raw.get("source_anchor_ids", [])
        if not isinstance(raw_anchor_ids, list) or not _anchors_are_allowed(
            raw_anchor_ids, allowed_anchor_ids
        ):
            gaps.append(
                _gap(
                    "unknown_anchor",
                    "location_ref",
                    target_id,
                    "Location mention has no resolvable authorised source anchor.",
                )
            )
            continue
        entity_id = raw.get("resolved_entity_id")
        original_label = raw.get("original_label")
        verified = verified_locations.get(str(entity_id)) if entity_id else None
        if verified is None and location_resolver is not None and isinstance(
            original_label, str
        ):
            verified = location_resolver(original_label)
        clean = {
            "id": target_id,
            "original_label": original_label,
            "source_anchor_ids": raw_anchor_ids,
            "resolved_entity_id": (
                verified.entity_id
                if verified is not None
                else str(entity_id)
                if entity_id
                else None
            ),
            "geometry_status": (
                "verified"
                if verified is not None
                else raw.get("geometry_status", "none")
            ),
            "longitude": None,
            "latitude": None,
            "coordinate_source_id": None,
        }
        if verified is not None:
            clean.update(
                longitude=verified.longitude,
                latitude=verified.latitude,
                coordinate_source_id=verified.coordinate_source_id,
                resolved_entity_id=verified.entity_id,
            )
        elif raw.get("geometry_status") == "verified":
            clean["geometry_status"] = "candidate" if entity_id else "ambiguous"
            gaps.append(
                _gap(
                    "unverified_location",
                    "location_ref",
                    target_id,
                    "Model-provided geometry was removed because no reviewed "
                    "coordinate source matched.",
                )
            )
        try:
            location_refs.append(LocationRef.model_validate(clean))
        except ValidationError as exc:
            gaps.append(
                _gap("invalid_model_output", "location_ref", target_id, str(exc))
            )

    temporal_ids = {item.id for item in temporal_refs}
    location_ids = {item.id for item in location_refs}
    events: list[EventCandidate] = []
    for index, raw in enumerate(_as_records(result.output, "events")):
        target_id = str(raw.get("id") or f"event_at_{index}")
        try:
            candidate_payload = dict(raw)
            candidate_payload["review_status"] = "pending_review"
            event = EventCandidate.model_validate(candidate_payload)
        except ValidationError as exc:
            gaps.append(_gap("invalid_model_output", "event", target_id, str(exc)))
            continue
        dangling = (
            set(event.claim_ids) - known_claim_ids
            or set(event.temporal_ref_ids) - temporal_ids
            or set(event.location_ref_ids) - location_ids
            or set(event.source_anchor_ids) - allowed_anchor_ids
        )
        if dangling:
            gaps.append(
                _gap(
                    "dangling_reference",
                    "event",
                    event.id,
                    "Event references a claim, time, location, or anchor outside this pass.",
                )
            )
            continue
        events.append(event)

    if not claims and not temporal_refs and not location_refs and not events:
        gaps.append(
            _gap(
                "no_source_content",
                "passage_unit",
                unit.id,
                "No source-addressable analysis artifact survived validation.",
            )
        )
    return AnalysisArtifacts(
        claims=claims,
        temporal_refs=temporal_refs,
        location_refs=location_refs,
        events=events,
        gaps=gaps,
    )


def run_cross_unit_synthesis_pass(
    gateway: ModelGateway,
    artifacts: AnalysisArtifacts,
    *,
    synthesis_id: str,
) -> AnalysisArtifacts:
    """Produce platform inferences that retain lower-level derivation IDs."""

    lower_claims = [
        claim for claim in artifacts.claims if claim.review_status != "rejected"
    ]
    if not lower_claims:
        return artifacts.merged(
            AnalysisArtifacts(
                gaps=[
                    _gap(
                        "no_source_content",
                        "synthesis",
                        synthesis_id,
                        "Cross-unit synthesis has no lower-level claims.",
                    )
                ]
            )
        )
    request = CrossUnitSynthesisRequest(
        synthesis_id=synthesis_id,
        input_artifact_ids=[claim.id for claim in lower_claims],
        lower_level_artifacts=[
            claim.model_dump(mode="json") for claim in lower_claims
        ],
    )
    result = gateway.cross_unit_synthesis(request)
    if result.status != "succeeded" or result.output is None:
        return artifacts.merged(
            AnalysisArtifacts(
                gaps=[
                    _gap(
                        "model_not_called",
                        "synthesis",
                        synthesis_id,
                        result.error_code or "No synthesis model result was available.",
                    )
                ]
            )
        )
    claims, gaps = _parse_claims(
        _as_records(result.output, "claims"),
        allowed_anchor_ids={
            anchor_id for claim in lower_claims for anchor_id in claim.source_anchor_ids
        },
        known_claim_ids={claim.id for claim in lower_claims},
        allowed_kinds={EpistemicLayer.PLATFORM_INFERENCE},
    )
    return artifacts.merged(AnalysisArtifacts(claims=claims, gaps=gaps))


def run_evidence_judge_pass(
    gateway: ModelGateway,
    artifacts: AnalysisArtifacts,
    *,
    judgment_id: str,
) -> AnalysisArtifacts:
    """Review claim relations without generating placeholder opposition."""

    candidate_claims = [
        claim for claim in artifacts.claims if claim.review_status != "rejected"
    ]
    if not candidate_claims:
        return artifacts.merged(
            AnalysisArtifacts(
                gaps=[
                    _gap(
                        "no_source_content",
                        "evidence_relation",
                        judgment_id,
                        "Evidence review has no claim candidates.",
                    )
                ]
            )
        )
    request = EvidenceJudgeRequest(
        judgment_id=judgment_id,
        candidate_artifact_ids=[claim.id for claim in candidate_claims],
        evidence_artifact_ids=[
            anchor_id
            for claim in candidate_claims
            for anchor_id in claim.source_anchor_ids
        ],
        candidate_artifacts=[claim.model_dump(mode="json") for claim in candidate_claims],
        evidence_artifacts=[],
    )
    result = gateway.evidence_judge(request)
    if result.status != "succeeded" or result.output is None:
        return artifacts.merged(
            AnalysisArtifacts(
                gaps=[
                    _gap(
                        "model_not_called",
                        "evidence_relation",
                        judgment_id,
                        result.error_code or "No evidence-judge result was available.",
                    )
                ]
            )
        )

    known_claim_ids = {claim.id for claim in candidate_claims}
    known_anchor_ids = {
        anchor_id for claim in candidate_claims for anchor_id in claim.source_anchor_ids
    }
    relations: list[EvidenceRelation] = []
    gaps: list[Gap] = []
    for index, raw in enumerate(_as_records(result.output, "relations")):
        target_id = str(raw.get("id") or f"relation_at_{index}")
        try:
            relation = EvidenceRelation.model_validate(raw)
        except ValidationError as exc:
            gaps.append(
                _gap("invalid_model_output", "evidence_relation", target_id, str(exc))
            )
            continue
        if (
            relation.from_claim_id not in known_claim_ids
            or relation.to_claim_id not in known_claim_ids
            or not set(relation.source_anchor_ids).issubset(known_anchor_ids)
        ):
            gaps.append(
                _gap(
                    "dangling_reference",
                    "evidence_relation",
                    relation.id,
                    "Evidence relation contains an unknown claim or anchor.",
                )
            )
            continue
        relations.append(relation)

    not_found = result.output.get("counterevidence_not_found_claim_ids", [])
    if isinstance(not_found, list):
        for claim_id in dict.fromkeys(str(value) for value in not_found):
            if claim_id in known_claim_ids:
                gaps.append(
                    _gap(
                        "counterevidence_not_found",
                        "claim",
                        claim_id,
                        "The approved evidence search found no counterevidence; "
                        "this does not confirm the claim.",
                    )
                )
    return artifacts.merged(
        AnalysisArtifacts(evidence_relations=relations, gaps=gaps)
    )


__all__ = [
    "AnalysisArtifacts",
    "ClaimCandidate",
    "ClaimKind",
    "EventCandidate",
    "EvidenceRelation",
    "Gap",
    "LocationRef",
    "PassageUnit",
    "SourceAnchorInput",
    "TemporalRef",
    "VerifiedLocation",
    "run_cross_unit_synthesis_pass",
    "run_evidence_judge_pass",
    "run_structured_extract_pass",
]
