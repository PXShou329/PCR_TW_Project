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
    [string]$A5CheckpointRoot,
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
$A5CheckpointRoot = [System.IO.Path]::GetFullPath($A5CheckpointRoot)
$VerifiedBackupPath = [System.IO.Path]::GetFullPath($VerifiedBackupPath)
$a5Core = Join-Path $A5CheckpointRoot "research_core\pcr_tw_project"
$a5Manifest = Join-Path $repoRoot "scripts\research_core_rp_a5_manifest.sha256"

if ($ProjectName -in @("pcr-tw-a5-arena", "pcr-tw-a4-water", "pcr-tw-b1")) {
    throw "ProjectName is reserved for an existing or legacy stack"
}
foreach ($requiredFile in @($EnvFile, $a5Manifest, $VerifiedBackupPath)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Missing B5 rollback drill input: $requiredFile"
    }
}
if (-not (Test-Path -LiteralPath $a5Core -PathType Container)) {
    throw "Missing RP-A5 research core: $a5Core"
}
$backupFile = Get-Item -LiteralPath $VerifiedBackupPath
if ($backupFile.Length -lt 1) {
    throw "Verified backup file is empty"
}
$actualBackupSha256 = (Get-FileHash -LiteralPath $VerifiedBackupPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualBackupSha256 -ne $VerifiedBackupSha256.ToLowerInvariant()) {
    throw "Verified backup SHA-256 mismatch"
}
Write-Host "VERIFIED_BACKUP_INPUT_OK sha256=$actualBackupSha256 bytes=$($backupFile.Length)"

$b5ManifestSha256 = "e74814d6433ee327611f10322937bdfa9687b9887f139ba6e6158a291dd12989"
$b5Revision = "d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d"
$b5Semantic = "a7467a838c2a9cfdfe48bda4a3b158fb374dd023caa3478a84c07678532ea9f4"
$b5EvidenceToClaimSha256 = "a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af"
$b5ClaimToEvidenceSha256 = "24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c"
$a5ManifestSha256 = "1826c8493d40f71a6d0bb9096f57b92fe4e839d52bddf021b0c51e0186dcbda7"
$a5Revision = "1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c"
$a5Semantic = "c77bc9893fa0b442832c1dff0c7c4a1c5e6d63ba9bce27c1c2f8078c5c2511b8"
$a5EvidenceToClaimSha256 = "84fea5ed4095dfcbb98cb52816c2e8a7a3d9fd1acd9ef225541ba27b8bcc192e"
$a5ClaimToEvidenceSha256 = "b0fefe463e3968266ed8a8378fd8b7f5c94817a4dd548f920facf7c182fa0e64"

$b5RowCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 73; claims = 69; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
    gacha_timeline_events = 5; gacha_timeline_evidence = 10; gacha_timeline_claims = 8
    gacha_community_sources = 4; gacha_timeline_community_sources = 0
}
$b5ServingCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 73; claims = 69; stage_evidence = 47; stage_claims = 46
    team_evidence = 95; claim_evidence = 159; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
    gacha_timeline_events = 5; gacha_timeline_evidence = 10; gacha_timeline_claims = 8
    gacha_community_sources = 4; gacha_timeline_community_sources = 0
}
$a5RowCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 64; claims = 62; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
}
$a5ServingCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 64; claims = 62; stage_evidence = 47; stage_claims = 46
    team_evidence = 95; claim_evidence = 150; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
}
$gachaTables = @(
    "gacha_timeline_events", "gacha_timeline_evidence", "gacha_timeline_claims",
    "gacha_community_sources", "gacha_timeline_community_sources"
)

function Get-Setting {
    param([string]$Name, [string]$Default = "")
    $processValue = [Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($processValue)) {
        return $processValue.Trim()
    }
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
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed: $($Arguments -join ' ')"
    }
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
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose config preflight failed: $($output -join [Environment]::NewLine)" }
    try { $config = ($output -join [Environment]::NewLine) | ConvertFrom-Json }
    catch { throw "Docker Compose config preflight did not return valid JSON" }
    if ([string]$config.name -cne $ProjectName) { throw "Resolved Compose project does not match ProjectName" }
    foreach ($name in @("api", "importer", "migration", "role-provision", "revision-history-verify")) {
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
    if (
        ($null -ne $db.ports -and @($db.ports).Count -ne 0) -or
        -not [bool]$config.networks.backend.internal
    ) {
        throw "Database or backend network exposure violates the rollback boundary"
    }
    if (
        [string]$scheduler.environment.SCHEDULER_ENABLED -cne "false" -or
        [string]$scheduler.environment.SHADOW_MODE -cne "true" -or
        [string]$scheduler.environment.AUTO_PUBLISH -cne "false"
    ) { throw "Resolved scheduler safety flags drifted" }
    Write-Host "B5_COMPOSE_PREFLIGHT_OK project=$ProjectName api_image=$ExpectedApiImage scheduler_image=$ExpectedSchedulerImage api_port=$ExpectedApiPort web_port=$ExpectedWebPort scheduler_port=$ExpectedSchedulerPort"
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
    Write-Host "B5_DB_TARGET_OK project=$ProjectName container=$containerId volume=$($mounts[0].Name)"
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
    $privilegeOutput = & (Join-Path $repoRoot "scripts\check_db_privileges.ps1") `
        -EnvFile $EnvFile `
        -ProjectName $ProjectName `
        -Database $postgresDatabase `
        -PostgresUser $postgresUser *>&1
    $privilegeExit = $LASTEXITCODE
    $privilegeLines = @(
        $privilegeOutput | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ }
    )
    $expectedMarker = "DB_PRIVILEGES_OK matrix_checks=651 actual_denials=23 allowed_smokes=10"
    if ($privilegeExit -ne 0 -or @($privilegeLines | Where-Object { $_ -ceq $expectedMarker }).Count -ne 1) {
        throw "Database privilege verifier did not emit the exact 7-privilege B5 contract"
    }
    $privilegeLines | ForEach-Object { Write-Host $_ }
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

function Assert-RevisionIdentity {
    param(
        [string]$Revision, [string]$ManifestSha256, [string]$SemanticSha256,
        [int]$CsvRows, [int]$ForwardCount, [string]$ForwardSha256,
        [int]$ReverseCount, [string]$ReverseSha256, [string]$ImportRunId,
        [string]$MaterializationSha256, [int]$MaterializationVersion,
        [int]$MaterializationTableCount, [System.Collections.IDictionary]$RowCounts,
        [string]$Label
    )
    $values = Get-Scalar "SELECT manifest_sha256 || '|' || raw_tree_sha256 || '|' || semantic_tree_sha256 || '|' || status || '|' || file_count || '|' || csv_file_count || '|' || csv_row_count || '|' || evidence_to_claim_count || '|' || evidence_to_claim_sha256 || '|' || claim_to_evidence_count || '|' || claim_to_evidence_sha256 || '|' || COALESCE(materialization_sha256, '') || '|' || COALESCE(import_run_id::text, '') FROM core_revisions WHERE revision_id='$Revision'"
    $expected = "$ManifestSha256|$Revision|$SemanticSha256|SUCCEEDED|48|13|$CsvRows|$ForwardCount|$ForwardSha256|$ReverseCount|$ReverseSha256|$MaterializationSha256|$ImportRunId"
    if ($values -ne $expected) { throw "$Label CoreRevision identity drifted" }
    $run = Get-Scalar "SELECT status || '|' || fixture_sha256 || '|' || canonical_source || '|' || COALESCE(manifest#>>'{materialization,schema_version}', '') || '|' || COALESCE(manifest#>>'{materialization,sha256}', '') || '|' || (SELECT count(*) FROM jsonb_object_keys(CASE WHEN jsonb_typeof(manifest#>'{materialization,tables}')='object' THEN manifest#>'{materialization,tables}' ELSE '{}'::jsonb END)) FROM import_runs WHERE id='$ImportRunId'"
    if ($run -ne "SUCCEEDED|$Revision|research_core_file_ssot|$MaterializationVersion|$MaterializationSha256|$MaterializationTableCount") {
        throw "$Label ImportRun identity drifted"
    }
    $counts = (Get-Scalar "SELECT row_counts::text FROM import_runs WHERE id='$ImportRunId'") | ConvertFrom-Json
    Assert-CountObject $counts $RowCounts "$Label ImportRun"
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

function Assert-B5State {
    param([string]$ExpectedRun, [string]$ExpectedMaterialization)
    $alembic = Get-Scalar "SELECT version_num FROM alembic_version"
    $revision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $run = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $materialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    if ($alembic -ne "v0007_gacha_timeline_slice" -or $revision -ne $b5Revision -or $run -ne $ExpectedRun -or $materialization -ne $ExpectedMaterialization) {
        throw "B5 database state is not safe for recovery or restart"
    }
    Assert-RevisionIdentity $b5Revision $b5ManifestSha256 $b5Semantic 376 120 $b5EvidenceToClaimSha256 298 $b5ClaimToEvidenceSha256 $ExpectedRun $ExpectedMaterialization 4 23 $b5RowCounts "B5"
    $counts = (Get-Scalar "SELECT serving_counts::text FROM materialization_state WHERE id=1") | ConvertFrom-Json
    Assert-CountObject $counts $b5ServingCounts "B5 MaterializationState"
    Assert-DatabaseCounts $b5ServingCounts "B5"
}

function Assert-A5State {
    param([string]$ExpectedAlembic, [string]$ExpectedRun, [string]$ExpectedMaterialization)
    $alembic = Get-Scalar "SELECT version_num FROM alembic_version"
    $revision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $run = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $materialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    if ($alembic -ne $ExpectedAlembic -or $revision -ne $a5Revision -or $run -ne $ExpectedRun -or $materialization -ne $ExpectedMaterialization) {
        throw "A5 rollback state identity drifted"
    }
    Assert-RevisionIdentity $a5Revision $a5ManifestSha256 $a5Semantic 356 111 $a5EvidenceToClaimSha256 277 $a5ClaimToEvidenceSha256 $ExpectedRun $ExpectedMaterialization 3 18 $a5RowCounts "A5"
    $counts = (Get-Scalar "SELECT serving_counts::text FROM materialization_state WHERE id=1") | ConvertFrom-Json
    Assert-CountObject $counts $a5ServingCounts "A5 MaterializationState"
    Assert-DatabaseCounts $a5ServingCounts "A5"
    $existingGachaTables = [int](Get-Scalar "SELECT COUNT(*) FROM (VALUES ('gacha_timeline_events'), ('gacha_timeline_evidence'), ('gacha_timeline_claims'), ('gacha_community_sources'), ('gacha_timeline_community_sources')) AS gacha_table(name) WHERE to_regclass('public.' || name) IS NOT NULL")
    if ($ExpectedAlembic -eq "v0007_gacha_timeline_slice") {
        if ($existingGachaTables -ne 5) { throw "A5-on-V0007 must retain all empty Gacha tables" }
        foreach ($table in $gachaTables) {
            if ([int](Get-Scalar "SELECT COUNT(*) FROM $table") -ne 0) { throw "A5 rollback left Gacha rows in $table" }
        }
    }
    elseif ($ExpectedAlembic -eq "v0006_arena_counter_slice" -and $existingGachaTables -ne 0) {
        throw "V0007 to V0006 downgrade left Gacha tables behind"
    }
}

function Assert-B5PublicReadiness {
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
    $gachaEventIds = @($gachaRows | ForEach-Object { $_.event_id })
    $expectedGachaEventIds = @(
        "JP_20260630_shefi_vardrache",
        "JP_20260703_luisemarie_summer",
        "JP_20260731_fubuki_summer",
        "JP_20260815_vampy_summer",
        "JP_20260823_tia"
    )
    $gachaLimitedStatuses = @($gachaRows | ForEach-Object { [string]$_.limited_status })
    $expectedGachaLimitedStatuses = @("YES", "YES", "YES", "UNKNOWN", "UNKNOWN")
    $gachaLimitedClaimIds = @(
        $gachaRows | ForEach-Object {
            if ($null -eq $_.limited_claim_id) { "<NULL>" } else { [string]$_.limited_claim_id }
        }
    )
    $expectedGachaLimitedClaimIds = @(
        "CLM-SHEFI-POOL",
        "CLM-LUISE-DATE",
        "CLM-JP-FUBUKI-DATE",
        "<NULL>",
        "<NULL>"
    )
    if (
        $ready.status -ne "ok" -or $ready.checks.database -ne "ok" -or $ready.checks.fixture -ne "imported" -or
        $baseline.data.application_version -ne "3.0.0-b5" -or
        $baseline.meta.source.revision_id -ne $b5Revision -or
        $baseline.meta.source.import_run_id -ne $originB5ImportRun -or
        $baseline.meta.source.materialization_sha256 -ne $originB5Materialization -or
        $gachaRows.Count -ne 5 -or @($community.data).Count -ne 4 -or
        ($gachaEventIds -join "|") -ne ($expectedGachaEventIds -join "|") -or
        ($gachaLimitedStatuses -join "|") -ne ($expectedGachaLimitedStatuses -join "|") -or
        ($gachaLimitedClaimIds -join "|") -ne ($expectedGachaLimitedClaimIds -join "|") -or
        @($gachaRows | Where-Object { $_.maturity -eq "MATURE" }).Count -ne 2 -or
        @($gachaRows | Where-Object { $_.maturity -eq "RESEARCH" }).Count -ne 3 -or
        $webHealth.status -ne "ok" -or $gachaPage.StatusCode -ne 200 -or
        $gachaPage.Content -notmatch "抽卡未來視" -or $gachaPage.Content -notmatch "限定身分 UNKNOWN" -or
        [bool]$scheduler.enabled -or -not [bool]$scheduler.shadow_mode -or [bool]$scheduler.canonical_write_capable
    ) { throw "B5 public readiness or Shadow Mode contract failed" }
    Write-Host "B5_PUBLIC_READINESS_OK api_port=$apiPort web_port=$webPort scheduler_port=$schedulerPort gacha_events=5 gacha_sources=4"
}

function Assert-OriginAnchor {
    $kind = Get-Scalar "SELECT kind FROM revision_activations WHERE sequence_no=$originActivationSequence"
    if ($kind -notin @("IMPORT", "REACTIVATE")) { throw "Origin B5 activation is not forward-moving" }
    $from = Get-Scalar "SELECT COALESCE(from_revision_id, '') FROM revision_activations WHERE sequence_no=$originActivationSequence"
    if ($originActivationEpoch -le 0 -or $originActivationEpoch -gt $originEpoch) { throw "Origin activation epoch is invalid" }
    Assert-Activation $originActivationSequence $from $b5Revision $kind $originActivationEpoch "Origin B5"
}

function Assert-RecoveryChain {
    $sequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $stateEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    $rollbackEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$($originActivationSequence + 1)")
    $reactivateEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$($originActivationSequence + 2)")
    if ($sequence -ne ($originActivationSequence + 2) -or $rollbackEpoch -le $originEpoch -or $reactivateEpoch -le $rollbackEpoch -or $stateEpoch -ne $reactivateEpoch) {
        throw "B5 recovery activation sequence or epoch chain is invalid"
    }
    Assert-Activation ($originActivationSequence + 1) $b5Revision $a5Revision "ROLLBACK" $rollbackEpoch "A5 rollback"
    Assert-Activation ($originActivationSequence + 2) $a5Revision $b5Revision "REACTIVATE" $reactivateEpoch "B5 reactivation"
}

function Get-RecoveryMode {
    $alembic = Get-Scalar "SELECT version_num FROM alembic_version"
    $revision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $run = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $materialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    $sequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $epoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($revision -eq $b5Revision) {
        Assert-B5State $originB5ImportRun $originB5Materialization
        if ($sequence -eq $originActivationSequence -and $epoch -eq $originEpoch) { Assert-OriginAnchor; return "ORIGIN_NOOP" }
        if ($sequence -eq ($originActivationSequence + 2)) { Assert-RecoveryChain; return "ALREADY_RESTORED_NOOP" }
        throw "Active B5 chronology is neither origin nor the exact restored chain"
    }
    if ($revision -eq $a5Revision -and $sequence -eq ($originActivationSequence + 1)) {
        if ($alembic -notin @("v0007_gacha_timeline_slice", "v0006_arena_counter_slice")) { throw "A5 recovery schema is unsupported" }
        Assert-A5State $alembic $run $materialization
        $rollbackEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
        if ($rollbackEpoch -le $originEpoch) { throw "A5 rollback epoch did not advance" }
        Assert-Activation ($originActivationSequence + 1) $b5Revision $a5Revision "ROLLBACK" $rollbackEpoch "A5 recovery"
        return "A5_REACTIVATE"
    }
    throw "Recovery state is neither origin B5, exact A5 rollback, nor restored B5"
}

function Restore-B5 {
    $mode = Get-RecoveryMode
    $expectedActivated = $mode -eq "A5_REACTIVATE"
    Write-Host "B5_RECOVERY_MODE_OK mode=$mode expected_activated=$($expectedActivated.ToString().ToLowerInvariant())"
    Invoke-Compose run --rm --no-deps migration alembic -c database/alembic.ini upgrade head
    Invoke-Compose run --rm --no-deps role-provision
    Assert-DbPrivilegeContract
    $output = & docker @compose run --rm --no-deps importer 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Canonical B5 restoration import failed: $($output -join [Environment]::NewLine)" }
    $baseline = @($output | ForEach-Object { [string]$_ } | Where-Object { $_ -match '^RESEARCH_BASELINE_OK\s*\|' })
    if ($baseline.Count -ne 1 -or $baseline[0] -notmatch [regex]::Escape("manifest_sha256=$b5ManifestSha256")) {
        throw "Canonical B5 restoration did not emit the pinned baseline proof"
    }
    Write-Host $baseline[0].Trim()
    $result = Get-ImportResult $output "B5 restoration"
    if (
        $result.created -ne $false -or $result.activated -ne $expectedActivated -or
        $result.revision_id -ne $b5Revision -or $result.raw_tree_sha256 -ne $b5Revision -or
        $result.semantic_tree_sha256 -ne $b5Semantic -or [int]$result.file_count -ne 48 -or
        [int]$result.csv_file_count -ne 13 -or [int]$result.csv_row_count -ne 376 -or
        $result.import_run_id -ne $originB5ImportRun
    ) { throw "B5 restoration ImportResult identity is invalid" }
    Assert-CountObject $result.row_counts $b5RowCounts "B5 restoration ImportResult"
    Assert-B5State $originB5ImportRun $originB5Materialization
    if ($mode -eq "ORIGIN_NOOP") { Assert-OriginAnchor } else { Assert-RecoveryChain }
    Write-Host "B5_RESTORED_OK mode=$mode alembic=v0007_gacha_timeline_slice active_revision=$b5Revision import_run=$originB5ImportRun gacha_events=5"
}

Assert-ComposePreflight
Invoke-Compose ps --status running db
Assert-RunningDbIdentity

$servicesStopped = $false
$needsB5Restore = $false
$primaryError = $null
$originB5ImportRun = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
$originB5Materialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
$originActivationSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
$originActivationEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$originActivationSequence")
$originEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")

try {
    Assert-B5State $originB5ImportRun $originB5Materialization
    Assert-OriginAnchor
    Assert-B5PublicReadiness
    Assert-DbPrivilegeContract
    $epochAfterReadiness = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($epochAfterReadiness -ne $originEpoch) { throw "B5 readiness changed the origin materialization epoch" }
    Write-Host "B5_ORIGIN_VERIFIED_OK alembic=v0007_gacha_timeline_slice active_revision=$b5Revision import_run=$originB5ImportRun materialization=$originB5Materialization activation_sequence=$originActivationSequence activation_epoch=$originActivationEpoch state_epoch=$originEpoch"

    $servicesStopped = $true
    Invoke-Compose stop web api scheduler
    $checkpointMount = "${A5CheckpointRoot}:/rollback:ro"
    $needsB5Restore = $true
    $rollbackOutput = & docker @compose run --rm --no-deps `
        --volume $checkpointMount `
        importer `
        python -m pcr_pipeline.import_pve `
        --research-core /rollback/research_core/pcr_tw_project `
        --manifest /app/scripts/research_core_rp_a5_manifest.sha256 `
        --manifest-sha256 $a5ManifestSha256 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Pinned RP-A5 activation failed: $($rollbackOutput -join [Environment]::NewLine)" }
    $proofLines = @($rollbackOutput | ForEach-Object { [string]$_ } | Where-Object { $_ -match '"status"\s*:\s*"PINNED_ROLLBACK_SOURCE_OK"' })
    if ($proofLines.Count -ne 1) { throw "RP-A5 activation did not emit one pinned-source proof" }
    $proof = $proofLines[0].Trim() | ConvertFrom-Json
    if ($proof.manifest_sha256 -ne $a5ManifestSha256 -or $proof.revision_id -ne $a5Revision -or [int]$proof.file_count -ne 48 -or [int]$proof.csv_row_count -ne 356) {
        throw "RP-A5 pinned-source proof is invalid"
    }
    Write-Host $proofLines[0].Trim()
    $a5Result = Get-ImportResult $rollbackOutput "RP-A5 activation"
    if (
        $a5Result.activated -ne $true -or $a5Result.revision_id -ne $a5Revision -or
        $a5Result.raw_tree_sha256 -ne $a5Revision -or $a5Result.semantic_tree_sha256 -ne $a5Semantic -or
        [int]$a5Result.file_count -ne 48 -or [int]$a5Result.csv_file_count -ne 13 -or
        [int]$a5Result.csv_row_count -ne 356
    ) { throw "RP-A5 ImportResult identity is invalid" }
    Assert-CountObject $a5Result.row_counts $a5RowCounts "RP-A5 ImportResult"
    $a5ImportRun = [string]$a5Result.import_run_id
    $a5Materialization = Get-Scalar "SELECT materialization_sha256 FROM core_revisions WHERE revision_id='$a5Revision' AND status='SUCCEEDED'"
    Assert-A5State "v0007_gacha_timeline_slice" $a5ImportRun $a5Materialization
    $a5Sequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $a5Epoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($a5Sequence -ne ($originActivationSequence + 1) -or $a5Epoch -le $originEpoch) { throw "A5 activation sequence or epoch did not advance exactly" }
    Assert-Activation $a5Sequence $b5Revision $a5Revision "ROLLBACK" $a5Epoch "RP-A5 rollback"
    Write-Host "A5_DATA_ROLLBACK_OK alembic=v0007_gacha_timeline_slice active_revision=$a5Revision import_run=$a5ImportRun materialization=$a5Materialization gacha_rows=0 activation_sequence=$a5Sequence epoch=$a5Epoch"

    Invoke-Compose run --rm --no-deps migration alembic -c database/alembic.ini downgrade v0006_arena_counter_slice
    Assert-A5State "v0006_arena_counter_slice" $a5ImportRun $a5Materialization
    Write-Host "B5_A5_SCHEMA_ROLLBACK_OK alembic=v0006_arena_counter_slice gacha_tables=0 active_revision=$a5Revision"

    Restore-B5
    $needsB5Restore = $false
}
catch {
    $primaryError = $_
}
finally {
    if ($needsB5Restore) {
        try { Restore-B5; $needsB5Restore = $false }
        catch {
            if ($null -eq $primaryError) { $primaryError = $_ }
            else { $primaryError = [System.Exception]::new("$($primaryError.Exception.Message); B5 restore also failed: $($_.Exception.Message)") }
        }
    }
    if ($servicesStopped -and -not $needsB5Restore) {
        try {
            Assert-B5State $originB5ImportRun $originB5Materialization
            Invoke-Compose up --detach --no-build --wait --wait-timeout 90 --no-deps scheduler api web
            Assert-B5PublicReadiness
            Invoke-Compose run --rm --no-deps revision-history-verify
            Write-Host "B5_SERVICES_READY_OK database=ok fixture=imported gacha_events=5"
        }
        catch {
            $restartError = $_
            try { Invoke-Compose stop web api scheduler }
            catch { $restartError = [System.Exception]::new("$($restartError.Exception.Message); service requiesce also failed: $($_.Exception.Message)") }
            if ($null -eq $primaryError) { $primaryError = $restartError }
            else { $primaryError = [System.Exception]::new("$($primaryError.Exception.Message); B5 readiness also failed: $($restartError.Exception.Message)") }
        }
    }
    elseif ($servicesStopped) {
        $message = "B5 restoration was not verified; services were left quiesced for manual recovery from the verified backup"
        Write-Warning "SERVICES_LEFT_QUIESCED: $message"
        if ($null -eq $primaryError) { $primaryError = [System.Exception]::new($message) }
    }
}

if ($null -ne $primaryError) { throw $primaryError }
Write-Host "B5_A5_ROLLBACK_DRILL_OK"
