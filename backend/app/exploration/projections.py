"""Read models derived from validated v6 analysis artifacts.

Projection builders copy labels and references from domain candidates; they do
not call a model and cannot create historical facts.  ``SceneProjection`` is
explicitly an aggregate so alternative narrative groupings can coexist over
the same evidence graph.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .contracts import EpistemicLayer
from .passes import AnalysisArtifacts


class ProjectionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArgumentNodeProjection(ProjectionModel):
    id: str
    claim_id: str
    statement: str
    epistemic_layer: EpistemicLayer
    speaker: str | None = None
    source_anchor_ids: tuple[str, ...] = ()
    derived_from_claim_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    review_status: str


class ArgumentEdgeProjection(ProjectionModel):
    id: str
    evidence_relation_id: str
    from_claim_id: str
    to_claim_id: str
    relation: str
    source_anchor_ids: tuple[str, ...] = ()
    comparison_scope: str | None = None


class ArgumentProjection(ProjectionModel):
    nodes: tuple[ArgumentNodeProjection, ...] = ()
    edges: tuple[ArgumentEdgeProjection, ...] = ()


class TimelineItemProjection(ProjectionModel):
    id: str
    event_id: str
    title: str
    temporal_ref_ids: tuple[str, ...]
    original_time_labels: tuple[str, ...]
    source_anchor_ids: tuple[str, ...]
    review_status: str


class TimelineProjection(ProjectionModel):
    items: tuple[TimelineItemProjection, ...] = ()


class MapPointProjection(ProjectionModel):
    id: str
    sequence_index: int = Field(ge=0)
    event_id: str
    location_ref_id: str
    label: str
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    coordinate_source_id: str
    source_anchor_ids: tuple[str, ...]


class MapSequenceProjection(ProjectionModel):
    id: str
    from_point_id: str
    to_point_id: str
    semantic: Literal["sequence_not_route"] = "sequence_not_route"


class MapProjection(ProjectionModel):
    points: tuple[MapPointProjection, ...] = ()
    sequence: tuple[MapSequenceProjection, ...] = ()
    unlocated_event_ids: tuple[str, ...] = ()


class InsightProjectionItem(ProjectionModel):
    id: str
    claim_id: str
    statement: str
    epistemic_layer: Literal[EpistemicLayer.PLATFORM_INFERENCE] = (
        EpistemicLayer.PLATFORM_INFERENCE
    )
    derived_from_claim_ids: tuple[str, ...] = Field(min_length=1)
    source_anchor_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = Field(min_length=1)
    review_status: str


class InsightProjection(ProjectionModel):
    items: tuple[InsightProjectionItem, ...] = ()


class SceneProjection(ProjectionModel):
    id: str
    event_id: str
    title: str
    summary: str
    claim_ids: tuple[str, ...]
    temporal_ref_ids: tuple[str, ...]
    location_ref_ids: tuple[str, ...]
    person_ids: tuple[str, ...]
    source_anchor_ids: tuple[str, ...]
    map_state: Literal["ready", "partial", "no_location"]
    truth_owner: Literal[False] = False


class ProjectionBundle(ProjectionModel):
    argument: ArgumentProjection
    timeline: TimelineProjection
    map: MapProjection
    insights: InsightProjection
    scenes: tuple[SceneProjection, ...]


def build_argument_projection(
    artifacts: AnalysisArtifacts,
    *,
    include_pending: bool = False,
) -> ArgumentProjection:
    claims = [
        claim
        for claim in artifacts.claims
        if claim.review_status == "accepted"
        or (include_pending and claim.review_status == "pending_review")
    ]
    claim_ids = {claim.id for claim in claims}
    nodes = tuple(
        ArgumentNodeProjection(
            id=f"argument_node:{claim.id}",
            claim_id=claim.id,
            statement=claim.statement,
            epistemic_layer=claim.kind,
            speaker=claim.speaker,
            source_anchor_ids=tuple(claim.source_anchor_ids),
            derived_from_claim_ids=tuple(claim.derived_from_claim_ids),
            limitations=tuple(claim.limitations),
            review_status=claim.review_status,
        )
        for claim in claims
    )
    edges = tuple(
        ArgumentEdgeProjection(
            id=f"argument_edge:{relation.id}",
            evidence_relation_id=relation.id,
            from_claim_id=relation.from_claim_id,
            to_claim_id=relation.to_claim_id,
            relation=relation.relation,
            source_anchor_ids=tuple(relation.source_anchor_ids),
            comparison_scope=relation.comparison_scope,
        )
        for relation in artifacts.evidence_relations
        if relation.from_claim_id in claim_ids and relation.to_claim_id in claim_ids
    )
    return ArgumentProjection(nodes=nodes, edges=edges)


def build_timeline_projection(
    artifacts: AnalysisArtifacts,
    *,
    include_pending: bool = False,
) -> TimelineProjection:
    temporal_by_id = {item.id: item for item in artifacts.temporal_refs}
    events = [
        event
        for event in artifacts.events
        if event.review_status == "accepted"
        or (include_pending and event.review_status == "pending_review")
    ]
    return TimelineProjection(
        items=tuple(
            TimelineItemProjection(
                id=f"timeline_item:{event.id}",
                event_id=event.id,
                title=event.title,
                temporal_ref_ids=tuple(event.temporal_ref_ids),
                original_time_labels=tuple(
                    temporal_by_id[ref_id].original_label
                    for ref_id in event.temporal_ref_ids
                ),
                source_anchor_ids=tuple(event.source_anchor_ids),
                review_status=event.review_status,
            )
            for event in events
        )
    )


def build_map_projection(
    artifacts: AnalysisArtifacts,
    *,
    include_pending: bool = False,
) -> MapProjection:
    verified_locations = {
        item.id: item
        for item in artifacts.location_refs
        if item.geometry_status == "verified"
    }
    events = [
        event
        for event in artifacts.events
        if event.review_status == "accepted"
        or (include_pending and event.review_status == "pending_review")
    ]
    points: list[MapPointProjection] = []
    unlocated: list[str] = []
    for event in events:
        located = False
        for location_ref_id in event.location_ref_ids:
            location = verified_locations.get(location_ref_id)
            if location is None:
                continue
            located = True
            points.append(
                MapPointProjection(
                    id=f"map_point:{event.id}:{location.id}",
                    sequence_index=len(points),
                    event_id=event.id,
                    location_ref_id=location.id,
                    label=location.original_label,
                    longitude=location.longitude,  # type: ignore[arg-type]
                    latitude=location.latitude,  # type: ignore[arg-type]
                    coordinate_source_id=location.coordinate_source_id,  # type: ignore[arg-type]
                    source_anchor_ids=tuple(location.source_anchor_ids),
                )
            )
        if not located:
            unlocated.append(event.id)
    sequence = tuple(
        MapSequenceProjection(
            id=f"map_sequence:{left.id}:{right.id}",
            from_point_id=left.id,
            to_point_id=right.id,
        )
        for left, right in zip(points, points[1:])
    )
    return MapProjection(
        points=tuple(points),
        sequence=sequence,
        unlocated_event_ids=tuple(unlocated),
    )


def build_insight_projection(
    artifacts: AnalysisArtifacts,
    *,
    include_pending: bool = False,
) -> InsightProjection:
    return InsightProjection(
        items=tuple(
            InsightProjectionItem(
                id=f"insight:{claim.id}",
                claim_id=claim.id,
                statement=claim.statement,
                derived_from_claim_ids=tuple(claim.derived_from_claim_ids),
                source_anchor_ids=tuple(claim.source_anchor_ids),
                limitations=tuple(claim.limitations),
                review_status=claim.review_status,
            )
            for claim in artifacts.claims
            if claim.kind == EpistemicLayer.PLATFORM_INFERENCE
            and (
                claim.review_status == "accepted"
                or (include_pending and claim.review_status == "pending_review")
            )
        )
    )


def build_scene_projections(
    artifacts: AnalysisArtifacts,
    *,
    include_pending: bool = False,
) -> tuple[SceneProjection, ...]:
    location_by_id = {item.id: item for item in artifacts.location_refs}
    scenes: list[SceneProjection] = []
    for event in artifacts.events:
        if not (
            event.review_status == "accepted"
            or (include_pending and event.review_status == "pending_review")
        ):
            continue
        verified_count = sum(
            location_by_id[ref_id].geometry_status == "verified"
            for ref_id in event.location_ref_ids
        )
        map_state: Literal["ready", "partial", "no_location"]
        if event.location_ref_ids and verified_count == len(event.location_ref_ids):
            map_state = "ready"
        elif verified_count:
            map_state = "partial"
        else:
            map_state = "no_location"
        scenes.append(
            SceneProjection(
                id=f"scene:{event.id}",
                event_id=event.id,
                title=event.title,
                summary=event.summary,
                claim_ids=tuple(event.claim_ids),
                temporal_ref_ids=tuple(event.temporal_ref_ids),
                location_ref_ids=tuple(event.location_ref_ids),
                person_ids=tuple(event.person_ids),
                source_anchor_ids=tuple(event.source_anchor_ids),
                map_state=map_state,
            )
        )
    return tuple(scenes)


def build_projection_bundle(
    artifacts: AnalysisArtifacts,
    *,
    available_anchor_ids: set[str] | None = None,
    include_pending: bool = False,
) -> ProjectionBundle:
    """Build all product read models after the domain integrity gate passes."""

    from .validators import validate_analysis_artifacts, validate_projection_bundle

    domain_report = validate_analysis_artifacts(
        artifacts, available_anchor_ids=available_anchor_ids
    )
    if not domain_report.is_valid:
        codes = ", ".join(issue.code for issue in domain_report.issues)
        raise ValueError(f"Analysis artifacts failed validation: {codes}")
    bundle = ProjectionBundle(
        argument=build_argument_projection(
            artifacts, include_pending=include_pending
        ),
        timeline=build_timeline_projection(
            artifacts, include_pending=include_pending
        ),
        map=build_map_projection(artifacts, include_pending=include_pending),
        insights=build_insight_projection(
            artifacts, include_pending=include_pending
        ),
        scenes=build_scene_projections(
            artifacts, include_pending=include_pending
        ),
    )
    projection_report = validate_projection_bundle(bundle, artifacts)
    if not projection_report.is_valid:
        codes = ", ".join(issue.code for issue in projection_report.issues)
        raise ValueError(f"Projection bundle failed validation: {codes}")
    return bundle


__all__ = [
    "ArgumentProjection",
    "InsightProjection",
    "MapProjection",
    "ProjectionBundle",
    "SceneProjection",
    "TimelineProjection",
    "build_argument_projection",
    "build_insight_projection",
    "build_map_projection",
    "build_projection_bundle",
    "build_scene_projections",
    "build_timeline_projection",
]
