"""Deterministic, source-text-free book profiling.

Upstream parsing computes numeric shape signals locally. This module samples
sections across the whole book and classifies the workflow route without an
LLM, summaries, or historical assertions.
"""

from __future__ import annotations

from statistics import fmean

from .contracts import (
    BookMetadataSignals,
    BookProfile,
    BookStructureSignals,
    BookType,
    BookTypeScore,
    DiscourseMode,
    ProfileTrait,
    ProfileDimensions,
    ProfileUncertainty,
    SampleStratum,
    SectionSignals,
    Sha256Checksum,
    SourceNature,
    StratifiedSample,
)


def _sample_indices(section_count: int, max_samples: int) -> list[int]:
    if section_count <= max_samples:
        return list(range(section_count))
    if max_samples == 1:
        return [section_count // 2]
    return sorted(
        {
            round(position * (section_count - 1) / (max_samples - 1))
            for position in range(max_samples)
        }
    )


def _stratum(index: int, section_count: int) -> SampleStratum:
    relative = index / max(section_count - 1, 1)
    if relative < 1 / 3:
        return SampleStratum.OPENING
    if relative > 2 / 3:
        return SampleStratum.CLOSING
    return SampleStratum.MIDDLE


def select_stratified_samples(
    sections: list[SectionSignals] | tuple[SectionSignals, ...],
    *,
    max_samples: int = 9,
) -> tuple[StratifiedSample, ...]:
    """Choose stable samples spanning opening, middle, closing and chapters."""

    if not sections:
        raise ValueError("at least one section signal is required")
    if max_samples < 1:
        raise ValueError("max_samples must be positive")
    if max_samples < 3 and len(sections) >= 3:
        raise ValueError("max_samples must be at least 3 for a multi-section book")
    ordered = sorted(sections, key=lambda section: section.section_index)
    indices = [section.section_index for section in ordered]
    if len(indices) != len(set(indices)):
        raise ValueError("section indexes must be unique")

    selected_positions = _sample_indices(len(ordered), min(max_samples, len(ordered)))
    return tuple(
        StratifiedSample(
            **section.model_dump(exclude={"section_index"}),
            section_index=section.section_index,
            stratum=_stratum(position, len(ordered)),
        )
        for position in selected_positions
        for section in [ordered[position]]
    )


def _mean(samples: tuple[StratifiedSample, ...], field: str) -> float:
    return round(fmean(float(getattr(sample, field)) for sample in samples), 6)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)


def _profile_dimensions(
    structure: BookStructureSignals,
    samples: tuple[StratifiedSample, ...],
) -> ProfileDimensions:
    return ProfileDimensions(
        chronology_density=_mean(samples, "chronology_density"),
        geography_density=_mean(samples, "geography_density"),
        actor_network_density=_mean(samples, "actor_density"),
        action_sequence_density=_mean(samples, "action_sequence_density"),
        argument_density=_mean(samples, "argument_density"),
        concept_density=_mean(samples, "concept_density"),
        citation_density=_clamp(
            (_mean(samples, "citation_density") + structure.footnote_density) / 2
        ),
        speaker_change_density=_mean(samples, "speaker_change_density"),
        structure_quality=_clamp(
            0.45
            + min(structure.heading_depth, 4) * 0.08
            + min(structure.section_count / 20, 1) * 0.15
            - structure.section_mode_variance * 0.2
        ),
        locator_quality=_clamp(
            0.6
            + min(structure.heading_depth, 3) * 0.1
            + min(structure.section_count / 30, 1) * 0.1
        ),
    )


def _type_scores(
    metadata: BookMetadataSignals,
    structure: BookStructureSignals,
    dimensions: ProfileDimensions,
) -> dict[BookType, float]:
    scores = {
        BookType.EVENT_NARRATIVE: (
            0.30 * dimensions.chronology_density
            + 0.22 * dimensions.action_sequence_density
            + 0.18 * dimensions.geography_density
            + 0.15 * dimensions.actor_network_density
            + 0.15 * (1 - dimensions.argument_density)
        ),
        BookType.ARGUMENTATIVE_MONOGRAPH: (
            0.47 * dimensions.argument_density
            + 0.23 * dimensions.citation_density
            + 0.20 * dimensions.concept_density
            + 0.10 * (1 - structure.source_boundary_density)
        ),
        BookType.BIOGRAPHY_MICROHISTORY: (
            0.45 * structure.named_subject_continuity
            + 0.20 * dimensions.actor_network_density
            + 0.15 * dimensions.chronology_density
            + 0.10 * dimensions.geography_density
            + 0.10 * dimensions.action_sequence_density
        ),
        BookType.INSTITUTIONAL_THEMATIC: (
            0.34 * dimensions.concept_density
            + 0.28 * structure.cross_period_comparison_density
            + 0.20 * dimensions.argument_density
            + 0.10 * dimensions.chronology_density
            + 0.08 * dimensions.citation_density
        ),
        BookType.SOURCE_COLLECTION: (
            0.32 * structure.source_boundary_density
            + 0.26 * dimensions.speaker_change_density
            + 0.20 * dimensions.citation_density
            + 0.12 * float(metadata.editor_or_compiler_present)
            + 0.10 * min(metadata.creator_count / 4, 1)
        ),
        BookType.REFERENCE_ATLAS: (
            0.38 * structure.entry_structure_density
            + 0.32 * structure.table_figure_density
            + 0.16 * dimensions.structure_quality
            + 0.14 * (1 - dimensions.action_sequence_density)
        ),
        BookType.MIXED: (
            0.70 * structure.section_mode_variance
            + 0.15 * min(dimensions.argument_density, dimensions.action_sequence_density)
            + 0.15 * min(dimensions.concept_density, dimensions.actor_network_density)
        ),
    }
    for hint in metadata.catalog_type_hints:
        scores[hint] += 0.12
    return {book_type: _clamp(score) for book_type, score in scores.items()}


def _traits(
    structure: BookStructureSignals,
    dimensions: ProfileDimensions,
) -> tuple[ProfileTrait, ...]:
    candidates = (
        (ProfileTrait.CHRONOLOGY_DENSE, dimensions.chronology_density >= 0.6),
        (ProfileTrait.GEOGRAPHY_DENSE, dimensions.geography_density >= 0.6),
        (ProfileTrait.ACTOR_NETWORK_DENSE, dimensions.actor_network_density >= 0.6),
        (ProfileTrait.ARGUMENT_DENSE, dimensions.argument_density >= 0.6),
        (ProfileTrait.CITATION_DENSE, dimensions.citation_density >= 0.6),
        (ProfileTrait.HIGHLY_STRUCTURED, dimensions.structure_quality >= 0.72),
        (
            ProfileTrait.HETEROGENEOUS_SECTIONS,
            structure.section_mode_variance >= 0.65,
        ),
    )
    return tuple(trait for trait, selected in candidates if selected)


def _discourse_modes(primary_type: BookType) -> tuple[DiscourseMode, ...]:
    return {
        BookType.EVENT_NARRATIVE: (DiscourseMode.NARRATIVE,),
        BookType.ARGUMENTATIVE_MONOGRAPH: (DiscourseMode.ANALYTIC,),
        BookType.BIOGRAPHY_MICROHISTORY: (
            DiscourseMode.NARRATIVE,
            DiscourseMode.ANALYTIC,
        ),
        BookType.INSTITUTIONAL_THEMATIC: (DiscourseMode.ANALYTIC,),
        BookType.SOURCE_COLLECTION: (DiscourseMode.DOCUMENTARY,),
        BookType.REFERENCE_ATLAS: (DiscourseMode.REFERENCE,),
        BookType.MIXED: (DiscourseMode.MIXED,),
    }[primary_type]


def _source_natures(
    primary_type: BookType,
    metadata: BookMetadataSignals,
) -> tuple[SourceNature, ...]:
    if metadata.source_nature_hints:
        return tuple(dict.fromkeys(metadata.source_nature_hints))
    return {
        BookType.SOURCE_COLLECTION: (SourceNature.EDITED_COLLECTION,),
        BookType.REFERENCE_ATLAS: (SourceNature.REFERENCE_WORK,),
        BookType.MIXED: (SourceNature.MIXED,),
    }.get(primary_type, (SourceNature.SECONDARY_SYNTHESIS,))


def build_book_profile(
    *,
    source_checksum: Sha256Checksum,
    metadata: BookMetadataSignals,
    structure: BookStructureSignals,
    section_signals: list[SectionSignals] | tuple[SectionSignals, ...],
    profile_revision: int = 1,
    max_samples: int = 9,
) -> BookProfile:
    """Build a repeatable profile from local metadata and numeric signals only."""

    if len(section_signals) != structure.section_count:
        raise ValueError("section signals must cover every parsed section")
    samples = select_stratified_samples(section_signals, max_samples=max_samples)
    dimensions = _profile_dimensions(structure, samples)
    scores = _type_scores(metadata, structure, dimensions)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0].value))
    primary_type = ranked[0][0]
    score_gap = ranked[0][1] - ranked[1][1]

    if structure.section_mode_variance >= 0.72 and score_gap < 0.18:
        primary_type = BookType.MIXED

    primary_score = scores[primary_type]
    confidence = _clamp(0.50 + primary_score * 0.35 + min(score_gap, 0.3) * 0.5)
    secondary_types = tuple(
        book_type
        for book_type, score in ranked
        if book_type != primary_type and score >= max(0.35, primary_score - 0.16)
    )[:2]

    uncertainties: list[ProfileUncertainty] = []
    if score_gap < 0.08:
        uncertainties.append(
            ProfileUncertainty(code="close_type_scores", affects_routing=True)
        )
    if structure.section_count < 3:
        uncertainties.append(
            ProfileUncertainty(code="insufficient_sections", affects_routing=False)
        )
    if dimensions.locator_quality < 0.65:
        uncertainties.append(
            ProfileUncertainty(code="weak_locator_quality", affects_routing=True)
        )
    if structure.section_mode_variance >= 0.65:
        uncertainties.append(
            ProfileUncertainty(code="high_section_variance", affects_routing=True)
        )

    type_scores = tuple(
        BookTypeScore(book_type=book_type, score=scores[book_type])
        for book_type in BookType
    )
    return BookProfile(
        source_checksum=source_checksum,
        profile_revision=profile_revision,
        primary_type=primary_type,
        secondary_types=secondary_types,
        secondary_traits=_traits(structure, dimensions),
        discourse_modes=_discourse_modes(primary_type),
        source_natures=_source_natures(primary_type, metadata),
        classification_confidence=confidence,
        dimensions=dimensions,
        type_scores=type_scores,
        samples=samples,
        metadata=metadata,
        structure=structure,
        uncertainties=tuple(uncertainties),
    )
