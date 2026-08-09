from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .pve_fixture import import_pve_projection
from .research_core_snapshot import (
    DEFAULT_MANIFEST,
    EXPECTED_MANIFEST_SHA256,
    RP_A2_MANIFEST_SHA256,
    RP_A3_MANIFEST_SHA256,
    RP_A4_MANIFEST_SHA256,
    RP_A5_MANIFEST_SHA256,
    load_research_core_snapshot,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE_CHECKER = REPOSITORY_ROOT / "scripts" / "check_research_baseline.py"
PINNED_ROLLBACK_MANIFESTS = frozenset(
    {
        RP_A2_MANIFEST_SHA256,
        RP_A3_MANIFEST_SHA256,
        RP_A4_MANIFEST_SHA256,
        RP_A5_MANIFEST_SHA256,
    }
)


def _verify_research_baseline(research_core: Path, checker: Path) -> None:
    environment = os.environ.copy()
    environment.update({"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    completed = subprocess.run(
        (sys.executable, str(checker), "--project-root", str(research_core)),
        cwd=REPOSITORY_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.returncode != 0:
        raise RuntimeError(
            f"research baseline verification failed with exit {completed.returncode}"
        )


def _verify_import_source(
    research_core: Path,
    manifest_path: Path,
    expected_manifest_sha256: str,
    checker: Path,
) -> None:
    """Verify the active release or an explicitly approved rollback tree."""

    if expected_manifest_sha256 == EXPECTED_MANIFEST_SHA256:
        _verify_research_baseline(research_core, checker)
        return
    if expected_manifest_sha256 not in PINNED_ROLLBACK_MANIFESTS:
        raise RuntimeError(
            "import source is neither the active release nor an approved rollback pin"
        )
    snapshot = load_research_core_snapshot(
        research_core,
        manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    report = snapshot.report()
    print(
        json.dumps(
            {
                "status": "PINNED_ROLLBACK_SOURCE_OK",
                "manifest_sha256": snapshot.manifest_sha256,
                "revision_id": snapshot.revision_id,
                "file_count": report.file_count,
                "csv_row_count": report.csv_row_count,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def main() -> int:
    configured_database_url = os.getenv("PCR_DATABASE_URL", "").strip() or None
    parser = argparse.ArgumentParser(
        description="Import and atomically activate the verified full-core/PVE revision"
    )
    parser.add_argument(
        "--research-core",
        type=Path,
        default=Path("research_core/pcr_tw_project"),
    )
    parser.add_argument(
        "--database-url",
        default=configured_database_url,
        required=configured_database_url is None,
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--manifest-sha256",
        default=EXPECTED_MANIFEST_SHA256,
        help="Reviewed digest of the manifest file; never inferred from the candidate tree.",
    )
    parser.add_argument(
        "--baseline-checker",
        type=Path,
        default=DEFAULT_BASELINE_CHECKER,
    )
    args = parser.parse_args()

    research_core = args.research_core.resolve(strict=True)
    manifest_path = args.manifest.resolve(strict=True)
    _verify_import_source(
        research_core,
        manifest_path,
        args.manifest_sha256,
        args.baseline_checker.resolve(strict=True),
    )
    engine = create_engine(args.database_url, pool_pre_ping=True)
    with Session(engine) as session:
        result = import_pve_projection(
            session,
            research_core,
            manifest_path=manifest_path,
            expected_manifest_sha256=args.manifest_sha256,
        )
    print(json.dumps(result.__dict__, ensure_ascii=False, sort_keys=True, default=list))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
