"""Timeline endpoints."""
from fastapi import APIRouter, Query
from ..services.timeline_service import map_story, timeline

router = APIRouter()


@router.get("/map-story")
def map_story_api(
    from_year: int | None = Query(None, alias="from", description="Start year"),
    to_year: int | None = Query(None, alias="to", description="End year"),
    limit: int = Query(1000, ge=1, le=2000),
):
    return map_story(from_year=from_year, to_year=to_year, limit=limit)


@router.get("")
def timeline_api(
    from_year: int | None = Query(None, alias="from", description="Start year"),
    to_year: int | None = Query(None, alias="to", description="End year"),
    type: str | None = Query(None, description="Filter Event/Battle/Person…"),
    limit: int = Query(500, le=5000),
):
    return timeline(from_year=from_year, to_year=to_year, type=type, limit=limit)
