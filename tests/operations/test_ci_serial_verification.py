from __future__ import annotations

import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
INFRA_README = REPOSITORY_ROOT / "infra" / "README.md"

PRE_RELEASE_VERIFIERS = (
    "scheduler-smoke",
    "round-trip-smoke",
    "consistency-smoke",
    "cache-epoch-smoke",
    "artifact-lock-smoke",
)
POST_RELEASE_VERIFIERS = (
    "revision-history-smoke",
    "revision-history-verify",
)
ORDERED_VERIFICATION_PIPELINE = PRE_RELEASE_VERIFIERS + POST_RELEASE_VERIFIERS
RELEASE_OPERATIONS = (
    "./scripts/backup_restore_smoke.ps1",
    "./scripts/a6_b5_rollback_drill.ps1",
)


def _nonempty_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_release_safe_serial_pipeline(lines: list[str]) -> None:
    base_up = [
        index
        for index, line in enumerate(lines)
        if "docker compose" in line and " up " in f" {line} "
    ]
    assert len(base_up) == 1
    assert "--profile" not in lines[base_up[0]]

    verifier_lines: list[tuple[int, str]] = []
    for service in ORDERED_VERIFICATION_PIPELINE:
        matches = [
            (index, line)
            for index, line in enumerate(lines)
            if "docker compose" in line and line.endswith(service)
        ]
        assert len(matches) == 1
        index, command = matches[0]
        assert "--profile verification" in command
        assert re.search(r"\brun\s+--rm\s+--no-deps\b", command)
        verifier_lines.append((index, command))

    indices = [index for index, _ in verifier_lines]
    assert base_up[0] < indices[0]
    assert indices == sorted(indices)

    operation_indices: list[int] = []
    for operation in RELEASE_OPERATIONS:
        matches = [index for index, line in enumerate(lines) if operation in line]
        assert len(matches) == 1
        operation_indices.append(matches[0])

    pre_release_end = indices[len(PRE_RELEASE_VERIFIERS) - 1]
    post_release_start = indices[len(PRE_RELEASE_VERIFIERS)]
    assert pre_release_end < operation_indices[0] < operation_indices[1]
    assert operation_indices[1] < post_release_start


def test_ci_starts_only_base_stack_then_runs_stateful_verifiers_serially() -> None:
    lines = _nonempty_lines(CI_WORKFLOW)
    _assert_release_safe_serial_pipeline(lines)
    assert not any(
        "docker compose" in line
        and "--profile verification" in line
        and " up " in f" {line} "
        for line in lines
    )


def test_documented_local_command_uses_the_same_fail_closed_order() -> None:
    lines = _nonempty_lines(INFRA_README)
    _assert_release_safe_serial_pipeline(lines)
    readme = INFRA_README.read_text(encoding="utf-8")
    assert re.search(
        r"不得用\s+`docker compose --profile verification \.\.\. up` 併發啟動。",
        readme,
    )
