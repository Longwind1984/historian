"""Deterministic, claim-free document shape signals for exploration v6.

The profiler needs to decide *how* to analyse a book before a model sees any
source packet.  This module therefore emits only counts, ratios and opaque
anchor locators.  Regex matches are deliberately treated as morphological
signals: a year-shaped token is not a verified date, and a place-shaped token
is not a resolved location.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from statistics import fmean, pvariance
from typing import Iterable

from app.schemas.exploration import PrivateDocument

from .contracts import (
    AnchorBatchScope,
    BookMetadataSignals,
    BookStructureSignals,
    BookType,
    LanguageRegister,
    PlanningScope,
    RightsAndPrivacy,
    SectionSignals,
)


_SENTENCE = re.compile(r"[。！？!?；;]+")
_TIME_SHAPE = re.compile(
    r"(?:\d{3,4}\s*年|\d{1,2}\s*月|\d{1,2}\s*日|"
    r"同年|次年|翌年|此前|此后|其后|当时|初年|末年|春|夏|秋|冬)"
)
_PLACE_SHAPE = re.compile(
    r"[\u3400-\u9fff]{1,8}(?:州|郡|县|府|京|都|城|关|镇|河|山|道|路|省|村)"
)
_ACTOR_SHAPE = re.compile(
    r"(?:[\u3400-\u9fff]{2,4}(?:帝|王|公|将军|宰相|先生|女士)|"
    r"(?:皇帝|官员|军队|士兵|百姓|使者|作者|学者|他|她|其人))"
)
_ACTION_SHAPE = re.compile(
    r"(?:率|领|攻|守|进|退|抵达|离开|迁|任|罢|杀|战|围|逃|返回|"
    r"发布|建立|废除|改革|继位|去世|出生|会见|命令|行动|发生)"
)
_ARGUMENT_SHAPE = re.compile(
    r"(?:因为|由于|因此|所以|可见|表明|说明|意味着|认为|主张|解释|"
    r"原因|结果|机制|证据|论证|然而|但是|尽管|并非|不能|值得注意)"
)
_CONCEPT_SHAPE = re.compile(
    r"(?:制度|结构|权力|国家|社会|政治|经济|文化|思想|组织|政策|"
    r"治理|机制|阶层|财政|军事|宗教|观念|理论)"
)
_CITATION_SHAPE = re.compile(
    r"(?:\[[0-9０-９]+\]|［[0-9０-９]+］|\([0-9０-９]+\)|"
    r"（[0-9０-９]+）|第\s*\d+\s*页|参见|引自|注\s*[0-9０-９]+)"
)
_SPEAKER_SHAPE = re.compile(r"(?:曰|说|写道|指出|认为|回忆|记载)[：,:，\s]*[“\"]")
_SOURCE_BOUNDARY = re.compile(r"(?:文献|档案|书信|日记|奏折|诏书|原文|引文)[：:]|[“\"]")
_PERIOD_COMPARISON = re.compile(r"(?:相比|相较|此前|此后|前期|后期|同期|不同阶段|从.+到)")
_FOOTNOTE = re.compile(r"(?:\[[0-9０-９]+\]|［[0-9０-９]+］|注\s*[0-9０-９]+)")
_TABLE_FIGURE = re.compile(r"(?:\|[^\n]+\||图\s*[0-9０-９]+|表\s*[0-9０-９]+)")
_ENTRY = re.compile(r"(?:^|\n)\s*[\u3400-\u9fffA-Za-z0-9]{1,30}[：:]", re.MULTILINE)


@dataclass(frozen=True)
class DocumentSignalBundle:
    """Safe profiler inputs and planning locators; never contains source text."""

    metadata: BookMetadataSignals
    structure: BookStructureSignals
    sections: tuple[SectionSignals, ...]
    planning_scope: PlanningScope
    anchor_ids: tuple[str, ...]


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)


def _density(pattern: re.Pattern[str], text: str, opportunities: int) -> float:
    return _clamp(len(pattern.findall(text)) / max(opportunities, 1))


def _sentences(text: str) -> int:
    return max(1, len(_SENTENCE.findall(text)))


def _title_subject(title: str) -> str | None:
    """Return a title-shaped subject token, not an asserted person identity."""

    compact = re.sub(r"[《》〈〉\s]", "", title)
    match = re.search(r"([\u3400-\u9fff]{2,8})(?:传|生平|年谱|的一生)$", compact)
    return match.group(1) if match else None


def _section_vector(section: SectionSignals) -> tuple[float, ...]:
    return (
        section.chronology_density,
        section.geography_density,
        section.actor_density,
        section.action_sequence_density,
        section.argument_density,
        section.concept_density,
        section.citation_density,
        section.speaker_change_density,
    )


def _mode_variance(sections: Iterable[SectionSignals]) -> float:
    rows = [_section_vector(section) for section in sections]
    if len(rows) < 2:
        return 0.0
    return _clamp(fmean(pvariance(column) for column in zip(*rows)) * 8)


def _batch_id(section_id: str, anchor_ids: tuple[str, ...]) -> str:
    digest = sha256((section_id + "\0" + "\0".join(anchor_ids)).encode()).hexdigest()
    return f"ab_{digest[:20]}"


def derive_document_signals(
    document: PrivateDocument,
    *,
    anchor_batch_size: int = 24,
    anchor_batch_char_limit: int = 36_000,
    catalog_type_hints: tuple[BookType, ...] = (),
) -> DocumentSignalBundle:
    """Derive complete section signals and stable chapter/batch scopes.

    ``catalog_type_hints`` is explicit caller metadata.  It is never inferred
    from claims in the body and is primarily useful when an import format has
    trustworthy catalogue information.
    """

    if not 1 <= anchor_batch_size <= 80:
        raise ValueError("anchor_batch_size must be between 1 and 80")
    if not 4_000 <= anchor_batch_char_limit <= 200_000:
        raise ValueError("anchor_batch_char_limit must be between 4000 and 200000")
    nonempty = [section for section in document.sections if section.paragraphs]
    if not nonempty:
        raise ValueError("document must contain at least one anchored section")

    section_signals: list[SectionSignals] = []
    batches: list[AnchorBatchScope] = []
    all_anchor_ids: list[str] = []
    all_text: list[str] = []
    title_subject = _title_subject(document.title)
    subject_sections = 0

    for section_index, section in enumerate(nonempty):
        anchor_ids = tuple(paragraph.id for paragraph in section.paragraphs)
        text = "\n".join(paragraph.text for paragraph in section.paragraphs)
        sentence_count = _sentences(text)
        paragraph_count = len(section.paragraphs)
        if title_subject and title_subject in text:
            subject_sections += 1
        signal = SectionSignals(
            section_id=section.id,
            section_index=section_index,
            anchor_ids=anchor_ids,
            chronology_density=_density(_TIME_SHAPE, text, sentence_count),
            geography_density=_density(_PLACE_SHAPE, text, sentence_count),
            actor_density=_density(_ACTOR_SHAPE, text, sentence_count),
            action_sequence_density=_density(_ACTION_SHAPE, text, sentence_count * 2),
            argument_density=_density(_ARGUMENT_SHAPE, text, sentence_count * 2),
            concept_density=_density(_CONCEPT_SHAPE, text, sentence_count * 2),
            citation_density=_density(_CITATION_SHAPE, text, paragraph_count),
            speaker_change_density=_density(_SPEAKER_SHAPE, text, sentence_count),
        )
        section_signals.append(signal)
        all_anchor_ids.extend(anchor_ids)
        all_text.append(text)
        batch_anchor_ids: list[str] = []
        batch_chars = 0
        for paragraph in section.paragraphs:
            would_overflow = batch_anchor_ids and (
                len(batch_anchor_ids) >= anchor_batch_size
                or batch_chars + len(paragraph.text) > anchor_batch_char_limit
            )
            if would_overflow:
                bounded_ids = tuple(batch_anchor_ids)
                batches.append(
                    AnchorBatchScope(
                        id=_batch_id(section.id, bounded_ids),
                        chapter_id=section.id,
                        anchor_ids=bounded_ids,
                    )
                )
                batch_anchor_ids = []
                batch_chars = 0
            batch_anchor_ids.append(paragraph.id)
            batch_chars += len(paragraph.text)
        if batch_anchor_ids:
            bounded_ids = tuple(batch_anchor_ids)
            batches.append(
                AnchorBatchScope(
                    id=_batch_id(section.id, bounded_ids),
                    chapter_id=section.id,
                    anchor_ids=bounded_ids,
                )
            )

    if len(all_anchor_ids) != len(set(all_anchor_ids)):
        raise ValueError("paragraph anchor IDs must be unique across the document")

    joined = "\n".join(all_text)
    paragraph_count = sum(len(section.paragraphs) for section in nonempty)
    character_count = sum(len(text) for text in all_text)
    section_count = len(nonempty)
    metadata_language = (
        document.epub_metadata.language
        if document.epub_metadata and document.epub_metadata.language
        else "zh"
    )
    metadata = BookMetadataSignals(
        language=metadata_language,
        creator_count=int(bool(document.author)),
        editor_or_compiler_present=bool(re.search(r"(?:主编|编著|编者)", document.title)),
        catalog_type_hints=catalog_type_hints,
        language_register=LanguageRegister.UNKNOWN,
        rights_and_privacy=RightsAndPrivacy.LOCAL_PRIVATE,
    )
    structure = BookStructureSignals(
        section_count=section_count,
        paragraph_count=paragraph_count,
        heading_depth=max(section.level for section in nonempty),
        average_paragraph_chars=round(character_count / max(paragraph_count, 1), 3),
        footnote_density=_clamp(len(_FOOTNOTE.findall(joined)) / max(paragraph_count, 1)),
        table_figure_density=_clamp(len(_TABLE_FIGURE.findall(joined)) / max(paragraph_count, 1)),
        entry_structure_density=_clamp(len(_ENTRY.findall(joined)) / max(paragraph_count, 1)),
        section_mode_variance=_mode_variance(section_signals),
        named_subject_continuity=_clamp(subject_sections / section_count),
        cross_period_comparison_density=_clamp(
            len(_PERIOD_COMPARISON.findall(joined)) / max(_sentences(joined), 1)
        ),
        source_boundary_density=_clamp(
            len(_SOURCE_BOUNDARY.findall(joined)) / max(_sentences(joined), 1)
        ),
    )
    return DocumentSignalBundle(
        metadata=metadata,
        structure=structure,
        sections=tuple(section_signals),
        planning_scope=PlanningScope(
            chapter_ids=tuple(section.id for section in nonempty),
            anchor_batches=tuple(batches),
        ),
        anchor_ids=tuple(all_anchor_ids),
    )


__all__ = ["DocumentSignalBundle", "derive_document_signals"]
