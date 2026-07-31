"""Entities endpoints: list, get, neighbors."""
from fastapi import APIRouter, HTTPException, Query
from ..services.entity_service import list_entities, get_entity, get_neighbors

router = APIRouter()


@router.get("")
def list_entities_api(
    type: str | None = Query(None, description="Filter by entity type"),
    year: int | None = Query(None, description="Filter by active year"),
    q: str | None = Query(None, description="Search in name/alias/bio"),
    limit: int = Query(200, le=2000),
    offset: int = 0,
    prefer_seed: bool = Query(False, description="Prioritize seed entities over CBDB"),
    role: str | None = Query(None, description="仅含 roles 数组中含该值的人物(如 emperor/general)"),
    importance: int | None = Query(None, description="精确匹配 importance(1核心/2重要/3一般)"),
    max_importance: int | None = Query(None, description="importance <= 该值(如 2=只看核心+重要)"),
    fields: str | None = Query(
        None,
        description="逗号分隔字段白名单;给定时仅返回这些字段(id/type 强制包含),未知字段忽略。未给定时返回全字段。"),
):
    field_list = (
        [f.strip() for f in fields.split(",") if f.strip()]
        if fields else None
    )
    return list_entities(type=type, year=year, q=q, limit=limit, offset=offset,
                         prefer_seed=prefer_seed, fields=field_list,
                         role=role, importance=importance, max_importance=max_importance)


@router.get("/{entity_id}")
def get_entity_api(entity_id: str):
    e = get_entity(entity_id)
    if e is None:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
    return e


@router.get("/{entity_id}/neighbors")
def get_neighbors_api(entity_id: str, depth: int = Query(1, ge=1, le=3)):
    return get_neighbors(entity_id, depth)
