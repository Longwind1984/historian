"""Deterministic resolver from source labels to reviewed history-kb places."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
import re

from .passes import VerifiedLocation


_SPACE = re.compile(r"\s+")


def _normalise_label(value: str) -> str:
    return _SPACE.sub("", value).strip("·・，,。.;；（）()[]【】")


class ReviewedPlaceResolver:
    """Resolve only unique exact names/aliases with recorded coordinates."""

    def __init__(self, places: Iterable[Mapping[str, object]]) -> None:
        candidates: dict[str, list[VerifiedLocation]] = defaultdict(list)
        for place in places:
            entity_id = place.get("id")
            name = place.get("name")
            longitude = place.get("longitude")
            latitude = place.get("latitude")
            if not (
                isinstance(entity_id, str)
                and isinstance(name, str)
                and isinstance(longitude, (int, float))
                and isinstance(latitude, (int, float))
            ):
                continue
            location = VerifiedLocation(
                entity_id=entity_id,
                label=name,
                longitude=float(longitude),
                latitude=float(latitude),
                coordinate_source_id=f"history-kb-place:{entity_id}",
            )
            labels = [name, place.get("modern_name")]
            aliases = place.get("aliases")
            if isinstance(aliases, list):
                labels.extend(aliases)
            for label in labels:
                if isinstance(label, str) and _normalise_label(label):
                    candidates[_normalise_label(label)].append(location)
        self._unique = {
            label: values[0]
            for label, values in candidates.items()
            if len({item.entity_id for item in values}) == 1
        }

    def __call__(self, label: str) -> VerifiedLocation | None:
        return self._unique.get(_normalise_label(label))


__all__ = ["ReviewedPlaceResolver"]
