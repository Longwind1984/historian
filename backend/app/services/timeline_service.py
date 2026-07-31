"""Timeline services: the general time index and the map-story playlist."""
from ..core.data import get_entity_index, get_relation_index


def _year_of(entity: dict) -> int | None:
    return (entity.get("date") or {}).get("year")


def _place_anchor(place: dict | None) -> dict | None:
    """Return a serialisable point only when both coordinates are recorded."""
    if not place:
        return None
    lat, lng = place.get("latitude"), place.get("longitude")
    if lat is None or lng is None:
        return None
    return {
        "id": place.get("id"),
        "name": place.get("name"),
        "latitude": lat,
        "longitude": lng,
    }


def _map_focus(entity: dict, eidx) -> dict | None:
    """Resolve only explicit Event/Battle map anchors; never infer a route."""
    location = _place_anchor(eidx.get(entity.get("location")))
    legs = []
    for leg in entity.get("march") or []:
        start = _place_anchor(eidx.get(leg.get("from")))
        end = _place_anchor(eidx.get(leg.get("to")))
        if not start or not end:
            continue
        legs.append({
            "from": start,
            "to": end,
            "note": leg.get("note") or "",
        })
    if not location and not legs:
        return None
    return {"location": location, "march": legs}


def _story_sort_key(item: dict) -> tuple:
    # 同日先播历史事件，再播与它严格匹配的人物生平节点；其后用稳定 ID 收口。
    return (
        item["year"], item.get("month") or 0, item.get("day") or 0,
        0 if item["kind"] == "event" else 1,
        item["entity_id"], item["id"],
    )


def map_story(
    from_year: int | None = None,
    to_year: int | None = None,
    limit: int = 1000,
) -> dict:
    """Build the auditable playlist used by the expanded historical map.

    Event/Battle items require an explicit location or at least one fully
    resolved ``march`` leg. Person ``life_events`` do not currently carry
    their own place reference. A life node is therefore admitted only when a
    related Event/Battle is in the same year *and* its full name occurs in the
    life-event text. The related event supplies the focus geometry; no
    birthplace, string place extraction, or other guessed coordinate is used.
    """
    eidx = get_entity_index()
    ridx = get_relation_index()
    focus_by_event: dict[str, dict] = {}
    event_items: list[dict] = []

    for entity_type in ("Event", "Battle"):
        for entity in eidx.entities_by_type(entity_type):
            year = _year_of(entity)
            if year is None:
                continue
            focus = _map_focus(entity, eidx)
            if not focus:
                continue
            eid = entity.get("id")
            focus_by_event[eid] = focus
            date = entity.get("date") or {}
            summary = (entity.get("description") or entity.get("significance")
                       or entity.get("impact") or "")
            event_items.append({
                "id": f"event:{eid}",
                "kind": "event",
                "year": year,
                "month": date.get("month"),
                "day": date.get("day"),
                "entity_id": eid,
                "entity_type": entity_type,
                "focus_entity_id": eid,
                "title": entity.get("name"),
                "summary": summary,
                "category": entity.get("category") or (
                    "battle" if entity_type == "Battle" else "other"),
                "source": (entity.get("sources") or [None])[0],
                **focus,
            })

    # Build a local Person -> related, already map-resolved events index.
    related_events: dict[str, set[str]] = {}
    for relation in ridx.relations:
        left, right = relation.get("from"), relation.get("to")
        left_entity, right_entity = eidx.get(left), eidx.get(right)
        if not left_entity or not right_entity:
            continue
        if left_entity.get("type") == "Person" and right in focus_by_event:
            related_events.setdefault(left, set()).add(right)
        elif right_entity.get("type") == "Person" and left in focus_by_event:
            related_events.setdefault(right, set()).add(left)

    life_items: list[dict] = []
    for person in eidx.entities_by_type("Person"):
        if person.get("importance") not in (1, 2):
            continue
        pid = person.get("id")
        candidate_events = [eidx.get(eid) for eid in related_events.get(pid, ())]
        candidate_events = [event for event in candidate_events if event]
        for life_index, life in enumerate(person.get("life_events") or []):
            year, text = life.get("year"), life.get("event")
            if year is None or not text:
                continue
            matches = [event for event in candidate_events
                       if _year_of(event) == year and (event.get("name") or "") in text]
            # Multiple exact-name matches are unusual but legitimate; stable ID order
            # makes the selected map focus deterministic without pretending certainty.
            for event in sorted(matches, key=lambda item: item.get("id") or ""):
                eid = event.get("id")
                focus = focus_by_event[eid]
                life_items.append({
                    "id": f"life:{pid}:{life_index}:{eid}",
                    "kind": "life_event",
                    "year": year,
                    "month": life.get("month"),
                    "day": life.get("day"),
                    "entity_id": pid,
                    "entity_type": "Person",
                    "focus_entity_id": eid,
                    "title": text,
                    "summary": person.get("bio") or "",
                    "category": "person",
                    "person_name": person.get("name"),
                    "source": life.get("source"),
                    "focus_note": f"地点依据同年关联事件「{event.get('name')}」",
                    **focus,
                })

    items = event_items + life_items
    if from_year is not None:
        items = [item for item in items if item["year"] >= from_year]
    if to_year is not None:
        items = [item for item in items if item["year"] <= to_year]
    items.sort(key=_story_sort_key)
    return {"total": len(items), "items": items[:limit]}


def timeline(
    from_year: int | None = None,
    to_year: int | None = None,
    type: str | None = None,
    limit: int = 500,
) -> dict:
    """Return time-ordered events for Person/Polity/Event/Battle."""
    eidx = get_entity_index()
    events = []

    source = eidx.entities_by_type(type) if type else eidx.entities

    for e in source:
        t = e.get("type")
        eid = e.get("id")
        name = e.get("name")
        if t == "Person":
            born = e.get("born")
            died = e.get("died")
            if born:
                events.append({"year": born.get("year"), "month": born.get("month"),
                               "type": "birth", "entity_id": eid, "entity_name": name,
                               "label": f"{name} 出生"})
            if died:
                events.append({"year": died.get("year"), "month": died.get("month"),
                               "type": "death", "entity_id": eid, "entity_name": name,
                               "label": f"{name} 卒"})
        elif t == "Polity":
            founded = e.get("founded")
            ended = e.get("ended")
            if founded:
                events.append({"year": founded.get("year"), "month": founded.get("month"),
                               "type": "founded", "entity_id": eid, "entity_name": name,
                               "label": f"{name} 建立"})
            if ended:
                events.append({"year": ended.get("year"), "month": ended.get("month"),
                               "type": "ended", "entity_id": eid, "entity_name": name,
                               "label": f"{name} 灭亡"})
        elif t in ("Event", "Battle"):
            date = e.get("date")
            if date:
                events.append({"year": date.get("year"), "month": date.get("month"),
                               "type": t.lower(), "entity_id": eid, "entity_name": name,
                               "label": name, "category": e.get("category")})

    if from_year is not None:
        events = [e for e in events if (e.get("year") or 0) >= from_year]
    if to_year is not None:
        events = [e for e in events if (e.get("year") or 9999) <= to_year]

    events.sort(key=lambda e: ((e.get("year") or 0), (e.get("month") or 0)))
    return {"total": len(events), "items": events[:limit]}
