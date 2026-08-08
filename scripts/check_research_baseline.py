#!/usr/bin/env python3
"""Run the immutable R3i research-core baseline in a disposable copy."""

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


EXPECTED_MANIFEST_SHA256 = "c9aa323626b453afb7f694dd526f90121ce0bf59eda90b3a30a9d955157a773a"
MANIFEST_PATH = Path(__file__).with_name("research_core_rp_b0_0_manifest.sha256")
MANIFEST_LINE = re.compile(r"^([0-9a-f]{64})  ([^\\]+(?:/[^\\]+)*)$")


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
            "MODE=PRE_SUITE CHECKS=112 FAIL=0 WARN=16",
            "GateA=False GateB=False GateC=False blk=7",
            "canonical=Y",
        ),
    ),
    ExpectedRun(
        "PRE_SUITE",
        ("tools/validate_project.py", "--mode", "PRE_SUITE"),
        0,
        (
            "MODE=PRE_SUITE CHECKS=112 FAIL=0 WARN=16",
            "GateA=False GateB=False GateC=False blk=7",
            "canonical=Y",
        ),
    ),
    ExpectedRun(
        "OPERATIONAL",
        ("tools/validate_project.py", "--mode", "OPERATIONAL"),
        0,
        (
            "MODE=OPERATIONAL CHECKS=111 FAIL=0 WARN=15",
            "GateA=False GateB=False GateC=False blk=7",
            "canonical=N",
        ),
    ),
    ExpectedRun(
        "ARTIFACT_READY",
        ("tools/validate_project.py", "--mode", "ARTIFACT_READY"),
        1,
        (
            "MODE=ARTIFACT_READY CHECKS=114 FAIL=3 WARN=15",
            "GateA=False GateB=False GateC=False blk=7",
            "canonical=N",
            "ARTIFACT_READY 需 Gate A",
            "ARTIFACT_READY 需 Gate B",
            "ARTIFACT_READY 需 Gate C",
        ),
    ),
)


def source_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    )


def load_manifest() -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not MANIFEST_PATH.is_file():
        return {}, [f"missing RP-B0-0 manifest: {MANIFEST_PATH}"]
    lines = MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    canonical = ("\n".join(lines) + "\n").encode("utf-8")
    manifest_sha256 = hashlib.sha256(canonical).hexdigest()
    if manifest_sha256 != EXPECTED_MANIFEST_SHA256:
        errors.append(
            "RP-B0-0 manifest digest mismatch "
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
    if len(entries) != 46:
        errors.append(f"expected 46 manifest entries, found {len(entries)}")
    return entries, errors


def verify_tree(root: Path) -> list[str]:
    manifest, errors = load_manifest()
    actual_paths = {
        path.relative_to(root).as_posix(): path for path in source_files(root)
    }
    expected_names = set(manifest)
    actual_names = set(actual_paths)
    for missing in sorted(expected_names - actual_names):
        errors.append(f"RP-B0-0 file missing: {missing}")
    for unexpected in sorted(actual_names - expected_names):
        errors.append(f"unexpected research-core file: {unexpected}")
    for relative in sorted(expected_names & actual_names):
        actual_digest = hashlib.sha256(actual_paths[relative].read_bytes()).hexdigest()
        if actual_digest != manifest[relative]:
            errors.append(
                f"RP-B0-0 SHA mismatch: {relative} "
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

    initial_files = source_files(original)
    errors = verify_tree(original)
    if len(initial_files) != 46:
        errors.append(f"expected 46 research-core files, found {len(initial_files)}")
    for required in ("tools/validate_project.py", "tools/mutation_test.py"):
        if not (original / required).is_file():
            errors.append(f"missing required file: {required}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="pcr-r3i-baseline-") as temporary:
        project = Path(temporary) / "pcr_tw_project"
        shutil.copytree(original, project)
        for expected in VALIDATOR_RUNS:
            errors.extend(run(project, expected))

        mutation = ExpectedRun(
            "MUTATION",
            ("tools/mutation_test.py",),
            0,
            ("MUTATION_TESTS ALL_OK", "active_scenarios=54"),
        )
        errors.extend(run(project, mutation))

    if errors:
        print("\nBASELINE_MISMATCH", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "\nRESEARCH_BASELINE_OK | files=46 | mutation_scenarios=54 "
        f"| manifest_sha256={EXPECTED_MANIFEST_SHA256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
