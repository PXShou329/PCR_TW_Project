from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import pcr_pipeline.pve_fixture as fixture_module
from pcr_api.repository import arena_counter_results
from pcr_database.models import (
    ArenaCounter,
    ArenaCounterClaim,
    ArenaCounterEvidence,
    ArenaCounterMember,
    ArenaDefense,
    ArenaDefenseMember,
    Base,
    Character,
    Claim,
    CoreRevision,
    Evidence,
    ImportRun,
    MaterializationState,
    OperationTimeline,
    RevisionActivation,
    Stage,
    Team,
    TeamMember,
    TimelineStep,
)
from pcr_pipeline.pve_fixture import (
    TARGET_GUIDE_ID,
    FixtureValidationError,
    MirrorDriftError,
    import_fire_8_10,
    import_pve_projection,
    load_fire_8_10_closure,
    load_pve_closure,
)
from pcr_pipeline.research_core_snapshot import (
    EXPECTED_CSV_ROW_COUNT,
    RP_A5_MANIFEST_SHA256,
    RP_A4_MANIFEST_SHA256,
    RP_A4_SNAPSHOT_CONTRACT,
    RP_A3_MANIFEST_SHA256,
    RP_A3_SNAPSHOT_CONTRACT,
    RP_A2_MANIFEST_SHA256,
    RP_A2_SNAPSHOT_CONTRACT,
    SnapshotValidationError,
    VALIDATOR_RUNTIME_PATHS,
    snapshot_contract_for_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_CORE = ROOT / "research_core" / "pcr_tw_project"
A4_MANIFEST = ROOT / "scripts" / "research_core_rp_a4_manifest.sha256"
A5_MANIFEST = ROOT / "scripts" / "research_core_rp_a5_manifest.sha256"
A3_MANIFEST = ROOT / "scripts" / "research_core_rp_a3_manifest.sha256"
RP_A2_MANIFEST = ROOT / "scripts" / "research_core_rp_a2_manifest.sha256"
SYNTHETIC_GUIDE_ID = "TW_DEEP_FIRE_09_10_SYNTHETIC"
SYNTHETIC_TEAM_ID = "TM-F910-SYNTHETIC"
SYNTHETIC_AXIS_ID = "AX-F910-SYNTHETIC-EV051"


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


def write_tree_manifest(core: Path, destination: Path) -> str:
    lines = []
    for path in sorted(candidate for candidate in core.rglob("*") if candidate.is_file()):
        relative = path.relative_to(core).as_posix()
        if relative in VALIDATOR_RUNTIME_PATHS:
            continue
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    canonical = ("\n".join(lines) + "\n").encode("utf-8")
    destination.write_bytes(canonical)
    return hashlib.sha256(canonical).hexdigest()


def build_manifested_core(
    tmp_path: Path,
    *,
    name: str,
) -> tuple[Path, Path, str]:
    core = tmp_path / name / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    manifest = tmp_path / f"{name}.sha256"
    return core, manifest, write_tree_manifest(core, manifest)


def export_checkpoint_core(tmp_path: Path, ref: str = "rp-b1-1") -> Path:
    """Export an immutable tagged research core without touching the worktree."""

    checkpoint_name = ref.replace("/", "_")
    archive = tmp_path / f"{checkpoint_name}.tar"
    subprocess.run(
        [
            "git",
            "archive",
            "--format=tar",
            f"--output={archive}",
            ref,
            "research_core/pcr_tw_project",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    destination = tmp_path / checkpoint_name
    destination.mkdir()
    with tarfile.open(archive, mode="r:") as bundle:
        bundle.extractall(destination, filter="data")
    return destination / "research_core" / "pcr_tw_project"


def build_synthetic_multi_stage_core(
    tmp_path: Path,
    *,
    name: str = "synthetic",
    source_core: Path = RESEARCH_CORE,
) -> tuple[Path, Path, str]:
    core = tmp_path / name / "pcr_tw_project"
    shutil.copytree(source_core, core)

    def add_guide(rows):
        source = next(row for row in rows if row["guide_id"] == TARGET_GUIDE_ID)
        guide = dict(source)
        guide.update(
            {
                "guide_id": SYNTHETIC_GUIDE_ID,
                "stage": "9-10",
                "status": "PROVISIONAL",
                "team_count": "0",
                "notes": "synthetic provisional stage for importer closure tests",
            }
        )
        rows.append(guide)

    def add_team(rows):
        source = next(row for row in rows if row["team_id"] == "TM-F810-03")
        requirements = fixture_module.json.loads(source["requirements"])
        requirements["timeline_ref"] = SYNTHETIC_AXIS_ID
        team = dict(source)
        team.update(
            {
                "team_id": SYNTHETIC_TEAM_ID,
                "guide_id": SYNTHETIC_GUIDE_ID,
                "stage": "紅焰9-10",
                "requirements": fixture_module.json.dumps(
                    requirements,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "clear_status": "PROVISIONAL",
                "notes": "synthetic non-effective team retained by typed projection",
            }
        )
        rows.append(team)

    def add_timeline(rows):
        source = next(
            row for row in rows if row["source_axis_id"] == "AX-F810-03-EV051"
        )
        timeline = dict(source)
        timeline.update(
            {
                "source_axis_id": SYNTHETIC_AXIS_ID,
                "team_id": SYNTHETIC_TEAM_ID,
                "timeline_variant_name": "synthetic source gap",
                "notes": "synthetic timeline closure row",
            }
        )
        rows.append(timeline)

    rewrite_csv(core / "24_PVE_GUIDE_REGISTRY.csv", add_guide)
    rewrite_csv(core / "25_PVE_TEAM_REGISTRY.csv", add_team)
    rewrite_csv(core / "26_PVE_OPERATION_TIMELINES.csv", add_timeline)
    manifest = tmp_path / f"{name}.sha256"
    return core, manifest, write_tree_manifest(core, manifest)


def allow_synthetic_snapshot_row_count(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_core: Path,
) -> None:
    original_loader = fixture_module.load_research_core_snapshot
    synthetic_root = synthetic_core.resolve()

    def load_with_synthetic_row_count(research_core, *args, **kwargs):
        if Path(research_core).resolve() == synthetic_root:
            kwargs["expected_csv_row_count"] = EXPECTED_CSV_ROW_COUNT + 3
        return original_loader(research_core, *args, **kwargs)

    monkeypatch.setattr(
        fixture_module,
        "load_research_core_snapshot",
        load_with_synthetic_row_count,
    )


def test_loader_builds_all_pve_closure_without_strengthening_unknowns() -> None:
    closure = load_pve_closure(RESEARCH_CORE)

    assert closure.guide["status"] == "VERIFIED"
    assert closure.guide["team_count"] == "5"
    assert [guide["guide_id"] for guide in closure.guides] == [
        TARGET_GUIDE_ID,
        "TW_DEEP_FIRE_10_10_20260802",
        "TW_DEEP_WATER_08_10_20260808",
    ]
    assert [team["team_id"] for team in closure.teams] == [
        "TM-F810-01",
        "TM-F810-02",
        "TM-F810-03",
        "TM-F810-04",
        "TM-F810-05",
        "TM-W810-01",
        "TM-W810-02",
        "TM-W810-03",
        "TM-W810-04",
        "TM-W810-05",
    ]
    assert len(closure.characters) == 35
    assert len(closure.evidence) == 64
    assert len(closure.claims) == 62
    assert len(closure.timelines) == 15
    assert len(closure.timeline_steps) == 37
    assert closure.dangling_claim_ids == ()
    assert [row["counter_id"] for row in closure.arena_rows] == [
        "TW_ARENA_20260525_01",
        "TW_ARENA_20260525_02",
    ]
    assert closure.arena_evidence_ids_by_counter == {
        "TW_ARENA_20260525_01": ("ev113", "ev114"),
        "TW_ARENA_20260525_02": ("ev113", "ev115"),
    }
    assert closure.arena_claim_ids_by_counter == {
        "TW_ARENA_20260525_01": (
            "CLM-ARENA-TW-DEF-20260525",
            "CLM-ARENA-TW-COUNTER-20260525-01",
        ),
        "TW_ARENA_20260525_02": (
            "CLM-ARENA-TW-DEF-20260525",
            "CLM-ARENA-TW-COUNTER-20260525-02",
        ),
    }

    first = closure.teams[0]
    assert first["operation_mode"] == "SOURCE_CONFLICT"
    requirements = fixture_module._validate_requirements(first)
    assert {item["mode"] for item in requirements["operation_mode_claims"]} == {
        "AUTO",
        "SEMI_AUTO",
    }
    assert all(
        value == "UNKNOWN"
        for slot in requirements["slots"].values()
        for value in slot.values()
    )
    fourth = next(team for team in closure.teams if team["team_id"] == "TM-F810-04")
    assert fourth["operation_mode"] == "UNKNOWN"
    fourth_requirements = fixture_module._validate_requirements(fourth)
    assert fourth_requirements["operation_mode_claims"] == [
        {"mode": "UNKNOWN", "source_id": "yt_p95ZoBCWuYE"}
    ]
    fifth_steps = [
        step
        for step in closure.timeline_steps
        if step["timeline_id"] == "TL-F810-05-EV083"
    ]
    assert len(fifth_steps) == 5
    assert all(step["trigger_type"] == "SOURCE_TEXT_ONLY" for step in fifth_steps)
    assert all(step["action_type"] == "NO_ACTION" for step in fifth_steps)


def test_water_8_10_closure_preserves_five_verified_teams_and_source_axes() -> None:
    closure = load_pve_closure(RESEARCH_CORE)
    guide_id = "TW_DEEP_WATER_08_10_20260808"
    guide = next(row for row in closure.guides if row["guide_id"] == guide_id)
    teams = [row for row in closure.teams if row["guide_id"] == guide_id]

    assert guide["status"] == "VERIFIED"
    assert guide["team_count"] == "5"
    assert guide["reproducibility"] == "CONFIRMED"
    assert [team["team_id"] for team in teams] == [
        "TM-W810-01",
        "TM-W810-02",
        "TM-W810-03",
        "TM-W810-04",
        "TM-W810-05",
    ]
    assert [team["operation_mode"] for team in teams] == [
        "MANUAL_TIMELINE",
        "SEMI_AUTO",
        "AUTO",
        "AUTO",
        "AUTO",
    ]
    assert all(team["clear_status"] == "VERIFIED" for team in teams)
    assert all(team["tw_availability_check"] == "PASS" for team in teams)
    assert len(
        {
            tuple(sorted(team[f"slot{slot}"] for slot in range(1, 6)))
            for team in teams
        }
    ) == 5

    for team in teams:
        requirements = fixture_module._validate_requirements(team)
        assert requirements["support"]["unit"] == "UNKNOWN"
        assert fixture_module._borrowed_states(team, requirements) == (None,) * 5
        assert all(
            value == "UNKNOWN"
            for slot in requirements["slots"].values()
            for value in slot.values()
        )

    water_axes = [
        row for row in closure.timelines if row["team_id"].startswith("TM-W810-")
    ]
    assert len(water_axes) == 5
    assert all(axis["status"] == "STRUCTURED" for axis in water_axes)
    assert all(axis["source_id"] == "yt_w3My0QHcoTA" for axis in water_axes)
    assert all(axis["reproducibility"] == "TW_REPRODUCED" for axis in water_axes)
    step_counts = {
        axis["team_id"]: sum(
            step["timeline_id"] == axis["timeline_id"]
            for step in closure.timeline_steps
        )
        for axis in water_axes
    }
    assert step_counts == {
        "TM-W810-01": 9,
        "TM-W810-02": 6,
        "TM-W810-03": 1,
        "TM-W810-04": 1,
        "TM-W810-05": 1,
    }
    selected_evidence_ids = {row["evidence_id"] for row in closure.evidence}
    assert {"ev084", "ev085", "ev086", "ev087", "ev088"} <= selected_evidence_ids
    assert {"ev089", "ev090"}.isdisjoint(selected_evidence_ids)
    assert all(row["status"] == "ACTIVE" for row in closure.evidence)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "counter_team_ids",
            "kaya_orig;kaya_orig;rem_orig;yuki_orig;saren_sum",
            "five distinct",
        ),
        ("empirical_win_rate", "100", "SINGLE_REPORT"),
        ("evidence_ids", "ev001", "Arena Evidence/Claim closure"),
        ("operation_mode", "AUTO", "operation_mode"),
    ],
)
def test_arena_source_truth_mutations_fail_closed(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)

    def mutate(rows):
        rows[0][field] = value

    rewrite_csv(core / "39_ARENA_COUNTER_REGISTRY.csv", mutate)

    with pytest.raises(FixtureValidationError, match=message):
        load_pve_closure(core)


def test_single_report_metadata_cannot_self_upgrade_to_verified(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)

    def self_upgrade(rows):
        for row in rows:
            row["status"] = "VERIFIED"
            row["reproducibility"] = "CONFIRMED"

    rewrite_csv(core / "39_ARENA_COUNTER_REGISTRY.csv", self_upgrade)

    with pytest.raises(
        FixtureValidationError,
        match="VERIFIED requires independent multi-source wins",
    ):
        load_pve_closure(core)


def _independent_multi_source_arena_core(tmp_path: Path) -> Path:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    result_claim_id = "CLM-ARENA-TW-COUNTER-20260525-01"
    second_evidence_id = "ev115"

    def mature_counter(rows):
        row = rows[0]
        row.update(
            {
                "status": "VERIFIED",
                "source_tier": "MULTI_PLAYER_REPORT",
                "claim_confidence": "C",
                "evidence_ids": f"ev114;{second_evidence_id}",
                "claim_ids": result_claim_id,
                "sample_size": "2",
                "wins": "2",
                "losses": "0",
                "source_record_count": "2",
                "source_platforms": "Bahamut;IndependentTest",
                "environment_match": "EXACT",
                "reproducibility": "CONFIRMED",
            }
        )
        rows[1]["claim_ids"] = result_claim_id
        rows[1]["evidence_ids"] = second_evidence_id

    def mature_claim(rows):
        claim = next(row for row in rows if row["claim_id"] == result_claim_id)
        claim.update(
            {
                "claim_confidence": "C",
                "evidence_ids": f"ev114;{second_evidence_id}",
                "independence_check": "YES",
                "version_match": "YES",
            }
        )
        next(
            row
            for row in rows
            if row["claim_id"] == "CLM-ARENA-TW-COUNTER-20260525-02"
        )["evidence_ids"] = ""

    def reuse_independent_evidence(rows):
        evidence = next(row for row in rows if row["evidence_id"] == second_evidence_id)
        evidence.update(
            {
                "claim_id": result_claim_id,
                "source_title": "TEST_ONLY independent Arena result",
                "source_url": "https://gamewith.jp/pricone-re/article/show/999999",
                "source_locator": "TEST_ONLY result record 2",
            }
        )

    rewrite_csv(core / "39_ARENA_COUNTER_REGISTRY.csv", mature_counter)
    rewrite_csv(core / "93_CLAIM_REGISTER.csv", mature_claim)
    rewrite_csv(core / "92_EVIDENCE_LEDGER.csv", reuse_independent_evidence)
    return core


def test_independent_multi_source_arena_result_is_importable(tmp_path: Path) -> None:
    core = _independent_multi_source_arena_core(tmp_path)
    closure = load_pve_closure(core)
    row = next(
        item for item in closure.arena_rows if item["counter_id"] == "TW_ARENA_20260525_01"
    )
    assert row["status"] == "VERIFIED"
    assert closure.arena_evidence_ids_by_counter[row["counter_id"]] == (
        "ev114",
        "ev115",
    )
    assert closure.arena_claim_ids_by_counter[row["counter_id"]] == (
        "CLM-ARENA-TW-COUNTER-20260525-01",
    )


def test_verified_arena_survives_importer_to_api_serving_closure(
    tmp_path: Path,
) -> None:
    core = _independent_multi_source_arena_core(tmp_path)
    manifest = tmp_path / "verified-arena.sha256"
    manifest_sha256 = write_tree_manifest(core, manifest)
    engine = sqlite_engine()

    with Session(engine) as session:
        import_pve_projection(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        session.commit()

        counters = arena_counter_results(session)
        verified = next(row for row in counters if row["status"] == "VERIFIED")
        assert verified["counter_id"] == "TW_ARENA_20260525_01"
        assert set(verified["evidence_ids"]) == {
            "ev114",
            "ev115",
        }
        assert verified["claim_ids"] == ["CLM-ARENA-TW-COUNTER-20260525-01"]
        assert {
            session.get(Evidence, evidence_id).module
            for evidence_id in verified["evidence_ids"]
        } == {"arena"}
        assert session.get(Claim, verified["claim_ids"][0]).module == "arena"


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("source_tier", "FAKE_STRONG", "source_tier is invalid"),
        (
            "source_tier",
            "SINGLE_PLAYER_REPORT",
            "VERIFIED requires independent multi-source wins",
        ),
        (
            "environment_match",
            "MISMATCH",
            "VERIFIED requires independent multi-source wins",
        ),
    ],
)
def test_verified_arena_rejects_weak_tier_or_environment_mismatch(
    tmp_path: Path,
    field: str,
    value: str,
    expected_message: str,
) -> None:
    core = _independent_multi_source_arena_core(tmp_path)

    def mutate(rows):
        rows[0][field] = value

    rewrite_csv(core / "39_ARENA_COUNTER_REGISTRY.csv", mutate)
    with pytest.raises(
        FixtureValidationError,
        match=expected_message,
    ):
        load_pve_closure(core)


def test_verified_arena_rejects_invented_evidence_tier(tmp_path: Path) -> None:
    core = _independent_multi_source_arena_core(tmp_path)

    def mutate(rows):
        next(
            row for row in rows if row["evidence_id"] == "ev115"
        )["source_tier"] = "FAKE_STRONG"

    rewrite_csv(core / "92_EVIDENCE_LEDGER.csv", mutate)
    with pytest.raises(
        FixtureValidationError,
        match="VERIFIED requires one independent B/C result Claim",
    ):
        load_pve_closure(core)


def test_verified_arena_same_hostname_different_ports_is_not_independent(
    tmp_path: Path,
) -> None:
    core = _independent_multi_source_arena_core(tmp_path)

    def mutate(rows):
        next(row for row in rows if row["evidence_id"] == "ev114")[
            "source_url"
        ] = "https://forum.gamer.com.tw:443/result-a"
        next(
            row for row in rows if row["evidence_id"] == "ev115"
        )["source_url"] = "https://forum.gamer.com.tw:444/result-b"

    rewrite_csv(core / "92_EVIDENCE_LEDGER.csv", mutate)
    with pytest.raises(
        FixtureValidationError,
        match="VERIFIED requires one independent B/C result Claim",
    ):
        load_pve_closure(core)


def test_duplicate_exact_arena_pair_is_rejected(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)

    def mutate(rows):
        duplicate = dict(rows[0])
        duplicate["counter_id"] = "TW_ARENA_DUPLICATE_PAIR"
        rows.append(duplicate)

    rewrite_csv(core / "39_ARENA_COUNTER_REGISTRY.csv", mutate)

    with pytest.raises(FixtureValidationError, match="duplicate exact Arena pair"):
        load_pve_closure(core)


def test_arena_defense_id_uses_full_sha256() -> None:
    closure = load_pve_closure(RESEARCH_CORE)
    specs = fixture_module._arena_defense_specs(closure.arena_rows)

    assert len(specs) == 1
    defense_id = specs[0]["defense_id"]
    assert defense_id.startswith("AD-")
    assert len(defense_id) == 67
    assert set(defense_id[3:]) <= set("0123456789abcdef")


def test_arena_fail_check_cannot_hide_all_available_members(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)

    rewrite_csv(
        core / "39_ARENA_COUNTER_REGISTRY.csv",
        lambda rows: rows[0].update({"tw_availability_check": "FAIL"}),
    )

    with pytest.raises(FixtureValidationError, match="availability closure must be PASS"):
        load_pve_closure(core)


def test_arena_unverified_member_is_not_invented_as_unavailable(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)

    def mark_character_unverified(rows):
        next(row for row in rows if row["unit_key"] == "kaya_orig")[
            "availability_status"
        ] = "UNVERIFIED"

    def mark_counters_unverified(rows):
        for row in rows:
            row["tw_availability_check"] = "UNVERIFIED"
            row["unavailable_unit_ids"] = "kaya_orig"

    rewrite_csv(core / "18_TW_CHARACTER_AVAILABILITY.csv", mark_character_unverified)
    rewrite_csv(core / "39_ARENA_COUNTER_REGISTRY.csv", mark_counters_unverified)

    with pytest.raises(FixtureValidationError, match="unavailable_unit_ids"):
        load_pve_closure(core)


def test_arena_pass_member_requires_tw_official_name_and_evidence(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)

    def remove_official_name(rows):
        next(row for row in rows if row["unit_key"] == "yuki_orig")["tw_name"] = (
            "【待查證】"
        )

    rewrite_csv(core / "18_TW_CHARACTER_AVAILABILITY.csv", remove_official_name)

    with pytest.raises(FixtureValidationError, match="TW official display name"):
        load_pve_closure(core)


def test_borrowed_member_projection_is_tri_state() -> None:
    closure = load_pve_closure(RESEARCH_CORE)
    teams = {row["team_id"]: row for row in closure.teams}

    explicit = teams["TM-F810-03"]
    assert fixture_module._borrowed_states(
        explicit, fixture_module._validate_requirements(explicit)
    ) == (False, False, True, False, False)

    unknown = teams["TM-W810-01"]
    assert fixture_module._borrowed_states(
        unknown, fixture_module._validate_requirements(unknown)
    ) == (None, None, None, None, None)

    conflict = teams["TM-F810-01"]
    assert fixture_module._borrowed_states(
        conflict, fixture_module._validate_requirements(conflict)
    ) == (None, None, None, None, None)

    assert fixture_module._borrowed_state_semantics_from_manifest({}) == (
        fixture_module.BORROWED_STATE_LEGACY_FALSE_V1
    )
    with pytest.raises(MirrorDriftError, match="unsupported borrowed-state semantics"):
        fixture_module._borrowed_state_semantics_from_manifest(
            {fixture_module.BORROWED_STATE_SEMANTICS_FIELD: "invented_v9"}
        )
    for invalid_semantics in (None, 1, {}, []):
        with pytest.raises(MirrorDriftError, match="unsupported borrowed-state semantics"):
            fixture_module._borrowed_state_semantics_from_manifest(
                {fixture_module.BORROWED_STATE_SEMANTICS_FIELD: invalid_semantics}
            )


def test_zero_team_guide_and_compatibility_loader_are_preserved() -> None:
    closure = load_pve_closure(RESEARCH_CORE)
    compatibility = load_fire_8_10_closure(RESEARCH_CORE)
    zero_team_guide = next(
        guide
        for guide in closure.guides
        if guide["guide_id"] == "TW_DEEP_FIRE_10_10_20260802"
    )

    assert compatibility.fingerprint == closure.fingerprint
    assert zero_team_guide["team_count"] == "0"
    assert not any(
        team["guide_id"] == zero_team_guide["guide_id"] for team in closure.teams
    )
    assert closure.stage_evidence_ids_by_guide[zero_team_guide["guide_id"]]
    assert closure.stage_claim_ids_by_guide[zero_team_guide["guide_id"]]


def test_closure_captures_each_source_file_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    source_paths = {
        (core / relative).resolve(): relative for relative in fixture_module.SOURCE_FILES
    }
    read_counts = {relative: 0 for relative in fixture_module.SOURCE_FILES}
    original_read_bytes = Path.read_bytes

    def counted_read_bytes(path: Path) -> bytes:
        relative = source_paths.get(path.resolve())
        if relative is not None:
            read_counts[relative] += 1
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", counted_read_bytes)
    closure = load_pve_closure(core)

    assert set(closure.file_hashes) == set(fixture_module.SOURCE_FILES)
    assert set(read_counts.values()) == {1}


def test_import_is_atomic_idempotent_and_preserves_fk_closure(tmp_path: Path) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="atomic",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        first = import_pve_projection(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        second = import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )

        assert first.created is True
        assert first.activated is True
        assert second.created is False
        assert second.activated is False
        assert first.import_run_id == second.import_run_id
        assert first.fixture_sha256 == second.fixture_sha256
        assert first.revision_id == first.raw_tree_sha256
        assert first.file_count == 48
        assert first.csv_file_count == 13
        assert first.csv_row_count == 356
        assert first.row_counts == {
            "stages": 3,
            "teams": 10,
            "team_members": 50,
            "characters": 35,
            "evidence": 64,
            "claims": 62,
            "operation_timelines": 15,
            "timeline_steps": 37,
            "arena_defenses": 1,
            "arena_defense_members": 5,
            "arena_counters": 2,
            "arena_counter_members": 10,
            "arena_counter_evidence": 4,
            "arena_counter_claims": 4,
        }
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 1
        assert session.scalar(select(func.count()).select_from(Stage)) == 3
        assert session.scalar(select(func.count()).select_from(Team)) == 10
        assert session.scalar(select(func.count()).select_from(TeamMember)) == 50
        assert session.scalar(select(func.count()).select_from(Character)) == 35
        assert session.scalar(select(func.count()).select_from(OperationTimeline)) == 15
        assert session.scalar(select(func.count()).select_from(TimelineStep)) == 37
        assert session.scalar(select(func.count()).select_from(ArenaDefense)) == 1
        assert session.scalar(select(func.count()).select_from(ArenaDefenseMember)) == 5
        assert session.scalar(select(func.count()).select_from(ArenaCounter)) == 2
        assert session.scalar(select(func.count()).select_from(ArenaCounterMember)) == 10
        assert session.scalar(select(func.count()).select_from(ArenaCounterEvidence)) == 4
        assert session.scalar(select(func.count()).select_from(ArenaCounterClaim)) == 4
        stage = session.get(Stage, TARGET_GUIDE_ID)
        assert stage is not None
        assert stage.team_count == 5
        zero_team_stage = session.get(Stage, "TW_DEEP_FIRE_10_10_20260802")
        assert zero_team_stage is not None
        assert zero_team_stage.team_count == 0
        state = session.get(MaterializationState, 1)
        revision = session.get(CoreRevision, first.revision_id)
        assert state is not None
        assert revision is not None
        assert revision.status == "SUCCEEDED"
        assert revision.import_run_id == first.import_run_id
        assert state.active_revision_id == first.revision_id
        assert state.active_import_run_id == first.import_run_id
        assert state.materialization_sha256 == revision.materialization_sha256
        assert session.scalar(select(func.count()).select_from(RevisionActivation)) == 1
        for table_name in (
            "arena_defenses",
            "arena_defense_members",
            "arena_counters",
            "arena_counter_members",
            "arena_counter_evidence",
            "arena_counter_claims",
        ):
            assert state.serving_counts[table_name] == first.row_counts[table_name]
        run = session.get(ImportRun, first.import_run_id)
        assert run is not None
        assert run.manifest["materialization"]["schema_version"] == 3

        arena_counter = session.get(ArenaCounter, "TW_ARENA_20260525_01")
        assert arena_counter is not None
        assert arena_counter.status == "SINGLE_REPORT"
        assert arena_counter.claim_confidence == "D"
        assert arena_counter.sample_size == 1
        assert arena_counter.wins == 1
        assert arena_counter.losses == 0
        assert arena_counter.empirical_win_rate is None
        assert arena_counter.randomness == "UNKNOWN（原樓主稱網站測試有贏也有輸）"
        assert arena_counter.reproducibility == "UNVERIFIED_REPEATABILITY"
        assert arena_counter.source_platforms == ["Bahamut"]
        assert arena_counter.source_payload["counter_id"] == arena_counter.counter_id

        imported_claim_ids = set(session.scalars(select(Claim.claim_id)).all())
        for evidence in session.scalars(select(Evidence)).all():
            if evidence.linked_claim_id is not None:
                assert evidence.linked_claim_id in imported_claim_ids
            assert evidence.linked_claim_id == evidence.declared_claim_id

        team = session.get(Team, "TM-F810-01")
        assert team is not None
        assert team.requirements_raw == fixture_module.json.dumps(
            team.requirements, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

        timeline = session.get(OperationTimeline, "AX-F810-02-EV073")
        assert timeline is not None
        assert timeline.timeline_id == "TL-F810-02-EV073"
        assert timeline.battle_duration_ms is None
        assert timeline.reproducibility == "UNVERIFIED_ON_TW"
        steps = session.scalars(
            select(TimelineStep)
            .where(TimelineStep.timeline_id == timeline.timeline_id)
            .order_by(TimelineStep.sequence_no)
        ).all()
        assert [step.sequence_no for step in steps] == list(range(1, 15))
        assert all(step.time_state == "NOT_STATED" for step in steps[:4])
        assert all(step.clock_from_ms is None and step.clock_to_ms is None for step in steps[:4])
        assert all(step.time_state == "STATED" for step in steps[4:])
        assert all(step.criticality == "UNKNOWN" for step in steps)


def test_synthetic_multi_stage_projection_retains_provisional_team_without_counting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core, manifest, manifest_sha256 = build_synthetic_multi_stage_core(tmp_path)
    allow_synthetic_snapshot_row_count(monkeypatch, core)
    closure = load_pve_closure(core)
    synthetic_guide = next(
        guide for guide in closure.guides if guide["guide_id"] == SYNTHETIC_GUIDE_ID
    )
    synthetic_team = next(
        team for team in closure.teams if team["team_id"] == SYNTHETIC_TEAM_ID
    )

    assert len(closure.guides) == 4
    assert len(closure.teams) == 11
    assert len(closure.timelines) == 16
    assert synthetic_guide["team_count"] == "0"
    assert synthetic_team["clear_status"] == "PROVISIONAL"
    assert synthetic_team["tw_availability_check"] == "PASS"

    engine = sqlite_engine()
    with Session(engine) as session:
        result = import_pve_projection(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )

        assert result.row_counts == {
            "stages": 4,
            "teams": 11,
            "team_members": 55,
            "characters": 35,
            "evidence": 64,
            "claims": 62,
            "operation_timelines": 16,
            "timeline_steps": 37,
            "arena_defenses": 1,
            "arena_defense_members": 5,
            "arena_counters": 2,
            "arena_counter_members": 10,
            "arena_counter_evidence": 4,
            "arena_counter_claims": 4,
        }
        stored_stage = session.get(Stage, SYNTHETIC_GUIDE_ID)
        stored_team = session.get(Team, SYNTHETIC_TEAM_ID)
        stored_axis = session.get(OperationTimeline, SYNTHETIC_AXIS_ID)
        assert stored_stage is not None
        assert stored_stage.team_count == 0
        assert stored_team is not None
        assert stored_team.clear_status == "PROVISIONAL"
        assert stored_axis is not None
        assert stored_axis.team_id == SYNTHETIC_TEAM_ID


def test_team_count_mismatch_is_rejected_before_any_write(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "24_PVE_GUIDE_REGISTRY.csv"

    def mutate(rows):
        for row in rows:
            if row["guide_id"] == TARGET_GUIDE_ID:
                row["team_count"] = "2"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="team_count differs"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(Stage)) == 0


def test_rejected_non_timeline_team_evidence_is_not_counted_as_effective(
    tmp_path: Path,
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "92_EVIDENCE_LEDGER.csv"

    def mutate(rows):
        evidence = next(row for row in rows if row["evidence_id"] == "ev074")
        evidence["status"] = "REJECTED"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="team_count differs"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(Stage)) == 0


def test_unknown_unit_is_rejected_before_any_write(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "25_PVE_TEAM_REGISTRY.csv"

    def mutate(rows):
        rows[0]["slot1"] = "missing_unit_key"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="missing ids"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_team_must_match_its_guides_server_and_stage_before_any_write(
    tmp_path: Path,
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "25_PVE_TEAM_REGISTRY.csv"

    def mutate(rows):
        team = next(row for row in rows if row["team_id"] == "TM-F810-01")
        team["stage"] = "紅焰10-10"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="server/stage differs"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(Stage)) == 0


def test_timeline_ref_must_equal_the_team_source_axis_closure(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "25_PVE_TEAM_REGISTRY.csv"

    def mutate(rows):
        team = next(row for row in rows if row["team_id"] == "TM-F810-02")
        requirements = fixture_module.json.loads(team["requirements"])
        requirements["timeline_ref"] = "AX-F810-02-EV070"
        team["requirements"] = fixture_module.json.dumps(
            requirements, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="timeline_ref differs"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_timeline_locator_must_remain_inside_its_evidence_locator(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "26_PVE_OPERATION_TIMELINES.csv"

    def mutate(rows):
        rows[0]["source_locator"] = "unrelated_source#invented"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="Evidence locator"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_unstated_source_time_cannot_be_invented(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "27_PVE_TIMELINE_STEPS.csv"

    def mutate(rows):
        step = next(row for row in rows if row["timeline_step_id"] == "TLS-F810-02-001")
        step["time_state"] = "STATED"
        step["clock_from_ms"] = "90000"
        step["clock_to_ms"] = "90000"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="strengthens an unstated source time"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_timeline_actor_must_be_a_member_of_its_team(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "27_PVE_TIMELINE_STEPS.csv"

    def mutate(rows):
        rows[4]["actor_unit_key"] = "maho_summer"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="not a member of its team"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_water_exact_timeline_boundary_rejects_locator_alias_before_database_write(
    tmp_path: Path,
) -> None:
    core, manifest, _ = build_manifested_core(tmp_path, name="water-boundary-drift")
    path = core / "27_PVE_TIMELINE_STEPS.csv"

    def mutate(rows):
        target = next(
            row for row in rows if row["timeline_step_id"] == "TLS-W810-01-006"
        )
        target["source_locator"] = "yt_w3My0QHcoTA@00:13-02:13#step-5"

    rewrite_csv(path, mutate)
    manifest_sha256 = write_tree_manifest(core, manifest)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(
            FixtureValidationError,
            match="AX-W810-01-EV084 steps violate the audited source boundary",
        ):
            import_pve_projection(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


@pytest.mark.parametrize(
    "unsafe_url",
    ["javascript:alert(1)", "https://pcrdfans.com/jp/battle"],
)
def test_unaudited_or_restricted_evidence_url_is_rejected(
    tmp_path: Path, unsafe_url: str
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "92_EVIDENCE_LEDGER.csv"

    def mutate(rows):
        for row in rows:
            if row["evidence_id"] == "ev050":
                row["source_url"] = unsafe_url

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="audited HTTPS source"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0


def test_database_failure_rolls_back_whole_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="database-failure",
    )
    engine = sqlite_engine()
    original_upsert = fixture_module._upsert
    calls = 0

    def fail_after_first_row(session, model, key, values):
        nonlocal calls
        calls += 1
        original_upsert(session, model, key, values)
        if calls == 2:
            raise RuntimeError("injected failure")

    monkeypatch.setattr(fixture_module, "_upsert", fail_after_first_row)
    with Session(engine) as session:
        with pytest.raises(RuntimeError, match="injected failure"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(Claim)) == 0


def test_timeline_step_failure_rolls_back_the_whole_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="timeline-step-failure",
    )
    engine = sqlite_engine()
    original_upsert = fixture_module._upsert

    def fail_on_timeline_step(session, model, key, values):
        original_upsert(session, model, key, values)
        if model is TimelineStep:
            raise RuntimeError("injected timeline step failure")

    monkeypatch.setattr(fixture_module, "_upsert", fail_on_timeline_step)
    with Session(engine) as session:
        with pytest.raises(RuntimeError, match="timeline step failure"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )
        for model in (ImportRun, Stage, Team, OperationTimeline, TimelineStep):
            assert session.scalar(select(func.count()).select_from(model)) == 0


def test_idempotent_replay_detects_stage_materialized_row_drift(
    tmp_path: Path,
) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="stage-drift",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        stage = session.get(Stage, "TW_DEEP_FIRE_10_10_20260802")
        assert stage is not None
        stage.source_payload = {**stage.source_payload, "notes": "tampered"}
        session.commit()

        with pytest.raises(
            MirrorDriftError,
            match="stage TW_DEEP_FIRE_10_10_20260802 drifted",
        ):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )


def test_idempotent_replay_detects_materialized_row_drift(tmp_path: Path) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="team-drift",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        team = session.get(Team, "TM-F810-01")
        assert team is not None
        team.source_payload = {**team.source_payload, "notes": "tampered"}
        session.commit()

        with pytest.raises(MirrorDriftError, match="TM-F810-01 drifted"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )


def test_idempotent_replay_detects_arena_source_truth_drift(tmp_path: Path) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="arena-drift",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        import_pve_projection(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        counter = session.get(ArenaCounter, "TW_ARENA_20260525_01")
        assert counter is not None
        counter.randomness = "tampered"
        session.commit()

        with pytest.raises(
            MirrorDriftError,
            match="Arena counter TW_ARENA_20260525_01 drifted",
        ):
            import_pve_projection(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ("defense", "Arena defense .* drifted"),
        ("defense_member", "Arena defense members drifted"),
        ("counter_member", "Arena counter members drifted"),
        ("counter_evidence", "Arena counter Evidence links drifted"),
        ("counter_claim", "Arena counter Claim links drifted"),
    ],
)
def test_idempotent_replay_detects_each_arena_table_tamper(
    tmp_path: Path,
    target: str,
    message: str,
) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name=f"arena-{target}-drift",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        import_pve_projection(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        counter_id = "TW_ARENA_20260525_01"
        defense_id = session.scalar(select(ArenaDefense.defense_id))
        assert defense_id is not None
        if target == "defense":
            stored = session.get(ArenaDefense, defense_id)
            assert stored is not None
            stored.notes = "tampered"
        elif target == "defense_member":
            stored = session.get(ArenaDefenseMember, (defense_id, 1))
            assert stored is not None
            session.delete(stored)
        elif target == "counter_member":
            stored = session.get(ArenaCounterMember, (counter_id, 1))
            assert stored is not None
            session.delete(stored)
        elif target == "counter_evidence":
            stored = session.get(ArenaCounterEvidence, (counter_id, "ev113"))
            assert stored is not None
            session.delete(stored)
        else:
            stored = session.get(
                ArenaCounterClaim,
                (counter_id, "CLM-ARENA-TW-DEF-20260525"),
            )
            assert stored is not None
            session.delete(stored)
        session.commit()

        with pytest.raises(MirrorDriftError, match=message):
            import_pve_projection(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )


def test_idempotent_replay_detects_timeline_materialization_drift(
    tmp_path: Path,
) -> None:
    core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="timeline-drift",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        import_fire_8_10(
            session,
            core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )
        timeline = session.get(OperationTimeline, "AX-F810-02-EV073")
        assert timeline is not None
        timeline.reproducibility = "TW_REPRODUCED"
        session.commit()

        with pytest.raises(MirrorDriftError, match="timeline AX-F810-02-EV073 drifted"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )


def test_dangling_evidence_claim_rejects_entire_serving_import(tmp_path: Path) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "92_EVIDENCE_LEDGER.csv"

    def mutate(rows):
        for row in rows:
            if row["evidence_id"] == "ev050":
                row["claim_id"] = "CLM-DOES-NOT-EXIST"

    rewrite_csv(path, mutate)
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(FixtureValidationError, match="selected evidence references missing claims"):
            import_fire_8_10(session, core)
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.get(Claim, "CLM-DOES-NOT-EXIST") is None
        assert session.get(Evidence, "ev050") is None


def test_unreviewed_changed_tree_is_rejected_before_database_write(tmp_path: Path) -> None:
    reviewed_core, manifest, manifest_sha256 = build_manifested_core(
        tmp_path,
        name="reviewed-base",
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        original = import_fire_8_10(
            session,
            reviewed_core,
            manifest_path=manifest,
            expected_manifest_sha256=manifest_sha256,
        )

        core = tmp_path / "pcr_tw_project"
        shutil.copytree(reviewed_core, core)
        path = core / "24_PVE_GUIDE_REGISTRY.csv"

        def mutate(rows):
            for row in rows:
                if row["guide_id"] == TARGET_GUIDE_ID:
                    row["notes"] = f"{row['notes']} test-only-source-revision"

        rewrite_csv(path, mutate)
        with pytest.raises(SnapshotValidationError, match="file SHA-256 mismatch"):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )

        assert session.scalar(select(func.count()).select_from(ImportRun)) == 1
        stage = session.get(Stage, TARGET_GUIDE_ID)
        assert stage is not None
        assert stage.import_run_id == original.import_run_id
        assert "test-only-source-revision" not in stage.notes


def test_source_change_between_closure_and_snapshot_is_rejected_before_database_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = tmp_path / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, core)
    path = core / "24_PVE_GUIDE_REGISTRY.csv"
    canonical_content = path.read_bytes()
    manifest = tmp_path / "toctou.sha256"
    manifest_sha256 = write_tree_manifest(core, manifest)

    def mutate(rows):
        for row in rows:
            if row["guide_id"] == TARGET_GUIDE_ID:
                row["notes"] = f"{row['notes']} transient-unreviewed-source"

    rewrite_csv(path, mutate)
    original_loader = fixture_module.load_research_core_snapshot

    def restore_canonical_then_load(*args, **kwargs):
        path.write_bytes(canonical_content)
        return original_loader(*args, **kwargs)

    monkeypatch.setattr(
        fixture_module,
        "load_research_core_snapshot",
        restore_canonical_then_load,
    )
    engine = sqlite_engine()
    with Session(engine) as session:
        with pytest.raises(
            FixtureValidationError,
            match="source files changed during import snapshot capture",
        ):
            import_fire_8_10(
                session,
                core,
                manifest_path=manifest,
                expected_manifest_sha256=manifest_sha256,
            )

        assert session.scalar(select(func.count()).select_from(ImportRun)) == 0
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 0
        assert session.scalar(select(func.count()).select_from(Stage)) == 0
        assert session.scalar(select(func.count()).select_from(MaterializationState)) == 0


def test_new_revision_activation_and_rollback_preserve_immutable_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = sqlite_engine()
    first_core = tmp_path / "first" / "pcr_tw_project"
    shutil.copytree(RESEARCH_CORE, first_core)
    first_manifest = tmp_path / "first.sha256"
    first_manifest_sha256 = write_tree_manifest(first_core, first_manifest)
    second_core, second_manifest, second_manifest_sha256 = (
        build_synthetic_multi_stage_core(tmp_path, name="second")
    )
    allow_synthetic_snapshot_row_count(monkeypatch, second_core)

    with Session(engine) as session:
        first = import_fire_8_10(
            session,
            first_core,
            manifest_path=first_manifest,
            expected_manifest_sha256=first_manifest_sha256,
        )
        second = import_fire_8_10(
            session,
            second_core,
            manifest_path=second_manifest,
            expected_manifest_sha256=second_manifest_sha256,
        )
        assert second.created is True
        assert second.activated is True
        assert second.revision_id != first.revision_id
        state = session.get(MaterializationState, 1)
        assert state is not None
        assert state.active_revision_id == second.revision_id
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 2
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 2
        assert session.get(Stage, SYNTHETIC_GUIDE_ID) is not None
        assert session.get(Team, SYNTHETIC_TEAM_ID) is not None
        assert session.get(OperationTimeline, SYNTHETIC_AXIS_ID) is not None
        session.rollback()  # end the read-only transaction opened by assertions

        rollback = import_fire_8_10(
            session,
            first_core,
            manifest_path=first_manifest,
            expected_manifest_sha256=first_manifest_sha256,
        )
        assert rollback.created is False
        assert rollback.activated is True
        assert rollback.revision_id == first.revision_id
        session.refresh(state)
        assert state.active_revision_id == first.revision_id
        assert session.get(Stage, SYNTHETIC_GUIDE_ID) is None
        assert session.get(Team, SYNTHETIC_TEAM_ID) is None
        assert session.get(OperationTimeline, SYNTHETIC_AXIS_ID) is None
        assert session.scalar(select(func.count()).select_from(Stage)) == 3
        assert session.scalar(select(func.count()).select_from(Team)) == 10
        assert session.scalar(select(func.count()).select_from(OperationTimeline)) == 15
        session.rollback()  # end the read-only transaction opened by assertions

        reactivate = import_fire_8_10(
            session,
            second_core,
            manifest_path=second_manifest,
            expected_manifest_sha256=second_manifest_sha256,
        )
        assert reactivate.created is False
        assert reactivate.activated is True
        assert reactivate.revision_id == second.revision_id
        session.refresh(state)
        assert state.active_revision_id == second.revision_id
        assert session.get(Stage, SYNTHETIC_GUIDE_ID) is not None
        assert session.get(Team, SYNTHETIC_TEAM_ID) is not None
        assert session.get(OperationTimeline, SYNTHETIC_AXIS_ID) is not None
        assert session.scalar(select(func.count()).select_from(Stage)) == 4
        assert session.scalar(select(func.count()).select_from(Team)) == 11
        assert session.scalar(select(func.count()).select_from(OperationTimeline)) == 16
        activations = session.scalars(
            select(RevisionActivation).order_by(RevisionActivation.sequence_no)
        ).all()
        assert [activation.kind for activation in activations] == [
            "IMPORT",
            "IMPORT",
            "ROLLBACK",
            "REACTIVATE",
        ]
        assert [activation.sequence_no for activation in activations] == [1, 2, 3, 4]
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 2
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 2
        assert {revision.status for revision in session.scalars(select(CoreRevision))} == {
            "SUCCEEDED"
        }


def test_a3_checkpoint_rolls_back_from_a4_and_reactivates_water_projection(
    tmp_path: Path,
) -> None:
    a3_core = export_checkpoint_core(tmp_path, "rp-a3-1")
    a4_core = export_checkpoint_core(tmp_path, "rp-a4-1")
    assert snapshot_contract_for_manifest(RP_A3_MANIFEST_SHA256) == (
        RP_A3_SNAPSHOT_CONTRACT
    )
    assert snapshot_contract_for_manifest(RP_A4_MANIFEST_SHA256) == (
        RP_A4_SNAPSHOT_CONTRACT
    )

    engine = sqlite_engine()
    with Session(engine) as session:
        a3 = import_pve_projection(
            session,
            a3_core,
            manifest_path=A3_MANIFEST,
            expected_manifest_sha256=RP_A3_MANIFEST_SHA256,
            application_version="3.0.0-a3",
        )
        assert a3.row_counts == {
            "stages": 2,
            "teams": 5,
            "team_members": 25,
            "characters": 17,
            "evidence": 34,
            "claims": 27,
            "operation_timelines": 10,
            "timeline_steps": 19,
        }
        assert session.get(Stage, "TW_DEEP_WATER_08_10_20260808") is None
        assert session.get(Team, "TM-W810-01") is None
        a3_run = session.get(ImportRun, a3.import_run_id)
        assert a3_run is not None
        assert a3_run.manifest[fixture_module.BORROWED_STATE_SEMANTICS_FIELD] == (
            fixture_module.BORROWED_STATE_LEGACY_FALSE_V1
        )
        assert all(
            member.is_borrowed is False
            for member in session.scalars(
                select(TeamMember).where(TeamMember.team_id == "TM-F810-01")
            )
        )

        # Simulate the immutable manifest shape created by the deployed A3
        # importer, before borrowed-state semantics became an explicit field.
        historical_a3_manifest = dict(a3_run.manifest)
        historical_a3_manifest.pop(fixture_module.BORROWED_STATE_SEMANTICS_FIELD)
        session.execute(
            update(ImportRun)
            .where(ImportRun.id == a3.import_run_id)
            .values(manifest=historical_a3_manifest)
            .execution_options(synchronize_session=False)
        )
        session.commit()
        session.expire_all()

        historical_replay = import_pve_projection(
            session,
            a3_core,
            manifest_path=A3_MANIFEST,
            expected_manifest_sha256=RP_A3_MANIFEST_SHA256,
        )
        assert historical_replay.created is False
        assert historical_replay.activated is False
        assert all(
            member.is_borrowed is False
            for member in session.scalars(
                select(TeamMember).where(TeamMember.team_id == "TM-F810-01")
            )
        )
        session.rollback()

        a4 = import_pve_projection(
            session,
            a4_core,
            manifest_path=A4_MANIFEST,
            expected_manifest_sha256=RP_A4_MANIFEST_SHA256,
        )
        assert a4.row_counts == {
            "stages": 3,
            "teams": 10,
            "team_members": 50,
            "characters": 25,
            "evidence": 55,
            "claims": 53,
            "operation_timelines": 15,
            "timeline_steps": 37,
        }
        assert session.get(Stage, "TW_DEEP_WATER_08_10_20260808") is not None
        assert session.get(Team, "TM-W810-05") is not None
        assert session.get(Character, "labyrista_alpha") is not None
        a4_run = session.get(ImportRun, a4.import_run_id)
        assert a4_run is not None
        assert a4_run.manifest[fixture_module.BORROWED_STATE_SEMANTICS_FIELD] == (
            fixture_module.BORROWED_STATE_TRISTATE_V1
        )
        assert all(
            member.is_borrowed is None
            for member in session.scalars(
                select(TeamMember).where(TeamMember.team_id == "TM-W810-01")
            )
        )
        session.rollback()

        rollback = import_pve_projection(
            session,
            a3_core,
            manifest_path=A3_MANIFEST,
            expected_manifest_sha256=RP_A3_MANIFEST_SHA256,
        )
        assert rollback.created is False
        assert rollback.activated is True
        assert session.scalar(select(func.count()).select_from(Stage)) == 2
        assert session.scalar(select(func.count()).select_from(Team)) == 5
        assert session.scalar(select(func.count()).select_from(Character)) == 17
        assert session.scalar(select(func.count()).select_from(Evidence)) == 34
        assert session.scalar(select(func.count()).select_from(OperationTimeline)) == 10
        assert session.scalar(select(func.count()).select_from(TimelineStep)) == 19
        assert session.get(Stage, "TW_DEEP_WATER_08_10_20260808") is None
        assert session.get(Team, "TM-W810-01") is None
        assert session.get(Character, "violet_isanami") is None
        assert all(
            member.is_borrowed is False
            for member in session.scalars(
                select(TeamMember).where(TeamMember.team_id == "TM-F810-01")
            )
        )
        a3_run = session.get(ImportRun, a3.import_run_id)
        assert a3_run is not None
        assert fixture_module.BORROWED_STATE_SEMANTICS_FIELD not in a3_run.manifest
        session.rollback()

        reactivate = import_pve_projection(
            session,
            a4_core,
            manifest_path=A4_MANIFEST,
            expected_manifest_sha256=RP_A4_MANIFEST_SHA256,
        )
        assert reactivate.created is False
        assert reactivate.activated is True
        assert session.get(Stage, "TW_DEEP_WATER_08_10_20260808") is not None
        assert session.get(Team, "TM-W810-05") is not None
        assert session.get(Character, "violet_isanami") is not None
        assert all(
            member.is_borrowed is None
            for member in session.scalars(
                select(TeamMember).where(TeamMember.team_id == "TM-W810-01")
            )
        )
        activations = session.scalars(
            select(RevisionActivation).order_by(RevisionActivation.sequence_no)
        ).all()
        assert [activation.kind for activation in activations] == [
            "IMPORT",
            "IMPORT",
            "ROLLBACK",
            "REACTIVATE",
        ]
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 2
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 2


def test_a4_pve_v2_rolls_back_from_a5_strategy_v3_and_reactivates_exactly(
    tmp_path: Path,
) -> None:
    a4_core = export_checkpoint_core(tmp_path, "rp-a4-1")
    engine = sqlite_engine()

    with Session(engine) as session:
        a4 = import_pve_projection(
            session,
            a4_core,
            manifest_path=A4_MANIFEST,
            expected_manifest_sha256=RP_A4_MANIFEST_SHA256,
            application_version="3.0.0-a4",
        )
        a4_run = session.get(ImportRun, a4.import_run_id)
        assert a4_run is not None
        assert a4_run.manifest["projection"] == fixture_module.FULL_PVE_PROJECTION
        assert a4_run.manifest["materialization"]["schema_version"] == 2
        assert a4.row_counts == {
            "stages": 3,
            "teams": 10,
            "team_members": 50,
            "characters": 25,
            "evidence": 55,
            "claims": 53,
            "operation_timelines": 15,
            "timeline_steps": 37,
        }
        assert session.scalar(select(func.count()).select_from(ArenaDefense)) == 0
        assert session.scalar(select(func.count()).select_from(ArenaCounter)) == 0
        session.rollback()

        a5 = import_pve_projection(
            session,
            RESEARCH_CORE,
            manifest_path=A5_MANIFEST,
            expected_manifest_sha256=RP_A5_MANIFEST_SHA256,
        )
        a5_run = session.get(ImportRun, a5.import_run_id)
        assert a5_run is not None
        assert a5_run.manifest["projection"] == fixture_module.FULL_STRATEGY_PROJECTION
        assert a5_run.manifest["materialization"]["schema_version"] == 3
        assert a5.row_counts["arena_defenses"] == 1
        assert a5.row_counts["arena_counters"] == 2
        assert session.scalar(select(func.count()).select_from(ArenaDefense)) == 1
        assert session.scalar(select(func.count()).select_from(ArenaCounter)) == 2
        session.rollback()

        rollback = import_pve_projection(
            session,
            a4_core,
            manifest_path=A4_MANIFEST,
            expected_manifest_sha256=RP_A4_MANIFEST_SHA256,
        )
        assert rollback.created is False
        assert rollback.activated is True
        assert rollback.row_counts == a4.row_counts
        assert session.scalar(select(func.count()).select_from(ArenaDefense)) == 0
        assert session.scalar(select(func.count()).select_from(ArenaDefenseMember)) == 0
        assert session.scalar(select(func.count()).select_from(ArenaCounter)) == 0
        assert session.scalar(select(func.count()).select_from(ArenaCounterMember)) == 0
        assert session.scalar(select(func.count()).select_from(ArenaCounterEvidence)) == 0
        assert session.scalar(select(func.count()).select_from(ArenaCounterClaim)) == 0
        a4_run = session.get(ImportRun, a4.import_run_id)
        assert a4_run is not None
        assert a4_run.manifest["materialization"]["schema_version"] == 2
        session.rollback()

        reactivate = import_pve_projection(
            session,
            RESEARCH_CORE,
            manifest_path=A5_MANIFEST,
            expected_manifest_sha256=RP_A5_MANIFEST_SHA256,
        )
        assert reactivate.created is False
        assert reactivate.activated is True
        assert reactivate.row_counts == a5.row_counts
        assert session.scalar(select(func.count()).select_from(ArenaDefense)) == 1
        assert session.scalar(select(func.count()).select_from(ArenaCounter)) == 2
        activations = session.scalars(
            select(RevisionActivation).order_by(RevisionActivation.sequence_no)
        ).all()
        assert [activation.kind for activation in activations] == [
            "IMPORT",
            "IMPORT",
            "ROLLBACK",
            "REACTIVATE",
        ]


def test_fresh_a5_first_load_of_a4_keeps_rollback_audit_semantics(
    tmp_path: Path,
) -> None:
    a4_core = export_checkpoint_core(tmp_path, "rp-a4-1")
    engine = sqlite_engine()

    with Session(engine) as session:
        a5 = import_pve_projection(
            session,
            RESEARCH_CORE,
            manifest_path=A5_MANIFEST,
            expected_manifest_sha256=RP_A5_MANIFEST_SHA256,
        )
        rollback = import_pve_projection(
            session,
            a4_core,
            manifest_path=A4_MANIFEST,
            expected_manifest_sha256=RP_A4_MANIFEST_SHA256,
        )
        reactivate = import_pve_projection(
            session,
            RESEARCH_CORE,
            manifest_path=A5_MANIFEST,
            expected_manifest_sha256=RP_A5_MANIFEST_SHA256,
        )

        assert a5.created is True
        assert rollback.created is True
        assert rollback.activated is True
        assert reactivate.created is False
        assert reactivate.activated is True
        activations = session.scalars(
            select(RevisionActivation).order_by(RevisionActivation.sequence_no)
        ).all()
        assert [activation.kind for activation in activations] == [
            "IMPORT",
            "ROLLBACK",
            "REACTIVATE",
        ]
        assert [activation.from_revision_id for activation in activations] == [
            None,
            a5.revision_id,
            rollback.revision_id,
        ]
        assert [activation.to_revision_id for activation in activations] == [
            a5.revision_id,
            rollback.revision_id,
            a5.revision_id,
        ]


def test_legacy_b1_manifest_rolls_back_and_reactivates_without_projection_drift(
    tmp_path: Path,
) -> None:
    first_core = export_checkpoint_core(tmp_path)
    a4_core = export_checkpoint_core(tmp_path, "rp-a4-1")
    assert snapshot_contract_for_manifest(RP_A2_MANIFEST_SHA256) == (
        RP_A2_SNAPSHOT_CONTRACT
    )

    engine = sqlite_engine()
    with Session(engine) as session:
        first = import_pve_projection(
            session,
            first_core,
            manifest_path=RP_A2_MANIFEST,
            expected_manifest_sha256=RP_A2_MANIFEST_SHA256,
            application_version="3.0.0-b1",
        )
        assert first.row_counts["stages"] == 1
        assert first.row_counts["teams"] == 3
        assert first.row_counts["characters"] == 8
        assert first.row_counts["evidence"] == 18
        assert first.row_counts["operation_timelines"] == 8
        assert first.row_counts["timeline_steps"] == 14
        first_run = session.get(ImportRun, first.import_run_id)
        assert first_run is not None
        assert first_run.manifest["projection"] == fixture_module.LEGACY_FIRE_PROJECTION

        # Simulate the immutable manifest shape written by the deployed B1
        # importer before projection became an explicit field.
        legacy_manifest = dict(first_run.manifest)
        legacy_manifest.pop("projection")
        legacy_manifest.pop(fixture_module.BORROWED_STATE_SEMANTICS_FIELD)
        legacy_manifest["target_guide_id"] = TARGET_GUIDE_ID
        # SQLite has no V0003 history trigger; a bulk update is used only to
        # construct the pre-existing B1 database fixture.  Application ORM
        # writes remain protected by the immutable-history guard.
        session.execute(
            update(ImportRun)
            .where(ImportRun.id == first.import_run_id)
            .values(manifest=legacy_manifest)
            .execution_options(synchronize_session=False)
        )
        session.commit()
        session.expire_all()

        second = import_pve_projection(
            session,
            a4_core,
            manifest_path=A4_MANIFEST,
            expected_manifest_sha256=RP_A4_MANIFEST_SHA256,
        )
        assert second.row_counts["stages"] == 3
        assert second.row_counts["teams"] == 10
        assert session.get(Stage, "TW_DEEP_FIRE_10_10_20260802") is not None
        assert session.get(Stage, "TW_DEEP_WATER_08_10_20260808") is not None
        assert session.get(Character, "anne_grea_orig") is not None
        assert session.get(Character, "violet_isanami") is not None
        session.rollback()

        rollback = import_pve_projection(
            session,
            first_core,
            manifest_path=RP_A2_MANIFEST,
            expected_manifest_sha256=RP_A2_MANIFEST_SHA256,
        )
        assert rollback.created is False
        assert rollback.activated is True
        assert session.scalar(select(func.count()).select_from(Stage)) == 1
        assert session.scalar(select(func.count()).select_from(Team)) == 3
        assert session.scalar(select(func.count()).select_from(Character)) == 8
        assert session.scalar(select(func.count()).select_from(Evidence)) == 18
        assert session.scalar(select(func.count()).select_from(OperationTimeline)) == 8
        assert session.scalar(select(func.count()).select_from(TimelineStep)) == 14
        assert session.get(Stage, "TW_DEEP_FIRE_10_10_20260802") is None
        assert session.get(Stage, "TW_DEEP_WATER_08_10_20260808") is None
        assert session.get(Character, "anne_grea_orig") is None
        assert session.get(Character, "violet_isanami") is None
        first_run = session.get(ImportRun, first.import_run_id)
        assert first_run is not None
        assert "projection" not in first_run.manifest
        assert first_run.manifest["target_guide_id"] == TARGET_GUIDE_ID
        session.rollback()

        reactivate = import_pve_projection(
            session,
            a4_core,
            manifest_path=A4_MANIFEST,
            expected_manifest_sha256=RP_A4_MANIFEST_SHA256,
        )
        assert reactivate.created is False
        assert reactivate.activated is True
        assert session.get(Stage, "TW_DEEP_FIRE_10_10_20260802") is not None
        assert session.get(Stage, "TW_DEEP_WATER_08_10_20260808") is not None
        assert session.get(Character, "anne_grea_orig") is not None
        assert session.get(Character, "violet_isanami") is not None
        activations = session.scalars(
            select(RevisionActivation).order_by(RevisionActivation.sequence_no)
        ).all()
        assert [activation.kind for activation in activations] == [
            "IMPORT",
            "IMPORT",
            "ROLLBACK",
            "REACTIVATE",
        ]
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 2
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 2


def test_failed_revision_switch_rolls_back_rows_pointer_and_artifact_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = sqlite_engine()
    first_core, first_manifest, first_manifest_sha256 = build_manifested_core(
        tmp_path,
        name="failed-base",
    )
    second_core = tmp_path / "failed" / "pcr_tw_project"
    shutil.copytree(first_core, second_core)
    readme = second_core / "README.md"
    readme.write_bytes(readme.read_bytes() + b"\n")
    second_manifest = tmp_path / "failed.sha256"
    second_manifest_sha256 = write_tree_manifest(second_core, second_manifest)

    with Session(engine) as session:
        first = import_fire_8_10(
            session,
            first_core,
            manifest_path=first_manifest,
            expected_manifest_sha256=first_manifest_sha256,
        )
        original_upsert = fixture_module._upsert

        def fail_first_typed_row(session, model, key, values):
            original_upsert(session, model, key, values)
            raise RuntimeError("injected revision switch failure")

        monkeypatch.setattr(fixture_module, "_upsert", fail_first_typed_row)
        with pytest.raises(RuntimeError, match="revision switch failure"):
            import_fire_8_10(
                session,
                second_core,
                manifest_path=second_manifest,
                expected_manifest_sha256=second_manifest_sha256,
            )

        state = session.get(MaterializationState, 1)
        stage = session.get(Stage, TARGET_GUIDE_ID)
        assert state is not None
        assert stage is not None
        assert state.active_revision_id == first.revision_id
        assert stage.import_run_id == first.import_run_id
        assert session.scalar(select(func.count()).select_from(CoreRevision)) == 1
        assert session.scalar(select(func.count()).select_from(ImportRun)) == 1
        assert session.scalar(select(func.count()).select_from(RevisionActivation)) == 1
