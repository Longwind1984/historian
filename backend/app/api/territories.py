"""Territory endpoints: return GeoJSON for polities by year."""
from fastapi import APIRouter, Query, HTTPException
from ..services.territory_service import territories_at, polity_territory

router = APIRouter()


@router.get("")
def territories_api(year: int = Query(..., description="Year to query")):
    return territories_at(year)


@router.get("/{polity_id}")
def polity_territory_api(polity_id: str, year: int | None = Query(None)):
    result = polity_territory(polity_id, year)
    if result is None:
        raise HTTPException(404, f"Polity {polity_id} not found")
    return result
