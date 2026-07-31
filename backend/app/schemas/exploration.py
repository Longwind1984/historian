"""Contracts for prompt-led and private, session-scoped explorations.

Imported text is deliberately kept separate from the repository's reviewed
YAML/GeoJSON truth sources. TXT, Markdown, and EPUB paragraph anchors are
locators, not trustworthy printed page numbers.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import AnyHttpUrl, BaseModel, Field, StringConstraints, model_validator


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class SourceFormat(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    EPUB = "epub"


class EvidenceLevel(str, Enum):
    SOURCE_DIRECT = "source_direct"
    MULTI_SOURCE = "multi_source"
    SINGLE_SOURCE = "single_source"
    AUTHOR_JUDGMENT = "author_judgment"
    MODEL_INFERENCE = "model_inference"
    DISPUTED = "disputed"
    EVIDENCE_GAP = "evidence_gap"


class ArgumentNodeType(str, Enum):
    QUESTION = "question"
    MATERIAL_OBSERVATION = "material_observation"
    REASONING_MECHANISM = "reasoning_mechanism"
    ACTION_OR_TURN = "action_or_turn"
    CONSEQUENCE = "consequence"
    LIMITATION = "limitation"


class EpistemicLayer(str, Enum):
    HISTORICAL_FACT = "historical_fact"
    AUTHOR_JUDGMENT = "author_judgment"
    PLATFORM_INFERENCE = "platform_inference"
    UNCERTAINTY = "uncertainty"


class ArgumentEdgeRelation(str, Enum):
    FRAMES = "frames"
    GROUNDS = "grounds"
    EXPLAINS = "explains"
    TRIGGERS = "triggers"
    LEADS_TO = "leads_to"
    QUALIFIES = "qualifies"
    COMPLICATES = "complicates"
    CONTRADICTS = "contradicts"


class ReviewStatus(str, Enum):
    PENDING = "pending_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class MapState(str, Enum):
    READY = "ready"
    NO_LOCATION = "no_location"


class ExplorationBrief(BaseModel):
    question: str | None = Field(default=None, max_length=2000)
    time_range: str | None = Field(default=None, max_length=100)
    geography: list[str] = Field(default_factory=list, max_length=50)
    threads: list[str] = Field(default_factory=list, max_length=10)
    status: Literal["draft", "confirmed"] = "draft"


class ScopeContract(BaseModel):
    """A research boundary to refine, not a generated historical answer."""

    original_question: NonEmptyText = Field(max_length=10_000)
    time_range: str | None = Field(default=None, max_length=100)
    geography: list[str] = Field(default_factory=list, max_length=50)
    narrative_threads: list[str] = Field(default_factory=list, max_length=10)
    fields_needing_confirmation: list[
        Literal["time_range", "geography", "narrative_threads"]
    ] = Field(default_factory=list)
    starter_questions: list[str] = Field(default_factory=list, max_length=6)
    processing_status: Literal["rule_scaffold", "needs_model"] = "rule_scaffold"


class PromptExplorationRequest(BaseModel):
    prompt: NonEmptyText = Field(max_length=10_000)
    user_supplied_time_range: str | None = Field(
        default=None,
        max_length=100,
        description="Stored verbatim; the server does not infer a date from the prompt.",
    )
    user_supplied_geography: list[str] = Field(default_factory=list, max_length=50)
    user_supplied_threads: list[str] = Field(default_factory=list, max_length=10)


class ImportExplorationRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2_000_000)
    source_format: SourceFormat
    title: str | None = Field(default=None, max_length=300)
    author: str | None = Field(default=None, max_length=200)
    version_label: str | None = Field(
        default=None,
        max_length=300,
        description="User-supplied edition label; never inferred from the text.",
    )
    brief: ExplorationBrief = Field(default_factory=ExplorationBrief)


class EpubImportRequest(BaseModel):
    content_base64: str = Field(
        min_length=1,
        # Base64 expands bytes by 4 * ceil(n / 3). This is the exact encoded
        # envelope for the service's 16 MiB compressed EPUB limit.
        max_length=22_369_624,
        description=(
            "Base64 EPUB bytes for at most 16 MiB compressed input; decoded "
            "bytes are kept in process memory only."
        ),
    )
    filename: str | None = Field(
        default=None,
        max_length=300,
        description="Optional display filename; it is not persisted as source bytes.",
    )
    title: str | None = Field(default=None, max_length=300)
    author: str | None = Field(default=None, max_length=200)
    version_label: str | None = Field(
        default=None,
        max_length=300,
        description="User-supplied edition label; never inferred from OPF metadata.",
    )
    brief: ExplorationBrief = Field(default_factory=ExplorationBrief)


class DocumentLocator(BaseModel):
    source_format: SourceFormat
    section_index: int = Field(ge=0)
    paragraph_index: int = Field(ge=0)
    spine_index: int | None = Field(default=None, ge=0)
    href: str | None = Field(default=None, max_length=1000)
    progression_percent: float = Field(ge=0, le=100)


class ParagraphAnchor(BaseModel):
    id: str
    section_id: str
    ordinal: int = Field(ge=0)
    text: str
    anchor_kind: Literal["paragraph"] = "paragraph"
    page_label: None = Field(
        default=None,
        description="No verified printed-page mapping exists; this stays null.",
    )
    locator: DocumentLocator


class DocumentSection(BaseModel):
    id: str
    title: str
    level: int = Field(ge=0, le=6)
    ordinal: int = Field(ge=0)
    paragraphs: list[ParagraphAnchor]


class EpubMetadata(BaseModel):
    opf_path: str
    language: str | None = None
    identifier: str | None = None
    publisher: str | None = None
    publication_date: str | None = None
    metadata_provenance: Literal["epub_opf"] = "epub_opf"


class PrivateDocument(BaseModel):
    id: str
    title: str
    author: str | None = None
    version_label: str | None = None
    source_format: SourceFormat
    checksum_sha256: str
    char_count: int = Field(ge=1)
    section_count: int = Field(ge=1)
    paragraph_count: int = Field(ge=1)
    retention: Literal["process_memory"] = "process_memory"
    ephemeral: Literal[True] = True
    sections: list[DocumentSection]
    epub_metadata: EpubMetadata | None = None


class SourceLocator(BaseModel):
    document_id: str
    section_id: str
    paragraph_id: str
    page_label: None = None
    document_locator: DocumentLocator


class Evidence(BaseModel):
    id: str
    claim_id: str
    source_kind: Literal["book_paragraph"] = "book_paragraph"
    locator: SourceLocator
    relation: Literal["source_context"] = "source_context"
    evidence_level: Literal[EvidenceLevel.SINGLE_SOURCE] = EvidenceLevel.SINGLE_SOURCE
    review_status: Literal[ReviewStatus.PENDING] = ReviewStatus.PENDING
    quote: None = Field(
        default=None,
        description="No quote is synthesized; the reader resolves the paragraph anchor.",
    )


class ArgumentGraphNode(BaseModel):
    id: NonEmptyText = Field(max_length=120)
    node_type: ArgumentNodeType
    title: ShortText
    summary: NonEmptyText = Field(max_length=2_000)
    detail: NonEmptyText = Field(max_length=6_000)
    epistemic_layer: EpistemicLayer
    source_anchor_ids: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def _deduplicate_source_anchors(self) -> ArgumentGraphNode:
        if len(set(self.source_anchor_ids)) != len(self.source_anchor_ids):
            raise ValueError("Argument node source_anchor_ids must be unique")
        return self


class ArgumentGraphEdge(BaseModel):
    id: NonEmptyText = Field(max_length=160)
    from_node_id: NonEmptyText = Field(max_length=120)
    to_node_id: NonEmptyText = Field(max_length=120)
    relation: ArgumentEdgeRelation
    label: ShortText
    source_anchor_ids: list[str] = Field(default_factory=list, max_length=20)


class ArgumentGraph(BaseModel):
    """A source-addressable reasoning graph, orthogonal to map/timeline Scene."""

    id: NonEmptyText = Field(max_length=120)
    question: NonEmptyText = Field(max_length=2_000)
    scene_id: str | None = Field(default=None, max_length=120)
    nodes: list[ArgumentGraphNode] = Field(min_length=6, max_length=24)
    edges: list[ArgumentGraphEdge] = Field(min_length=5, max_length=60)
    review_status: ReviewStatus = ReviewStatus.PENDING

    @model_validator(mode="after")
    def _validate_graph(self) -> ArgumentGraph:
        node_ids = [node.id for node in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("Argument graph node ids must be unique")
        edge_ids = [edge.id for edge in self.edges]
        if len(set(edge_ids)) != len(edge_ids):
            raise ValueError("Argument graph edge ids must be unique")

        required_types = set(ArgumentNodeType)
        present_types = {node.node_type for node in self.nodes}
        missing = sorted(item.value for item in required_types - present_types)
        if missing:
            raise ValueError(
                f"Argument graph is missing required node types: {', '.join(missing)}"
            )

        known_nodes = set(node_ids)
        known_source_anchors = {
            anchor_id
            for node in self.nodes
            for anchor_id in node.source_anchor_ids
        }
        for edge in self.edges:
            if edge.from_node_id not in known_nodes or edge.to_node_id not in known_nodes:
                raise ValueError(
                    f"Argument graph edge {edge.id} references an unknown node"
                )
            if edge.from_node_id == edge.to_node_id:
                raise ValueError(
                    f"Argument graph edge {edge.id} cannot reference one node twice"
                )
            if not set(edge.source_anchor_ids).issubset(known_source_anchors):
                raise ValueError(
                    f"Argument graph edge {edge.id} references an unknown source anchor"
                )
            if (
                edge.relation == ArgumentEdgeRelation.CONTRADICTS
                and not edge.source_anchor_ids
            ):
                raise ValueError(
                    f"Contradiction edge {edge.id} requires material locators"
                )
        return self


class ArgumentPromptContract(BaseModel):
    contract_version: Literal["book_argument_graph.v1"] = "book_argument_graph.v1"
    task: Literal["build_argument_graph"] = "build_argument_graph"
    invocation_status: Literal["not_called"] = "not_called"
    processing_status: Literal["needs_model"] = "needs_model"
    request_text: NonEmptyText = Field(max_length=10_000)
    source_anchor_ids: list[str] = Field(default_factory=list, max_length=20)
    source_locators: list[SourceLocator] = Field(default_factory=list, max_length=20)
    source_payload_state: Literal[
        "requires_runtime_injection", "missing_source"
    ]
    requested_views: list[
        Literal["chronology", "causal_threads", "person_interactions", "map_candidates"]
    ] = Field(default_factory=list, max_length=4)
    guardrails: list[NonEmptyText] = Field(min_length=6, max_length=12)
    output_schema: dict[str, Any]

    @model_validator(mode="after")
    def _validate_source_contract(self) -> ArgumentPromptContract:
        locator_anchor_ids = [
            locator.paragraph_id for locator in self.source_locators
        ]
        if self.source_anchor_ids != locator_anchor_ids:
            raise ValueError(
                "Prompt source_anchor_ids must preserve source_locators order"
            )
        expected_state = (
            "requires_runtime_injection"
            if self.source_locators
            else "missing_source"
        )
        if self.source_payload_state != expected_state:
            raise ValueError(
                "Prompt source_payload_state does not match available locators"
            )
        return self


class Claim(BaseModel):
    id: str
    text: str
    claim_kind: Literal["structure_proposal", "research_question"] = "structure_proposal"
    evidence_level: Literal[
        EvidenceLevel.MODEL_INFERENCE, EvidenceLevel.EVIDENCE_GAP
    ] = EvidenceLevel.MODEL_INFERENCE
    review_status: ReviewStatus = ReviewStatus.PENDING
    source_anchor_ids: list[str] = Field(default_factory=list)
    provenance: Literal[
        "composer_structure_proposal", "prompt_scope_scaffold"
    ] = "composer_structure_proposal"


class Scene(BaseModel):
    id: str
    title: str
    summary: str
    temporal_label: str | None = None
    temporal_precision: Literal["user_supplied", "unknown"] = "unknown"
    map_state: Literal[MapState.NO_LOCATION] = MapState.NO_LOCATION
    map_focus: None = Field(
        default=None,
        description="No place is inferred from imported prose or user wording.",
    )
    claim_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_level: EvidenceLevel = EvidenceLevel.MODEL_INFERENCE
    review_status: ReviewStatus = ReviewStatus.PENDING


class ComposerEntry(BaseModel):
    id: str
    intent: Literal["question", "note", "propose_scene", "request_deep_analysis"]
    message: str
    anchor_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    processing_status: Literal[
        "recorded_no_llm", "structured_proposal", "needs_model"
    ]


class AnalysisQueueItem(BaseModel):
    id: str
    request_text: str
    anchor_ids: list[str] = Field(default_factory=list)
    evidence_boundary: Literal["selected_book_anchors", "evidence_gap"]
    requested_views: list[
        Literal["chronology", "causal_threads", "person_interactions", "map_candidates"]
    ] = Field(default_factory=list)
    status: Literal["queued"] = "queued"
    processing_status: Literal["needs_model"] = "needs_model"
    prompt_contract: ArgumentPromptContract
    candidate_output: ArgumentGraph | None = Field(
        default=None,
        description="No analysis, quotation, page, time, place, or opposition is fabricated.",
    )
    created_at: datetime


class ReadingProgress(BaseModel):
    anchor_id: str
    progression_percent: float = Field(ge=0, le=100)
    locator: DocumentLocator
    updated_at: datetime


class ExternalReadingBridge(BaseModel):
    provider: Literal["weread"]
    url: AnyHttpUrl
    external_locator: str = Field(max_length=1000)
    user_provided_excerpt: str | None = Field(default=None, max_length=20_000)
    sync_mode: Literal["manual_sync"] = "manual_sync"
    access_boundary: Literal[
        "cross_origin_no_dom_access"
    ] = "cross_origin_no_dom_access"
    dom_access: Literal[False] = False
    updated_at: datetime


class SessionBoundary(BaseModel):
    storage: Literal["process_memory"] = "process_memory"
    ttl_seconds: float = Field(gt=0)
    max_sessions: int = Field(ge=1)
    max_total_source_chars: int = Field(ge=1)
    restart_clears_session: Literal[True] = True


class ExplorationSnapshot(BaseModel):
    id: str
    revision: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    retention: Literal["process_memory"] = "process_memory"
    persistence_warning: Literal[
        "Process restart clears this private exploration."
    ] = "Process restart clears this private exploration."
    session_boundary: SessionBoundary
    entry_mode: Literal["prompt", "book"]
    document: PrivateDocument | None = None
    brief: ExplorationBrief
    scope_contract: ScopeContract | None = None
    active_anchor_id: str | None = None
    active_scene_id: str | None = None
    reading_progress: ReadingProgress | None = None
    external_reading_bridge: ExternalReadingBridge | None = None
    scenes: list[Scene] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    argument_graphs: list[ArgumentGraph] = Field(default_factory=list)
    composer_entries: list[ComposerEntry] = Field(default_factory=list)
    analysis_queue: list[AnalysisQueueItem] = Field(default_factory=list)


class ComposeRequest(BaseModel):
    base_revision: int = Field(ge=1)
    intent: Literal["question", "note", "propose_scene", "request_deep_analysis"]
    message: NonEmptyText = Field(max_length=10_000)
    anchor_ids: list[str] = Field(default_factory=list, max_length=20)
    scene_title: str | None = Field(default=None, max_length=300)
    temporal_label: str | None = Field(
        default=None,
        max_length=100,
        description="Stored verbatim as user supplied; never normalized into a fact.",
    )
    requested_views: list[
        Literal["chronology", "causal_threads", "person_interactions", "map_candidates"]
    ] = Field(default_factory=list, max_length=4)


class ComposerMutationResult(BaseModel):
    mutation_id: str
    outcome: Literal["recorded_no_llm", "scene_proposed", "analysis_queued"]
    snapshot: ExplorationSnapshot


class MutationBase(BaseModel):
    base_revision: int = Field(ge=1)


class SetActiveAnchorMutation(MutationBase):
    type: Literal["set_active_anchor"]
    anchor_id: str


class UpdateReadingProgressMutation(MutationBase):
    type: Literal["update_reading_progress"]
    anchor_id: str


class SyncExternalReadingMutation(MutationBase):
    type: Literal["sync_external_reading_progress"]
    provider: Literal["weread"]
    url: AnyHttpUrl
    external_locator: ShortText
    user_provided_excerpt: str | None = Field(default=None, max_length=20_000)


class UpdateScopeContractMutation(MutationBase):
    type: Literal["update_scope_contract"]
    user_supplied_time_range: ShortText | None = None
    user_supplied_geography: list[ShortText] | None = Field(
        default=None, max_length=50
    )
    user_supplied_threads: list[ShortText] | None = Field(
        default=None, max_length=10
    )

    @model_validator(mode="after")
    def require_scope_change(self):
        if (
            self.user_supplied_time_range is None
            and self.user_supplied_geography is None
            and self.user_supplied_threads is None
        ):
            raise ValueError("At least one scope field must be supplied")
        return self


class SetActiveSceneMutation(MutationBase):
    type: Literal["set_active_scene"]
    scene_id: str


class ReviewSceneMutation(MutationBase):
    type: Literal["review_scene"]
    scene_id: str
    decision: Literal[ReviewStatus.ACCEPTED, ReviewStatus.REJECTED]


ExplorationMutation = Annotated[
    SetActiveAnchorMutation
    | UpdateReadingProgressMutation
    | SyncExternalReadingMutation
    | UpdateScopeContractMutation
    | SetActiveSceneMutation
    | ReviewSceneMutation,
    Field(discriminator="type"),
]
