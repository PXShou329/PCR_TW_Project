from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from pcr_database.models import Claim, Evidence, Stage, Team

from ..database import get_session
from ..repository import (
    baseline_data,
    claim_detail,
    evidence_detail,
    latest_import,
    mirror_readiness,
    response_meta,
    stage_detail,
    stage_summary,
    team_detail,
    timeline_data,
    timeline_warnings,
)
from ..schemas import (
    BaselineData,
    ClaimData,
    Envelope,
    EvidenceData,
    StageDetail,
    StageSummary,
    TeamDetail,
    TimelineData,
)


router = APIRouter(prefix="/api/v1", tags=["v1"])


def _run_or_503(session: Session):
    run = latest_import(session)
    if run is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "FIXTURE_NOT_READY", "resource": "import_run", "id": None},
        )
    materialized, reason = mirror_readiness(session, run)
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
    return run


def _not_found(resource: str, identifier: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "NOT_FOUND", "resource": resource, "id": identifier},
    )


@router.get("/baseline", response_model=Envelope[BaselineData])
def baseline(session: Session = Depends(get_session)) -> Envelope[BaselineData]:
    run = _run_or_503(session)
    return Envelope(data=baseline_data(session, run), meta=response_meta(run))


@router.get("/stages", response_model=Envelope[list[StageSummary]])
def list_stages(session: Session = Depends(get_session)) -> Envelope[list[StageSummary]]:
    run = _run_or_503(session)
    stages = session.scalars(select(Stage).order_by(Stage.guide_id)).all()
    return Envelope(data=[stage_summary(stage) for stage in stages], meta=response_meta(run))


@router.get("/stages/{guide_id}", response_model=Envelope[StageDetail])
def get_stage(guide_id: str, session: Session = Depends(get_session)) -> Envelope[StageDetail]:
    run = _run_or_503(session)
    stage = session.get(Stage, guide_id)
    if stage is None:
        raise _not_found("stage", guide_id)
    return Envelope(data=stage_detail(session, stage), meta=response_meta(run))


@router.get("/teams/{team_id}", response_model=Envelope[TeamDetail])
def get_team(team_id: str, session: Session = Depends(get_session)) -> Envelope[TeamDetail]:
    run = _run_or_503(session)
    team = session.get(Team, team_id)
    if team is None:
        raise _not_found("team", team_id)
    detail = team_detail(session, team)
    return Envelope(
        data=detail,
        meta=response_meta(run, extra_warnings=timeline_warnings(detail["timeline"])),
    )


@router.get("/teams/{team_id}/timelines", response_model=Envelope[TimelineData])
def get_team_timelines(
    team_id: str,
    session: Session = Depends(get_session),
) -> Envelope[TimelineData]:
    run = _run_or_503(session)
    team = session.get(Team, team_id)
    if team is None:
        raise _not_found("team", team_id)
    timeline = timeline_data(session, team)
    return Envelope(
        data=timeline,
        meta=response_meta(run, extra_warnings=timeline_warnings(timeline)),
    )


@router.get("/evidence/{evidence_id}", response_model=Envelope[EvidenceData])
def get_evidence(evidence_id: str, session: Session = Depends(get_session)) -> Envelope[EvidenceData]:
    run = _run_or_503(session)
    evidence = session.get(Evidence, evidence_id)
    if evidence is None:
        raise _not_found("evidence", evidence_id)
    return Envelope(data=evidence_detail(evidence), meta=response_meta(run))


@router.get("/claims/{claim_id}", response_model=Envelope[ClaimData])
def get_claim(claim_id: str, session: Session = Depends(get_session)) -> Envelope[ClaimData]:
    run = _run_or_503(session)
    claim = session.get(Claim, claim_id)
    if claim is None:
        raise _not_found("claim", claim_id)
    return Envelope(data=claim_detail(session, claim), meta=response_meta(run))


@router.get("/pvp/counters", response_model=Envelope[list[dict[str, object]]])
def pvp_counters(
    defense_signature: str | None = Query(default=None, max_length=600),
    session: Session = Depends(get_session),
) -> Envelope[list[dict[str, object]]]:
    del defense_signature
    run = _run_or_503(session)
    return Envelope(
        data=[],
        meta=response_meta(run, extra_warnings=["NO_VERIFIED_COUNTER"]),
    )
