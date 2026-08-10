#!/usr/bin/env python3
"""Run the immutable RP-B4-0 research-core baseline in a disposable copy."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "data_pipeline"))
sys.path.insert(0, str(REPOSITORY_ROOT / "database"))

from pcr_pipeline.research_core_snapshot import (  # noqa: E402
    SnapshotValidationError,
    research_core_file_inventory,
)


EXPECTED_MANIFEST_SHA256 = "eda30340c02f2f470475e652786104c521faf2ea4cc20be44cf09f3798fe8c5f"
MANIFEST_PATH = Path(__file__).with_name("research_core_rp_b4_0_manifest.sha256")
MANIFEST_LINE = re.compile(r"^([0-9a-f]{64})  ([^\\]+(?:/[^\\]+)*)$")
VALIDATOR_RUNTIME_PATHS = {
    "tools/reports/pre_suite.json",
    "tools/reports/operational.json",
    "tools/reports/artifact_ready.json",
}


@dataclass(frozen=True)
class ExpectedRun:
    name: str
    arguments: tuple[str, ...]
    exit_code: int
    required: tuple[str, ...]


VALIDATOR_RUNS = (
    ExpectedRun(
        "PRE_SUITE --write",
        ("tools/validate_project.py", "--mode", "PRE_SUITE", "--write"),
        0,
        (
            "MODE=PRE_SUITE CHECKS=166 FAIL=0 WARN=22",
            "GateA=False GateB=False GateC=False blk=14",
            "canonical=Y",
        ),
    ),
    ExpectedRun(
        "PRE_SUITE",
        ("tools/validate_project.py", "--mode", "PRE_SUITE"),
        0,
        (
            "MODE=PRE_SUITE CHECKS=166 FAIL=0 WARN=22",
            "GateA=False GateB=False GateC=False blk=14",
            "canonical=Y",
        ),
    ),
    ExpectedRun(
        "OPERATIONAL",
        ("tools/validate_project.py", "--mode", "OPERATIONAL"),
        0,
        (
            "MODE=OPERATIONAL CHECKS=165 FAIL=0 WARN=21",
            "GateA=False GateB=False GateC=False blk=14",
            "canonical=N",
        ),
    ),
    ExpectedRun(
        "ARTIFACT_READY",
        ("tools/validate_project.py", "--mode", "ARTIFACT_READY"),
        1,
        (
            "MODE=ARTIFACT_READY CHECKS=168 FAIL=3 WARN=21",
            "GateA=False GateB=False GateC=False blk=14",
            "canonical=N",
            "ARTIFACT_READY 需 Gate A",
            "ARTIFACT_READY 需 Gate B",
            "ARTIFACT_READY 需 Gate C",
        ),
    ),
)


def source_files(root: Path) -> list[Path]:
    inventory = research_core_file_inventory(root)
    return [inventory[relative] for relative in sorted(inventory)]


def load_manifest() -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not MANIFEST_PATH.is_file():
        return {}, [f"missing RP-B4-0 manifest: {MANIFEST_PATH}"]
    lines = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    canonical = ("\n".join(lines) + "\n").encode("utf-8")
    manifest_sha256 = hashlib.sha256(canonical).hexdigest()
    if manifest_sha256 != EXPECTED_MANIFEST_SHA256:
        errors.append(
            "RP-B4-0 manifest digest mismatch "
            f"(expected {EXPECTED_MANIFEST_SHA256}, got {manifest_sha256})"
        )
    entries: dict[str, str] = {}
    for line_number, line in enumerate(lines, 1):
        match = MANIFEST_LINE.fullmatch(line)
        if not match:
            errors.append(f"invalid manifest line {line_number}: {line!r}")
            continue
        digest, relative = match.groups()
        if relative in entries:
            errors.append(f"duplicate manifest path: {relative}")
        entries[relative] = digest
    if len(entries) != 48:
        errors.append(f"expected 48 manifest entries, found {len(entries)}")
    return entries, errors


def verify_tree(root: Path) -> list[str]:
    manifest, errors = load_manifest()
    actual_paths = {
        path.relative_to(root).as_posix(): path for path in source_files(root)
    }
    expected_names = set(manifest)
    actual_names = set(actual_paths)
    for missing in sorted(expected_names - actual_names):
        errors.append(f"RP-B4-0 file missing: {missing}")
    for unexpected in sorted(actual_names - expected_names):
        errors.append(f"unexpected research-core file: {unexpected}")
    for relative in sorted(expected_names & actual_names):
        actual_digest = hashlib.sha256(actual_paths[relative].read_bytes()).hexdigest()
        if actual_digest != manifest[relative]:
            errors.append(
                f"RP-B4-0 SHA mismatch: {relative} "
                f"(expected {manifest[relative]}, got {actual_digest})"
            )
    return errors


def run(project: Path, expected: ExpectedRun) -> list[str]:
    environment = os.environ.copy()
    environment.update({"PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    completed = subprocess.run(
        (sys.executable, *expected.arguments),
        cwd=project,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = completed.stdout.rstrip()
    print(f"\n===== {expected.name} | exit={completed.returncode} =====")
    print(output)
    errors: list[str] = []
    if completed.returncode != expected.exit_code:
        errors.append(
            f"{expected.name}: expected exit {expected.exit_code}, got {completed.returncode}"
        )
    for required in expected.required:
        if required not in output:
            errors.append(f"{expected.name}: missing output {required!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path("research_core/pcr_tw_project"),
    )
    arguments = parser.parse_args()
    original = arguments.project_root.resolve()
    if not original.is_dir():
        print(f"ERROR: research core not found: {original}", file=sys.stderr)
        return 2

    try:
        initial_files = source_files(original)
        errors = verify_tree(original)
    except SnapshotValidationError as exc:
        print(f"ERROR: unsafe research-core inventory: {exc}", file=sys.stderr)
        return 1
    if len(initial_files) != 48:
        errors.append(f"expected 48 research-core files, found {len(initial_files)}")
    for required in ("tools/validate_project.py", "tools/mutation_test.py"):
        if not (original / required).is_file():
            errors.append(f"missing required file: {required}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="pcr-b4-0-baseline-") as temporary:
        project = Path(temporary) / "pcr_tw_project"
        shutil.copytree(original, project)
        for expected in VALIDATOR_RUNS:
            errors.extend(run(project, expected))
            if expected.name == "PRE_SUITE --write":
                errors.extend(
                    f"post-write tree: {error}" for error in verify_tree(project)
                )

        mutation = ExpectedRun(
            "MUTATION",
            ("tools/mutation_test.py",),
            0,
            ("MUTATION_TESTS ALL_OK", "active_scenarios=122"),
        )
        errors.extend(run(project, mutation))
        errors.extend(f"post-mutation tree: {error}" for error in verify_tree(project))

    if errors:
        print("\nBASELINE_MISMATCH", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "\nRESEARCH_BASELINE_OK | files=48 | mutation_scenarios=122 "
        f"| manifest_sha256={EXPECTED_MANIFEST_SHA256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
