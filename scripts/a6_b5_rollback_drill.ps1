[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$EnvFile,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9_-]{0,62}$')]
    [string]$ProjectName,
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ExpectedApiImage,
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ExpectedSchedulerImage,
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 65535)]
    [int]$ExpectedApiPort,
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 65535)]
    [int]$ExpectedWebPort,
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 65535)]
    [int]$ExpectedSchedulerPort,
    [Parameter(Mandatory = $true)]
    [string]$B5CheckpointRoot,
    [Parameter(Mandatory = $true)]
    [string]$VerifiedBackupPath,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{64}$')]
    [string]$VerifiedBackupSha256
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$composeFile = Join-Path $repoRoot "infra\compose.yml"
$EnvFile = [System.IO.Path]::GetFullPath($EnvFile)
$B5CheckpointRoot = [System.IO.Path]::GetFullPath($B5CheckpointRoot)
$VerifiedBackupPath = [System.IO.Path]::GetFullPath($VerifiedBackupPath)
$b5Core = Join-Path $B5CheckpointRoot "research_core\pcr_tw_project"
$b5Manifest = Join-Path $repoRoot "scripts\research_core_rp_b5_1_manifest.sha256"
$a6Manifest = Join-Path $repoRoot "scripts\research_core_rp_a6_0_manifest.sha256"

if ($ProjectName -in @("pcr-tw-b5-gacha", "pcr-tw-a5-arena", "pcr-tw-a4-water", "pcr-tw-b1")) {
    throw "ProjectName is reserved for an existing or legacy stack"
}
foreach ($requiredFile in @($EnvFile, $b5Manifest, $a6Manifest, $VerifiedBackupPath)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Missing A6 rollback drill input: $requiredFile"
    }
}
if (-not (Test-Path -LiteralPath $b5Core -PathType Container)) {
    throw "Missing immutable RP-B5 research core: $b5Core"
}

$a6ManifestSha256 = "fbcac9cb9aadcd1569f881469189dc791c68a4a329637cc9db2c0d7263d68ed1"
$a6Revision = "3f5e738a6a7f0463583b38d0fc2ca1ae35bdc563f3815cf436dfc10913764d97"
$a6Semantic = "82495781cca66b9ca3fc221e609a3cb6c06ebaa823f7a8613c9d5d1d01d9e1ee"
$a6ArtifactMirrorSha256 = "e44a9fa38a89a5672d00c0a58d8b8946fecd41e541c08c9733fb3d06fbc1b88a"
$b5ManifestSha256 = "e74814d6433ee327611f10322937bdfa9687b9887f139ba6e6158a291dd12989"
$b5Revision = "d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d"
$b5Semantic = "a7467a838c2a9cfdfe48bda4a3b158fb374dd023caa3478a84c07678532ea9f4"
$evidenceToClaimSha256 = "a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af"
$claimToEvidenceSha256 = "24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c"

# A6 changes research-gate semantics only. B5 and A6 intentionally share the
# V0007/v4 typed materialization shape and exact serving closure.
$rowCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 73; claims = 69; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
    gacha_timeline_events = 5; gacha_timeline_evidence = 10; gacha_timeline_claims = 8
    gacha_community_sources = 4; gacha_timeline_community_sources = 0
}
$servingCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 73; claims = 69; stage_evidence = 47; stage_claims = 46
    team_evidence = 95; claim_evidence = 159; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
    gacha_timeline_events = 5; gacha_timeline_evidence = 10; gacha_timeline_claims = 8
    gacha_community_sources = 4; gacha_timeline_community_sources = 0
}

# Backup verification is deliberately completed before Compose preflight or any
# service/database mutation. A failed drill therefore always has a pre-verified
# manual recovery artifact before the rollback boundary is crossed.
$backupFile = Get-Item -LiteralPath $VerifiedBackupPath
if ($backupFile.Length -lt 1) { throw "Verified backup file is empty" }
$actualBackupSha256 = (Get-FileHash -LiteralPath $VerifiedBackupPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualBackupSha256 -ne $VerifiedBackupSha256.ToLowerInvariant()) {
    throw "Verified backup SHA-256 mismatch"
}
$actualB5ManifestSha256 = (Get-FileHash -LiteralPath $b5Manifest -Algorithm SHA256).Hash.ToLowerInvariant()
$actualA6ManifestSha256 = (Get-FileHash -LiteralPath $a6Manifest -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualB5ManifestSha256 -ne $b5ManifestSha256 -or $actualA6ManifestSha256 -ne $a6ManifestSha256) {
    throw "Release manifest file SHA-256 mismatch"
}
Write-Host "VERIFIED_BACKUP_INPUT_OK sha256=$actualBackupSha256 bytes=$($backupFile.Length)"
Write-Host "A6_B5_MANIFEST_INPUTS_OK a6=$actualA6ManifestSha256 b5=$actualB5ManifestSha256 artifact_diagnostic=$a6ArtifactMirrorSha256"

function Get-Setting {
    param([string]$Name, [string]$Default = "")
    $processValue = [Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($processValue)) { return $processValue.Trim() }
    foreach ($line in Get-Content -LiteralPath $EnvFile) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
        $prefix = "$Name="
        if ($trimmed.StartsWith($prefix, [StringComparison]::Ordinal)) {
            return $trimmed.Substring($prefix.Length).Trim().Trim('"').Trim("'")
        }
    }
    return $Default
}

$postgresUser = Get-Setting -Name "POSTGRES_USER" -Default "pcr_owner"
$postgresDatabase = Get-Setting -Name "POSTGRES_DB" -Default "pcr_tw"
$schedulerEnabled = (Get-Setting -Name "SCHEDULER_ENABLED" -Default "false").ToLowerInvariant()
$shadowMode = (Get-Setting -Name "SHADOW_MODE" -Default "true").ToLowerInvariant()
$autoPublish = (Get-Setting -Name "AUTO_PUBLISH" -Default "false").ToLowerInvariant()
if ($postgresUser -notmatch '^[a-zA-Z][a-zA-Z0-9_]{0,62}$' -or $postgresDatabase -notmatch '^[a-zA-Z][a-zA-Z0-9_]{0,40}$') {
    throw "Database owner or database name contains unsupported characters"
}
if ($schedulerEnabled -ne "false" -or $shadowMode -ne "true" -or $autoPublish -ne "false") {
    throw "Scheduler must remain disabled in Shadow Mode with auto-publish off during rollback"
}
$compose = @(
    "compose", "--project-name", $ProjectName,
    "--profile", "verification",
    "--env-file", $EnvFile, "-f", $composeFile
)

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker @compose @Arguments
    if ($LASTEXITCODE -ne 0) { throw "docker compose command failed" }
}

function Get-ResolvedService {
    param($Config, [string]$ServiceName)
    $property = $Config.services.PSObject.Properties[$ServiceName]
    if ($null -eq $property) { throw "Compose preflight is missing service: $ServiceName" }
    return $property.Value
}

function Assert-LoopbackPort {
    param($Service, [int]$Target, [int]$Published, [string]$Label)
    $ports = @($Service.ports)
    if (
        $ports.Count -ne 1 -or [int]$ports[0].target -ne $Target -or
        [int]$ports[0].published -ne $Published -or
        [string]$ports[0].host_ip -cne "127.0.0.1" -or
        [string]$ports[0].protocol -cne "tcp"
    ) { throw "$Label port binding does not match the expected loopback endpoint" }
}

function Assert-ComposePreflight {
    $output = & docker @compose config --format json 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose config preflight failed" }
    try { $config = ($output -join [Environment]::NewLine) | ConvertFrom-Json }
    catch { throw "Docker Compose config preflight did not return valid JSON" }
    if ([string]$config.name -cne $ProjectName) { throw "Resolved Compose project does not match ProjectName" }
    foreach ($name in @("api", "importer", "role-provision", "revision-history-verify")) {
        if ([string](Get-ResolvedService $config $name).image -cne $ExpectedApiImage) {
            throw "Resolved $name image does not match ExpectedApiImage"
        }
    }
    foreach ($name in @("scheduler", "scheduler-smoke")) {
        if ([string](Get-ResolvedService $config $name).image -cne $ExpectedSchedulerImage) {
            throw "Resolved $name image does not match ExpectedSchedulerImage"
        }
    }
    $api = Get-ResolvedService $config "api"
    $web = Get-ResolvedService $config "web"
    $scheduler = Get-ResolvedService $config "scheduler"
    $db = Get-ResolvedService $config "db"
    Assert-LoopbackPort $api 8000 $ExpectedApiPort "API"
    Assert-LoopbackPort $web 3000 $ExpectedWebPort "Web"
    Assert-LoopbackPort $scheduler 8081 $ExpectedSchedulerPort "Scheduler"
    if (($null -ne $db.ports -and @($db.ports).Count -ne 0) -or -not [bool]$config.networks.backend.internal) {
        throw "Database or backend network exposure violates the rollback boundary"
    }
    if (
        [string]$scheduler.environment.SCHEDULER_ENABLED -cne "false" -or
        [string]$scheduler.environment.SHADOW_MODE -cne "true" -or
        [string]$scheduler.environment.AUTO_PUBLISH -cne "false"
    ) { throw "Resolved scheduler safety flags drifted" }
    Write-Host "A6_COMPOSE_PREFLIGHT_OK project=$ProjectName api_image=$ExpectedApiImage scheduler_image=$ExpectedSchedulerImage api_port=$ExpectedApiPort web_port=$ExpectedWebPort scheduler_port=$ExpectedSchedulerPort"
}

function Assert-RunningDbIdentity {
    $containerId = (& docker @compose ps -q db 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $containerId -notmatch '^[0-9a-f]{12,64}$') {
        throw "Could not identify exactly one running database container"
    }
    $output = & docker inspect $containerId 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Could not inspect the database container" }
    try { $inspection = @(($output -join [Environment]::NewLine) | ConvertFrom-Json)[0] }
    catch { throw "Database container inspection was not valid JSON" }
    $mounts = @($inspection.Mounts | Where-Object { $_.Destination -eq "/var/lib/postgresql" })
    if (
        [string]$inspection.Config.Labels.'com.docker.compose.project' -cne $ProjectName -or
        $mounts.Count -ne 1 -or [string]$mounts[0].Type -cne "volume" -or
        [string]$mounts[0].Name -cne "${ProjectName}_pg_data"
    ) { throw "Running database is not the expected isolated project volume" }
    Write-Host "A6_DB_TARGET_OK project=$ProjectName container=$containerId volume=$($mounts[0].Name)"
}

function Get-Scalar {
    param([string]$Sql)
    $value = & docker @compose exec -T db psql -X -q -v ON_ERROR_STOP=1 `
        -U $postgresUser -d $postgresDatabase -t -A -c $Sql
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL scalar query failed" }
    return ($value | Select-Object -Last 1).Trim()
}

function Get-ActualPort {
    param([string]$Service, [int]$ContainerPort, [int]$ExpectedPort)
    $output = & docker @compose port $Service $ContainerPort 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Could not resolve running $Service port" }
    $lines = @($output | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
    if ($lines.Count -ne 1 -or $lines[0] -notmatch '^127\.0\.0\.1:(\d{1,5})$') {
        throw "Running $Service endpoint is ambiguous or not loopback-only"
    }
    $actual = [int]$Matches[1]
    if ($actual -ne $ExpectedPort) { throw "Running $Service port differs from the preflight pin" }
    return $actual
}

function Assert-DbPrivilegeContract {
    $output = & (Join-Path $repoRoot "scripts\check_db_privileges.ps1") `
        -EnvFile $EnvFile -ProjectName $ProjectName -Database $postgresDatabase `
        -PostgresUser $postgresUser *>&1
    $exit = $LASTEXITCODE
    $lines = @($output | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
    $marker = "DB_PRIVILEGES_OK matrix_checks=651 actual_denials=23 allowed_smokes=10"
    if ($exit -ne 0 -or @($lines | Where-Object { $_ -ceq $marker }).Count -ne 1) {
        throw "Database privilege verifier did not emit the exact 7-privilege A6 contract"
    }
    $lines | ForEach-Object { Write-Host $_ }
}

function Assert-CountObject {
    param($Actual, [System.Collections.IDictionary]$Expected, [string]$Label)
    $names = @($Actual.PSObject.Properties.Name)
    if ($names.Count -ne $Expected.Count -or @($names | Where-Object { -not $Expected.Contains($_) }).Count -ne 0) {
        throw "$Label row-count keys do not match the pinned closure"
    }
    foreach ($name in $Expected.Keys) {
        if ([int]$Actual.$name -ne [int]$Expected[$name]) { throw "$Label row-count mismatch for $name" }
    }
}

function Assert-DatabaseCounts {
    param([System.Collections.IDictionary]$Expected, [string]$Label)
    foreach ($table in $Expected.Keys) {
        if ([int](Get-Scalar "SELECT COUNT(*) FROM $table") -ne [int]$Expected[$table]) {
            throw "$Label database count mismatch for $table"
        }
    }
}

function Get-ImportResult {
    param([object[]]$Output, [string]$Label)
    $lines = @($Output | ForEach-Object { [string]$_ } | Where-Object {
        $_ -match '^\{.*"activated"\s*:\s*(true|false)' -and $_ -match '"revision_id"\s*:'
    })
    if ($lines.Count -ne 1) { throw "$Label importer did not emit exactly one ImportResult JSON object" }
    try { return $lines[0].Trim() | ConvertFrom-Json }
    catch { throw "$Label ImportResult JSON is invalid" }
}

function Get-PinnedB5SourceProof {
    param([object[]]$Output, [string]$Label)
    $lines = @($Output | ForEach-Object { [string]$_ } | Where-Object {
        $_ -match '^\{.*"status"\s*:\s*"PINNED_ROLLBACK_SOURCE_OK"'
    })
    if ($lines.Count -ne 1) { throw "$Label did not emit exactly one pinned-source proof" }
    try { $proof = $lines[0].Trim() | ConvertFrom-Json }
    catch { throw "$Label pinned-source proof JSON is invalid" }
    if (
        $proof.status -ne "PINNED_ROLLBACK_SOURCE_OK" -or
        $proof.manifest_sha256 -ne $b5ManifestSha256 -or
        $proof.revision_id -ne $b5Revision -or
        [int]$proof.file_count -ne 48 -or
        [int]$proof.csv_row_count -ne 376
    ) { throw "$Label pinned-source proof is invalid" }
    return [pscustomobject]@{ Proof = $proof; Line = $lines[0].Trim() }
}

function Assert-RevisionIdentity {
    param(
        [string]$Revision, [string]$ManifestSha256, [string]$SemanticSha256,
        [string]$ImportRunId, [string]$MaterializationSha256, [string]$Label
    )
    $values = Get-Scalar "SELECT manifest_sha256 || '|' || raw_tree_sha256 || '|' || semantic_tree_sha256 || '|' || status || '|' || file_count || '|' || csv_file_count || '|' || csv_row_count || '|' || evidence_to_claim_count || '|' || evidence_to_claim_sha256 || '|' || claim_to_evidence_count || '|' || claim_to_evidence_sha256 || '|' || COALESCE(materialization_sha256, '') || '|' || COALESCE(import_run_id::text, '') FROM core_revisions WHERE revision_id='$Revision'"
    $expected = "$ManifestSha256|$Revision|$SemanticSha256|SUCCEEDED|48|13|376|120|$evidenceToClaimSha256|298|$claimToEvidenceSha256|$MaterializationSha256|$ImportRunId"
    if ($values -ne $expected) { throw "$Label CoreRevision identity drifted" }
    $run = Get-Scalar "SELECT status || '|' || fixture_sha256 || '|' || canonical_source || '|' || COALESCE(manifest#>>'{materialization,schema_version}', '') || '|' || COALESCE(manifest#>>'{materialization,sha256}', '') || '|' || (SELECT count(*) FROM jsonb_object_keys(CASE WHEN jsonb_typeof(manifest#>'{materialization,tables}')='object' THEN manifest#>'{materialization,tables}' ELSE '{}'::jsonb END)) FROM import_runs WHERE id='$ImportRunId'"
    if ($run -ne "SUCCEEDED|$Revision|research_core_file_ssot|4|$MaterializationSha256|23") {
        throw "$Label ImportRun identity drifted"
    }
    $counts = (Get-Scalar "SELECT row_counts::text FROM import_runs WHERE id='$ImportRunId'") | ConvertFrom-Json
    Assert-CountObject $counts $rowCounts "$Label ImportRun"
}

function Assert-ActiveState {
    param(
        [string]$Revision, [string]$ManifestSha256, [string]$SemanticSha256,
        [string]$ExpectedRun, [string]$ExpectedMaterialization, [string]$Label
    )
    $alembic = Get-Scalar "SELECT version_num FROM alembic_version"
    $activeRevision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $activeRun = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $activeMaterialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    if (
        $alembic -ne "v0007_gacha_timeline_slice" -or $activeRevision -ne $Revision -or
        $activeRun -ne $ExpectedRun -or $activeMaterialization -ne $ExpectedMaterialization
    ) { throw "$Label database state is not safe for recovery or restart" }
    Assert-RevisionIdentity $Revision $ManifestSha256 $SemanticSha256 $ExpectedRun $ExpectedMaterialization $Label
    $counts = (Get-Scalar "SELECT serving_counts::text FROM materialization_state WHERE id=1") | ConvertFrom-Json
    Assert-CountObject $counts $servingCounts "$Label MaterializationState"
    Assert-DatabaseCounts $servingCounts $Label
}

function Assert-A6State {
    param([string]$ExpectedRun, [string]$ExpectedMaterialization)
    Assert-ActiveState $a6Revision $a6ManifestSha256 $a6Semantic $ExpectedRun $ExpectedMaterialization "A6"
}

function Assert-B5State {
    param([string]$ExpectedRun, [string]$ExpectedMaterialization)
    Assert-ActiveState $b5Revision $b5ManifestSha256 $b5Semantic $ExpectedRun $ExpectedMaterialization "B5"
}

function Assert-Activation {
    param([long]$Sequence, [string]$From, [string]$To, [string]$Kind, [long]$Epoch, [string]$Label)
    $values = Get-Scalar "SELECT COALESCE(from_revision_id, '') || '|' || to_revision_id || '|' || kind || '|' || reason || '|' || actor || '|' || epoch FROM revision_activations WHERE sequence_no=$Sequence"
    $reasons = @{
        IMPORT = "activate manifest-pinned full-core import"
        ROLLBACK = "rollback to earlier verified immutable revision"
        REACTIVATE = "reactivate later verified immutable revision"
    }
    if ($values -ne "$From|$To|$Kind|$($reasons[$Kind])|pcr_pipeline.import_pve|$Epoch") {
        throw "$Label activation audit chronology drifted"
    }
}

function Assert-PublicReadiness {
    param(
        [string]$ExpectedRevision, [string]$ExpectedSemantic,
        [string]$ExpectedImportRun, [string]$ExpectedMaterialization,
        [ValidateSet("A6", "B5")][string]$Label
    )
    $apiPort = Get-ActualPort "api" 8000 $ExpectedApiPort
    $webPort = Get-ActualPort "web" 3000 $ExpectedWebPort
    $schedulerPort = Get-ActualPort "scheduler" 8081 $ExpectedSchedulerPort
    $ready = Invoke-RestMethod "http://127.0.0.1:${apiPort}/health/ready" -TimeoutSec 10
    $baseline = Invoke-RestMethod "http://127.0.0.1:${apiPort}/api/v1/baseline" -TimeoutSec 10
    $gacha = Invoke-RestMethod "http://127.0.0.1:${apiPort}/api/v1/gacha/timeline" -TimeoutSec 10
    $community = Invoke-RestMethod "http://127.0.0.1:${apiPort}/api/v1/gacha/community-sources" -TimeoutSec 10
    $webHealth = Invoke-RestMethod "http://127.0.0.1:${webPort}/api/health" -TimeoutSec 10
    $gachaPage = Invoke-WebRequest "http://127.0.0.1:${webPort}/gacha" -TimeoutSec 10
    $scheduler = Invoke-RestMethod "http://127.0.0.1:${schedulerPort}/health" -TimeoutSec 10
    $gachaRows = @($gacha.data)
    $eventIds = @($gachaRows | ForEach-Object { $_.event_id })
    $expectedEventIds = @(
        "JP_20260630_shefi_vardrache", "JP_20260703_luisemarie_summer",
        "JP_20260731_fubuki_summer", "JP_20260815_vampy_summer", "JP_20260823_tia"
    )
    $limitedStatuses = @($gachaRows | ForEach-Object { [string]$_.limited_status })
    $expectedLimitedStatuses = @("YES", "YES", "YES", "UNKNOWN", "UNKNOWN")
    $limitedClaimIds = @($gachaRows | ForEach-Object {
        if ($null -eq $_.limited_claim_id) { "<NULL>" } else { [string]$_.limited_claim_id }
    })
    $expectedLimitedClaimIds = @("CLM-SHEFI-POOL", "CLM-LUISE-DATE", "CLM-JP-FUBUKI-DATE", "<NULL>", "<NULL>")
    Assert-CountObject $baseline.data.counts $rowCounts "$Label public baseline"
    if (
        $ready.status -ne "ok" -or $ready.checks.database -ne "ok" -or $ready.checks.fixture -ne "imported" -or
        $baseline.data.application_version -ne "3.0.0-a6" -or
        $baseline.meta.source.canonical_source -ne "research_core_file_ssot" -or
        $baseline.meta.source.fixture_sha256 -ne $ExpectedRevision -or
        $baseline.meta.source.revision_id -ne $ExpectedRevision -or
        $baseline.meta.source.raw_tree_sha256 -ne $ExpectedRevision -or
        $baseline.meta.source.semantic_tree_sha256 -ne $ExpectedSemantic -or
        $baseline.meta.source.import_run_id -ne $ExpectedImportRun -or
        $baseline.meta.source.materialization_sha256 -ne $ExpectedMaterialization -or
        $gachaRows.Count -ne 5 -or @($community.data).Count -ne 4 -or
        ($eventIds -join "|") -ne ($expectedEventIds -join "|") -or
        ($limitedStatuses -join "|") -ne ($expectedLimitedStatuses -join "|") -or
        ($limitedClaimIds -join "|") -ne ($expectedLimitedClaimIds -join "|") -or
        @($gachaRows | Where-Object { $_.maturity -eq "MATURE" }).Count -ne 2 -or
        @($gachaRows | Where-Object { $_.maturity -eq "RESEARCH" }).Count -ne 3 -or
        $webHealth.status -ne "ok" -or $gachaPage.StatusCode -ne 200 -or
        $gachaPage.Content -notmatch "抽卡未來視" -or $gachaPage.Content -notmatch "限定身分 UNKNOWN" -or
        [bool]$scheduler.enabled -or -not [bool]$scheduler.shadow_mode -or [bool]$scheduler.canonical_write_capable
    ) { throw "$Label public readiness or Shadow Mode contract failed" }
    Write-Host "${Label}_PUBLIC_READINESS_OK api_port=$apiPort web_port=$webPort scheduler_port=$schedulerPort revision=$ExpectedRevision import_run=$ExpectedImportRun materialization=$ExpectedMaterialization gacha_events=5 gacha_sources=4"
}

function Assert-A6PublicReadiness {
    Assert-PublicReadiness $a6Revision $a6Semantic $originA6ImportRun $originA6Materialization "A6"
}

function Assert-B5PublicReadiness {
    Assert-PublicReadiness $b5Revision $b5Semantic $b5ImportRun $b5Materialization "B5"
}

function Assert-OriginAnchor {
    $kind = Get-Scalar "SELECT kind FROM revision_activations WHERE sequence_no=$originActivationSequence"
    if ($kind -notin @("IMPORT", "REACTIVATE")) { throw "Origin A6 activation is not forward-moving" }
    $from = Get-Scalar "SELECT COALESCE(from_revision_id, '') FROM revision_activations WHERE sequence_no=$originActivationSequence"
    if ($originActivationEpoch -le 0 -or $originActivationEpoch -gt $originEpoch) { throw "Origin activation epoch is invalid" }
    Assert-Activation $originActivationSequence $from $a6Revision $kind $originActivationEpoch "Origin A6"
}

function Assert-RecoveryChain {
    $sequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $stateEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    $rollbackEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$($originActivationSequence + 1)")
    $reactivateEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$($originActivationSequence + 2)")
    if ($sequence -ne ($originActivationSequence + 2) -or $rollbackEpoch -le $originEpoch -or $reactivateEpoch -le $rollbackEpoch -or $stateEpoch -ne $reactivateEpoch) {
        throw "A6 recovery activation sequence or epoch chain is invalid"
    }
    Assert-Activation ($originActivationSequence + 1) $a6Revision $b5Revision "ROLLBACK" $rollbackEpoch "B5 rollback"
    Assert-Activation ($originActivationSequence + 2) $b5Revision $a6Revision "REACTIVATE" $reactivateEpoch "A6 reactivation"
}

function Get-RecoveryMode {
    $alembic = Get-Scalar "SELECT version_num FROM alembic_version"
    if ($alembic -ne "v0007_gacha_timeline_slice") { throw "A6/B5 recovery schema drifted" }
    $revision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $sequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $epoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($revision -eq $a6Revision) {
        Assert-A6State $originA6ImportRun $originA6Materialization
        if ($sequence -eq $originActivationSequence -and $epoch -eq $originEpoch) { Assert-OriginAnchor; return "ORIGIN_NOOP" }
        if ($sequence -eq ($originActivationSequence + 2)) { Assert-RecoveryChain; return "ALREADY_RESTORED_NOOP" }
        throw "Active A6 chronology is neither origin nor the exact restored chain"
    }
    if ($revision -eq $b5Revision -and $sequence -eq ($originActivationSequence + 1)) {
        if ([string]::IsNullOrWhiteSpace($script:b5ImportRun)) {
            $script:b5ImportRun = Get-Scalar "SELECT COALESCE(import_run_id::text, '') FROM core_revisions WHERE revision_id='$b5Revision' AND status='SUCCEEDED'"
            $script:b5Materialization = Get-Scalar "SELECT COALESCE(materialization_sha256, '') FROM core_revisions WHERE revision_id='$b5Revision' AND status='SUCCEEDED'"
        }
        Assert-B5State $b5ImportRun $b5Materialization
        $rollbackEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
        if ($rollbackEpoch -le $originEpoch) { throw "B5 rollback epoch did not advance" }
        Assert-Activation ($originActivationSequence + 1) $a6Revision $b5Revision "ROLLBACK" $rollbackEpoch "B5 recovery"
        return "B5_REACTIVATE"
    }
    throw "Recovery state is neither origin A6, exact B5 rollback, nor restored A6"
}

function Restore-A6 {
    $mode = Get-RecoveryMode
    $expectedActivated = $mode -eq "B5_REACTIVATE"
    Write-Host "A6_RECOVERY_MODE_OK mode=$mode expected_activated=$($expectedActivated.ToString().ToLowerInvariant())"
    Invoke-Compose run --rm --no-deps role-provision
    Assert-DbPrivilegeContract
    $output = & docker @compose run --rm --no-deps importer 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Canonical A6 restoration import failed" }
    $baseline = @($output | ForEach-Object { [string]$_ } | Where-Object { $_ -match '^RESEARCH_BASELINE_OK\s*\|' })
    if ($baseline.Count -ne 1 -or $baseline[0] -notmatch [regex]::Escape("manifest_sha256=$a6ManifestSha256")) {
        throw "Canonical A6 restoration did not emit the pinned baseline proof"
    }
    Write-Host $baseline[0].Trim()
    $result = Get-ImportResult $output "A6 restoration"
    if (
        $result.created -ne $false -or $result.activated -ne $expectedActivated -or
        $result.revision_id -ne $a6Revision -or $result.raw_tree_sha256 -ne $a6Revision -or
        $result.semantic_tree_sha256 -ne $a6Semantic -or [int]$result.file_count -ne 48 -or
        [int]$result.csv_file_count -ne 13 -or [int]$result.csv_row_count -ne 376 -or
        $result.import_run_id -ne $originA6ImportRun
    ) { throw "A6 restoration ImportResult identity is invalid" }
    Assert-CountObject $result.row_counts $rowCounts "A6 restoration ImportResult"
    Assert-A6State $originA6ImportRun $originA6Materialization
    Assert-DbPrivilegeContract
    if ($mode -eq "ORIGIN_NOOP") { Assert-OriginAnchor } else { Assert-RecoveryChain }
    Write-Host "A6_RESTORED_OK mode=$mode alembic=v0007_gacha_timeline_slice active_revision=$a6Revision import_run=$originA6ImportRun artifact_diagnostic=$a6ArtifactMirrorSha256"
}

Assert-ComposePreflight
Invoke-Compose ps --status running db
Assert-RunningDbIdentity

$servicesStopped = $false
$needsA6Restore = $false
$intermediateServicesMayRun = $false
$primaryError = $null
$originA6ImportRun = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
$originA6Materialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
$originActivationSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
$originActivationEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$originActivationSequence")
$originEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
$b5ImportRun = ""
$b5Materialization = ""
$b5ExpectedCreated = $true
$checkpointMount = "${B5CheckpointRoot}:/rollback:ro"
$b5SourceVerifierCode = "from pathlib import Path; from pcr_pipeline.import_pve import _verify_import_source; _verify_import_source(Path('/rollback/research_core/pcr_tw_project'), Path('/app/scripts/research_core_rp_b5_1_manifest.sha256'), '$b5ManifestSha256', Path('/app/scripts/check_research_baseline.py'))"

try {
    Assert-A6State $originA6ImportRun $originA6Materialization
    $b5HistoryCount = [int](Get-Scalar "SELECT COUNT(*) FROM core_revisions WHERE revision_id='$b5Revision'")
    if ($b5HistoryCount -eq 1) {
        $b5ExpectedCreated = $false
        $b5ImportRun = Get-Scalar "SELECT COALESCE(import_run_id::text, '') FROM core_revisions WHERE revision_id='$b5Revision' AND status='SUCCEEDED'"
        $b5Materialization = Get-Scalar "SELECT COALESCE(materialization_sha256, '') FROM core_revisions WHERE revision_id='$b5Revision' AND status='SUCCEEDED'"
        if ($b5ImportRun -notmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' -or $b5Materialization -notmatch '^[0-9a-f]{64}$') {
            throw "Existing immutable B5 release evidence is incomplete"
        }
        Assert-RevisionIdentity $b5Revision $b5ManifestSha256 $b5Semantic $b5ImportRun $b5Materialization "Immutable B5"
        Write-Host "B5_IMMUTABLE_RELEASE_INPUT_OK history=present expected_create=false revision=$b5Revision import_run=$b5ImportRun materialization=$b5Materialization files=48 csv=13 rows=376 edges=120/298"
    }
    elseif ($b5HistoryCount -eq 0) {
        Write-Host "B5_IMMUTABLE_RELEASE_INPUT_OK history=absent expected_create=true revision=$b5Revision manifest=$b5ManifestSha256 files=48 csv=13 rows=376 edges=120/298"
    }
    else {
        throw "B5 CoreRevision uniqueness invariant failed"
    }
    Assert-OriginAnchor
    Assert-A6PublicReadiness
    Assert-DbPrivilegeContract
    $epochAfterReadiness = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($epochAfterReadiness -ne $originEpoch) { throw "A6 readiness changed the origin materialization epoch" }
    Write-Host "A6_ORIGIN_VERIFIED_OK alembic=v0007_gacha_timeline_slice active_revision=$a6Revision import_run=$originA6ImportRun materialization=$originA6Materialization activation_sequence=$originActivationSequence activation_epoch=$originActivationEpoch state_epoch=$originEpoch"

    $preflightProofOutput = & docker @compose run --rm --no-deps `
        --volume $checkpointMount `
        importer `
        python -c $b5SourceVerifierCode 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Immutable RP-B5 checkpoint preflight failed" }
    $preflightProof = Get-PinnedB5SourceProof $preflightProofOutput "RP-B5 checkpoint preflight"
    Assert-A6State $originA6ImportRun $originA6Materialization
    $sequenceAfterCheckpointProof = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $epochAfterCheckpointProof = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($sequenceAfterCheckpointProof -ne $originActivationSequence -or $epochAfterCheckpointProof -ne $originEpoch) {
        throw "Read-only B5 checkpoint verification changed A6 chronology or epoch"
    }
    Write-Host $preflightProof.Line
    Write-Host "B5_CHECKPOINT_PREFLIGHT_OK revision=$b5Revision manifest=$b5ManifestSha256 files=48 rows=376 activation_sequence=$sequenceAfterCheckpointProof epoch=$epochAfterCheckpointProof"

    $servicesStopped = $true
    Invoke-Compose stop web api scheduler
    $needsA6Restore = $true
    $rollbackOutput = & docker @compose run --rm --no-deps `
        --volume $checkpointMount `
        importer `
        python -m pcr_pipeline.import_pve `
        --research-core /rollback/research_core/pcr_tw_project `
        --manifest /app/scripts/research_core_rp_b5_1_manifest.sha256 `
        --manifest-sha256 $b5ManifestSha256 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Pinned RP-B5 activation failed" }
    $activationProof = Get-PinnedB5SourceProof $rollbackOutput "RP-B5 activation"
    Write-Host $activationProof.Line
    $b5Result = Get-ImportResult $rollbackOutput "RP-B5 activation"
    if (
        $b5Result.created -ne $b5ExpectedCreated -or $b5Result.activated -ne $true -or
        $b5Result.revision_id -ne $b5Revision -or $b5Result.raw_tree_sha256 -ne $b5Revision -or
        $b5Result.semantic_tree_sha256 -ne $b5Semantic -or [int]$b5Result.file_count -ne 48 -or
        [int]$b5Result.csv_file_count -ne 13 -or [int]$b5Result.csv_row_count -ne 376
    ) { throw "RP-B5 ImportResult identity is invalid" }
    Assert-CountObject $b5Result.row_counts $rowCounts "RP-B5 ImportResult"
    $b5ImportRun = [string]$b5Result.import_run_id
    $b5Materialization = Get-Scalar "SELECT COALESCE(materialization_sha256, '') FROM core_revisions WHERE revision_id='$b5Revision' AND status='SUCCEEDED'"
    if ($b5ImportRun -notmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' -or $b5Materialization -notmatch '^[0-9a-f]{64}$') {
        throw "RP-B5 import did not establish immutable release evidence"
    }
    Assert-B5State $b5ImportRun $b5Materialization
    $b5Sequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $b5Epoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($b5Sequence -ne ($originActivationSequence + 1) -or $b5Epoch -le $originEpoch) {
        throw "B5 activation sequence or epoch did not advance exactly"
    }
    Assert-Activation $b5Sequence $a6Revision $b5Revision "ROLLBACK" $b5Epoch "RP-B5 rollback"
    Write-Host "A6_B5_DATA_ROLLBACK_OK alembic=v0007_gacha_timeline_slice active_revision=$b5Revision import_run=$b5ImportRun materialization=$b5Materialization activation_sequence=$b5Sequence epoch=$b5Epoch"
    Write-Host "A6_B5_SAME_SCHEMA_ROLLBACK_OK alembic=v0007_gacha_timeline_slice migration_commands=0"

    $intermediateServicesMayRun = $true
    Invoke-Compose up --detach --no-build --wait --wait-timeout 90 --no-deps scheduler api web
    Assert-B5PublicReadiness
    Assert-B5State $b5ImportRun $b5Materialization
    $b5ServingSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $b5ServingEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($b5ServingSequence -ne $b5Sequence -or $b5ServingEpoch -ne $b5Epoch) {
        throw "B5 public readiness changed rollback chronology or epoch"
    }
    Write-Host "B5_INTERMEDIATE_SERVICES_READY_OK api_image=$ExpectedApiImage scheduler_image=$ExpectedSchedulerImage activation_sequence=$b5ServingSequence epoch=$b5ServingEpoch"
    Invoke-Compose stop web api scheduler
    $intermediateServicesMayRun = $false
    Assert-B5State $b5ImportRun $b5Materialization
    Write-Host "B5_INTERMEDIATE_SERVICES_STOPPED_OK active_revision=$b5Revision"

    Restore-A6
    $needsA6Restore = $false
}
catch {
    $primaryError = $_
}
finally {
    if ($needsA6Restore -and $intermediateServicesMayRun) {
        try {
            Invoke-Compose stop web api scheduler
            $intermediateServicesMayRun = $false
            Write-Host "B5_INTERMEDIATE_SERVICES_RECOVERY_STOP_OK"
        }
        catch {
            if ($null -eq $primaryError) { $primaryError = $_ }
            else { $primaryError = [System.Exception]::new("$($primaryError.Exception.Message); intermediate service stop also failed: $($_.Exception.Message)") }
        }
    }
    if ($needsA6Restore -and -not $intermediateServicesMayRun) {
        try { Restore-A6; $needsA6Restore = $false }
        catch {
            if ($null -eq $primaryError) { $primaryError = $_ }
            else { $primaryError = [System.Exception]::new("$($primaryError.Exception.Message); A6 restore also failed: $($_.Exception.Message)") }
        }
    }
    if ($servicesStopped -and -not $needsA6Restore) {
        try {
            Assert-A6State $originA6ImportRun $originA6Materialization
            $preRestartEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
            $preRestartSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
            if ($preRestartSequence -eq $originActivationSequence -and $preRestartEpoch -eq $originEpoch) {
                Assert-OriginAnchor
                $finalChronology = "ORIGIN_NOOP"
            }
            elseif ($preRestartSequence -eq ($originActivationSequence + 2)) {
                Assert-RecoveryChain
                $finalChronology = "ROLLBACK_REACTIVATE"
            }
            else {
                throw "Final A6 state is neither exact origin nor the exact rollback/reactivation chain"
            }
            Invoke-Compose up --detach --no-build --wait --wait-timeout 90 --no-deps scheduler api web
            Assert-A6PublicReadiness
            Invoke-Compose run --rm --no-deps revision-history-verify
            $finalEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
            $finalSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
            if ($finalSequence -ne $preRestartSequence -or $finalEpoch -ne $preRestartEpoch) {
                throw "Final A6 readiness changed the verified chronology or epoch"
            }
            if ($finalChronology -eq "ORIGIN_NOOP") { Assert-OriginAnchor } else { Assert-RecoveryChain }
            Write-Host "A6_SERVICES_READY_OK database=ok fixture=imported gacha_events=5 chronology=$finalChronology activation_sequence=$finalSequence epoch=$finalEpoch"
        }
        catch {
            $restartError = $_
            try { Invoke-Compose stop web api scheduler }
            catch { $restartError = [System.Exception]::new("$($restartError.Exception.Message); service requiesce also failed: $($_.Exception.Message)") }
            if ($null -eq $primaryError) { $primaryError = $restartError }
            else { $primaryError = [System.Exception]::new("$($primaryError.Exception.Message); A6 readiness also failed: $($restartError.Exception.Message)") }
        }
    }
    elseif ($servicesStopped) {
        $warningMarker = if ($intermediateServicesMayRun) {
            "SERVICES_RECOVERY_BOUNDARY_FAILED"
        }
        else {
            "SERVICES_LEFT_QUIESCED"
        }
        $message = if ($intermediateServicesMayRun) {
            "A6 restoration was not verified and intermediate service shutdown failed; use the verified backup before serving traffic"
        }
        else {
            "A6 restoration was not verified; services were left quiesced for manual recovery from the verified backup"
        }
        Write-Warning "${warningMarker}: $message"
        if ($null -eq $primaryError) { $primaryError = [System.Exception]::new($message) }
    }
}

if ($null -ne $primaryError) { throw $primaryError }
Write-Host "A6_B5_ROLLBACK_DRILL_OK"
