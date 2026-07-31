"""Graph query endpoints: shortest path, contemporaries."""
from fastapi import APIRouter, HTTPException, Query
from ..services.graph_service import shortest_path, contemporaries, spacetime

router = APIRouter()


@router.get("/shortest")
def shortest_path_api(
    from_id: str = Query(..., alias="from"),
    to_id: str = Query(..., alias="to"),
    max_depth: int = Query(4, ge=1, le=6),
):
    return shortest_path(from_id, to_id, max_depth)


@router.get("/contemporaries")
def contemporaries_api(
    person_id: str = Query(..., alias="person"),
    year: int = Query(...),
    radius: int = Query(50, ge=1, le=100),
):
    peers = contemporaries(person_id, year, radius)
    return {"person": person_id, "year": year, "count": len(peers), "peers": peers}


@router.get("/spacetime")
def spacetime_api():
    """时空柱数据地基：每实体 时间+地理+朝代+链接度。

    返回 {meta, dynasties, nodes}，详见 graph_service.spacetime。
    供星图重构（docs/starmap-redesign.md §0/§4/§5）的时空柱渲染。
    """
    return spacetime()
