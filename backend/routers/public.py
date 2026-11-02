# [Input] Explicit public application URLs, backend version, and allowed CORS origins.
# [Output] Existing root, health, robots, sitemap, and llms routes for server and embedded Python.
# [Pos] Shared Dream public routes; importing this module starts no service or authentication owner.
# [Sync] 2026-10-25: extract existing public endpoints for the real iOS FastAPI bootstrap.

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response
from seo_content import build_llms_txt, build_robots_txt, build_sitemap_xml


def create_public_router(*, backend_version: str, cors_allow_origins: list[str],
                         public_base_url: str, backend_public_base_url: str) -> APIRouter:
    router = APIRouter()

    @router.get("/")
    def root():
        base = backend_public_base_url.rstrip("/") + "/"
        return PlainTextResponse(
            f"The server is configured with a public base URL of {base}"
            f" - did you mean to visit {base}api/claude-agent/threads instead?"
        )

    @router.get("/robots.txt", include_in_schema=False)
    def robots_txt():
        return PlainTextResponse(build_robots_txt(public_base_url), media_type="text/plain; charset=utf-8")

    @router.get("/sitemap.xml", include_in_schema=False)
    def sitemap_xml():
        return Response(build_sitemap_xml(public_base_url), media_type="application/xml; charset=utf-8")

    @router.get("/llms.txt", include_in_schema=False)
    def llms_txt():
        return PlainTextResponse(
            build_llms_txt(public_base_url, backend_public_base_url),
            media_type="text/plain; charset=utf-8",
        )

    @router.get("/api/health")
    def health():
        return {"status": "ok", "version": backend_version, "cors_allow_origins": cors_allow_origins}

    return router

