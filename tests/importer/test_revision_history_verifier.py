from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session

from pcr_database.models import Base, CoreFile, MaterializationState
from pcr_pipeline.research_core_snapshot import SnapshotDriftError
from pcr_pipeline.revision_history_smoke import run_smoke
from pcr_pipeline.verify_revision_history import verify_revision_history


def test_revision_history_verifier_checks_every_revision_and_detects_content_drift(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "history.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    seeded = run_smoke(database_url)
    verified = verify_revision_history(database_url)

    assert seeded["status"] == "REVISION_HISTORY_OK"
    assert verified["status"] == "REVISION_HISTORY_VERIFIED"
    assert verified["revision_count"] == 2
    assert verified["import_run_count"] == 2
    assert verified["activation_count"] == 3
    assert verified["inactive_revision_count"] == 1
    assert len(str(verified["history_sha256"])) == 64

    with Session(engine) as session, session.begin():
        state = session.get(MaterializationState, 1)
        assert state is not None
        inactive_revision_id = str(seeded["inactive_revision_id"])
        session.execute(
            update(CoreFile.__table__)
            .where(
                CoreFile.revision_id == inactive_revision_id,
                CoreFile.relative_path == "README.md",
            )
            .values(content=b"tampered inactive revision\n")
        )

    with pytest.raises(SnapshotDriftError):
        verify_revision_history(database_url)
