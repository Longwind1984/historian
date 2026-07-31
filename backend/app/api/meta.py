"""Meta endpoints: schema registry, stats."""
from fastapi import APIRouter
from ..core.data import load_schema_registry, load_relations_schema, load_all_entities, load_all_relations

router = APIRouter()


@router.get("/meta/schema")
def get_schema():
    return {"node_types": load_schema_registry(), "relations": load_relations_schema()}


@router.get("/meta/stats")
def get_stats():
    entities = load_all_entities()
    relations = load_all_relations()
    by_type: dict[str, int] = {}
    for e in entities:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "entity_count": len(entities),
        "relation_count": len(relations),
        "entities_by_type": by_type,
    }


@router.get("/meta/entity_types")
def get_entity_types():
    schema = load_schema_registry()
    return [
        {"type": t, "label": s.get("label", t), "label_en": s.get("label_en", t),
         "icon": s.get("icon"), "color": s.get("color"), "description": s.get("description")}
        for t, s in schema.items()
    ]
