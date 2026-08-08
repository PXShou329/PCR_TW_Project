from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pcr_database.materialization import (
    build_materialization_manifest,
    materialization_drift_reason,
)
from pcr_database.models import (
    Character,
    Claim,
    ClaimEvidence,
    Evidence,
    ImportRun,
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


B0_TARGET_GUIDE_ID = "TW_DEEP_FIRE_08_10_20260802"
B0_EXPECTED_COUNTS = {
    "stages": 1,
    "teams": 3,
    "team_members": 15,
    "characters": 8,
    "evidence": 18,
    "claims": 13,
    "operation_timelines": 8,
    "timeline_steps": 14,
}


def latest_import(session: Session) -> ImportRun | None:
    return session.scalar(
        select(ImportRun)
        .where(ImportRun.status == "SUCCEEDED")
        .order_by(ImportRun.imported_at.desc(), ImportRun.id.desc())
        .limit(1)
    )


def mirror_readiness(session: Session, run: ImportRun) -> tuple[bool, str]:
    """Verify that the B0 read mirror still materializes its imported closure.

    A successful ImportRun is provenance, not proof that serving rows still
    exist. Readiness therefore fails closed when a serving row is removed,
    replaced by another import, or no longer matches the declared three-team
    closure. This deliberately remains B0-specific until B1 introduces a
    revision-generic parity manifest.
    """

    if run.row_counts != B0_EXPECTED_COUNTS:
        return False, "manifest_count_drift"

    actual_counts = {
        "stages": session.scalar(select(func.count()).select_from(Stage)) or 0,
        "teams": session.scalar(select(func.count()).select_from(Team)) or 0,
        "team_members": session.scalar(select(func.count()).select_from(TeamMember)) or 0,
        "characters": session.scalar(select(func.count()).select_from(Character)) or 0,
        "evidence": session.scalar(select(func.count()).select_from(Evidence)) or 0,
        "claims": session.scalar(select(func.count()).select_from(Claim)) or 0,
        "operation_timelines": session.scalar(
            select(func.count()).select_from(OperationTimeline)
        ) or 0,
        "timeline_steps": session.scalar(select(func.count()).select_from(TimelineStep)) or 0,
    }
    if actual_counts != B0_EXPECTED_COUNTS:
        return False, "row_count_drift"

    drift_reason = materialization_drift_reason(
        run.manifest.get("materialization"),
        build_materialization_manifest(session),
    )
    if drift_reason is not None:
        return False, drift_reason

    stage = session.get(Stage, B0_TARGET_GUIDE_ID)
    if stage is None or stage.import_run_id != run.id or stage.team_count != 3:
        return False, "stage_drift"

    teams = session.scalars(
        select(Team).where(Team.guide_id == B0_TARGET_GUIDE_ID).order_by(Team.team_id)
    ).all()
    if (
        len(teams) != 3
        or len({team.signature for team in teams}) != 3
        or any(team.import_run_id != run.id for team in teams)
    ):
        return False, "team_drift"

    member_counts = dict(
        session.execute(
            select(TeamMember.team_id, func.count())
            .where(TeamMember.team_id.in_([team.team_id for team in teams]))
            .group_by(TeamMember.team_id)
        ).all()
    )
    if member_counts != {team.team_id: 5 for team in teams}:
        return False, "team_member_drift"

    if len(effective_team_signatures(session, B0_TARGET_GUIDE_ID)) != 3:
        return False, "effective_team_drift"

    for model in (Character, Evidence, Claim, OperationTimeline, TimelineStep):
        foreign_rows = session.scalar(
            select(func.count()).select_from(model).where(model.import_run_id != run.id)
        )
        if foreign_rows:
            return False, f"{model.__tablename__}_revision_drift"

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
    *,
    extra_warnings: list[str] | None = None,
) -> ResponseMeta:
    warnings = list(run.manifest.get("warnings", []))
    warnings.extend(extra_warnings or [])
    return ResponseMeta(
        generated_at=datetime.now(timezone.utc),
        source=SourceMeta(
            canonical_source=run.canonical_source,
            fixture_sha256=run.fixture_sha256,
            import_run_id=run.id,
            imported_at=run.imported_at,
            research_core_version=run.research_core_version,
        ),
        warnings=warnings,
    )


def baseline_data(session: Session, run: ImportRun) -> dict[str, Any]:
    counts = {
        "stages": session.scalar(select(func.count()).select_from(Stage)) or 0,
        "teams": session.scalar(select(func.count()).select_from(Team)) or 0,
        "team_members": session.scalar(select(func.count()).select_from(TeamMember)) or 0,
        "characters": session.scalar(select(func.count()).select_from(Character)) or 0,
        "evidence": session.scalar(select(func.count()).select_from(Evidence)) or 0,
        "claims": session.scalar(select(func.count()).select_from(Claim)) or 0,
        "operation_timelines": session.scalar(
            select(func.count()).select_from(OperationTimeline)
        ) or 0,
        "timeline_steps": session.scalar(select(func.count()).select_from(TimelineStep)) or 0,
    }
    featured = session.scalar(select(Stage).order_by(Stage.guide_id).limit(1))
    return {
        "research_core_version": run.research_core_version,
        "application_version": run.application_version,
        "canonical_source": run.canonical_source,
        "generated_at": run.imported_at,
        "counts": counts,
        "gates": run.manifest.get("stats", {}).get("gate", {}),
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
