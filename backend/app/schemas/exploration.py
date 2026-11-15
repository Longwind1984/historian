"""Contracts for prompt-led and private, session-scoped explorations.

Imported text is deliberately kept separate from the repository's reviewed
YAML/GeoJSON truth sources. TXT, Markdown, and EPUB anchors do not claim
printed pagination. PDF/OCR anchors carry only page-safe locator metadata;
original PDF bytes, image paths, and OCR text remain in the private vault.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class SourceFormat(str, Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    EPUB = "epub"
    PDF_OCR = "pdf_ocr"


class OcrState(str, Enum):
    RENDERED = "rendered"
    OCR_UNVERIFIED = "ocr_unverified"
    OCR_REVIEWED = "ocr_reviewed"


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


class PdfOcrPageInput(BaseModel):
    """One page of local OCR; never accepts a filesystem or image locator."""

    model_config = ConfigDict(extra="forbid")

    pdf_page_index: int = Field(ge=0)
    printed_page_label: str | None = Field(default=None, max_length=50)
    ocr_state: OcrState
    ocr_confidence: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Page-level OCR confidence on a 0-100 percentage scale.",
    )
    content: str = Field(default="", max_length=100_000)

    @model_validator(mode="after")
    def _validate_ocr_state(self) -> PdfOcrPageInput:
        readable = bool(self.content.strip())
        if self.ocr_state is OcrState.RENDERED:
            if readable or self.ocr_confidence is not None:
                raise ValueError(
                    "rendered PDF pages cannot carry OCR text or confidence"
                )
        elif not readable or self.ocr_confidence is None:
            raise ValueError(
                "OCR pages require readable content and ocr_confidence"
            )
        return self


class ImportExplorationRequest(BaseModel):
    content: str | None = Field(default=None, max_length=2_000_000)
    source_format: SourceFormat
    title: str | None = Field(default=None, max_length=300)
    author: str | None = Field(default=None, max_length=200)
    version_label: str | None = Field(
        default=None,
        max_length=300,
        description="User-supplied edition label; never inferred from the text.",
    )
    pdf_checksum_sha256: Annotated[
        str, StringConstraints(pattern=r"^[a-f0-9]{64}$")
    ] | None = None
    pdf_pages: list[PdfOcrPageInput] | None = Field(default=None, max_length=5_000)
    brief: ExplorationBrief = Field(default_factory=ExplorationBrief)

    @model_validator(mode="after")
    def _validate_source_payload(self) -> ImportExplorationRequest:
        if self.source_format is SourceFormat.PDF_OCR:
            if self.content is not None:
                raise ValueError("PDF/OCR import uses pdf_pages instead of content")
            if not self.pdf_checksum_sha256 or not self.pdf_pages:
                raise ValueError(
                    "PDF/OCR import requires pdf_checksum_sha256 and pdf_pages"
                )
            indices = [page.pdf_page_index for page in self.pdf_pages]
            if len(indices) != len(set(indices)):
                raise ValueError("PDF/OCR pdf_page_index values must be unique")
        else:
            if not self.content or not self.content.strip():
                raise ValueError("Text and Markdown imports require readable content")
            if self.pdf_checksum_sha256 is not None or self.pdf_pages is not None:
                raise ValueError("PDF/OCR metadata is only valid for pdf_ocr imports")
        return self


class EpubImportRequest(BaseModel):
    content_base64: str = Field(
        min_length=1,
        # Base64 expands bytes by 4 * ceil(n / 3). This is the exact encoded
        # envelope for the service's 16 MiB compressed EPUB limit.
        max_length=22_369_624,
        description=(
            "Base64 EPUB bytes for at most 16 MiB compressed input; decoded "
            "bytes are written only to the local private source vault."
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
    model_config = ConfigDict(extra="forbid")

    source_format: SourceFormat
    section_index: int = Field(ge=0)
    paragraph_index: int = Field(ge=0)
    spine_index: int | None = Field(default=None, ge=0)
    href: str | None = Field(default=None, max_length=1000)
    pdf_page_index: int | None = Field(default=None, ge=0)
    printed_page_label: str | None = Field(default=None, max_length=50)
    ocr_state: OcrState | None = None
    ocr_confidence: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Page-level OCR confidence on a 0-100 percentage scale.",
    )
    progression_percent: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def _validate_format_locator(self) -> DocumentLocator:
        pdf_values = (
            self.pdf_page_index,
            self.printed_page_label,
            self.ocr_state,
            self.ocr_confidence,
        )
        if self.source_format is SourceFormat.PDF_OCR:
            if self.pdf_page_index is None or self.ocr_state is None:
                raise ValueError(
                    "PDF/OCR locators require pdf_page_index and ocr_state"
                )
            if self.ocr_state is OcrState.RENDERED:
                raise ValueError("Paragraph anchors require completed OCR")
            if self.ocr_confidence is None:
                raise ValueError("OCR paragraph locators require ocr_confidence")
            if self.spine_index is not None or self.href is not None:
                raise ValueError("PDF/OCR locators cannot carry EPUB or path locators")
        elif any(value is not None for value in pdf_values):
            raise ValueError("PDF/OCR locator fields require source_format=pdf_ocr")
        return self


class ParagraphAnchor(BaseModel):
    id: str
    section_id: str
    ordinal: int = Field(ge=0)
    text: str
    anchor_kind: Literal["paragraph"] = "paragraph"
    page_label: str | None = Field(default=None, max_length=50)
    locator: DocumentLocator

    @model_validator(mode="after")
    def _mirror_printed_page_label(self) -> ParagraphAnchor:
        expected = self.locator.printed_page_label
        if self.page_label is not None and self.page_label != expected:
            raise ValueError("page_label must match locator.printed_page_label")
        self.page_label = expected
        return self


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


class PdfOcrPageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pdf_page_index: int = Field(ge=0)
    printed_page_label: str | None = Field(default=None, max_length=50)
    ocr_state: OcrState
    ocr_confidence: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Page-level OCR confidence on a 0-100 percentage scale.",
    )
    paragraph_anchor_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_page_state(self) -> PdfOcrPageMetadata:
        if len(self.paragraph_anchor_ids) != len(set(self.paragraph_anchor_ids)):
            raise ValueError("PDF/OCR paragraph_anchor_ids must be unique")
        if self.ocr_state is OcrState.RENDERED:
            if self.ocr_confidence is not None or self.paragraph_anchor_ids:
                raise ValueError(
                    "rendered PDF page metadata cannot reference OCR anchors"
                )
        elif self.ocr_confidence is None or not self.paragraph_anchor_ids:
            raise ValueError(
                "OCR page metadata requires confidence and paragraph anchors"
            )
        return self


class PdfOcrMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pdf_checksum_sha256: Annotated[
        str, StringConstraints(pattern=r"^[a-f0-9]{64}$")
    ]
    page_count: int = Field(ge=1)
    pages: list[PdfOcrPageMetadata] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_pages(self) -> PdfOcrMetadata:
        indices = [page.pdf_page_index for page in self.pages]
        if self.page_count != len(self.pages):
            raise ValueError("PDF/OCR page_count must match pages")
        if len(indices) != len(set(indices)):
            raise ValueError("PDF/OCR page metadata indices must be unique")
        if indices != sorted(indices):
            raise ValueError("PDF/OCR page metadata must be ordered by page index")
        return self


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
    retention: Literal["private_source_vault"] = "private_source_vault"
    ephemeral: Literal[False] = False
    sections: list[DocumentSection]
    epub_metadata: EpubMetadata | None = None
    pdf_ocr_metadata: PdfOcrMetadata | None = None

    @model_validator(mode="after")
    def _validate_format_metadata(self) -> PrivateDocument:
        if self.source_format is SourceFormat.EPUB:
            if self.epub_metadata is None or self.pdf_ocr_metadata is not None:
                raise ValueError("EPUB documents require only epub_metadata")
        elif self.source_format is SourceFormat.PDF_OCR:
            if self.pdf_ocr_metadata is None or self.epub_metadata is not None:
                raise ValueError("PDF/OCR documents require only pdf_ocr_metadata")
        elif self.epub_metadata is not None or self.pdf_ocr_metadata is not None:
            raise ValueError("Text documents cannot carry binary source metadata")
        if self.source_format is SourceFormat.PDF_OCR:
            assert self.pdf_ocr_metadata is not None
            anchors = {
                paragraph.id: paragraph
                for section in self.sections
                for paragraph in section.paragraphs
            }
            metadata_anchor_ids = [
                anchor_id
                for page in self.pdf_ocr_metadata.pages
                for anchor_id in page.paragraph_anchor_ids
            ]
            if len(metadata_anchor_ids) != len(set(metadata_anchor_ids)):
                raise ValueError("PDF/OCR metadata anchor IDs must be globally unique")
            if set(metadata_anchor_ids) != set(anchors):
                raise ValueError("PDF/OCR metadata must cover every paragraph anchor")
            for page in self.pdf_ocr_metadata.pages:
                for anchor_id in page.paragraph_anchor_ids:
                    locator = anchors[anchor_id].locator
                    if (
                        locator.pdf_page_index != page.pdf_page_index
                        or locator.printed_page_label != page.printed_page_label
                        or locator.ocr_state != page.ocr_state
                        or locator.ocr_confidence != page.ocr_confidence
                    ):
                        raise ValueError(
                            "PDF/OCR page metadata does not match paragraph locator"
                        )
        return self


class SourceLocator(BaseModel):
    document_id: str
    section_id: str
    paragraph_id: str
    page_label: str | None = Field(default=None, max_length=50)
    document_locator: DocumentLocator

    @model_validator(mode="after")
    def _mirror_printed_page_label(self) -> SourceLocator:
        expected = self.document_locator.printed_page_label
        if self.page_label is not None and self.page_label != expected:
            raise ValueError("page_label must match document_locator.printed_page_label")
        self.page_label = expected
        return self


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
    nodes: list[ArgumentGraphNode] = Field(min_length=2, max_length=24)
    edges: list[ArgumentGraphEdge] = Field(min_length=1, max_length=60)
    review_status: ReviewStatus = ReviewStatus.PENDING

    @model_validator(mode="after")
    def _validate_graph(self) -> ArgumentGraph:
        node_ids = [node.id for node in self.nodes]
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("Argument graph node ids must be unique")
        edge_ids = [edge.id for edge in self.edges]
        if len(set(edge_ids)) != len(edge_ids):
            raise ValueError("Argument graph edge ids must be unique")

        # Different books expose different structures. Event narratives often
        # need actions and consequences, while argumentative monographs may
        # contain only observations, mechanisms, and qualifications. Requiring
        # every visual node kind incentivised the model to fabricate missing
        # steps. A limitation remains mandatory so every graph states its
        # evidence boundary; source anchors are mandatory on every node.
        required_types = {ArgumentNodeType.LIMITATION}
        present_types = {node.node_type for node in self.nodes}
        missing = sorted(item.value for item in required_types - present_types)
        if missing:
            raise ValueError(
                f"Argument graph is missing required safety node types: {', '.join(missing)}"
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
    storage: Literal["sqlite_control_plane_private_vault"] = (
        "sqlite_control_plane_private_vault"
    )
    private_source_in_database: Literal[False] = False
    restart_clears_session: Literal[False] = False
    explicit_delete_required: Literal[True] = True


class ExplorationSnapshot(BaseModel):
    id: str
    revision: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime
    retention: Literal["private_source_vault"] = "private_source_vault"
    persistence_warning: Literal[
        "Stored locally until this exploration is explicitly deleted."
    ] = "Stored locally until this exploration is explicitly deleted."
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


class AnalysisRunCreateRequest(BaseModel):
    """Create a durable plan; workers are dispatched outside the HTTP request."""

    base_revision: int = Field(ge=1)


class AnalysisWorkItemStatus(BaseModel):
    id: str
    pass_type: str
    state: Literal[
        "queued",
        "running",
        "retry_wait",
        "succeeded",
        "failed",
        "cancelled",
    ]
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    last_error_code: str | None = None


class AnalysisRunStatus(BaseModel):
    id: str
    exploration_id: str
    plan_id: str
    plan_revision: int = Field(ge=1)
    primary_book_type: str
    state: Literal[
        "planned",
        "queued",
        "running",
        "retry_wait",
        "paused",
        "waiting_review",
        "waiting_input",
        "failed",
        "cancelled",
        "completed",
    ]
    cancel_requested: bool
    dispatch: Literal["external_worker_required"] = "external_worker_required"
    created_at: datetime
    updated_at: datetime
    work_items: list[AnalysisWorkItemStatus] = Field(default_factory=list)


class AnalysisRunList(BaseModel):
    items: list[AnalysisRunStatus] = Field(default_factory=list)


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
