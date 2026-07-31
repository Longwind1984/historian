"""Relations endpoints."""
from fastapi import APIRouter, Query
from ..core.data import load_all_relations

router = APIRouter()


@router.get("")
def list_relations(
    type: str | None = Query(None),
    from_id: str | None = Query(None, alias="from"),
    to_id: str | None = Query(None, alias="to"),
    year: int | None = Query(None, description="Filter by relation active in year"),
    limit: int = Query(500, le=5000),
    offset: int = Query(0, ge=0),
):
    relations = load_all_relations()
    if type:
        relations = [r for r in relations if r.get("type") == type]
    if from_id:
        relations = [r for r in relations if r.get("from") == from_id]
    if to_id:
        relations = [r for r in relations if r.get("to") == to_id]
    if year is not None:
        def active(r):
            since = (r.get("since") or {}).get("year", -9999)
            until = (r.get("until") or {}).get("year", 9999)
            return since <= year <= until
        relations = [r for r in relations if active(r)]
    return {
        "total": len(relations),
        "offset": offset,
        "limit": limit,
        "items": relations[offset:offset + limit],
    }
