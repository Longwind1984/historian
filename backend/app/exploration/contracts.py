"""Typed v6 contracts for profiling and deterministic workflow planning.

The contracts deliberately contain no source text and no model-authored
historical facts. Workers may only propose typed candidates, each carrying an
epistemic layer. Human review and the existing reviewed YAML/GeoJSON knowledge
base remain separate promotion boundaries.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


UnitInterval = Annotated[float, Field(ge=0.0, le=1.0)]
Sha256Checksum = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[a-f0-9]{64}$"),
]
StableIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]


class ContractModel(BaseModel):
    """Reject silent contract drift and keep planning values immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class BookType(str, Enum):
    EVENT_NARRATIVE = "event_narrative"
    ARGUMENTATIVE_MONOGRAPH = "argumentative_monograph"
    BIOGRAPHY_MICROHISTORY = "biography_microhistory"
    INSTITUTIONAL_THEMATIC = "institutional_thematic"
    SOURCE_COLLECTION = "source_collection"
    REFERENCE_ATLAS = "reference_atlas"
    MIXED = "mixed"


class SampleStratum(str, Enum):
    OPENING = "opening"
    MIDDLE = "middle"
    CLOSING = "closing"


class RightsAndPrivacy(str, Enum):
    LOCAL_PRIVATE = "local_private"
    PUBLIC_DOMAIN = "public_domain"
    PUBLIC_LICENSED = "public_licensed"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class DiscourseMode(str, Enum):
    NARRATIVE = "narrative"
    ANALYTIC = "analytic"
    DOCUMENTARY = "documentary"
    REFERENCE = "reference"
    MIXED = "mixed"


class SourceNature(str, Enum):
    SECONDARY_SYNTHESIS = "secondary_synthesis"
    PRIMARY_SOURCE = "primary_source"
    EDITED_COLLECTION = "edited_collection"
    REFERENCE_WORK = "reference_work"
    MIXED = "mixed"


class LanguageRegister(str, Enum):
    MODERN_VERNACULAR = "modern_vernacular"
    CLASSICAL_CHINESE = "classical_chinese"
    TRANSLATED = "translated"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ProfileTrait(str, Enum):
    CHRONOLOGY_DENSE = "chronology_dense"
    GEOGRAPHY_DENSE = "geography_dense"
    ACTOR_NETWORK_DENSE = "actor_network_dense"
    ARGUMENT_DENSE = "argument_dense"
    CITATION_DENSE = "citation_dense"
    HIGHLY_STRUCTURED = "highly_structured"
    HETEROGENEOUS_SECTIONS = "heterogeneous_sections"


class EpistemicLayer(str, Enum):
    """Mutually visible layers that must never be flattened into one fact list."""

    SOURCE_STATEMENT = "source_statement"
    AUTHOR_JUDGMENT = "author_judgment"
    PLATFORM_INFERENCE = "platform_inference"
    EXTERNAL_EVIDENCE = "external_evidence"


class SourceSet(str, Enum):
    ORIGINAL_BOOK = "original_book"
    REVIEWED_KB = "reviewed_kb"
    USER_MATERIAL = "user_material"
    PUBLIC_EXTERNAL = "public_external"


class ExecutorKind(str, Enum):
    DETERMINISTIC = "deterministic"
    MODEL = "model"
    HUMAN_GATE = "human_gate"


class WorkerKind(str, Enum):
    PASSAGE_ANALYST = "passage_analyst"
    ENTITY_RESOLVER = "entity_resolver"
    TEMPORAL_GEO_RESOLVER = "temporal_geo_resolver"
    EVENT_ANALYST = "event_analyst"
    ARGUMENT_ANALYST = "argument_analyst"
    PERSON_ANALYST = "person_analyst"
    INSTITUTION_ANALYST = "institution_analyst"
    SOURCE_STRUCTURE_ANALYST = "source_structure_analyst"
    REFERENCE_INDEXER = "reference_indexer"
    CHAPTER_SYNTHESIZER = "chapter_synthesizer"
    THREAD_SYNTHESIZER = "thread_synthesizer"
    EXTERNAL_EVIDENCE_WORKER = "external_evidence_worker"
    CRITIC_WORKER = "critic_worker"
    HUMAN_REVIEWER = "human_reviewer"
    PROJECTION_WORKER = "projection_worker"


class AnalysisPass(str, Enum):
    PASSAGE_ANALYSIS = "passage_analysis"
    ENTITY_RESOLUTION = "entity_resolution"
    TEMPORAL_GEO_RESOLUTION = "temporal_geo_resolution"
    EVENT_EXTRACTION = "event_extraction"
    EVENT_SEQUENCE = "event_sequence"
    ARGUMENT_EXTRACTION = "argument_extraction"
    LIMITATION_EXTRACTION = "limitation_extraction"
    PERSON_COREFERENCE = "person_coreference"
    LIFE_EVENT_EXTRACTION = "life_event_extraction"
    RELATIONSHIP_EXTRACTION = "relationship_extraction"
    CONCEPT_INSTITUTION_EXTRACTION = "concept_institution_extraction"
    PERIOD_COMPARISON = "period_comparison"
    SOURCE_BOUNDARY_DETECTION = "source_boundary_detection"
    SPEAKER_ATTRIBUTION = "speaker_attribution"
    SOURCE_DATE_ATTRIBUTION = "source_date_attribution"
    REFERENCE_STRUCTURE_INDEX = "reference_structure_index"
    TABLE_FIGURE_LOCATORS = "table_figure_locators"
    CHAPTER_MODE_CLASSIFICATION = "chapter_mode_classification"
    CHAPTER_DIGEST = "chapter_digest"
    CROSS_CHAPTER_SYNTHESIS = "cross_chapter_synthesis"
    EXTERNAL_EVIDENCE = "external_evidence"
    CRITIC_AUDIT = "critic_audit"
    HUMAN_REVIEW = "human_review"
    BUILD_PROJECTIONS = "build_projections"


class ArtifactKind(str, Enum):
    CLAIM_CANDIDATES = "claim_candidates"
    MENTIONS = "mentions"
    ENTITY_RESOLUTIONS = "entity_resolutions"
    TEMPORAL_LOCATION_CANDIDATES = "temporal_location_candidates"
    EVENT_CANDIDATES = "event_candidates"
    EVENT_SEQUENCE_CANDIDATES = "event_sequence_candidates"
    ARGUMENT_CANDIDATES = "argument_candidates"
    LIMITATIONS = "limitations"
    PERSON_CLUSTERS = "person_clusters"
    RELATIONSHIP_CANDIDATES = "relationship_candidates"
    CONCEPT_INSTITUTION_CANDIDATES = "concept_institution_candidates"
    PERIOD_COMPARISONS = "period_comparisons"
    SOURCE_BOUNDARIES = "source_boundaries"
    SPEAKER_ATTRIBUTIONS = "speaker_attributions"
    SOURCE_DATES = "source_dates"
    REFERENCE_INDEX = "reference_index"
    TABLE_FIGURE_ANCHORS = "table_figure_anchors"
    CHAPTER_MODES = "chapter_modes"
    CHAPTER_DIGESTS = "chapter_digests"
    NARRATIVE_THREADS = "narrative_threads"
    EXTERNAL_EVIDENCE_CANDIDATES = "external_evidence_candidates"
    QUALITY_REPORT = "quality_report"
    REVIEW_QUEUE = "review_queue"
    PROJECTIONS = "projections"


class InputUnit(str, Enum):
    ANCHOR_BATCH = "anchor_batch"
    DOCUMENT_STRUCTURE = "document_structure"
    CHAPTER_CANDIDATES = "chapter_candidates"
    BOOK_CANDIDATES = "book_candidates"
    REVIEWED_CANDIDATES = "reviewed_candidates"


class BookMetadataSignals(ContractModel):
    """Deterministic metadata signals; values are not historical assertions."""

    language: str = Field(default="und", min_length=2, max_length=20)
    creator_count: int = Field(default=0, ge=0)
    editor_or_compiler_present: bool = False
    catalog_type_hints: tuple[BookType, ...] = ()
    source_nature_hints: tuple[SourceNature, ...] = ()
    language_register: LanguageRegister = LanguageRegister.UNKNOWN
    rights_and_privacy: RightsAndPrivacy = RightsAndPrivacy.UNKNOWN


class BookStructureSignals(ContractModel):
    section_count: int = Field(ge=1)
    paragraph_count: int = Field(ge=1)
    heading_depth: int = Field(default=1, ge=0, le=12)
    average_paragraph_chars: float = Field(default=0.0, ge=0.0)
    footnote_density: UnitInterval = 0.0
    table_figure_density: UnitInterval = 0.0
    entry_structure_density: UnitInterval = 0.0
    section_mode_variance: UnitInterval = 0.0
    named_subject_continuity: UnitInterval = 0.0
    cross_period_comparison_density: UnitInterval = 0.0
    source_boundary_density: UnitInterval = 0.0


class SectionSignals(ContractModel):
    """Content-shape signals computed locally; source text never enters the profile."""

    section_id: StableIdentifier
    section_index: int = Field(ge=0)
    anchor_ids: tuple[StableIdentifier, ...] = Field(min_length=1)
    chronology_density: UnitInterval = 0.0
    geography_density: UnitInterval = 0.0
    actor_density: UnitInterval = 0.0
    action_sequence_density: UnitInterval = 0.0
    argument_density: UnitInterval = 0.0
    concept_density: UnitInterval = 0.0
    citation_density: UnitInterval = 0.0
    speaker_change_density: UnitInterval = 0.0


class StratifiedSample(ContractModel):
    section_id: StableIdentifier
    section_index: int = Field(ge=0)
    stratum: SampleStratum
    anchor_ids: tuple[StableIdentifier, ...] = Field(min_length=1)
    chronology_density: UnitInterval = 0.0
    geography_density: UnitInterval = 0.0
    actor_density: UnitInterval = 0.0
    action_sequence_density: UnitInterval = 0.0
    argument_density: UnitInterval = 0.0
    concept_density: UnitInterval = 0.0
    citation_density: UnitInterval = 0.0
    speaker_change_density: UnitInterval = 0.0


class ProfileDimensions(ContractModel):
    chronology_density: UnitInterval
    geography_density: UnitInterval
    actor_network_density: UnitInterval
    action_sequence_density: UnitInterval
    argument_density: UnitInterval
    concept_density: UnitInterval
    citation_density: UnitInterval
    speaker_change_density: UnitInterval
    structure_quality: UnitInterval
    locator_quality: UnitInterval


class BookTypeScore(ContractModel):
    book_type: BookType
    score: UnitInterval


class ProfileUncertainty(ContractModel):
    code: Literal[
        "close_type_scores",
        "insufficient_sections",
        "weak_locator_quality",
        "high_section_variance",
    ]
    affects_routing: bool


class BookProfile(ContractModel):
    contract_version: Literal["book_profile.v1"] = "book_profile.v1"
    source_checksum: Sha256Checksum
    profile_revision: int = Field(default=1, ge=1)
    primary_type: BookType
    secondary_types: tuple[BookType, ...] = ()
    secondary_traits: tuple[ProfileTrait, ...] = ()
    discourse_modes: tuple[DiscourseMode, ...] = Field(min_length=1)
    source_natures: tuple[SourceNature, ...] = Field(min_length=1)
    classification_confidence: UnitInterval
    dimensions: ProfileDimensions
    type_scores: tuple[BookTypeScore, ...] = Field(min_length=7, max_length=7)
    samples: tuple[StratifiedSample, ...] = Field(min_length=1)
    metadata: BookMetadataSignals
    structure: BookStructureSignals
    uncertainties: tuple[ProfileUncertainty, ...] = ()
    profiler_mode: Literal["deterministic_signals_only"] = (
        "deterministic_signals_only"
    )
    historical_claims_emitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_profile(self) -> "BookProfile":
        score_types = [item.book_type for item in self.type_scores]
        if len(set(score_types)) != len(BookType) or set(score_types) != set(BookType):
            raise ValueError("type_scores must contain each book type exactly once")
        if self.primary_type in self.secondary_types:
            raise ValueError("primary_type cannot also be a secondary type")
        if len(set(self.secondary_types)) != len(self.secondary_types):
            raise ValueError("secondary_types must be unique")
        if len(set(self.secondary_traits)) != len(self.secondary_traits):
            raise ValueError("secondary_traits must be unique")
        if len(set(self.discourse_modes)) != len(self.discourse_modes):
            raise ValueError("discourse_modes must be unique")
        if len(set(self.source_natures)) != len(self.source_natures):
            raise ValueError("source_natures must be unique")
        return self


class SourcePolicy(ContractModel):
    allowed_source_sets: tuple[SourceSet, ...] = (
        SourceSet.ORIGINAL_BOOK,
        SourceSet.REVIEWED_KB,
    )
    enable_external_evidence: bool = False
    allow_external_network: bool = False
    allow_model_source_text: bool = False

    @model_validator(mode="after")
    def validate_external_boundary(self) -> "SourcePolicy":
        if len(set(self.allowed_source_sets)) != len(self.allowed_source_sets):
            raise ValueError("allowed_source_sets must be unique")
        has_external = SourceSet.PUBLIC_EXTERNAL in self.allowed_source_sets
        has_supplied_external = SourceSet.USER_MATERIAL in self.allowed_source_sets
        if self.allow_external_network and not has_external:
            raise ValueError(
                "network access requires the public_external source set"
            )
        if self.enable_external_evidence and not (has_external or has_supplied_external):
            raise ValueError(
                "external evidence requires public_external or user_material sources"
            )
        return self


class AnchorBatchScope(ContractModel):
    id: StableIdentifier
    chapter_id: StableIdentifier
    anchor_ids: tuple[StableIdentifier, ...] = Field(min_length=1)


class PlanningScope(ContractModel):
    """Stable parser output used to fan work out without carrying source text."""

    chapter_ids: tuple[StableIdentifier, ...] = ()
    anchor_batches: tuple[AnchorBatchScope, ...] = ()

    @model_validator(mode="after")
    def validate_scope(self) -> "PlanningScope":
        if len(set(self.chapter_ids)) != len(self.chapter_ids):
            raise ValueError("chapter_ids must be unique")
        batch_ids = [batch.id for batch in self.anchor_batches]
        if len(set(batch_ids)) != len(batch_ids):
            raise ValueError("anchor batch ids must be unique")
        if self.anchor_batches and not self.chapter_ids:
            raise ValueError("anchor batches require chapter ids")
        unknown_chapters = {
            batch.chapter_id for batch in self.anchor_batches
        } - set(self.chapter_ids)
        if unknown_chapters:
            raise ValueError("anchor batches reference unknown chapters")
        if self.chapter_ids:
            covered_chapters = {batch.chapter_id for batch in self.anchor_batches}
            if covered_chapters != set(self.chapter_ids):
                raise ValueError("every chapter must have at least one anchor batch")
        return self


class WorkOutputContract(ContractModel):
    artifact_kinds: tuple[ArtifactKind, ...] = Field(min_length=1)
    epistemic_layers: tuple[EpistemicLayer, ...] = ()
    candidate_only: Literal[True] = True
    may_publish_reviewed_historical_facts: Literal[False] = False


class WorkItemSpec(ContractModel):
    id: Annotated[str, StringConstraints(pattern=r"^wi_[a-f0-9]{20}$")]
    pass_type: AnalysisPass
    executor: ExecutorKind
    worker: WorkerKind
    input_unit: InputUnit
    scope_key: StableIdentifier
    depends_on: tuple[Annotated[str, StringConstraints(pattern=r"^wi_[a-f0-9]{20}$")], ...] = ()
    allowed_source_sets: tuple[SourceSet, ...]
    output: WorkOutputContract
    timeout_seconds: int = Field(default=120, ge=1, le=3600)
    max_attempts: int = Field(default=2, ge=1, le=5)

    @model_validator(mode="after")
    def validate_epistemic_boundary(self) -> "WorkItemSpec":
        layers = set(self.output.epistemic_layers)
        if EpistemicLayer.EXTERNAL_EVIDENCE in layers and (
            not {
                SourceSet.PUBLIC_EXTERNAL,
                SourceSet.USER_MATERIAL,
            }.intersection(self.allowed_source_sets)
        ):
            raise ValueError("external evidence output requires an external source set")
        if self.pass_type == AnalysisPass.CROSS_CHAPTER_SYNTHESIS and layers != {
            EpistemicLayer.PLATFORM_INFERENCE
        }:
            raise ValueError("cross-chapter synthesis may emit platform inference only")
        if self.pass_type == AnalysisPass.EXTERNAL_EVIDENCE and layers != {
            EpistemicLayer.EXTERNAL_EVIDENCE
        }:
            raise ValueError("external evidence pass must remain in its own layer")
        return self


class SkippedPass(ContractModel):
    pass_type: AnalysisPass
    reason_code: Literal[
        "book_type_not_selected",
        "external_sources_disabled",
        "insufficient_signal",
    ]


class QualityGate(ContractModel):
    code: Literal[
        "all_references_resolve",
        "all_claims_have_provenance",
        "epistemic_layers_preserved",
        "human_review_required",
        "projection_uses_reviewed_candidates",
    ]
    blocking: Literal[True] = True


class AnalysisPlan(ContractModel):
    contract_version: Literal["analysis_plan.v1"] = "analysis_plan.v1"
    id: Annotated[str, StringConstraints(pattern=r"^plan_[a-f0-9]{20}$")]
    source_checksum: Sha256Checksum
    plan_version: StableIdentifier
    pipeline_version: StableIdentifier
    prompt_bundle_version: StableIdentifier
    profile_revision: int = Field(ge=1)
    primary_type: BookType
    source_policy: SourcePolicy
    planning_scope: PlanningScope = PlanningScope()
    work_items: tuple[WorkItemSpec, ...] = Field(min_length=1)
    skipped_passes: tuple[SkippedPass, ...] = ()
    quality_gates: tuple[QualityGate, ...] = Field(min_length=1)
    max_concurrency: int = Field(default=4, ge=1, le=32)
    estimated_work_item_count: int = Field(ge=1)
    candidate_only: Literal[True] = True
    models_may_publish_reviewed_historical_facts: Literal[False] = False

    @model_validator(mode="after")
    def validate_dag_and_boundaries(self) -> "AnalysisPlan":
        ids = [item.id for item in self.work_items]
        if len(ids) != len(set(ids)):
            raise ValueError("work item ids must be unique")
        if self.estimated_work_item_count != len(self.work_items):
            raise ValueError("estimated_work_item_count must match work_items")

        known = set(ids)
        dependencies = {item.id: set(item.depends_on) for item in self.work_items}
        for item_id, item_dependencies in dependencies.items():
            unknown = item_dependencies - known
            if unknown:
                raise ValueError(f"{item_id} depends on unknown work items")
            if item_id in item_dependencies:
                raise ValueError(f"{item_id} cannot depend on itself")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(item_id: str) -> None:
            if item_id in visiting:
                raise ValueError("analysis plan must be acyclic")
            if item_id in visited:
                return
            visiting.add(item_id)
            for dependency in dependencies[item_id]:
                visit(dependency)
            visiting.remove(item_id)
            visited.add(item_id)

        for item_id in ids:
            visit(item_id)

        if self.work_items[-1].pass_type != AnalysisPass.BUILD_PROJECTIONS:
            raise ValueError("the final work item must build projections")
        if not {
            SourceSet.PUBLIC_EXTERNAL,
            SourceSet.USER_MATERIAL,
        }.intersection(self.source_policy.allowed_source_sets):
            if any(
                item.pass_type == AnalysisPass.EXTERNAL_EVIDENCE
                for item in self.work_items
            ):
                raise ValueError("external evidence pass requires an enabled source policy")
        return self
