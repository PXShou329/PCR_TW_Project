from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from pcr_database.models import Claim, Evidence, Stage, Team, arena_formation_signature

from ..database import get_session
from ..repository import (
    ResponseMetaRecord,
    active_revision,
    arena_counter_results,
    baseline_data,
    claim_detail,
    evidence_detail,
    has_arena_materialization,
    latest_import,
    mirror_readiness,
    pvp_character_options,
    response_meta,
    stage_detail,
    stage_summary,
    team_detail,
    timeline_data,
    timeline_warnings,
)
from ..schemas import (
    ArenaCounterData,
    BaselineData,
    ClaimData,
    Envelope,
    EvidenceData,
    PvpCharacterData,
    StageDetail,
    StageSummary,
    TeamDetail,
    TimelineData,
)


router = APIRouter(prefix="/api/v1", tags=["v1"])


def _run_or_503(session: Session):
    try:
        run = latest_import(session)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "resource": "database",
                "id": None,
            },
        ) from error
    if run is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "FIXTURE_NOT_READY", "resource": "import_run", "id": None},
        )
    try:
        materialized, reason = mirror_readiness(session, run)
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "resource": "database",
                "id": None,
            },
        ) from error
    if not materialized:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "FIXTURE_DRIFT",
                "resource": "import_run",
                "id": run.id,
                "reason": reason,
            },
        )
    revision = active_revision(session, run)
    if revision is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "FIXTURE_DRIFT",
                "resource": "import_run",
                "id": run.id,
                "reason": "active_pointer_drift",
            },
        )
    return run, revision


def _not_found(resource: str, identifier: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "NOT_FOUND", "resource": resource, "id": identifier},
    )


@router.get("/baseline", response_model=Envelope[BaselineData])
def baseline(session: Session = Depends(get_session)) -> Envelope[BaselineData]:
    run, revision = _run_or_503(session)
    return Envelope(
        data=baseline_data(session, run),
        meta=response_meta(run, revision),
    )


@router.get("/stages", response_model=Envelope[list[StageSummary]])
def list_stages(session: Session = Depends(get_session)) -> Envelope[list[StageSummary]]:
    run, revision = _run_or_503(session)
    stages = session.scalars(select(Stage).order_by(Stage.guide_id)).all()
    return Envelope(
        data=[stage_summary(stage) for stage in stages],
        meta=response_meta(run, revision),
    )


@router.get("/stages/{guide_id}", response_model=Envelope[StageDetail])
def get_stage(guide_id: str, session: Session = Depends(get_session)) -> Envelope[StageDetail]:
    run, revision = _run_or_503(session)
    stage = session.get(Stage, guide_id)
    if stage is None:
        raise _not_found("stage", guide_id)
    return Envelope(
        data=stage_detail(session, stage),
        meta=response_meta(run, revision),
    )


@router.get("/teams/{team_id}", response_model=Envelope[TeamDetail])
def get_team(team_id: str, session: Session = Depends(get_session)) -> Envelope[TeamDetail]:
    run, revision = _run_or_503(session)
    team = session.get(Team, team_id)
    if team is None:
        raise _not_found("team", team_id)
    detail = team_detail(session, team)
    return Envelope(
        data=detail,
        meta=response_meta(
            run,
            revision,
            extra_warnings=timeline_warnings(detail["timeline"]),
        ),
    )


@router.get("/teams/{team_id}/timelines", response_model=Envelope[TimelineData])
def get_team_timelines(
    team_id: str,
    session: Session = Depends(get_session),
) -> Envelope[TimelineData]:
    run, revision = _run_or_503(session)
    team = session.get(Team, team_id)
    if team is None:
        raise _not_found("team", team_id)
    timeline = timeline_data(session, team)
    return Envelope(
        data=timeline,
        meta=response_meta(
            run,
            revision,
            extra_warnings=timeline_warnings(timeline),
        ),
    )


@router.get("/evidence/{evidence_id}", response_model=Envelope[EvidenceData])
def get_evidence(evidence_id: str, session: Session = Depends(get_session)) -> Envelope[EvidenceData]:
    run, revision = _run_or_503(session)
    evidence = session.get(Evidence, evidence_id)
    if evidence is None:
        raise _not_found("evidence", evidence_id)
    return Envelope(
        data=evidence_detail(evidence),
        meta=response_meta(run, revision),
    )


@router.get("/claims/{claim_id}", response_model=Envelope[ClaimData])
def get_claim(claim_id: str, session: Session = Depends(get_session)) -> Envelope[ClaimData]:
    run, revision = _run_or_503(session)
    claim = session.get(Claim, claim_id)
    if claim is None:
        raise _not_found("claim", claim_id)
    return Envelope(
        data=claim_detail(session, claim),
        meta=response_meta(run, revision),
    )


def _exact_defense_signature(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return arena_formation_signature(value.split(";"))
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_DEFENSE_SIGNATURE",
                "resource": "arena_defense",
                "id": value,
                "reason": str(error),
            },
        ) from error


@router.get("/pvp/characters", response_model=Envelope[list[PvpCharacterData]])
def pvp_characters(
    session: Session = Depends(get_session),
) -> Envelope[list[PvpCharacterData]]:
    run, revision = _run_or_503(session)
    try:
        characters, records = pvp_character_options(session)
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "FIXTURE_DRIFT",
                "resource": "pvp_characters",
                "id": None,
                "reason": "character_serving_closure_invalid",
            },
        ) from error
    return Envelope(
        data=characters,
        meta=response_meta(run, revision, records=records),
    )


def _arena_meta_records(counters: list[dict]) -> list[ResponseMetaRecord]:
    """Aggregate only mechanically closed counter facts at envelope scope.

    Freshness and confidence remain unknown until defense, Claim, and Evidence
    records participate in one typed metadata closure.
    """

    return [
        ResponseMetaRecord(
            server=counter["server"],
            environment_version=counter["environment_version"],
            evidence_ids=tuple(counter["evidence_ids"]),
            claim_ids=tuple(counter["claim_ids"]),
        )
        for counter in counters
    ]


@router.get("/pvp/counters", response_model=Envelope[list[ArenaCounterData]])
def pvp_counters(
    defense_signature: str | None = Query(default=None, max_length=600),
    session: Session = Depends(get_session),
) -> Envelope[list[ArenaCounterData]]:
    exact_signature = _exact_defense_signature(defense_signature)
    run, revision = _run_or_503(session)
    if not has_arena_materialization(run):
        return Envelope(
            data=[],
            meta=response_meta(
                run,
                revision,
                extra_warnings=["NO_ARENA_MATERIALIZATION", "NO_VERIFIED_COUNTER"],
            ),
        )

    try:
        counters = arena_counter_results(
            session,
            defense_signature=exact_signature,
        )
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "FIXTURE_DRIFT",
                "resource": "arena_materialization",
                "id": exact_signature,
                "reason": "arena_serving_closure_invalid",
            },
        ) from error
    warnings: list[str] = []
    if exact_signature is not None and not counters:
        warnings.append("NO_EXACT_COUNTER")
    if not any(counter["status"] == "VERIFIED" for counter in counters):
        warnings.append("NO_VERIFIED_COUNTER")
    if any(counter["status"] == "SINGLE_REPORT" for counter in counters):
        warnings.append("SINGLE_REPORT_REFERENCE_ONLY")
    return Envelope(
        data=counters,
        meta=response_meta(
            run,
            revision,
            records=_arena_meta_records(counters),
            extra_warnings=warnings,
        ),
    )
