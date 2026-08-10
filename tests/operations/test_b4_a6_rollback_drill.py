from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "b4_a6_rollback_drill.ps1"


def source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_drill_requires_exact_target_checkpoint_and_verified_backup() -> None:
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
        "$A6CheckpointRoot",
        "$VerifiedBackupPath",
        "$VerifiedBackupSha256",
    ):
        assert parameter in params
    assert text.count("[Parameter(Mandatory = $true)]") == 10
    assert "LeaveAtA6" not in text
    assert "LeaveAtB4" not in text
    for reserved_project in (
        "pcr-tw-a6",
        "pcr-tw-a6-parena",
        "pcr-tw-a6-parena-serial",
        "pcr-tw-a6-parena-drill",
        "pcr-tw-b5-gacha",
        "pcr-tw-a5-arena",
        "pcr-tw-a4-water",
        "pcr-tw-a3-fire",
        "pcr-tw-b1",
        "pcr-tw-b1-final",
    ):
        assert f'"{reserved_project}"' in text
    assert '"--project-name", $ProjectName' in text
    assert '"--profile", "verification"' in text
    assert "function Assert-ComposePreflight" in text
    assert "function Assert-RunningDbIdentity" in text
    assert "com.docker.compose.project" in text
    assert '"$($ProjectName)_pg_data"' in text


def test_backup_and_both_manifests_are_verified_before_compose_or_database() -> None:
    text = source()
    backup_hash = text.index("Verified backup SHA-256 mismatch")
    a6_manifest_hash = text.index("$actualA6ManifestSha256")
    b4_manifest_hash = text.index("$actualB4ManifestSha256")
    receipt = text.index("VERIFIED_BACKUP_INPUT_OK", b4_manifest_hash)
    preflight_call = text.index("Assert-ComposePreflight\nInvoke-Compose ps")
    first_query = text.index("$originB4ImportRun =", preflight_call)
    assert "Get-FileHash -LiteralPath $VerifiedBackupPath -Algorithm SHA256" in text[:receipt]
    assert backup_hash < a6_manifest_hash < b4_manifest_hash < receipt
    assert receipt < preflight_call < first_query


def test_release_pins_schema_versions_and_count_closures_are_exact() -> None:
    text = source()
    for digest in (
        "eda30340c02f2f470475e652786104c521faf2ea4cc20be44cf09f3798fe8c5f",
        "1ba25a73df01ca8d9b161c60836d997f6db202a18d140ee1e92a7d96f62d7a17",
        "46000a4a6f9ee70067876c7c1a73fd61d4d06a6f93c5b61831c15d41c9d8811e",
        "bb71dce87b8a651de794672741a5481a6b754861d694561974ce534e17eb9720",
        "fbcac9cb9aadcd1569f881469189dc791c68a4a329637cc9db2c0d7263d68ed1",
        "3f5e738a6a7f0463583b38d0fc2ca1ae35bdc563f3815cf436dfc10913764d97",
        "82495781cca66b9ca3fc221e609a3cb6c06ebaa823f7a8613c9d5d1d01d9e1ee",
        "e44a9fa38a89a5672d00c0a58d8b8946fecd41e541c08c9733fb3d06fbc1b88a",
    ):
        assert digest in text
    for marker in (
        "$a6RowCounts = [ordered]@{",
        "$a6PublicRowCounts = [ordered]@{}",
        "$a6ServingCounts = [ordered]@{",
        "$b4RowCounts = [ordered]@{",
        "$b4ServingCounts = [ordered]@{",
        "arena_source_records = 6",
        "parena_cases = 0",
        "parena_case_matchups = 0",
        "parena_case_sources = 0",
        "parena_case_evidence = 0",
        "parena_case_claims = 0",
        "$SchemaVersion|$MaterializationSha256|$TableCount",
        'Assert-B4State $originB4ImportRun $originB4Materialization',
        '"v0008_parena_planner_slice"',
        '"v0007_gacha_timeline_slice"',
    ):
        assert marker in text
    assert '5 29 $b4RowCounts' in text
    assert '4 23 $a6RowCounts' in text


def test_a6_public_baseline_zero_fills_v5_fields_without_widening_v4_identity() -> None:
    text = source()
    count_setup = text[text.index("$a6RowCounts = [ordered]@{") : text.index("$a6ServingCounts = [ordered]@{")]
    assert "foreach ($name in $a6RowCounts.Keys)" in count_setup
    assert "$a6PublicRowCounts[$name] = $a6RowCounts[$name]" in count_setup
    assert "foreach ($table in $parenaTables)" in count_setup
    assert "$a6PublicRowCounts[$table] = 0" in count_setup

    public_helper = text[
        text.index("function Assert-A6PublicReadiness") :
        text.index("function Invoke-Migration")
    ]
    assert "$a6Materialization $a6ExpectedApplicationVersion $a6PublicRowCounts $false" in public_helper
    assert "$a6Materialization $a6ExpectedApplicationVersion $a6RowCounts $false" not in public_helper

    # Immutable ImportResult/DB identity remains the exact v4 closure.
    assert '4 23 $a6RowCounts' in text
    assert 'Assert-CountObject $a6Result.row_counts $a6RowCounts "RP-A6 ImportResult"' in text


def test_public_application_version_follows_exact_b4_or_immutable_a6_provenance() -> None:
    text = source()
    public = text[
        text.index("function Assert-PublicReadiness") :
        text.index("function Invoke-Migration")
    ]
    assert "[string]$ExpectedApplicationVersion" in public
    assert "$baseline.data.application_version -ne $ExpectedApplicationVersion" in public
    assert '$originB4Materialization "3.0.0-b4" $b4RowCounts $true' in public
    assert "$a6Materialization $a6ExpectedApplicationVersion $a6PublicRowCounts $false" in public

    history = text[text.index('$a6ExpectedApplicationVersion = "3.0.0-b4"') :]
    assert "SELECT COALESCE(application_version, '') FROM import_runs" in history
    assert '$a6ExpectedApplicationVersion -notin @("3.0.0-a6", "3.0.0-b4")' in history
    assert "application_version=$a6ExpectedApplicationVersion" in history


def test_preflight_pins_images_ports_network_shadow_and_origin_readiness() -> None:
    text = source()
    preflight = text[text.index("function Assert-ComposePreflight") :]
    for service in (
        "api",
        "importer",
        "migration",
        "role-provision",
        "revision-history-verify",
        "scheduler",
        "scheduler-smoke",
    ):
        assert f'"{service}"' in preflight
    assert "Assert-LoopbackPort $api 8000 $ExpectedApiPort" in preflight
    assert "Assert-LoopbackPort $web 3000 $ExpectedWebPort" in preflight
    assert "Assert-LoopbackPort $scheduler 8081 $ExpectedSchedulerPort" in preflight
    assert "$config.networks.backend.internal" in preflight
    assert '$scheduler.environment.SCHEDULER_ENABLED -cne "false"' in preflight
    assert '$scheduler.environment.SHADOW_MODE -cne "true"' in preflight
    assert '$scheduler.environment.AUTO_PUBLISH -cne "false"' in preflight

    origin = text.index("try {")
    state = text.index("Assert-B4State $originB4ImportRun", origin)
    anchor = text.index("Assert-OriginAnchor", state)
    readiness = text.index("Assert-B4PublicReadiness", anchor)
    acl = text.index("Assert-DbPrivilegeContract", readiness)
    epoch = text.index("$epochAfterReadiness", acl)
    checkpoint = text.index("$preflightProofOutput = & docker", epoch)
    stopped = text.index("$servicesStopped = $true", checkpoint)
    assert state < anchor < readiness < acl < epoch < checkpoint < stopped
    assert "Get-ActualPort" in text[text.index("function Assert-PublicReadiness") : readiness]


def test_checkpoint_tree_is_fully_verified_before_services_stopped_flag() -> None:
    text = source()
    helper = text[
        text.index("function Get-PinnedA6SourceProof") :
        text.index("function Assert-RevisionIdentity")
    ]
    for marker in (
        '"PINNED_ROLLBACK_SOURCE_OK"',
        "$lines.Count -ne 1",
        "$proof.manifest_sha256 -ne $a6ManifestSha256",
        "$proof.revision_id -ne $a6Revision",
        "[int]$proof.file_count -ne 48",
        "[int]$proof.csv_row_count -ne 376",
    ):
        assert marker in helper
    verifier_code = text.index("$a6SourceVerifierCode =")
    preflight_run = text.index("$preflightProofOutput = & docker", verifier_code)
    verify_call = text.index("python -c $a6SourceVerifierCode", preflight_run)
    proof_parse = text.index("Get-PinnedA6SourceProof $preflightProofOutput", verify_call)
    origin_state = text.index("Assert-B4State $originB4ImportRun", proof_parse)
    epoch_guard = text.index("$epochAfterCheckpointProof", origin_state)
    marker = text.index("A6_CHECKPOINT_PREFLIGHT_OK", epoch_guard)
    stopped = text.index("$servicesStopped = $true", marker)
    stop = text.index("Invoke-Compose stop web api scheduler", stopped)
    assert verifier_code < preflight_run < verify_call < proof_parse
    assert proof_parse < origin_state < epoch_guard < marker < stopped < stop
    assert "_verify_import_source" in text[verifier_code:preflight_run]
    assert "--volume $checkpointMount" in text[preflight_run:verify_call]


def test_a6_activation_clears_exact_six_tables_before_guarded_downgrade() -> None:
    text = source()
    activation = text.index("$rollbackOutput = & docker")
    result = text.index("$a6Result = Get-ImportResult", activation)
    state_v8 = text.index("Assert-A6StateAtV8 $a6ImportRun", result)
    acl = text.index("Assert-DbPrivilegeContract", state_v8)
    chronology = text.index("Assert-Activation $a6Sequence", acl)
    guard_state = text.index("Assert-A6StateAtV8 $a6ImportRun", chronology)
    downgrade = text.index('Invoke-Migration "downgrade" "v0007_gacha_timeline_slice"', guard_state)
    state_v7 = text.index("Assert-A6StateAtV7 $a6ImportRun", downgrade)
    assert activation < result < state_v8 < acl < chronology < guard_state < downgrade < state_v7
    assert "$parenaTables = @(" in text
    for table in (
        "arena_source_records",
        "parena_cases",
        "parena_case_matchups",
        "parena_case_sources",
        "parena_case_evidence",
        "parena_case_claims",
    ):
        assert text.count(f'"{table}"') >= 1
    assert 'Assert-ParenaTableShape $true 0 "A6 at V0008"' not in text
    assert '$a6ServingCounts $true 0 "A6 at V0008"' in text
    assert "B4_A6_SCHEMA_DOWNGRADE_OK" in text


def test_a6_v7_public_readiness_requires_real_503_then_services_stop() -> None:
    text = source()
    readiness = text[text.index("function Assert-PublicReadiness") : text.index("function Invoke-Migration")]
    for marker in (
        "/api/v1/parena/environments",
        "/api/v1/solver/parena",
        "$parenaEnvironments.StatusCode -ne 503",
        "$parenaSolver.StatusCode -ne 503",
        '"NO_PARENA_MATERIALIZATION"',
        "/parena",
        "scheduler.canonical_write_capable",
        '"3.0.0-b4"',
        "$gachaRows.Count -ne 5",
        "@($community.data).Count -ne 4",
    ):
        assert marker in readiness
    assert '$parenaSolver.Payload.data.match_type -ne "EXACT"' in readiness
    assert '[bool]$parenaSolver.Payload.data.similar_enabled' in readiness
    downgrade_marker = text.index("B4_A6_SCHEMA_DOWNGRADE_OK")
    may_run = text.index("$intermediateServicesMayRun = $true", downgrade_marker)
    up = text.index("Invoke-Compose up --detach --no-build --wait", may_run)
    public = text.index("Assert-A6PublicReadiness", up)
    state = text.index("Assert-A6StateAtV7", public)
    ready_marker = text.index("A6_INTERMEDIATE_SERVICES_READY_OK", state)
    stop = text.index("Invoke-Compose stop web api scheduler", ready_marker)
    assert downgrade_marker < may_run < up < public < state < ready_marker < stop


def test_v7_to_v8_upgrade_precedes_b4_reactivation_and_final_acl() -> None:
    text = source()
    intermediate_stop = text.index("A6_INTERMEDIATE_SERVICES_STOPPED_OK")
    upgrade = text.index('Invoke-Migration "upgrade" "head"', intermediate_stop)
    state_v8 = text.index("Assert-A6StateAtV8", upgrade)
    upgrade_marker = text.index("A6_B4_SCHEMA_UPGRADE_OK", state_v8)
    restore = text.index("Restore-B4", upgrade_marker)
    assert intermediate_stop < upgrade < state_v8 < upgrade_marker < restore
    restore_fn = text[text.index("function Restore-B4") : text.index("Assert-ComposePreflight\n")]
    role = restore_fn.index("role-provision")
    acl_before = restore_fn.index("Assert-DbPrivilegeContract", role)
    importer = restore_fn.index("$output = & docker", acl_before)
    b4_state = restore_fn.index("Assert-B4State", importer)
    acl_after = restore_fn.index("Assert-DbPrivilegeContract", b4_state)
    assert role < acl_before < importer < b4_state < acl_after
    assert "DB_PRIVILEGES_OK matrix_checks=777 actual_denials=26 allowed_smokes=12" in text


def test_activation_chronology_is_exact_monotonic_two_step() -> None:
    text = source()
    assert 'ROLLBACK = "rollback to earlier verified immutable revision"' in text
    assert 'REACTIVATE = "reactivate later verified immutable revision"' in text
    assert "($originActivationSequence + 1) $b4Revision $a6Revision" in text
    assert "($originActivationSequence + 2) $a6Revision $b4Revision" in text
    assert "$rollbackEpoch -le $originEpoch" in text
    assert "$reactivateEpoch -le $rollbackEpoch" in text
    assert "$stateEpoch -ne $reactivateEpoch" in text
    assert "$a6Sequence -ne ($originActivationSequence + 1)" in text
    assert "$a6Epoch -le $originEpoch" in text


def test_recovery_accepts_only_origin_a6_intermediate_or_exact_restored_b4() -> None:
    text = source()
    assert 'return "ORIGIN_NOOP"' in text
    assert 'return "ALREADY_RESTORED_NOOP"' in text
    assert 'return "A6_REACTIVATE"' in text
    assert 'throw "Recovery state is neither origin B4, exact A6 rollback, nor restored B4"' in text
    assert '$expectedActivated = $mode -eq "A6_REACTIVATE"' in text
    assert "if ($needsB4Restore -and $intermediateServicesMayRun)" in text
    assert "if ($needsB4Restore -and -not $intermediateServicesMayRun)" in text
    assert "SERVICES_LEFT_QUIESCED" in text
    assert "manual recovery from the verified backup" in text
    recovery = text[text.index("function Get-RecoveryMode") : text.index("function Restore-B4")]
    assert 'if ($alembic -eq "v0007_gacha_timeline_slice")' in recovery
    assert 'Invoke-Migration "upgrade" "head"' in recovery
    assert 'elseif ($alembic -eq "v0008_parena_planner_slice")' in recovery


def test_final_restart_requires_exact_b4_origin_or_plus_two_chain() -> None:
    text = source()
    restart_gate = text.index("if ($servicesStopped -and -not $needsB4Restore)")
    state = text.index("Assert-B4State $originB4ImportRun", restart_gate)
    chronology = text.index("$preRestartSequence", state)
    up = text.index("Invoke-Compose up --detach --no-build --wait", chronology)
    readiness = text.index("Assert-B4PublicReadiness", up)
    acl = text.index("Assert-DbPrivilegeContract", readiness)
    history = text.index("revision-history-verify", acl)
    final_epoch = text.index("$finalEpoch", history)
    marker = text.index("B4_SERVICES_READY_OK", final_epoch)
    assert restart_gate < state < chronology < up < readiness < acl < history < final_epoch < marker
    block = text[state:marker]
    assert "$preRestartSequence -eq $originActivationSequence" in block
    assert "$preRestartEpoch -eq $originEpoch" in block
    assert "$preRestartSequence -eq ($originActivationSequence + 2)" in block
    assert "$finalSequence -ne $preRestartSequence" in block
    assert "$finalEpoch -ne $preRestartEpoch" in block
    assert "B4_A6_ROLLBACK_DRILL_OK" in text
