from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_session
from ..repository import latest_import, mirror_readiness
from ..schemas import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="ok", checks={"process": "ok"})


@router.get("/health/ready", response_model=HealthResponse)
def ready(session: Session = Depends(get_session)) -> HealthResponse | JSONResponse:
    try:
        session.execute(text("SELECT 1"))
        run = latest_import(session)
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "checks": {"database": "error", "fixture": "unknown"}},
        )
    if run is None:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "checks": {"database": "ok", "fixture": "missing"}},
        )
    try:
        materialized, fixture_status = mirror_readiness(session, run)
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "checks": {"database": "error", "fixture": "unknown"}},
        )
    if not materialized:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "checks": {"database": "ok", "fixture": fixture_status}},
        )
    return HealthResponse(status="ok", checks={"database": "ok", "fixture": "imported"})
