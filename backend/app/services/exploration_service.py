"""Process-local exploration parsing and mutation service.

Private source bytes and parsed paragraphs live only in this bounded in-memory
store. Nothing here writes imported material to the repository, a database, or
logs. EPUBs are treated as untrusted ZIP containers and are never extracted.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
from pathlib import PurePosixPath
import posixpath
import re
import threading
import time
from urllib.parse import unquote, urlsplit
from uuid import uuid4
import xml.etree.ElementTree as ElementTree
import zipfile

from ..prompts.book_argument_graph import build_book_argument_prompt_contract
from ..schemas.exploration import (
    AnalysisQueueItem,
    Claim,
    ComposeRequest,
    ComposerEntry,
    ComposerMutationResult,
    DocumentLocator,
    DocumentSection,
    EpubImportRequest,
    EpubMetadata,
    Evidence,
    EvidenceLevel,
    ExplorationBrief,
    ExplorationMutation,
    ExplorationSnapshot,
    ExternalReadingBridge,
    ImportExplorationRequest,
    MapState,
    ParagraphAnchor,
    PrivateDocument,
    PromptExplorationRequest,
    ReadingProgress,
    ReviewSceneMutation,
    ReviewStatus,
    Scene,
    ScopeContract,
    SessionBoundary,
    SetActiveAnchorMutation,
    SetActiveSceneMutation,
    SourceFormat,
    SourceLocator,
    SyncExternalReadingMutation,
    UpdateReadingProgressMutation,
    UpdateScopeContractMutation,
)


_MARKDOWN_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")
_PLAIN_SECTION_HEADING = re.compile(
    r"^\s*第[〇零一二三四五六七八九十百千万两0-9]{1,16}"
    r"[章节编卷部篇]\s*[^。！？!?]{0,80}\s*$"
)

# The compressed-size ceiling is only the first transport guard. Entry count,
# per-entry size, total expansion, spine length, and readable text remain
# independently bounded below. 16 MiB is the smallest practical binary tier
# that admits current local books without weakening ZIP-bomb protections.
MAX_EPUB_BYTES = 16 * 1024 * 1024
MAX_EPUB_ENTRY_COUNT = 500
MAX_EPUB_ENTRY_BYTES = 8 * 1024 * 1024
MAX_EPUB_TOTAL_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
MAX_EPUB_MARKUP_BYTES = 4 * 1024 * 1024
MAX_EPUB_SPINE_ITEMS = 2_000
MAX_EPUB_TEXT_CHARS = 1_500_000
DEFAULT_MAX_TOTAL_SOURCE_CHARS = 8_000_000
_ALLOWED_ZIP_COMPRESSION = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
_XML_FORBIDDEN_MARKERS = (b"<!doctype", b"<!entity")
_EPUB_DOCUMENT_MEDIA_TYPES = {"application/xhtml+xml", "text/html"}


class ExplorationError(Exception):
    """Base exception for exploration requests."""


class ExplorationNotFound(ExplorationError):
    pass


class InvalidPrivateText(ExplorationError):
    pass


class UnknownAnchor(ExplorationError):
    pass


class UnknownScene(ExplorationError):
    pass


class RevisionConflict(ExplorationError):
    def __init__(self, expected: int, actual: int):
        super().__init__(
            f"Exploration revision conflict: expected {expected}, current {actual}"
        )
        self.expected = expected
        self.actual = actual


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _normalise_content(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff").strip()


def _anchor_id(section_ordinal: int, paragraph_ordinal: int, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
    return f"p_{section_ordinal}_{paragraph_ordinal}_{digest}"


def _progression(global_ordinal: int, paragraph_count: int) -> float:
    if paragraph_count <= 1:
        return 0.0
    return round((global_ordinal / (paragraph_count - 1)) * 100, 4)


def _build_section(
    title: str,
    level: int,
    ordinal: int,
    paragraph_texts: list[str],
    source_format: SourceFormat,
) -> DocumentSection | None:
    paragraphs = []
    for paragraph_ordinal, paragraph_text in enumerate(paragraph_texts):
        cleaned = paragraph_text.strip()
        if not cleaned:
            continue
        paragraphs.append(
            ParagraphAnchor(
                id=_anchor_id(ordinal, paragraph_ordinal, cleaned),
                section_id=f"section_{ordinal}",
                ordinal=paragraph_ordinal,
                text=cleaned,
                locator=DocumentLocator(
                    source_format=source_format,
                    section_index=ordinal,
                    paragraph_index=paragraph_ordinal,
                    progression_percent=0,
                ),
            )
        )
    if not paragraphs:
        return None
    return DocumentSection(
        id=f"section_{ordinal}",
        title=title.strip() or "未命名章节",
        level=level,
        ordinal=ordinal,
        paragraphs=paragraphs,
    )


def _apply_document_progression(sections: list[DocumentSection]) -> None:
    paragraphs = [
        paragraph for section in sections for paragraph in section.paragraphs
    ]
    for global_ordinal, paragraph in enumerate(paragraphs):
        paragraph.locator.progression_percent = _progression(
            global_ordinal, len(paragraphs)
        )


def _parse_sections(
    content: str, source_format: SourceFormat
) -> tuple[list[DocumentSection], str | None]:
    """Parse headings and blank-line paragraphs without inventing pagination."""
    sections: list[DocumentSection] = []
    current_title = "正文"
    current_level = 0
    paragraph_lines: list[str] = []
    section_paragraphs: list[str] = []
    first_heading: str | None = None

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            paragraph = "\n".join(line.rstrip() for line in paragraph_lines).strip()
            if paragraph:
                section_paragraphs.append(paragraph)
            paragraph_lines = []

    def flush_section() -> None:
        nonlocal section_paragraphs
        flush_paragraph()
        section = _build_section(
            current_title,
            current_level,
            len(sections),
            section_paragraphs,
            source_format,
        )
        if section is not None:
            sections.append(section)
        section_paragraphs = []

    for line in content.split("\n"):
        heading_title: str | None = None
        heading_level = 0
        if source_format == SourceFormat.MARKDOWN:
            match = _MARKDOWN_HEADING.match(line)
            if match:
                heading_level = len(match.group(1))
                heading_title = match.group(2).strip()
        elif _PLAIN_SECTION_HEADING.match(line):
            heading_title = line.strip()
            heading_level = 1

        if heading_title:
            if first_heading is None:
                first_heading = heading_title
            flush_section()
            current_title = heading_title
            current_level = heading_level
            continue

        if not line.strip():
            flush_paragraph()
            continue
        paragraph_lines.append(line)

    flush_section()
    _apply_document_progression(sections)
    return sections, first_heading


def _parse_text_document(request: ImportExplorationRequest) -> PrivateDocument:
    if request.source_format == SourceFormat.EPUB:
        raise InvalidPrivateText("Use the EPUB import endpoint for EPUB bytes")
    content = _normalise_content(request.content)
    if not content:
        raise InvalidPrivateText("Imported private text has no readable content")
    sections, first_heading = _parse_sections(content, request.source_format)
    if not sections:
        raise InvalidPrivateText(
            "Imported private text has no readable paragraphs after parsing"
        )
    inferred_markdown_title = (
        first_heading if request.source_format == SourceFormat.MARKDOWN else None
    )
    title = (request.title or inferred_markdown_title or "未命名私人文本").strip()
    paragraph_count = sum(len(section.paragraphs) for section in sections)
    return PrivateDocument(
        id=_new_id("doc"),
        title=title,
        author=request.author.strip() if request.author else None,
        version_label=request.version_label.strip() if request.version_label else None,
        source_format=request.source_format,
        checksum_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        char_count=len(content),
        section_count=len(sections),
        paragraph_count=paragraph_count,
        sections=sections,
    )


def _assert_safe_markup(data: bytes, label: str) -> None:
    if len(data) > MAX_EPUB_MARKUP_BYTES:
        raise InvalidPrivateText(f"EPUB markup entry is too large: {label}")
    lowered = data.lower()
    if any(marker in lowered for marker in _XML_FORBIDDEN_MARKERS):
        raise InvalidPrivateText(
            f"EPUB markup contains a forbidden DOCTYPE or entity declaration: {label}"
        )


def _parse_xml(data: bytes, label: str) -> ElementTree.Element:
    _assert_safe_markup(data, label)
    try:
        return ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise InvalidPrivateText(f"Invalid EPUB XML in {label}") from error


def _safe_archive_path(raw_path: str, label: str) -> str:
    decoded = unquote(raw_path)
    decoded_parts = PurePosixPath(decoded).parts
    if (
        not decoded
        or "\x00" in decoded
        or "\\" in decoded
        or decoded.startswith("/")
        or urlsplit(decoded).scheme
        or urlsplit(decoded).netloc
        or ".." in decoded_parts
    ):
        raise InvalidPrivateText(f"Unsafe EPUB archive path in {label}")
    normalized = posixpath.normpath(decoded)
    path = PurePosixPath(normalized)
    if normalized in {"", "."} or any(part == ".." for part in path.parts):
        raise InvalidPrivateText(f"Unsafe EPUB archive path in {label}")
    return normalized


def _resolve_epub_href(opf_path: str, href: str) -> str:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        raise InvalidPrivateText("Remote resources cannot be EPUB spine documents")
    relative_path = _safe_archive_path(parsed.path, "OPF manifest href")
    return _safe_archive_path(
        posixpath.join(posixpath.dirname(opf_path), relative_path),
        "resolved OPF manifest href",
    )


def _validate_epub_archive(
    epub_bytes: bytes,
) -> tuple[zipfile.ZipFile, dict[str, zipfile.ZipInfo]]:
    if len(epub_bytes) > MAX_EPUB_BYTES:
        raise InvalidPrivateText("EPUB exceeds the 16 MiB compressed-size limit")
    try:
        archive = zipfile.ZipFile(io.BytesIO(epub_bytes))
    except (zipfile.BadZipFile, OSError) as error:
        raise InvalidPrivateText("Uploaded bytes are not a readable EPUB ZIP") from error

    infos = archive.infolist()
    if len(infos) > MAX_EPUB_ENTRY_COUNT:
        archive.close()
        raise InvalidPrivateText("EPUB contains too many ZIP entries")

    total_uncompressed = 0
    info_by_name: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        safe_name = _safe_archive_path(info.filename.rstrip("/"), "ZIP entry")
        if info.flag_bits & 0x1:
            archive.close()
            raise InvalidPrivateText("Encrypted EPUB ZIP entries are not supported")
        if info.compress_type not in _ALLOWED_ZIP_COMPRESSION:
            archive.close()
            raise InvalidPrivateText("Unsupported EPUB ZIP compression method")
        unix_file_type = (info.external_attr >> 16) & 0o170000
        if unix_file_type == 0o120000:
            archive.close()
            raise InvalidPrivateText("EPUB ZIP symlink entries are not supported")
        if info.file_size > MAX_EPUB_ENTRY_BYTES:
            archive.close()
            raise InvalidPrivateText("EPUB ZIP entry exceeds the 8 MiB limit")
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_EPUB_TOTAL_UNCOMPRESSED_BYTES:
            archive.close()
            raise InvalidPrivateText("EPUB exceeds the 64 MiB expansion limit")
        if not info.is_dir():
            if safe_name in info_by_name:
                archive.close()
                raise InvalidPrivateText("EPUB contains duplicate normalized ZIP paths")
            info_by_name[safe_name] = info

    return archive, info_by_name


def _read_archive_member(
    archive: zipfile.ZipFile,
    info_by_name: dict[str, zipfile.ZipInfo],
    path: str,
    label: str,
) -> bytes:
    info = info_by_name.get(path)
    if info is None:
        raise InvalidPrivateText(f"EPUB is missing {label}")
    try:
        return archive.read(info)
    except (RuntimeError, zipfile.BadZipFile, OSError) as error:
        raise InvalidPrivateText(f"Could not read EPUB {label}") from error


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_child_text(
    parent: ElementTree.Element | None, local_name: str
) -> str | None:
    if parent is None:
        return None
    for element in parent.iter():
        if _local_name(element.tag) == local_name:
            text = " ".join("".join(element.itertext()).split())
            if text:
                return text
    return None


class _SpineHTMLParser(HTMLParser):
    """Extract only reader-visible blocks; scripts and resources are ignored."""

    _BLOCK_TAGS = {"p", "li", "blockquote"}
    _HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
    _IGNORED_TAGS = {"script", "style", "noscript", "svg"}
    _VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.paragraphs: list[str] = []
        self.first_heading: str | None = None
        self.document_title: str | None = None
        self._ignored_depth = 0
        self._capture_tag: str | None = None
        self._capture_depth = 0
        self._capture_text: list[str] = []
        self._title_depth = 0
        self._title_text: list[str] = []
        self._heading_depth = 0
        self._heading_text: list[str] = []
        self._body_depth = 0
        self._body_text: list[str] = []

    @staticmethod
    def _clean(parts: list[str]) -> str:
        return " ".join("".join(parts).split())

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self._IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "body":
            self._body_depth += 1
        elif self._body_depth:
            if tag == "br":
                self._body_text.append("\n")
            elif tag in self._BLOCK_TAGS | self._HEADING_TAGS:
                self._body_text.append("\n")

        if tag == "title":
            self._title_depth += 1
            return
        if self._title_depth:
            return
        if tag in self._HEADING_TAGS and not self._heading_depth:
            self._heading_depth = 1
            self._heading_text = []
        elif self._heading_depth:
            self._heading_depth += 1

        if tag in self._BLOCK_TAGS and self._capture_tag is None:
            self._capture_tag = tag
            self._capture_depth = 1
            self._capture_text = []
        elif self._capture_tag is not None:
            if tag == "br":
                self._capture_text.append("\n")
            if tag not in self._VOID_TAGS:
                self._capture_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._VOID_TAGS:
            return
        if self._ignored_depth:
            if tag in self._IGNORED_TAGS:
                self._ignored_depth -= 1
            return
        if self._title_depth:
            if tag == "title":
                self._title_depth -= 1
                if not self._title_depth:
                    cleaned = self._clean(self._title_text)
                    self.document_title = cleaned or None
                    self._title_text = []
            return

        if self._heading_depth:
            self._heading_depth -= 1
            if not self._heading_depth and self.first_heading is None:
                cleaned = self._clean(self._heading_text)
                self.first_heading = cleaned or None
                self._heading_text = []

        if self._capture_tag is not None:
            self._capture_depth -= 1
            if not self._capture_depth:
                cleaned = self._clean(self._capture_text)
                if cleaned:
                    self.paragraphs.append(cleaned)
                self._capture_tag = None
                self._capture_text = []

        if tag == "body" and self._body_depth:
            self._body_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._title_depth:
            self._title_text.append(data)
            return
        if self._heading_depth:
            self._heading_text.append(data)
        if self._capture_tag is not None:
            self._capture_text.append(data)
        if self._body_depth:
            self._body_text.append(data)

    def fallback_paragraphs(self) -> list[str]:
        if self.paragraphs:
            return self.paragraphs
        cleaned = self._clean(self._body_text)
        return [cleaned] if cleaned else []


@dataclass
class _RawEpubSection:
    title: str
    spine_index: int
    href: str
    paragraphs: list[str]


def _decode_markup(data: bytes, label: str) -> str:
    _assert_safe_markup(data, label)
    # HTMLParser operates on Unicode. UTF-8 is the EPUB default; XML declarations
    # from common producers may still specify UTF-16.
    encodings = ["utf-8-sig"]
    declaration = data[:200].lower()
    if b"encoding='utf-16" in declaration or b'encoding="utf-16' in declaration:
        encodings.insert(0, "utf-16")
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise InvalidPrivateText(f"EPUB spine document is not valid Unicode: {label}")


def _parse_epub_document(request: EpubImportRequest) -> PrivateDocument:
    try:
        epub_bytes = base64.b64decode(request.content_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise InvalidPrivateText("EPUB content_base64 is not valid base64") from error
    if not epub_bytes:
        raise InvalidPrivateText("EPUB upload is empty")

    archive, info_by_name = _validate_epub_archive(epub_bytes)
    try:
        mimetype_info = info_by_name.get("mimetype")
        if mimetype_info is not None:
            mimetype = _read_archive_member(
                archive, info_by_name, "mimetype", "mimetype"
            )
            if mimetype.strip() != b"application/epub+zip":
                raise InvalidPrivateText("ZIP mimetype is not application/epub+zip")

        container_path = "META-INF/container.xml"
        container_root = _parse_xml(
            _read_archive_member(
                archive, info_by_name, container_path, "META-INF/container.xml"
            ),
            container_path,
        )
        rootfile = next(
            (
                node
                for node in container_root.iter()
                if _local_name(node.tag) == "rootfile"
            ),
            None,
        )
        if rootfile is None or not rootfile.attrib.get("full-path"):
            raise InvalidPrivateText("EPUB container has no OPF rootfile")
        opf_path = _safe_archive_path(
            rootfile.attrib["full-path"], "container rootfile"
        )
        opf_root = _parse_xml(
            _read_archive_member(archive, info_by_name, opf_path, "OPF package"),
            opf_path,
        )

        metadata = next(
            (
                child
                for child in opf_root
                if _local_name(child.tag) == "metadata"
            ),
            None,
        )
        manifest = next(
            (
                child
                for child in opf_root
                if _local_name(child.tag) == "manifest"
            ),
            None,
        )
        spine = next(
            (child for child in opf_root if _local_name(child.tag) == "spine"),
            None,
        )
        if manifest is None or spine is None:
            raise InvalidPrivateText("EPUB OPF is missing manifest or spine")

        manifest_items: dict[str, tuple[str, str]] = {}
        for item in manifest:
            if _local_name(item.tag) != "item":
                continue
            item_id = item.attrib.get("id", "").strip()
            href = item.attrib.get("href", "").strip()
            media_type = item.attrib.get("media-type", "").strip().lower()
            if item_id and href:
                if item_id in manifest_items:
                    raise InvalidPrivateText("EPUB manifest contains duplicate item ids")
                manifest_items[item_id] = (href, media_type)

        itemrefs = [
            itemref.attrib.get("idref", "").strip()
            for itemref in spine
            if _local_name(itemref.tag) == "itemref"
        ]
        itemrefs = [itemref for itemref in itemrefs if itemref]
        if not itemrefs:
            raise InvalidPrivateText("EPUB spine is empty")
        if len(itemrefs) > MAX_EPUB_SPINE_ITEMS:
            raise InvalidPrivateText("EPUB spine contains too many documents")

        raw_sections: list[_RawEpubSection] = []
        for spine_index, itemref in enumerate(itemrefs):
            manifest_item = manifest_items.get(itemref)
            if manifest_item is None:
                raise InvalidPrivateText("EPUB spine references a missing manifest item")
            href, media_type = manifest_item
            if media_type not in _EPUB_DOCUMENT_MEDIA_TYPES:
                continue
            resolved_path = _resolve_epub_href(opf_path, href)
            markup = _read_archive_member(
                archive, info_by_name, resolved_path, "spine document"
            )
            parser = _SpineHTMLParser()
            try:
                parser.feed(_decode_markup(markup, resolved_path))
                parser.close()
            except (UnicodeError, ValueError) as error:
                raise InvalidPrivateText(
                    f"Could not parse EPUB spine document: {resolved_path}"
                ) from error
            paragraphs = parser.fallback_paragraphs()
            if not paragraphs:
                continue
            raw_sections.append(
                _RawEpubSection(
                    title=(
                        parser.first_heading
                        or parser.document_title
                        or PurePosixPath(resolved_path).stem
                    ),
                    spine_index=spine_index,
                    href=resolved_path,
                    paragraphs=paragraphs,
                )
            )

        paragraph_count = sum(len(section.paragraphs) for section in raw_sections)
        if not paragraph_count:
            raise InvalidPrivateText("EPUB spine has no readable paragraphs")
        total_text_chars = sum(
            len(paragraph)
            for section in raw_sections
            for paragraph in section.paragraphs
        )
        if total_text_chars > MAX_EPUB_TEXT_CHARS:
            raise InvalidPrivateText(
                "EPUB readable text exceeds the 1,500,000-character limit"
            )

        sections: list[DocumentSection] = []
        global_ordinal = 0
        for section_ordinal, raw_section in enumerate(raw_sections):
            section_id = f"section_{section_ordinal}"
            paragraphs = []
            for paragraph_ordinal, text in enumerate(raw_section.paragraphs):
                paragraphs.append(
                    ParagraphAnchor(
                        id=_anchor_id(section_ordinal, paragraph_ordinal, text),
                        section_id=section_id,
                        ordinal=paragraph_ordinal,
                        text=text,
                        locator=DocumentLocator(
                            source_format=SourceFormat.EPUB,
                            section_index=section_ordinal,
                            paragraph_index=paragraph_ordinal,
                            spine_index=raw_section.spine_index,
                            href=raw_section.href,
                            progression_percent=_progression(
                                global_ordinal, paragraph_count
                            ),
                        ),
                    )
                )
                global_ordinal += 1
            sections.append(
                DocumentSection(
                    id=section_id,
                    title=raw_section.title,
                    level=1,
                    ordinal=section_ordinal,
                    paragraphs=paragraphs,
                )
            )

        opf_title = _first_child_text(metadata, "title")
        opf_author = _first_child_text(metadata, "creator")
        title = (request.title or opf_title or "未命名 EPUB").strip()
        author = (request.author or opf_author or "").strip() or None
        return PrivateDocument(
            id=_new_id("doc"),
            title=title,
            author=author,
            version_label=(
                request.version_label.strip() if request.version_label else None
            ),
            source_format=SourceFormat.EPUB,
            checksum_sha256=hashlib.sha256(epub_bytes).hexdigest(),
            char_count=total_text_chars,
            section_count=len(sections),
            paragraph_count=paragraph_count,
            sections=sections,
            epub_metadata=EpubMetadata(
                opf_path=opf_path,
                language=_first_child_text(metadata, "language"),
                identifier=_first_child_text(metadata, "identifier"),
                publisher=_first_child_text(metadata, "publisher"),
                publication_date=_first_child_text(metadata, "date"),
            ),
        )
    finally:
        archive.close()


def _scope_contract(request: PromptExplorationRequest) -> ScopeContract:
    missing = []
    starter_questions = []
    if not request.user_supplied_time_range:
        missing.append("time_range")
        starter_questions.append("你希望从哪个时间点开始、到哪个时间点结束？")
    if not request.user_supplied_geography:
        missing.append("geography")
        starter_questions.append("这次探索应优先落在哪些地点或区域？")
    if not request.user_supplied_threads:
        missing.append("narrative_threads")
        starter_questions.append("你最想先追踪人物、事件、制度还是观念中的哪条主线？")
    if not missing:
        starter_questions.append("哪些节点必须回到原始材料核验？")
    return ScopeContract(
        original_question=request.prompt,
        time_range=(
            request.user_supplied_time_range.strip()
            if request.user_supplied_time_range
            else None
        ),
        geography=list(dict.fromkeys(request.user_supplied_geography)),
        narrative_threads=list(dict.fromkeys(request.user_supplied_threads)),
        fields_needing_confirmation=missing,
        starter_questions=starter_questions,
    )


@dataclass
class _SessionRecord:
    snapshot: ExplorationSnapshot
    last_access_monotonic: float


class ExplorationStore:
    """Thread-safe, bounded in-memory store for private explorations."""

    def __init__(
        self,
        max_sessions: int = 64,
        ttl_seconds: float = 6 * 60 * 60,
        max_total_source_chars: int = DEFAULT_MAX_TOTAL_SOURCE_CHARS,
    ):
        if max_sessions < 1:
            raise ValueError("max_sessions must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_total_source_chars < 1:
            raise ValueError("max_total_source_chars must be positive")
        self._max_sessions = max_sessions
        self._ttl_seconds = ttl_seconds
        self._max_total_source_chars = max_total_source_chars
        self._records: dict[str, _SessionRecord] = {}
        self._lock = threading.RLock()

    def _purge_expired(self, now: float) -> None:
        expired = [
            exploration_id
            for exploration_id, record in self._records.items()
            if now - record.last_access_monotonic > self._ttl_seconds
        ]
        for exploration_id in expired:
            del self._records[exploration_id]

    @staticmethod
    def _source_char_count(snapshot: ExplorationSnapshot) -> int:
        return snapshot.document.char_count if snapshot.document is not None else 0

    def _evict_for(self, incoming_source_chars: int) -> None:
        current_source_chars = sum(
            self._source_char_count(record.snapshot)
            for record in self._records.values()
        )
        while self._records and (
            len(self._records) >= self._max_sessions
            or current_source_chars + incoming_source_chars
            > self._max_total_source_chars
        ):
            oldest_id = min(
                self._records,
                key=lambda exploration_id: self._records[
                    exploration_id
                ].last_access_monotonic,
            )
            current_source_chars -= self._source_char_count(
                self._records[oldest_id].snapshot
            )
            del self._records[oldest_id]

    def _boundary(self) -> SessionBoundary:
        return SessionBoundary(
            ttl_seconds=self._ttl_seconds,
            max_sessions=self._max_sessions,
            max_total_source_chars=self._max_total_source_chars,
        )

    def _evict_if_full(self) -> None:
        """Backward-compatible helper retained for callers outside this module."""
        if len(self._records) < self._max_sessions:
            return
        oldest_id = min(
            self._records,
            key=lambda exploration_id: self._records[
                exploration_id
            ].last_access_monotonic,
        )
        del self._records[oldest_id]

    def _record(self, exploration_id: str) -> _SessionRecord:
        now = time.monotonic()
        self._purge_expired(now)
        record = self._records.get(exploration_id)
        if record is None:
            raise ExplorationNotFound(f"Exploration {exploration_id} not found")
        record.last_access_monotonic = now
        return record

    def _save_new(self, snapshot: ExplorationSnapshot) -> ExplorationSnapshot:
        with self._lock:
            monotonic_now = time.monotonic()
            self._purge_expired(monotonic_now)
            incoming_source_chars = self._source_char_count(snapshot)
            if incoming_source_chars > self._max_total_source_chars:
                raise InvalidPrivateText(
                    "Imported source exceeds this process store's character budget"
                )
            self._evict_for(incoming_source_chars)
            self._records[snapshot.id] = _SessionRecord(
                snapshot=snapshot,
                last_access_monotonic=monotonic_now,
            )
            return self._copy(snapshot)

    @staticmethod
    def _copy(snapshot: ExplorationSnapshot) -> ExplorationSnapshot:
        return snapshot.model_copy(deep=True)

    @staticmethod
    def _assert_revision(snapshot: ExplorationSnapshot, base_revision: int) -> None:
        if snapshot.revision != base_revision:
            raise RevisionConflict(base_revision, snapshot.revision)

    @staticmethod
    def _anchors(snapshot: ExplorationSnapshot) -> dict[str, ParagraphAnchor]:
        if snapshot.document is None:
            return {}
        return {
            paragraph.id: paragraph
            for section in snapshot.document.sections
            for paragraph in section.paragraphs
        }

    def create(self, request: ImportExplorationRequest) -> ExplorationSnapshot:
        return self._create_book(_parse_text_document(request), request.brief)

    def create_epub(self, request: EpubImportRequest) -> ExplorationSnapshot:
        return self._create_book(_parse_epub_document(request), request.brief)

    def _create_book(
        self, document: PrivateDocument, brief: ExplorationBrief
    ) -> ExplorationSnapshot:
        now = _utc_now()
        first_anchor = document.sections[0].paragraphs[0]
        snapshot = ExplorationSnapshot(
            id=_new_id("exploration"),
            revision=1,
            created_at=now,
            updated_at=now,
            session_boundary=self._boundary(),
            entry_mode="book",
            document=document,
            brief=brief.model_copy(deep=True),
            active_anchor_id=first_anchor.id,
            reading_progress=ReadingProgress(
                anchor_id=first_anchor.id,
                progression_percent=first_anchor.locator.progression_percent,
                locator=first_anchor.locator.model_copy(deep=True),
                updated_at=now,
            ),
        )
        return self._save_new(snapshot)

    def create_from_prompt(
        self, request: PromptExplorationRequest
    ) -> ExplorationSnapshot:
        now = _utc_now()
        contract = _scope_contract(request)
        claim = Claim(
            id=_new_id("claim"),
            text=request.prompt,
            claim_kind="research_question",
            evidence_level=EvidenceLevel.EVIDENCE_GAP,
            provenance="prompt_scope_scaffold",
        )
        scene = Scene(
            id=_new_id("scene"),
            title="研究问题",
            summary=request.prompt,
            temporal_label=contract.time_range,
            temporal_precision=(
                "user_supplied" if contract.time_range else "unknown"
            ),
            map_state=MapState.NO_LOCATION,
            claim_ids=[claim.id],
            evidence_level=EvidenceLevel.EVIDENCE_GAP,
        )
        snapshot = ExplorationSnapshot(
            id=_new_id("exploration"),
            revision=1,
            created_at=now,
            updated_at=now,
            session_boundary=self._boundary(),
            entry_mode="prompt",
            brief=ExplorationBrief(
                question=request.prompt,
                time_range=contract.time_range,
                geography=contract.geography,
                threads=contract.narrative_threads,
                status="draft",
            ),
            scope_contract=contract,
            active_scene_id=scene.id,
            scenes=[scene],
            claims=[claim],
            composer_entries=[
                ComposerEntry(
                    id=_new_id("entry"),
                    intent="question",
                    message=request.prompt,
                    created_at=now,
                    processing_status="needs_model",
                )
            ],
        )
        return self._save_new(snapshot)

    def get(self, exploration_id: str) -> ExplorationSnapshot:
        with self._lock:
            return self._copy(self._record(exploration_id).snapshot)

    def delete(self, exploration_id: str) -> None:
        with self._lock:
            self._record(exploration_id)
            del self._records[exploration_id]

    def compose(
        self,
        exploration_id: str,
        request: ComposeRequest,
    ) -> ComposerMutationResult:
        with self._lock:
            record = self._record(exploration_id)
            snapshot = record.snapshot
            self._assert_revision(snapshot, request.base_revision)
            anchors = self._anchors(snapshot)
            anchor_ids = list(dict.fromkeys(request.anchor_ids))
            unknown = [anchor_id for anchor_id in anchor_ids if anchor_id not in anchors]
            if unknown:
                raise UnknownAnchor(f"Unknown paragraph anchors: {', '.join(unknown)}")

            mutation_id = _new_id("mutation")
            entry = ComposerEntry(
                id=mutation_id,
                intent=request.intent,
                message=request.message,
                anchor_ids=anchor_ids,
                created_at=_utc_now(),
                processing_status=(
                    "structured_proposal"
                    if request.intent == "propose_scene"
                    else "needs_model"
                    if request.intent == "request_deep_analysis"
                    else "recorded_no_llm"
                ),
            )
            snapshot.composer_entries.append(entry)
            outcome = "recorded_no_llm"

            if request.intent == "propose_scene":
                claim_id = _new_id("claim")
                claim = Claim(
                    id=claim_id,
                    text=request.message,
                    source_anchor_ids=anchor_ids,
                )
                snapshot.claims.append(claim)

                evidence_ids = []
                if snapshot.document is not None:
                    for anchor_id in anchor_ids:
                        paragraph = anchors[anchor_id]
                        evidence = Evidence(
                            id=_new_id("evidence"),
                            claim_id=claim_id,
                            locator=SourceLocator(
                                document_id=snapshot.document.id,
                                section_id=paragraph.section_id,
                                paragraph_id=paragraph.id,
                                document_locator=paragraph.locator.model_copy(deep=True),
                            ),
                        )
                        snapshot.evidence.append(evidence)
                        evidence_ids.append(evidence.id)

                scene = Scene(
                    id=_new_id("scene"),
                    title=(request.scene_title or "待命名 Scene").strip(),
                    summary=request.message,
                    temporal_label=(
                        request.temporal_label.strip()
                        if request.temporal_label
                        else None
                    ),
                    temporal_precision=(
                        "user_supplied" if request.temporal_label else "unknown"
                    ),
                    map_state=MapState.NO_LOCATION,
                    claim_ids=[claim_id],
                    evidence_ids=evidence_ids,
                    evidence_level=(
                        EvidenceLevel.MODEL_INFERENCE
                        if evidence_ids
                        else EvidenceLevel.EVIDENCE_GAP
                    ),
                )
                snapshot.scenes.append(scene)
                snapshot.active_scene_id = scene.id
                if anchor_ids:
                    snapshot.active_anchor_id = anchor_ids[0]
                outcome = "scene_proposed"

            elif request.intent == "request_deep_analysis":
                source_locators = []
                if snapshot.document is not None:
                    source_locators = [
                        SourceLocator(
                            document_id=snapshot.document.id,
                            section_id=anchors[anchor_id].section_id,
                            paragraph_id=anchors[anchor_id].id,
                            document_locator=anchors[
                                anchor_id
                            ].locator.model_copy(deep=True),
                        )
                        for anchor_id in anchor_ids
                    ]
                snapshot.analysis_queue.append(
                    AnalysisQueueItem(
                        id=_new_id("analysis"),
                        request_text=request.message,
                        anchor_ids=anchor_ids,
                        evidence_boundary=(
                            "selected_book_anchors"
                            if anchor_ids
                            else "evidence_gap"
                        ),
                        requested_views=list(dict.fromkeys(request.requested_views)),
                        prompt_contract=build_book_argument_prompt_contract(
                            request_text=request.message,
                            source_locators=source_locators,
                            requested_views=request.requested_views,
                        ),
                        created_at=_utc_now(),
                    )
                )
                outcome = "analysis_queued"

            snapshot.revision += 1
            snapshot.updated_at = _utc_now()
            return ComposerMutationResult(
                mutation_id=mutation_id,
                outcome=outcome,
                snapshot=self._copy(snapshot),
            )

    def mutate(
        self,
        exploration_id: str,
        mutation: ExplorationMutation,
    ) -> ExplorationSnapshot:
        with self._lock:
            record = self._record(exploration_id)
            snapshot = record.snapshot
            self._assert_revision(snapshot, mutation.base_revision)

            if isinstance(mutation, SetActiveAnchorMutation):
                if mutation.anchor_id not in self._anchors(snapshot):
                    raise UnknownAnchor(
                        f"Unknown paragraph anchor: {mutation.anchor_id}"
                    )
                snapshot.active_anchor_id = mutation.anchor_id
            elif isinstance(mutation, UpdateReadingProgressMutation):
                paragraph = self._anchors(snapshot).get(mutation.anchor_id)
                if paragraph is None:
                    raise UnknownAnchor(
                        f"Unknown paragraph anchor: {mutation.anchor_id}"
                    )
                now = _utc_now()
                snapshot.active_anchor_id = paragraph.id
                snapshot.reading_progress = ReadingProgress(
                    anchor_id=paragraph.id,
                    progression_percent=paragraph.locator.progression_percent,
                    locator=paragraph.locator.model_copy(deep=True),
                    updated_at=now,
                )
            elif isinstance(mutation, SyncExternalReadingMutation):
                snapshot.external_reading_bridge = ExternalReadingBridge(
                    provider=mutation.provider,
                    url=mutation.url,
                    external_locator=mutation.external_locator,
                    user_provided_excerpt=mutation.user_provided_excerpt,
                    updated_at=_utc_now(),
                )
            elif isinstance(mutation, UpdateScopeContractMutation):
                if snapshot.scope_contract is None:
                    raise InvalidPrivateText(
                        "This exploration has no prompt scope contract to update"
                    )
                current = snapshot.scope_contract
                refreshed = _scope_contract(
                    PromptExplorationRequest(
                        prompt=current.original_question,
                        user_supplied_time_range=(
                            mutation.user_supplied_time_range
                            if mutation.user_supplied_time_range is not None
                            else current.time_range
                        ),
                        user_supplied_geography=(
                            mutation.user_supplied_geography
                            if mutation.user_supplied_geography is not None
                            else current.geography
                        ),
                        user_supplied_threads=(
                            mutation.user_supplied_threads
                            if mutation.user_supplied_threads is not None
                            else current.narrative_threads
                        ),
                    )
                )
                snapshot.scope_contract = refreshed
                snapshot.brief.time_range = refreshed.time_range
                snapshot.brief.geography = refreshed.geography
                snapshot.brief.threads = refreshed.narrative_threads
                research_scene = next(
                    (
                        scene
                        for scene in snapshot.scenes
                        if scene.title == "研究问题"
                    ),
                    None,
                )
                if research_scene is not None:
                    research_scene.temporal_label = refreshed.time_range
                    research_scene.temporal_precision = (
                        "user_supplied" if refreshed.time_range else "unknown"
                    )
            elif isinstance(mutation, SetActiveSceneMutation):
                if not any(scene.id == mutation.scene_id for scene in snapshot.scenes):
                    raise UnknownScene(f"Unknown Scene: {mutation.scene_id}")
                snapshot.active_scene_id = mutation.scene_id
            elif isinstance(mutation, ReviewSceneMutation):
                scene = next(
                    (
                        candidate
                        for candidate in snapshot.scenes
                        if candidate.id == mutation.scene_id
                    ),
                    None,
                )
                if scene is None:
                    raise UnknownScene(f"Unknown Scene: {mutation.scene_id}")
                scene.review_status = ReviewStatus(mutation.decision)

            snapshot.revision += 1
            snapshot.updated_at = _utc_now()
            return self._copy(snapshot)

    def clear(self) -> None:
        """Clear process-local sessions; intended for tests and process shutdown."""
        with self._lock:
            self._records.clear()


exploration_store = ExplorationStore()
