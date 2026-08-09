from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from pcr_database.models import Base

from .research_core_snapshot import (
    DEFAULT_MANIFEST,
    DEFAULT_RESEARCH_CORE,
    export_materialized_revision,
    load_research_core_snapshot,
    materialize_snapshot,
    materialized_report,
)


def _engine(database_url: str | None) -> tuple[Engine, bool]:
    if database_url:
        return create_engine(database_url, pool_pre_ping=True), False
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine, True


def _run_baseline(export_root: Path, checker: Path) -> dict[str, Any]:
    # checker 自己先 copytree 至 disposable directory；--write 永遠不會碰 export hash。
    completed = subprocess.run(
        (sys.executable, str(checker), "--project-root", str(export_root)),
        cwd=checker.parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "exit_code": completed.returncode,
        "last_line": completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "",
    }


def run_round_trip_smoke(
    *,
    research_core: Path = DEFAULT_RESEARCH_CORE,
    manifest_path: Path = DEFAULT_MANIFEST,
    database_url: str | None = None,
    output_directory: Path | None = None,
    run_baseline: bool = False,
    baseline_checker: Path | None = None,
) -> dict[str, Any]:
    source = load_research_core_snapshot(research_core, manifest_path)
    engine, create_schema = _engine(database_url)
    if create_schema:
        Base.metadata.create_all(engine)

    with tempfile.TemporaryDirectory(prefix="pcr-b1-round-trip-") as temporary:
        temporary_root = Path(temporary)
        first_destination = output_directory or temporary_root / "export-one"
        second_destination = temporary_root / "export-two"
        with Session(engine) as session, session.begin():
            created = materialize_snapshot(session, source)
            database_report = materialized_report(
                session,
                source.revision_id,
                require_succeeded=False,
            )
            first_report = export_materialized_revision(
                session,
                source.revision_id,
                first_destination,
                canonical_root=research_core,
                verify_manifest_path=manifest_path,
                require_succeeded=False,
            )
            second_report = export_materialized_revision(
                session,
                source.revision_id,
                second_destination,
                canonical_root=research_core,
                verify_manifest_path=manifest_path,
                require_succeeded=False,
            )

        expected = source.report().as_dict()
        reports = [
            database_report.as_dict(),
            first_report.as_dict(),
            second_report.as_dict(),
        ]
        if any(report != expected for report in reports):
            raise RuntimeError("ROUND_TRIP_PARITY_MISMATCH")

        baseline: dict[str, Any] | None = None
        if run_baseline:
            checker = baseline_checker or (
                Path(__file__).resolve().parents[2] / "scripts" / "check_research_baseline.py"
            )
            baseline = _run_baseline(first_destination, checker.resolve(strict=True))
            if baseline["exit_code"] != 0:
                raise RuntimeError(
                    "ROUND_TRIP_BASELINE_FAILED "
                    f"exit={baseline['exit_code']} last_line={baseline['last_line']}"
                )
            # 防止日後 checker 實作誤改傳入 root；驗證後再核對 exact-byte revision。
            after_baseline = load_research_core_snapshot(first_destination, manifest_path)
            if after_baseline.raw_tree_sha256 != source.raw_tree_sha256:
                raise RuntimeError("ROUND_TRIP_BASELINE_MUTATED_EXPORT")

        return {
            "status": "ROUND_TRIP_OK",
            "created": created,
            "deterministic_exports": True,
            "report": expected,
            "baseline": baseline,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the manifest-pinned research-core DB/export round trip"
    )
    parser.add_argument("--research-core", type=Path, default=DEFAULT_RESEARCH_CORE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--database-url", default=os.getenv("PCR_DATABASE_URL") or None)
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--run-baseline", action="store_true")
    parser.add_argument("--baseline-checker", type=Path)
    arguments = parser.parse_args()

    result = run_round_trip_smoke(
        research_core=arguments.research_core,
        manifest_path=arguments.manifest,
        database_url=arguments.database_url,
        output_directory=arguments.output_directory,
        run_baseline=arguments.run_baseline,
        baseline_checker=arguments.baseline_checker,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
