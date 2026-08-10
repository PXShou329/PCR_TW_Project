from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import pcr_pipeline.pve_fixture as fixture_module
from pcr_database.models import ArenaSourceRecord, Base, ImportRun, ParenaCase
from pcr_pipeline.pve_fixture import import_pve_projection, load_pve_closure
from pcr_pipeline.pve_fixture import FixtureValidationError
from pcr_pipeline.research_core_snapshot import RP_B4_0_MANIFEST_SHA256


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "research_core" / "pcr_tw_project"
MANIFEST = ROOT / "scripts" / "research_core_rp_b4_0_manifest.sha256"


def sqlite_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def test_canonical_parena_source_and_case_projection_is_truthful() -> None:
    closure = load_pve_closure(CORE)
    assert len(closure.arena_sources) == 6
    assert len(closure.parena_cases) == 0
    assert closure.parena_matchups_by_case == {}
    assert closure.parena_source_ids_by_case == {}
    assert closure.parena_evidence_ids_by_case == {}
    assert closure.parena_claim_ids_by_case == {}


def test_canonical_b4_manifest_materializes_v5_without_rewriting_a6() -> None:
    engine = sqlite_engine()
    with Session(engine) as session:
        first = import_pve_projection(
            session,
            CORE,
            manifest_path=MANIFEST,
            expected_manifest_sha256=RP_B4_0_MANIFEST_SHA256,
        )
    assert first.created is True
    assert first.row_counts["arena_source_records"] == 6
    assert first.row_counts["parena_cases"] == 0
    with Session(engine) as session:
        run = session.get(ImportRun, first.import_run_id)
        assert run is not None
        assert run.manifest["projection"] == fixture_module.FULL_PARENA_PLATFORM_PROJECTION
        assert run.manifest["materialization"]["schema_version"] == 5
        assert session.scalar(select(func.count()).select_from(ArenaSourceRecord)) == 6
        assert session.scalar(select(func.count()).select_from(ParenaCase)) == 0

    with Session(engine) as session:
        replay = import_pve_projection(
            session,
            CORE,
            manifest_path=MANIFEST,
            expected_manifest_sha256=RP_B4_0_MANIFEST_SHA256,
        )
        assert replay.created is False
        assert replay.activated is False


def synthetic_mature_case_inputs():
    closure = load_pve_closure(CORE)
    unit_keys = [
        row["unit_key"]
        for row in closure.characters
        if row["availability_status"] == "AVAILABLE"
    ][:30]
    assert len(unit_keys) == 30
    characters = {
        unit_key: {"unit_key": unit_key, "availability_status": "AVAILABLE"}
        for unit_key in unit_keys
    }
    claims = {}
    evidence = {}
    arena_rows = []
    for number in (1, 2, 3):
        claim_id = f"CL-ARENA-{number}"
        evidence_id = f"EV-ARENA-{number}"
        claims[claim_id] = {
            "claim_id": claim_id,
            "status": "ACTIVE",
            "server": "TW",
            "module": "arena",
            "claim_type": "SOURCE_FACT",
            "claim_confidence": "C",
            "independence_check": "YES",
            "version_match": "YES",
            "evidence_ids": evidence_id,
            "verified_date": "2026-08-08",
            "next_review_due": "2026-08-31",
        }
        evidence[evidence_id] = {
            "evidence_id": evidence_id,
            "status": "ACTIVE",
            "server": "TW",
            "module": "arena",
            "claim_id": claim_id,
            "source_tier": "SINGLE_PLAYER_REPORT",
            "evidence_confidence": "C",
            "source_url": f"https://forum.gamer.com.tw/arena-{number}",
            "source_locator": f"arena-{number}",
            "source_title": f"arena-{number}",
            "verified_date": "2026-08-08",
            "published_date": "2026-08-07",
            "published_date_precision": "DAY",
        }
        enemy = unit_keys[(number - 1) * 5 : number * 5]
        counter = unit_keys[15 + (number - 1) * 5 : 15 + number * 5]
        arena_rows.append(
            {
                "counter_id": f"AC-{number}",
                "server": "TW",
                "environment_version": "TW-2026-08",
                "enemy_team_ids": ";".join(enemy),
                "counter_team_ids": ";".join(counter),
                "status": "VERIFIED",
                "tw_availability_check": "PASS",
                "reproducibility": "CONFIRMED",
                "verified_date": "2026-08-08",
                "last_review_due": "2026-08-31",
                "claim_ids": claim_id,
                "evidence_ids": evidence_id,
            }
        )

    claims["CL-PARENA-WIN"] = {
        "claim_id": "CL-PARENA-WIN",
        "status": "ACTIVE",
        "server": "TW",
        "module": "parena",
        "claim_type": "SOURCE_FACT",
        "claim_confidence": "D",
        "independence_check": "NO",
        "version_match": "YES",
        "evidence_ids": "EV-PARENA-WIN",
        "verified_date": "2026-08-09",
        "next_review_due": "2026-08-31",
    }
    evidence["EV-PARENA-WIN"] = {
        "evidence_id": "EV-PARENA-WIN",
        "status": "ACTIVE",
        "server": "TW",
        "module": "parena",
        "claim_id": "CL-PARENA-WIN",
        "source_tier": "SINGLE_PLAYER_REPORT",
        "evidence_confidence": "D",
        "source_url": "https://forum.gamer.com.tw/parena-win",
        "source_locator": "parena-win",
        "source_title": "parena-win",
        "verified_date": "2026-08-09",
        "published_date": "2026-08-09",
        "published_date_precision": "DAY",
    }
    source = {
        "source_id": "ARENA-SRC-TEST",
        "title": "pytest",
        "platform": "Bahamut",
        "source_type": "FORUM_THREAD",
        "server": "TW",
        "url": "https://forum.gamer.com.tw/source",
        "last_checked": "2026-08-10",
        "freshness_window": "90d",
        "access_status": "ACTIVE",
        "confidence_cap": "D",
        "extraction_method": "pytest",
        "notes": "pytest",
    }
    case = {
        "case_id": "PA-TW-TEST",
        "server": "TW",
        "environment_version": "TW-2026-08",
        "hidden_team_mode": "NONE",
        "status": "VERIFIED",
        "verified_date": "2026-08-10",
        "source_ids": "ARENA-SRC-TEST",
        "evidence_ids": "EV-ARENA-1;EV-ARENA-2;EV-ARENA-3;EV-PARENA-WIN",
        "claim_ids": "CL-ARENA-1;CL-ARENA-2;CL-ARENA-3;CL-PARENA-WIN",
        "tw_availability_check": "PASS",
        "non_overlap_check": "PASS",
        "reproducibility": "CONFIRMED",
        "last_review_due": "2026-08-31",
        "notes": "synthetic test-only mature case",
        "case_win_claim_id": "CL-PARENA-WIN",
    }
    for number, arena_row in enumerate(arena_rows, start=1):
        case[f"enemy_team{number}"] = arena_row["enemy_team_ids"]
        case[f"counter_team{number}"] = arena_row["counter_team_ids"]
        case[f"team{number}_result_claim_id"] = arena_row["claim_ids"]
    return (source,), (case,), tuple(arena_rows), characters, evidence, claims


def test_synthetic_mature_case_is_typed_only_inside_test_fixture() -> None:
    inputs = synthetic_mature_case_inputs()
    result = fixture_module._validate_parena_closure(
        inputs[0],
        inputs[1],
        arena_rows=inputs[2],
        characters_by_id=inputs[3],
        evidence_by_id=inputs[4],
        claims_by_id=inputs[5],
        today=date(2026, 8, 10),
    )
    assert [row["case_id"] for row in result[1]] == ["PA-TW-TEST"]
    assert len(result[2]["PA-TW-TEST"]) == 3
    values = fixture_module._parena_case_values(
        result[1][0],
        claims_by_id=inputs[5],
        import_run_id="00000000-0000-0000-0000-000000000801",
    )
    assert values["case_win_confidence"] == "D"


@pytest.mark.parametrize("confidence", ("B", "C", "D"))
def test_parena_case_values_preserve_canonical_win_confidence(confidence: str) -> None:
    inputs = synthetic_mature_case_inputs()
    claims = deepcopy(inputs[5])
    claims["CL-PARENA-WIN"]["claim_confidence"] = confidence

    values = fixture_module._parena_case_values(
        inputs[1][0],
        claims_by_id=claims,
        import_run_id="00000000-0000-0000-0000-000000000801",
    )

    assert values["case_win_confidence"] == confidence


@pytest.mark.parametrize("confidence", ("A", "E", "UNKNOWN"))
def test_parena_case_values_reject_noncanonical_win_confidence(
    confidence: str,
) -> None:
    inputs = synthetic_mature_case_inputs()
    claims = deepcopy(inputs[5])
    claims["CL-PARENA-WIN"]["claim_confidence"] = confidence

    with pytest.raises(FixtureValidationError, match="case WIN confidence is invalid"):
        fixture_module._parena_case_values(
            inputs[1][0],
            claims_by_id=claims,
            import_run_id="00000000-0000-0000-0000-000000000801",
        )


def test_synthetic_case_with_cross_team_overlap_fails_closed() -> None:
    inputs = list(synthetic_mature_case_inputs())
    cases = deepcopy(inputs[1])
    first_counter = cases[0]["counter_team1"].split(";")[0]
    third = cases[0]["counter_team3"].split(";")
    third[0] = first_counter
    cases[0]["counter_team3"] = ";".join(third)
    with pytest.raises(FixtureValidationError, match="3x5 TW AVAILABLE shape"):
        fixture_module._validate_parena_closure(
            inputs[0],
            cases,
            arena_rows=inputs[2],
            characters_by_id=inputs[3],
            evidence_by_id=inputs[4],
            claims_by_id=inputs[5],
            today=date(2026, 8, 10),
        )


@pytest.mark.parametrize(
    ("access_status", "confidence_cap"),
    [
        ("ACTIVE", "C"),
        ("PARTIAL", "D"),
        ("BLOCKED", "E"),
        ("STALE", "C"),
        ("ARCHIVED", "D"),
    ],
)
def test_arena_source_validator_accepts_exact_file46_enums(
    access_status: str,
    confidence_cap: str,
) -> None:
    source = deepcopy(synthetic_mature_case_inputs()[0][0])
    source.update(access_status=access_status, confidence_cap=confidence_cap)

    validated = fixture_module._validate_parena_closure(
        (source,),
        (),
        arena_rows=(),
        characters_by_id={},
        evidence_by_id={},
        claims_by_id={},
        today=date(2026, 8, 10),
    )

    assert validated[0][0]["access_status"] == access_status
    assert validated[0][0]["confidence_cap"] == confidence_cap


@pytest.mark.parametrize(
    ("access_status", "confidence_cap"),
    [
        ("REJECTED", "D"),
        ("UNKNOWN", "D"),
        ("ACTIVE", "A"),
        ("ACTIVE", "B"),
        ("ACTIVE", "UNKNOWN"),
    ],
)
def test_arena_source_validator_rejects_noncanonical_file46_enums(
    access_status: str,
    confidence_cap: str,
) -> None:
    source = deepcopy(synthetic_mature_case_inputs()[0][0])
    source.update(access_status=access_status, confidence_cap=confidence_cap)

    with pytest.raises(FixtureValidationError, match="invalid Arena source record"):
        fixture_module._validate_parena_closure(
            (source,),
            (),
            arena_rows=(),
            characters_by_id={},
            evidence_by_id={},
            claims_by_id={},
            today=date(2026, 8, 10),
        )
