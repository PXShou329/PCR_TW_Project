from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .database import build_engine, build_session_factory
from .private_gacha.runtime import (
    GachaLibraryNotFound,
    GachaLibraryRuntime,
    GachaLibraryUnavailable,
)
from .private_pve.runtime import (
    PveLibraryNotFound,
    PveLibraryRuntime,
    PveLibraryUnavailable,
)
from .routes.health import router as health_router
from .private_gacha.router import router as gacha_library_router
from .private_pve.router import router as pve_library_router
from .routes.v1 import router as v1_router


def create_app(
    *,
    settings: Settings | None = None,
    session_factory: sessionmaker[Session] | Callable[[], Session] | None = None,
) -> FastAPI:
    resolved = settings or Settings.from_environment()
    app = FastAPI(
        title="PCR TW Guide-Only Strategy API",
        version=resolved.application_version,
        docs_url="/docs",
        redoc_url=None,
    )
    app.state.settings = resolved
    app.state.session_factory = session_factory or build_session_factory(build_engine(resolved))
    app.state.pve_library_runtime = PveLibraryRuntime.from_settings(resolved)
    app.state.gacha_library_runtime = GachaLibraryRuntime.from_settings(resolved)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        # POST is limited to the read-only exact P-Arena solver. No endpoint
        # mutates canonical or serving data.
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
        max_age=600,
    )

    @app.exception_handler(SQLAlchemyError)
    async def database_unavailable(
        request: Request,
        _error: SQLAlchemyError,
    ) -> JSONResponse:
        if request.url.path == "/health/ready":
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "checks": {"database": "error", "fixture": "unknown"},
                },
            )
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "DATABASE_UNAVAILABLE",
                    "resource": "database",
                    "id": None,
                }
            },
        )

    @app.exception_handler(PveLibraryUnavailable)
    async def pve_library_unavailable(
        _request: Request,
        error: PveLibraryUnavailable,
    ) -> JSONResponse:
        body: dict[str, object] = {
            "code": error.code,
            "message": error.message,
        }
        if error.details is not None:
            body["details"] = error.details
        return JSONResponse(status_code=503, content={"error": body})

    @app.exception_handler(PveLibraryNotFound)
    async def pve_library_not_found(
        _request: Request,
        error: PveLibraryNotFound,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "PVE_LIBRARY_NOT_FOUND",
                    "message": "The requested PVE library resource was not found.",
                    "details": {
                        "resource": error.resource,
                        "id": error.identifier,
                    },
                }
            },
        )

    @app.exception_handler(GachaLibraryUnavailable)
    async def gacha_library_unavailable(
        _request: Request,
        error: GachaLibraryUnavailable,
    ) -> JSONResponse:
        body: dict[str, object] = {
            "code": error.code,
            "message": error.message,
        }
        if error.details is not None:
            body["details"] = error.details
        return JSONResponse(status_code=503, content={"error": body})

    @app.exception_handler(GachaLibraryNotFound)
    async def gacha_library_not_found(
        _request: Request,
        error: GachaLibraryNotFound,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "GACHA_LIBRARY_NOT_FOUND",
                    "message": "The requested Gacha library resource was not found.",
                    "details": {
                        "resource": error.resource,
                        "id": error.identifier,
                    },
                }
            },
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    app.include_router(health_router)
    app.include_router(v1_router)
    app.include_router(pve_library_router)
    app.include_router(gacha_library_router)
    return app


app = create_app()
