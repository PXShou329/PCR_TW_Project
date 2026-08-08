[CmdletBinding()]
param(
    [string]$EnvFile,
    [string]$ProjectName,
    [string]$PostgresUser,
    [string]$SourceDatabase = "pcr_tw",
    [switch]$SeedRevisionHistory,
    [switch]$KeepBackup,
    [Parameter(HelpMessage = "Keep the restored database at V0005 after the intentionally rejected borrowed-state downgrade probe.")]
    [switch]$KeepRestoredDatabase
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$composeFile = Join-Path $repoRoot "infra\compose.yml"
if (-not $EnvFile) {
    $EnvFile = Join-Path $repoRoot ".env"
}
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

if (-not $PostgresUser) {
    $PostgresUser = Get-Setting -Name "POSTGRES_USER" -Default "pcr_owner"
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
$apiContainer = "pcr-tw-b1-restore-api-${suffix}"
$webContainer = "pcr-tw-b1-restore-web-${suffix}"
if ($restoreDatabase -notmatch '^[a-zA-Z][a-zA-Z0-9_]*_restore_smoke_[a-f0-9]{6}$') {
    throw "Internal safety check rejected restore database name"
}
if (-not $backupPath.StartsWith($backupRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    throw "Internal safety check rejected backup path"
}

$compose = @("compose")
if ($ProjectName) {
    if ($ProjectName -notmatch '^[a-z0-9][a-z0-9_-]{0,62}$') {
        throw "ProjectName contains unsupported characters"
    }
    $compose += @("--project-name", $ProjectName)
}
$compose += @("--env-file", $EnvFile, "-f", $composeFile)
$restoreCreated = $false
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
    if ($Container -notmatch '^pcr-tw-b1-restore-(api|web)-[a-f0-9]{6}$') {
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
    $value = & docker @compose exec -T db psql `
        --username=$PostgresUser --dbname=$Database --tuples-only --no-align --command=$Sql
    if ($LASTEXITCODE -ne 0) {
        throw "psql scalar query failed for database $Database"
    }
    return ($value | Out-String).Trim()
}

$primaryError = $null
$cleanupErrors = [System.Collections.Generic.List[string]]::new()

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
    Invoke-DockerChecked ps --status running db
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

    Invoke-DockerChecked exec -T db pg_dump `
        --username=$PostgresUser `
        --dbname=$SourceDatabase `
        --format=custom `
        --compress=9 `
        --file="/backups/$backupName"
    # The running DB may have been created with a different BACKUP_DIR than the
    # current process. Ensure the verified local retention path contains the
    # dump without assuming that the bind mount still matches current config.
    if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
        Invoke-DockerChecked cp "db:/backups/$backupName" $backupPath
    }
    if (-not (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
        throw "Database dump was not copied to the verified local backup path"
    }

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

    $encodedOwnerPassword = [Uri]::EscapeDataString($ownerPassword)
    $ownerRestoreUrl = "postgresql://${PostgresUser}:${encodedOwnerPassword}@db:5432/${restoreDatabase}"
    $ownerRestoreMigrationUrl = "postgresql+psycopg://${PostgresUser}:${encodedOwnerPassword}@db:5432/${restoreDatabase}"
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
    $privilegeArgs = @{
        EnvFile = $EnvFile
        Database = $restoreDatabase
        PostgresUser = $PostgresUser
    }
    if ($ProjectName) {
        $privilegeArgs.ProjectName = $ProjectName
    }
    & (Join-Path $repoRoot "scripts\check_db_privileges.ps1") @privilegeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Restored database privilege/immutability probes failed"
    }
    Write-Host "RESTORED_DB_GUARDS_OK database=$restoreDatabase"

    # Read the restored artifact mirror through the real read-only API role,
    # export it twice, and run the five research-core commands on a disposable copy.
    Invoke-DockerChecked run --rm --no-deps `
        --env "PCR_DATABASE_URL=$apiRestoreUrl" `
        round-trip-smoke
    Write-Host "RESTORED_ROUND_TRIP_OK role=pcr_api files=48 csv=13 rows=325"

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
        $baseline.meta.source.revision_id.Length -ne 64 -or
        $baseline.meta.source.raw_tree_sha256.Length -ne 64 -or
        $baseline.meta.source.semantic_tree_sha256.Length -ne 64 -or
        $baseline.meta.source.materialization_sha256.Length -ne 64
    ) {
        throw "Restored API revision metadata contract failed"
    }
    $expectedCounts = @{
        stages = 3; teams = 10; team_members = 50; characters = 25; evidence = 55; claims = 53;
        operation_timelines = 15; timeline_steps = 37
    }
    foreach ($name in $expectedCounts.Keys) {
        if ([int]$baseline.data.counts.$name -ne $expectedCounts[$name]) {
            throw "Restored API count mismatch for $name"
        }
    }
    if ($baseline.data.application_version -ne "3.0.0-a4") {
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
    $sourceTextSteps = @($sourceTextTimeline.data.sources[0].steps)
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
        $waterEvidence.data.evidence_id -ne "ev084"
    ) {
        throw "Restored API critical read path failed"
    }
    Write-Host "RESTORED_API_READINESS_OK role=pcr_api stages=3 teams=10 timelines=15 steps=37 fire=VERIFIED water=VERIFIED evidence=ev052,ev084"

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
    Write-Host "RESTORED_WEB_EVIDENCE_OK stage=VERIFIED evidence=ev052"

    # NULL is canonical source truth when the evidence does not establish which
    # member was borrowed.  V0005 -> V0004 must therefore fail transactionally
    # instead of coercing NULL to false.  UNKNOWN operation modes are checked as
    # an additional invariant; their V0004 -> V0003 boundary is covered by the
    # offline migration regression suite.
    $borrowedNullBefore = [int](Get-Scalar -Database $restoreDatabase -Sql "SELECT COUNT(*) FROM team_members WHERE is_borrowed IS NULL")
    if ($borrowedNullBefore -lt 1) {
        throw "Restored database has no canonical unknown borrowed-state rows"
    }
    Stop-DisposableContainer -Container $webContainer
    $webContainerCreated = $false
    Stop-DisposableContainer -Container $apiContainer
    $apiContainerCreated = $false
    $downgradeOutput = & docker @compose run --rm --no-deps `
        --env "PCR_DATABASE_URL=$ownerRestoreMigrationUrl" `
        migration `
        alembic -c database/alembic.ini downgrade v0004_unknown_operation_mode 2>&1
    $downgradeExit = $LASTEXITCODE
    $postDowngradeRevision = Get-Scalar -Database $restoreDatabase -Sql "SELECT version_num FROM alembic_version"
    $borrowedNullAfter = [int](Get-Scalar -Database $restoreDatabase -Sql "SELECT COUNT(*) FROM team_members WHERE is_borrowed IS NULL")
    $unknownTimelineCount = [int](Get-Scalar -Database $restoreDatabase -Sql "SELECT COUNT(*) FROM operation_timelines WHERE operation_mode='UNKNOWN'")
    if (
        $downgradeExit -eq 0 -or
        $postDowngradeRevision -ne "v0005_borrowed_tristate" -or
        $borrowedNullAfter -ne $borrowedNullBefore -or
        $unknownTimelineCount -lt 1
    ) {
        throw "Lossy borrowed-state downgrade was not rejected transactionally"
    }
    Write-Host "BORROWED_TRISTATE_DOWNGRADE_BLOCKED_OK alembic=$postDowngradeRevision borrowed_nulls=$borrowedNullAfter unknown_timelines=$unknownTimelineCount"

    Write-Host "BACKUP_RESTORE_OK source=$SourceDatabase restore=$restoreDatabase tables=$($tables.Count) source_alembic=$sourceRevision restored_alembic=$postDowngradeRevision"
    Write-Host "Backup: $backupPath"
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
