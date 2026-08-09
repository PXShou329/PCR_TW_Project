from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from pcr_database.materialization import (
    MATERIALIZATION_MANIFEST_VERSION,
    build_materialization_manifest,
)
from pcr_database.models import (
    Base,
    GachaCommunitySource,
    GachaTimelineClaim,
    GachaTimelineCommunitySource,
    GachaTimelineEvent,
    GachaTimelineEvidence,
    ImportRun,
)
from pcr_pipeline.pve_fixture import (
    FixtureValidationError,
    MirrorDriftError,
    import_fire_8_10,
    load_pve_closure,
)
from pcr_pipeline.research_core_snapshot import VALIDATOR_RUNTIME_PATHS
import pcr_pipeline.research_core_snapshot as snapshot_module
from pcr_pipeline.research_core_snapshot import SnapshotContract


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_CORE = ROOT / "research_core" / "pcr_tw_project"


def sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


def rewrite_csv(path: Path, mutate) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    mutate(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def manifested_core(tmp_path: Path) -> tuple[Path, Path, str]:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    lines: list[str] = []
    for path in sorted(candidate for candidate in core.rglob("*") if candidate.is_file()):
        relative = path.relative_to(core).as_posix()
        if relative in VALIDATOR_RUNTIME_PATHS:
            continue
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    content = ("\n".join(lines) + "\n").encode("utf-8")
    manifest = tmp_path / "MANIFEST.sha256"
    manifest.write_bytes(content)
    return core, manifest, hashlib.sha256(content).hexdigest()


def live_snapshot_contract(core: Path) -> SnapshotContract:
    files = [
        path
        for path in core.rglob("*")
        if path.is_file()
        and path.relative_to(core).as_posix() not in VALIDATOR_RUNTIME_PATHS
    ]
    csv_files = [path for path in files if path.suffix == ".csv"]
    csv_row_count = 0
    for path in csv_files:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            csv_row_count += sum(1 for _ in csv.DictReader(handle))
    with (core / "92_EVIDENCE_LEDGER.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        evidence_rows = list(csv.DictReader(handle))
    with (core / "93_CLAIM_REGISTER.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        claim_rows = list(csv.DictReader(handle))
    return SnapshotContract(
        file_count=len(files),
        csv_file_count=len(csv_files),
        csv_row_count=csv_row_count,
        evidence_to_claim_count=sum(
            bool(row["claim_id"].strip()) for row in evidence_rows
        ),
        claim_to_evidence_count=sum(
            len([item for item in row["evidence_ids"].split(";") if item.strip()])
            for row in claim_rows
        ),
    )


def test_canonical_gacha_closure_imports_atomically_and_replays_idempotently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core, manifest, manifest_sha256 = manifested_core(tmp_path)
    monkeypatch.setattr(
        snapshot_module,
        "CURRENT_SNAPSHOT_CONTRACT",
        live_snapshot_contract(core),
    )
    closure = load_pve_closure(core)
    assert len(closure.gacha_events) == 5
    assert len(closure.gacha_community_sources) == 4
    assert sum(map(len, closure.gacha_evidence_ids_by_event.values())) == 10
    assert sum(map(len, closure.gacha_claim_ids_by_event.values())) == 8
    assert sum(map(len, closure.gacha_community_source_ids_by_event.values())) == 0

    engine = sqlite_engine()
    with Session(engine) as session:
        result = import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
    assert result.created is True
    assert result.activated is True
    assert result.row_counts["gacha_timeline_events"] == 5
    assert result.row_counts["gacha_community_sources"] == 4
    assert result.row_counts["gacha_timeline_evidence"] == 10
    assert result.row_counts["gacha_timeline_claims"] == 8
    assert result.row_counts["gacha_timeline_community_sources"] == 0

    with Session(engine) as session:
        events = session.scalars(
            select(GachaTimelineEvent).order_by(GachaTimelineEvent.event_id)
        ).all()
        sources = session.scalars(
            select(GachaCommunitySource).order_by(GachaCommunitySource.source_id)
        ).all()
        run = session.get(ImportRun, result.import_run_id)
        assert run is not None
        materialization = build_materialization_manifest(session)
        assert materialization == run.manifest["materialization"]
        assert materialization["schema_version"] == MATERIALIZATION_MANIFEST_VERSION

    assert len(events) == 5
    assert {event.source_server for event in events} == {"JP"}
    assert {event.target_server for event in events} == {"TW"}
    assert all(event.tw_name is None for event in events)
    assert events[0].source_payload["tw_temp_name"] == "【待查證】"
    assert {event.limited_status for event in events} == {"YES", "UNKNOWN"}
    assert {event.event_id: event.limited_claim_id for event in events} == {
        "JP_20260630_shefi_vardrache": "CLM-SHEFI-POOL",
        "JP_20260703_luisemarie_summer": "CLM-LUISE-DATE",
        "JP_20260731_fubuki_summer": "CLM-JP-FUBUKI-DATE",
        "JP_20260815_vampy_summer": None,
        "JP_20260823_tia": None,
    }
    assert events[0].source_payload["limited_claim_id"] == "CLM-SHEFI-POOL"
    assert [(source.coverage_start, source.coverage_end) for source in sources] == [
        ("2026-01", "2026-12"),
        ("2025-05-04", "2026-12-01"),
        (None, None),
        ("2022-08-05", "2022-10-07"),
    ]

    with Session(engine) as session:
        assert session.query(GachaTimelineEvidence).count() == 10
        assert session.query(GachaTimelineClaim).count() == 8
        assert session.query(GachaTimelineCommunitySource).count() == 0

    with Session(engine) as session:
        replay = import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
    assert replay.created is False
    assert replay.activated is False
    assert replay.import_run_id == result.import_run_id


def test_gacha_coverage_accepts_mixed_month_and_day_precision(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    rewrite_csv(
        core / "45_GACHA_COMMUNITY_SOURCE_INDEX.csv",
        lambda rows: rows[0].update(
            coverage_start="2026-02-15",
            coverage_end="2026-02",
        ),
    )

    closure = load_pve_closure(core)
    source = next(
        row
        for row in closure.gacha_community_sources
        if row["source_id"] == "GACHA-COMM-001"
    )
    assert source["coverage_start"] == "2026-02-15"
    assert source["coverage_end"] == "2026-02"


@pytest.mark.parametrize(
    ("relative_path", "mutate", "message"),
    (
        (
            "45_GACHA_COMMUNITY_SOURCE_INDEX.csv",
            lambda rows: rows[0].update(coverage_start="2026-13"),
            "YYYY-MM or YYYY-MM-DD",
        ),
        (
            "45_GACHA_COMMUNITY_SOURCE_INDEX.csv",
            lambda rows: rows[0].update(coverage_start="2026-02-30"),
            "is not a calendar date",
        ),
        (
            "45_GACHA_COMMUNITY_SOURCE_INDEX.csv",
            lambda rows: rows[0].update(confidence_cap="A"),
            "confidence_cap is invalid",
        ),
        (
            "45_GACHA_COMMUNITY_SOURCE_INDEX.csv",
            lambda rows: rows[0].update(
                coverage_start="2026-12", coverage_end="2026-01"
            ),
            "coverage range is invalid",
        ),
        (
            "41_GACHA_TIMELINE.csv",
            lambda rows: next(
                row for row in rows if row["maturity"] == "RESEARCH"
            ).update(pve_value="高"),
            "must remain NOT_EVALUATED/UNKNOWN",
        ),
        (
            "41_GACHA_TIMELINE.csv",
            lambda rows: next(
                row for row in rows if row["maturity"] == "RESEARCH"
            ).update(relative_priority="必抽"),
            "must remain NOT_EVALUATED/UNKNOWN",
        ),
        (
            "41_GACHA_TIMELINE.csv",
            lambda rows: rows[0].update(limited="推定限定"),
            "must be YES/NO/UNKNOWN source truth",
        ),
        (
            "41_GACHA_TIMELINE.csv",
            lambda rows: rows[0].update(limited_claim_id=""),
            "limited lacks designated ACTIVE JP OFFICIAL/A provenance",
        ),
        (
            "41_GACHA_TIMELINE.csv",
            lambda rows: rows[0].update(limited_claim_id="CLM-LUISE-DATE"),
            "limited lacks designated ACTIVE JP OFFICIAL/A provenance",
        ),
        (
            "41_GACHA_TIMELINE.csv",
            lambda rows: next(
                row for row in rows if row["limited"] == "UNKNOWN"
            ).update(limited_claim_id="CLM-JP-85-LIVE-GACHA"),
            "limited_claim_id must be empty when limited is UNKNOWN",
        ),
        (
            "92_EVIDENCE_LEDGER.csv",
            lambda rows: next(
                row for row in rows if row["evidence_id"] == "ev032"
            ).update(evidence_confidence="D"),
            "limited lacks designated ACTIVE JP OFFICIAL/A provenance",
        ),
        (
            "92_EVIDENCE_LEDGER.csv",
            lambda rows: next(
                row for row in rows if row["evidence_id"] == "ev032"
            ).update(source_tier="MAJOR_GUIDE"),
            "limited lacks designated ACTIVE JP OFFICIAL/A provenance",
        ),
        (
            "93_CLAIM_REGISTER.csv",
            lambda rows: next(
                row for row in rows if row["claim_id"] == "CLM-SHEFI-POOL"
            ).update(claim_confidence="B"),
            "limited lacks designated ACTIVE JP OFFICIAL/A provenance",
        ),
        (
            "41_GACHA_TIMELINE.csv",
            lambda rows: rows[0].update(tw_temp_name="自行翻譯名"),
            "lacks direct ACTIVE TW OFFICIAL/A support",
        ),
        (
            "41_GACHA_TIMELINE.csv",
            lambda rows: rows[0].update(community_source_count="1"),
            "differs from linked sources",
        ),
        (
            "41_GACHA_TIMELINE.csv",
            lambda rows: rows[0].update(evidence_ids="ev-does-not-exist"),
            "references missing ids",
        ),
    ),
)
def test_gacha_source_truth_mutations_fail_closed(
    tmp_path: Path,
    relative_path: str,
    mutate,
    message: str,
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    rewrite_csv(core / relative_path, mutate)
    with pytest.raises(FixtureValidationError, match=message):
        load_pve_closure(core)


def _rewrite_vampy_as_official_override(core: Path, *, evidence_confidence: str) -> None:
    rewrite_csv(
        core / "41_GACHA_TIMELINE.csv",
        lambda rows: next(
            row
            for row in rows
            if row["event_id"] == "JP_20260815_vampy_summer"
        ).update(forecast_method="OFFICIAL_OVERRIDE"),
    )
    rewrite_csv(
        core / "93_CLAIM_REGISTER.csv",
        lambda rows: next(
            row for row in rows if row["claim_id"] == "CLM-JP-85-LIVE-GACHA"
        ).update(server="TW"),
    )
    rewrite_csv(
        core / "92_EVIDENCE_LEDGER.csv",
        lambda rows: next(
            row for row in rows if row["evidence_id"] == "ev123"
        ).update(server="TW", evidence_confidence=evidence_confidence),
    )


def test_official_override_requires_direct_active_tw_official_a_closure(
    tmp_path: Path,
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    _rewrite_vampy_as_official_override(core, evidence_confidence="A")

    closure = load_pve_closure(core)
    event = next(
        row
        for row in closure.gacha_events
        if row["event_id"] == "JP_20260815_vampy_summer"
    )
    assert event["forecast_method"] == "OFFICIAL_OVERRIDE"


def test_official_override_rejects_weak_tw_evidence(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    _rewrite_vampy_as_official_override(core, evidence_confidence="D")

    with pytest.raises(
        FixtureValidationError,
        match="OFFICIAL_OVERRIDE lacks direct ACTIVE TW OFFICIAL/A provenance",
    ):
        load_pve_closure(core)


def test_idempotent_replay_detects_limited_claim_materialization_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core, manifest, manifest_sha256 = manifested_core(tmp_path)
    monkeypatch.setattr(
        snapshot_module,
        "CURRENT_SNAPSHOT_CONTRACT",
        live_snapshot_contract(core),
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        event_row = session.get(
            GachaTimelineEvent,
            "JP_20260630_shefi_vardrache",
        )
        assert event_row is not None
        event_row.limited_claim_id = "CLM-SHEFI-DATE"
        session.commit()

        with pytest.raises(MirrorDriftError, match="Gacha event .* drifted"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )
