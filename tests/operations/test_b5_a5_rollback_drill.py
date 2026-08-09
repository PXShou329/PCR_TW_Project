from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "b5_a5_rollback_drill.ps1"


def source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_drill_has_no_permanent_a5_mode_and_requires_exact_target() -> None:
    text = source()
    params = text[: text.index("$ErrorActionPreference")]
    for parameter in (
        "$EnvFile",
        "$ProjectName",
        "$ExpectedApiImage",
        "$ExpectedSchedulerImage",
        "$ExpectedApiPort",
        "$ExpectedWebPort",
        "$ExpectedSchedulerPort",
        "$A5CheckpointRoot",
        "$VerifiedBackupPath",
        "$VerifiedBackupSha256",
    ):
        assert parameter in params
    assert "LeaveAtA5" not in text
    assert "LeaveAtA4" not in text
    assert '"pcr-tw-a5-arena", "pcr-tw-a4-water", "pcr-tw-b1"' in text
    assert '"--project-name", $ProjectName' in text
    assert '"--profile", "verification"' in text
    assert "$null -ne $db.ports" in text
    assert "function Assert-ComposePreflight" in text
    assert "function Assert-RunningDbIdentity" in text
    assert "com.docker.compose.project" in text
    assert '"${ProjectName}_pg_data"' in text


def test_preflight_pins_images_ports_network_and_shadow_mode() -> None:
    text = source()
    preflight = text[text.index("function Assert-ComposePreflight") :]

    assert "config --format json" in preflight
    assert "ExpectedApiImage" in preflight
    assert "ExpectedSchedulerImage" in preflight
    assert "Assert-LoopbackPort $api 8000 $ExpectedApiPort" in preflight
    assert "Assert-LoopbackPort $web 3000 $ExpectedWebPort" in preflight
    assert "Assert-LoopbackPort $scheduler 8081 $ExpectedSchedulerPort" in preflight
    assert "$config.networks.backend.internal" in preflight
    assert '$scheduler.environment.SCHEDULER_ENABLED -cne "false"' in preflight
    assert '$scheduler.environment.SHADOW_MODE -cne "true"' in preflight
    assert '$scheduler.environment.AUTO_PUBLISH -cne "false"' in preflight

    preflight_call = text.index("Assert-ComposePreflight\nInvoke-Compose ps")
    target_call = text.index("Assert-RunningDbIdentity", preflight_call)
    first_db_read = text.index("$originB5ImportRun = Get-Scalar", target_call)
    assert preflight_call < target_call < first_db_read


def test_exact_b5_and_a5_portable_pins_are_embedded() -> None:
    text = source()
    for digest in (
        "e74814d6433ee327611f10322937bdfa9687b9887f139ba6e6158a291dd12989",
        "d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d",
        "a7467a838c2a9cfdfe48bda4a3b158fb374dd023caa3478a84c07678532ea9f4",
        "a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af",
        "24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c",
        "1826c8493d40f71a6d0bb9096f57b92fe4e839d52bddf021b0c51e0186dcbda7",
        "1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c",
        "c77bc9893fa0b442832c1dff0c7c4a1c5e6d63ba9bce27c1c2f8078c5c2511b8",
        "84fea5ed4095dfcbb98cb52816c2e8a7a3d9fd1acd9ef225541ba27b8bcc192e",
        "b0fefe463e3968266ed8a8378fd8b7f5c94817a4dd548f920facf7c182fa0e64",
    ):
        assert digest in text
    assert "Assert-RevisionIdentity $b5Revision" in text
    assert " 376 120 $b5EvidenceToClaimSha256 298 " in text
    assert " $ExpectedMaterialization 4 23 $b5RowCounts" in text
    assert "Assert-RevisionIdentity $a5Revision" in text
    assert " 356 111 $a5EvidenceToClaimSha256 277 " in text
    assert " $ExpectedMaterialization 3 18 $a5RowCounts" in text


def test_exact_b5_and_a5_count_closures_include_gacha_boundary() -> None:
    text = source()
    for marker in (
        "$b5RowCounts = [ordered]@{",
        "$b5ServingCounts = [ordered]@{",
        "evidence = 73",
        "claims = 69",
        "claim_evidence = 159",
        "gacha_timeline_events = 5",
        "gacha_timeline_evidence = 10",
        "gacha_timeline_claims = 8",
        "gacha_community_sources = 4",
        "gacha_timeline_community_sources = 0",
        "$a5RowCounts = [ordered]@{",
        "$a5ServingCounts = [ordered]@{",
        "evidence = 64",
        "claims = 62",
        "claim_evidence = 150",
    ):
        assert marker in text
    assert "Assert-CountObject $result.row_counts $b5RowCounts" in text
    assert "Assert-CountObject $a5Result.row_counts $a5RowCounts" in text
    assert 'throw "A5 rollback left Gacha rows in $table"' in text
    assert 'throw "V0007 to V0006 downgrade left Gacha tables behind"' in text


def test_backup_is_verified_before_any_rollback_side_effect() -> None:
    text = source()
    hash_check = text.index("Verified backup SHA-256 mismatch")
    receipt = text.index("VERIFIED_BACKUP_INPUT_OK", hash_check)
    stop = text.index("Invoke-Compose stop web api scheduler")
    assert "Get-FileHash -LiteralPath $VerifiedBackupPath -Algorithm SHA256" in text[:receipt]
    assert hash_check < receipt < stop


def test_recovery_is_armed_before_a5_import_and_services_stop_is_recoverable() -> None:
    text = source()
    stop = text.index("Invoke-Compose stop web api scheduler")
    stopped_guard = text.rindex("$servicesStopped = $true", 0, stop)
    importer = text.index("$rollbackOutput = & docker", stop)
    recovery_guard = text.rindex("$needsB5Restore = $true", stop, importer)
    assert stopped_guard < stop < recovery_guard < importer
    assert "if ($needsB5Restore)" in text
    assert "SERVICES_LEFT_QUIESCED" in text
    assert "manual recovery from the verified backup" in text


def test_data_rollback_is_verified_before_v0007_schema_downgrade() -> None:
    text = source()
    proof = text.index("PINNED_ROLLBACK_SOURCE_OK")
    a5_state = text.index('Assert-A5State "v0007_gacha_timeline_slice"', proof)
    zero_marker = text.index("A5_DATA_ROLLBACK_OK", a5_state)
    downgrade = text.index("downgrade v0006_arena_counter_slice", zero_marker)
    v6_state = text.index('Assert-A5State "v0006_arena_counter_slice"', downgrade)
    schema_marker = text.index("B5_A5_SCHEMA_ROLLBACK_OK", v6_state)
    assert proof < a5_state < zero_marker < downgrade < v6_state < schema_marker
    assert "research_core_rp_a5_manifest.sha256" in text
    assert "/rollback/research_core/pcr_tw_project" in text
    assert '[int]$proof.csv_row_count -ne 356' in text


def test_b5_restore_upgrades_then_reapplies_roles_before_import() -> None:
    text = source()
    restore = text.index("function Restore-B5")
    upgrade = text.index("alembic -c database/alembic.ini upgrade head", restore)
    roles = text.index("Invoke-Compose run --rm --no-deps role-provision", upgrade)
    privileges = text.index("Assert-DbPrivilegeContract", roles)
    importer = text.index("$output = & docker", privileges)
    b5_state = text.index("Assert-B5State $originB5ImportRun", importer)
    assert upgrade < roles < privileges < importer < b5_state
    assert "$result.created -ne $false" in text[restore:]
    assert "$result.activated -ne $expectedActivated" in text[restore:]
    assert "$result.import_run_id -ne $originB5ImportRun" in text[restore:]
    assert "manifest_sha256=$b5ManifestSha256" in text[restore:]


def test_acl_gate_pins_final_matrix_before_mutation_and_after_role_reapply() -> None:
    text = source()
    helper = text[text.index("function Assert-DbPrivilegeContract") : text.index("function Assert-CountObject")]
    assert '"scripts\\check_db_privileges.ps1"' in helper
    assert "DB_PRIVILEGES_OK matrix_checks=651 actual_denials=23 allowed_smokes=10" in helper
    assert "privilegeExit -ne 0" in helper
    origin_call = text.index("Assert-DbPrivilegeContract", text.index("Assert-B5PublicReadiness", text.index("try {")))
    stop = text.index("Invoke-Compose stop web api scheduler", origin_call)
    assert origin_call < stop


def test_activation_audit_is_exact_and_monotonic() -> None:
    text = source()
    assert 'ROLLBACK = "rollback to earlier verified immutable revision"' in text
    assert 'REACTIVATE = "reactivate later verified immutable revision"' in text
    assert "pcr_pipeline.import_pve" in text
    assert "($originActivationSequence + 1) $b5Revision $a5Revision" in text
    assert "($originActivationSequence + 2) $a5Revision $b5Revision" in text
    assert "$rollbackEpoch -le $originEpoch" in text
    assert "$reactivateEpoch -le $rollbackEpoch" in text
    assert "$stateEpoch -ne $reactivateEpoch" in text
    assert "$a5Sequence -ne ($originActivationSequence + 1)" in text


def test_recovery_classifies_only_exact_origin_a5_or_restored_b5() -> None:
    text = source()
    assert 'return "ORIGIN_NOOP"' in text
    assert 'return "ALREADY_RESTORED_NOOP"' in text
    assert 'return "A5_REACTIVATE"' in text
    assert 'throw "Recovery state is neither origin B5, exact A5 rollback, nor restored B5"' in text
    assert '$expectedActivated = $mode -eq "A5_REACTIVATE"' in text
    assert "Assert-RecoveryChain" in text


def test_services_restart_only_after_exact_b5_and_full_readiness() -> None:
    text = source()
    restart_gate = text.index("if ($servicesStopped -and -not $needsB5Restore)")
    state = text.index("Assert-B5State $originB5ImportRun", restart_gate)
    up = text.index("Invoke-Compose up --detach --no-build --wait --wait-timeout 90 --no-deps", state)
    readiness = text.index("Assert-B5PublicReadiness", up)
    history = text.index("revision-history-verify", readiness)
    marker = text.index("B5_SERVICES_READY_OK", history)
    assert restart_gate < state < up < readiness < history < marker
    assert "Invoke-Compose stop web api scheduler" in text[up:]
    assert "B5_A5_ROLLBACK_DRILL_OK" in text


def test_public_readiness_pins_b5_gacha_web_and_scheduler() -> None:
    text = source()
    readiness = text[text.index("function Assert-B5PublicReadiness") : text.index("function Assert-OriginAnchor")]
    for marker in (
        '"3.0.0-b5"',
        "/api/v1/gacha/timeline",
        "/api/v1/gacha/community-sources",
        "/gacha",
        '$gachaRows.Count -ne 5',
        '@($community.data).Count -ne 4',
        '@($gachaRows | Where-Object { $_.maturity -eq "MATURE" }).Count -ne 2',
        '@($gachaRows | Where-Object { $_.maturity -eq "RESEARCH" }).Count -ne 3',
        '$expectedGachaLimitedStatuses = @("YES", "YES", "YES", "UNKNOWN", "UNKNOWN")',
        '($gachaLimitedClaimIds -join "|") -ne ($expectedGachaLimitedClaimIds -join "|")',
        '($gachaEventIds -join "|") -ne ($expectedGachaEventIds -join "|")',
        '"CLM-SHEFI-POOL"',
        '"CLM-LUISE-DATE"',
        '"CLM-JP-FUBUKI-DATE"',
        'gachaPage.Content -notmatch "抽卡未來視"',
        'gachaPage.Content -notmatch "限定身分 UNKNOWN"',
        "scheduler.canonical_write_capable",
    ):
        assert marker in readiness
