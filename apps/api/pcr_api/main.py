from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .database import build_engine, build_session_factory
from .routes.health import router as health_router
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
        max_age=600,
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
    return app


app = create_app()
