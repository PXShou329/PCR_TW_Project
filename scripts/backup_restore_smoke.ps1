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
    [string]$PostgresUser,
    [string]$SourceDatabase,
    [switch]$SeedRevisionHistory,
    [switch]$KeepBackup,
    [Parameter(HelpMessage = "Keep the full restored A6 database. The destructive empty-Gacha downgrade probe always uses a separate disposable database.")]
    [switch]$KeepRestoredDatabase
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$composeFile = Join-Path $repoRoot "infra\compose.yml"
$EnvFile = [System.IO.Path]::GetFullPath($EnvFile)
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Missing private environment file: $EnvFile"
}

function Get-Setting {
    param([string]$Name, [string]$Default = "")
    $processValue = [Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($processValue)) {
        return $processValue
    }
    foreach ($line in Get-Content -LiteralPath $EnvFile) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }
        $prefix = "$Name="
        if ($trimmed.StartsWith($prefix, [StringComparison]::Ordinal)) {
            $value = $trimmed.Substring($prefix.Length).Trim()
            if (
                $value.Length -ge 2 -and
                (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                 ($value.StartsWith("'") -and $value.EndsWith("'")))
            ) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            return $value
        }
    }
    return $Default
}

if ($ProjectName -in @("pcr-tw-b5-gacha", "pcr-tw-a5-arena", "pcr-tw-a4-water", "pcr-tw-b1")) {
    throw "ProjectName is reserved for an existing or legacy stack"
}
if (-not $PostgresUser) {
    $PostgresUser = Get-Setting -Name "POSTGRES_USER" -Default "pcr_owner"
}
if (-not $SourceDatabase) {
    $SourceDatabase = Get-Setting -Name "POSTGRES_DB" -Default "pcr_tw"
}
if ($SourceDatabase -notmatch '^[a-zA-Z][a-zA-Z0-9_]{0,40}$') {
    throw "SourceDatabase contains unsupported characters"
}
if ($PostgresUser -notmatch '^[a-zA-Z][a-zA-Z0-9_]{0,62}$') {
    throw "PostgresUser contains unsupported characters"
}
$ownerPassword = Get-Setting -Name "POSTGRES_PASSWORD"
$apiPassword = Get-Setting -Name "PCR_API_DB_PASSWORD"
$importerPassword = Get-Setting -Name "PCR_IMPORTER_DB_PASSWORD"
$schedulerPassword = Get-Setting -Name "PCR_SCHEDULER_DB_PASSWORD"
foreach ($required in @(
    @{ Name = "POSTGRES_PASSWORD"; Value = $ownerPassword },
    @{ Name = "PCR_API_DB_PASSWORD"; Value = $apiPassword },
    @{ Name = "PCR_IMPORTER_DB_PASSWORD"; Value = $importerPassword },
    @{ Name = "PCR_SCHEDULER_DB_PASSWORD"; Value = $schedulerPassword }
)) {
    if ([string]::IsNullOrWhiteSpace($required.Value)) {
        throw "$($required.Name) is required for restored least-privilege API verification"
    }
}
$encodedApiPassword = [Uri]::EscapeDataString($apiPassword)
$encodedImporterPassword = [Uri]::EscapeDataString($importerPassword)
$a6ManifestSha256 = "fbcac9cb9aadcd1569f881469189dc791c68a4a329637cc9db2c0d7263d68ed1"
$a6Revision = "3f5e738a6a7f0463583b38d0fc2ca1ae35bdc563f3815cf436dfc10913764d97"
$a6Semantic = "82495781cca66b9ca3fc221e609a3cb6c06ebaa823f7a8613c9d5d1d01d9e1ee"
$a6ArtifactMirrorSha256 = "e44a9fa38a89a5672d00c0a58d8b8946fecd41e541c08c9733fb3d06fbc1b88a"
$a6EvidenceToClaimSha256 = "a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af"
$a6ClaimToEvidenceSha256 = "24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c"
$a6RowCounts = [ordered]@{
    stages = 3; teams = 10; team_members = 50; characters = 35
    evidence = 73; claims = 69; operation_timelines = 15; timeline_steps = 37
    arena_defenses = 1; arena_defense_members = 5; arena_counters = 2
    arena_counter_members = 10; arena_counter_evidence = 4; arena_counter_claims = 4
    gacha_timeline_events = 5; gacha_timeline_evidence = 10; gacha_timeline_claims = 8
    gacha_community_sources = 4; gacha_timeline_community_sources = 0
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

$configuredBackupRoot = Get-Setting -Name "BACKUP_DIR" -Default "..\.runtime\backups"
if ([System.IO.Path]::IsPathRooted($configuredBackupRoot)) {
    $backupRoot = [System.IO.Path]::GetFullPath($configuredBackupRoot)
}
else {
    $backupRoot = [System.IO.Path]::GetFullPath(
        (Join-Path (Split-Path -Parent $composeFile) $configuredBackupRoot)
    )
}
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$stamp = [DateTimeOffset]::UtcNow.ToString("yyyyMMddHHmmss")
$suffix = [Guid]::NewGuid().ToString("N").Substring(0, 6)
$backupName = "${SourceDatabase}_${stamp}_${suffix}.dump"
$backupPath = [System.IO.Path]::GetFullPath((Join-Path $backupRoot $backupName))
$restoreDatabase = "${SourceDatabase}_restore_smoke_${suffix}"
$probeDatabase = "${SourceDatabase}_v7_probe_${suffix}"
$apiContainer = "${ProjectName}-restore-api-${suffix}"
$webContainer = "${ProjectName}-restore-web-${suffix}"
if ($restoreDatabase -notmatch '^[a-zA-Z][a-zA-Z0-9_]*_restore_smoke_[a-f0-9]{6}$') {
    throw "Internal safety check rejected restore database name"
}
if ($probeDatabase -notmatch '^[a-zA-Z][a-zA-Z0-9_]*_v7_probe_[a-f0-9]{6}$') {
    throw "Internal safety check rejected V0007 probe database name"
}
if (-not $backupPath.StartsWith($backupRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    throw "Internal safety check rejected backup path"
}

$compose = @(
    "compose", "--project-name", $ProjectName,
    "--profile", "verification",
    "--env-file", $EnvFile, "-f", $composeFile
)
$restoreCreated = $false
$probeCreated = $false
$apiContainerCreated = $false
$webContainerCreated = $false

function Invoke-DockerChecked {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker @compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker command failed (exit=$LASTEXITCODE); arguments suppressed"
    }
}

function Invoke-DockerJson {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    $output = & docker @compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker JSON command failed (exit=$LASTEXITCODE); arguments suppressed"
    }
    $jsonLine = @($output | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })[-1]
    try {
        return $jsonLine | ConvertFrom-Json
    }
    catch {
        throw "docker command did not return a JSON result"
    }
}

function Get-ResolvedService {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][string]$ServiceName
    )
    $property = $Config.services.PSObject.Properties[$ServiceName]
    if ($null -eq $property) {
        throw "Compose preflight is missing service: $ServiceName"
    }
    return $property.Value
}

function Assert-LoopbackPort {
    param(
        [Parameter(Mandatory = $true)]$Service,
        [Parameter(Mandatory = $true)][int]$ContainerPort,
        [Parameter(Mandatory = $true)][int]$ExpectedPort,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $ports = @($Service.ports)
    if ($ports.Count -ne 1) {
        throw "$Label must expose exactly one published port"
    }
    $binding = $ports[0]
    if (
        [int]$binding.target -ne $ContainerPort -or
        [int]$binding.published -ne $ExpectedPort -or
        [string]$binding.host_ip -cne "127.0.0.1" -or
        [string]$binding.protocol -cne "tcp"
    ) {
        throw "$Label port binding does not match the expected loopback endpoint"
    }
}

function Assert-ComposePreflight {
    $configOutput = & docker @compose config --format json 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose config preflight failed: $($configOutput -join [Environment]::NewLine)"
    }
    try {
        $config = ($configOutput -join [Environment]::NewLine) | ConvertFrom-Json
    }
    catch {
        throw "Docker Compose config preflight did not return valid JSON"
    }
    if ([string]$config.name -cne $ProjectName) {
        throw "Resolved Compose project does not match ProjectName"
    }
    foreach ($serviceName in @(
        "api", "importer", "migration", "role-provision", "round-trip-smoke",
        "consistency-smoke", "cache-epoch-smoke", "artifact-lock-smoke",
        "revision-history-smoke", "revision-history-verify"
    )) {
        $service = Get-ResolvedService -Config $config -ServiceName $serviceName
        if ([string]$service.image -cne $ExpectedApiImage) {
            throw "Resolved $serviceName image does not match ExpectedApiImage"
        }
    }
    foreach ($serviceName in @("scheduler", "scheduler-smoke")) {
        $service = Get-ResolvedService -Config $config -ServiceName $serviceName
        if ([string]$service.image -cne $ExpectedSchedulerImage) {
            throw "Resolved $serviceName image does not match ExpectedSchedulerImage"
        }
    }
    $api = Get-ResolvedService -Config $config -ServiceName "api"
    $web = Get-ResolvedService -Config $config -ServiceName "web"
    $scheduler = Get-ResolvedService -Config $config -ServiceName "scheduler"
    $db = Get-ResolvedService -Config $config -ServiceName "db"
    Assert-LoopbackPort -Service $api -ContainerPort 8000 -ExpectedPort $ExpectedApiPort -Label "API"
    Assert-LoopbackPort -Service $web -ContainerPort 3000 -ExpectedPort $ExpectedWebPort -Label "Web"
    Assert-LoopbackPort -Service $scheduler -ContainerPort 8081 -ExpectedPort $ExpectedSchedulerPort -Label "Scheduler"
    if ($null -ne $db.ports -and @($db.ports).Count -ne 0) {
        throw "Database must not expose a published port"
    }
    if (
        [string]$scheduler.environment.SCHEDULER_ENABLED -cne "false" -or
        [string]$scheduler.environment.SHADOW_MODE -cne "true" -or
        [string]$scheduler.environment.AUTO_PUBLISH -cne "false"
    ) {
        throw "Scheduler safety flags do not match disabled Shadow Mode"
    }
    if (-not [bool]$config.networks.backend.internal) {
        throw "Resolved backend network must remain internal"
    }
    Write-Host "A6_COMPOSE_PREFLIGHT_OK project=$ProjectName api_image=$ExpectedApiImage scheduler_image=$ExpectedSchedulerImage api_port=$ExpectedApiPort web_port=$ExpectedWebPort scheduler_port=$ExpectedSchedulerPort"
}

function Assert-RunningDbIdentity {
    $containerId = (& docker @compose ps -q db 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $containerId -notmatch '^[0-9a-f]{12,64}$') {
        throw "Compose preflight could not identify exactly one running database container"
    }
    $inspectOutput = & docker inspect $containerId 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect the resolved database container"
    }
    try {
        $inspection = @(($inspectOutput -join [Environment]::NewLine) | ConvertFrom-Json)[0]
    }
    catch {
        throw "Database container inspection was not valid JSON"
    }
    if ([string]$inspection.Config.Labels.'com.docker.compose.project' -cne $ProjectName) {
        throw "Running database container belongs to a different Compose project"
    }
    $dataMounts = @($inspection.Mounts | Where-Object { $_.Destination -eq "/var/lib/postgresql" })
    if (
        $dataMounts.Count -ne 1 -or
        [string]$dataMounts[0].Type -cne "volume" -or
        [string]$dataMounts[0].Name -cne "${ProjectName}_pg_data"
    ) {
        throw "Running database does not use the expected isolated project volume"
    }
    Write-Host "A6_DB_TARGET_OK project=$ProjectName container=$containerId volume=$($dataMounts[0].Name)"
    return $containerId
}

function Get-PublishedPort {
    param([string]$Container, [string]$ContainerPort)
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $mapping = & docker port $Container $ContainerPort 2>$null
        if ($LASTEXITCODE -eq 0 -and ($mapping | Out-String) -match '127\.0\.0\.1:(\d+)') {
            return [int]$Matches[1]
        }
        Start-Sleep -Seconds 1
    }
    throw "Timed out waiting for loopback port on disposable container $Container"
}

function Wait-JsonEndpoint {
    param([string]$Uri)
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            return Invoke-RestMethod -Uri $Uri -TimeoutSec 2
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    throw "Timed out waiting for restored service endpoint"
}

function Stop-DisposableContainer {
    param([string]$Container)
    $expectedPattern = '^' + [regex]::Escape($ProjectName) + '-restore-(api|web)-[a-f0-9]{6}$'
    if ($Container -notmatch $expectedPattern) {
        throw "Internal safety check rejected disposable container name"
    }
    $running = & docker inspect --format '{{.State.Running}}' $Container 2>$null
    if ($LASTEXITCODE -ne 0) {
        return
    }
    if (($running | Out-String).Trim() -eq "true") {
        & docker stop --time 5 $Container | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Could not stop disposable container $Container"
        }
    }
    & docker rm $Container | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not remove disposable container $Container"
    }
    Write-Host "Removed disposable restore container: $Container"
}

function Get-Scalar {
    param([string]$Database, [string]$Sql)
    $value = & docker @compose exec -T db psql -X -q -v ON_ERROR_STOP=1 `
        --username=$PostgresUser --dbname=$Database --tuples-only --no-align --command=$Sql
    if ($LASTEXITCODE -ne 0) {
        throw "psql scalar query failed for database $Database"
    }
    return ($value | Out-String).Trim()
}

function Assert-CountObject {
    param(
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Expected,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $actualNames = @($Actual.PSObject.Properties.Name)
    if (
        $actualNames.Count -ne $Expected.Count -or
        @($actualNames | Where-Object { -not $Expected.Contains($_) }).Count -ne 0
    ) {
        throw "$Label row-count keys do not match the pinned closure"
    }
    foreach ($name in $Expected.Keys) {
        if ([int]$Actual.$name -ne [int]$Expected[$name]) {
            throw "$Label row-count mismatch for $name"
        }
    }
}

function Assert-A6DatabaseIdentity {
    param(
        [Parameter(Mandatory = $true)][string]$Database,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $alembic = Get-Scalar -Database $Database -Sql "SELECT version_num FROM alembic_version"
    $activeRevision = Get-Scalar -Database $Database -Sql "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $activeRun = Get-Scalar -Database $Database -Sql "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $activeMaterialization = Get-Scalar -Database $Database -Sql "SELECT COALESCE(materialization_sha256, '') FROM materialization_state WHERE id=1"
    $epoch = [long](Get-Scalar -Database $Database -Sql "SELECT epoch FROM materialization_state WHERE id=1")
    if (
        $alembic -ne "v0007_gacha_timeline_slice" -or
        $activeRevision -ne $a6Revision -or
        $activeRun -notmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' -or
        $activeMaterialization -notmatch '^[0-9a-f]{64}$' -or
        $epoch -le 0
    ) {
        throw "$Label active A6 state is invalid"
    }
    $revisionValues = Get-Scalar -Database $Database -Sql "SELECT manifest_sha256 || '|' || raw_tree_sha256 || '|' || semantic_tree_sha256 || '|' || status || '|' || file_count || '|' || csv_file_count || '|' || csv_row_count || '|' || evidence_to_claim_count || '|' || evidence_to_claim_sha256 || '|' || claim_to_evidence_count || '|' || claim_to_evidence_sha256 || '|' || COALESCE(materialization_sha256, '') || '|' || COALESCE(import_run_id::text, '') FROM core_revisions WHERE revision_id='$a6Revision'"
    $expectedRevisionValues = "$a6ManifestSha256|$a6Revision|$a6Semantic|SUCCEEDED|48|13|376|120|$a6EvidenceToClaimSha256|298|$a6ClaimToEvidenceSha256|$activeMaterialization|$activeRun"
    if ($revisionValues -ne $expectedRevisionValues) {
        throw "$Label portable or instance CoreRevision identity drifted"
    }
    $runValues = Get-Scalar -Database $Database -Sql "SELECT status || '|' || fixture_sha256 || '|' || canonical_source || '|' || COALESCE(manifest#>>'{materialization,schema_version}', '') || '|' || COALESCE(manifest#>>'{materialization,sha256}', '') || '|' || (SELECT count(*) FROM jsonb_object_keys(CASE WHEN jsonb_typeof(manifest#>'{materialization,tables}')='object' THEN manifest#>'{materialization,tables}' ELSE '{}'::jsonb END)) FROM import_runs WHERE id='$activeRun'"
    if ($runValues -ne "SUCCEEDED|$a6Revision|research_core_file_ssot|4|$activeMaterialization|23") {
        throw "$Label active ImportRun identity drifted"
    }
    $runCounts = (Get-Scalar -Database $Database -Sql "SELECT row_counts::text FROM import_runs WHERE id='$activeRun'") | ConvertFrom-Json
    $servingCounts = (Get-Scalar -Database $Database -Sql "SELECT serving_counts::text FROM materialization_state WHERE id=1") | ConvertFrom-Json
    Assert-CountObject -Actual $runCounts -Expected $a6RowCounts -Label "$Label ImportRun"
    Assert-CountObject -Actual $servingCounts -Expected $a6ServingCounts -Label "$Label MaterializationState"
    foreach ($table in $a6ServingCounts.Keys) {
        $actual = [int](Get-Scalar -Database $Database -Sql "SELECT COUNT(*) FROM $table")
        if ($actual -ne [int]$a6ServingCounts[$table]) {
            throw "$Label database count mismatch for $table"
        }
    }
    # This diagnostic is intentionally not used as portable revision identity.
    # The exact portable manifest, edge closures, and typed materialization above
    # are the release gates; this hash identifies the full source artifact mirror.
    Write-Host "A6_ARTIFACT_DIAGNOSTIC_PINNED sha256=$a6ArtifactMirrorSha256"
    return [pscustomobject]@{
        Alembic = $alembic
        Revision = $activeRevision
        ImportRun = $activeRun
        Materialization = $activeMaterialization
        Epoch = $epoch
    }
}

function Assert-DbPrivilegeContract {
    param([Parameter(Mandatory = $true)][string]$Database)
    $privilegeOutput = & (Join-Path $repoRoot "scripts\check_db_privileges.ps1") `
        -EnvFile $EnvFile `
        -ProjectName $ProjectName `
        -Database $Database `
        -PostgresUser $PostgresUser *>&1
    $privilegeExit = $LASTEXITCODE
    $privilegeLines = @(
        $privilegeOutput | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ }
    )
    $expectedMarker = "DB_PRIVILEGES_OK matrix_checks=651 actual_denials=23 allowed_smokes=10"
    if ($privilegeExit -ne 0 -or @($privilegeLines | Where-Object { $_ -ceq $expectedMarker }).Count -ne 1) {
        throw "Database privilege verifier did not emit the exact 7-privilege A6 contract"
    }
    $privilegeLines | ForEach-Object { Write-Host $_ }
}

$primaryError = $null
$cleanupErrors = [System.Collections.Generic.List[string]]::new()
$receipt = $null

function Invoke-CleanupStep {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    try {
        & $Action
    }
    catch {
        $script:cleanupErrors.Add("${Name}: $($_.Exception.Message)")
    }
}

try {
    Assert-ComposePreflight
    Invoke-DockerChecked ps --status running db
    $dbContainerId = Assert-RunningDbIdentity
    # CI may explicitly seed a real A -> B -> A importer cycle. It is opt-in so
    # an operator running a restore drill against a durable database never gets
    # synthetic history as an unexpected side effect.
    $sourceImporterUrl = "postgresql+psycopg://pcr_importer:${encodedImporterPassword}@db:5432/${SourceDatabase}"
    $sourceApiUrl = "postgresql+psycopg://pcr_api:${encodedApiPassword}@db:5432/${SourceDatabase}"
    if ($SeedRevisionHistory) {
        Invoke-DockerChecked run --rm --no-deps `
            --env "PCR_DATABASE_URL=$sourceImporterUrl" `
            revision-history-smoke
    }
    $sourceIdentity = Assert-A6DatabaseIdentity -Database $SourceDatabase -Label "Source"
    $sourceRevisionCount = [int](Get-Scalar -Database $SourceDatabase -Sql "SELECT COUNT(*) FROM core_revisions")
    $sourceActivationCount = [int](Get-Scalar -Database $SourceDatabase -Sql "SELECT COUNT(*) FROM revision_activations")
    $verifyRevisionHistory = $sourceRevisionCount -ge 2 -and $sourceActivationCount -ge 3
    if ($SeedRevisionHistory -and -not $verifyRevisionHistory) {
        throw "Revision history smoke did not establish backup coverage"
    }
    if ($verifyRevisionHistory) {
        Write-Host "SOURCE_REVISION_HISTORY_OK revisions=$sourceRevisionCount activations=$sourceActivationCount"
    }
    else {
        Write-Warning "Source has no inactive revision history; current-revision restore remains covered"
    }
    $sourceHistory = Invoke-DockerJson run --rm --no-deps `
        --env "PCR_DATABASE_URL=$sourceApiUrl" `
        revision-history-verify
    if ($sourceHistory.status -ne "REVISION_HISTORY_VERIFIED") {
        throw "Source revision history verifier did not complete"
    }
    if (
        $sourceHistory.active_revision_id -and
        $sourceHistory.active_revision_id -ne $a6Revision
    ) {
        throw "Source history verifier reported a non-A6 active revision"
    }

    Invoke-DockerChecked exec -T db pg_dump `
        --username=$PostgresUser `
        --dbname=$SourceDatabase `
        --format=custom `
        --compress=9 `
        --file="/backups/$backupName"
    $sourceIdentityAfterDump = Assert-A6DatabaseIdentity -Database $SourceDatabase -Label "Source after dump"
    if (
        $sourceIdentityAfterDump.ImportRun -ne $sourceIdentity.ImportRun -or
        $sourceIdentityAfterDump.Materialization -ne $sourceIdentity.Materialization -or
        $sourceIdentityAfterDump.Epoch -ne $sourceIdentity.Epoch
    ) {
        throw "Source materialization identity or epoch changed while the backup was captured"
    }
    # The running DB may have been created with a different BACKUP_DIR than the
    # current process. Ensure the verified local retention path contains the
    # dump without assuming that the bind mount still matches current config.
    if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
        Invoke-DockerChecked cp "${dbContainerId}:/backups/$backupName" $backupPath
    }
    if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
        throw "Database dump was not copied to the verified local backup path"
    }
    $backupSha256 = (Get-FileHash -LiteralPath $backupPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $backupBytes = (Get-Item -LiteralPath $backupPath).Length
    if ($backupBytes -lt 1) {
        throw "Database dump is empty"
    }
    Write-Host "BACKUP_ARTIFACT_VERIFIED sha256=$backupSha256 bytes=$backupBytes path=$backupPath"

    Invoke-DockerChecked exec -T db createdb `
        --username=$PostgresUser `
        --template=template0 `
        --encoding=UTF8 `
        $restoreDatabase
    $restoreCreated = $true

    Invoke-DockerChecked exec -T db pg_restore `
        --username=$PostgresUser `
        --dbname=$restoreDatabase `
        --exit-on-error `
        --no-owner `
        --no-privileges `
        "/backups/$backupName"

    $tableSql = "SELECT quote_ident(tablename) FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    $tables = & docker @compose exec -T db psql `
        --username=$PostgresUser --dbname=$SourceDatabase --tuples-only --no-align --command=$tableSql
    if ($LASTEXITCODE -ne 0) {
        throw "Could not enumerate source tables"
    }
    $tables = @($tables | Where-Object { $_ -and $_.Trim() })
    if ($tables.Count -eq 0) {
        throw "Source database has no public tables; refusing a meaningless restore PASS"
    }
    $restoreTables = & docker @compose exec -T db psql -X -q -v ON_ERROR_STOP=1 `
        --username=$PostgresUser --dbname=$restoreDatabase --tuples-only --no-align --command=$tableSql
    if ($LASTEXITCODE -ne 0) {
        throw "Could not enumerate restored tables"
    }
    $restoreTables = @($restoreTables | Where-Object { $_ -and $_.Trim() })
    if (
        $restoreTables.Count -ne $tables.Count -or
        (Compare-Object -ReferenceObject $tables -DifferenceObject $restoreTables).Count -ne 0
    ) {
        throw "Source and restored public table sets differ"
    }

    foreach ($quotedTable in $tables) {
        $countSql = "SELECT COUNT(*) FROM public.$quotedTable"
        $sourceCount = Get-Scalar -Database $SourceDatabase -Sql $countSql
        $restoreCount = Get-Scalar -Database $restoreDatabase -Sql $countSql
        if ($sourceCount -ne $restoreCount) {
            throw "Row-count mismatch for $quotedTable (source=$sourceCount restore=$restoreCount)"
        }
    }

    $restoredRevisionCount = [int](Get-Scalar -Database $restoreDatabase -Sql "SELECT COUNT(*) FROM core_revisions")
    $restoredInactiveCount = [int](Get-Scalar -Database $restoreDatabase -Sql "SELECT COUNT(*) FROM core_revisions WHERE revision_id<>(SELECT active_revision_id FROM materialization_state WHERE id=1)")
    $restoredActivationCount = [int](Get-Scalar -Database $restoreDatabase -Sql "SELECT COUNT(*) FROM revision_activations")
    $restoredRollbackCount = [int](Get-Scalar -Database $restoreDatabase -Sql "SELECT COUNT(*) FROM revision_activations WHERE kind='ROLLBACK'")
    if ($verifyRevisionHistory -and (
        $restoredRevisionCount -ne $sourceRevisionCount -or
        $restoredActivationCount -ne $sourceActivationCount -or
        $restoredInactiveCount -lt 1 -or
        $restoredRollbackCount -lt 1
    )) {
        throw "Restored immutable revision/audit history coverage failed"
    }
    if ($verifyRevisionHistory) {
        Write-Host "RESTORED_REVISION_HISTORY_OK revisions=$restoredRevisionCount inactive=$restoredInactiveCount activations=$restoredActivationCount rollbacks=$restoredRollbackCount"
    }

    $revisionSql = "SELECT version_num FROM alembic_version"
    $sourceRevision = Get-Scalar -Database $SourceDatabase -Sql $revisionSql
    $restoreRevision = Get-Scalar -Database $restoreDatabase -Sql $revisionSql
    if ($sourceRevision -ne $restoreRevision) {
        throw "Alembic revision mismatch (source=$sourceRevision restore=$restoreRevision)"
    }
    $restoreIdentity = Assert-A6DatabaseIdentity -Database $restoreDatabase -Label "Restored"
    if (
        $restoreIdentity.ImportRun -ne $sourceIdentity.ImportRun -or
        $restoreIdentity.Materialization -ne $sourceIdentity.Materialization -or
        $restoreIdentity.Epoch -ne $sourceIdentity.Epoch
    ) {
        throw "Restored active A6 instance identity differs from source"
    }

    $encodedOwnerPassword = [Uri]::EscapeDataString($ownerPassword)
    $ownerRestoreUrl = "postgresql://${PostgresUser}:${encodedOwnerPassword}@db:5432/${restoreDatabase}"
    $apiRestoreUrl = "postgresql+psycopg://pcr_api:${encodedApiPassword}@db:5432/${restoreDatabase}"

    # pg_restore deliberately omits ACLs. Reapply the idempotent service-role
    # contract to the restored database before testing with the real API role.
    Invoke-DockerChecked run --rm --no-deps `
        --env "PCR_OWNER_DATABASE_URL=$ownerRestoreUrl" `
        --env "PCR_API_DB_PASSWORD=$apiPassword" `
        --env "PCR_IMPORTER_DB_PASSWORD=$importerPassword" `
        --env "PCR_SCHEDULER_DB_PASSWORD=$schedulerPassword" `
        role-provision

    $restoredHistory = Invoke-DockerJson run --rm --no-deps `
        --env "PCR_DATABASE_URL=$apiRestoreUrl" `
        revision-history-verify
    if (
        $restoredHistory.status -ne "REVISION_HISTORY_VERIFIED" -or
        $restoredHistory.history_sha256 -ne $sourceHistory.history_sha256 -or
        [int]$restoredHistory.revision_count -ne [int]$sourceHistory.revision_count -or
        [int]$restoredHistory.import_run_count -ne [int]$sourceHistory.import_run_count -or
        [int]$restoredHistory.activation_count -ne [int]$sourceHistory.activation_count
    ) {
        throw "Restored revision/import/activation content digest differs from source"
    }
    Write-Host "RESTORED_HISTORY_DIGEST_OK sha256=$($restoredHistory.history_sha256) revisions=$($restoredHistory.revision_count) activations=$($restoredHistory.activation_count)"

    # A row-count match alone cannot prove that security triggers, composite
    # foreign keys, and service-role ACLs survived restore. Re-run the same
    # real-statement denial probes against the disposable restored database.
    Assert-DbPrivilegeContract -Database $restoreDatabase
    Write-Host "RESTORED_DB_GUARDS_OK database=$restoreDatabase"

    # Read the restored artifact mirror through the real read-only API role,
    # export it twice, and run the five research-core commands on a disposable copy.
    Invoke-DockerChecked run --rm --no-deps `
        --env "PCR_DATABASE_URL=$apiRestoreUrl" `
        round-trip-smoke
    Write-Host "RESTORED_ROUND_TRIP_OK role=pcr_api files=48 csv=13 rows=376"

    Invoke-DockerChecked run --detach --no-deps `
        --name $apiContainer `
        --publish "127.0.0.1::8000" `
        --env "PCR_DATABASE_URL=$apiRestoreUrl" `
        api
    $apiContainerCreated = $true
    $apiPort = Get-PublishedPort -Container $apiContainer -ContainerPort "8000/tcp"
    $ready = Wait-JsonEndpoint -Uri "http://127.0.0.1:${apiPort}/health/ready"
    if ($ready.status -ne "ok" -or $ready.checks.database -ne "ok" -or $ready.checks.fixture -ne "imported") {
        throw "Restored API readiness contract failed"
    }

    $baseline = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/baseline" -TimeoutSec 5
    if (
        $baseline.meta.source.canonical_source -ne "research_core_file_ssot" -or
        $baseline.meta.source.fixture_sha256 -ne $a6Revision -or
        $baseline.meta.source.import_run_id -ne $sourceIdentity.ImportRun -or
        $baseline.meta.source.revision_id -ne $a6Revision -or
        $baseline.meta.source.raw_tree_sha256 -ne $a6Revision -or
        $baseline.meta.source.semantic_tree_sha256 -ne $a6Semantic -or
        $baseline.meta.source.materialization_sha256 -ne $sourceIdentity.Materialization
    ) {
        throw "Restored API revision metadata contract failed"
    }
    Assert-CountObject -Actual $baseline.data.counts -Expected $a6RowCounts -Label "Restored API"
    if ($baseline.data.application_version -ne "3.0.0-a6") {
        throw "Restored API application version mismatch"
    }
    $stage = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/stages/TW_DEEP_FIRE_08_10_20260802" -TimeoutSec 5
    $timeline = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/teams/TM-F810-02/timelines" -TimeoutSec 5
    $unknownTeam = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/teams/TM-F810-04" -TimeoutSec 5
    $sourceTextTimeline = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/teams/TM-F810-05/timelines" -TimeoutSec 5
    $evidence = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/evidence/ev052" -TimeoutSec 5
    $waterStage = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/stages/TW_DEEP_WATER_08_10_20260808" -TimeoutSec 5
    $waterTimeline = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/teams/TM-W810-01/timelines" -TimeoutSec 5
    $waterAutoTeam = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/teams/TM-W810-05" -TimeoutSec 5
    $waterEvidence = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/evidence/ev084" -TimeoutSec 5
    $arena = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/pvp/counters" -TimeoutSec 5
    $gacha = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/gacha/timeline" -TimeoutSec 5
    $gachaCommunity = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/gacha/community-sources" -TimeoutSec 5
    $sourceTextSteps = @($sourceTextTimeline.data.sources[0].steps)
    $arenaRows = @($arena.data)
    $arenaWarnings = @($arena.meta.warnings)
    $arenaMembers = @(
        $arenaRows | ForEach-Object {
            $_.defense_members
            $_.counter_members
        }
    )
    $gachaRows = @($gacha.data)
    $gachaCommunityRows = @($gachaCommunity.data)
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
    $gachaSourceIds = @($gachaCommunityRows | ForEach-Object { $_.source_id })
    $expectedGachaSourceIds = @(
        "GACHA-COMM-001", "GACHA-COMM-002", "GACHA-COMM-003", "GACHA-COMM-004"
    )
    if (
        $stage.data.status -ne "VERIFIED" -or
        [int]$stage.data.team_count -ne 5 -or
        $stage.data.reproducibility -ne "CONFIRMED" -or
        [int]$stage.data.coverage.verified_distinct_teams -ne 5 -or
        [int]$stage.data.coverage.remaining -ne 0 -or
        -not [bool]$stage.data.coverage.is_mature -or
        $timeline.data.status -ne "PARTIAL" -or
        [int]$timeline.data.structured_sources -ne 1 -or
        [int]$timeline.data.registered_sources -ne 4 -or
        $timeline.data.steps.Count -ne 0 -or
        $timeline.data.sources[-1].reproducibility -ne "UNVERIFIED_ON_TW" -or
        $timeline.data.sources[-1].battle_duration_ms -ne $null -or
        $timeline.data.sources[-1].steps.Count -ne 14 -or
        $unknownTeam.data.operation_mode -ne "UNKNOWN" -or
        $unknownTeam.data.timeline.status -ne "SOURCE_GAP" -or
        [int]$unknownTeam.data.timeline.structured_sources -ne 0 -or
        [int]$unknownTeam.data.timeline.registered_sources -ne 1 -or
        $unknownTeam.data.timeline.sources[0].operation_mode -ne "UNKNOWN" -or
        $unknownTeam.data.timeline.sources[0].steps.Count -ne 0 -or
        $sourceTextTimeline.data.status -ne "STRUCTURED" -or
        [int]$sourceTextTimeline.data.structured_sources -ne 1 -or
        [int]$sourceTextTimeline.data.registered_sources -ne 1 -or
        $sourceTextSteps.Count -ne 5 -or
        @($sourceTextSteps | Where-Object { $_.trigger_type -ne "SOURCE_TEXT_ONLY" }).Count -ne 0 -or
        @($sourceTextSteps | Where-Object { $_.action_type -ne "NO_ACTION" }).Count -ne 0 -or
        $evidence.data.evidence_id -ne "ev052" -or
        $waterStage.data.status -ne "VERIFIED" -or
        [int]$waterStage.data.team_count -ne 5 -or
        [int]$waterStage.data.coverage.verified_distinct_teams -ne 5 -or
        -not [bool]$waterStage.data.coverage.is_mature -or
        $waterTimeline.data.status -ne "STRUCTURED" -or
        [int]$waterTimeline.data.structured_sources -ne 1 -or
        [int]$waterTimeline.data.registered_sources -ne 1 -or
        $waterTimeline.data.sources[0].reproducibility -ne "TW_REPRODUCED" -or
        $waterTimeline.data.sources[0].steps.Count -ne 9 -or
        $waterAutoTeam.data.operation_mode -ne "AUTO" -or
        $waterAutoTeam.data.timeline.sources[0].steps.Count -ne 1 -or
        $waterEvidence.data.evidence_id -ne "ev084" -or
        $arenaRows.Count -ne 2 -or
        @($arenaRows | Where-Object { $_.status -ne "SINGLE_REPORT" }).Count -ne 0 -or
        @($arenaRows | Where-Object { $_.tw_availability_check -ne "PASS" }).Count -ne 0 -or
        @($arenaRows | Where-Object { $_.defense_members.Count -ne 5 -or $_.counter_members.Count -ne 5 }).Count -ne 0 -or
        @($arenaMembers | Where-Object { $_.display_name_source -ne "TW_OFFICIAL" }).Count -ne 0 -or
        $arenaWarnings -notcontains "NO_VERIFIED_COUNTER" -or
        $arenaWarnings -notcontains "SINGLE_REPORT_REFERENCE_ONLY" -or
        ($gachaEventIds -join "|") -ne ($expectedGachaEventIds -join "|") -or
        ($gachaLimitedStatuses -join "|") -ne ($expectedGachaLimitedStatuses -join "|") -or
        ($gachaLimitedClaimIds -join "|") -ne ($expectedGachaLimitedClaimIds -join "|") -or
        @($gachaRows | Where-Object { $_.source_server -ne "JP" -or $_.target_server -ne "TW" -or $null -ne $_.tw_name }).Count -ne 0 -or
        @($gachaRows | Where-Object { $_.maturity -eq "MATURE" }).Count -ne 2 -or
        @($gachaRows | Where-Object { $_.maturity -eq "RESEARCH" }).Count -ne 3 -or
        @($gachaRows | Where-Object {
            $_.maturity -eq "RESEARCH" -and (
                $_.arena_value -ne "NOT_EVALUATED" -or
                $_.p_arena_value -ne "NOT_EVALUATED" -or
                $_.pve_value -ne "NOT_EVALUATED" -or
                $_.clan_value -ne "NOT_EVALUATED" -or
                $_.relative_priority -ne "NOT_EVALUATED"
            )
        }).Count -ne 0 -or
        @($gachaRows | Where-Object { $_.event_id -in @("JP_20260815_vampy_summer", "JP_20260823_tia") -and $_.limited_status -ne "UNKNOWN" }).Count -ne 0 -or
        $gacha.meta.server -ne "MIXED" -or
        $null -ne $gacha.meta.verified_at -or
        $gacha.meta.stale_status -ne "UNKNOWN" -or
        $gacha.meta.confidence -ne "UNKNOWN" -or
        ($gachaSourceIds -join "|") -ne ($expectedGachaSourceIds -join "|") -or
        @($gachaCommunityRows | Where-Object { $_.confidence_cap -ne "D" }).Count -ne 0 -or
        @($gachaCommunityRows | Where-Object { $_.update_status -eq "CHECKED" }).Count -ne 2 -or
        @($gachaCommunityRows | Where-Object { $_.update_status -eq "STALE" }).Count -ne 2
    ) {
        throw "Restored API critical read path failed"
    }
    Write-Host "RESTORED_API_READINESS_OK role=pcr_api stages=3 teams=10 timelines=15 steps=37 arena_defenses=1 arena_counters=2 gacha_events=5 gacha_sources=4 fire=VERIFIED water=VERIFIED arena=SINGLE_REPORT"

    Invoke-DockerChecked run --detach --no-deps `
        --name $webContainer `
        --publish "127.0.0.1::3000" `
        --env "API_BASE_URL=http://${apiContainer}:8000" `
        web
    $webContainerCreated = $true
    $webPort = Get-PublishedPort -Container $webContainer -ContainerPort "3000/tcp"
    $webHealth = Wait-JsonEndpoint -Uri "http://127.0.0.1:${webPort}/api/health"
    $proxyEvidence = Invoke-RestMethod -Uri "http://127.0.0.1:${webPort}/api/v1/evidence/ev052" -TimeoutSec 5
    $homeResponse = Invoke-WebRequest -Uri "http://127.0.0.1:${webPort}/" -TimeoutSec 5
    $gachaResponse = Invoke-WebRequest -Uri "http://127.0.0.1:${webPort}/gacha" -TimeoutSec 5
    if ($webHealth.status -ne "ok") {
        throw "Restored Web health failed"
    }
    if ($proxyEvidence.data.evidence_id -ne "ev052") {
        throw "Restored Web Evidence proxy failed"
    }
    if (
        $homeResponse.StatusCode -ne 200 -or
        $homeResponse.Content -notmatch "已驗證通關" -or
        $homeResponse.Content -notmatch "research_core_file_ssot"
    ) {
        throw "Restored Web SSR content failed"
    }
    if (
        $gachaResponse.StatusCode -ne 200 -or
        $gachaResponse.Content -notmatch "抽卡未來視" -or
        $gachaResponse.Content -notmatch "ヴァンピィ（サマー）" -or
        $gachaResponse.Content -notmatch "限定身分 UNKNOWN"
    ) {
        throw "Restored Web Gacha SSR content failed"
    }
    Write-Host "RESTORED_WEB_EVIDENCE_OK stage=VERIFIED evidence=ev052 gacha_events=5 gacha_ssr=ok"

    # A second restored database isolates the destructive negative probe from
    # both the source and the fully verified restore. V0007 must reject an
    # active v4 owner even after all Gacha rows were manually removed.
    Invoke-DockerChecked exec -T db createdb `
        --username=$PostgresUser `
        --template=template0 `
        --encoding=UTF8 `
        $probeDatabase
    $probeCreated = $true
    Invoke-DockerChecked exec -T db pg_restore `
        --username=$PostgresUser `
        --dbname=$probeDatabase `
        --exit-on-error `
        --no-owner `
        --no-privileges `
        "/backups/$backupName"
    $probeIdentity = Assert-A6DatabaseIdentity -Database $probeDatabase -Label "V0007 probe"
    Get-Scalar -Database $probeDatabase -Sql "TRUNCATE TABLE gacha_timeline_community_sources, gacha_timeline_claims, gacha_timeline_evidence, gacha_community_sources, gacha_timeline_events"
    $probeGachaRows = [int](Get-Scalar -Database $probeDatabase -Sql "SELECT (SELECT COUNT(*) FROM gacha_timeline_events) + (SELECT COUNT(*) FROM gacha_timeline_evidence) + (SELECT COUNT(*) FROM gacha_timeline_claims) + (SELECT COUNT(*) FROM gacha_community_sources) + (SELECT COUNT(*) FROM gacha_timeline_community_sources)")
    $probeNonGachaRows = [int](Get-Scalar -Database $probeDatabase -Sql "SELECT (SELECT COUNT(*) FROM stages) + (SELECT COUNT(*) FROM teams) + (SELECT COUNT(*) FROM team_members) + (SELECT COUNT(*) FROM characters) + (SELECT COUNT(*) FROM evidence) + (SELECT COUNT(*) FROM claims) + (SELECT COUNT(*) FROM stage_evidence) + (SELECT COUNT(*) FROM stage_claims) + (SELECT COUNT(*) FROM team_evidence) + (SELECT COUNT(*) FROM claim_evidence) + (SELECT COUNT(*) FROM operation_timelines) + (SELECT COUNT(*) FROM timeline_steps) + (SELECT COUNT(*) FROM arena_defenses) + (SELECT COUNT(*) FROM arena_defense_members) + (SELECT COUNT(*) FROM arena_counters) + (SELECT COUNT(*) FROM arena_counter_members) + (SELECT COUNT(*) FROM arena_counter_evidence) + (SELECT COUNT(*) FROM arena_counter_claims)")
    if ($probeGachaRows -ne 0) {
        throw "V0007 negative probe did not establish an empty Gacha closure"
    }
    $encodedOwnerPassword = [Uri]::EscapeDataString($ownerPassword)
    $ownerProbeMigrationUrl = "postgresql+psycopg://${PostgresUser}:${encodedOwnerPassword}@db:5432/${probeDatabase}"
    $downgradeOutput = & docker @compose run --rm --no-deps `
        --env "PCR_DATABASE_URL=$ownerProbeMigrationUrl" `
        migration `
        alembic -c database/alembic.ini downgrade v0006_arena_counter_slice 2>&1
    $downgradeExit = $LASTEXITCODE
    $postDowngradeRevision = Get-Scalar -Database $probeDatabase -Sql "SELECT version_num FROM alembic_version"
    $postDowngradeActiveRevision = Get-Scalar -Database $probeDatabase -Sql "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $postDowngradeActiveRun = Get-Scalar -Database $probeDatabase -Sql "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $postDowngradeMaterialization = Get-Scalar -Database $probeDatabase -Sql "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    $postDowngradeEpoch = [long](Get-Scalar -Database $probeDatabase -Sql "SELECT epoch FROM materialization_state WHERE id=1")
    $postDowngradeGachaTables = [int](Get-Scalar -Database $probeDatabase -Sql "SELECT COUNT(*) FROM (VALUES ('gacha_timeline_events'), ('gacha_timeline_evidence'), ('gacha_timeline_claims'), ('gacha_community_sources'), ('gacha_timeline_community_sources')) AS gacha_table(name) WHERE to_regclass('public.' || name) IS NOT NULL")
    $postDowngradeNonGachaRows = [int](Get-Scalar -Database $probeDatabase -Sql "SELECT (SELECT COUNT(*) FROM stages) + (SELECT COUNT(*) FROM teams) + (SELECT COUNT(*) FROM team_members) + (SELECT COUNT(*) FROM characters) + (SELECT COUNT(*) FROM evidence) + (SELECT COUNT(*) FROM claims) + (SELECT COUNT(*) FROM stage_evidence) + (SELECT COUNT(*) FROM stage_claims) + (SELECT COUNT(*) FROM team_evidence) + (SELECT COUNT(*) FROM claim_evidence) + (SELECT COUNT(*) FROM operation_timelines) + (SELECT COUNT(*) FROM timeline_steps) + (SELECT COUNT(*) FROM arena_defenses) + (SELECT COUNT(*) FROM arena_defense_members) + (SELECT COUNT(*) FROM arena_counters) + (SELECT COUNT(*) FROM arena_counter_members) + (SELECT COUNT(*) FROM arena_counter_evidence) + (SELECT COUNT(*) FROM arena_counter_claims)")
    if (
        $downgradeExit -eq 0 -or
        ($downgradeOutput -join [Environment]::NewLine) -notmatch "verified Arena v3 materialization owns the mirror" -or
        $postDowngradeRevision -ne "v0007_gacha_timeline_slice" -or
        $postDowngradeActiveRevision -ne $probeIdentity.Revision -or
        $postDowngradeActiveRun -ne $probeIdentity.ImportRun -or
        $postDowngradeMaterialization -ne $probeIdentity.Materialization -or
        $postDowngradeEpoch -ne $probeIdentity.Epoch -or
        $postDowngradeGachaTables -ne 5 -or
        $postDowngradeNonGachaRows -ne $probeNonGachaRows
    ) {
        throw "V0007 active-v4 empty-Gacha downgrade was not rejected transactionally"
    }
    Write-Host "GACHA_DOWNGRADE_BLOCKED_OK alembic=$postDowngradeRevision gacha_rows=0 gacha_tables=$postDowngradeGachaTables active_revision=$postDowngradeActiveRevision"

    $finalSourceIdentity = Assert-A6DatabaseIdentity -Database $SourceDatabase -Label "Source after restore drill"
    if (
        $finalSourceIdentity.ImportRun -ne $sourceIdentity.ImportRun -or
        $finalSourceIdentity.Materialization -ne $sourceIdentity.Materialization -or
        $finalSourceIdentity.Epoch -ne $sourceIdentity.Epoch
    ) {
        throw "Source materialization changed during the restore drill"
    }
    $receipt = [ordered]@{
        status = "BACKUP_RESTORE_VERIFIED"
        project = $ProjectName
        source_database = $SourceDatabase
        path = $backupPath
        sha256 = $backupSha256
        bytes = $backupBytes
        alembic_revision = $sourceIdentity.Alembic
        revision_id = $sourceIdentity.Revision
        import_run_id = $sourceIdentity.ImportRun
        materialization_sha256 = $sourceIdentity.Materialization
        artifact_mirror_diagnostic_sha256 = $a6ArtifactMirrorSha256
        source_epoch = $sourceIdentity.Epoch
        backup_retained = [bool]$KeepBackup
        restore_database_retained = [bool]$KeepRestoredDatabase
    }
}
catch {
    $primaryError = $_
}
finally {
    if ($webContainerCreated) {
        Invoke-CleanupStep -Name "web container" -Action {
            Stop-DisposableContainer -Container $webContainer
        }
    }
    if ($apiContainerCreated) {
        Invoke-CleanupStep -Name "API container" -Action {
            Stop-DisposableContainer -Container $apiContainer
        }
    }
    if ($probeCreated) {
        Invoke-CleanupStep -Name "V0007 probe database" -Action {
            Invoke-DockerChecked exec -T db dropdb `
                --username=$PostgresUser `
                --if-exists `
                $probeDatabase
            Write-Host "Removed disposable V0007 probe database: $probeDatabase"
        }
    }
    if ($restoreCreated -and -not $KeepRestoredDatabase) {
        Invoke-CleanupStep -Name "restore database" -Action {
            Invoke-DockerChecked exec -T db dropdb `
                --username=$PostgresUser `
                --if-exists `
                $restoreDatabase
            Write-Host "Removed disposable restore database: $restoreDatabase"
        }
    }
    if (-not $KeepBackup) {
        # The dump is created by the postgres user inside the bind mount. On a
        # Linux GitHub runner that UID-owned file cannot necessarily be removed
        # by host PowerShell. Always delete the exact container basename first;
        # if docker cp created a separate local copy, delete only that validated
        # path afterwards.
        Invoke-CleanupStep -Name "backup files" -Action {
            Invoke-DockerChecked exec -T db rm -f -- "/backups/$backupName"
            if (Test-Path -LiteralPath $backupPath -PathType Leaf) {
                Remove-Item -LiteralPath $backupPath -Force
            }
            if (Test-Path -LiteralPath $backupPath -PathType Leaf) {
                throw "Disposable smoke backup cleanup failed"
            }
            Write-Host "Removed disposable smoke backup: $backupPath"
        }
    }
}

if ($primaryError) {
    if ($cleanupErrors.Count -gt 0) {
        Write-Warning "Cleanup also reported: $($cleanupErrors -join '; ')"
    }
    throw $primaryError
}
if ($cleanupErrors.Count -gt 0) {
    throw "Backup/restore succeeded but cleanup failed: $($cleanupErrors -join '; ')"
}
if ($null -eq $receipt) {
    throw "Backup/restore completed without a verification receipt"
}
Write-Host "BACKUP_RESTORE_OK source=$SourceDatabase restore=$restoreDatabase tables=$($tables.Count) source_alembic=$sourceRevision restored_alembic=$restoreRevision"
Write-Output ($receipt | ConvertTo-Json -Compress)
if ($KeepBackup) {
    Write-Host "Retained verified backup: $backupPath"
}
