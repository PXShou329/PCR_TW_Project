from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKUP_RESTORE_SCRIPT = REPOSITORY_ROOT / "scripts" / "backup_restore_smoke.ps1"
API_DOCKERFILE = REPOSITORY_ROOT / "infra" / "docker" / "api.Dockerfile"
CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"


def source() -> str:
    return BACKUP_RESTORE_SCRIPT.read_text(encoding="utf-8")


def test_b5_ci_uses_exact_stack_backup_and_rollback_contract() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    for marker in (
        "group: rp-b5-1-",
        "COMPOSE_PROJECT_NAME: pcr-tw-b5-ci",
        "PCR_API_IMAGE: pcr-tw-platform-api:b5-ci",
        "PCR_SCHEDULER_IMAGE: pcr-tw-platform-scheduler:b5-ci",
        "-ProjectName $env:COMPOSE_PROJECT_NAME",
        "-ExpectedApiImage $env:PCR_API_IMAGE",
        "-ExpectedSchedulerImage $env:PCR_SCHEDULER_IMAGE",
        "-ExpectedApiPort ([int]$env:API_PORT)",
        "-ExpectedWebPort ([int]$env:WEB_PORT)",
        "-ExpectedSchedulerPort ([int]$env:SCHEDULER_HEALTH_PORT)",
        "git archive --format=tar --output=$checkpointArchive rp-a5-2",
        "./scripts/b5_a5_rollback_drill.ps1",
    ):
        assert marker in workflow
    assert "-SeedRevisionHistory" not in workflow


def test_target_identity_is_mandatory_and_precedes_database_access() -> None:
    text = source()
    parameter_block = text[: text.index("$ErrorActionPreference")]
    for parameter in (
        "$EnvFile",
        "$ProjectName",
        "$ExpectedApiImage",
        "$ExpectedSchedulerImage",
        "$ExpectedApiPort",
        "$ExpectedWebPort",
        "$ExpectedSchedulerPort",
    ):
        assert parameter in parameter_block
    assert text.count("[Parameter(Mandatory = $true)]") >= 7
    assert '"pcr-tw-a5-arena", "pcr-tw-a4-water", "pcr-tw-b1"' in text
    assert '"--project-name", $ProjectName' in text
    assert '"--profile", "verification"' in text
    assert "function Assert-ComposePreflight" in text
    assert "config --format json" in text
    assert "function Assert-RunningDbIdentity" in text
    assert "com.docker.compose.project" in text
    assert '"${ProjectName}_pg_data"' in text

    preflight = text.index("Assert-ComposePreflight\n    Invoke-DockerChecked ps")
    db_identity = text.index("Assert-RunningDbIdentity", preflight)
    first_database_query = text.index(
        "$sourceImporterUrl =", db_identity
    )
    assert preflight < db_identity < first_database_query


def test_preflight_pins_images_ports_network_and_scheduler_safety() -> None:
    text = source()
    preflight = text[text.index("function Assert-ComposePreflight") :]

    for service in (
        "api",
        "importer",
        "migration",
        "role-provision",
        "round-trip-smoke",
        "consistency-smoke",
        "cache-epoch-smoke",
        "artifact-lock-smoke",
        "revision-history-smoke",
        "revision-history-verify",
    ):
        assert f'"{service}"' in preflight
    assert '$service.image -cne $ExpectedApiImage' in preflight
    assert '$service.image -cne $ExpectedSchedulerImage' in preflight
    assert "Assert-LoopbackPort -Service $api -ContainerPort 8000" in preflight
    assert "Assert-LoopbackPort -Service $web -ContainerPort 3000" in preflight
    assert "Assert-LoopbackPort -Service $scheduler -ContainerPort 8081" in preflight
    assert "Database must not expose a published port" in preflight
    assert "$null -ne $db.ports" in preflight
    assert "$config.networks.backend.internal" in preflight
    assert '$scheduler.environment.SCHEDULER_ENABLED -cne "false"' in preflight
    assert '$scheduler.environment.SHADOW_MODE -cne "true"' in preflight
    assert '$scheduler.environment.AUTO_PUBLISH -cne "false"' in preflight


def test_b5_identity_and_all_count_closures_are_exact() -> None:
    text = source()
    for digest in (
        "e74814d6433ee327611f10322937bdfa9687b9887f139ba6e6158a291dd12989",
        "d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d",
        "a7467a838c2a9cfdfe48bda4a3b158fb374dd023caa3478a84c07678532ea9f4",
        "a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af",
        "24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c",
    ):
        assert digest in text
    for marker in (
        "file_count || '|' || csv_file_count || '|' || csv_row_count",
        "SUCCEEDED|48|13|376|120",
        "research_core_file_ssot|4|$activeMaterialization|23",
        "$b5RowCounts = [ordered]@{",
        "$b5ServingCounts = [ordered]@{",
        "evidence = 73",
        "claims = 69",
        "stage_evidence = 47",
        "stage_claims = 46",
        "team_evidence = 95",
        "claim_evidence = 159",
        "gacha_timeline_events = 5",
        "gacha_timeline_evidence = 10",
        "gacha_timeline_claims = 8",
        "gacha_community_sources = 4",
        "gacha_timeline_community_sources = 0",
    ):
        assert marker in text
    assert '"v0007_gacha_timeline_slice"' in text
    assert '"3.0.0-b5"' in text


def test_source_identity_and_epoch_are_stable_across_dump_and_drill() -> None:
    text = source()
    source_identity = text.index(
        '$sourceIdentity = Assert-B5DatabaseIdentity -Database $SourceDatabase'
    )
    dump = text.index("Invoke-DockerChecked exec -T db pg_dump", source_identity)
    after_dump = text.index(
        '$sourceIdentityAfterDump = Assert-B5DatabaseIdentity', dump
    )
    restored = text.index(
        '$restoreIdentity = Assert-B5DatabaseIdentity', after_dump
    )
    final = text.index(
        '$finalSourceIdentity = Assert-B5DatabaseIdentity', restored
    )

    assert source_identity < dump < after_dump < restored < final
    assert "$sourceIdentityAfterDump.Epoch -ne $sourceIdentity.Epoch" in text
    assert "$restoreIdentity.Materialization -ne $sourceIdentity.Materialization" in text
    assert "$finalSourceIdentity.Epoch -ne $sourceIdentity.Epoch" in text
    assert "Source and restored public table sets differ" in text


def test_restore_covers_gacha_api_web_and_unknown_semantics() -> None:
    text = source()
    assert "$proxyGacha" not in text
    for route in (
        "/api/v1/gacha/timeline",
        "/api/v1/gacha/community-sources",
        "/gacha",
    ):
        assert route in text
    assert '@($gachaRows | Where-Object { $_.maturity -eq "MATURE" }).Count -ne 2' in text
    assert '@($gachaRows | Where-Object { $_.maturity -eq "RESEARCH" }).Count -ne 3' in text
    assert '$_.relative_priority -ne "NOT_EVALUATED"' in text
    assert '$_.limited_status -ne "UNKNOWN"' in text
    assert '$expectedGachaLimitedStatuses = @("YES", "YES", "YES", "UNKNOWN", "UNKNOWN")' in text
    for claim_id in (
        "CLM-SHEFI-POOL",
        "CLM-LUISE-DATE",
        "CLM-JP-FUBUKI-DATE",
    ):
        assert claim_id in text
    assert '($gachaLimitedClaimIds -join "|") -ne ($expectedGachaLimitedClaimIds -join "|")' in text
    assert '($gachaEventIds -join "|") -ne ($expectedGachaEventIds -join "|")' in text
    assert '@($gachaCommunityRows | Where-Object { $_.update_status -eq "CHECKED" }).Count -ne 2' in text
    assert '@($gachaCommunityRows | Where-Object { $_.update_status -eq "STALE" }).Count -ne 2' in text
    assert 'gachaResponse.Content -notmatch "抽卡未來視"' in text
    assert 'gachaResponse.Content -notmatch "限定身分 UNKNOWN"' in text
    assert "RESTORED_API_READINESS_OK" in text
    assert "gacha_events=5 gacha_sources=4" in text


def test_v0007_empty_v4_probe_is_separate_and_fails_closed() -> None:
    text = source()
    probe = text[text.index("# A second restored database") :]

    assert "$probeDatabase" in probe
    assert "$probeCreated = $true" in probe
    assert "TRUNCATE TABLE gacha_timeline_community_sources" in probe
    assert "$probeGachaRows -ne 0" in probe
    assert "downgrade v0006_arena_counter_slice" in probe
    assert "$downgradeExit -eq 0" in probe
    assert "verified Arena v3 materialization owns the mirror" in probe
    assert '$postDowngradeRevision -ne "v0007_gacha_timeline_slice"' in probe
    assert "$postDowngradeGachaTables -ne 5" in probe
    assert "$postDowngradeActiveRevision -ne $probeIdentity.Revision" in probe
    assert "$postDowngradeActiveRun -ne $probeIdentity.ImportRun" in probe
    assert "$postDowngradeMaterialization -ne $probeIdentity.Materialization" in probe
    assert "$postDowngradeEpoch -ne $probeIdentity.Epoch" in probe
    assert "$postDowngradeNonGachaRows -ne $probeNonGachaRows" in probe
    assert "GACHA_DOWNGRADE_BLOCKED_OK" in probe
    assert "ARENA_DOWNGRADE_BLOCKED_OK" not in probe

    probe_create = probe.index("createdb")
    probe_restore = probe.index("pg_restore", probe_create)
    truncate = probe.index("TRUNCATE TABLE", probe_restore)
    downgrade = probe.index("downgrade v0006_arena_counter_slice", truncate)
    assert probe_create < probe_restore < truncate < downgrade


def test_cleanup_and_machine_readable_receipt_are_fail_closed() -> None:
    text = source()
    receipt = text.index('status = "BACKUP_RESTORE_VERIFIED"')
    final_identity = text.index("$finalSourceIdentity =", text.index("GACHA_DOWNGRADE_BLOCKED_OK"))
    receipt_output = text.index("Write-Output ($receipt | ConvertTo-Json -Compress)", receipt)
    cleanup_failure = text.index('throw "Backup/restore succeeded but cleanup failed:', receipt)
    assert final_identity < receipt
    for field in (
        "project = $ProjectName",
        "source_database = $SourceDatabase",
        "path = $backupPath",
        "sha256 = $backupSha256",
        "bytes = $backupBytes",
        "alembic_revision = $sourceIdentity.Alembic",
        "revision_id = $sourceIdentity.Revision",
        "import_run_id = $sourceIdentity.ImportRun",
        "materialization_sha256 = $sourceIdentity.Materialization",
        "source_epoch = $sourceIdentity.Epoch",
    ):
        assert field in text[receipt:]
    assert cleanup_failure < receipt_output
    assert 'throw "Backup/restore completed without a verification receipt"' in text[cleanup_failure:receipt_output]
    assert "backup_retained = [bool]$KeepBackup" in text[receipt:]
    assert "restore_database_retained = [bool]$KeepRestoredDatabase" in text[receipt:]
    assert 'Invoke-CleanupStep -Name "V0007 probe database"' in text
    assert "Removed disposable V0007 probe database" in text
    assert 'Invoke-CleanupStep -Name "restore database"' in text
    assert 'Invoke-CleanupStep -Name "backup files"' in text


def test_backup_fallback_uses_verified_db_container_identity() -> None:
    text = source()
    identity = text.index("$dbContainerId = Assert-RunningDbIdentity")
    dump = text.index("pg_dump", identity)
    copy = text.index('Invoke-DockerChecked cp "${dbContainerId}:/backups/$backupName"', dump)
    assert "return $containerId" in text[text.index("function Assert-RunningDbIdentity") : identity]
    assert identity < dump < copy
    assert 'cp "db:/backups/$backupName"' not in text


def test_restored_acl_gate_requires_final_b5_matrix_marker() -> None:
    text = source()
    helper = text[text.index("function Assert-DbPrivilegeContract") : text.index("$primaryError")]
    assert '"scripts\\check_db_privileges.ps1"' in helper
    assert "DB_PRIVILEGES_OK matrix_checks=651 actual_denials=23 allowed_smokes=10" in helper
    assert "privilegeExit -ne 0" in helper
    assert "exact 7-privilege B5 contract" in helper
    call = text.index("Assert-DbPrivilegeContract -Database $restoreDatabase")
    round_trip = text.index("round-trip-smoke", call)
    assert call < round_trip
    assert "Cleanup also reported" in text


def test_api_image_contains_current_and_rollback_manifests() -> None:
    text = API_DOCKERFILE.read_text(encoding="utf-8")

    assert "scripts/research_core_rp_b5_1_manifest.sha256" in text
    assert "scripts/research_core_rp_a5_manifest.sha256" in text
    assert "scripts/research_core_rp_a4_manifest.sha256" in text
    assert "scripts/research_core_rp_a3_manifest.sha256" in text
    assert "scripts/research_core_rp_a2_manifest.sha256" in text
