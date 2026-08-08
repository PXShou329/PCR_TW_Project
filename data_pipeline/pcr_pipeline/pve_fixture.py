from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from pcr_database.models import (
    Character,
    Claim,
    ClaimEvidence,
    Evidence,
    ImportRun,
    Stage,
    StageClaim,
    StageEvidence,
    Team,
    TeamEvidence,
    TeamMember,
)
from pcr_database.materialization import (
    build_materialization_manifest,
    materialization_drift_reason,
)


TARGET_GUIDE_ID = "TW_DEEP_FIRE_08_10_20260802"
APPLICATION_VERSION = "3.0.0-b0"
CANONICAL_SOURCE = "research_core_file_ssot"

# B0 imports one audited vertical slice only.  Expanding this set requires a
# reviewed Source Registry change; restricted/China sources are deliberately
# absent and can never become a public href merely by editing the ledger.
B0_AUDITED_EVIDENCE_HOSTS = frozenset(
    {
        "games.appmatch.jp",
        "gamewith.jp",
        "www.princessconnect.so-net.tw",
        "www.youtube.com",
    }
)

SOURCE_FILES = (
    "18_TW_CHARACTER_AVAILABILITY.csv",
    "24_PVE_GUIDE_REGISTRY.csv",
    "25_PVE_TEAM_REGISTRY.csv",
    "92_EVIDENCE_LEDGER.csv",
    "93_CLAIM_REGISTER.csv",
    "tools/stats.json",
)


class FixtureValidationError(ValueError):
    """Raised before any write when the file closure is incomplete or inconsistent."""


class MirrorDriftError(RuntimeError):
    """Raised when a supposedly imported fixture is no longer materialized exactly."""


@dataclass(frozen=True)
class FixtureClosure:
    fingerprint: str
    guide: dict[str, str]
    teams: tuple[dict[str, str], ...]
    characters: tuple[dict[str, str], ...]
    evidence: tuple[dict[str, str], ...]
    claims: tuple[dict[str, str], ...]
    stage_evidence_ids: tuple[str, ...]
    stage_claim_ids: tuple[str, ...]
    team_evidence_ids: dict[str, tuple[str, ...]]
    dangling_claim_ids: tuple[str, ...]
    stats: dict[str, Any]
    file_hashes: dict[str, str]


@dataclass(frozen=True)
class ImportResult:
    import_run_id: str
    fixture_sha256: str
    created: bool
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


def _read_csv(path: Path, key: str) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or key not in reader.fieldnames:
            raise FixtureValidationError(f"{path.name} is missing key column {key}")
        rows = tuple({name: value or "" for name, value in row.items()} for row in reader)
    values = [row[key] for row in rows]
    if len(values) != len(set(values)):
        raise FixtureValidationError(f"{path.name} contains duplicate {key}")
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


def _file_fingerprint(root: Path) -> tuple[str, dict[str, str]]:
    digest = hashlib.sha256()
    file_hashes: dict[str, str] = {}
    for relative in SOURCE_FILES:
        content = (root / relative).read_bytes()
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
    if not isinstance(requirements, dict):
        raise FixtureValidationError(f"{team['team_id']} requirements must be an object")

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
    modes = {item.get("mode") for item in claims if isinstance(item, dict)}
    if team["operation_mode"] == "SOURCE_CONFLICT" and len(modes) < 2:
        raise FixtureValidationError(
            f"{team['team_id']} SOURCE_CONFLICT must preserve conflicting source modes"
        )
    if team["operation_mode"] != "SOURCE_CONFLICT" and modes != {team["operation_mode"]}:
        raise FixtureValidationError(
            f"{team['team_id']} operation mode differs from its source claims"
        )
    return requirements


def load_fire_8_10_closure(research_core: Path) -> FixtureClosure:
    root = research_core.resolve()
    missing_files = [relative for relative in SOURCE_FILES if not (root / relative).is_file()]
    if missing_files:
        raise FixtureValidationError(f"research core is missing files: {missing_files}")

    fingerprint, file_hashes = _file_fingerprint(root)
    characters_all = _read_csv(root / SOURCE_FILES[0], "unit_key")
    guides_all = _read_csv(root / SOURCE_FILES[1], "guide_id")
    teams_all = _read_csv(root / SOURCE_FILES[2], "team_id")
    evidence_all = _read_csv(root / SOURCE_FILES[3], "evidence_id")
    claims_all = _read_csv(root / SOURCE_FILES[4], "claim_id")
    stats = json.loads((root / SOURCE_FILES[5]).read_text(encoding="utf-8"))

    characters_by_id = {row["unit_key"]: row for row in characters_all}
    guides_by_id = {row["guide_id"]: row for row in guides_all}
    evidence_by_id = {row["evidence_id"]: row for row in evidence_all}
    claims_by_id = {row["claim_id"]: row for row in claims_all}

    if TARGET_GUIDE_ID not in guides_by_id:
        raise FixtureValidationError(f"target guide {TARGET_GUIDE_ID} is absent")
    guide = guides_by_id[TARGET_GUIDE_ID]
    teams = tuple(sorted(
        (row for row in teams_all if row["guide_id"] == TARGET_GUIDE_ID),
        key=lambda row: row["team_id"],
    ))
    if len(teams) != 3:
        raise FixtureValidationError(f"target guide must contain exactly 3 teams, got {len(teams)}")
    try:
        declared_team_count = int(guide["team_count"])
    except ValueError as exc:
        raise FixtureValidationError("guide team_count must be an integer") from exc

    signatures: set[tuple[str, ...]] = set()
    unit_keys: set[str] = set()
    team_evidence_ids: dict[str, tuple[str, ...]] = {}
    for team in teams:
        if team["clear_status"] != "VERIFIED" or team["tw_availability_check"] != "PASS":
            raise FixtureValidationError(
                f"{team['team_id']} is not an effective VERIFIED/PASS team"
            )
        members = tuple(team[f"slot{slot}"] for slot in range(1, 6))
        if any(not member for member in members) or len(set(members)) != 5:
            raise FixtureValidationError(f"{team['team_id']} must contain five distinct units")
        signature = tuple(sorted(members))
        if signature in signatures:
            raise FixtureValidationError(f"duplicate five-unit signature at {team['team_id']}")
        signatures.add(signature)
        unit_keys.update(members)
        _validate_requirements(team)
        support_slot = team["support_slot"].strip()
        if support_slot and support_slot not in {f"slot{slot}" for slot in range(1, 6)}:
            raise FixtureValidationError(f"{team['team_id']} support_slot is invalid")
        team_evidence_ids[team["team_id"]] = _split_ids(team["evidence_ids"])

    if declared_team_count != len(teams) or declared_team_count != len(signatures):
        raise FixtureValidationError(
            "guide team_count differs from the verified distinct five-unit team count"
        )
    _require_ids(unit_keys, characters_by_id, relation="team slots")
    characters = tuple(characters_by_id[key] for key in sorted(unit_keys))
    unavailable = [
        row["unit_key"] for row in characters if row["availability_status"] != "AVAILABLE"
    ]
    if unavailable:
        raise FixtureValidationError(f"team units are not TW AVAILABLE: {unavailable}")

    stage_evidence_ids = _split_ids(guide["evidence_ids"])
    stage_claim_ids = _split_ids(guide["claim_ids"])
    _require_ids(stage_evidence_ids, evidence_by_id, relation="guide evidence_ids")
    _require_ids(stage_claim_ids, claims_by_id, relation="guide claim_ids")
    for team_id, ids in team_evidence_ids.items():
        _require_ids(ids, evidence_by_id, relation=f"{team_id} evidence_ids")

    selected_evidence = set(stage_evidence_ids)
    for ids in team_evidence_ids.values():
        selected_evidence.update(ids)
    for character in characters:
        ids = _split_ids(character["source_evidence_ids"])
        _require_ids(ids, evidence_by_id, relation=f"{character['unit_key']} source_evidence_ids")
        selected_evidence.update(ids)

    selected_claims = set(stage_claim_ids)
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

    return FixtureClosure(
        fingerprint=fingerprint,
        guide=guide,
        teams=teams,
        characters=characters,
        evidence=evidence,
        claims=tuple(claims_by_id[key] for key in sorted(selected_claims)),
        stage_evidence_ids=stage_evidence_ids,
        stage_claim_ids=stage_claim_ids,
        team_evidence_ids=team_evidence_ids,
        dangling_claim_ids=tuple(sorted(dangling_claims)),
        stats=stats,
        file_hashes=file_hashes,
    )


def _upsert(session: Session, model: type[Any], key: Any, values: dict[str, Any]) -> None:
    row = session.get(model, key)
    if row is None:
        session.add(model(**values))
        return
    for name, value in values.items():
        setattr(row, name, value)


def _counts(closure: FixtureClosure) -> dict[str, int]:
    return {
        "stages": 1,
        "teams": len(closure.teams),
        "team_members": len(closure.teams) * 5,
        "characters": len(closure.characters),
        "evidence": len(closure.evidence),
        "claims": len(closure.claims),
    }


def _assert_materialized(session: Session, closure: FixtureClosure) -> None:
    stage = session.get(Stage, TARGET_GUIDE_ID)
    if (
        stage is None
        or stage.team_count != len(closure.teams)
        or stage.source_payload != closure.guide
    ):
        raise MirrorDriftError("idempotent fixture stage is missing or has a different team_count")
    expected_team_ids = {row["team_id"] for row in closure.teams}
    actual_team_ids = set(
        session.scalars(select(Team.team_id).where(Team.guide_id == TARGET_GUIDE_ID)).all()
    )
    if actual_team_ids != expected_team_ids:
        raise MirrorDriftError("idempotent fixture team ids drifted")
    member_count = session.scalar(
        select(func.count()).select_from(TeamMember).where(TeamMember.team_id.in_(expected_team_ids))
    )
    if member_count != len(expected_team_ids) * 5:
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

    for model, key_name, rows in (
        (Character, "unit_key", closure.characters),
        (Evidence, "evidence_id", closure.evidence),
        (Claim, "claim_id", closure.claims),
    ):
        for source_row in rows:
            stored = session.get(model, source_row[key_name])
            if stored is None or stored.source_payload != source_row:
                raise MirrorDriftError(
                    f"idempotent fixture {model.__tablename__} {source_row[key_name]} drifted"
                )

    stage_evidence = set(
        session.scalars(
            select(StageEvidence.evidence_id).where(StageEvidence.guide_id == TARGET_GUIDE_ID)
        ).all()
    )
    stage_claims = set(
        session.scalars(
            select(StageClaim.claim_id).where(StageClaim.guide_id == TARGET_GUIDE_ID)
        ).all()
    )
    if stage_evidence != set(closure.stage_evidence_ids):
        raise MirrorDriftError("idempotent fixture stage evidence links drifted")
    if stage_claims != set(closure.stage_claim_ids):
        raise MirrorDriftError("idempotent fixture stage claim links drifted")

    for team_id, expected in closure.team_evidence_ids.items():
        actual = set(
            session.scalars(
                select(TeamEvidence.evidence_id).where(TeamEvidence.team_id == team_id)
            ).all()
        )
        if actual != set(expected):
            raise MirrorDriftError(f"idempotent fixture {team_id} evidence links drifted")

    selected_evidence_ids = {row["evidence_id"] for row in closure.evidence}
    for row in closure.claims:
        expected = set(_split_ids(row["evidence_ids"])) & selected_evidence_ids
        actual = set(
            session.scalars(
                select(ClaimEvidence.evidence_id).where(ClaimEvidence.claim_id == row["claim_id"])
            ).all()
        )
        if actual != expected:
            raise MirrorDriftError(f"idempotent fixture {row['claim_id']} evidence links drifted")


def import_fire_8_10(
    session: Session,
    research_core: Path,
    *,
    application_version: str = APPLICATION_VERSION,
    now: datetime | None = None,
) -> ImportResult:
    """Validate and import the exact Fire Deep Zone 8-10 closure atomically.

    Parsing and all cross-registry checks happen before the transaction. No dummy
    Claim is created for an Evidence row whose declared Claim is absent.
    """

    closure = load_fire_8_10_closure(research_core)
    row_counts = _counts(closure)
    imported_at = now or datetime.now(timezone.utc)
    run_id = str(uuid4())

    with session.begin():
        previous = session.scalar(
            select(ImportRun).where(ImportRun.fixture_sha256 == closure.fingerprint)
        )
        if previous is not None:
            if previous.status != "SUCCEEDED":
                raise MirrorDriftError("fixture fingerprint exists without a successful import")
            _assert_materialized(session, closure)
            drift_reason = materialization_drift_reason(
                previous.manifest.get("materialization"),
                build_materialization_manifest(session),
            )
            if drift_reason is not None:
                raise MirrorDriftError(
                    f"idempotent fixture complete closure drifted: {drift_reason}"
                )
            return ImportResult(
                import_run_id=previous.id,
                fixture_sha256=closure.fingerprint,
                created=False,
                row_counts=dict(previous.row_counts),
                warnings=tuple(previous.manifest.get("warnings", [])),
            )

        other_successful_run = session.scalar(
            select(ImportRun.id).where(ImportRun.status == "SUCCEEDED").limit(1)
        )
        if other_successful_run is not None:
            raise MirrorDriftError(
                "B0 read mirror contains a different fixture fingerprint; "
                "rebuild the disposable mirror instead of partially updating it"
            )

        warnings: tuple[str, ...] = ()
        run = ImportRun(
            id=run_id,
            fixture_sha256=closure.fingerprint,
            canonical_source=CANONICAL_SOURCE,
            research_core_version=str(closure.stats.get("project_version", "UNKNOWN")),
            application_version=application_version,
            imported_at=imported_at,
            status="RUNNING",
            manifest={
                "target_guide_id": TARGET_GUIDE_ID,
                "input_file_sha256": closure.file_hashes,
                "stats": closure.stats,
                "warnings": list(warnings),
            },
            row_counts=row_counts,
        )
        session.add(run)
        session.flush()

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
                    "published_date": _parse_date(
                        row["published_date"], field=f"{row['evidence_id']}.published_date"
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

        guide = closure.guide
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
                    guide["verified_date"], field=f"{guide['guide_id']}.verified_date", required=True
                ),
                "applicable_version": guide["applicable_version"],
                "team_count": int(guide["team_count"]),
                "source_tier": guide["source_tier"],
                "claim_confidence": guide["claim_confidence"],
                "reproducibility": guide["reproducibility"],
                "last_review_due": _parse_date(
                    guide["last_review_due"], field=f"{guide['guide_id']}.last_review_due"
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
        session.execute(delete(TeamMember).where(TeamMember.team_id.in_(team_ids)))
        session.execute(delete(TeamEvidence).where(TeamEvidence.team_id.in_(team_ids)))
        session.execute(delete(StageEvidence).where(StageEvidence.guide_id == TARGET_GUIDE_ID))
        session.execute(delete(StageClaim).where(StageClaim.guide_id == TARGET_GUIDE_ID))
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
        for evidence_id in closure.stage_evidence_ids:
            session.add(StageEvidence(guide_id=TARGET_GUIDE_ID, evidence_id=evidence_id))
        for claim_id in closure.stage_claim_ids:
            session.add(StageClaim(guide_id=TARGET_GUIDE_ID, claim_id=claim_id))
        selected_evidence_ids = {row["evidence_id"] for row in closure.evidence}
        for row in closure.claims:
            for evidence_id in _split_ids(row["evidence_ids"]):
                if evidence_id in selected_evidence_ids:
                    session.add(ClaimEvidence(claim_id=row["claim_id"], evidence_id=evidence_id))

        session.flush()
        _assert_materialized(session, closure)
        run.manifest = {
            **run.manifest,
            "materialization": build_materialization_manifest(session),
        }
        run.status = "SUCCEEDED"
        session.flush()

    return ImportResult(
        import_run_id=run_id,
        fixture_sha256=closure.fingerprint,
        created=True,
        row_counts=row_counts,
        warnings=warnings,
    )
