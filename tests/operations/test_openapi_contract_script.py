from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("canonical_fragment", "drifted_fragment", "expected_field", "removed_literal"),
    [
        (
            """export type OperationMode =
  | \"AUTO\"
  | \"SEMI_AUTO\"
  | \"MANUAL_TIMELINE\"
  | \"SOURCE_CONFLICT\"
  | \"UNKNOWN\";""",
            """export type OperationMode =
  | \"AUTO\"
  | \"SEMI_AUTO\"
  | \"MANUAL_TIMELINE\"
  | \"SOURCE_CONFLICT\";""",
            "TeamSummary.operation_mode type differs",
            "UNKNOWN",
        ),
        (
            """export type TimelineTriggerType =
  | \"CLOCK\"
  | \"UB_READY\"
  | \"ANIMATION_CUE\"
  | \"HP_THRESHOLD\"
  | \"WAVE_START\"
  | \"BOSS_ACTION\"
  | \"SOURCE_TEXT_ONLY\";""",
            """export type TimelineTriggerType =
  | \"CLOCK\"
  | \"UB_READY\"
  | \"ANIMATION_CUE\"
  | \"HP_THRESHOLD\"
  | \"WAVE_START\"
  | \"BOSS_ACTION\";""",
            "TimelineStepData.trigger_type type differs",
            "SOURCE_TEXT_ONLY",
        ),
        (
            """export type TimelineActionType =
  | \"USE_UB\"
  | \"WAIT\"
  | \"AUTO_ON\"
  | \"AUTO_OFF\"
  | \"SET_ON\"
  | \"SET_OFF\"
  | \"PAUSE\"
  | \"RESUME\"
  | \"TARGET\"
  | \"NO_ACTION\";""",
            """export type TimelineActionType =
  | \"USE_UB\"
  | \"WAIT\"
  | \"AUTO_ON\"
  | \"AUTO_OFF\"
  | \"SET_ON\"
  | \"SET_OFF\"
  | \"PAUSE\"
  | \"RESUME\"
  | \"TARGET\";""",
            "TimelineStepData.action_type type differs",
            "NO_ACTION",
        ),
        (
            """export type GachaLimitedStatus = "YES" | "NO" | "UNKNOWN";""",
            """export type GachaLimitedStatus = "YES" | "NO";""",
            "GachaTimelineEventData.limited_status type differs",
            "UNKNOWN",
        ),
        (
            """export type GachaMaturity = "MATURE" | "RESEARCH";""",
            """export type GachaMaturity = "MATURE";""",
            "GachaTimelineEventData.maturity type differs",
            "RESEARCH",
        ),
        (
            """export type GachaCommunityConfidenceCap = "C" | "D" | "E";""",
            """export type GachaCommunityConfidenceCap = "B" | "C" | "D" | "E";""",
            "GachaCommunitySourceData.confidence_cap type differs",
            "B",
        ),
    ],
)
def test_contract_checker_rejects_enum_drift(
    tmp_path: Path,
    canonical_fragment: str,
    drifted_fragment: str,
    expected_field: str,
    removed_literal: str,
) -> None:
    node = shutil.which("node")
    if node is None or not (ROOT / "node_modules" / "typescript").is_dir():
        pytest.skip("Node.js workspace dependencies are unavailable")

    canonical = (ROOT / "packages" / "api-client" / "src" / "types.ts").read_text(
        encoding="utf-8"
    )
    assert canonical.count(canonical_fragment) == 1

    drifted_types = tmp_path / "types.ts"
    drifted_types.write_text(
        canonical.replace(canonical_fragment, drifted_fragment),
        encoding="utf-8",
        newline="\n",
    )
    environment = os.environ.copy()
    environment.update(
        {
            "PCR_API_CLIENT_TYPES": str(drifted_types),
            "PCR_OPENAPI_PYTHON": sys.executable,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )

    completed = subprocess.run(
        [node, "scripts/check-openapi-contract.mjs"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    output = completed.stdout + completed.stderr
    assert completed.returncode == 1
    assert expected_field in output
    assert f'"{removed_literal}"' in output
