from __future__ import annotations

import json
import os
from urllib.error import HTTPError
from urllib.request import urlopen

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError


GUIDE_ID = "TW_DEEP_FIRE_08_10_20260802"
MARKER = " [B1_CACHE_EPOCH_PROBE]"


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _readiness(api_base_url: str) -> tuple[int, dict[str, object]]:
    url = f"{api_base_url.rstrip('/')}/health/ready"
    try:
        with urlopen(url, timeout=10) as response:  # noqa: S310 - fixed internal URL
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def run_smoke(importer_database_url: str, api_base_url: str) -> dict[str, object]:
    writer_engine = create_engine(importer_database_url, pool_pre_ping=True)
    mutated = False
    initial_notes = ""
    before_epoch = -1
    mutated_epoch = -1
    rewind_error = ""

    warm_status, warm_payload = _readiness(api_base_url)
    if warm_status != 200 or warm_payload.get("status") != "ok":
        raise RuntimeError(f"API readiness did not warm successfully: {warm_payload}")

    try:
        with writer_engine.connect() as writer:
            initial_notes = writer.execute(
                text("SELECT notes FROM stages WHERE guide_id=:guide_id"),
                {"guide_id": GUIDE_ID},
            ).scalar_one()
            before_epoch = int(
                writer.execute(
                    text("SELECT epoch FROM materialization_state WHERE id=1")
                ).scalar_one()
            )
        if initial_notes.endswith(MARKER):
            raise RuntimeError("cache/epoch probe marker already exists")

        with writer_engine.begin() as writer:
            result = writer.execute(
                text("UPDATE stages SET notes=notes || :marker WHERE guide_id=:guide_id"),
                {"guide_id": GUIDE_ID, "marker": MARKER},
            )
            if result.rowcount != 1:
                raise RuntimeError("cache/epoch probe target is missing")
        mutated = True

        with writer_engine.connect() as writer:
            mutated_epoch = int(
                writer.execute(
                    text("SELECT epoch FROM materialization_state WHERE id=1")
                ).scalar_one()
            )
        if mutated_epoch <= before_epoch:
            raise RuntimeError("typed mutation did not advance materialization epoch")

        drift_status, drift_payload = _readiness(api_base_url)
        if drift_status != 503:
            raise RuntimeError(
                f"pre-warmed API did not fail closed on typed drift: {drift_payload}"
            )
        fixture_check = dict(drift_payload.get("checks", {})).get("fixture", "")
        if not str(fixture_check).startswith("materialization_"):
            raise RuntimeError(f"unexpected drift reason: {fixture_check}")

        try:
            with writer_engine.begin() as writer:
                writer.execute(
                    text("UPDATE materialization_state SET epoch=:epoch WHERE id=1"),
                    {"epoch": before_epoch},
                )
        except DBAPIError as error:
            rewind_error = str(error.orig)
        else:
            raise RuntimeError("database allowed materialization epoch rewind")
        if "epoch" not in rewind_error.lower():
            raise RuntimeError(f"epoch rewind hit the wrong database guard: {rewind_error}")

        with writer_engine.connect() as writer:
            epoch_after_denial = int(
                writer.execute(
                    text("SELECT epoch FROM materialization_state WHERE id=1")
                ).scalar_one()
            )
        if epoch_after_denial != mutated_epoch:
            raise RuntimeError("denied epoch rewind changed committed materialization state")
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
                    raise RuntimeError("cache/epoch probe cleanup failed")

    recovered_status, recovered_payload = _readiness(api_base_url)
    if recovered_status != 200 or recovered_payload.get("status") != "ok":
        raise RuntimeError(f"API did not recover after drift cleanup: {recovered_payload}")
    with writer_engine.connect() as writer:
        restored_notes = writer.execute(
            text("SELECT notes FROM stages WHERE guide_id=:guide_id"),
            {"guide_id": GUIDE_ID},
        ).scalar_one()
        restored_epoch = int(
            writer.execute(
                text("SELECT epoch FROM materialization_state WHERE id=1")
            ).scalar_one()
        )
    if restored_notes != initial_notes or restored_epoch <= mutated_epoch:
        raise RuntimeError("cache/epoch probe did not restore the serving mirror")

    return {
        "status": "CACHE_EPOCH_FAIL_CLOSED_OK",
        "warm_http": warm_status,
        "drift_http": drift_status,
        "recovered_http": recovered_status,
        "epoch_before": before_epoch,
        "epoch_mutated": mutated_epoch,
        "epoch_restored": restored_epoch,
    }


def main() -> int:
    result = run_smoke(
        _required_environment("PCR_IMPORTER_DATABASE_URL"),
        _required_environment("PCR_API_BASE_URL"),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
