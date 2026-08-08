from __future__ import annotations

import os
from pathlib import Path

import pytest

# Importing the ASGI module is intentionally fail-closed without a database
# URL. Tests provide an explicit in-memory value before importing it.
os.environ.setdefault("PCR_DATABASE_URL", "sqlite://")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from pcr_api.config import Settings
from pcr_api.main import create_app
from pcr_database.models import Base
from pcr_pipeline.pve_fixture import import_fire_8_10


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_CORE = ROOT / "research_core" / "pcr_tw_project"


def make_factory(*, imported: bool = True) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    if imported:
        with factory() as session:
            import_fire_8_10(session, RESEARCH_CORE)
    return factory


@pytest.fixture()
def client() -> TestClient:
    factory = make_factory()
    app = create_app(
        settings=Settings(database_url="sqlite://", application_version="3.0.0-a4"),
        session_factory=factory,
    )
    with TestClient(app) as test_client:
        yield test_client
