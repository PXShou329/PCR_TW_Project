[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$EnvFile,
    [Parameter(Mandatory = $true)]
    [string]$CheckpointRoot,
    [Parameter(HelpMessage = "After exact A3 verification and V0005 to V0004 downgrade, keep services quiesced for an intentional A3 deployment instead of restoring A4.")]
    [switch]$LeaveAtA3
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$composeFile = Join-Path $repoRoot "infra\compose.yml"
$EnvFile = [System.IO.Path]::GetFullPath($EnvFile)
$CheckpointRoot = [System.IO.Path]::GetFullPath($CheckpointRoot)
$checkpointCore = Join-Path $CheckpointRoot "research_core\pcr_tw_project"
$a3Manifest = Join-Path $repoRoot "scripts\research_core_rp_a3_manifest.sha256"
$a3ManifestSha256 = "ab62e07483dfea07c992b950b9c05c74fa0e3767fa0b3bce64b20193a1860333"
$a3Revision = "46d4fea8c1c5cd92e2fd5cb71a7a3ca232d872b1c6d56ce6cd100971250bde45"
$a3Materialization = "67e8f2c5435ab70af951e94daab814cf524cb09853b2ab0008d9f32499bfa2b1"
$a4Revision = "c5a5f13e0efaf96c1a266c1016d3a1a54740859952ce21f9db3cf89d779d57b9"

foreach ($requiredFile in @($EnvFile, $a3Manifest)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Missing rollback drill input: $requiredFile"
    }
}
if (-not (Test-Path -LiteralPath $checkpointCore -PathType Container)) {
    throw "Missing RP-A3 research core: $checkpointCore"
}

function Get-Setting {
    param([string]$Name, [string]$Default = "")
    $processValue = [Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($processValue)) {
        return $processValue.Trim()
    }
    foreach ($line in Get-Content -LiteralPath $EnvFile) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }
        $prefix = "$Name="
        if ($trimmed.StartsWith($prefix, [StringComparison]::Ordinal)) {
            return $trimmed.Substring($prefix.Length).Trim().Trim('"').Trim("'")
        }
    }
    return $Default
}

$postgresUser = Get-Setting -Name "POSTGRES_USER" -Default "pcr_owner"
$postgresDatabase = Get-Setting -Name "POSTGRES_DB" -Default "pcr_tw"
$apiPortText = Get-Setting -Name "API_PORT" -Default "8000"
if ($apiPortText -notmatch '^\d{1,5}$') {
    throw "API_PORT must be a decimal TCP port"
}
$apiPort = [int]$apiPortText
if ($apiPort -lt 1 -or $apiPort -gt 65535) {
    throw "API_PORT is outside the TCP port range"
}
$schedulerEnabled = (Get-Setting -Name "SCHEDULER_ENABLED" -Default "false").ToLowerInvariant()
$shadowMode = (Get-Setting -Name "SHADOW_MODE" -Default "true").ToLowerInvariant()
$autoPublish = (Get-Setting -Name "AUTO_PUBLISH" -Default "false").ToLowerInvariant()
if ($schedulerEnabled -ne "false") {
    throw "SCHEDULER_ENABLED must remain false during rollback"
}
if ($shadowMode -ne "true") {
    throw "SHADOW_MODE must remain true during rollback"
}
if ($autoPublish -ne "false") {
    throw "AUTO_PUBLISH must remain false during rollback"
}
$compose = @("compose", "--env-file", $EnvFile, "-f", $composeFile)

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker @compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed: $($Arguments -join ' ')"
    }
}

function Get-Scalar {
    param([string]$Sql)
    $value = & docker @compose exec -T db `
        psql -X -q -t -A -v ON_ERROR_STOP=1 `
        -U $postgresUser -d $postgresDatabase -c $Sql
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL scalar query failed"
    }
    return ($value | Select-Object -Last 1).Trim()
}

function Assert-A4DatabaseState {
    $revision = Get-Scalar "SELECT version_num FROM alembic_version"
    $activeRevision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    if (
        $revision -ne "v0005_borrowed_tristate" -or
        $activeRevision -ne $a4Revision
    ) {
        throw "A4 database state is not safe for service restart"
    }
}

function Restore-A4 {
    Invoke-Compose run --rm --no-deps migration `
        alembic -c database/alembic.ini upgrade head
    Invoke-Compose run --rm --no-deps importer
    $revision = Get-Scalar "SELECT version_num FROM alembic_version"
    $activeRevision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $waterStages = [int](Get-Scalar "SELECT COUNT(*) FROM stages WHERE guide_id='TW_DEEP_WATER_08_10_20260808'")
    $borrowedNulls = [int](Get-Scalar "SELECT COUNT(*) FROM team_members WHERE is_borrowed IS NULL")
    if (
        $revision -ne "v0005_borrowed_tristate" -or
        $activeRevision -ne $a4Revision -or
        $waterStages -ne 1 -or
        $borrowedNulls -lt 1
    ) {
        throw "A4 restoration verification failed"
    }
    Write-Host "A4_RESTORED_OK alembic=$revision active_revision=$activeRevision borrowed_nulls=$borrowedNulls"
}

$servicesStopped = $false
$needsA4Restore = $false
$leaveAtA3Completed = $false
$primaryError = $null
try {
    Assert-A4DatabaseState

    # Mark recovery before the native command.  Docker may stop only a subset
    # before returning a non-zero exit, so finally must always attempt restart.
    $servicesStopped = $true
    Invoke-Compose stop web api scheduler
    $checkpointMount = "${CheckpointRoot}:/rollback:ro"
    # The importer commits atomically, but process/output handling can still
    # fail after the commit.  Arm idempotent A4 restoration before invocation.
    $needsA4Restore = $true
    $rollbackOutput = & docker @compose run --rm --no-deps `
        --volume $checkpointMount `
        importer `
        python -m pcr_pipeline.import_pve `
        --research-core /rollback/research_core/pcr_tw_project `
        --manifest /app/scripts/research_core_rp_a3_manifest.sha256 `
        --manifest-sha256 $a3ManifestSha256 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Pinned RP-A3 activation failed: $($rollbackOutput -join [Environment]::NewLine)"
    }
    $proofLines = @(
        $rollbackOutput |
            ForEach-Object { [string]$_ } |
            Where-Object { $_ -match '"status"\s*:\s*"PINNED_ROLLBACK_SOURCE_OK"' }
    )
    if ($proofLines.Count -ne 1) {
        throw "RP-A3 activation did not emit the pinned-source proof"
    }
    $proofLine = $proofLines[0].Trim()
    $proof = $proofLine | ConvertFrom-Json
    if (
        $proof.status -ne "PINNED_ROLLBACK_SOURCE_OK" -or
        $proof.manifest_sha256 -ne $a3ManifestSha256 -or
        $proof.revision_id -ne $a3Revision -or
        [int]$proof.file_count -ne 48 -or
        [int]$proof.csv_row_count -ne 239
    ) {
        throw "RP-A3 pinned-source proof payload is invalid"
    }
    Write-Host $proofLine
    $borrowedNulls = [int](Get-Scalar "SELECT COUNT(*) FROM team_members WHERE is_borrowed IS NULL")
    $stageCount = [int](Get-Scalar "SELECT COUNT(*) FROM stages")
    $teamCount = [int](Get-Scalar "SELECT COUNT(*) FROM teams")
    $waterStages = [int](Get-Scalar "SELECT COUNT(*) FROM stages WHERE guide_id='TW_DEEP_WATER_08_10_20260808'")
    $activeRevision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $activeMaterialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    if (
        $borrowedNulls -ne 0 -or
        $stageCount -ne 2 -or
        $teamCount -ne 5 -or
        $waterStages -ne 0 -or
        $activeRevision -ne $a3Revision -or
        $activeMaterialization -ne $a3Materialization
    ) {
        throw "RP-A3 legacy materialization is not downgrade-safe"
    }
    Write-Host "A3_LEGACY_MATERIALIZATION_OK stages=$stageCount teams=$teamCount borrowed_nulls=$borrowedNulls active_revision=$activeRevision materialization=$activeMaterialization"

    Invoke-Compose run --rm --no-deps migration `
        alembic -c database/alembic.ini downgrade v0004_unknown_operation_mode
    $downgradedRevision = Get-Scalar "SELECT version_num FROM alembic_version"
    if ($downgradedRevision -ne "v0004_unknown_operation_mode") {
        throw "V0005 to V0004 downgrade did not complete"
    }
    $downgradedActive = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $downgradedMaterialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    if (
        $downgradedActive -ne $a3Revision -or
        $downgradedMaterialization -ne $a3Materialization
    ) {
        throw "A3 identity changed during schema downgrade"
    }
    Write-Host "A4_A3_ROLLBACK_READY_OK alembic=$downgradedRevision borrowed_nulls=$borrowedNulls"

    if ($LeaveAtA3) {
        # This is the sole successful permanent-rollback boundary.  The exact
        # A3 data and schema were verified, but old services remain quiesced
        # until the operator deploys the rp-a3-1 images.
        $leaveAtA3Completed = $true
        $needsA4Restore = $false
    }
    else {
        Restore-A4
        $needsA4Restore = $false
    }
}
catch {
    $primaryError = $_
}
finally {
    if ($needsA4Restore) {
        try {
            Restore-A4
            $needsA4Restore = $false
        }
        catch {
            if ($null -eq $primaryError) {
                $primaryError = $_
            }
            else {
                $primaryError = [System.Exception]::new(
                    "$($primaryError.Exception.Message); A4 restore also failed: $($_.Exception.Message)"
                )
            }
        }
    }
    if ($servicesStopped -and $leaveAtA3Completed) {
        Write-Host "A3_SERVICES_QUIESCED_OK deploy_tag=rp-a3-1"
    }
    elseif ($servicesStopped -and -not $needsA4Restore) {
        try {
            Assert-A4DatabaseState
            Invoke-Compose up --detach --no-build --wait --wait-timeout 60 scheduler api web
            $ready = Invoke-RestMethod `
                -Uri "http://127.0.0.1:${apiPort}/health/ready" `
                -TimeoutSec 5
            if (
                $ready.status -ne "ok" -or
                $ready.checks.database -ne "ok" -or
                $ready.checks.fixture -ne "imported"
            ) {
                throw "A4 API readiness contract failed after service restart"
            }
            Write-Host "A4_SERVICES_READY_OK database=ok fixture=imported"
        }
        catch {
            $restartError = $_
            try {
                Invoke-Compose stop web api scheduler
            }
            catch {
                $restartError = [System.Exception]::new(
                    "$($restartError.Exception.Message); service requiesce also failed: $($_.Exception.Message)"
                )
            }
            if ($null -eq $primaryError) {
                $primaryError = $restartError
            }
            else {
                $primaryError = [System.Exception]::new(
                    "$($primaryError.Exception.Message); A4 service readiness also failed: $($restartError.Exception.Message)"
                )
            }
        }
    }
    elseif ($servicesStopped) {
        $quiescedMessage = "A4 restoration was not verified; services were left quiesced for manual recovery"
        Write-Warning "SERVICES_LEFT_QUIESCED: $quiescedMessage"
        if ($null -eq $primaryError) {
            $primaryError = [System.Exception]::new($quiescedMessage)
        }
    }
}

if ($null -ne $primaryError) {
    throw $primaryError
}
if ($LeaveAtA3) {
    Write-Host "A4_A3_ROLLBACK_COMPLETE_OK alembic=v0004_unknown_operation_mode services=quiesced"
}
else {
    Write-Host "A4_A3_ROLLBACK_DRILL_OK"
}
