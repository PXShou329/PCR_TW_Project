from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from pcr_database.models import CoreRevision, MaterializationState, RevisionActivation

from .pve_fixture import import_fire_8_10
from .research_core_snapshot import (
    DEFAULT_MANIFEST,
    EXPECTED_MANIFEST_SHA256,
    canonical_manifest_sha256,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_CORE = REPOSITORY_ROOT / "research_core" / "pcr_tw_project"


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _write_manifest(root: Path, destination: Path) -> str:
    lines: list[str] = []
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative_path = path.relative_to(root).as_posix()
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative_path}")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return canonical_manifest_sha256(lines)


def run_smoke(database_url: str) -> dict[str, object]:
    engine = create_engine(database_url, pool_pre_ping=True)
    with tempfile.TemporaryDirectory(prefix="pcr-b1-history-") as temporary:
        temporary_root = Path(temporary)
        second_core = temporary_root / "pcr_tw_project"
        shutil.copytree(RESEARCH_CORE, second_core)
        readme = second_core / "README.md"
        readme.write_bytes(readme.read_bytes() + b"\n")
        second_manifest = temporary_root / "MANIFEST.sha256"
        second_manifest_sha256 = _write_manifest(second_core, second_manifest)

        with Session(engine) as session:
            canonical = import_fire_8_10(
                session,
                RESEARCH_CORE,
                manifest_path=DEFAULT_MANIFEST,
                expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
            )
            before_activations = int(
                session.scalar(select(func.count()).select_from(RevisionActivation)) or 0
            )
            session.rollback()

            alternate = import_fire_8_10(
                session,
                second_core,
                manifest_path=second_manifest,
                expected_manifest_sha256=second_manifest_sha256,
            )
            restored = import_fire_8_10(
                session,
                RESEARCH_CORE,
                manifest_path=DEFAULT_MANIFEST,
                expected_manifest_sha256=EXPECTED_MANIFEST_SHA256,
            )

            state = session.get(MaterializationState, 1)
            revision_count = int(
                session.scalar(select(func.count()).select_from(CoreRevision)) or 0
            )
            activations = session.scalars(
                select(RevisionActivation).order_by(RevisionActivation.sequence_no)
            ).all()
            if state is None or state.active_revision_id != canonical.revision_id:
                raise RuntimeError("revision history smoke did not restore canonical pointer")
            if restored.revision_id != canonical.revision_id or not restored.activated:
                raise RuntimeError("canonical revision rollback did not activate")
            if alternate.revision_id == canonical.revision_id or not alternate.activated:
                raise RuntimeError("alternate immutable revision was not activated")
            if revision_count < 2 or len(activations) < before_activations + 2:
                raise RuntimeError("inactive revision or activation audit history is missing")
            last_kinds = [activation.kind for activation in activations[-2:]]
            expected_first = "IMPORT" if alternate.created else "REACTIVATE"
            if last_kinds != [expected_first, "ROLLBACK"]:
                raise RuntimeError(
                    f"unexpected revision activation chronology: {last_kinds}"
                )

    return {
        "status": "REVISION_HISTORY_OK",
        "canonical_revision_id": canonical.revision_id,
        "inactive_revision_id": alternate.revision_id,
        "inactive_created": alternate.created,
        "revision_count": revision_count,
        "activation_count": len(activations),
        "last_activation_kinds": last_kinds,
    }


def main() -> int:
    result = run_smoke(_required_environment("PCR_DATABASE_URL"))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
