from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "a6_b5_rollback_drill.ps1"


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
        "$B5CheckpointRoot",
        "$VerifiedBackupPath",
        "$VerifiedBackupSha256",
    ):
        assert parameter in params
    assert text.count("[Parameter(Mandatory = $true)]") == 10
    assert "LeaveAtB5" not in text
    assert "LeaveAtA6" not in text
    assert (
        '"pcr-tw-b5-gacha", "pcr-tw-a5-arena", "pcr-tw-a4-water", "pcr-tw-b1"'
        in text
    )
    assert '"--project-name", $ProjectName' in text
    assert '"--profile", "verification"' in text
    assert "function Assert-ComposePreflight" in text
    assert "function Assert-RunningDbIdentity" in text
    assert "com.docker.compose.project" in text
    assert '"${ProjectName}_pg_data"' in text


def test_release_pins_and_shared_v4_closure_are_exact() -> None:
    text = source()
    for digest in (
        "fbcac9cb9aadcd1569f881469189dc791c68a4a329637cc9db2c0d7263d68ed1",
        "3f5e738a6a7f0463583b38d0fc2ca1ae35bdc563f3815cf436dfc10913764d97",
        "82495781cca66b9ca3fc221e609a3cb6c06ebaa823f7a8613c9d5d1d01d9e1ee",
        "e44a9fa38a89a5672d00c0a58d8b8946fecd41e541c08c9733fb3d06fbc1b88a",
        "e74814d6433ee327611f10322937bdfa9687b9887f139ba6e6158a291dd12989",
        "d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d",
        "a7467a838c2a9cfdfe48bda4a3b158fb374dd023caa3478a84c07678532ea9f4",
        "a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af",
        "24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c",
    ):
        assert digest in text
    for marker in (
        "$rowCounts = [ordered]@{",
        "$servingCounts = [ordered]@{",
        "evidence = 73",
        "claims = 69",
        "claim_evidence = 159",
        "gacha_timeline_events = 5",
        "gacha_timeline_evidence = 10",
        "gacha_timeline_claims = 8",
        "gacha_community_sources = 4",
        "gacha_timeline_community_sources = 0",
        "SUCCEEDED|48|13|376|120",
        "research_core_file_ssot|4|$MaterializationSha256|23",
    ):
        assert marker in text
    assert "A6_B5_MANIFEST_INPUTS_OK" in text
    assert "artifact_diagnostic=$a6ArtifactMirrorSha256" in text


def test_backup_and_both_manifest_files_are_verified_before_side_effects() -> None:
    text = source()
    backup_hash = text.index("Verified backup SHA-256 mismatch")
    b5_manifest_hash = text.index("$actualB5ManifestSha256")
    a6_manifest_hash = text.index("$actualA6ManifestSha256")
    receipt = text.index("VERIFIED_BACKUP_INPUT_OK", backup_hash)
    preflight_call = text.index("Assert-ComposePreflight\nInvoke-Compose ps")
    stop = text.index("Invoke-Compose stop web api scheduler", preflight_call)
    assert "Get-FileHash -LiteralPath $VerifiedBackupPath -Algorithm SHA256" in text[:receipt]
    assert backup_hash < b5_manifest_hash < a6_manifest_hash < receipt < preflight_call < stop


def test_preflight_pins_images_ports_network_and_shadow_mode() -> None:
    text = source()
    preflight = text[text.index("function Assert-ComposePreflight") :]
    for service in ("api", "importer", "role-provision", "revision-history-verify"):
        assert f'"{service}"' in preflight
    assert "$service.image" not in preflight  # calls resolve each service directly
    assert "ExpectedApiImage" in preflight
    assert "ExpectedSchedulerImage" in preflight
    assert "Assert-LoopbackPort $api 8000 $ExpectedApiPort" in preflight
    assert "Assert-LoopbackPort $web 3000 $ExpectedWebPort" in preflight
    assert "Assert-LoopbackPort $scheduler 8081 $ExpectedSchedulerPort" in preflight
    assert "$null -ne $db.ports" in preflight
    assert "$config.networks.backend.internal" in preflight
    assert '$scheduler.environment.SCHEDULER_ENABLED -cne "false"' in preflight
    assert '$scheduler.environment.SHADOW_MODE -cne "true"' in preflight
    assert '$scheduler.environment.AUTO_PUBLISH -cne "false"' in preflight


def test_origin_and_immutable_b5_release_input_are_closed_before_stop() -> None:
    text = source()
    origin_state = text.index("Assert-A6State $originA6ImportRun", text.index("try {"))
    b5_history_count = text.index("$b5HistoryCount", origin_state)
    exact_history = text.index(
        "Assert-RevisionIdentity $b5Revision $b5ManifestSha256 $b5Semantic",
        b5_history_count,
    )
    release_marker = text.index("B5_IMMUTABLE_RELEASE_INPUT_OK", exact_history)
    absent_branch = text.index("history=absent expected_create=true", release_marker)
    origin_anchor = text.index("Assert-OriginAnchor", absent_branch)
    readiness = text.index("Assert-A6PublicReadiness", origin_anchor)
    acl = text.index("Assert-DbPrivilegeContract", readiness)
    epoch = text.index("$epochAfterReadiness", acl)
    stop = text.index("Invoke-Compose stop web api scheduler", epoch)
    assert origin_state < b5_history_count < exact_history < release_marker < absent_branch < origin_anchor < readiness < acl < epoch < stop
    assert "Existing immutable B5 release evidence is incomplete" in text
    assert "history=present expected_create=false" in text
    assert "files=48 csv=13 rows=376 edges=120/298" in text


def test_rollback_is_same_schema_and_never_invokes_alembic() -> None:
    text = source()
    lower = text.lower()
    assert "alembic -c" not in lower
    assert " downgrade " not in lower
    assert " upgrade " not in lower
    assert '"migration"' not in text[text.index("function Assert-ComposePreflight") :]
    assert text.count('"v0007_gacha_timeline_slice"') >= 2
    rollback_state = text.index("Assert-B5State $b5ImportRun $b5Materialization")
    marker = text.index("A6_B5_SAME_SCHEMA_ROLLBACK_OK", rollback_state)
    restore = text.index("Restore-A6", marker)
    assert rollback_state < marker < restore
    assert "migration_commands=0" in text[marker:restore]


def test_pinned_b5_import_accepts_only_exact_existing_or_first_materialization() -> None:
    text = source()
    stop = text.index("Invoke-Compose stop web api scheduler")
    recovery_armed = text.index("$needsA6Restore = $true", stop)
    importer = text.index("$rollbackOutput = & docker", recovery_armed)
    assert stop < recovery_armed < importer
    rollback = text[importer : text.index("Restore-A6", importer)]
    assert "${B5CheckpointRoot}:/rollback:ro" in text
    assert "--research-core /rollback/research_core/pcr_tw_project" in rollback
    assert "--manifest /app/scripts/research_core_rp_b5_1_manifest.sha256" in rollback
    assert "--manifest-sha256 $b5ManifestSha256" in rollback
    assert 'Get-PinnedB5SourceProof $rollbackOutput "RP-B5 activation"' in rollback
    assert "$b5Result.created -ne $b5ExpectedCreated" in rollback
    assert "$b5Result.activated -ne $true" in rollback
    assert '$b5ImportRun = [string]$b5Result.import_run_id' in rollback
    assert "RP-B5 import did not establish immutable release evidence" in rollback


def test_checkpoint_tree_is_fully_verified_before_service_stop_boundary() -> None:
    text = source()
    helper = text[
        text.index("function Get-PinnedB5SourceProof") :
        text.index("function Assert-RevisionIdentity")
    ]
    for marker in (
        '"PINNED_ROLLBACK_SOURCE_OK"',
        "$lines.Count -ne 1",
        "$proof.manifest_sha256 -ne $b5ManifestSha256",
        "$proof.revision_id -ne $b5Revision",
        "[int]$proof.file_count -ne 48",
        "[int]$proof.csv_row_count -ne 376",
    ):
        assert marker in helper
    assert "csv_file_count" not in helper  # verifier proof does not emit this field

    verifier_code = text.index("$b5SourceVerifierCode =")
    preflight_run = text.index("$preflightProofOutput = & docker", verifier_code)
    verify_call = text.index("python -c $b5SourceVerifierCode", preflight_run)
    proof_parse = text.index(
        'Get-PinnedB5SourceProof $preflightProofOutput "RP-B5 checkpoint preflight"',
        verify_call,
    )
    state = text.index("Assert-A6State $originA6ImportRun", proof_parse)
    sequence_guard = text.index("$sequenceAfterCheckpointProof", state)
    marker = text.index("B5_CHECKPOINT_PREFLIGHT_OK", sequence_guard)
    stopped_guard = text.index("$servicesStopped = $true", marker)
    stop = text.index("Invoke-Compose stop web api scheduler", stopped_guard)
    assert verifier_code < preflight_run < verify_call < proof_parse < state < sequence_guard < marker < stopped_guard < stop
    code_line = text[text.index("$b5SourceVerifierCode =") : preflight_run]
    assert "_verify_import_source" in code_line
    assert "create_engine" not in code_line
    assert "import_pve_projection" not in code_line
    assert "--no-deps" in text[preflight_run:verify_call]
    assert "--volume $checkpointMount" in text[preflight_run:verify_call]


def test_activation_audit_is_exact_monotonic_and_two_step() -> None:
    text = source()
    assert 'ROLLBACK = "rollback to earlier verified immutable revision"' in text
    assert 'REACTIVATE = "reactivate later verified immutable revision"' in text
    assert "pcr_pipeline.import_pve" in text
    assert "($originActivationSequence + 1) $a6Revision $b5Revision" in text
    assert "($originActivationSequence + 2) $b5Revision $a6Revision" in text
    assert "$rollbackEpoch -le $originEpoch" in text
    assert "$reactivateEpoch -le $rollbackEpoch" in text
    assert "$stateEpoch -ne $reactivateEpoch" in text
    assert "$b5Sequence -ne ($originActivationSequence + 1)" in text
    assert "$b5Epoch -le $originEpoch" in text


def test_recovery_accepts_only_origin_b5_intermediate_or_exact_restored_a6() -> None:
    text = source()
    assert 'return "ORIGIN_NOOP"' in text
    assert 'return "ALREADY_RESTORED_NOOP"' in text
    assert 'return "B5_REACTIVATE"' in text
    assert 'throw "Recovery state is neither origin A6, exact B5 rollback, nor restored A6"' in text
    assert '$expectedActivated = $mode -eq "B5_REACTIVATE"' in text
    assert "Assert-RecoveryChain" in text
    assert "if ($needsA6Restore -and $intermediateServicesMayRun)" in text
    assert "if ($needsA6Restore -and -not $intermediateServicesMayRun)" in text
    assert "SERVICES_LEFT_QUIESCED" in text
    assert "manual recovery from the verified backup" in text


def test_acl_contract_runs_before_mutation_and_after_role_reapply() -> None:
    text = source()
    helper = text[text.index("function Assert-DbPrivilegeContract") : text.index("function Assert-CountObject")]
    assert '"scripts\\check_db_privileges.ps1"' in helper
    assert "DB_PRIVILEGES_OK matrix_checks=651 actual_denials=23 allowed_smokes=10" in helper
    assert "exact 7-privilege A6 contract" in helper
    origin_acl = text.index("Assert-DbPrivilegeContract", text.index("try {"))
    stop = text.index("Invoke-Compose stop web api scheduler", origin_acl)
    restore = text.index("function Restore-A6")
    roles = text.index("Invoke-Compose run --rm --no-deps role-provision", restore)
    restore_acl = text.index("Assert-DbPrivilegeContract", roles)
    importer = text.index("$output = & docker", restore_acl)
    restored_state = text.index("Assert-A6State $originA6ImportRun", importer)
    final_acl = text.index("Assert-DbPrivilegeContract", restored_state)
    assert origin_acl < stop
    assert roles < restore_acl < importer
    assert importer < restored_state < final_acl


def test_public_readiness_pins_a6_and_b5_instance_gacha_web_and_scheduler() -> None:
    text = source()
    readiness = text[text.index("function Assert-PublicReadiness") : text.index("function Assert-OriginAnchor")]
    for marker in (
        '"3.0.0-a6"',
        "/api/v1/gacha/timeline",
        "/api/v1/gacha/community-sources",
        "/gacha",
        "$baseline.meta.source.revision_id -ne $ExpectedRevision",
        "$baseline.meta.source.import_run_id -ne $ExpectedImportRun",
        "$baseline.meta.source.materialization_sha256 -ne $ExpectedMaterialization",
        'Assert-CountObject $baseline.data.counts $rowCounts "$Label public baseline"',
        "$gachaRows.Count -ne 5",
        "@($community.data).Count -ne 4",
        '"CLM-SHEFI-POOL"',
        '"CLM-LUISE-DATE"',
        '"CLM-JP-FUBUKI-DATE"',
        '"YES", "YES", "YES", "UNKNOWN", "UNKNOWN"',
        "抽卡未來視",
        "限定身分 UNKNOWN",
        "scheduler.canonical_write_capable",
    ):
        assert marker in readiness
    assert "Assert-PublicReadiness $a6Revision $a6Semantic $originA6ImportRun $originA6Materialization \"A6\"" in readiness
    assert "Assert-PublicReadiness $b5Revision $b5Semantic $b5ImportRun $b5Materialization \"B5\"" in readiness


def test_b5_intermediate_services_are_ready_then_requiesced_before_restore() -> None:
    text = source()
    rollback_marker = text.index("A6_B5_SAME_SCHEMA_ROLLBACK_OK")
    may_run = text.index("$intermediateServicesMayRun = $true", rollback_marker)
    up = text.index("Invoke-Compose up --detach --no-build --wait --wait-timeout 90 --no-deps", may_run)
    readiness = text.index("Assert-B5PublicReadiness", up)
    state = text.index("Assert-B5State $b5ImportRun $b5Materialization", readiness)
    sequence = text.index("$b5ServingSequence", state)
    marker = text.index("B5_INTERMEDIATE_SERVICES_READY_OK", sequence)
    stop = text.index("Invoke-Compose stop web api scheduler", marker)
    stopped_guard = text.index("$intermediateServicesMayRun = $false", stop)
    post_stop_state = text.index("Assert-B5State $b5ImportRun $b5Materialization", stopped_guard)
    restore = text.index("Restore-A6", post_stop_state)
    assert rollback_marker < may_run < up < readiness < state < sequence < marker < stop < stopped_guard < post_stop_state < restore

    finally_block = text[text.index("finally {") :]
    recovery_stop = finally_block.index("if ($needsA6Restore -and $intermediateServicesMayRun)")
    stop_again = finally_block.index("Invoke-Compose stop web api scheduler", recovery_stop)
    restore_gate = finally_block.index("if ($needsA6Restore -and -not $intermediateServicesMayRun)", stop_again)
    restore_again = finally_block.index("Restore-A6", restore_gate)
    assert recovery_stop < stop_again < restore_gate < restore_again


def test_services_restart_only_after_exact_a6_and_final_epoch_guards() -> None:
    text = source()
    restart_gate = text.index("if ($servicesStopped -and -not $needsA6Restore)")
    state = text.index("Assert-A6State $originA6ImportRun", restart_gate)
    up = text.index("Invoke-Compose up --detach --no-build --wait --wait-timeout 90 --no-deps", state)
    readiness = text.index("Assert-A6PublicReadiness", up)
    history = text.index("revision-history-verify", readiness)
    final_epoch = text.index("$finalEpoch", history)
    chain = text.index("Assert-RecoveryChain", final_epoch)
    marker = text.index("A6_SERVICES_READY_OK", chain)
    assert restart_gate < state < up < readiness < history < final_epoch < chain < marker
    final_block = text[state:marker]
    assert "$preRestartSequence -eq $originActivationSequence" in final_block
    assert "$preRestartEpoch -eq $originEpoch" in final_block
    assert "$preRestartSequence -eq ($originActivationSequence + 2)" in final_block
    assert 'Assert-OriginAnchor\n                $finalChronology = "ORIGIN_NOOP"' in final_block
    assert 'Assert-RecoveryChain\n                $finalChronology = "ROLLBACK_REACTIVATE"' in final_block
    assert "$finalSequence -ne $preRestartSequence" in final_block
    assert "$finalEpoch -ne $preRestartEpoch" in final_block
    assert "A6_B5_ROLLBACK_DRILL_OK" in text
