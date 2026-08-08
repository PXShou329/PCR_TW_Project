from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pcr_pipeline.research_core_snapshot import (
    SnapshotDriftError,
    canonical_json_sha256,
    materialized_report,
)
from pcr_database.materialization import (
    SERVING_MODELS,
    build_materialization_manifest,
    materialization_drift_reason,
)
from pcr_database.models import (
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
}
_SERVING_TABLE_NAMES = frozenset(model.__tablename__ for model in SERVING_MODELS)
_READINESS_CACHE_MAX_ENTRIES = 32
_readiness_cache: OrderedDict[tuple[int, str, str, int, str], None] = OrderedDict()
_readiness_cache_lock = Lock()


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
    declared_counts = run.manifest.get("serving_row_counts")
    if (
        not isinstance(declared_counts, dict)
        or set(declared_counts) != _SERVING_TABLE_NAMES
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in declared_counts.values()
        )
    ):
        return None

    materialization = run.manifest.get("materialization")
    if not isinstance(materialization, dict):
        return None
    tables = materialization.get("tables")
    if not isinstance(tables, dict) or set(tables) != _SERVING_TABLE_NAMES:
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
        or set(state.serving_counts) != _SERVING_TABLE_NAMES
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
        build_materialization_manifest(session),
    )
    if drift_reason is not None:
        return False, drift_reason

    if _is_postgresql(session):
        _cache_ready(cache_key)

    return True, "imported"


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
    extra_warnings: list[str] | None = None,
) -> ResponseMeta:
    if revision.materialization_sha256 is None:
        raise RuntimeError("active revision has no materialization digest")
    warnings = list(run.manifest.get("warnings", []))
    warnings.extend(extra_warnings or [])
    return ResponseMeta(
        generated_at=datetime.now(timezone.utc),
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
        name: serving_counts[model.__tablename__]
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
