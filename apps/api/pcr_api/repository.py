from __future__ import annotations

from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from threading import Lock
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pcr_pipeline.research_core_snapshot import (
    SnapshotDriftError,
    canonical_json_sha256,
    materialized_report,
)
from pcr_database.materialization import (
    LEGACY_MATERIALIZATION_MANIFEST_VERSION,
    LEGACY_SERVING_MODELS,
    MATERIALIZATION_MANIFEST_VERSION,
    SERVING_MODELS,
    build_materialization_manifest,
    materialization_drift_reason,
)
from pcr_database.models import (
    ArenaCounter,
    ArenaCounterClaim,
    ArenaCounterEvidence,
    ArenaCounterMember,
    ArenaDefense,
    ArenaDefenseMember,
    Character,
    Claim,
    ClaimEvidence,
    CoreRevision,
    Evidence,
    ImportRun,
    MaterializationState,
    OperationTimeline,
    Stage,
    StageClaim,
    StageEvidence,
    Team,
    TeamEvidence,
    TeamMember,
    TimelineStep,
)

from .schemas import ResponseMeta, SourceMeta


_BASELINE_COUNT_TABLES = {
    "stages": Stage,
    "teams": Team,
    "team_members": TeamMember,
    "characters": Character,
    "evidence": Evidence,
    "claims": Claim,
    "operation_timelines": OperationTimeline,
    "timeline_steps": TimelineStep,
    "arena_defenses": ArenaDefense,
    "arena_defense_members": ArenaDefenseMember,
    "arena_counters": ArenaCounter,
    "arena_counter_members": ArenaCounterMember,
    "arena_counter_evidence": ArenaCounterEvidence,
    "arena_counter_claims": ArenaCounterClaim,
}
_SERVING_TABLE_NAMES = frozenset(model.__tablename__ for model in SERVING_MODELS)
_LEGACY_SERVING_TABLE_NAMES = frozenset(
    model.__tablename__ for model in LEGACY_SERVING_MODELS
)
_SERVING_TABLE_NAMES_BY_MANIFEST_VERSION = {
    LEGACY_MATERIALIZATION_MANIFEST_VERSION: _LEGACY_SERVING_TABLE_NAMES,
    MATERIALIZATION_MANIFEST_VERSION: _SERVING_TABLE_NAMES,
}
_READINESS_CACHE_MAX_ENTRIES = 32
_readiness_cache: OrderedDict[tuple[int, str, str, int, str], None] = OrderedDict()
_readiness_cache_lock = Lock()
_ARENA_VERIFIED_SOURCE_TIERS = frozenset(
    {
        "OFFICIAL",
        "MAJOR_GUIDE",
        "STRUCTURED_DB",
        "COMMUNITY_WIKI",
        "MULTI_PLAYER_REPORT",
    }
)
_ARENA_VERIFIED_EVIDENCE_TIERS = frozenset(
    {
        "OFFICIAL",
        "MAJOR_GUIDE",
        "STRUCTURED_DB",
        "COMMUNITY_WIKI",
        "MULTI_PLAYER_REPORT",
        "SINGLE_PLAYER_REPORT",
    }
)
_CONFIDENCE_RANK = {value: rank for rank, value in enumerate("ABCDE")}


@dataclass(frozen=True)
class ResponseMetaRecord:
    """Typed facts contributed by one record to envelope-level metadata."""

    server: str | None = None
    environment_version: str | None = None
    verified_at: date | None = None
    stale_status: str | None = None
    confidence: str | None = None
    evidence_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()


def _aggregate_dimension(values: list[str | None]) -> str:
    """Return a homogeneous value, MIXED known values, or fail-closed UNKNOWN."""

    if not values or any(not value or value == "UNKNOWN" for value in values):
        return "UNKNOWN"
    distinct = set(values)
    return next(iter(distinct)) if len(distinct) == 1 else "MIXED"


def conservative_response_metadata(
    records: list[ResponseMetaRecord],
) -> dict[str, Any]:
    """Aggregate only facts proven by the complete returned record closure.

    A missing fact makes that aggregate UNKNOWN (or null for ``verified_at``).
    This intentionally never substitutes import time for content verification.
    """

    servers = [record.server for record in records]
    environments = [record.environment_version for record in records]
    verified_dates = [record.verified_at for record in records]
    stale_statuses = [record.stale_status for record in records]
    confidences = [record.confidence for record in records]

    verified_at = (
        min(verified_dates)
        if verified_dates and all(value is not None for value in verified_dates)
        else None
    )
    if not stale_statuses or any(
        value not in {"CURRENT", "STALE"} for value in stale_statuses
    ):
        stale_status = "UNKNOWN"
    else:
        stale_status = "STALE" if "STALE" in stale_statuses else "CURRENT"

    if not confidences or any(value not in _CONFIDENCE_RANK for value in confidences):
        confidence = "UNKNOWN"
    else:
        confidence = max(confidences, key=lambda value: _CONFIDENCE_RANK[value])

    return {
        "server": _aggregate_dimension(servers),
        "environment_version": _aggregate_dimension(environments),
        "verified_at": verified_at,
        "stale_status": stale_status,
        "confidence": confidence,
        "evidence_ids": sorted(
            {
                identifier
                for record in records
                for identifier in record.evidence_ids
                if identifier
            }
        ),
        "claim_ids": sorted(
            {
                identifier
                for record in records
                for identifier in record.claim_ids
                if identifier
            }
        ),
    }


def latest_import(session: Session) -> ImportRun | None:
    """Resolve the serving import exclusively through the active singleton pointer."""

    state = session.get(MaterializationState, 1)
    if state is None or state.active_import_run_id is None:
        return None
    return session.get(ImportRun, state.active_import_run_id)


def active_revision(session: Session, run: ImportRun) -> CoreRevision | None:
    state = session.get(MaterializationState, 1)
    if (
        state is None
        or state.active_import_run_id != run.id
        or state.active_revision_id is None
    ):
        return None
    return session.get(CoreRevision, state.active_revision_id)


def _manifest_serving_counts(run: ImportRun) -> dict[str, int] | None:
    materialization = run.manifest.get("materialization")
    if not isinstance(materialization, dict):
        return None
    expected_table_names = _SERVING_TABLE_NAMES_BY_MANIFEST_VERSION.get(
        materialization.get("schema_version")
    )
    if expected_table_names is None:
        return None

    declared_counts = run.manifest.get("serving_row_counts")
    if (
        not isinstance(declared_counts, dict)
        or set(declared_counts) != expected_table_names
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in declared_counts.values()
        )
    ):
        return None

    tables = materialization.get("tables")
    if not isinstance(tables, dict) or set(tables) != expected_table_names:
        return None

    counts: dict[str, int] = {}
    for table_name, table_manifest in tables.items():
        if not isinstance(table_manifest, dict):
            return None
        primary_keys = table_manifest.get("primary_keys")
        row_sha256 = table_manifest.get("row_sha256")
        if (
            not isinstance(primary_keys, list)
            or not isinstance(row_sha256, dict)
            or len(primary_keys) != len(row_sha256)
        ):
            return None
        counts[table_name] = len(primary_keys)
    if counts != declared_counts:
        return None
    return dict(declared_counts)


def _is_postgresql(session: Session) -> bool:
    bind = session.get_bind()
    return bind.dialect.name == "postgresql"


def _readiness_cache_key(
    session: Session,
    state: MaterializationState,
    run: ImportRun,
) -> tuple[int, str, str, int, str]:
    return (
        id(session.get_bind()),
        str(state.active_revision_id),
        str(state.active_import_run_id),
        state.epoch,
        canonical_json_sha256(run.manifest),
    )


def _is_cached_ready(key: tuple[int, str, str, int, str]) -> bool:
    with _readiness_cache_lock:
        if key not in _readiness_cache:
            return False
        _readiness_cache.move_to_end(key)
        return True


def _cache_ready(key: tuple[int, str, str, int, str]) -> None:
    with _readiness_cache_lock:
        _readiness_cache[key] = None
        _readiness_cache.move_to_end(key)
        while len(_readiness_cache) > _READINESS_CACHE_MAX_ENTRIES:
            _readiness_cache.popitem(last=False)


def mirror_readiness(session: Session, run: ImportRun) -> tuple[bool, str]:
    """Verify the active full-core revision and its complete serving closure."""

    state = session.get(MaterializationState, 1)
    if state is None:
        return False, "active_pointer_missing"
    if state.active_import_run_id != run.id or state.active_revision_id is None:
        return False, "active_pointer_drift"
    revision = session.get(CoreRevision, state.active_revision_id)
    if revision is None:
        return False, "active_revision_missing"
    if (
        run.status != "SUCCEEDED"
        or revision.status != "SUCCEEDED"
        or revision.import_run_id != run.id
        or revision.project_version != run.research_core_version
        or run.fixture_sha256 != revision.raw_tree_sha256
        or revision.revision_id != revision.raw_tree_sha256
    ):
        return False, "active_revision_drift"

    expected_counts = _manifest_serving_counts(run)
    if expected_counts is None:
        return False, "serving_count_manifest_drift"
    if (
        not isinstance(state.serving_counts, dict)
        or set(state.serving_counts) != set(expected_counts)
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in state.serving_counts.values()
        )
        or state.serving_counts != expected_counts
    ):
        return False, "serving_count_state_drift"

    expected_materialization = run.manifest.get("materialization")
    expected_materialization_sha256 = (
        expected_materialization.get("sha256")
        if isinstance(expected_materialization, dict)
        else None
    )
    if (
        not isinstance(expected_materialization_sha256, str)
        or len(expected_materialization_sha256) != 64
        or revision.materialization_sha256 != expected_materialization_sha256
        or state.materialization_sha256 != expected_materialization_sha256
    ):
        return False, "materialization_digest_drift"

    cache_key = _readiness_cache_key(session, state, run)
    if _is_postgresql(session) and _is_cached_ready(cache_key):
        return True, "imported"

    try:
        core_report = materialized_report(session, revision.revision_id).as_dict()
    except SnapshotDriftError as error:
        return False, error.reason
    if run.manifest.get("core_revision") != core_report:
        return False, "core_revision_manifest_drift"

    drift_reason = materialization_drift_reason(
        expected_materialization,
        build_materialization_manifest(
            session,
            expected_manifest=expected_materialization,
        ),
    )
    if drift_reason is not None:
        return False, drift_reason

    if _is_postgresql(session):
        _cache_ready(cache_key)

    return True, "imported"


def has_arena_materialization(run: ImportRun) -> bool:
    """Return whether the immutable serving manifest owns the Arena closure."""

    materialization = run.manifest.get("materialization")
    if not isinstance(materialization, dict):
        return False
    tables = materialization.get("tables")
    return (
        materialization.get("schema_version") == MATERIALIZATION_MANIFEST_VERSION
        and isinstance(tables, dict)
        and {
            "arena_defenses",
            "arena_defense_members",
            "arena_counters",
            "arena_counter_members",
            "arena_counter_evidence",
            "arena_counter_claims",
        }
        <= set(tables)
    )


def _declared_team_evidence(team: Team) -> set[str]:
    raw = team.source_payload.get("evidence_ids")
    if not isinstance(raw, str):
        return set()
    return {item.strip() for item in raw.split(";") if item.strip()}


def effective_team_signatures(session: Session, guide_id: str) -> set[str]:
    """Return only signatures that satisfy the application PVE Gate predicate.

    This mirrors the corrected research-core gate at the serving boundary: a
    row is not an effective clear merely because it exists in ``teams``.
    """

    signatures: set[str] = set()
    teams = session.scalars(select(Team).where(Team.guide_id == guide_id)).all()
    today = datetime.now(timezone.utc).date()
    for team in teams:
        if (
            team.clear_status != "VERIFIED"
            or team.tw_availability_check != "PASS"
            or team.verified_date is None
            or team.verified_date > today
        ):
            continue

        members = session.execute(
            select(
                TeamMember.slot,
                TeamMember.unit_key,
                Character.availability_status,
            )
            .join(Character, Character.unit_key == TeamMember.unit_key)
            .where(TeamMember.team_id == team.team_id)
            .order_by(TeamMember.slot)
        ).all()
        member_keys = [unit_key for _slot, unit_key, _availability in members]
        if (
            len(members) != 5
            or {slot for slot, _unit_key, _availability in members} != {1, 2, 3, 4, 5}
            or len(set(member_keys)) != 5
            or any(availability != "AVAILABLE" for _slot, _unit_key, availability in members)
            or team.signature != ";".join(sorted(member_keys))
        ):
            continue

        declared_evidence = _declared_team_evidence(team)
        evidence_rows = session.execute(
            select(
                TeamEvidence.evidence_id,
                Evidence.declared_claim_id,
                Evidence.linked_claim_id,
                Evidence.status,
                Claim.status,
            )
            .join(Evidence, Evidence.evidence_id == TeamEvidence.evidence_id)
            .outerjoin(Claim, Claim.claim_id == Evidence.linked_claim_id)
            .where(TeamEvidence.team_id == team.team_id)
        ).all()
        actual_evidence = {row.evidence_id for row in evidence_rows}
        if not declared_evidence or actual_evidence != declared_evidence:
            continue
        if any(
            row.declared_claim_id is None
            or row.linked_claim_id != row.declared_claim_id
            or row.status != "ACTIVE"
            or row[4] != "ACTIVE"
            for row in evidence_rows
        ):
            continue

        signatures.add(team.signature)
    return signatures


def response_meta(
    run: ImportRun,
    revision: CoreRevision,
    *,
    records: list[ResponseMetaRecord] | None = None,
    extra_warnings: list[str] | None = None,
) -> ResponseMeta:
    if revision.materialization_sha256 is None:
        raise RuntimeError("active revision has no materialization digest")
    warnings = list(run.manifest.get("warnings", []))
    warnings.extend(extra_warnings or [])
    aggregate = conservative_response_metadata(records or [])
    return ResponseMeta(
        api_version="v1",
        generated_at=datetime.now(timezone.utc),
        **aggregate,
        data_revision=revision.revision_id,
        source=SourceMeta(
            canonical_source=run.canonical_source,
            fixture_sha256=run.fixture_sha256,
            import_run_id=run.id,
            revision_id=revision.revision_id,
            imported_at=run.imported_at,
            research_core_version=run.research_core_version,
            raw_tree_sha256=revision.raw_tree_sha256,
            semantic_tree_sha256=revision.semantic_tree_sha256,
            materialization_sha256=revision.materialization_sha256,
        ),
        warnings=warnings,
    )


def baseline_data(session: Session, run: ImportRun) -> dict[str, Any]:
    serving_counts = _manifest_serving_counts(run)
    if serving_counts is None:
        raise RuntimeError("active ImportRun has no valid serving count manifest")
    counts = {
        name: serving_counts.get(model.__tablename__, 0)
        for name, model in _BASELINE_COUNT_TABLES.items()
    }
    featured = session.scalar(select(Stage).order_by(Stage.guide_id).limit(1))
    return {
        "research_core_version": run.research_core_version,
        "application_version": run.application_version,
        "canonical_source": run.canonical_source,
        "generated_at": run.imported_at,
        "counts": counts,
        "gates": {
            key: bool(run.manifest.get("stats", {}).get("gate", {}).get(key, False))
            for key in ("gate_a", "gate_b", "gate_c")
        },
        "featured_stage": stage_summary(featured) if featured else None,
    }


def stage_summary(stage: Stage) -> dict[str, Any]:
    return {
        "guide_id": stage.guide_id,
        "server": stage.server,
        "mode": stage.mode,
        "area": stage.area,
        "stage": stage.stage,
        "status": stage.status,
        "team_count": stage.team_count,
        "reproducibility": stage.reproducibility,
        "verified_date": stage.verified_date,
    }


def team_summary(session: Session, team: Team) -> dict[str, Any]:
    members = session.execute(
        select(TeamMember.slot, TeamMember.unit_key, TeamMember.is_borrowed, Character.tw_name)
        .join(Character, Character.unit_key == TeamMember.unit_key)
        .where(TeamMember.team_id == team.team_id)
        .order_by(TeamMember.slot)
    ).all()
    return {
        "team_id": team.team_id,
        "operation_mode": team.operation_mode,
        "clear_status": team.clear_status,
        "stability": team.stability,
        "members": [
            {
                "slot": slot,
                "unit_key": unit_key,
                "tw_name": tw_name,
                "is_borrowed": is_borrowed,
            }
            for slot, unit_key, is_borrowed, tw_name in members
        ],
    }


def stage_detail(session: Session, stage: Stage) -> dict[str, Any]:
    teams = session.scalars(
        select(Team).where(Team.guide_id == stage.guide_id).order_by(Team.team_id)
    ).all()
    evidence_ids = session.scalars(
        select(StageEvidence.evidence_id)
        .where(StageEvidence.guide_id == stage.guide_id)
        .order_by(StageEvidence.evidence_id)
    ).all()
    claim_ids = session.scalars(
        select(StageClaim.claim_id)
        .where(StageClaim.guide_id == stage.guide_id)
        .order_by(StageClaim.claim_id)
    ).all()
    verified_distinct = len(effective_team_signatures(session, stage.guide_id))
    target = 5
    return {
        **stage_summary(stage),
        "applicable_version": stage.applicable_version,
        "source_tier": stage.source_tier,
        "claim_confidence": stage.claim_confidence,
        "last_review_due": stage.last_review_due,
        "notes": stage.notes,
        "coverage": {
            "verified_distinct_teams": verified_distinct,
            "maturity_target": target,
            "remaining": max(0, target - verified_distinct),
            "is_mature": verified_distinct >= target and stage.status == "VERIFIED",
        },
        "teams": [team_summary(session, team) for team in teams],
        "evidence_ids": list(evidence_ids),
        "claim_ids": list(claim_ids),
    }


def _step_data(step: TimelineStep) -> dict[str, Any]:
    return {
        "timeline_step_id": step.timeline_step_id,
        "timeline_id": step.timeline_id,
        "sequence_no": step.sequence_no,
        "source_step_no": step.source_step_no,
        "trigger_type": step.trigger_type,
        "trigger_actor_unit_key": step.trigger_actor_unit_key or "NONE",
        "time_state": step.time_state,
        "clock_from_ms": step.clock_from_ms,
        "clock_to_ms": step.clock_to_ms,
        "actor_unit_key": step.actor_unit_key or "NONE",
        "action_type": step.action_type,
        "target_unit_key": step.target_unit_key or "NONE",
        "auto_state_after": step.auto_state_after,
        "animation_cue": step.animation_cue,
        "hp_threshold": step.hp_threshold,
        "tolerance_ms": step.tolerance_ms,
        "criticality": step.criticality,
        "instruction_zh_tw": step.instruction_zh_tw,
        "failure_if_missed": step.failure_if_missed,
        "source_locator": step.source_locator,
    }


def timeline_data(session: Session, team: Team) -> dict[str, Any]:
    """Serialize source axes independently; never merge or reorder their steps."""

    axes = session.scalars(
        select(OperationTimeline)
        .where(OperationTimeline.team_id == team.team_id)
        .order_by(OperationTimeline.source_axis_id)
    ).all()
    structured_ids = [axis.timeline_id for axis in axes if axis.timeline_id is not None]
    steps_by_timeline: dict[str, list[TimelineStep]] = {
        timeline_id: [] for timeline_id in structured_ids
    }
    if structured_ids:
        steps = session.scalars(
            select(TimelineStep)
            .where(TimelineStep.timeline_id.in_(structured_ids))
            .order_by(TimelineStep.timeline_id, TimelineStep.sequence_no)
        ).all()
        for step in steps:
            steps_by_timeline[step.timeline_id].append(step)

    sources: list[dict[str, Any]] = []
    for axis in axes:
        common = {
            "source_axis_id": axis.source_axis_id,
            "source_id": axis.source_id,
            "source_evidence_id": axis.source_evidence_id,
            "source_locator": axis.source_locator,
            "timeline_variant_name": axis.timeline_variant_name,
            "operation_mode": axis.operation_mode,
            "reproducibility": axis.reproducibility,
            "last_verified_at": axis.last_verified_at,
            "notes": axis.notes,
        }
        if axis.status == "STRUCTURED":
            assert axis.timeline_id is not None
            sources.append(
                {
                    **common,
                    "status": "STRUCTURED",
                    "timeline_id": axis.timeline_id,
                    "clock_mode": axis.clock_mode,
                    "battle_duration_ms": axis.battle_duration_ms,
                    "initial_auto_state": axis.initial_auto_state,
                    "gap_reason": None,
                    "steps": [
                        _step_data(step) for step in steps_by_timeline[axis.timeline_id]
                    ],
                }
            )
        else:
            sources.append(
                {
                    **common,
                    "status": "SOURCE_GAP",
                    "timeline_id": None,
                    "clock_mode": None,
                    "battle_duration_ms": None,
                    "initial_auto_state": None,
                    "gap_reason": axis.gap_reason,
                    "steps": [],
                }
            )

    structured_sources = sum(source["status"] == "STRUCTURED" for source in sources)
    registered_sources = len(sources)
    if registered_sources == 0:
        status = "MISSING"
    elif structured_sources == registered_sources:
        status = "STRUCTURED"
    elif structured_sources == 0:
        status = "SOURCE_GAP"
    else:
        status = "PARTIAL"
    return {
        "status": status,
        "structured_sources": structured_sources,
        "registered_sources": registered_sources,
        "sources": sources,
        # Compatibility projection only. ``timeline_ref`` now stores source
        # axis ids, but the deprecated B0 parser shape remains unchanged.
        "references": [
            {
                "source_id": value.partition("@")[0],
                "locator": value.partition("@")[2] or "UNKNOWN",
                "raw": value,
            }
            for value in str(team.requirements.get("timeline_ref", "")).split(";")
            if value
        ],
        # Deprecated: flattening source-specific steps would destroy evidence
        # provenance and execution order.
        "steps": [],
    }


def timeline_warnings(timeline: dict[str, Any]) -> list[str]:
    status = timeline["status"]
    if status == "SOURCE_GAP":
        return ["STRUCTURED_TIMELINE_SOURCE_GAP"]
    if status == "PARTIAL":
        return ["STRUCTURED_TIMELINE_PARTIAL"]
    if status == "MISSING":
        return ["STRUCTURED_TIMELINE_MISSING"]
    return []


def team_detail(session: Session, team: Team) -> dict[str, Any]:
    data = team_summary(session, team)
    evidence_ids = session.scalars(
        select(TeamEvidence.evidence_id)
        .where(TeamEvidence.team_id == team.team_id)
        .order_by(TeamEvidence.evidence_id)
    ).all()
    data.update(
        {
            "guide_id": team.guide_id,
            "server": team.server,
            "stage": team.stage_label,
            "support_slot": team.support_slot,
            "requirements": team.requirements,
            "timeline": timeline_data(session, team),
            "source_ids": list(team.source_ids),
            "evidence_ids": list(evidence_ids),
            "tw_availability_check": team.tw_availability_check,
            "verified_date": team.verified_date,
            "last_review_due": team.last_review_due,
            "notes": team.notes,
        }
    )
    return data


def _arena_member_rows_by_owner(
    session: Session,
    *,
    owner_column: Any,
    owner_ids: list[str],
) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = {owner_id: [] for owner_id in owner_ids}
    if not owner_ids:
        return grouped
    rows = session.execute(
        select(
            owner_column,
            owner_column.class_.slot,
            owner_column.class_.unit_key,
            Character.availability_status,
            Character.tw_name,
            Character.jp_name,
        )
        .join(Character, Character.unit_key == owner_column.class_.unit_key)
        .where(owner_column.in_(owner_ids))
        .order_by(owner_column, owner_column.class_.slot)
    ).all()
    for owner_id, slot, unit_key, availability, tw_name, jp_name in rows:
        grouped.setdefault(owner_id, []).append(
            (slot, unit_key, availability, tw_name, jp_name)
        )
    return grouped


def _serialize_arena_members(
    *,
    owner_id: str,
    signature: str,
    rows: list[Any],
) -> list[dict[str, Any]]:
    unit_keys = [unit_key for _slot, unit_key, _availability, _tw_name, _jp_name in rows]
    if (
        len(rows) != 5
        or {
            slot
            for slot, _unit_key, _availability, _tw_name, _jp_name in rows
        }
        != {1, 2, 3, 4, 5}
        or len(set(unit_keys)) != 5
        or ";".join(sorted(unit_keys)) != signature
    ):
        raise RuntimeError(f"invalid Arena formation closure: {owner_id}")
    members: list[dict[str, Any]] = []
    for slot, unit_key, availability, tw_name, jp_name in rows:
        display_name, display_name_source = _arena_display_name(
            unit_key=unit_key,
            availability=availability,
            tw_name=tw_name,
            jp_name=jp_name,
        )
        members.append(
            {
                "slot": slot,
                "unit_key": unit_key,
                "display_name": display_name,
                "display_name_source": display_name_source,
            }
        )
    return members


def _arena_relation_ids_by_counter(
    session: Session,
    *,
    value_column: Any,
    counter_ids: list[str],
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    if not counter_ids:
        return grouped
    counter_column = value_column.class_.counter_id
    rows = session.execute(
        select(counter_column, value_column)
        .where(counter_column.in_(counter_ids))
        .order_by(counter_column, value_column)
    ).all()
    for counter_id, value in rows:
        grouped[counter_id].append(value)
    return grouped


def _stored_official_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.upper() in {
        "UNKNOWN",
        "N/A",
        "NA",
        "PENDING",
        "NOT_RELEASED",
        "UNVERIFIED",
    } or normalized in {"【待查證】", "待查證", "未確認", "—", "-"}:
        return None
    return normalized


def _referenced_evidence_ids(value: Any) -> tuple[str, ...]:
    """Normalize a stored JSON ID list, failing closed on malformed values."""

    if not isinstance(value, list):
        return ()
    normalized: list[str] = []
    for identifier in value:
        if not isinstance(identifier, str) or not identifier.strip():
            return ()
        normalized.append(identifier.strip())
    return tuple(normalized)


def _is_active_tw_official_a_evidence(evidence: Evidence | None) -> bool:
    return bool(
        evidence is not None
        and evidence.status == "ACTIVE"
        and evidence.server == "TW"
        and evidence.source_tier == "OFFICIAL"
        and evidence.evidence_confidence == "A"
    )


def _arena_display_name(
    *,
    unit_key: str,
    availability: str,
    tw_name: Any,
    jp_name: Any,
) -> tuple[str, str]:
    """Select only a stored official name; never synthesize a translation."""

    if availability == "AVAILABLE":
        official_tw_name = _stored_official_name(tw_name)
        if official_tw_name is not None:
            return official_tw_name, "TW_OFFICIAL"
    elif availability == "NOT_RELEASED":
        official_jp_name = _stored_official_name(jp_name)
        if official_jp_name is not None:
            return official_jp_name, "JP_OFFICIAL"

    raise RuntimeError(f"Arena member has no stored official display name: {unit_key}")


def pvp_character_options(
    session: Session,
) -> tuple[list[dict[str, str]], list[ResponseMetaRecord]]:
    """Return deterministic, canonical TW-available options for the Arena picker."""

    characters = session.scalars(
        select(Character).where(Character.availability_status == "AVAILABLE")
    ).all()
    evidence_ids_by_unit = {
        character.unit_key: _referenced_evidence_ids(character.source_evidence_ids)
        for character in characters
    }
    referenced_evidence_ids = sorted(
        {
            evidence_id
            for evidence_ids in evidence_ids_by_unit.values()
            for evidence_id in evidence_ids
        }
    )
    evidence_by_id = {
        evidence.evidence_id: evidence
        for evidence in session.scalars(
            select(Evidence).where(Evidence.evidence_id.in_(referenced_evidence_ids))
        ).all()
    }
    rows: list[tuple[str, str, str, Character]] = []
    for character in characters:
        tw_name = _stored_official_name(character.tw_name)
        if tw_name is None:
            raise RuntimeError(
                f"TW-available picker character has no stored official name: "
                f"{character.unit_key}"
            )
        source_evidence_ids = evidence_ids_by_unit[character.unit_key]
        if not any(
            _is_active_tw_official_a_evidence(evidence_by_id.get(evidence_id))
            for evidence_id in source_evidence_ids
        ):
            raise RuntimeError(
                "TW-available picker character lacks ACTIVE TW OFFICIAL/A "
                f"Evidence: {character.unit_key}"
            )
        jp_name = _stored_official_name(character.jp_name) or "UNKNOWN"
        rows.append((tw_name, character.unit_key, jp_name, character))
    rows.sort(key=lambda row: (row[0], row[1]))

    payload = [
        {
            "unit_key": unit_key,
            "tw_name": tw_name,
            "jp_name": jp_name,
            "tw_availability_status": "AVAILABLE",
        }
        for tw_name, unit_key, jp_name, _character in rows
    ]
    records = [
        ResponseMetaRecord(
            server="TW",
            evidence_ids=evidence_ids_by_unit[character.unit_key],
        )
        for _tw_name, _unit_key, _jp_name, character in rows
    ]
    return payload, records


def _arena_verified_serving_closure_is_mature(
    counter: ArenaCounter,
    *,
    evidence_ids: list[str],
    claim_ids: list[str],
    evidence_by_id: dict[str, Evidence],
    claim_by_id: dict[str, Claim],
    claim_evidence_ids: dict[str, list[str]],
) -> bool:
    """Fail closed if a stored VERIFIED label no longer has multi-source proof."""

    if counter.status != "VERIFIED":
        return True
    if (
        counter.outcome != "WIN"
        or counter.verification == "UNKNOWN"
        or counter.claim_confidence not in {"B", "C"}
        or counter.reproducibility != "CONFIRMED"
        or counter.source_tier not in _ARENA_VERIFIED_SOURCE_TIERS
        or counter.source_record_count < 2
        or counter.sample_size is None
        or counter.sample_size < 2
        or counter.wins is None
        or counter.wins < 2
        or counter.environment_match != "EXACT"
        or len(claim_ids) != 1
    ):
        return False

    claim_id = claim_ids[0]
    claim = claim_by_id.get(claim_id)
    if claim is None or (
        claim.status != "ACTIVE"
        or claim.module != "arena"
        or claim.server != "TW"
        or claim.claim_type != "SOURCE_FACT"
        or claim.claim_confidence != counter.claim_confidence
        or claim.independence_check != "YES"
        or claim.version_match != "YES"
    ):
        return False
    linked_evidence_ids = claim_evidence_ids.get(claim_id, [])
    if (
        len(linked_evidence_ids) < 2
        or len(linked_evidence_ids) != len(set(linked_evidence_ids))
        or set(linked_evidence_ids) != set(evidence_ids)
    ):
        return False

    evidence_rows = [evidence_by_id.get(evidence_id) for evidence_id in evidence_ids]
    if any(evidence is None for evidence in evidence_rows):
        return False
    source_identities: set[str] = set()
    for evidence in evidence_rows:
        assert evidence is not None  # narrowed by the fail-closed guard above
        if (
            evidence.status != "ACTIVE"
            or evidence.module != "arena"
            or evidence.server != "TW"
            or evidence.declared_claim_id != claim_id
            or evidence.source_tier not in _ARENA_VERIFIED_EVIDENCE_TIERS
        ):
            return False
        parsed_source = urlsplit(evidence.source_url)
        hostname = (parsed_source.hostname or "").lower()
        if (
            parsed_source.scheme.lower() != "https"
            or not hostname
            or parsed_source.username is not None
            or parsed_source.password is not None
        ):
            return False
        if hostname.startswith("www."):
            hostname = hostname[4:]
        source_identities.add(hostname)
    return len(source_identities) >= 2


def arena_counter_results(
    session: Session,
    *,
    defense_signature: str | None = None,
) -> list[dict[str, Any]]:
    """Serialize only exact, source-backed TW wins with complete 5v5 closure."""

    statement = (
        select(ArenaCounter, ArenaDefense)
        .join(ArenaDefense, ArenaDefense.defense_id == ArenaCounter.defense_id)
        .where(
            ArenaDefense.server == "TW",
            ArenaDefense.review_status == "CURRENT",
            ArenaDefense.status.in_(("VERIFIED", "PROVISIONAL", "SINGLE_REPORT")),
            ArenaCounter.status.in_(("VERIFIED", "PROVISIONAL", "SINGLE_REPORT")),
            ArenaCounter.match_type == "EXACT",
            ArenaCounter.outcome == "WIN",
            ArenaCounter.tw_availability_check == "PASS",
        )
        .order_by(ArenaDefense.defense_id, ArenaCounter.counter_id)
    )
    if defense_signature is not None:
        statement = statement.where(
            ArenaDefense.formation_signature == defense_signature
        )

    rows = session.execute(statement).all()
    if not rows:
        return []

    defense_ids = list(dict.fromkeys(defense.defense_id for _counter, defense in rows))
    counter_ids = [counter.counter_id for counter, _defense in rows]
    defense_member_rows = _arena_member_rows_by_owner(
        session,
        owner_column=ArenaDefenseMember.defense_id,
        owner_ids=defense_ids,
    )
    counter_member_rows = _arena_member_rows_by_owner(
        session,
        owner_column=ArenaCounterMember.counter_id,
        owner_ids=counter_ids,
    )
    evidence_ids_by_counter = _arena_relation_ids_by_counter(
        session,
        value_column=ArenaCounterEvidence.evidence_id,
        counter_ids=counter_ids,
    )
    claim_ids_by_counter = _arena_relation_ids_by_counter(
        session,
        value_column=ArenaCounterClaim.claim_id,
        counter_ids=counter_ids,
    )
    verified_counters = [counter for counter, _defense in rows if counter.status == "VERIFIED"]
    verified_evidence_ids = sorted(
        {
            evidence_id
            for counter in verified_counters
            for evidence_id in evidence_ids_by_counter.get(counter.counter_id, [])
        }
    )
    verified_claim_ids = sorted(
        {
            claim_id
            for counter in verified_counters
            for claim_id in claim_ids_by_counter.get(counter.counter_id, [])
        }
    )
    evidence_by_id: dict[str, Evidence] = {}
    claim_by_id: dict[str, Claim] = {}
    claim_evidence_ids: dict[str, list[str]] = defaultdict(list)
    if verified_counters:
        if verified_evidence_ids:
            evidence_by_id = {
                evidence.evidence_id: evidence
                for evidence in session.scalars(
                    select(Evidence).where(Evidence.evidence_id.in_(verified_evidence_ids))
                )
            }
        if verified_claim_ids:
            claim_by_id = {
                claim.claim_id: claim
                for claim in session.scalars(
                    select(Claim).where(Claim.claim_id.in_(verified_claim_ids))
                )
            }
            for claim_id, evidence_id in session.execute(
                select(ClaimEvidence.claim_id, ClaimEvidence.evidence_id).where(
                    ClaimEvidence.claim_id.in_(verified_claim_ids)
                )
            ):
                claim_evidence_ids[claim_id].append(evidence_id)

    result: list[dict[str, Any]] = []
    for counter, defense in rows:
        if not _arena_verified_serving_closure_is_mature(
            counter,
            evidence_ids=evidence_ids_by_counter.get(counter.counter_id, []),
            claim_ids=claim_ids_by_counter.get(counter.counter_id, []),
            evidence_by_id=evidence_by_id,
            claim_by_id=claim_by_id,
            claim_evidence_ids=claim_evidence_ids,
        ):
            raise RuntimeError(
                f"Arena VERIFIED maturity closure is invalid: {counter.counter_id}"
            )
        defense_members = _serialize_arena_members(
            owner_id=defense.defense_id,
            signature=defense.formation_signature,
            rows=defense_member_rows.get(defense.defense_id, []),
        )
        counter_members = _serialize_arena_members(
            owner_id=counter.counter_id,
            signature=counter.formation_signature,
            rows=counter_member_rows.get(counter.counter_id, []),
        )
        result.append(
            {
                "counter_id": counter.counter_id,
                "defense_id": defense.defense_id,
                "server": defense.server,
                "environment_version": defense.environment_version,
                "arena_bracket": defense.arena_bracket,
                "defense_signature": defense.formation_signature,
                "counter_signature": counter.formation_signature,
                "defense_members": defense_members,
                "counter_members": counter_members,
                "status": counter.status,
                "match_type": counter.match_type,
                "outcome": counter.outcome,
                "verification": counter.verification,
                "sample_size": counter.sample_size,
                "wins": counter.wins,
                "losses": counter.losses,
                "empirical_win_rate": counter.empirical_win_rate,
                "randomness": counter.randomness,
                "rng_risk": counter.rng_risk,
                "claim_confidence": counter.claim_confidence,
                "reproducibility": counter.reproducibility,
                "source_tier": counter.source_tier,
                "source_record_count": counter.source_record_count,
                "source_platforms": list(counter.source_platforms),
                "tw_availability_check": counter.tw_availability_check,
                "unavailable_unit_ids": list(counter.unavailable_unit_ids),
                "required_upgrade_check": counter.required_upgrade_check,
                "operation_mode": counter.operation_mode,
                "environment_match": counter.environment_match,
                "speed_conditions": counter.speed_conditions,
                "initial_action_notes": counter.initial_action_notes,
                "verified_date": counter.verified_date,
                "last_review_due": counter.last_review_due,
                "record_date_min": counter.record_date_min,
                "record_date_max": counter.record_date_max,
                "notes": counter.notes,
                "evidence_ids": evidence_ids_by_counter.get(counter.counter_id, []),
                "claim_ids": claim_ids_by_counter.get(counter.counter_id, []),
            }
        )
    return result


def evidence_detail(evidence: Evidence) -> dict[str, Any]:
    return {
        "evidence_id": evidence.evidence_id,
        "declared_claim_id": evidence.declared_claim_id,
        "linked_claim_id": evidence.linked_claim_id,
        "module": evidence.module,
        "server": evidence.server,
        "source_tier": evidence.source_tier,
        "evidence_confidence": evidence.evidence_confidence,
        "source_title": evidence.source_title,
        "source_url": evidence.source_url,
        "source_locator": evidence.source_locator,
        "published_date": evidence.published_date,
        "published_date_precision": evidence.published_date_precision,
        "verified_date": evidence.verified_date,
        "claim_summary": evidence.claim_summary,
        "limitations": evidence.limitations,
        "status": evidence.status,
    }


def claim_detail(session: Session, claim: Claim) -> dict[str, Any]:
    evidence_ids = session.scalars(
        select(ClaimEvidence.evidence_id)
        .where(ClaimEvidence.claim_id == claim.claim_id)
        .order_by(ClaimEvidence.evidence_id)
    ).all()
    return {
        "claim_id": claim.claim_id,
        "module": claim.module,
        "server": claim.server,
        "claim_text": claim.claim_text,
        "claim_type": claim.claim_type,
        "claim_confidence": claim.claim_confidence,
        "independence_check": claim.independence_check,
        "version_match": claim.version_match,
        "status": claim.status,
        "verified_date": claim.verified_date,
        "next_review_due": claim.next_review_due,
        "evidence_ids": list(evidence_ids),
        "notes": claim.notes,
    }
