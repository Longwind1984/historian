"""Compile a BookProfile into a bounded, deterministic analysis DAG."""

from __future__ import annotations

from hashlib import sha256
import json

from .contracts import (
    AnalysisPass,
    AnalysisPlan,
    ArtifactKind,
    AnchorBatchScope,
    BookProfile,
    BookType,
    EpistemicLayer,
    ExecutorKind,
    InputUnit,
    QualityGate,
    PlanningScope,
    SkippedPass,
    SourcePolicy,
    SourceSet,
    WorkerKind,
    WorkItemSpec,
    WorkOutputContract,
)


DEFAULT_PLAN_VERSION = "book-analysis-plan.v1"
DEFAULT_PIPELINE_VERSION = "book-analysis-pipeline.v6.0"
DEFAULT_PROMPT_BUNDLE_VERSION = "candidate-extraction.v1"


_PASS_CONTRACTS: dict[
    AnalysisPass,
    tuple[
        ExecutorKind,
        WorkerKind,
        InputUnit,
        tuple[ArtifactKind, ...],
        tuple[EpistemicLayer, ...],
    ],
] = {
    AnalysisPass.PASSAGE_ANALYSIS: (
        ExecutorKind.MODEL,
        WorkerKind.PASSAGE_ANALYST,
        InputUnit.ANCHOR_BATCH,
        (ArtifactKind.CLAIM_CANDIDATES, ArtifactKind.MENTIONS),
        (EpistemicLayer.SOURCE_STATEMENT, EpistemicLayer.AUTHOR_JUDGMENT),
    ),
    AnalysisPass.ENTITY_RESOLUTION: (
        ExecutorKind.DETERMINISTIC,
        WorkerKind.ENTITY_RESOLVER,
        InputUnit.BOOK_CANDIDATES,
        (ArtifactKind.ENTITY_RESOLUTIONS,),
        (),
    ),
    AnalysisPass.TEMPORAL_GEO_RESOLUTION: (
        ExecutorKind.DETERMINISTIC,
        WorkerKind.TEMPORAL_GEO_RESOLVER,
        InputUnit.BOOK_CANDIDATES,
        (ArtifactKind.TEMPORAL_LOCATION_CANDIDATES,),
        (),
    ),
    AnalysisPass.EVENT_EXTRACTION: (
        ExecutorKind.MODEL,
        WorkerKind.EVENT_ANALYST,
        InputUnit.ANCHOR_BATCH,
        (ArtifactKind.EVENT_CANDIDATES,),
        (EpistemicLayer.SOURCE_STATEMENT, EpistemicLayer.AUTHOR_JUDGMENT),
    ),
    AnalysisPass.EVENT_SEQUENCE: (
        ExecutorKind.DETERMINISTIC,
        WorkerKind.EVENT_ANALYST,
        InputUnit.BOOK_CANDIDATES,
        (ArtifactKind.EVENT_SEQUENCE_CANDIDATES,),
        (),
    ),
    AnalysisPass.ARGUMENT_EXTRACTION: (
        ExecutorKind.MODEL,
        WorkerKind.ARGUMENT_ANALYST,
        InputUnit.ANCHOR_BATCH,
        (ArtifactKind.ARGUMENT_CANDIDATES,),
        (EpistemicLayer.AUTHOR_JUDGMENT,),
    ),
    AnalysisPass.LIMITATION_EXTRACTION: (
        ExecutorKind.MODEL,
        WorkerKind.ARGUMENT_ANALYST,
        InputUnit.ANCHOR_BATCH,
        (ArtifactKind.LIMITATIONS,),
        (EpistemicLayer.AUTHOR_JUDGMENT,),
    ),
    AnalysisPass.PERSON_COREFERENCE: (
        ExecutorKind.MODEL,
        WorkerKind.PERSON_ANALYST,
        InputUnit.BOOK_CANDIDATES,
        (ArtifactKind.PERSON_CLUSTERS,),
        (),
    ),
    AnalysisPass.LIFE_EVENT_EXTRACTION: (
        ExecutorKind.MODEL,
        WorkerKind.PERSON_ANALYST,
        InputUnit.ANCHOR_BATCH,
        (ArtifactKind.EVENT_CANDIDATES,),
        (EpistemicLayer.SOURCE_STATEMENT, EpistemicLayer.AUTHOR_JUDGMENT),
    ),
    AnalysisPass.RELATIONSHIP_EXTRACTION: (
        ExecutorKind.MODEL,
        WorkerKind.PERSON_ANALYST,
        InputUnit.ANCHOR_BATCH,
        (ArtifactKind.RELATIONSHIP_CANDIDATES,),
        (EpistemicLayer.SOURCE_STATEMENT, EpistemicLayer.AUTHOR_JUDGMENT),
    ),
    AnalysisPass.CONCEPT_INSTITUTION_EXTRACTION: (
        ExecutorKind.MODEL,
        WorkerKind.INSTITUTION_ANALYST,
        InputUnit.ANCHOR_BATCH,
        (ArtifactKind.CONCEPT_INSTITUTION_CANDIDATES,),
        (EpistemicLayer.SOURCE_STATEMENT, EpistemicLayer.AUTHOR_JUDGMENT),
    ),
    AnalysisPass.PERIOD_COMPARISON: (
        ExecutorKind.MODEL,
        WorkerKind.INSTITUTION_ANALYST,
        InputUnit.BOOK_CANDIDATES,
        (ArtifactKind.PERIOD_COMPARISONS,),
        (EpistemicLayer.PLATFORM_INFERENCE,),
    ),
    AnalysisPass.SOURCE_BOUNDARY_DETECTION: (
        ExecutorKind.DETERMINISTIC,
        WorkerKind.SOURCE_STRUCTURE_ANALYST,
        InputUnit.DOCUMENT_STRUCTURE,
        (ArtifactKind.SOURCE_BOUNDARIES,),
        (),
    ),
    AnalysisPass.SPEAKER_ATTRIBUTION: (
        ExecutorKind.MODEL,
        WorkerKind.SOURCE_STRUCTURE_ANALYST,
        InputUnit.ANCHOR_BATCH,
        (ArtifactKind.SPEAKER_ATTRIBUTIONS,),
        (EpistemicLayer.SOURCE_STATEMENT,),
    ),
    AnalysisPass.SOURCE_DATE_ATTRIBUTION: (
        ExecutorKind.MODEL,
        WorkerKind.SOURCE_STRUCTURE_ANALYST,
        InputUnit.ANCHOR_BATCH,
        (ArtifactKind.SOURCE_DATES,),
        (EpistemicLayer.SOURCE_STATEMENT,),
    ),
    AnalysisPass.REFERENCE_STRUCTURE_INDEX: (
        ExecutorKind.DETERMINISTIC,
        WorkerKind.REFERENCE_INDEXER,
        InputUnit.DOCUMENT_STRUCTURE,
        (ArtifactKind.REFERENCE_INDEX,),
        (),
    ),
    AnalysisPass.TABLE_FIGURE_LOCATORS: (
        ExecutorKind.DETERMINISTIC,
        WorkerKind.REFERENCE_INDEXER,
        InputUnit.DOCUMENT_STRUCTURE,
        (ArtifactKind.TABLE_FIGURE_ANCHORS,),
        (),
    ),
    AnalysisPass.CHAPTER_MODE_CLASSIFICATION: (
        ExecutorKind.DETERMINISTIC,
        WorkerKind.SOURCE_STRUCTURE_ANALYST,
        InputUnit.DOCUMENT_STRUCTURE,
        (ArtifactKind.CHAPTER_MODES,),
        (),
    ),
    AnalysisPass.CHAPTER_DIGEST: (
        ExecutorKind.MODEL,
        WorkerKind.CHAPTER_SYNTHESIZER,
        InputUnit.CHAPTER_CANDIDATES,
        (ArtifactKind.CHAPTER_DIGESTS,),
        (EpistemicLayer.SOURCE_STATEMENT, EpistemicLayer.AUTHOR_JUDGMENT),
    ),
    AnalysisPass.CROSS_CHAPTER_SYNTHESIS: (
        ExecutorKind.MODEL,
        WorkerKind.THREAD_SYNTHESIZER,
        InputUnit.BOOK_CANDIDATES,
        (ArtifactKind.NARRATIVE_THREADS,),
        (EpistemicLayer.PLATFORM_INFERENCE,),
    ),
    AnalysisPass.EXTERNAL_EVIDENCE: (
        ExecutorKind.MODEL,
        WorkerKind.EXTERNAL_EVIDENCE_WORKER,
        InputUnit.BOOK_CANDIDATES,
        (ArtifactKind.EXTERNAL_EVIDENCE_CANDIDATES,),
        (EpistemicLayer.EXTERNAL_EVIDENCE,),
    ),
    AnalysisPass.CRITIC_AUDIT: (
        ExecutorKind.MODEL,
        WorkerKind.CRITIC_WORKER,
        InputUnit.BOOK_CANDIDATES,
        (ArtifactKind.QUALITY_REPORT,),
        (),
    ),
    AnalysisPass.HUMAN_REVIEW: (
        ExecutorKind.HUMAN_GATE,
        WorkerKind.HUMAN_REVIEWER,
        InputUnit.BOOK_CANDIDATES,
        (ArtifactKind.REVIEW_QUEUE,),
        (),
    ),
    AnalysisPass.BUILD_PROJECTIONS: (
        ExecutorKind.DETERMINISTIC,
        WorkerKind.PROJECTION_WORKER,
        InputUnit.REVIEWED_CANDIDATES,
        (ArtifactKind.PROJECTIONS,),
        (),
    ),
}


_TYPE_PASSES: dict[BookType, tuple[AnalysisPass, ...]] = {
    BookType.EVENT_NARRATIVE: (
        AnalysisPass.PASSAGE_ANALYSIS,
        AnalysisPass.ENTITY_RESOLUTION,
        AnalysisPass.TEMPORAL_GEO_RESOLUTION,
        AnalysisPass.EVENT_EXTRACTION,
        AnalysisPass.EVENT_SEQUENCE,
        AnalysisPass.CHAPTER_DIGEST,
        AnalysisPass.CROSS_CHAPTER_SYNTHESIS,
    ),
    BookType.ARGUMENTATIVE_MONOGRAPH: (
        AnalysisPass.PASSAGE_ANALYSIS,
        AnalysisPass.ARGUMENT_EXTRACTION,
        AnalysisPass.LIMITATION_EXTRACTION,
        AnalysisPass.ENTITY_RESOLUTION,
        AnalysisPass.CHAPTER_DIGEST,
        AnalysisPass.CROSS_CHAPTER_SYNTHESIS,
    ),
    BookType.BIOGRAPHY_MICROHISTORY: (
        AnalysisPass.PASSAGE_ANALYSIS,
        AnalysisPass.PERSON_COREFERENCE,
        AnalysisPass.ENTITY_RESOLUTION,
        AnalysisPass.TEMPORAL_GEO_RESOLUTION,
        AnalysisPass.LIFE_EVENT_EXTRACTION,
        AnalysisPass.RELATIONSHIP_EXTRACTION,
        AnalysisPass.CHAPTER_DIGEST,
        AnalysisPass.CROSS_CHAPTER_SYNTHESIS,
    ),
    BookType.INSTITUTIONAL_THEMATIC: (
        AnalysisPass.PASSAGE_ANALYSIS,
        AnalysisPass.CONCEPT_INSTITUTION_EXTRACTION,
        AnalysisPass.PERIOD_COMPARISON,
        AnalysisPass.ENTITY_RESOLUTION,
        AnalysisPass.CHAPTER_DIGEST,
        AnalysisPass.CROSS_CHAPTER_SYNTHESIS,
    ),
    BookType.SOURCE_COLLECTION: (
        AnalysisPass.SOURCE_BOUNDARY_DETECTION,
        AnalysisPass.SPEAKER_ATTRIBUTION,
        AnalysisPass.SOURCE_DATE_ATTRIBUTION,
        AnalysisPass.PASSAGE_ANALYSIS,
        AnalysisPass.ENTITY_RESOLUTION,
        AnalysisPass.CHAPTER_DIGEST,
    ),
    BookType.REFERENCE_ATLAS: (
        AnalysisPass.REFERENCE_STRUCTURE_INDEX,
        AnalysisPass.TABLE_FIGURE_LOCATORS,
        AnalysisPass.ENTITY_RESOLUTION,
        AnalysisPass.TEMPORAL_GEO_RESOLUTION,
    ),
    BookType.MIXED: (
        AnalysisPass.CHAPTER_MODE_CLASSIFICATION,
        AnalysisPass.PASSAGE_ANALYSIS,
        AnalysisPass.ENTITY_RESOLUTION,
        AnalysisPass.TEMPORAL_GEO_RESOLUTION,
        AnalysisPass.EVENT_EXTRACTION,
        AnalysisPass.ARGUMENT_EXTRACTION,
        AnalysisPass.LIMITATION_EXTRACTION,
        AnalysisPass.CONCEPT_INSTITUTION_EXTRACTION,
        AnalysisPass.CHAPTER_DIGEST,
        AnalysisPass.CROSS_CHAPTER_SYNTHESIS,
    ),
}


def stable_work_item_id(
    *,
    source_checksum: str,
    plan_version: str,
    pass_type: AnalysisPass,
    scope_key: str = "book",
) -> str:
    """Return a stable, content-addressed work ID without source text."""

    payload = json.dumps(
        {
            "source_checksum": source_checksum,
            "plan_version": plan_version,
            "pass_type": pass_type.value,
            "scope_key": scope_key,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"wi_{sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _source_policy_fingerprint(source_policy: SourcePolicy) -> str:
    payload = json.dumps(
        source_policy.model_dump(mode="json"),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:12]


def _planning_scope_fingerprint(planning_scope: PlanningScope) -> str:
    payload = json.dumps(
        planning_scope.model_dump(mode="json"),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:12]


def _stable_plan_id(
    source_checksum: str,
    plan_version: str,
    primary_type: BookType,
    source_policy: SourcePolicy,
    planning_scope: PlanningScope,
) -> str:
    payload = (
        f"{source_checksum}:{plan_version}:{primary_type.value}:"
        f"{_source_policy_fingerprint(source_policy)}:"
        f"{_planning_scope_fingerprint(planning_scope)}"
    )
    return f"plan_{sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _work_scopes(
    input_unit: InputUnit,
    planning_scope: PlanningScope,
) -> tuple[str, ...]:
    if input_unit == InputUnit.ANCHOR_BATCH and planning_scope.anchor_batches:
        return tuple(f"batch:{batch.id}" for batch in planning_scope.anchor_batches)
    if input_unit == InputUnit.CHAPTER_CANDIDATES and planning_scope.chapter_ids:
        return tuple(f"chapter:{chapter_id}" for chapter_id in planning_scope.chapter_ids)
    return ("book",)


def _terminal_ids(items: list[WorkItemSpec]) -> tuple[str, ...]:
    consumed = {dependency for item in items for dependency in item.depends_on}
    return tuple(item.id for item in items if item.id not in consumed)


def _dependency_ids(
    *,
    pass_type: AnalysisPass,
    unit_scope: str,
    created: list[WorkItemSpec],
    created_by_pass: dict[AnalysisPass, list[WorkItemSpec]],
    planning_scope: PlanningScope,
) -> tuple[str, ...]:
    def ids(candidate: AnalysisPass) -> tuple[str, ...]:
        return tuple(item.id for item in created_by_pass.get(candidate, ()))

    def same_scope(candidate: AnalysisPass) -> tuple[str, ...]:
        matches = tuple(
            item.id
            for item in created_by_pass.get(candidate, ())
            if item.scope_key.endswith(f":{unit_scope}")
        )
        return matches or ids(candidate)

    if not created:
        return ()
    if pass_type == AnalysisPass.PASSAGE_ANALYSIS:
        return ids(AnalysisPass.SOURCE_BOUNDARY_DETECTION) + ids(
            AnalysisPass.CHAPTER_MODE_CLASSIFICATION
        )
    if pass_type in {
        AnalysisPass.EVENT_EXTRACTION,
        AnalysisPass.ARGUMENT_EXTRACTION,
        AnalysisPass.LIMITATION_EXTRACTION,
        AnalysisPass.LIFE_EVENT_EXTRACTION,
        AnalysisPass.RELATIONSHIP_EXTRACTION,
        AnalysisPass.CONCEPT_INSTITUTION_EXTRACTION,
    }:
        return same_scope(AnalysisPass.PASSAGE_ANALYSIS)
    if pass_type in {
        AnalysisPass.ENTITY_RESOLUTION,
        AnalysisPass.TEMPORAL_GEO_RESOLUTION,
        AnalysisPass.PERSON_COREFERENCE,
    }:
        return ids(AnalysisPass.PASSAGE_ANALYSIS) or ids(
            AnalysisPass.REFERENCE_STRUCTURE_INDEX
        )
    if pass_type in {
        AnalysisPass.SPEAKER_ATTRIBUTION,
        AnalysisPass.SOURCE_DATE_ATTRIBUTION,
    }:
        return ids(AnalysisPass.SOURCE_BOUNDARY_DETECTION)
    if pass_type == AnalysisPass.TABLE_FIGURE_LOCATORS:
        return ids(AnalysisPass.REFERENCE_STRUCTURE_INDEX)
    if pass_type == AnalysisPass.EVENT_SEQUENCE:
        return ids(AnalysisPass.EVENT_EXTRACTION) + ids(
            AnalysisPass.TEMPORAL_GEO_RESOLUTION
        )
    if pass_type == AnalysisPass.PERIOD_COMPARISON:
        return ids(AnalysisPass.CONCEPT_INSTITUTION_EXTRACTION)
    if pass_type == AnalysisPass.CHAPTER_DIGEST:
        chapter_id = unit_scope.removeprefix("chapter:")
        batch_scope_suffixes = {
            f":batch:{batch.id}"
            for batch in planning_scope.anchor_batches
            if batch.chapter_id == chapter_id
        }
        local_items = tuple(
            item.id
            for item in created
            if any(item.scope_key.endswith(suffix) for suffix in batch_scope_suffixes)
        )
        book_items = tuple(
            item.id for item in created if item.scope_key.endswith(":book")
        )
        return tuple(dict.fromkeys(local_items + book_items)) or _terminal_ids(created)
    if pass_type == AnalysisPass.CROSS_CHAPTER_SYNTHESIS:
        return ids(AnalysisPass.CHAPTER_DIGEST)
    if pass_type in {
        AnalysisPass.EXTERNAL_EVIDENCE,
        AnalysisPass.CRITIC_AUDIT,
        AnalysisPass.HUMAN_REVIEW,
        AnalysisPass.BUILD_PROJECTIONS,
    }:
        return _terminal_ids(created)
    return _terminal_ids(created)


def _source_sets_for_pass(
    pass_type: AnalysisPass,
    policy: SourcePolicy,
) -> tuple[SourceSet, ...]:
    """Grant each pass the smallest source set that preserves layer boundaries."""

    allowed = set(policy.allowed_source_sets)
    if pass_type == AnalysisPass.EXTERNAL_EVIDENCE:
        return tuple(
            source_set
            for source_set in (SourceSet.USER_MATERIAL, SourceSet.PUBLIC_EXTERNAL)
            if source_set in allowed
        )
    if pass_type in {
        AnalysisPass.ENTITY_RESOLUTION,
        AnalysisPass.TEMPORAL_GEO_RESOLUTION,
    }:
        return tuple(
            source_set
            for source_set in (SourceSet.ORIGINAL_BOOK, SourceSet.REVIEWED_KB)
            if source_set in allowed
        )
    if pass_type in {AnalysisPass.HUMAN_REVIEW, AnalysisPass.BUILD_PROJECTIONS}:
        return policy.allowed_source_sets
    return (
        (SourceSet.ORIGINAL_BOOK,)
        if SourceSet.ORIGINAL_BOOK in allowed
        else policy.allowed_source_sets
    )


def compile_analysis_plan(
    profile: BookProfile,
    *,
    source_policy: SourcePolicy | None = None,
    plan_version: str = DEFAULT_PLAN_VERSION,
    pipeline_version: str = DEFAULT_PIPELINE_VERSION,
    prompt_bundle_version: str = DEFAULT_PROMPT_BUNDLE_VERSION,
    max_concurrency: int = 4,
    planning_scope: PlanningScope | None = None,
) -> AnalysisPlan:
    """Compile an inspectable DAG; no worker or model is invoked here."""

    policy = source_policy or SourcePolicy()
    scope = planning_scope or PlanningScope()
    if SourceSet.ORIGINAL_BOOK not in policy.allowed_source_sets:
        raise ValueError("book analysis requires the original_book source set")
    route_scope_key = (
        f"book:{profile.primary_type.value}:"
        f"{_source_policy_fingerprint(policy)}:"
        f"{_planning_scope_fingerprint(scope)}"
    )
    selected_list = list(_TYPE_PASSES[profile.primary_type])
    if policy.enable_external_evidence:
        selected_list.append(AnalysisPass.EXTERNAL_EVIDENCE)
    selected_list.extend(
        [
            AnalysisPass.CRITIC_AUDIT,
            AnalysisPass.HUMAN_REVIEW,
            AnalysisPass.BUILD_PROJECTIONS,
        ]
    )
    selected = tuple(selected_list)

    work_items: list[WorkItemSpec] = []
    work_items_by_pass: dict[AnalysisPass, list[WorkItemSpec]] = {}
    for pass_type in selected:
        executor, worker, input_unit, artifact_kinds, epistemic_layers = _PASS_CONTRACTS[
            pass_type
        ]
        source_sets = _source_sets_for_pass(pass_type, policy)
        for unit_scope in _work_scopes(input_unit, scope):
            item_scope_key = f"{route_scope_key}:{unit_scope}"
            item = WorkItemSpec(
                id=stable_work_item_id(
                    source_checksum=profile.source_checksum,
                    plan_version=plan_version,
                    pass_type=pass_type,
                    scope_key=item_scope_key,
                ),
                pass_type=pass_type,
                executor=executor,
                worker=worker,
                input_unit=input_unit,
                scope_key=item_scope_key,
                depends_on=_dependency_ids(
                    pass_type=pass_type,
                    unit_scope=unit_scope,
                    created=work_items,
                    created_by_pass=work_items_by_pass,
                    planning_scope=scope,
                ),
                allowed_source_sets=source_sets,
                output=WorkOutputContract(
                    artifact_kinds=artifact_kinds,
                    epistemic_layers=epistemic_layers,
                ),
            )
            work_items.append(item)
            work_items_by_pass.setdefault(pass_type, []).append(item)

    selected_set = set(selected)
    skipped = []
    for pass_type in AnalysisPass:
        if pass_type in selected_set:
            continue
        reason = (
            "external_sources_disabled"
            if pass_type == AnalysisPass.EXTERNAL_EVIDENCE
            else "book_type_not_selected"
        )
        skipped.append(SkippedPass(pass_type=pass_type, reason_code=reason))

    return AnalysisPlan(
        id=_stable_plan_id(
            profile.source_checksum,
            plan_version,
            profile.primary_type,
            policy,
            scope,
        ),
        source_checksum=profile.source_checksum,
        plan_version=plan_version,
        pipeline_version=pipeline_version,
        prompt_bundle_version=prompt_bundle_version,
        profile_revision=profile.profile_revision,
        primary_type=profile.primary_type,
        source_policy=policy,
        planning_scope=scope,
        work_items=tuple(work_items),
        skipped_passes=tuple(skipped),
        quality_gates=tuple(
            QualityGate(code=code)
            for code in (
                "all_references_resolve",
                "all_claims_have_provenance",
                "epistemic_layers_preserved",
                "human_review_required",
                "projection_uses_reviewed_candidates",
            )
        ),
        max_concurrency=max_concurrency,
        estimated_work_item_count=len(work_items),
    )
