from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "a5_a4_rollback_drill.ps1"


def test_a5_a4_drill_uses_exact_pins_and_restores_a5() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "PINNED_ROLLBACK_SOURCE_OK" in source
    assert "Write-Host $proofLine" in source
    assert "$proof.manifest_sha256 -ne $a4ManifestSha256" in source
    assert "$proof.revision_id -ne $a4Revision" in source
    assert "[int]$proof.file_count -ne 48" in source
    assert "[int]$proof.csv_row_count -ne 325" in source
    assert "research_core_rp_a4_manifest.sha256" in source
    assert (
        "3daf2ab7c212b4f11c58883980d0ada3862400923c81a9bdedcc0500e59b1a9e"
        in source
    )
    assert (
        "c5a5f13e0efaf96c1a266c1016d3a1a54740859952ce21f9db3cf89d779d57b9"
        in source
    )
    assert "73bc25ab75e78f4e762c3afc902c53dfa47180a36a7359a102fbf5e173fb35bf" in source
    assert "6a589eb4eca59f94e52af22752d376be576c1b1562b28a43acadb2abfa219853" in source
    assert "3c4450f90814fa78384d36d60434c665e1b3a2b7b247804ed324d223e7aeb12a" in source
    assert (
        "1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c"
        in source
    )
    assert (
        "1826c8493d40f71a6d0bb9096f57b92fe4e839d52bddf021b0c51e0186dcbda7"
        in source
    )
    assert "c77bc9893fa0b442832c1dff0c7c4a1c5e6d63ba9bce27c1c2f8078c5c2511b8" in source
    assert "84fea5ed4095dfcbb98cb52816c2e8a7a3d9fd1acd9ef225541ba27b8bcc192e" in source
    assert "b0fefe463e3968266ed8a8378fd8b7f5c94817a4dd548f920facf7c182fa0e64" in source
    assert "function Assert-RevisionIdentity" in source
    assert "$activeImportRun -ne $ExpectedImportRunId" in source
    assert "$activeMaterialization -ne $ExpectedMaterializationSha256" in source
    assert "$a4InstanceMaterialization" in source
    assert "downgrade v0005_borrowed_tristate" in source
    assert "A5_A4_ROLLBACK_READY_OK" in source
    assert "alembic -c database/alembic.ini upgrade head" in source
    assert "RESEARCH_BASELINE_OK" in source
    assert "A5_RESTORED_OK" in source
    assert "A5_A4_ROLLBACK_DRILL_OK" in source
    assert "$LeaveAtA4" in source
    assert "A4_SERVICES_QUIESCED_OK" in source
    assert "A5_A4_ROLLBACK_COMPLETE_OK" in source
    assert "$VerifiedBackupPath" in source
    assert "$VerifiedBackupSha256" in source
    assert "VERIFIED_BACKUP_INPUT_OK" in source
    assert "Get-FileHash -LiteralPath $VerifiedBackupPath -Algorithm SHA256" in source
    assert "CROSS JOIN LATERAL jsonb_object_keys" in source
    assert "jsonb_object_length" not in source


def test_a4_activation_requires_all_six_arena_tables_to_be_empty() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    tables = (
        "arena_defenses",
        "arena_defense_members",
        "arena_counters",
        "arena_counter_members",
        "arena_counter_evidence",
        "arena_counter_claims",
    )

    for table in tables:
        assert f'SELECT COUNT(*) FROM {table}' in source
        assert f"{table} = 0" in source

    a4_zero_check = source.index('}) -Label "A4"')
    downgrade = source.index("downgrade v0005_borrowed_tristate", a4_zero_check)
    assert a4_zero_check < downgrade
    assert "to_regclass('public.' || name) IS NOT NULL" in source[downgrade:]


def test_a5_a4_drill_arms_recovery_before_side_effects() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    stop_call = source.index("Invoke-Compose stop web api scheduler")
    restart_guard = source.index("$servicesStopped = $true")
    importer_call = source.index("$rollbackOutput = & docker")
    restore_guard = source.index("$needsA5Restore = $true")

    assert restart_guard < stop_call
    assert restore_guard < importer_call


def test_a5_a4_drill_restarts_only_after_verified_a5_health() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    restart_gate = source.index("if ($servicesStopped -and -not $needsA5Restore)")
    database_guard = source.index("Assert-A5DatabaseState", restart_gate)
    compose_wait = source.index(
        "Invoke-Compose up --detach --no-build --wait --wait-timeout 60",
        database_guard,
    )
    readiness = source.index('/health/ready"', compose_wait)
    success = source.index("A5_SERVICES_READY_OK", readiness)

    assert restart_gate < database_guard < compose_wait < readiness < success
    assert "SERVICES_LEFT_QUIESCED" in source
    assert "Invoke-Compose stop web api scheduler" in source[compose_wait:]


def test_a5_restore_reapplies_service_role_grants_before_import() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    restore = source.index("function Restore-A5")
    upgrade = source.index("alembic -c database/alembic.ini upgrade head", restore)
    role_provision = source.index(
        "Invoke-Compose run --rm --no-deps role-provision", upgrade
    )
    importer = source.index("$restoreOutput = & docker", role_provision)

    assert upgrade < role_provision < importer


def test_permanent_a4_boundary_is_after_exact_identity_and_downgrade_checks() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    precheck = source.index("$activeMaterialization -ne $a4InstanceMaterialization")
    arena_zero = source.index('}) -Label "A4"')
    downgrade = source.index("downgrade v0005_borrowed_tristate", precheck)
    post_revision = source.index(
        '$downgradedRevision -ne "v0005_borrowed_tristate"', downgrade
    )
    post_identity = source.index(
        "$downgradedMaterialization -ne $a4InstanceMaterialization", post_revision
    )
    post_schema = source.index("$remainingArenaTables -ne 0", post_identity)
    permanent_boundary = source.index("$leaveAtA4Completed = $true", post_schema)

    assert arena_zero < precheck < downgrade
    assert downgrade < post_revision < post_identity < post_schema < permanent_boundary


def test_scheduler_safety_flags_are_checked_before_quiesce_or_mutation() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    scheduler_guard = source.index("SCHEDULER_ENABLED must remain false")
    shadow_guard = source.index("SHADOW_MODE must remain true")
    publisher_guard = source.index("AUTO_PUBLISH must remain false")
    backup_guard = source.index("VERIFIED_BACKUP_INPUT_OK")
    first_side_effect = source.index("Invoke-Compose stop web api scheduler")

    assert backup_guard < first_side_effect
    assert scheduler_guard < first_side_effect
    assert shadow_guard < first_side_effect
    assert publisher_guard < first_side_effect


def test_a5_restore_verifies_normalized_arena_closure() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assertion = source.index("function Assert-A5DatabaseState")
    restoration = source.index("function Restore-A5", assertion)
    block = source[assertion:restoration]

    assert "arena_defenses = 1" in source
    assert "arena_defense_members = 5" in source
    assert "arena_counters = 2" in source
    assert "arena_counter_members = 10" in source
    assert "arena_counter_evidence = 4" in source
    assert "arena_counter_claims = 4" in source
    assert '$revision -ne "v0006_arena_counter_slice"' in block
    assert "$activeRevision -ne $a5Revision" in block
    assert "$activeImportRun -ne $ExpectedImportRunId" in block
    assert "$activeMaterialization -ne $ExpectedMaterializationSha256" in block
    assert "Assert-RevisionIdentity" in block
    assert "Assert-DatabaseCounts -Expected $a5ServingCounts" in block
    assert "stage_evidence = 47" in source
    assert "stage_claims = 46" in source
    assert "team_evidence = 95" in source
    assert "claim_evidence = 150" in source


def test_a5_a4_drill_verifies_import_results_and_activation_chronology() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "function Get-ImportResult" in source
    assert "$a4Result = Get-ImportResult" in source
    assert "$restoreResult = Get-ImportResult" in source
    assert "$Result.created -ne $false" in source
    assert "$Result.activated -ne $ExpectedActivated" in source
    assert "-ExpectedActivated $expectedActivated" in source
    assert '$a4Result.activated -ne $true' in source
    assert '-Kind "ROLLBACK"' in source
    assert '-Kind "REACTIVATE"' in source
    assert "$a4ActivationSequence -ne ($originActivationSequence + 1)" in source
    assert "$reactivationSequence -ne ($originActivationSequence + 2)" in source
    assert "$restoreResult.import_run_id -ne $originA5ImportRunId" in source


def test_a5_restore_classifies_exact_noop_reactivate_and_reentrant_states() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    restore_start = source.index("function Restore-A5")
    restore_end = source.index("$servicesStopped = $false", restore_start)
    restore = source[restore_start:restore_end]

    assert 'return "ORIGIN_NOOP"' in source
    assert 'return "A4_REACTIVATE"' in source
    assert 'return "ALREADY_RESTORED_NOOP"' in source
    assert '$expectedActivated = $recoveryMode -eq "A4_REACTIVATE"' in restore
    assert "Assert-A5RecoveryOutcome -Mode $recoveryMode" in restore
    assert "$a4ActivationVerified" not in restore
    assert "$sequence -ne $originActivationSequence" in source
    assert "$epoch -ne $originEpoch" in source
    assert "$stateEpoch -ne $reactivationEpoch" in source
    assert "$rollbackEpoch -le $originEpoch" in source
    assert "$reactivationEpoch -le $rollbackEpoch" in source


def test_a5_recovery_chain_requires_exact_append_only_audit_identity() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "function Assert-OriginActivationAnchor" in source
    assert "Assert-OriginActivationAnchor" in source[
        source.index("$originEpoch ="):source.index("Invoke-Compose stop web api scheduler")
    ]
    assert '$actualActor -ne "pcr_pipeline.import_pve"' in source
    assert 'ROLLBACK = "rollback to earlier verified immutable revision"' in source
    assert 'REACTIVATE = "reactivate later verified immutable revision"' in source
    assert "-Sequence ($originActivationSequence + 1)" in source
    assert "-Sequence $reactivationSequence" in source


def test_compose_target_preflight_is_explicit_and_precedes_database_access() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    for parameter in (
        "$ProjectName",
        "$ExpectedApiImage",
        "$ExpectedSchedulerImage",
        "$ExpectedApiPort",
    ):
        assert parameter in source[: source.index(")\n\n$ErrorActionPreference")]
    assert '"--project-name", $ProjectName' in source
    assert "function Assert-ComposePreflight" in source
    assert "config --format json" in source
    assert '@("api", "importer", "migration", "role-provision")' in source
    assert '$service.image -cne $ExpectedApiImage' in source
    assert '$scheduler.image -cne $ExpectedSchedulerImage' in source
    assert '[int]$apiBinding.published -ne $ExpectedApiPort' in source
    assert '[string]$apiBinding.host_ip -cne "127.0.0.1"' in source

    preflight = source.index("Assert-ComposePreflight\n\n$servicesStopped")
    first_database_access = source.index(
        '$originA5ImportRunId = Get-Scalar "SELECT active_import_run_id', preflight
    )
    first_side_effect = source.index("Invoke-Compose stop web api scheduler")
    assert preflight < first_database_access < first_side_effect


def test_restarted_api_uses_and_verifies_the_actual_compose_port() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    restart = source.index(
        "Invoke-Compose up --detach --no-build --wait --wait-timeout 60"
    )
    actual_port = source.index("$actualApiPort = Get-ActualApiPort", restart)
    readiness = source.index(
        'http://127.0.0.1:${actualApiPort}/health/ready', actual_port
    )

    assert "& docker @compose port api 8000" in source
    assert "^127\\.0\\.0\\.1:(\\d{1,5})$" in source
    assert "$actualApiPort -ne $ExpectedApiPort" in source
    assert restart < actual_port < readiness
