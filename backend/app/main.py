"""FastAPI application factory and container entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .api import entities, explorations, relations, graph, territories, timeline, meta, links

APP_VERSION = "1.4.0"


# 谭其骧历史地图集瓦片，自托管。
#
# 为什么不直连 tile.osgeo.cn：那台 nginx 对 curl（GET 与 OPTIONS 都试过）稳定返回
# Access-control-allow-origin: *，但 Chromium 取瓦片时报
# "blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present"，
# 于是 maplibre 全灭而 <img> 标签照样能显示（img 不校验 CORS）。同一浏览器、同一 URL，
# 裸 Image 加载 30~121ms 成功、maplibre 的 fetch 必失败 —— 差异不在可达性，在 CORS，
# 且我们既控制不了那台服务器，也无法从外部把这个差异诊断到底。
#
# 底图是产品功能，不该挂在一个既控制不了、又诊断不清的第三方服务上。当前把用到的
# 29 幅共 5023 个 PNG（127MB，含 28 幅年代表 + 1 幅区域备查）放在本地：同源，
# 没有 CORS 这回事。
# 重新抓取见 scripts/fetch_atlas_tiles.py（幂等，已存在的跳过）。
def create_app(
    api_prefix: str = "/api",
    mount_tiles: bool = True,
    enable_private_explorations: bool | None = None,
) -> FastAPI:
    """Create the API for containers or a path-prefixed serverless runtime."""
    private_explorations_enabled = (
        settings.private_explorations_enabled
        if enable_private_explorations is None
        else enable_private_explorations
    )
    application = FastAPI(
        title="History KB API",
        description="Interactive knowledge base of Chinese history (Five Dynasties & Ten Kingdoms and beyond)",
        version=APP_VERSION,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(meta.router, prefix=api_prefix, tags=["meta"])
    application.include_router(entities.router, prefix=f"{api_prefix}/entities", tags=["entities"])
    application.include_router(relations.router, prefix=f"{api_prefix}/relations", tags=["relations"])
    application.include_router(graph.router, prefix=f"{api_prefix}/graph", tags=["graph"])
    application.include_router(territories.router, prefix=f"{api_prefix}/territories", tags=["territories"])
    application.include_router(timeline.router, prefix=f"{api_prefix}/timeline", tags=["timeline"])
    application.include_router(links.router, prefix=f"{api_prefix}/links", tags=["links"])
    if private_explorations_enabled:
        application.include_router(
            explorations.router,
            prefix=f"{api_prefix}/explorations",
            tags=["explorations"],
        )

    atlas_dir = settings.data_dir / "geo" / "atlas_tiles"
    if mount_tiles and atlas_dir.exists():
        application.mount("/tiles/atlas", StaticFiles(directory=str(atlas_dir)), name="atlas-tiles")

    @application.get("/")
    def root():
        public_prefix = api_prefix or "/api"
        endpoints = [
            f"{public_prefix}/meta/schema",
            f"{public_prefix}/entities",
            f"{public_prefix}/relations",
            f"{public_prefix}/graph/shortest",
            f"{public_prefix}/territories",
            f"{public_prefix}/timeline",
            f"{public_prefix}/links/scan/{{id}}",
            f"{public_prefix}/links/backlinks/{{id}}",
        ]
        if private_explorations_enabled:
            endpoints.extend([
                f"{public_prefix}/explorations/from-prompt",
                f"{public_prefix}/explorations/import",
                f"{public_prefix}/explorations/import-epub",
            ])
        return {
            "name": "History KB API",
            "version": APP_VERSION,
            "docs": f"{public_prefix}/docs" if not api_prefix else "/docs",
            "endpoints": endpoints,
        }

    return application


app = create_app()
