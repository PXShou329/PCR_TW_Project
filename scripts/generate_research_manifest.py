#!/usr/bin/env python3
"""Generate one reviewed research-core manifest candidate and portable pins."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "data_pipeline"))
sys.path.insert(0, str(REPOSITORY_ROOT / "database"))

from pcr_pipeline.research_core_snapshot import (  # noqa: E402
    candidate_manifest_lines,
    canonical_manifest_bytes,
    canonical_manifest_sha256,
    core_materialization_sha256,
    load_research_core_snapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Write a production-safe candidate manifest. This command never updates "
            "application, test, runbook, or rollback pins."
        )
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=REPOSITORY_ROOT / "research_core" / "pcr_tw_project",
    )
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    project = arguments.project_root.resolve(strict=True)
    output = arguments.output.resolve(strict=False)
    try:
        output.relative_to(project)
    except ValueError:
        pass
    else:
        parser.error("--output must be outside the research-core tree")
    if output.exists():
        parser.error("--output already exists; generate into a new review path")
    lines = candidate_manifest_lines(project)
    payload = canonical_manifest_bytes(lines)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    manifest_sha256 = canonical_manifest_sha256(lines)
    snapshot = load_research_core_snapshot(
        project,
        output,
        expected_manifest_sha256=manifest_sha256,
    )
    report = snapshot.report()
    print(
        json.dumps(
            {
                "status": "RESEARCH_MANIFEST_CANDIDATE_READY",
                "output": str(output),
                "manifest_sha256": manifest_sha256,
                "raw_tree_sha256": snapshot.raw_tree_sha256,
                "semantic_tree_sha256": snapshot.semantic_tree_sha256,
                "artifact_mirror_sha256": core_materialization_sha256(snapshot),
                "file_count": report.file_count,
                "csv_file_count": report.csv_file_count,
                "csv_row_count": report.csv_row_count,
                "evidence_to_claim_count": report.evidence_to_claim_count,
                "evidence_to_claim_sha256": report.evidence_to_claim_sha256,
                "claim_to_evidence_count": report.claim_to_evidence_count,
                "claim_to_evidence_sha256": report.claim_to_evidence_sha256,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
