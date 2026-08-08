from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from pcr_database.models import (
    Character,
    Claim,
    ClaimEvidence,
    Evidence,
    CoreRevision,
    ImportRun,
    MaterializationState,
    OperationTimeline,
    RevisionActivation,
    Stage,
    StageClaim,
    StageEvidence,
    Team,
    TeamEvidence,
    TeamMember,
    TimelineStep,
)
from pcr_database.materialization import (
    build_materialization_manifest,
    materialization_drift_reason,
)
from pcr_pipeline.research_core_snapshot import (
    DEFAULT_MANIFEST,
    EXPECTED_MANIFEST_SHA256,
    ResearchCoreSnapshot,
    assert_materialized_snapshot,
    finalize_materialized_snapshot,
    load_research_core_snapshot,
    materialize_snapshot,
)


# Compatibility identifier for the original B0 vertical-slice API.  The typed
# projection itself is no longer restricted to this guide.
TARGET_GUIDE_ID = "TW_DEEP_FIRE_08_10_20260802"
APPLICATION_VERSION = "3.0.0-a3"
CANONICAL_SOURCE = "research_core_file_ssot"
IMPORT_LOCK_KEY = 0x5043524231
FULL_PVE_PROJECTION = "pve_18_24_25_26_27_closure_v2"
LEGACY_FIRE_PROJECTION = "fire_8_10_18_24_25_26_27_closure_v1"
# rp-b1-1 / rp-a2 raw tree.  Its historical ImportRun materialized only the
# Fire 8-10 vertical slice.  Keeping this identity code-owned makes a clean
# restore deterministic even when no historical database row is present yet.
LEGACY_FIRE_REVISION_IDS = frozenset(
    {"fd3f1a0a102873ad4a0f0248e24f52cfc0e4e2e7f371e3abe35fd6848ba00900"}
)

# The PVE projection may only materialize Evidence from this reviewed host
# boundary. Restricted/China sources are deliberately absent and can never
# become a public href merely by editing the ledger.
B0_AUDITED_EVIDENCE_HOSTS = frozenset(
    {
        "games.appmatch.jp",
        "gamewith.jp",
        "priconne-redive.jp",
        "www.nicozon.net",
        "www.princessconnect.so-net.tw",
        "www.youtube.com",
    }
)

SOURCE_FILES = (
    "18_TW_CHARACTER_AVAILABILITY.csv",
    "24_PVE_GUIDE_REGISTRY.csv",
    "25_PVE_TEAM_REGISTRY.csv",
    "26_PVE_OPERATION_TIMELINES.csv",
    "27_PVE_TIMELINE_STEPS.csv",
    "92_EVIDENCE_LEDGER.csv",
    "93_CLAIM_REGISTER.csv",
    "tools/stats.json",
)

TIMELINE_OPERATION_MODES = frozenset(
    {"AUTO", "SEMI_AUTO", "MANUAL_TIMELINE", "UNKNOWN"}
)
TIMELINE_CLOCK_MODES = frozenset({"COUNTDOWN", "ELAPSED", "UNKNOWN"})
TIMELINE_AUTO_STATES = frozenset({"ON", "OFF", "UNKNOWN"})
TIMELINE_REPRODUCIBILITY = frozenset({"UNVERIFIED_ON_TW", "TW_REPRODUCED", "UNKNOWN"})
TIMELINE_GAP_REASONS = frozenset(
    {"NONE", "INSUFFICIENT_SOURCE_DETAIL", "PENDING_EXTRACTION"}
)
TIMELINE_TRIGGERS = frozenset(
    {
        "CLOCK",
        "UB_READY",
        "ANIMATION_CUE",
        "HP_THRESHOLD",
        "WAVE_START",
        "BOSS_ACTION",
        "SOURCE_TEXT_ONLY",
    }
)
TIMELINE_ACTIONS = frozenset(
    {
        "USE_UB",
        "WAIT",
        "AUTO_ON",
        "AUTO_OFF",
        "SET_ON",
        "SET_OFF",
        "PAUSE",
        "RESUME",
        "TARGET",
        "NO_ACTION",
    }
)
TIMELINE_CRITICALITIES = frozenset({"NORMAL", "CRITICAL", "UNKNOWN"})
TIMELINE_TIME_STATES = frozenset({"STATED", "NOT_STATED"})
PVE_CLEAR_STATUSES = frozenset({"VERIFIED", "PROVISIONAL", "STALE"})
PVE_TW_CHECKS = frozenset({"PASS", "FAIL", "UNVERIFIED"})
PVE_OPERATION_MODES = frozenset(
    {"AUTO", "SEMI_AUTO", "MANUAL_TIMELINE", "SOURCE_CONFLICT", "UNKNOWN"}
)

# This audited boundary records what the actually opened source states.  It is
# deliberately code-owned: editing a CSV cannot turn an unstated time into a
# canonical value or invent a battle duration.
AUDITED_TIMELINE_TIME_BOUNDARIES = {
    "AX-F810-02-EV073": {
        "battle_duration_ms": "UNKNOWN",
        "criticality": "UNKNOWN",
        "source_locator_prefix": "2025年9月魔法半自動／手順",
        "source_step_numbers": frozenset(range(1, 9)),
        "not_stated_source_steps": frozenset({1}),
    }
}


class FixtureValidationError(ValueError):
    """Raised before any write when the file closure is incomplete or inconsistent."""


class MirrorDriftError(RuntimeError):
    """Raised when a supposedly imported fixture is no longer materialized exactly."""


@dataclass(frozen=True)
class FixtureClosure:
    fingerprint: str
    guides: tuple[dict[str, str], ...]
    teams: tuple[dict[str, str], ...]
    characters: tuple[dict[str, str], ...]
    evidence: tuple[dict[str, str], ...]
    claims: tuple[dict[str, str], ...]
    timelines: tuple[dict[str, str], ...]
    timeline_steps: tuple[dict[str, str], ...]
    stage_evidence_ids_by_guide: dict[str, tuple[str, ...]]
    stage_claim_ids_by_guide: dict[str, tuple[str, ...]]
    team_evidence_ids: dict[str, tuple[str, ...]]
    dangling_claim_ids: tuple[str, ...]
    stats: dict[str, Any]
    file_hashes: dict[str, str]

    @property
    def guide(self) -> dict[str, str]:
        """Return the historical Fire 8-10 guide for compatibility callers."""

        for guide in self.guides:
            if guide["guide_id"] == TARGET_GUIDE_ID:
                return guide
        raise FixtureValidationError(
            f"compatibility guide {TARGET_GUIDE_ID} is absent from this PVE closure"
        )

    @property
    def stage_evidence_ids(self) -> tuple[str, ...]:
        """Return historical Fire 8-10 stage Evidence links."""

        return self.stage_evidence_ids_by_guide.get(TARGET_GUIDE_ID, ())

    @property
    def stage_claim_ids(self) -> tuple[str, ...]:
        """Return historical Fire 8-10 stage Claim links."""

        return self.stage_claim_ids_by_guide.get(TARGET_GUIDE_ID, ())


@dataclass(frozen=True)
class ImportResult:
    import_run_id: str
    fixture_sha256: str
    created: bool
    activated: bool
    revision_id: str
    raw_tree_sha256: str
    semantic_tree_sha256: str
    file_count: int
    csv_file_count: int
    csv_row_count: int
    row_counts: dict[str, int]
    warnings: tuple[str, ...]


def _split_ids(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(";") if item.strip())


def _parse_date(value: str, *, field: str, required: bool = False) -> date | None:
    normalized = value.strip()
    if not normalized or normalized in {"—", "-"}:
        if required:
            raise FixtureValidationError(f"{field} must be an ISO date")
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise FixtureValidationError(f"{field} is not an ISO date: {value!r}") from exc


def _parse_published_date(
    value: str,
    *,
    precision: str,
    field: str,
) -> date | None:
    """Normalize a precision-qualified source date for the SQL ``Date`` type.

    MONTH/YEAR values use the interval's lower bound only as storage
    normalization; ``published_date_precision`` remains authoritative, so this
    does not strengthen the source to day precision.
    """

    normalized = value.strip()
    normalized_precision = precision.strip()
    if not normalized or normalized in {"—", "-"}:
        return None
    formats = {
        "DAY": "%Y-%m-%d",
        "MONTH": "%Y-%m",
        "YEAR": "%Y",
    }
    date_format = formats.get(normalized_precision)
    if date_format is None:
        raise FixtureValidationError(
            f"{field} has a value without DAY/MONTH/YEAR precision"
        )
    try:
        return datetime.strptime(normalized, date_format).date()
    except ValueError as exc:
        raise FixtureValidationError(
            f"{field} does not match {normalized_precision} precision: {value!r}"
        ) from exc


def _parse_int(
    value: str,
    *,
    field: str,
    allow_unknown: bool = False,
    positive: bool = False,
) -> int | None:
    normalized = value.strip()
    if allow_unknown and normalized == "UNKNOWN":
        return None
    if not normalized.isdigit():
        raise FixtureValidationError(f"{field} must be an unsigned integer")
    parsed = int(normalized)
    if positive and parsed < 1:
        raise FixtureValidationError(f"{field} must be a positive integer")
    return parsed


def _unit_or_none(value: str) -> str | None:
    return None if value == "NONE" else value


def _read_csv(
    relative_path: str,
    content: bytes,
    key: str,
) -> tuple[dict[str, str], ...]:
    try:
        text_content = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FixtureValidationError(f"{relative_path} must be UTF-8") from exc
    with io.StringIO(text_content, newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or key not in reader.fieldnames:
            raise FixtureValidationError(f"{relative_path} is missing key column {key}")
        rows = tuple({name: value or "" for name, value in row.items()} for row in reader)
    values = [row[key] for row in rows]
    if len(values) != len(set(values)):
        raise FixtureValidationError(f"{relative_path} contains duplicate {key}")
    return rows


def _require_ids(
    ids: Iterable[str], rows: dict[str, dict[str, str]], *, relation: str
) -> None:
    missing = sorted(set(ids) - rows.keys())
    if missing:
        raise FixtureValidationError(f"{relation} references missing ids: {missing}")


def _validate_evidence_url(row: dict[str, str]) -> None:
    url = row["source_url"].strip()
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme.lower() != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or host not in B0_AUDITED_EVIDENCE_HOSTS
    ):
        raise FixtureValidationError(
            f"{row['evidence_id']} source_url is not an audited HTTPS source"
        )


def _capture_source_files(root: Path) -> dict[str, bytes]:
    return {relative: (root / relative).read_bytes() for relative in SOURCE_FILES}


def _file_fingerprint(
    source_contents: dict[str, bytes],
) -> tuple[str, dict[str, str]]:
    digest = hashlib.sha256()
    file_hashes: dict[str, str] = {}
    for relative in SOURCE_FILES:
        content = source_contents[relative]
        current = hashlib.sha256(content).hexdigest()
        file_hashes[relative] = current
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest(), file_hashes


def _validate_requirements(team: dict[str, str]) -> dict[str, Any]:
    raw = team["requirements"]
    try:
        requirements = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FixtureValidationError(f"{team['team_id']} requirements is malformed JSON") from exc
    expected_top_level = {
        "schema_version",
        "operation_mode_claims",
        "slots",
        "support",
        "timeline_ref",
        "failure_conditions",
    }
    if (
        not isinstance(requirements, dict)
        or set(requirements) != expected_top_level
        or requirements.get("schema_version") != "1.0"
    ):
        raise FixtureValidationError(
            f"{team['team_id']} requirements must use the complete 1.0 schema"
        )

    canonical = json.dumps(requirements, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if raw != canonical:
        raise FixtureValidationError(f"{team['team_id']} requirements is not canonical JSON")

    slots = requirements.get("slots")
    expected_slots = {f"slot{number}" for number in range(1, 6)}
    expected_fields = {
        "connect_rank",
        "element_boost",
        "rank",
        "six_star",
        "star",
        "ue1",
        "ue2",
    }
    if not isinstance(slots, dict) or set(slots) != expected_slots:
        raise FixtureValidationError(f"{team['team_id']} requirements must contain slot1..slot5")
    for slot_name, values in slots.items():
        if not isinstance(values, dict) or set(values) != expected_fields:
            raise FixtureValidationError(
                f"{team['team_id']} {slot_name} requirements fields are incomplete"
            )
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            raise FixtureValidationError(f"{team['team_id']} {slot_name} contains blank facts")

    claims = requirements.get("operation_mode_claims")
    if not isinstance(claims, list) or not claims:
        raise FixtureValidationError(f"{team['team_id']} has no operation_mode_claims")
    if any(
        not isinstance(item, dict)
        or set(item) != {"source_id", "mode"}
        or not isinstance(item.get("source_id"), str)
        or not item["source_id"].strip()
        or item.get("mode") not in TIMELINE_OPERATION_MODES
        for item in claims
    ):
        raise FixtureValidationError(
            f"{team['team_id']} operation_mode_claims contain an invalid source or mode"
        )
    claim_sources = [item["source_id"] for item in claims]
    if len(claim_sources) != len(set(claim_sources)):
        raise FixtureValidationError(
            f"{team['team_id']} operation_mode_claims contain duplicate sources"
        )
    row_sources = set(_split_ids(team["source_ids"]))
    missing_row_sources = sorted(set(claim_sources) - row_sources)
    if missing_row_sources:
        raise FixtureValidationError(
            f"{team['team_id']} operation_mode_claims are outside source_ids: "
            f"{missing_row_sources}"
        )
    modes = {item["mode"] for item in claims}
    if team["operation_mode"] == "SOURCE_CONFLICT" and len(modes) < 2:
        raise FixtureValidationError(
            f"{team['team_id']} SOURCE_CONFLICT must preserve conflicting source modes"
        )
    if team["operation_mode"] != "SOURCE_CONFLICT" and modes != {team["operation_mode"]}:
        raise FixtureValidationError(
            f"{team['team_id']} operation mode differs from its source claims"
        )
    timeline_ref = requirements.get("timeline_ref")
    if not isinstance(timeline_ref, str) or not _split_ids(timeline_ref):
        raise FixtureValidationError(f"{team['team_id']} has no source-axis timeline_ref")
    support = requirements.get("support")
    if (
        not isinstance(support, dict)
        or set(support) != {"unit", "requirements"}
        or any(
            not isinstance(value, str) or not value.strip()
            for value in support.values()
        )
    ):
        raise FixtureValidationError(
            f"{team['team_id']} support requirements are incomplete"
        )
    failure_conditions = requirements.get("failure_conditions")
    if (
        not isinstance(failure_conditions, list)
        or not failure_conditions
        or any(
            not isinstance(value, str) or not value.strip()
            for value in failure_conditions
        )
    ):
        raise FixtureValidationError(
            f"{team['team_id']} failure_conditions are incomplete"
        )
    return requirements


def _validate_timeline_closure(
    *,
    teams: tuple[dict[str, str], ...],
    requirements_by_team: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, str]],
    team_evidence_ids: dict[str, tuple[str, ...]],
    timelines_all: tuple[dict[str, str], ...],
    steps_all: tuple[dict[str, str], ...],
) -> tuple[tuple[dict[str, str], ...], tuple[dict[str, str], ...]]:
    teams_by_id = {team["team_id"]: team for team in teams}
    unknown_timeline_teams = sorted(
        {row["team_id"] for row in timelines_all} - teams_by_id.keys()
    )
    if unknown_timeline_teams:
        raise FixtureValidationError(
            "operation timelines reference missing teams: "
            f"{unknown_timeline_teams}"
        )
    timelines = tuple(
        sorted(
            (row for row in timelines_all if row["team_id"] in teams_by_id),
            key=lambda row: row["source_axis_id"],
        )
    )
    pairs = [(row["team_id"], row["source_id"]) for row in timelines]
    if len(pairs) != len(set(pairs)):
        raise FixtureValidationError("operation timelines duplicate a team/source axis")

    structured_ids = [
        row["timeline_id"] for row in timelines if row["status"] == "STRUCTURED"
    ]
    if len(structured_ids) != len(set(structured_ids)):
        raise FixtureValidationError("structured timeline_id values must be unique")
    steps = tuple(
        sorted(
            (row for row in steps_all if row["timeline_id"] in set(structured_ids)),
            key=lambda row: (row["timeline_id"], int(row["sequence_no"]) if row["sequence_no"].isdigit() else -1),
        )
    )
    known_structured_ids = {
        row["timeline_id"]
        for row in timelines
        if row["status"] == "STRUCTURED" and row["timeline_id"] != "UNKNOWN"
    }
    orphan_step_ids = sorted(
        {row["timeline_id"] for row in steps_all} - known_structured_ids
    )
    if orphan_step_ids:
        raise FixtureValidationError(
            f"timeline steps reference non-structured timelines: {orphan_step_ids}"
        )

    for timeline in timelines:
        axis_id = timeline["source_axis_id"]
        team = teams_by_id[timeline["team_id"]]
        requirements = requirements_by_team[timeline["team_id"]]
        source_claims = {
            item.get("source_id"): item.get("mode")
            for item in requirements["operation_mode_claims"]
            if isinstance(item, dict)
        }
        if source_claims.get(timeline["source_id"]) != timeline["operation_mode"]:
            raise FixtureValidationError(
                f"{axis_id} operation mode differs from its team source claim"
            )
        if timeline["operation_mode"] not in TIMELINE_OPERATION_MODES:
            raise FixtureValidationError(f"{axis_id} operation_mode is invalid")
        evidence_id = timeline["source_evidence_id"]
        evidence = evidence_by_id.get(evidence_id)
        if (
            evidence is None
            or evidence_id not in team_evidence_ids[timeline["team_id"]]
            or evidence["status"] != "ACTIVE"
        ):
            raise FixtureValidationError(f"{axis_id} source evidence is outside its team closure")
        evidence_locator = evidence["source_locator"]
        if not (
            timeline["source_locator"] == evidence_locator
            or timeline["source_locator"].startswith(f"{evidence_locator}#")
        ):
            raise FixtureValidationError(
                f"{axis_id} locator is not the Evidence locator or its # sub-location"
            )
        if (
            timeline["clock_mode"] not in TIMELINE_CLOCK_MODES
            or timeline["initial_auto_state"] not in TIMELINE_AUTO_STATES
            or timeline["reproducibility"] not in TIMELINE_REPRODUCIBILITY
            or timeline["gap_reason"] not in TIMELINE_GAP_REASONS
        ):
            raise FixtureValidationError(f"{axis_id} contains an invalid timeline enum")
        for field in ("source_locator", "timeline_variant_name", "notes"):
            if not timeline[field].strip():
                raise FixtureValidationError(f"{axis_id}.{field} must not be blank")
        _parse_date(
            timeline["last_verified_at"],
            field=f"{axis_id}.last_verified_at",
            required=True,
        )

        if timeline["status"] == "STRUCTURED":
            if (
                timeline["timeline_id"] == "UNKNOWN"
                or timeline["clock_mode"] == "UNKNOWN"
                or timeline["initial_auto_state"] == "UNKNOWN"
                or timeline["gap_reason"] != "NONE"
            ):
                raise FixtureValidationError(f"{axis_id} STRUCTURED state shape is invalid")
            _parse_int(
                timeline["battle_duration_ms"],
                field=f"{axis_id}.battle_duration_ms",
                allow_unknown=True,
                positive=True,
            )
            if (
                team["server"] == "TW"
                and evidence["server"] != "TW"
                and timeline["reproducibility"] != "UNVERIFIED_ON_TW"
            ):
                raise FixtureValidationError(
                    f"{axis_id} cross-server timeline must remain UNVERIFIED_ON_TW"
                )
            if timeline["reproducibility"] == "TW_REPRODUCED" and evidence["server"] != "TW":
                raise FixtureValidationError(
                    f"{axis_id} non-TW evidence cannot claim TW_REPRODUCED"
                )
        elif timeline["status"] == "SOURCE_GAP":
            if (
                timeline["timeline_id"] != "UNKNOWN"
                or timeline["clock_mode"] != "UNKNOWN"
                or timeline["battle_duration_ms"] != "UNKNOWN"
                or timeline["initial_auto_state"] != "UNKNOWN"
                or timeline["reproducibility"] != "UNKNOWN"
                or timeline["gap_reason"] == "NONE"
            ):
                raise FixtureValidationError(f"{axis_id} SOURCE_GAP state shape is invalid")
        else:
            raise FixtureValidationError(f"{axis_id} status is invalid")

        boundary = AUDITED_TIMELINE_TIME_BOUNDARIES.get(axis_id)
        if boundary and timeline["battle_duration_ms"] != boundary["battle_duration_ms"]:
            raise FixtureValidationError(f"{axis_id} invents an unstated battle duration")

    for team in teams:
        declared_axes = set(_split_ids(requirements_by_team[team["team_id"]].get("timeline_ref", "")))
        actual_axes = {
            timeline["source_axis_id"]
            for timeline in timelines
            if timeline["team_id"] == team["team_id"]
        }
        if declared_axes != actual_axes:
            raise FixtureValidationError(
                f"{team['team_id']} timeline_ref differs from its source_axis_id closure"
            )
        if (
            team["operation_mode"] not in {"SEMI_AUTO", "MANUAL_TIMELINE", "SOURCE_CONFLICT"}
        ):
            continue
        expected = {
            (item["source_id"], item["mode"])
            for item in requirements_by_team[team["team_id"]]["operation_mode_claims"]
        }
        actual = {
            (timeline["source_id"], timeline["operation_mode"])
            for timeline in timelines
            if timeline["team_id"] == team["team_id"]
        }
        if actual != expected:
            raise FixtureValidationError(
                f"{team['team_id']} operation timeline source closure is incomplete"
            )

    timeline_by_id = {
        timeline["timeline_id"]: timeline
        for timeline in timelines
        if timeline["status"] == "STRUCTURED"
    }
    steps_by_timeline: dict[str, list[dict[str, str]]] = {
        timeline_id: [] for timeline_id in timeline_by_id
    }
    for step in steps:
        timeline = timeline_by_id[step["timeline_id"]]
        team = teams_by_id[timeline["team_id"]]
        members = {team[f"slot{slot}"] for slot in range(1, 6)}
        step_id = step["timeline_step_id"]
        sequence_no = _parse_int(
            step["sequence_no"], field=f"{step_id}.sequence_no", positive=True
        )
        source_step_no = _parse_int(
            step["source_step_no"], field=f"{step_id}.source_step_no", positive=True
        )
        assert sequence_no is not None and source_step_no is not None
        if (
            step["trigger_type"] not in TIMELINE_TRIGGERS
            or step["time_state"] not in TIMELINE_TIME_STATES
            or step["action_type"] not in TIMELINE_ACTIONS
            or step["auto_state_after"] not in TIMELINE_AUTO_STATES
            or step["criticality"] not in TIMELINE_CRITICALITIES
        ):
            raise FixtureValidationError(f"{step_id} contains an invalid timeline step enum")

        if step["time_state"] == "STATED":
            clock_from = _parse_int(step["clock_from_ms"], field=f"{step_id}.clock_from_ms")
            clock_to = _parse_int(step["clock_to_ms"], field=f"{step_id}.clock_to_ms")
            assert clock_from is not None and clock_to is not None
            if timeline["clock_mode"] == "COUNTDOWN" and clock_from < clock_to:
                raise FixtureValidationError(f"{step_id} countdown range is reversed")
            if timeline["clock_mode"] == "ELAPSED" and clock_from > clock_to:
                raise FixtureValidationError(f"{step_id} elapsed range is reversed")
            duration = _parse_int(
                timeline["battle_duration_ms"],
                field=f"{timeline['source_axis_id']}.battle_duration_ms",
                allow_unknown=True,
                positive=True,
            )
            if duration is not None and (clock_from > duration or clock_to > duration):
                raise FixtureValidationError(f"{step_id} exceeds its stated battle duration")
        elif step["clock_from_ms"] != "UNKNOWN" or step["clock_to_ms"] != "UNKNOWN":
            raise FixtureValidationError(f"{step_id} invents a time not stated by the source")

        _parse_int(
            step["tolerance_ms"],
            field=f"{step_id}.tolerance_ms",
            allow_unknown=True,
        )
        for key in ("trigger_actor_unit_key", "actor_unit_key", "target_unit_key"):
            if step[key] != "NONE" and step[key] not in members:
                raise FixtureValidationError(f"{step_id}.{key} is not a member of its team")
        if (
            step["action_type"] in {"USE_UB", "SET_ON", "SET_OFF", "TARGET"}
            and step["actor_unit_key"] not in members
        ):
            raise FixtureValidationError(f"{step_id} action requires a team actor")
        if step["action_type"] == "TARGET" and step["target_unit_key"] not in members:
            raise FixtureValidationError(f"{step_id} TARGET requires a team target")
        for field in (
            "animation_cue",
            "hp_threshold",
            "tolerance_ms",
            "instruction_zh_tw",
            "failure_if_missed",
            "source_locator",
        ):
            if not step[field].strip():
                raise FixtureValidationError(f"{step_id}.{field} must not be blank")

        boundary = AUDITED_TIMELINE_TIME_BOUNDARIES.get(timeline["source_axis_id"])
        if (
            boundary
            and source_step_no in boundary["not_stated_source_steps"]
            and step["time_state"] != "NOT_STATED"
        ):
            raise FixtureValidationError(f"{step_id} strengthens an unstated source time")
        steps_by_timeline[step["timeline_id"]].append(step)

    for timeline_id, timeline_steps in steps_by_timeline.items():
        ordered_steps = sorted(timeline_steps, key=lambda step: int(step["sequence_no"]))
        sequence = [int(step["sequence_no"]) for step in ordered_steps]
        if sequence != list(range(1, len(timeline_steps) + 1)):
            raise FixtureValidationError(f"{timeline_id} sequence_no must be contiguous from 1")
        if not timeline_steps:
            raise FixtureValidationError(f"{timeline_id} STRUCTURED timeline has no steps")
        source_sequence = [int(step["source_step_no"]) for step in ordered_steps]
        if (
            source_sequence != sorted(source_sequence)
            or set(source_sequence) != set(range(1, max(source_sequence, default=0) + 1))
        ):
            raise FixtureValidationError(
                f"{timeline_id} source_step_no groups must be ordered and contiguous"
            )

        timeline = timeline_by_id[timeline_id]
        boundary = AUDITED_TIMELINE_TIME_BOUNDARIES.get(timeline["source_axis_id"])
        if boundary and (
            set(source_sequence) != boundary["source_step_numbers"]
            or any(
                step["source_locator"]
                != f"{boundary['source_locator_prefix']}{step['source_step_no']}"
                for step in ordered_steps
            )
            or any(
                step["criticality"] != boundary["criticality"]
                for step in ordered_steps
            )
        ):
            raise FixtureValidationError(
                f"{timeline['source_axis_id']} steps violate the audited source boundary"
            )

    return timelines, steps


def load_pve_closure(research_core: Path) -> FixtureClosure:
    """Load the complete typed PVE projection from canonical files 18/24/25/26/27.

    Every guide and team is retained.  A guide's declared ``team_count`` is
    checked against the canonical effective-team predicate, so PROVISIONAL or
    otherwise non-effective rows remain inspectable without being counted as
    verified clears.
    """

    root = research_core.resolve()
    missing_files = [relative for relative in SOURCE_FILES if not (root / relative).is_file()]
    if missing_files:
        raise FixtureValidationError(f"research core is missing files: {missing_files}")

    source_contents = _capture_source_files(root)
    fingerprint, file_hashes = _file_fingerprint(source_contents)
    characters_all = _read_csv(SOURCE_FILES[0], source_contents[SOURCE_FILES[0]], "unit_key")
    guides_all = _read_csv(SOURCE_FILES[1], source_contents[SOURCE_FILES[1]], "guide_id")
    teams_all = _read_csv(SOURCE_FILES[2], source_contents[SOURCE_FILES[2]], "team_id")
    timelines_all = _read_csv(
        SOURCE_FILES[3], source_contents[SOURCE_FILES[3]], "source_axis_id"
    )
    timeline_steps_all = _read_csv(
        SOURCE_FILES[4], source_contents[SOURCE_FILES[4]], "timeline_step_id"
    )
    evidence_all = _read_csv(
        SOURCE_FILES[5], source_contents[SOURCE_FILES[5]], "evidence_id"
    )
    claims_all = _read_csv(SOURCE_FILES[6], source_contents[SOURCE_FILES[6]], "claim_id")
    try:
        stats = json.loads(source_contents[SOURCE_FILES[7]].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FixtureValidationError(f"{SOURCE_FILES[7]} must be valid UTF-8 JSON") from exc

    characters = tuple(sorted(characters_all, key=lambda row: row["unit_key"]))
    guides = tuple(sorted(guides_all, key=lambda row: row["guide_id"]))
    teams = tuple(sorted(teams_all, key=lambda row: row["team_id"]))
    characters_by_id = {row["unit_key"]: row for row in characters}
    guides_by_id = {row["guide_id"]: row for row in guides_all}
    evidence_by_id = {row["evidence_id"]: row for row in evidence_all}
    claims_by_id = {row["claim_id"]: row for row in claims_all}

    unknown_team_guides = sorted(
        {team["guide_id"] for team in teams} - guides_by_id.keys()
    )
    if unknown_team_guides:
        raise FixtureValidationError(
            f"team guide_id references missing guides: {unknown_team_guides}"
        )

    available_unit_keys = {
        unit_key
        for unit_key, character in characters_by_id.items()
        if character["availability_status"] == "AVAILABLE"
    }
    team_evidence_ids: dict[str, tuple[str, ...]] = {}
    requirements_by_team: dict[str, dict[str, Any]] = {}
    effective_signatures_by_guide: dict[str, set[tuple[str, ...]]] = {
        guide["guide_id"]: set() for guide in guides
    }
    seen_stage_signatures: set[tuple[str, tuple[str, ...]]] = set()
    for team in teams:
        guide = guides_by_id[team["guide_id"]]
        expected_stage = f"{guide['area']}{guide['stage']}"
        if team["server"] != guide["server"] or team["stage"] != expected_stage:
            raise FixtureValidationError(
                f"{team['team_id']} server/stage differs from its guide relation"
            )
        if team["clear_status"] not in PVE_CLEAR_STATUSES:
            raise FixtureValidationError(
                f"{team['team_id']} clear_status is invalid"
            )
        if team["tw_availability_check"] not in PVE_TW_CHECKS:
            raise FixtureValidationError(
                f"{team['team_id']} tw_availability_check is invalid"
            )
        if team["operation_mode"] not in PVE_OPERATION_MODES:
            raise FixtureValidationError(
                f"{team['team_id']} operation_mode is invalid"
            )
        members = tuple(team[f"slot{slot}"] for slot in range(1, 6))
        if any(not member for member in members) or len(set(members)) != 5:
            raise FixtureValidationError(f"{team['team_id']} must contain five distinct units")
        _require_ids(members, characters_by_id, relation=f"{team['team_id']} slots")
        signature = tuple(sorted(members))
        stage_signature = (team["guide_id"], signature)
        if stage_signature in seen_stage_signatures:
            raise FixtureValidationError(
                f"duplicate stage five-unit signature at {team['team_id']}"
            )
        seen_stage_signatures.add(stage_signature)
        requirements_by_team[team["team_id"]] = _validate_requirements(team)
        support_slot = team["support_slot"].strip()
        if support_slot and support_slot not in {f"slot{slot}" for slot in range(1, 6)}:
            raise FixtureValidationError(f"{team['team_id']} support_slot is invalid")
        evidence_ids = _split_ids(team["evidence_ids"])
        _require_ids(
            evidence_ids,
            evidence_by_id,
            relation=f"{team['team_id']} evidence_ids",
        )
        team_evidence_ids[team["team_id"]] = evidence_ids
        _parse_date(
            team["verified_date"],
            field=f"{team['team_id']}.verified_date",
            required=True,
        )
        unavailable_members = sorted(set(members) - available_unit_keys)
        if team["tw_availability_check"] == "PASS" and unavailable_members:
            raise FixtureValidationError(
                f"{team['team_id']} PASS units are not TW AVAILABLE: "
                f"{unavailable_members}"
            )
        if (
            team["clear_status"] == "VERIFIED"
            and team["tw_availability_check"] == "PASS"
            and evidence_ids
        ):
            effective_signatures_by_guide[team["guide_id"]].add(signature)

    stage_evidence_ids_by_guide: dict[str, tuple[str, ...]] = {}
    stage_claim_ids_by_guide: dict[str, tuple[str, ...]] = {}
    for guide in guides:
        raw_team_count = guide["team_count"]
        if (
            not raw_team_count.isdigit()
            or (len(raw_team_count) > 1 and raw_team_count.startswith("0"))
        ):
            raise FixtureValidationError(
                f"{guide['guide_id']} team_count must be a canonical non-negative integer"
            )
        declared_team_count = int(raw_team_count)
        effective_team_count = len(effective_signatures_by_guide[guide["guide_id"]])
        if declared_team_count != effective_team_count:
            raise FixtureValidationError(
                f"{guide['guide_id']} team_count differs from the verified distinct "
                "five-unit team count"
            )
        evidence_ids = _split_ids(guide["evidence_ids"])
        claim_ids = _split_ids(guide["claim_ids"])
        _require_ids(
            evidence_ids,
            evidence_by_id,
            relation=f"{guide['guide_id']} evidence_ids",
        )
        _require_ids(
            claim_ids,
            claims_by_id,
            relation=f"{guide['guide_id']} claim_ids",
        )
        stage_evidence_ids_by_guide[guide["guide_id"]] = evidence_ids
        stage_claim_ids_by_guide[guide["guide_id"]] = claim_ids

    selected_evidence: set[str] = set()
    for ids in stage_evidence_ids_by_guide.values():
        selected_evidence.update(ids)
    for ids in team_evidence_ids.values():
        selected_evidence.update(ids)
    for character in characters:
        ids = _split_ids(character["source_evidence_ids"])
        _require_ids(ids, evidence_by_id, relation=f"{character['unit_key']} source_evidence_ids")
        selected_evidence.update(ids)

    selected_claims: set[str] = set()
    for ids in stage_claim_ids_by_guide.values():
        selected_claims.update(ids)
    dangling_claims: set[str] = set()
    changed = True
    while changed:
        changed = False
        for evidence_id in sorted(selected_evidence):
            declared_claim_id = evidence_by_id[evidence_id]["claim_id"].strip()
            if not declared_claim_id:
                continue
            if declared_claim_id in claims_by_id:
                if declared_claim_id not in selected_claims:
                    selected_claims.add(declared_claim_id)
                    changed = True
            else:
                dangling_claims.add(declared_claim_id)
        for claim_id in sorted(selected_claims):
            for evidence_id in _split_ids(claims_by_id[claim_id]["evidence_ids"]):
                if evidence_id not in evidence_by_id:
                    raise FixtureValidationError(
                        f"claim {claim_id} references missing evidence {evidence_id}"
                    )
                if evidence_id not in selected_evidence:
                    selected_evidence.add(evidence_id)
                    changed = True

    if dangling_claims:
        raise FixtureValidationError(
            "selected evidence references missing claims: "
            f"{sorted(dangling_claims)}"
        )

    evidence = tuple(evidence_by_id[key] for key in sorted(selected_evidence))
    for row in evidence:
        _validate_evidence_url(row)

    timelines, timeline_steps = _validate_timeline_closure(
        teams=teams,
        requirements_by_team=requirements_by_team,
        evidence_by_id=evidence_by_id,
        team_evidence_ids=team_evidence_ids,
        timelines_all=timelines_all,
        steps_all=timeline_steps_all,
    )

    return FixtureClosure(
        fingerprint=fingerprint,
        guides=guides,
        teams=teams,
        characters=characters,
        evidence=evidence,
        claims=tuple(claims_by_id[key] for key in sorted(selected_claims)),
        timelines=timelines,
        timeline_steps=timeline_steps,
        stage_evidence_ids_by_guide=stage_evidence_ids_by_guide,
        stage_claim_ids_by_guide=stage_claim_ids_by_guide,
        team_evidence_ids=team_evidence_ids,
        dangling_claim_ids=tuple(sorted(dangling_claims)),
        stats=stats,
        file_hashes=file_hashes,
    )


def _legacy_fire_projection(closure: FixtureClosure) -> FixtureClosure:
    """Rebuild the immutable B1 Fire 8-10 typed projection from a full closure."""

    guide = closure.guide
    teams = tuple(
        team for team in closure.teams if team["guide_id"] == TARGET_GUIDE_ID
    )
    team_ids = {team["team_id"] for team in teams}
    unit_keys = {
        team[f"slot{slot}"] for team in teams for slot in range(1, 6)
    }
    characters = tuple(
        character
        for character in closure.characters
        if character["unit_key"] in unit_keys
    )
    team_evidence_ids = {
        team_id: closure.team_evidence_ids[team_id] for team_id in sorted(team_ids)
    }

    evidence_by_id = {row["evidence_id"]: row for row in closure.evidence}
    claims_by_id = {row["claim_id"]: row for row in closure.claims}
    selected_evidence = set(closure.stage_evidence_ids)
    for evidence_ids in team_evidence_ids.values():
        selected_evidence.update(evidence_ids)
    for character in characters:
        selected_evidence.update(_split_ids(character["source_evidence_ids"]))
    selected_claims = set(closure.stage_claim_ids)

    changed = True
    while changed:
        changed = False
        for evidence_id in sorted(selected_evidence):
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                raise FixtureValidationError(
                    f"legacy Fire projection is missing evidence {evidence_id}"
                )
            declared_claim_id = evidence["claim_id"].strip()
            if declared_claim_id and declared_claim_id not in selected_claims:
                if declared_claim_id not in claims_by_id:
                    raise FixtureValidationError(
                        f"legacy Fire projection is missing claim {declared_claim_id}"
                    )
                selected_claims.add(declared_claim_id)
                changed = True
        for claim_id in sorted(selected_claims):
            claim = claims_by_id.get(claim_id)
            if claim is None:
                raise FixtureValidationError(
                    f"legacy Fire projection is missing claim {claim_id}"
                )
            for evidence_id in _split_ids(claim["evidence_ids"]):
                if evidence_id not in selected_evidence:
                    if evidence_id not in evidence_by_id:
                        raise FixtureValidationError(
                            f"legacy Fire projection is missing evidence {evidence_id}"
                        )
                    selected_evidence.add(evidence_id)
                    changed = True

    timelines = tuple(
        timeline for timeline in closure.timelines if timeline["team_id"] in team_ids
    )
    structured_timeline_ids = {
        timeline["timeline_id"]
        for timeline in timelines
        if timeline["status"] == "STRUCTURED"
    }
    timeline_steps = tuple(
        step
        for step in closure.timeline_steps
        if step["timeline_id"] in structured_timeline_ids
    )
    return FixtureClosure(
        fingerprint=closure.fingerprint,
        guides=(guide,),
        teams=teams,
        characters=characters,
        evidence=tuple(evidence_by_id[key] for key in sorted(selected_evidence)),
        claims=tuple(claims_by_id[key] for key in sorted(selected_claims)),
        timelines=timelines,
        timeline_steps=timeline_steps,
        stage_evidence_ids_by_guide={
            TARGET_GUIDE_ID: closure.stage_evidence_ids
        },
        stage_claim_ids_by_guide={TARGET_GUIDE_ID: closure.stage_claim_ids},
        team_evidence_ids=team_evidence_ids,
        dangling_claim_ids=(),
        stats=closure.stats,
        file_hashes=closure.file_hashes,
    )


def load_fire_8_10_closure(research_core: Path) -> FixtureClosure:
    """Compatibility wrapper; the returned closure now contains all PVE rows."""

    return load_pve_closure(research_core)


def _upsert(session: Session, model: type[Any], key: Any, values: dict[str, Any]) -> None:
    row = session.get(model, key)
    if row is None:
        session.add(model(**values))
        return
    for name, value in values.items():
        setattr(row, name, value)


def _timeline_values(row: dict[str, str], *, import_run_id: str) -> dict[str, Any]:
    axis_id = row["source_axis_id"]
    return {
        "source_axis_id": axis_id,
        "timeline_id": None if row["timeline_id"] == "UNKNOWN" else row["timeline_id"],
        "team_id": row["team_id"],
        "source_id": row["source_id"],
        "source_evidence_id": row["source_evidence_id"],
        "source_locator": row["source_locator"],
        "timeline_variant_name": row["timeline_variant_name"],
        "operation_mode": row["operation_mode"],
        "clock_mode": row["clock_mode"],
        "battle_duration_ms": _parse_int(
            row["battle_duration_ms"],
            field=f"{axis_id}.battle_duration_ms",
            allow_unknown=True,
            positive=True,
        ),
        "initial_auto_state": row["initial_auto_state"],
        "status": row["status"],
        "reproducibility": row["reproducibility"],
        "gap_reason": row["gap_reason"],
        "last_verified_at": _parse_date(
            row["last_verified_at"],
            field=f"{axis_id}.last_verified_at",
            required=True,
        ),
        "notes": row["notes"],
        "source_payload": row,
        "import_run_id": import_run_id,
    }


def _timeline_step_values(
    row: dict[str, str],
    *,
    team_id: str,
    import_run_id: str,
) -> dict[str, Any]:
    step_id = row["timeline_step_id"]
    return {
        "timeline_step_id": step_id,
        "timeline_id": row["timeline_id"],
        "team_id": team_id,
        "sequence_no": _parse_int(
            row["sequence_no"], field=f"{step_id}.sequence_no", positive=True
        ),
        "source_step_no": _parse_int(
            row["source_step_no"], field=f"{step_id}.source_step_no", positive=True
        ),
        "trigger_type": row["trigger_type"],
        "trigger_actor_unit_key": _unit_or_none(row["trigger_actor_unit_key"]),
        "time_state": row["time_state"],
        "clock_from_ms": _parse_int(
            row["clock_from_ms"],
            field=f"{step_id}.clock_from_ms",
            allow_unknown=True,
        ),
        "clock_to_ms": _parse_int(
            row["clock_to_ms"],
            field=f"{step_id}.clock_to_ms",
            allow_unknown=True,
        ),
        "actor_unit_key": _unit_or_none(row["actor_unit_key"]),
        "action_type": row["action_type"],
        "target_unit_key": _unit_or_none(row["target_unit_key"]),
        "auto_state_after": row["auto_state_after"],
        "animation_cue": row["animation_cue"],
        "hp_threshold": row["hp_threshold"],
        "tolerance_ms": _parse_int(
            row["tolerance_ms"],
            field=f"{step_id}.tolerance_ms",
            allow_unknown=True,
        ),
        "criticality": row["criticality"],
        "instruction_zh_tw": row["instruction_zh_tw"],
        "failure_if_missed": row["failure_if_missed"],
        "source_locator": row["source_locator"],
        "source_payload": row,
        "import_run_id": import_run_id,
    }


def _counts(closure: FixtureClosure) -> dict[str, int]:
    return {
        "stages": len(closure.guides),
        "teams": len(closure.teams),
        "team_members": len(closure.teams) * 5,
        "characters": len(closure.characters),
        "evidence": len(closure.evidence),
        "claims": len(closure.claims),
        "operation_timelines": len(closure.timelines),
        "timeline_steps": len(closure.timeline_steps),
    }


def _assert_materialized(session: Session, closure: FixtureClosure) -> None:
    expected_guide_ids = {row["guide_id"] for row in closure.guides}
    actual_guide_ids = set(session.scalars(select(Stage.guide_id)).all())
    if actual_guide_ids != expected_guide_ids:
        raise MirrorDriftError("idempotent fixture stage ids drifted")
    for source_row in closure.guides:
        stage = session.get(Stage, source_row["guide_id"])
        if (
            stage is None
            or stage.team_count != int(source_row["team_count"])
            or stage.source_payload != source_row
        ):
            raise MirrorDriftError(
                f"idempotent fixture stage {source_row['guide_id']} drifted"
            )

    expected_team_ids = {row["team_id"] for row in closure.teams}
    actual_team_ids = set(session.scalars(select(Team.team_id)).all())
    if actual_team_ids != expected_team_ids:
        raise MirrorDriftError("idempotent fixture team ids drifted")
    expected_member_rows = {
        (
            row["team_id"],
            slot,
            row[f"slot{slot}"],
            row["support_slot"].strip() == f"slot{slot}",
        )
        for row in closure.teams
        for slot in range(1, 6)
    }
    actual_member_rows = {
        tuple(stored)
        for stored in session.execute(
            select(
                TeamMember.team_id,
                TeamMember.slot,
                TeamMember.unit_key,
                TeamMember.is_borrowed,
            )
        ).all()
    }
    if actual_member_rows != expected_member_rows:
        raise MirrorDriftError("idempotent fixture team members drifted")

    for row in closure.teams:
        team = session.get(Team, row["team_id"])
        expected_members = [row[f"slot{slot}"] for slot in range(1, 6)]
        actual_members = session.execute(
            select(TeamMember.slot, TeamMember.unit_key, TeamMember.is_borrowed)
            .where(TeamMember.team_id == row["team_id"])
            .order_by(TeamMember.slot)
        ).all()
        expected_support = row["support_slot"].strip()
        if (
            team is None
            or team.source_payload != row
            or team.requirements_raw != row["requirements"]
            or team.signature != ";".join(sorted(expected_members))
            or actual_members
            != [
                (slot, unit_key, expected_support == f"slot{slot}")
                for slot, unit_key in enumerate(expected_members, start=1)
            ]
        ):
            raise MirrorDriftError(f"idempotent fixture team {row['team_id']} drifted")

    timeline_ids_by_axis = {
        row["source_axis_id"]: row for row in closure.timelines
    }
    actual_axis_ids = set(
        session.scalars(select(OperationTimeline.source_axis_id)).all()
    )
    if actual_axis_ids != set(timeline_ids_by_axis):
        raise MirrorDriftError("idempotent fixture operation timeline axes drifted")
    for axis_id, source_row in timeline_ids_by_axis.items():
        stored = session.get(OperationTimeline, axis_id)
        expected = _timeline_values(source_row, import_run_id=stored.import_run_id if stored else "")
        if stored is None or any(
            getattr(stored, name) != value for name, value in expected.items()
        ):
            raise MirrorDriftError(f"idempotent fixture timeline {axis_id} drifted")

    structured_team_by_id = {
        row["timeline_id"]: row["team_id"]
        for row in closure.timelines
        if row["status"] == "STRUCTURED"
    }
    expected_step_ids = {row["timeline_step_id"] for row in closure.timeline_steps}
    actual_step_ids = set(session.scalars(select(TimelineStep.timeline_step_id)).all())
    if actual_step_ids != expected_step_ids:
        raise MirrorDriftError("idempotent fixture timeline steps drifted")
    for source_row in closure.timeline_steps:
        stored = session.get(TimelineStep, source_row["timeline_step_id"])
        expected = _timeline_step_values(
            source_row,
            team_id=structured_team_by_id[source_row["timeline_id"]],
            import_run_id=stored.import_run_id if stored else "",
        )
        if stored is None or any(
            getattr(stored, name) != value for name, value in expected.items()
        ):
            raise MirrorDriftError(
                f"idempotent fixture timeline step {source_row['timeline_step_id']} drifted"
            )

    for model, key_name, rows in (
        (Character, "unit_key", closure.characters),
        (Evidence, "evidence_id", closure.evidence),
        (Claim, "claim_id", closure.claims),
    ):
        expected_ids = {source_row[key_name] for source_row in rows}
        actual_ids = set(session.scalars(select(getattr(model, key_name))).all())
        if actual_ids != expected_ids:
            raise MirrorDriftError(
                f"idempotent fixture {model.__tablename__} ids drifted"
            )
        for source_row in rows:
            stored = session.get(model, source_row[key_name])
            if stored is None or stored.source_payload != source_row:
                raise MirrorDriftError(
                    f"idempotent fixture {model.__tablename__} {source_row[key_name]} drifted"
                )

    expected_stage_evidence = {
        (guide_id, evidence_id)
        for guide_id, evidence_ids in closure.stage_evidence_ids_by_guide.items()
        for evidence_id in evidence_ids
    }
    actual_stage_evidence = {
        tuple(stored)
        for stored in session.execute(
            select(StageEvidence.guide_id, StageEvidence.evidence_id)
        ).all()
    }
    expected_stage_claims = {
        (guide_id, claim_id)
        for guide_id, claim_ids in closure.stage_claim_ids_by_guide.items()
        for claim_id in claim_ids
    }
    actual_stage_claims = {
        tuple(stored)
        for stored in session.execute(
            select(StageClaim.guide_id, StageClaim.claim_id)
        ).all()
    }
    if actual_stage_evidence != expected_stage_evidence:
        raise MirrorDriftError("idempotent fixture stage evidence links drifted")
    if actual_stage_claims != expected_stage_claims:
        raise MirrorDriftError("idempotent fixture stage claim links drifted")

    expected_team_evidence = {
        (team_id, evidence_id)
        for team_id, evidence_ids in closure.team_evidence_ids.items()
        for evidence_id in evidence_ids
    }
    actual_team_evidence = {
        tuple(stored)
        for stored in session.execute(
            select(TeamEvidence.team_id, TeamEvidence.evidence_id)
        ).all()
    }
    if actual_team_evidence != expected_team_evidence:
        raise MirrorDriftError("idempotent fixture team evidence links drifted")

    selected_evidence_ids = {row["evidence_id"] for row in closure.evidence}
    expected_claim_evidence = {
        (row["claim_id"], evidence_id)
        for row in closure.claims
        for evidence_id in _split_ids(row["evidence_ids"])
        if evidence_id in selected_evidence_ids
    }
    actual_claim_evidence = {
        tuple(stored)
        for stored in session.execute(
            select(ClaimEvidence.claim_id, ClaimEvidence.evidence_id)
        ).all()
    }
    if actual_claim_evidence != expected_claim_evidence:
        raise MirrorDriftError("idempotent fixture claim evidence links drifted")
    for row in closure.claims:
        expected = set(_split_ids(row["evidence_ids"])) & selected_evidence_ids
        actual = set(
            session.scalars(
                select(ClaimEvidence.evidence_id).where(ClaimEvidence.claim_id == row["claim_id"])
            ).all()
        )
        if actual != expected:
            raise MirrorDriftError(f"idempotent fixture {row['claim_id']} evidence links drifted")


def _acquire_import_lock(session: Session) -> None:
    """Serialize revision activation on PostgreSQL; SQLite tests are single-writer."""

    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": IMPORT_LOCK_KEY},
        )


def _materialization_state(session: Session) -> MaterializationState:
    state = session.get(MaterializationState, 1)
    if state is None:
        state = MaterializationState(
            id=1,
            active_revision_id=None,
            active_import_run_id=None,
            epoch=0,
            materialization_sha256=None,
            serving_counts={},
        )
        session.add(state)
        session.flush()
    return state


def _clear_serving_mirror(session: Session) -> None:
    """Remove only typed serving rows, in FK-safe order, inside the activation transaction."""

    for model in (
        TimelineStep,
        OperationTimeline,
        TeamMember,
        TeamEvidence,
        StageEvidence,
        StageClaim,
        ClaimEvidence,
        Team,
        Stage,
        Evidence,
        Claim,
        Character,
    ):
        session.execute(delete(model))
    session.flush()


def _serving_counts(materialization: dict[str, Any]) -> dict[str, int]:
    tables = materialization.get("tables")
    if not isinstance(tables, dict):
        raise MirrorDriftError("typed materialization has no table manifest")
    counts: dict[str, int] = {}
    for table_name, table_manifest in tables.items():
        if not isinstance(table_manifest, dict) or not isinstance(
            table_manifest.get("primary_keys"), list
        ):
            raise MirrorDriftError(
                f"typed materialization table is malformed: {table_name}"
            )
        counts[table_name] = len(table_manifest["primary_keys"])
    return counts


def _import_result(
    *,
    run: ImportRun,
    snapshot: ResearchCoreSnapshot,
    created: bool,
    activated: bool,
) -> ImportResult:
    return ImportResult(
        import_run_id=run.id,
        fixture_sha256=run.fixture_sha256,
        created=created,
        activated=activated,
        revision_id=snapshot.revision_id,
        raw_tree_sha256=snapshot.raw_tree_sha256,
        semantic_tree_sha256=snapshot.semantic_tree_sha256,
        file_count=len(snapshot.files),
        csv_file_count=len(snapshot.csv_files),
        csv_row_count=snapshot.csv_row_count,
        row_counts=dict(run.row_counts),
        warnings=tuple(run.manifest.get("warnings", [])),
    )


def _initial_import_sequence(session: Session, revision_id: str) -> int:
    sequence_no = session.scalar(
        select(func.min(RevisionActivation.sequence_no)).where(
            RevisionActivation.to_revision_id == revision_id,
            RevisionActivation.kind == "IMPORT",
        )
    )
    if sequence_no is None:
        raise MirrorDriftError(
            f"revision activation chronology is incomplete: {revision_id}"
        )
    return int(sequence_no)


def _activation_kind(
    session: Session,
    *,
    created: bool,
    previous_revision_id: str | None,
    target_revision_id: str,
) -> str:
    if created:
        return "IMPORT"
    if previous_revision_id is None or previous_revision_id == target_revision_id:
        raise MirrorDriftError("existing revision activation has no distinct active predecessor")
    previous_sequence = _initial_import_sequence(session, previous_revision_id)
    target_sequence = _initial_import_sequence(session, target_revision_id)
    if target_sequence < previous_sequence:
        return "ROLLBACK"
    if target_sequence > previous_sequence:
        return "REACTIVATE"
    raise MirrorDriftError("distinct revisions share an initial-import chronology position")


def _projection_from_manifest(manifest: dict[str, Any]) -> str:
    """Recover the immutable typed projection selected by an existing run.

    B1 manifests predate the explicit projection field.  Their historical
    ``target_guide_id`` marker is therefore the only supported compatibility
    path; every other unknown or missing projection fails closed.
    """

    projection = manifest.get("projection")
    if projection in {FULL_PVE_PROJECTION, LEGACY_FIRE_PROJECTION}:
        return str(projection)
    if projection is None and manifest.get("target_guide_id") == TARGET_GUIDE_ID:
        return LEGACY_FIRE_PROJECTION
    raise MirrorDriftError("import run has an unsupported typed projection")


def _closure_for_projection(
    full_closure: FixtureClosure,
    projection: str,
) -> FixtureClosure:
    if projection == FULL_PVE_PROJECTION:
        return full_closure
    if projection == LEGACY_FIRE_PROJECTION:
        return _legacy_fire_projection(full_closure)
    raise MirrorDriftError(f"unsupported typed projection: {projection}")


def import_pve_projection(
    session: Session,
    research_core: Path,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    application_version: str = APPLICATION_VERSION,
    now: datetime | None = None,
) -> ImportResult:
    """Atomically activate a full-core revision and its complete typed PVE closure.

    All file/row and selected-domain validation happens before any database write.
    The active pointer is switched only after artifact parity, typed parity and the
    immutable ImportRun manifest have all been verified in the same transaction.
    """

    # Keep the domain validator first so malformed selected facts retain precise
    # errors; a valid candidate must then also match the independently pinned full tree.
    full_closure = load_pve_closure(research_core)
    snapshot = load_research_core_snapshot(
        research_core,
        manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    changed_source_files = [
        relative
        for relative in SOURCE_FILES
        if full_closure.file_hashes.get(relative) != snapshot.file(relative).sha256
    ]
    if changed_source_files:
        raise FixtureValidationError(
            "source files changed during import snapshot capture: "
            f"{changed_source_files}"
        )
    imported_at = now or datetime.now(timezone.utc)

    with session.begin():
        _acquire_import_lock(session)
        state = _materialization_state(session)
        previous = session.scalar(
            select(ImportRun).where(ImportRun.fixture_sha256 == snapshot.raw_tree_sha256)
        )
        projection = (
            _projection_from_manifest(previous.manifest)
            if previous is not None
            else (
                LEGACY_FIRE_PROJECTION
                if snapshot.revision_id in LEGACY_FIRE_REVISION_IDS
                else FULL_PVE_PROJECTION
            )
        )
        closure = _closure_for_projection(full_closure, projection)
        row_counts = _counts(closure)
        if previous is not None:
            if previous.status != "SUCCEEDED":
                raise MirrorDriftError("revision fingerprint exists without a successful import")
            revision = session.get(CoreRevision, snapshot.revision_id)
            if revision is None or revision.import_run_id != previous.id:
                raise MirrorDriftError("revision/import provenance is incomplete")
            assert_materialized_snapshot(session, snapshot)
            if (
                state.active_revision_id == snapshot.revision_id
                and state.active_import_run_id == previous.id
            ):
                _assert_materialized(session, closure)
                actual_materialization = build_materialization_manifest(session)
                drift_reason = materialization_drift_reason(
                    previous.manifest.get("materialization"),
                    actual_materialization,
                )
                if drift_reason is not None:
                    raise MirrorDriftError(
                        f"idempotent revision complete closure drifted: {drift_reason}"
                    )
                expected_sha256 = actual_materialization.get("sha256")
                expected_counts = _serving_counts(actual_materialization)
                if (
                    not isinstance(expected_sha256, str)
                    or revision.materialization_sha256 != expected_sha256
                    or state.materialization_sha256 != expected_sha256
                    or state.serving_counts != expected_counts
                ):
                    raise MirrorDriftError("idempotent active materialization digest drifted")
                return _import_result(
                    run=previous,
                    snapshot=snapshot,
                    created=False,
                    activated=False,
                )
            run = previous
            run_id = run.id
            created = False
        else:
            run_id = str(uuid4())
            created = True

        warnings: tuple[str, ...] = ()
        if created:
            run = ImportRun(
                id=run_id,
                fixture_sha256=snapshot.raw_tree_sha256,
                canonical_source=CANONICAL_SOURCE,
                research_core_version=str(closure.stats.get("project_version", "UNKNOWN")),
                application_version=application_version,
                imported_at=imported_at,
                status="RUNNING",
                manifest={
                    "projection": projection,
                    "guide_ids": [guide["guide_id"] for guide in closure.guides],
                    **(
                        {"target_guide_id": TARGET_GUIDE_ID}
                        if projection == LEGACY_FIRE_PROJECTION
                        else {}
                    ),
                    "selected_fixture_sha256": closure.fingerprint,
                    "selected_input_file_sha256": closure.file_hashes,
                    "core_revision": snapshot.report().as_dict(),
                    "stats": closure.stats,
                    "warnings": list(warnings),
                },
                row_counts=row_counts,
            )
            session.add(run)
            session.flush()
            materialize_snapshot(session, snapshot, import_run_id=run_id)

        # A revision switch is a full replacement, never a partial upsert. Any
        # later error rolls these deletes and the previous active pointer back.
        _clear_serving_mirror(session)

        for row in closure.claims:
            _upsert(
                session,
                Claim,
                row["claim_id"],
                {
                    "claim_id": row["claim_id"],
                    "module": row["module"],
                    "server": row["server"],
                    "claim_text": row["claim_text"],
                    "claim_type": row["claim_type"],
                    "claim_confidence": row["claim_confidence"],
                    "independence_check": row["independence_check"],
                    "version_match": row["version_match"],
                    "status": row["status"],
                    "verified_date": _parse_date(
                        row["verified_date"], field=f"{row['claim_id']}.verified_date", required=True
                    ),
                    "next_review_due": _parse_date(
                        row["next_review_due"], field=f"{row['claim_id']}.next_review_due"
                    ),
                    "affected_files": row["affected_files"],
                    "notes": row["notes"],
                    "declared_evidence_ids": list(_split_ids(row["evidence_ids"])),
                    "source_payload": row,
                    "import_run_id": run_id,
                },
            )
        session.flush()

        selected_claim_ids = {row["claim_id"] for row in closure.claims}
        for row in closure.evidence:
            declared_claim_id = row["claim_id"].strip() or None
            linked_claim_id = (
                declared_claim_id if declared_claim_id in selected_claim_ids else None
            )
            _upsert(
                session,
                Evidence,
                row["evidence_id"],
                {
                    "evidence_id": row["evidence_id"],
                    "declared_claim_id": declared_claim_id,
                    "linked_claim_id": linked_claim_id,
                    "module": row["module"],
                    "server": row["server"],
                    "source_tier": row["source_tier"],
                    "evidence_confidence": row["evidence_confidence"],
                    "source_title": row["source_title"],
                    "source_url": row["source_url"],
                    "source_locator": row["source_locator"],
                    "published_date": _parse_published_date(
                        row["published_date"],
                        precision=row["published_date_precision"],
                        field=f"{row['evidence_id']}.published_date",
                    ),
                    "published_date_precision": row["published_date_precision"],
                    "verified_date": _parse_date(
                        row["verified_date"],
                        field=f"{row['evidence_id']}.verified_date",
                        required=True,
                    ),
                    "claim_summary": row["claim_summary"],
                    "limitations": row["limitations"],
                    "affected_files": row["affected_files"],
                    "status": row["status"],
                    "source_payload": row,
                    "import_run_id": run_id,
                },
            )
        session.flush()

        for row in closure.characters:
            _upsert(
                session,
                Character,
                row["unit_key"],
                {
                    "unit_key": row["unit_key"],
                    "tw_name": row["tw_name"],
                    "jp_name": row["jp_name"],
                    "version": row["version"],
                    "tw_release_date": _parse_date(
                        row["tw_release_date"], field=f"{row['unit_key']}.tw_release_date"
                    ),
                    "availability_status": row["availability_status"],
                    "ue1_status": row["ue1_status"],
                    "ue2_status": row["ue2_status"],
                    "six_star_status": row["six_star_status"],
                    "connect_rank_status": row["connect_rank_status"],
                    "element": row["element"],
                    "source_evidence_ids": list(_split_ids(row["source_evidence_ids"])),
                    "last_verified": _parse_date(
                        row["last_verified"], field=f"{row['unit_key']}.last_verified", required=True
                    ),
                    "last_review_due": _parse_date(
                        row["last_review_due"], field=f"{row['unit_key']}.last_review_due"
                    ),
                    "notes": row["notes"],
                    "source_payload": row,
                    "import_run_id": run_id,
                },
            )
        session.flush()

        for guide in closure.guides:
            _upsert(
                session,
                Stage,
                guide["guide_id"],
                {
                    "guide_id": guide["guide_id"],
                    "server": guide["server"],
                    "mode": guide["mode"],
                    "area": guide["area"],
                    "stage": guide["stage"],
                    "status": guide["status"],
                    "verified_date": _parse_date(
                        guide["verified_date"],
                        field=f"{guide['guide_id']}.verified_date",
                        required=True,
                    ),
                    "applicable_version": guide["applicable_version"],
                    "team_count": int(guide["team_count"]),
                    "source_tier": guide["source_tier"],
                    "claim_confidence": guide["claim_confidence"],
                    "reproducibility": guide["reproducibility"],
                    "last_review_due": _parse_date(
                        guide["last_review_due"],
                        field=f"{guide['guide_id']}.last_review_due",
                    ),
                    "notes": guide["notes"],
                    "source_payload": guide,
                    "import_run_id": run_id,
                },
            )
        session.flush()

        for row in closure.teams:
            members = tuple(row[f"slot{slot}"] for slot in range(1, 6))
            _upsert(
                session,
                Team,
                row["team_id"],
                {
                    "team_id": row["team_id"],
                    "guide_id": row["guide_id"],
                    "server": row["server"],
                    "stage_label": row["stage"],
                    "support_slot": row["support_slot"].strip() or None,
                    "operation_mode": row["operation_mode"],
                    "requirements": _validate_requirements(row),
                    "requirements_raw": row["requirements"],
                    "clear_status": row["clear_status"],
                    "stability": row["stability"],
                    "source_ids": list(_split_ids(row["source_ids"])),
                    "tw_availability_check": row["tw_availability_check"],
                    "verified_date": _parse_date(
                        row["verified_date"], field=f"{row['team_id']}.verified_date", required=True
                    ),
                    "last_review_due": _parse_date(
                        row["last_review_due"], field=f"{row['team_id']}.last_review_due"
                    ),
                    "notes": row["notes"],
                    "signature": ";".join(sorted(members)),
                    "source_payload": row,
                    "import_run_id": run_id,
                },
            )
        session.flush()

        team_ids = [row["team_id"] for row in closure.teams]
        guide_ids = [row["guide_id"] for row in closure.guides]
        session.execute(delete(TeamMember).where(TeamMember.team_id.in_(team_ids)))
        session.execute(delete(TeamEvidence).where(TeamEvidence.team_id.in_(team_ids)))
        session.execute(delete(StageEvidence).where(StageEvidence.guide_id.in_(guide_ids)))
        session.execute(delete(StageClaim).where(StageClaim.guide_id.in_(guide_ids)))
        if selected_claim_ids:
            session.execute(delete(ClaimEvidence).where(ClaimEvidence.claim_id.in_(selected_claim_ids)))

        for row in closure.teams:
            support_slot = row["support_slot"].strip()
            for slot in range(1, 6):
                session.add(
                    TeamMember(
                        team_id=row["team_id"],
                        slot=slot,
                        unit_key=row[f"slot{slot}"],
                        is_borrowed=support_slot == f"slot{slot}",
                    )
                )
            for evidence_id in closure.team_evidence_ids[row["team_id"]]:
                session.add(TeamEvidence(team_id=row["team_id"], evidence_id=evidence_id))
        for guide_id, evidence_ids in closure.stage_evidence_ids_by_guide.items():
            for evidence_id in evidence_ids:
                session.add(StageEvidence(guide_id=guide_id, evidence_id=evidence_id))
        for guide_id, claim_ids in closure.stage_claim_ids_by_guide.items():
            for claim_id in claim_ids:
                session.add(StageClaim(guide_id=guide_id, claim_id=claim_id))
        selected_evidence_ids = {row["evidence_id"] for row in closure.evidence}
        for row in closure.claims:
            for evidence_id in _split_ids(row["evidence_ids"]):
                if evidence_id in selected_evidence_ids:
                    session.add(ClaimEvidence(claim_id=row["claim_id"], evidence_id=evidence_id))

        session.flush()

        for row in closure.timelines:
            _upsert(
                session,
                OperationTimeline,
                row["source_axis_id"],
                _timeline_values(row, import_run_id=run_id),
            )
        session.flush()

        structured_team_by_id = {
            row["timeline_id"]: row["team_id"]
            for row in closure.timelines
            if row["status"] == "STRUCTURED"
        }
        for row in closure.timeline_steps:
            _upsert(
                session,
                TimelineStep,
                row["timeline_step_id"],
                _timeline_step_values(
                    row,
                    team_id=structured_team_by_id[row["timeline_id"]],
                    import_run_id=run_id,
                ),
            )
        session.flush()

        _assert_materialized(session, closure)
        materialization = build_materialization_manifest(session)
        materialization_sha256 = materialization.get("sha256")
        if not isinstance(materialization_sha256, str):
            raise MirrorDriftError("typed materialization has no SHA-256")
        serving_counts = _serving_counts(materialization)

        if created:
            run.manifest = {
                **run.manifest,
                "materialization": materialization,
                "serving_row_counts": serving_counts,
            }
            run.status = "SUCCEEDED"
            finalize_materialized_snapshot(
                session,
                snapshot,
                import_run_id=run_id,
                typed_materialization_sha256=materialization_sha256,
            )
        else:
            drift_reason = materialization_drift_reason(
                run.manifest.get("materialization"),
                materialization,
            )
            if drift_reason is not None:
                raise MirrorDriftError(
                    f"reactivated revision typed closure drifted: {drift_reason}"
                )
            revision = session.get(CoreRevision, snapshot.revision_id)
            if (
                revision is None
                or revision.status != "SUCCEEDED"
                or revision.materialization_sha256 != materialization_sha256
            ):
                raise MirrorDriftError("reactivated revision metadata drifted")
        session.flush()

        # Epoch triggers have now observed every artifact/typed/run write. Refresh
        # before reserving the activation epoch, then append audit and switch last.
        session.refresh(state)
        next_epoch = state.epoch + 1
        previous_revision_id = state.active_revision_id
        sequence_no = (
            session.scalar(select(func.max(RevisionActivation.sequence_no))) or 0
        ) + 1
        activation_kind = _activation_kind(
            session,
            created=created,
            previous_revision_id=previous_revision_id,
            target_revision_id=snapshot.revision_id,
        )
        session.add(
            RevisionActivation(
                activation_id=str(uuid4()),
                sequence_no=sequence_no,
                from_revision_id=previous_revision_id,
                to_revision_id=snapshot.revision_id,
                kind=activation_kind,
                reason={
                    "IMPORT": "activate manifest-pinned full-core import",
                    "ROLLBACK": "rollback to earlier verified immutable revision",
                    "REACTIVATE": "reactivate later verified immutable revision",
                }[activation_kind],
                actor="pcr_pipeline.import_pve",
                activated_at=imported_at,
                epoch=next_epoch,
            )
        )
        session.flush()

        state.active_revision_id = snapshot.revision_id
        state.active_import_run_id = run_id
        state.epoch = next_epoch
        state.materialization_sha256 = materialization_sha256
        state.serving_counts = serving_counts
        state.updated_at = imported_at
        session.flush()
        result = _import_result(
            run=run,
            snapshot=snapshot,
            created=created,
            activated=True,
        )

    return result


def import_fire_8_10(
    session: Session,
    research_core: Path,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    application_version: str = APPLICATION_VERSION,
    now: datetime | None = None,
) -> ImportResult:
    """Compatibility wrapper; imports the complete PVE projection."""

    return import_pve_projection(
        session,
        research_core,
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
        application_version=application_version,
        now=now,
    )
