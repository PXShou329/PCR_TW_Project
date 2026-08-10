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
    [string]$A6CheckpointRoot,
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
$A6CheckpointRoot = [System.IO.Path]::GetFullPath($A6CheckpointRoot)
$VerifiedBackupPath = [System.IO.Path]::GetFullPath($VerifiedBackupPath)
$a6Core = Join-Path $A6CheckpointRoot "research_core\pcr_tw_project"
$a6Manifest = Join-Path $repoRoot "scripts\research_core_rp_a6_0_manifest.sha256"
$b4Manifest = Join-Path $repoRoot "scripts\research_core_rp_b4_0_manifest.sha256"

if ($ProjectName -in @(
    "pcr-tw-a6", "pcr-tw-a6-parena", "pcr-tw-a6-parena-serial", "pcr-tw-a6-parena-drill",
    "pcr-tw-b5-gacha", "pcr-tw-a5-arena", "pcr-tw-a4-water", "pcr-tw-a3-fire",
    "pcr-tw-b1", "pcr-tw-b1-final"
)) {
    throw "ProjectName is reserved for an existing or legacy stack"
}
foreach ($requiredFile in @($EnvFile, $a6Manifest, $b4Manifest, $VerifiedBackupPath)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Missing B4 rollback drill input: $requiredFile"
    }
}
if (-not (Test-Path -LiteralPath $a6Core -PathType Container)) {
    throw "Missing immutable RP-A6 research core: $a6Core"
}

$b4ManifestSha256 = "eda30340c02f2f470475e652786104c521faf2ea4cc20be44cf09f3798fe8c5f"
$b4Revision = "1ba25a73df01ca8d9b161c60836d997f6db202a18d140ee1e92a7d96f62d7a17"
$b4Semantic = "46000a4a6f9ee70067876c7c1a73fd61d4d06a6f93c5b61831c15d41c9d8811e"
$b4ArtifactMirrorSha256 = "bb71dce87b8a651de794672741a5481a6b754861d694561974ce534e17eb9720"
$a6ManifestSha256 = "fbcac9cb9aadcd1569f881469189dc791c68a4a329637cc9db2c0d7263d68ed1"
$a6Revision = "3f5e738a6a7f0463583b38d0fc2ca1ae35bdc563f3815cf436dfc10913764d97"
$a6Semantic = "82495781cca66b9ca3fc221e609a3cb6c06ebaa823f7a8613c9d5d1d01d9e1ee"
$a6ArtifactMirrorSha256 = "e44a9fa38a89a5672d00c0a58d8b8946fecd41e541c08c9733fb3d06fbc1b88a"
$evidenceToClaimSha256 = "a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af"
$claimToEvidenceSha256 = "24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c"
$parenaTables = @(
    "arena_source_records", "parena_cases", "parena_case_matchups",
    "parena_case_sources", "parena_case_evidence", "parena_case_claims"
)
$a6RowCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 73; claims = 69; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
    gacha_timeline_events = 5; gacha_timeline_evidence = 10; gacha_timeline_claims = 8
    gacha_community_sources = 4; gacha_timeline_community_sources = 0
}
$a6PublicRowCounts = [ordered]@{}
foreach ($name in $a6RowCounts.Keys) {
    $a6PublicRowCounts[$name] = $a6RowCounts[$name]
}
foreach ($table in $parenaTables) {
    # The current B4 BaselineCounts schema keeps these fields required while an
    # immutable v4/A6 projection truthfully reports them as zero.
    $a6PublicRowCounts[$table] = 0
}
$a6ServingCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 73; claims = 69; stage_evidence = 47; stage_claims = 46
    team_evidence = 95; claim_evidence = 159; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
    gacha_timeline_events = 5; gacha_timeline_evidence = 10; gacha_timeline_claims = 8
    gacha_community_sources = 4; gacha_timeline_community_sources = 0
}
$b4RowCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 73; claims = 69; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
    gacha_timeline_events = 5; gacha_timeline_evidence = 10; gacha_timeline_claims = 8
    gacha_community_sources = 4; gacha_timeline_community_sources = 0
    arena_source_records = 6; parena_cases = 0; parena_case_matchups = 0
    parena_case_sources = 0; parena_case_evidence = 0; parena_case_claims = 0
}
$b4ServingCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 73; claims = 69; stage_evidence = 47; stage_claims = 46
    team_evidence = 95; claim_evidence = 159; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
    gacha_timeline_events = 5; gacha_timeline_evidence = 10; gacha_timeline_claims = 8
    gacha_community_sources = 4; gacha_timeline_community_sources = 0
    arena_source_records = 6; parena_cases = 0; parena_case_matchups = 0
    parena_case_sources = 0; parena_case_evidence = 0; parena_case_claims = 0
}

# Backup verification is the first mutation boundary: no Compose or database
# command may run before this independently retained artifact is authenticated.
$backupFile = Get-Item -LiteralPath $VerifiedBackupPath
if ($backupFile.Length -lt 1) { throw "Verified backup file is empty" }
$actualBackupSha256 = (Get-FileHash -LiteralPath $VerifiedBackupPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualBackupSha256 -ne $VerifiedBackupSha256.ToLowerInvariant()) {
    throw "Verified backup SHA-256 mismatch"
}
$actualA6ManifestSha256 = (Get-FileHash -LiteralPath $a6Manifest -Algorithm SHA256).Hash.ToLowerInvariant()
$actualB4ManifestSha256 = (Get-FileHash -LiteralPath $b4Manifest -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualA6ManifestSha256 -ne $a6ManifestSha256 -or $actualB4ManifestSha256 -ne $b4ManifestSha256) {
    throw "Release manifest file SHA-256 mismatch"
}
Write-Host "VERIFIED_BACKUP_INPUT_OK sha256=$actualBackupSha256 bytes=$($backupFile.Length)"
Write-Host "B4_A6_MANIFEST_INPUTS_OK b4=$actualB4ManifestSha256 a6=$actualA6ManifestSha256 b4_artifact=$b4ArtifactMirrorSha256 a6_artifact=$a6ArtifactMirrorSha256"

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
$ownerPassword = Get-Setting -Name "POSTGRES_PASSWORD"
$schedulerEnabled = (Get-Setting -Name "SCHEDULER_ENABLED" -Default "false").ToLowerInvariant()
$shadowMode = (Get-Setting -Name "SHADOW_MODE" -Default "true").ToLowerInvariant()
$autoPublish = (Get-Setting -Name "AUTO_PUBLISH" -Default "false").ToLowerInvariant()
if (
    $postgresUser -notmatch '^[a-zA-Z][a-zA-Z0-9_]{0,62}$' -or
    $postgresDatabase -notmatch '^[a-zA-Z][a-zA-Z0-9_]{0,40}$' -or
    [string]::IsNullOrWhiteSpace($ownerPassword)
) { throw "Database owner, database name, or password is invalid" }
if ($schedulerEnabled -ne "false" -or $shadowMode -ne "true" -or $autoPublish -ne "false") {
    throw "Scheduler must remain disabled in Shadow Mode with auto-publish off during rollback"
}
$encodedOwnerPassword = [Uri]::EscapeDataString($ownerPassword)
$ownerMigrationUrl = "postgresql+psycopg://$($postgresUser):$encodedOwnerPassword@db:5432/$postgresDatabase"
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
    if (($null -ne $db.ports -and @($db.ports).Count -ne 0) -or -not [bool]$config.networks.backend.internal) {
        throw "Database or backend network exposure violates the rollback boundary"
    }
    if (
        [string]$scheduler.environment.SCHEDULER_ENABLED -cne "false" -or
        [string]$scheduler.environment.SHADOW_MODE -cne "true" -or
        [string]$scheduler.environment.AUTO_PUBLISH -cne "false"
    ) { throw "Resolved scheduler safety flags drifted" }
    Write-Host "B4_COMPOSE_PREFLIGHT_OK project=$ProjectName api_image=$ExpectedApiImage scheduler_image=$ExpectedSchedulerImage api_port=$ExpectedApiPort web_port=$ExpectedWebPort scheduler_port=$ExpectedSchedulerPort"
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
        [string]$mounts[0].Name -cne "$($ProjectName)_pg_data"
    ) { throw "Running database is not the expected isolated project volume" }
    Write-Host "B4_DB_TARGET_OK project=$ProjectName container=$containerId volume=$($mounts[0].Name)"
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
    $marker = "DB_PRIVILEGES_OK matrix_checks=777 actual_denials=26 allowed_smokes=12"
    if ($exit -ne 0 -or @($lines | Where-Object { $_ -ceq $marker }).Count -ne 1) {
        throw "Database privilege verifier did not emit the exact 7-privilege B4 contract"
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

function Assert-ParenaTableShape {
    param([bool]$ExpectedPresent, [int]$ExpectedRows, [string]$Label)
    $values = ($parenaTables | ForEach-Object { "('$_')" }) -join ","
    $present = [int](Get-Scalar "SELECT COUNT(*) FROM (VALUES $values) AS required(name) WHERE to_regclass('public.' || name) IS NOT NULL")
    $expectedPresentCount = if ($ExpectedPresent) { 6 } else { 0 }
    if ($present -ne $expectedPresentCount) { throw "$Label P-Arena table set drifted" }
    if ($ExpectedPresent) {
        $rows = [int](Get-Scalar "SELECT (SELECT COUNT(*) FROM arena_source_records) + (SELECT COUNT(*) FROM parena_cases) + (SELECT COUNT(*) FROM parena_case_matchups) + (SELECT COUNT(*) FROM parena_case_sources) + (SELECT COUNT(*) FROM parena_case_evidence) + (SELECT COUNT(*) FROM parena_case_claims)")
        if ($rows -ne $ExpectedRows) { throw "$Label P-Arena row closure drifted" }
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

function Get-PinnedA6SourceProof {
    param([object[]]$Output, [string]$Label)
    $lines = @($Output | ForEach-Object { [string]$_ } | Where-Object {
        $_ -match '^\{.*"status"\s*:\s*"PINNED_ROLLBACK_SOURCE_OK"'
    })
    if ($lines.Count -ne 1) { throw "$Label did not emit exactly one pinned-source proof" }
    try { $proof = $lines[0].Trim() | ConvertFrom-Json }
    catch { throw "$Label pinned-source proof JSON is invalid" }
    if (
        $proof.status -ne "PINNED_ROLLBACK_SOURCE_OK" -or
        $proof.manifest_sha256 -ne $a6ManifestSha256 -or
        $proof.revision_id -ne $a6Revision -or
        [int]$proof.file_count -ne 48 -or [int]$proof.csv_row_count -ne 376
    ) { throw "$Label pinned-source proof is invalid" }
    return [pscustomobject]@{ Proof = $proof; Line = $lines[0].Trim() }
}

function Assert-RevisionIdentity {
    param(
        [string]$Revision,
        [string]$ManifestSha256,
        [string]$SemanticSha256,
        [string]$ImportRunId,
        [string]$MaterializationSha256,
        [int]$SchemaVersion,
        [int]$TableCount,
        [System.Collections.IDictionary]$RowCounts,
        [string]$Label
    )
    $values = Get-Scalar "SELECT manifest_sha256 || '|' || raw_tree_sha256 || '|' || semantic_tree_sha256 || '|' || status || '|' || file_count || '|' || csv_file_count || '|' || csv_row_count || '|' || evidence_to_claim_count || '|' || evidence_to_claim_sha256 || '|' || claim_to_evidence_count || '|' || claim_to_evidence_sha256 || '|' || COALESCE(materialization_sha256, '') || '|' || COALESCE(import_run_id::text, '') FROM core_revisions WHERE revision_id='$Revision'"
    $expected = "$ManifestSha256|$Revision|$SemanticSha256|SUCCEEDED|48|13|376|120|$evidenceToClaimSha256|298|$claimToEvidenceSha256|$MaterializationSha256|$ImportRunId"
    if ($values -ne $expected) { throw "$Label CoreRevision identity drifted" }
    $run = Get-Scalar "SELECT status || '|' || fixture_sha256 || '|' || canonical_source || '|' || COALESCE(manifest#>>'{materialization,schema_version}', '') || '|' || COALESCE(manifest#>>'{materialization,sha256}', '') || '|' || (SELECT count(*) FROM jsonb_object_keys(CASE WHEN jsonb_typeof(manifest#>'{materialization,tables}')='object' THEN manifest#>'{materialization,tables}' ELSE '{}'::jsonb END)) FROM import_runs WHERE id='$ImportRunId'"
    if ($run -ne "SUCCEEDED|$Revision|research_core_file_ssot|$SchemaVersion|$MaterializationSha256|$TableCount") {
        throw "$Label ImportRun identity drifted"
    }
    $counts = (Get-Scalar "SELECT row_counts::text FROM import_runs WHERE id='$ImportRunId'") | ConvertFrom-Json
    Assert-CountObject $counts $RowCounts "$Label ImportRun"
}

function Assert-ActiveState {
    param(
        [string]$ExpectedAlembic,
        [string]$Revision,
        [string]$ManifestSha256,
        [string]$SemanticSha256,
        [string]$ExpectedRun,
        [string]$ExpectedMaterialization,
        [int]$SchemaVersion,
        [int]$TableCount,
        [System.Collections.IDictionary]$RowCounts,
        [System.Collections.IDictionary]$ServingCounts,
        [bool]$ParenaPresent,
        [int]$ParenaRows,
        [string]$Label
    )
    $alembic = Get-Scalar "SELECT version_num FROM alembic_version"
    $activeRevision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $activeRun = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $activeMaterialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    if (
        $alembic -ne $ExpectedAlembic -or $activeRevision -ne $Revision -or
        $activeRun -ne $ExpectedRun -or $activeMaterialization -ne $ExpectedMaterialization
    ) { throw "$Label database state is not safe for recovery or restart" }
    Assert-RevisionIdentity $Revision $ManifestSha256 $SemanticSha256 $ExpectedRun `
        $ExpectedMaterialization $SchemaVersion $TableCount $RowCounts $Label
    $counts = (Get-Scalar "SELECT serving_counts::text FROM materialization_state WHERE id=1") | ConvertFrom-Json
    Assert-CountObject $counts $ServingCounts "$Label MaterializationState"
    Assert-DatabaseCounts $ServingCounts $Label
    Assert-ParenaTableShape $ParenaPresent $ParenaRows $Label
}

function Assert-B4State {
    param([string]$ExpectedRun, [string]$ExpectedMaterialization)
    Assert-ActiveState "v0008_parena_planner_slice" $b4Revision $b4ManifestSha256 `
        $b4Semantic $ExpectedRun $ExpectedMaterialization 5 29 $b4RowCounts `
        $b4ServingCounts $true 6 "B4"
}

function Assert-A6StateAtV8 {
    param([string]$ExpectedRun, [string]$ExpectedMaterialization)
    Assert-ActiveState "v0008_parena_planner_slice" $a6Revision $a6ManifestSha256 `
        $a6Semantic $ExpectedRun $ExpectedMaterialization 4 23 $a6RowCounts `
        $a6ServingCounts $true 0 "A6 at V0008"
}

function Assert-A6StateAtV7 {
    param([string]$ExpectedRun, [string]$ExpectedMaterialization)
    Assert-ActiveState "v0007_gacha_timeline_slice" $a6Revision $a6ManifestSha256 `
        $a6Semantic $ExpectedRun $ExpectedMaterialization 4 23 $a6RowCounts `
        $a6ServingCounts $false 0 "A6 at V0007"
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

function Assert-OriginAnchor {
    $kind = Get-Scalar "SELECT kind FROM revision_activations WHERE sequence_no=$originActivationSequence"
    if ($kind -notin @("IMPORT", "REACTIVATE")) { throw "Origin B4 activation is not forward-moving" }
    $from = Get-Scalar "SELECT COALESCE(from_revision_id, '') FROM revision_activations WHERE sequence_no=$originActivationSequence"
    if ($originActivationEpoch -le 0 -or $originActivationEpoch -gt $originEpoch) {
        throw "Origin B4 activation epoch is invalid"
    }
    Assert-Activation $originActivationSequence $from $b4Revision $kind $originActivationEpoch "Origin B4"
}

function Assert-RecoveryChain {
    $sequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $stateEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    $rollbackEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$($originActivationSequence + 1)")
    $reactivateEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$($originActivationSequence + 2)")
    if (
        $sequence -ne ($originActivationSequence + 2) -or
        $rollbackEpoch -le $originEpoch -or
        $reactivateEpoch -le $rollbackEpoch -or
        $stateEpoch -ne $reactivateEpoch
    ) { throw "B4 recovery activation sequence or epoch chain is invalid" }
    Assert-Activation ($originActivationSequence + 1) $b4Revision $a6Revision "ROLLBACK" $rollbackEpoch "A6 rollback"
    Assert-Activation ($originActivationSequence + 2) $a6Revision $b4Revision "REACTIVATE" $reactivateEpoch "B4 reactivation"
}

function Get-HttpJson {
    param([string]$Uri, [string]$Method = "Get", [string]$Body = "")
    $arguments = @{
        Uri = $Uri
        Method = $Method
        TimeoutSec = 10
        SkipHttpErrorCheck = $true
    }
    if ($Body) {
        $arguments.ContentType = "application/json"
        $arguments.Body = $Body
    }
    $response = Invoke-WebRequest @arguments
    try { $payload = $response.Content | ConvertFrom-Json }
    catch { throw "Endpoint did not return JSON: $Uri" }
    return [pscustomobject]@{ StatusCode = [int]$response.StatusCode; Payload = $payload }
}

function Assert-PublicReadiness {
    param(
        [ValidateSet("B4", "A6")][string]$Label,
        [string]$ExpectedRevision,
        [string]$ExpectedSemantic,
        [string]$ExpectedImportRun,
        [string]$ExpectedMaterialization,
        [string]$ExpectedApplicationVersion,
        [System.Collections.IDictionary]$ExpectedRowCounts,
        [bool]$ExpectParenaMaterialization
    )
    $apiPort = Get-ActualPort "api" 8000 $ExpectedApiPort
    $webPort = Get-ActualPort "web" 3000 $ExpectedWebPort
    $schedulerPort = Get-ActualPort "scheduler" 8081 $ExpectedSchedulerPort
    $ready = Invoke-RestMethod "http://127.0.0.1:$apiPort/health/ready" -TimeoutSec 10
    $baseline = Invoke-RestMethod "http://127.0.0.1:$apiPort/api/v1/baseline" -TimeoutSec 10
    $gacha = Invoke-RestMethod "http://127.0.0.1:$apiPort/api/v1/gacha/timeline" -TimeoutSec 10
    $community = Invoke-RestMethod "http://127.0.0.1:$apiPort/api/v1/gacha/community-sources" -TimeoutSec 10
    $characters = Invoke-RestMethod "http://127.0.0.1:$apiPort/api/v1/pvp/characters" -TimeoutSec 10
    $availableKeys = @(
        $characters.data |
            Where-Object { $_.tw_availability_status -eq "AVAILABLE" } |
            Select-Object -First 15 |
            ForEach-Object { $_.unit_key }
    )
    if ($availableKeys.Count -ne 15 -or @($availableKeys | Select-Object -Unique).Count -ne 15) {
        throw "$Label public API did not expose 15 distinct TW AVAILABLE units"
    }
    $requestBody = [ordered]@{
        server = "TW"
        environment_version = "TW-ROLLBACK-$Label"
        defense_teams = @(
            @($availableKeys[0..4]), @($availableKeys[5..9]), @($availableKeys[10..14])
        )
    } | ConvertTo-Json -Depth 5 -Compress
    $parenaEnvironments = Get-HttpJson "http://127.0.0.1:$apiPort/api/v1/parena/environments"
    $parenaSolver = Get-HttpJson "http://127.0.0.1:$apiPort/api/v1/solver/parena" "Post" $requestBody
    $webHealth = Invoke-RestMethod "http://127.0.0.1:$webPort/api/health" -TimeoutSec 10
    $gachaPage = Invoke-WebRequest "http://127.0.0.1:$webPort/gacha" -TimeoutSec 10
    $parenaPage = Invoke-WebRequest "http://127.0.0.1:$webPort/parena" -TimeoutSec 10
    $scheduler = Invoke-RestMethod "http://127.0.0.1:$schedulerPort/health" -TimeoutSec 10
    $gachaRows = @($gacha.data)
    $eventIds = @($gachaRows | ForEach-Object { $_.event_id })
    $expectedEventIds = @(
        "JP_20260630_shefi_vardrache", "JP_20260703_luisemarie_summer",
        "JP_20260731_fubuki_summer", "JP_20260815_vampy_summer", "JP_20260823_tia"
    )
    Assert-CountObject $baseline.data.counts $ExpectedRowCounts "$Label public baseline"
    if (
        $ready.status -ne "ok" -or $ready.checks.database -ne "ok" -or
        $ready.checks.fixture -ne "imported" -or
        $baseline.data.application_version -ne $ExpectedApplicationVersion -or
        $baseline.meta.source.canonical_source -ne "research_core_file_ssot" -or
        $baseline.meta.source.fixture_sha256 -ne $ExpectedRevision -or
        $baseline.meta.source.revision_id -ne $ExpectedRevision -or
        $baseline.meta.source.raw_tree_sha256 -ne $ExpectedRevision -or
        $baseline.meta.source.semantic_tree_sha256 -ne $ExpectedSemantic -or
        $baseline.meta.source.import_run_id -ne $ExpectedImportRun -or
        $baseline.meta.source.materialization_sha256 -ne $ExpectedMaterialization -or
        $gachaRows.Count -ne 5 -or @($community.data).Count -ne 4 -or
        ($eventIds -join "|") -ne ($expectedEventIds -join "|") -or
        $webHealth.status -ne "ok" -or $gachaPage.StatusCode -ne 200 -or
        $gachaPage.Content -notmatch "抽卡未來視" -or
        $parenaPage.StatusCode -ne 200 -or
        $parenaPage.Content -notmatch "公主競技場三隊規劃" -or
        [bool]$scheduler.enabled -or -not [bool]$scheduler.shadow_mode -or
        [bool]$scheduler.canonical_write_capable
    ) { throw "$Label public readiness or Shadow Mode contract failed" }
    if ($ExpectParenaMaterialization) {
        if (
            $parenaEnvironments.StatusCode -ne 200 -or
            @($parenaEnvironments.Payload.data).Count -ne 0 -or
            @($parenaEnvironments.Payload.meta.warnings) -notcontains "NO_MATURE_PARENA_CASE" -or
            $parenaSolver.StatusCode -ne 200 -or
            $parenaSolver.Payload.data.match_type -ne "EXACT" -or
            [bool]$parenaSolver.Payload.data.similar_enabled -or
            @($parenaSolver.Payload.data.cases).Count -ne 0 -or
            @($parenaSolver.Payload.meta.warnings) -notcontains "NO_MATURE_PARENA_CASE"
        ) { throw "B4 P-Arena zero-case truth contract failed" }
    }
    else {
        if (
            $parenaEnvironments.StatusCode -ne 503 -or
            $parenaEnvironments.Payload.detail.code -ne "NO_PARENA_MATERIALIZATION" -or
            $parenaSolver.StatusCode -ne 503 -or
            $parenaSolver.Payload.detail.code -ne "NO_PARENA_MATERIALIZATION" -or
            $parenaPage.Content -notmatch "NO_PARENA_MATERIALIZATION"
        ) { throw "A6 P-Arena fail-closed contract failed" }
    }
    Write-Host "$($Label)_PUBLIC_READINESS_OK api_port=$apiPort web_port=$webPort scheduler_port=$schedulerPort revision=$ExpectedRevision import_run=$ExpectedImportRun materialization=$ExpectedMaterialization gacha_events=5 gacha_sources=4 parena_materialized=$($ExpectParenaMaterialization.ToString().ToLowerInvariant())"
}

function Assert-B4PublicReadiness {
    Assert-PublicReadiness "B4" $b4Revision $b4Semantic $originB4ImportRun `
        $originB4Materialization "3.0.0-b4" $b4RowCounts $true
}

function Assert-A6PublicReadiness {
    Assert-PublicReadiness "A6" $a6Revision $a6Semantic $a6ImportRun `
        $a6Materialization $a6ExpectedApplicationVersion $a6PublicRowCounts $false
}

function Invoke-Migration {
    param([ValidateSet("upgrade", "downgrade")][string]$Direction, [string]$Target, [string]$Label)
    $output = & docker @compose run --rm --no-deps `
        --env "PCR_DATABASE_URL=$ownerMigrationUrl" `
        migration `
        alembic -c database/alembic.ini $Direction $Target 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "$Label migration failed: $($output -join [Environment]::NewLine)"
    }
    $output | ForEach-Object { Write-Host $_ }
}

function Get-RecoveryMode {
    $alembic = Get-Scalar "SELECT version_num FROM alembic_version"
    $revision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $sequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $epoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($revision -eq $b4Revision -and $alembic -eq "v0008_parena_planner_slice") {
        Assert-B4State $originB4ImportRun $originB4Materialization
        if ($sequence -eq $originActivationSequence -and $epoch -eq $originEpoch) {
            Assert-OriginAnchor
            return "ORIGIN_NOOP"
        }
        if ($sequence -eq ($originActivationSequence + 2)) {
            Assert-RecoveryChain
            return "ALREADY_RESTORED_NOOP"
        }
        throw "Active B4 chronology is neither origin nor the exact restored chain"
    }
    if ($revision -eq $a6Revision -and $sequence -eq ($originActivationSequence + 1)) {
        if ([string]::IsNullOrWhiteSpace($script:a6ImportRun)) {
            $script:a6ImportRun = Get-Scalar "SELECT COALESCE(import_run_id::text, '') FROM core_revisions WHERE revision_id='$a6Revision' AND status='SUCCEEDED'"
            $script:a6Materialization = Get-Scalar "SELECT COALESCE(materialization_sha256, '') FROM core_revisions WHERE revision_id='$a6Revision' AND status='SUCCEEDED'"
        }
        if ($alembic -eq "v0007_gacha_timeline_slice") {
            Assert-A6StateAtV7 $a6ImportRun $a6Materialization
            Invoke-Migration "upgrade" "head" "A6 V0007 to V0008 recovery"
            Assert-A6StateAtV8 $a6ImportRun $a6Materialization
        }
        elseif ($alembic -eq "v0008_parena_planner_slice") {
            Assert-A6StateAtV8 $a6ImportRun $a6Materialization
        }
        else {
            throw "A6 recovery schema is neither V0007 nor V0008"
        }
        $rollbackEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
        if ($rollbackEpoch -le $originEpoch) { throw "A6 rollback epoch did not advance" }
        Assert-Activation ($originActivationSequence + 1) $b4Revision $a6Revision `
            "ROLLBACK" $rollbackEpoch "A6 recovery"
        return "A6_REACTIVATE"
    }
    throw "Recovery state is neither origin B4, exact A6 rollback, nor restored B4"
}

function Restore-B4 {
    $mode = Get-RecoveryMode
    $expectedActivated = $mode -eq "A6_REACTIVATE"
    Write-Host "B4_RECOVERY_MODE_OK mode=$mode expected_activated=$($expectedActivated.ToString().ToLowerInvariant())"
    Invoke-Compose run --rm --no-deps role-provision
    Assert-DbPrivilegeContract
    $output = & docker @compose run --rm --no-deps importer 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Canonical B4 restoration import failed" }
    $baseline = @($output | ForEach-Object { [string]$_ } | Where-Object { $_ -match '^RESEARCH_BASELINE_OK\s*\|' })
    if ($baseline.Count -ne 1 -or $baseline[0] -notmatch [regex]::Escape("manifest_sha256=$b4ManifestSha256")) {
        throw "Canonical B4 restoration did not emit the pinned baseline proof"
    }
    Write-Host $baseline[0].Trim()
    $result = Get-ImportResult $output "B4 restoration"
    if (
        $result.created -ne $false -or $result.activated -ne $expectedActivated -or
        $result.revision_id -ne $b4Revision -or $result.raw_tree_sha256 -ne $b4Revision -or
        $result.semantic_tree_sha256 -ne $b4Semantic -or [int]$result.file_count -ne 48 -or
        [int]$result.csv_file_count -ne 13 -or [int]$result.csv_row_count -ne 376 -or
        $result.import_run_id -ne $originB4ImportRun
    ) { throw "B4 restoration ImportResult identity is invalid" }
    Assert-CountObject $result.row_counts $b4RowCounts "B4 restoration ImportResult"
    Assert-B4State $originB4ImportRun $originB4Materialization
    Assert-DbPrivilegeContract
    if ($mode -eq "ORIGIN_NOOP") { Assert-OriginAnchor }
    else { Assert-RecoveryChain }
    Write-Host "B4_RESTORED_OK mode=$mode alembic=v0008_parena_planner_slice active_revision=$b4Revision import_run=$originB4ImportRun artifact_diagnostic=$b4ArtifactMirrorSha256"
}

Assert-ComposePreflight
Invoke-Compose ps --status running db
Assert-RunningDbIdentity

$servicesStopped = $false
$needsB4Restore = $false
$intermediateServicesMayRun = $false
$primaryError = $null
$originB4ImportRun = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
$originB4Materialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
$originActivationSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
$originActivationEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$originActivationSequence")
$originEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
$a6ImportRun = ""
$a6Materialization = ""
$a6ExpectedCreated = $true
$a6ExpectedApplicationVersion = "3.0.0-b4"
$checkpointMount = "$($A6CheckpointRoot):/rollback:ro"
$a6SourceVerifierCode = "from pathlib import Path; from pcr_pipeline.import_pve import _verify_import_source; _verify_import_source(Path('/rollback/research_core/pcr_tw_project'), Path('/app/scripts/research_core_rp_a6_0_manifest.sha256'), '$a6ManifestSha256', Path('/app/scripts/check_research_baseline.py'))"

try {
    Assert-B4State $originB4ImportRun $originB4Materialization
    $a6HistoryCount = [int](Get-Scalar "SELECT COUNT(*) FROM core_revisions WHERE revision_id='$a6Revision'")
    if ($a6HistoryCount -eq 1) {
        $a6ExpectedCreated = $false
        $a6ImportRun = Get-Scalar "SELECT COALESCE(import_run_id::text, '') FROM core_revisions WHERE revision_id='$a6Revision' AND status='SUCCEEDED'"
        $a6Materialization = Get-Scalar "SELECT COALESCE(materialization_sha256, '') FROM core_revisions WHERE revision_id='$a6Revision' AND status='SUCCEEDED'"
        $a6ExpectedApplicationVersion = Get-Scalar "SELECT COALESCE(application_version, '') FROM import_runs WHERE id='$a6ImportRun' AND status='SUCCEEDED'"
        if (
            $a6ImportRun -notmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' -or
            $a6Materialization -notmatch '^[0-9a-f]{64}$' -or
            $a6ExpectedApplicationVersion -notin @("3.0.0-a6", "3.0.0-b4")
        ) { throw "Existing immutable A6 release evidence is incomplete" }
        Assert-RevisionIdentity $a6Revision $a6ManifestSha256 $a6Semantic $a6ImportRun `
            $a6Materialization 4 23 $a6RowCounts "Immutable A6"
        Write-Host "A6_IMMUTABLE_RELEASE_INPUT_OK history=present expected_create=false revision=$a6Revision import_run=$a6ImportRun materialization=$a6Materialization application_version=$a6ExpectedApplicationVersion files=48 csv=13 rows=376 edges=120/298"
    }
    elseif ($a6HistoryCount -eq 0) {
        Write-Host "A6_IMMUTABLE_RELEASE_INPUT_OK history=absent expected_create=true revision=$a6Revision manifest=$a6ManifestSha256 files=48 csv=13 rows=376 edges=120/298"
    }
    else {
        throw "A6 CoreRevision uniqueness invariant failed"
    }

    Assert-OriginAnchor
    Assert-B4PublicReadiness
    Assert-DbPrivilegeContract
    Assert-B4State $originB4ImportRun $originB4Materialization
    $epochAfterReadiness = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    $sequenceAfterReadiness = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    if ($epochAfterReadiness -ne $originEpoch -or $sequenceAfterReadiness -ne $originActivationSequence) {
        throw "B4 origin readiness changed chronology or materialization epoch"
    }
    Write-Host "B4_ORIGIN_VERIFIED_OK alembic=v0008_parena_planner_slice active_revision=$b4Revision import_run=$originB4ImportRun materialization=$originB4Materialization activation_sequence=$originActivationSequence activation_epoch=$originActivationEpoch state_epoch=$originEpoch"

    # This full tree proof must complete before servicesStopped becomes true.
    $preflightProofOutput = & docker @compose run --rm --no-deps `
        --volume $checkpointMount `
        importer `
        python -c $a6SourceVerifierCode 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Immutable RP-A6 checkpoint preflight failed" }
    $preflightProof = Get-PinnedA6SourceProof $preflightProofOutput "RP-A6 checkpoint preflight"
    Assert-B4State $originB4ImportRun $originB4Materialization
    $sequenceAfterCheckpointProof = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $epochAfterCheckpointProof = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($sequenceAfterCheckpointProof -ne $originActivationSequence -or $epochAfterCheckpointProof -ne $originEpoch) {
        throw "Read-only A6 checkpoint verification changed B4 chronology or epoch"
    }
    Write-Host $preflightProof.Line
    Write-Host "A6_CHECKPOINT_PREFLIGHT_OK revision=$a6Revision manifest=$a6ManifestSha256 files=48 rows=376 activation_sequence=$sequenceAfterCheckpointProof epoch=$epochAfterCheckpointProof"

    $servicesStopped = $true
    $needsB4Restore = $true
    Invoke-Compose stop web api scheduler

    $rollbackOutput = & docker @compose run --rm --no-deps `
        --volume $checkpointMount `
        importer `
        python -m pcr_pipeline.import_pve `
        --research-core /rollback/research_core/pcr_tw_project `
        --manifest /app/scripts/research_core_rp_a6_0_manifest.sha256 `
        --manifest-sha256 $a6ManifestSha256 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Pinned RP-A6 activation failed" }
    $activationProof = Get-PinnedA6SourceProof $rollbackOutput "RP-A6 activation"
    Write-Host $activationProof.Line
    $a6Result = Get-ImportResult $rollbackOutput "RP-A6 activation"
    if (
        $a6Result.created -ne $a6ExpectedCreated -or $a6Result.activated -ne $true -or
        $a6Result.revision_id -ne $a6Revision -or $a6Result.raw_tree_sha256 -ne $a6Revision -or
        $a6Result.semantic_tree_sha256 -ne $a6Semantic -or [int]$a6Result.file_count -ne 48 -or
        [int]$a6Result.csv_file_count -ne 13 -or [int]$a6Result.csv_row_count -ne 376
    ) { throw "RP-A6 ImportResult identity is invalid" }
    Assert-CountObject $a6Result.row_counts $a6RowCounts "RP-A6 ImportResult"
    $a6ImportRun = [string]$a6Result.import_run_id
    $a6Materialization = Get-Scalar "SELECT COALESCE(materialization_sha256, '') FROM core_revisions WHERE revision_id='$a6Revision' AND status='SUCCEEDED'"
    if (
        $a6ImportRun -notmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' -or
        $a6Materialization -notmatch '^[0-9a-f]{64}$'
    ) { throw "RP-A6 import did not establish immutable release evidence" }
    Assert-A6StateAtV8 $a6ImportRun $a6Materialization
    Invoke-Compose run --rm --no-deps role-provision
    Assert-DbPrivilegeContract
    $a6Sequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $a6Epoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($a6Sequence -ne ($originActivationSequence + 1) -or $a6Epoch -le $originEpoch) {
        throw "A6 activation sequence or epoch did not advance exactly"
    }
    Assert-Activation $a6Sequence $b4Revision $a6Revision "ROLLBACK" $a6Epoch "RP-A6 rollback"
    Write-Host "B4_A6_DATA_ROLLBACK_OK alembic=v0008_parena_planner_slice active_revision=$a6Revision import_run=$a6ImportRun materialization=$a6Materialization activation_sequence=$a6Sequence epoch=$a6Epoch parena_rows=0"

    # V0008 downgrade is allowed only after the importer has established the
    # exact immutable A6 v4/23 owner and cleared all six P-Arena tables.
    Assert-A6StateAtV8 $a6ImportRun $a6Materialization
    Invoke-Migration "downgrade" "v0007_gacha_timeline_slice" "A6 guarded V0008 to V0007"
    Assert-A6StateAtV7 $a6ImportRun $a6Materialization
    $sequenceAfterDowngrade = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $epochAfterDowngrade = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($sequenceAfterDowngrade -ne $a6Sequence -or $epochAfterDowngrade -ne $a6Epoch) {
        throw "V0008 to V0007 migration changed A6 chronology or epoch"
    }
    Write-Host "B4_A6_SCHEMA_DOWNGRADE_OK from=v0008_parena_planner_slice to=v0007_gacha_timeline_slice active_revision=$a6Revision parena_tables=0"

    $intermediateServicesMayRun = $true
    Invoke-Compose up --detach --no-build --wait --wait-timeout 90 --no-deps scheduler api web
    Assert-A6PublicReadiness
    Assert-A6StateAtV7 $a6ImportRun $a6Materialization
    $a6ServingSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $a6ServingEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($a6ServingSequence -ne $a6Sequence -or $a6ServingEpoch -ne $a6Epoch) {
        throw "A6 public readiness changed rollback chronology or epoch"
    }
    Write-Host "A6_INTERMEDIATE_SERVICES_READY_OK api_image=$ExpectedApiImage scheduler_image=$ExpectedSchedulerImage activation_sequence=$a6ServingSequence epoch=$a6ServingEpoch parena_endpoints=503"
    Invoke-Compose stop web api scheduler
    $intermediateServicesMayRun = $false
    Assert-A6StateAtV7 $a6ImportRun $a6Materialization
    Write-Host "A6_INTERMEDIATE_SERVICES_STOPPED_OK active_revision=$a6Revision"

    Invoke-Migration "upgrade" "head" "A6 V0007 to V0008 reactivation preparation"
    Assert-A6StateAtV8 $a6ImportRun $a6Materialization
    Write-Host "A6_B4_SCHEMA_UPGRADE_OK from=v0007_gacha_timeline_slice to=v0008_parena_planner_slice active_revision=$a6Revision parena_tables=6 parena_rows=0"

    Restore-B4
    $needsB4Restore = $false
}
catch {
    $primaryError = $_
}
finally {
    if ($needsB4Restore -and $intermediateServicesMayRun) {
        try {
            Invoke-Compose stop web api scheduler
            $intermediateServicesMayRun = $false
            Write-Host "A6_INTERMEDIATE_SERVICES_RECOVERY_STOP_OK"
        }
        catch {
            if ($null -eq $primaryError) { $primaryError = $_ }
            else {
                $primaryError = [System.Exception]::new(
                    "$($primaryError.Exception.Message); intermediate service stop also failed: $($_.Exception.Message)"
                )
            }
        }
    }
    if ($needsB4Restore -and -not $intermediateServicesMayRun) {
        try {
            Restore-B4
            $needsB4Restore = $false
        }
        catch {
            if ($null -eq $primaryError) { $primaryError = $_ }
            else {
                $primaryError = [System.Exception]::new(
                    "$($primaryError.Exception.Message); B4 restore also failed: $($_.Exception.Message)"
                )
            }
        }
    }
    if ($servicesStopped -and -not $needsB4Restore) {
        try {
            Assert-B4State $originB4ImportRun $originB4Materialization
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
                throw "Final B4 state is neither exact origin nor the exact rollback/reactivation chain"
            }
            Invoke-Compose up --detach --no-build --wait --wait-timeout 90 --no-deps scheduler api web
            Assert-B4PublicReadiness
            Assert-DbPrivilegeContract
            Invoke-Compose run --rm --no-deps revision-history-verify
            $finalEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
            $finalSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
            if ($finalSequence -ne $preRestartSequence -or $finalEpoch -ne $preRestartEpoch) {
                throw "Final B4 readiness changed the verified chronology or epoch"
            }
            if ($finalChronology -eq "ORIGIN_NOOP") { Assert-OriginAnchor }
            else { Assert-RecoveryChain }
            Write-Host "B4_SERVICES_READY_OK database=ok fixture=imported gacha_events=5 parena_cases=0 chronology=$finalChronology activation_sequence=$finalSequence epoch=$finalEpoch"
        }
        catch {
            $restartError = $_
            try { Invoke-Compose stop web api scheduler }
            catch {
                $restartError = [System.Exception]::new(
                    "$($restartError.Exception.Message); service requiesce also failed: $($_.Exception.Message)"
                )
            }
            if ($null -eq $primaryError) { $primaryError = $restartError }
            else {
                $primaryError = [System.Exception]::new(
                    "$($primaryError.Exception.Message); B4 readiness also failed: $($restartError.Exception.Message)"
                )
            }
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
            "B4 restoration was not verified and intermediate service shutdown failed; use the verified backup before serving traffic"
        }
        else {
            "B4 restoration was not verified; services were left quiesced for manual recovery from the verified backup"
        }
        Write-Warning "$($warningMarker): $message"
        if ($null -eq $primaryError) { $primaryError = [System.Exception]::new($message) }
    }
}

if ($null -ne $primaryError) { throw $primaryError }
Write-Host "B4_A6_ROLLBACK_DRILL_OK"
