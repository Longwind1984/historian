"""v6 book profiling and deterministic planning contracts."""

from __future__ import annotations

from hashlib import sha256

import pytest

from app.exploration.contracts import (
    AnalysisPass,
    AnchorBatchScope,
    BookMetadataSignals,
    BookStructureSignals,
    BookType,
    EpistemicLayer,
    PlanningScope,
    SectionSignals,
    SourcePolicy,
    SourceSet,
)
from app.exploration.planning import compile_analysis_plan
from app.exploration.profiling import build_book_profile, select_stratified_samples


CHECKSUM = sha256(b"stable-private-book-fixture").hexdigest()


def _sections(kind: BookType, count: int = 9) -> list[SectionSignals]:
    values = {
        BookType.EVENT_NARRATIVE: dict(
            chronology_density=0.90,
            geography_density=0.82,
            actor_density=0.72,
            action_sequence_density=0.93,
            argument_density=0.18,
        ),
        BookType.ARGUMENTATIVE_MONOGRAPH: dict(
            chronology_density=0.22,
            geography_density=0.10,
            actor_density=0.25,
            action_sequence_density=0.12,
            argument_density=0.94,
            concept_density=0.86,
            citation_density=0.75,
        ),
        BookType.BIOGRAPHY_MICROHISTORY: dict(
            chronology_density=0.78,
            geography_density=0.56,
            actor_density=0.91,
            action_sequence_density=0.73,
            argument_density=0.25,
        ),
    }[kind]
    return [
        SectionSignals(
            section_id=f"section-{index}",
            section_index=index,
            anchor_ids=(f"anchor-{index}",),
            **values,
        )
        for index in range(count)
    ]


def _profile(kind: BookType):
    structure_kwargs = {
        BookType.EVENT_NARRATIVE: {},
        BookType.ARGUMENTATIVE_MONOGRAPH: {"footnote_density": 0.8},
        BookType.BIOGRAPHY_MICROHISTORY: {"named_subject_continuity": 0.96},
    }[kind]
    return build_book_profile(
        source_checksum=CHECKSUM,
        metadata=BookMetadataSignals(catalog_type_hints=(kind,)),
        structure=BookStructureSignals(
            section_count=9,
            paragraph_count=90,
            heading_depth=3,
            **structure_kwargs,
        ),
        section_signals=_sections(kind),
    )


def test_stratified_samples_cover_book_instead_of_only_the_opening():
    sections = _sections(BookType.EVENT_NARRATIVE, count=12)
    samples = select_stratified_samples(sections, max_samples=5)

    assert [sample.section_index for sample in samples] == [0, 3, 6, 8, 11]
    assert {sample.stratum.value for sample in samples} == {
        "opening",
        "middle",
        "closing",
    }
    assert all(not hasattr(sample, "text") for sample in samples)


@pytest.mark.parametrize(
    "expected_type",
    [
        BookType.EVENT_NARRATIVE,
        BookType.ARGUMENTATIVE_MONOGRAPH,
        BookType.BIOGRAPHY_MICROHISTORY,
    ],
)
def test_deterministic_profile_routes_three_distinct_book_types(expected_type):
    first = _profile(expected_type)
    second = _profile(expected_type)

    assert first == second
    assert first.primary_type == expected_type
    assert first.profiler_mode == "deterministic_signals_only"
    assert first.historical_claims_emitted is False
    assert len(first.type_scores) == 7
    assert first.discourse_modes
    assert first.source_natures


def test_three_book_types_compile_distinct_acyclic_dags():
    plans = {
        book_type: compile_analysis_plan(_profile(book_type))
        for book_type in (
            BookType.EVENT_NARRATIVE,
            BookType.ARGUMENTATIVE_MONOGRAPH,
            BookType.BIOGRAPHY_MICROHISTORY,
        )
    }
    pass_sets = {
        book_type: {item.pass_type for item in plan.work_items}
        for book_type, plan in plans.items()
    }

    assert AnalysisPass.EVENT_SEQUENCE in pass_sets[BookType.EVENT_NARRATIVE]
    assert AnalysisPass.ARGUMENT_EXTRACTION in pass_sets[
        BookType.ARGUMENTATIVE_MONOGRAPH
    ]
    assert AnalysisPass.PERSON_COREFERENCE in pass_sets[
        BookType.BIOGRAPHY_MICROHISTORY
    ]
    assert len({tuple(sorted(item.value for item in passes)) for passes in pass_sets.values()}) == 3
    assert all(plan.work_items[-1].pass_type == AnalysisPass.BUILD_PROJECTIONS for plan in plans.values())


def test_work_item_ids_are_stable_for_same_checksum_and_plan_version():
    profile = _profile(BookType.EVENT_NARRATIVE)
    first = compile_analysis_plan(profile, plan_version="planner.v7")
    second = compile_analysis_plan(profile, plan_version="planner.v7")
    changed = compile_analysis_plan(profile, plan_version="planner.v8")
    changed_policy = compile_analysis_plan(
        profile,
        plan_version="planner.v7",
        source_policy=SourcePolicy(
            allowed_source_sets=(
                SourceSet.ORIGINAL_BOOK,
                SourceSet.USER_MATERIAL,
            ),
            enable_external_evidence=True,
        ),
    )

    assert [item.id for item in first.work_items] == [
        item.id for item in second.work_items
    ]
    assert first.id == second.id
    assert [item.id for item in first.work_items] != [
        item.id for item in changed.work_items
    ]
    assert first.id != changed_policy.id


def test_plan_fans_out_anchor_batches_and_chapters_then_joins_at_book_level():
    scope = PlanningScope(
        chapter_ids=("chapter-1", "chapter-2"),
        anchor_batches=(
            AnchorBatchScope(
                id="batch-1a",
                chapter_id="chapter-1",
                anchor_ids=("anchor-1", "anchor-2"),
            ),
            AnchorBatchScope(
                id="batch-1b",
                chapter_id="chapter-1",
                anchor_ids=("anchor-3",),
            ),
            AnchorBatchScope(
                id="batch-2a",
                chapter_id="chapter-2",
                anchor_ids=("anchor-4",),
            ),
        ),
    )
    plan = compile_analysis_plan(
        _profile(BookType.EVENT_NARRATIVE),
        planning_scope=scope,
    )

    passage_items = [
        item for item in plan.work_items if item.pass_type == AnalysisPass.PASSAGE_ANALYSIS
    ]
    event_items = [
        item for item in plan.work_items if item.pass_type == AnalysisPass.EVENT_EXTRACTION
    ]
    digest_items = [
        item for item in plan.work_items if item.pass_type == AnalysisPass.CHAPTER_DIGEST
    ]
    synthesis = next(
        item
        for item in plan.work_items
        if item.pass_type == AnalysisPass.CROSS_CHAPTER_SYNTHESIS
    )

    assert len(passage_items) == 3
    assert len(event_items) == 3
    assert len(digest_items) == 2
    assert all(len(item.depends_on) == 1 for item in event_items)
    assert set(synthesis.depends_on) == {item.id for item in digest_items}
    assert plan.estimated_work_item_count == len(plan.work_items)

    repeated = compile_analysis_plan(
        _profile(BookType.EVENT_NARRATIVE),
        planning_scope=scope,
    )
    assert [item.id for item in repeated.work_items] == [
        item.id for item in plan.work_items
    ]


def test_plan_never_allows_models_to_publish_historical_facts_and_keeps_layers_separate():
    plan = compile_analysis_plan(_profile(BookType.ARGUMENTATIVE_MONOGRAPH))

    assert plan.models_may_publish_reviewed_historical_facts is False
    assert all(item.output.candidate_only for item in plan.work_items)
    assert all(
        item.output.may_publish_reviewed_historical_facts is False
        for item in plan.work_items
    )
    synthesis = next(
        item
        for item in plan.work_items
        if item.pass_type == AnalysisPass.CROSS_CHAPTER_SYNTHESIS
    )
    assert synthesis.output.epistemic_layers == (
        EpistemicLayer.PLATFORM_INFERENCE,
    )

    with_external = compile_analysis_plan(
        _profile(BookType.ARGUMENTATIVE_MONOGRAPH),
        source_policy=SourcePolicy(
            allowed_source_sets=(
                SourceSet.ORIGINAL_BOOK,
                SourceSet.REVIEWED_KB,
                SourceSet.PUBLIC_EXTERNAL,
            ),
            enable_external_evidence=True,
            allow_external_network=True,
        ),
    )
    external = next(
        item
        for item in with_external.work_items
        if item.pass_type == AnalysisPass.EXTERNAL_EVIDENCE
    )
    assert external.output.epistemic_layers == (
        EpistemicLayer.EXTERNAL_EVIDENCE,
    )
    assert SourceSet.PUBLIC_EXTERNAL in external.allowed_source_sets
    source_analysis = next(
        item
        for item in with_external.work_items
        if item.pass_type == AnalysisPass.PASSAGE_ANALYSIS
    )
    assert source_analysis.allowed_source_sets == (SourceSet.ORIGINAL_BOOK,)
