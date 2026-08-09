from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, text

from pcr_api.config import Settings
from pcr_api.database import build_engine


GUIDE_ID = "TW_DEEP_FIRE_08_10_20260802"
MARKER = " [B1_REPEATABLE_READ_PROBE]"


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def run_smoke(api_database_url: str, importer_database_url: str) -> dict[str, object]:
    reader_engine = build_engine(Settings(database_url=api_database_url))
    writer_engine = create_engine(importer_database_url, pool_pre_ping=True)
    mutated = False
    initial_notes = ""
    before_epoch = -1
    mutated_epoch = -1

    try:
        with reader_engine.connect() as reader:
            if reader.get_isolation_level().upper() != "REPEATABLE READ":
                raise RuntimeError("API reader is not using REPEATABLE READ")
            reader_transaction = reader.begin()
            try:
                before = reader.execute(
                    text(
                        "SELECT active_revision_id, active_import_run_id, epoch "
                        "FROM materialization_state WHERE id=1"
                    )
                ).one()
                initial_notes = reader.execute(
                    text("SELECT notes FROM stages WHERE guide_id=:guide_id"),
                    {"guide_id": GUIDE_ID},
                ).scalar_one()
                if initial_notes.endswith(MARKER):
                    raise RuntimeError("repeatable-read probe marker already exists")
                before_epoch = int(before.epoch)

                with writer_engine.begin() as writer:
                    result = writer.execute(
                        text(
                            "UPDATE stages SET notes=notes || :marker "
                            "WHERE guide_id=:guide_id"
                        ),
                        {"guide_id": GUIDE_ID, "marker": MARKER},
                    )
                    if result.rowcount != 1:
                        raise RuntimeError("repeatable-read probe target is missing")
                mutated = True

                with writer_engine.connect() as writer:
                    mutated_epoch = int(
                        writer.execute(
                            text("SELECT epoch FROM materialization_state WHERE id=1")
                        ).scalar_one()
                    )
                if mutated_epoch <= before_epoch:
                    raise RuntimeError("typed DML did not advance the materialization epoch")

                during = reader.execute(
                    text(
                        "SELECT active_revision_id, active_import_run_id, epoch "
                        "FROM materialization_state WHERE id=1"
                    )
                ).one()
                during_notes = reader.execute(
                    text("SELECT notes FROM stages WHERE guide_id=:guide_id"),
                    {"guide_id": GUIDE_ID},
                ).scalar_one()
                if tuple(during) != tuple(before) or during_notes != initial_notes:
                    raise RuntimeError("API transaction observed a mixed activation snapshot")
            finally:
                reader_transaction.rollback()
    finally:
        if mutated:
            with writer_engine.begin() as writer:
                result = writer.execute(
                    text(
                        "UPDATE stages "
                        "SET notes=left(notes, length(notes) - length(:marker)) "
                        "WHERE guide_id=:guide_id "
                        "AND right(notes, length(:marker))=:marker"
                    ),
                    {"guide_id": GUIDE_ID, "marker": MARKER},
                )
                if result.rowcount != 1:
                    raise RuntimeError("repeatable-read probe cleanup failed")

    with reader_engine.connect() as fresh_reader:
        restored_notes = fresh_reader.execute(
            text("SELECT notes FROM stages WHERE guide_id=:guide_id"),
            {"guide_id": GUIDE_ID},
        ).scalar_one()
        restored_epoch = int(
            fresh_reader.execute(
                text("SELECT epoch FROM materialization_state WHERE id=1")
            ).scalar_one()
        )
    if restored_notes != initial_notes or restored_epoch <= mutated_epoch:
        raise RuntimeError("repeatable-read probe did not restore the serving mirror")

    return {
        "status": "REPEATABLE_READ_CONSISTENCY_OK",
        "isolation": "REPEATABLE READ",
        "epoch_before": before_epoch,
        "epoch_mutated": mutated_epoch,
        "epoch_restored": restored_epoch,
    }


def main() -> int:
    result = run_smoke(
        _required_environment("PCR_API_DATABASE_URL"),
        _required_environment("PCR_IMPORTER_DATABASE_URL"),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
