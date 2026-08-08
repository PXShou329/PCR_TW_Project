[CmdletBinding()]
param(
    [string]$EnvFile,
    [string]$ProjectName,
    [string]$PostgresUser,
    [string]$SourceDatabase = "pcr_tw",
    [switch]$KeepBackup,
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

$backupRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot ".runtime\backups"))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$stamp = [DateTimeOffset]::UtcNow.ToString("yyyyMMddHHmmss")
$suffix = [Guid]::NewGuid().ToString("N").Substring(0, 6)
$backupName = "${SourceDatabase}_${stamp}_${suffix}.dump"
$backupPath = [System.IO.Path]::GetFullPath((Join-Path $backupRoot $backupName))
$restoreDatabase = "${SourceDatabase}_restore_smoke_${suffix}"
$apiContainer = "pcr-tw-b0-restore-api-${suffix}"
$webContainer = "pcr-tw-b0-restore-web-${suffix}"
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
$previousBackupDirectory = $env:BACKUP_DIR
$env:BACKUP_DIR = $backupRoot
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
    if ($Container -notmatch '^pcr-tw-b0-restore-(api|web)-[a-f0-9]{6}$') {
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

try {
    Invoke-DockerChecked ps --status running db
    Invoke-DockerChecked exec -T db pg_dump `
        --username=$PostgresUser `
        --dbname=$SourceDatabase `
        --format=custom `
        --compress=9 `
        --file="/backups/$backupName"

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

    $revisionSql = "SELECT version_num FROM alembic_version"
    $sourceRevision = Get-Scalar -Database $SourceDatabase -Sql $revisionSql
    $restoreRevision = Get-Scalar -Database $restoreDatabase -Sql $revisionSql
    if ($sourceRevision -ne $restoreRevision) {
        throw "Alembic revision mismatch (source=$sourceRevision restore=$restoreRevision)"
    }

    $encodedOwnerPassword = [Uri]::EscapeDataString($ownerPassword)
    $encodedApiPassword = [Uri]::EscapeDataString($apiPassword)
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
    $expectedCounts = @{
        stages = 1; teams = 3; team_members = 15; characters = 8; evidence = 18; claims = 13;
        operation_timelines = 8; timeline_steps = 14
    }
    foreach ($name in $expectedCounts.Keys) {
        if ([int]$baseline.data.counts.$name -ne $expectedCounts[$name]) {
            throw "Restored API count mismatch for $name"
        }
    }
    $stage = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/stages/TW_DEEP_FIRE_08_10_20260802" -TimeoutSec 5
    $timeline = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/teams/TM-F810-02/timelines" -TimeoutSec 5
    $evidence = Invoke-RestMethod -Uri "http://127.0.0.1:${apiPort}/api/v1/evidence/ev052" -TimeoutSec 5
    if (
        $stage.data.status -ne "PROVISIONAL" -or
        [int]$stage.data.team_count -ne 3 -or
        $timeline.data.status -ne "PARTIAL" -or
        [int]$timeline.data.structured_sources -ne 1 -or
        [int]$timeline.data.registered_sources -ne 4 -or
        $timeline.data.steps.Count -ne 0 -or
        $timeline.data.sources[-1].reproducibility -ne "UNVERIFIED_ON_TW" -or
        $timeline.data.sources[-1].battle_duration_ms -ne $null -or
        $timeline.data.sources[-1].steps.Count -ne 14 -or
        $evidence.data.evidence_id -ne "ev052"
    ) {
        throw "Restored API critical read path failed"
    }
    Write-Host "RESTORED_API_READINESS_OK role=pcr_api stage=PROVISIONAL teams=3 timelines=8 steps=14 evidence=ev052"

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
        $homeResponse.Content -notmatch "暫定攻略" -or
        $homeResponse.Content -notmatch "research_core_file_ssot"
    ) {
        throw "Restored Web SSR content failed"
    }
    Write-Host "RESTORED_WEB_EVIDENCE_OK stage=PROVISIONAL evidence=ev052"

    Write-Host "BACKUP_RESTORE_OK source=$SourceDatabase restore=$restoreDatabase tables=$($tables.Count) alembic=$sourceRevision"
    Write-Host "Backup: $backupPath"
}
finally {
    if ($webContainerCreated) {
        Stop-DisposableContainer -Container $webContainer
    }
    if ($apiContainerCreated) {
        Stop-DisposableContainer -Container $apiContainer
    }
    if ($restoreCreated -and -not $KeepRestoredDatabase) {
        Invoke-DockerChecked exec -T db dropdb `
            --username=$PostgresUser `
            --if-exists `
            $restoreDatabase
        Write-Host "Removed disposable restore database: $restoreDatabase"
    }
    if ((Test-Path -LiteralPath $backupPath -PathType Leaf) -and -not $KeepBackup) {
        # The dump is created by the postgres user inside the bind mount. On a
        # Linux GitHub runner that UID-owned file cannot be removed by host
        # PowerShell, even though the complete restore drill has passed. Delete
        # the exact validated basename through the same database container,
        # then confirm the bind-mounted host path is gone.
        Invoke-DockerChecked exec -T db rm -f -- "/backups/$backupName"
        if (Test-Path -LiteralPath $backupPath -PathType Leaf) {
            throw "Database container did not remove the disposable smoke backup"
        }
        Write-Host "Removed disposable smoke backup: $backupPath"
    }
    if ($null -eq $previousBackupDirectory) {
        Remove-Item Env:BACKUP_DIR -ErrorAction SilentlyContinue
    }
    else {
        $env:BACKUP_DIR = $previousBackupDirectory
    }
}
