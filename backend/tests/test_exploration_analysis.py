"""Contract tests for v6 analysis passes, gates, and product projections."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.exploration.georesolution import ReviewedPlaceResolver
from app.exploration.model_gateway import (
    DeterministicModelGateway,
    NoModelGateway,
    StructuredExtractRequest,
)
from app.exploration.passes import (
    AnalysisArtifacts,
    ClaimCandidate,
    EventCandidate,
    PassageUnit,
    SourceAnchorInput,
    VerifiedLocation,
    run_cross_unit_synthesis_pass,
    run_evidence_judge_pass,
    run_structured_extract_pass,
)
from app.exploration.projections import build_projection_bundle
from app.exploration.validators import validate_analysis_artifacts


def _unit() -> PassageUnit:
    return PassageUnit(
        id="chapter-1",
        anchors=[
            SourceAnchorInput(id="anchor-1", text="私有正文一。"),
            SourceAnchorInput(id="anchor-2", text="私有正文二。"),
        ],
        verified_locations=[
            VerifiedLocation(
                entity_id="place-reviewed",
                label="已核地点",
                longitude=116.4,
                latitude=39.9,
                coordinate_source_id="kb:data/places/reviewed.yaml",
            )
        ],
    )


def _extract_output() -> dict:
    return {
        "claims": [
            {
                "id": "claim-source",
                "statement": "材料明确陈述了一项行动。",
                "kind": "source_statement",
                "speaker": "原书叙述",
                "source_anchor_ids": ["anchor-1"],
                "review_status": "accepted",
            },
            {
                "id": "claim-author",
                "statement": "作者把该行动解释为制度压力的结果。",
                "kind": "author_judgment",
                "speaker": "本书作者",
                "source_anchor_ids": ["anchor-2"],
                "review_status": "accepted",
            },
            {
                "id": "claim-unsourced",
                "statement": "没有任何来源定位的模型补充。",
                "kind": "source_statement",
                "source_anchor_ids": [],
            },
        ],
        "temporal_refs": [
            {
                "id": "time-verbatim",
                "original_label": "同年冬",
                "source_anchor_ids": ["anchor-1"],
                "normalization_status": "verbatim",
                "precision": "relative",
            }
        ],
        "location_refs": [
            {
                "id": "location-reviewed",
                "original_label": "已核地点",
                "source_anchor_ids": ["anchor-1"],
                "resolved_entity_id": "place-reviewed",
                "geometry_status": "verified",
                # The pass must ignore model coordinates and copy reviewed KB data.
                "longitude": 0,
                "latitude": 0,
                "coordinate_source_id": "model-memory",
            },
            {
                "id": "location-guessed",
                "original_label": "同名地点",
                "source_anchor_ids": ["anchor-2"],
                "resolved_entity_id": "place-not-reviewed",
                "geometry_status": "verified",
                "longitude": 88,
                "latitude": 44,
                "coordinate_source_id": "model-memory",
            },
        ],
        "events": [
            {
                "id": "event-located",
                "title": "已核地点中的行动",
                "summary": "摘要只重组已引用的候选主张。",
                "claim_ids": ["claim-source"],
                "source_anchor_ids": ["anchor-1"],
                "temporal_ref_ids": ["time-verbatim"],
                "location_ref_ids": ["location-reviewed"],
                "review_status": "accepted",
            },
            {
                "id": "event-unlocated",
                "title": "未核地点中的行动",
                "summary": "地点保持待核，不继承上一事件坐标。",
                "claim_ids": ["claim-author"],
                "source_anchor_ids": ["anchor-2"],
                "location_ref_ids": ["location-guessed"],
                "review_status": "accepted",
            },
        ],
    }


def _accept_reviewed(artifacts: AnalysisArtifacts) -> AnalysisArtifacts:
    """Stand in for the separate human-review mutation in projection tests."""

    return artifacts.model_copy(
        update={
            "claims": [
                claim.model_copy(update={"review_status": "accepted"})
                for claim in artifacts.claims
            ],
            "events": [
                event.model_copy(update={"review_status": "accepted"})
                for event in artifacts.events
            ],
        }
    )


def test_gateway_envelopes_do_not_serialize_private_runtime_payloads():
    request = StructuredExtractRequest(
        unit_id="unit",
        source_anchor_ids=["a1"],
        source_text_by_anchor_id={"a1": "不得进入 checkpoint 的正文"},
    )
    assert "source_text_by_anchor_id" not in request.model_dump()
    assert "不得进入 checkpoint 的正文" not in request.model_dump_json()

    no_model_result = NoModelGateway().structured_extract(request)
    assert no_model_result.status == "not_called"
    assert no_model_result.output is None
    assert no_model_result.model_dump()["error_code"] == "model_not_configured"

    fake = DeterministicModelGateway(
        structured_extract_outputs={"unit": {"claims": []}}
    )
    result = fake.structured_extract(request)
    assert result.status == "succeeded"
    assert result.output == {"claims": []}
    assert "output" not in result.model_dump()


def test_external_evidence_stays_in_its_own_source_layer():
    external = ClaimCandidate(
        id="external-claim",
        statement="另一份独立材料提出了不同范围的观察。",
        kind="external_evidence",
        external_source_ids=["external-source-1"],
    )
    assert external.kind.value == "external_evidence"
    assert external.source_anchor_ids == []
    with pytest.raises(ValidationError, match="independent source ID"):
        ClaimCandidate(
            id="external-unsourced",
            statement="没有外部来源 ID 的内容不能进入外证层。",
            kind="external_evidence",
        )


def test_extraction_keeps_epistemic_layers_and_turns_unsourced_content_into_gap():
    gateway = DeterministicModelGateway(
        structured_extract_outputs={"chapter-1": _extract_output()}
    )
    artifacts = run_structured_extract_pass(gateway, _unit())

    assert [(claim.id, claim.kind.value) for claim in artifacts.claims] == [
        ("claim-source", "source_statement"),
        ("claim-author", "author_judgment"),
    ]
    assert artifacts.claims[1].speaker == "本书作者"
    assert {claim.review_status for claim in artifacts.claims} == {
        "pending_review"
    }
    assert {event.review_status for event in artifacts.events} == {
        "pending_review"
    }
    assert "claim-unsourced" not in {claim.id for claim in artifacts.claims}
    assert any(
        gap.target_id == "claim-unsourced"
        and gap.code == "claim_missing_provenance"
        for gap in artifacts.gaps
    )

    locations = {location.id: location for location in artifacts.location_refs}
    assert (
        locations["location-reviewed"].longitude,
        locations["location-reviewed"].latitude,
    ) == (116.4, 39.9)
    assert locations["location-reviewed"].coordinate_source_id.startswith("kb:")
    assert locations["location-guessed"].geometry_status == "candidate"
    assert locations["location-guessed"].longitude is None
    assert any(gap.code == "unverified_location" for gap in artifacts.gaps)


def test_reviewed_place_resolver_promotes_only_unique_exact_labels():
    resolver = ReviewedPlaceResolver(
        [
            {
                "id": "pl_changan",
                "name": "长安",
                "modern_name": "西安",
                "aliases": ["京兆府"],
                "longitude": 108.95,
                "latitude": 34.27,
            },
            {
                "id": "pl_other-a",
                "name": "同名府",
                "longitude": 110.0,
                "latitude": 35.0,
            },
            {
                "id": "pl_other-b",
                "name": "同名府",
                "longitude": 111.0,
                "latitude": 36.0,
            },
        ]
    )
    output = _extract_output()
    output["location_refs"] = [
        {
            "id": "location-changan",
            "original_label": "京兆府",
            "source_anchor_ids": ["anchor-1"],
            "resolved_entity_id": None,
            "geometry_status": "candidate",
        },
        {
            "id": "location-ambiguous",
            "original_label": "同名府",
            "source_anchor_ids": ["anchor-2"],
            "resolved_entity_id": None,
            "geometry_status": "ambiguous",
        },
    ]
    output["events"] = []
    artifacts = run_structured_extract_pass(
        DeterministicModelGateway(
            structured_extract_outputs={"chapter-1": output}
        ),
        _unit(),
        location_resolver=resolver,
    )
    locations = {item.id: item for item in artifacts.location_refs}
    assert locations["location-changan"].geometry_status == "verified"
    assert locations["location-changan"].resolved_entity_id == "pl_changan"
    assert locations["location-changan"].coordinate_source_id == (
        "history-kb-place:pl_changan"
    )
    assert locations["location-ambiguous"].geometry_status == "ambiguous"
    assert locations["location-ambiguous"].longitude is None


def test_synthesis_projection_preserves_return_to_source_chain():
    gateway = DeterministicModelGateway(
        structured_extract_outputs={"chapter-1": _extract_output()},
        cross_unit_synthesis_outputs={
            "book-thread": {
                "claims": [
                    {
                        "id": "insight-platform",
                        "statement": (
                            "平台提出：行动与作者解释共同构成一条待复核主线。"
                        ),
                        "kind": "platform_inference",
                        "derived_from_claim_ids": [
                            "claim-source",
                            "claim-author",
                        ],
                        "limitations": [
                            "目前只覆盖两个段落锚点，不能外推到全书。"
                        ],
                        "review_status": "accepted",
                    }
                ]
            }
        },
        evidence_judge_outputs={
            "judge-thread": {
                "relations": [],
                "counterevidence_not_found_claim_ids": ["insight-platform"],
            }
        },
    )
    artifacts = run_structured_extract_pass(gateway, _unit())
    artifacts = run_cross_unit_synthesis_pass(
        gateway, artifacts, synthesis_id="book-thread"
    )
    artifacts = run_evidence_judge_pass(
        gateway, artifacts, judgment_id="judge-thread"
    )

    report = validate_analysis_artifacts(
        artifacts, available_anchor_ids={"anchor-1", "anchor-2"}
    )
    assert report.is_valid, report.issues
    assert artifacts.evidence_relations == []
    assert any(
        gap.code == "counterevidence_not_found"
        and gap.target_id == "insight-platform"
        for gap in artifacts.gaps
    )

    bundle = build_projection_bundle(
        _accept_reviewed(artifacts),
        available_anchor_ids={"anchor-1", "anchor-2"},
    )
    insight = bundle.insights.items[0]
    assert insight.claim_id == "insight-platform"
    assert insight.derived_from_claim_ids == (
        "claim-source",
        "claim-author",
    )
    assert insight.limitations == (
        "目前只覆盖两个段落锚点，不能外推到全书。",
    )

    argument_by_claim = {node.claim_id: node for node in bundle.argument.nodes}
    assert argument_by_claim[insight.derived_from_claim_ids[0]].source_anchor_ids == (
        "anchor-1",
    )
    located_scene = next(
        scene for scene in bundle.scenes if scene.event_id == "event-located"
    )
    assert located_scene.claim_ids == ("claim-source",)
    assert located_scene.source_anchor_ids == ("anchor-1",)
    assert located_scene.truth_owner is False


def test_map_projection_consumes_only_verified_locations_and_never_draws_route():
    artifacts = run_structured_extract_pass(
        DeterministicModelGateway(
            structured_extract_outputs={"chapter-1": _extract_output()}
        ),
        _unit(),
    )
    artifacts = _accept_reviewed(artifacts)
    bundle = build_projection_bundle(
        artifacts,
        available_anchor_ids={"anchor-1", "anchor-2"},
    )

    assert [point.location_ref_id for point in bundle.map.points] == [
        "location-reviewed"
    ]
    assert bundle.map.unlocated_event_ids == ("event-unlocated",)
    assert all(edge.semantic == "sequence_not_route" for edge in bundle.map.sequence)
    assert next(
        scene for scene in bundle.scenes if scene.event_id == "event-unlocated"
    ).map_state == "no_location"


def test_cross_artifact_validator_rejects_dangling_event_references():
    artifacts = AnalysisArtifacts(
        claims=[
            ClaimCandidate(
                id="claim-1",
                statement="有来源的陈述",
                kind="source_statement",
                source_anchor_ids=["anchor-1"],
                review_status="accepted",
            )
        ],
        events=[
            EventCandidate(
                id="event-dangling",
                title="悬空事件",
                summary="引用了不存在的主张。",
                claim_ids=["claim-missing"],
                source_anchor_ids=["anchor-1"],
                review_status="accepted",
            )
        ],
    )
    report = validate_analysis_artifacts(
        artifacts, available_anchor_ids={"anchor-1"}
    )
    assert not report.is_valid
    assert {issue.code for issue in report.issues} == {"unknown_event_claim"}
    with pytest.raises(ValueError, match="unknown_event_claim"):
        build_projection_bundle(
            artifacts,
            available_anchor_ids={"anchor-1"},
        )
