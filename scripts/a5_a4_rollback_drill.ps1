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
    [string]$CheckpointRoot,
    [Parameter(Mandatory = $true)]
    [string]$VerifiedBackupPath,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{64}$')]
    [string]$VerifiedBackupSha256,
    [Parameter(HelpMessage = "After exact A4 verification and V0006 to V0005 downgrade, keep services quiesced for an intentional A4 deployment instead of restoring A5.")]
    [switch]$LeaveAtA4
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$composeFile = Join-Path $repoRoot "infra\compose.yml"
$EnvFile = [System.IO.Path]::GetFullPath($EnvFile)
$CheckpointRoot = [System.IO.Path]::GetFullPath($CheckpointRoot)
$VerifiedBackupPath = [System.IO.Path]::GetFullPath($VerifiedBackupPath)
$checkpointCore = Join-Path $CheckpointRoot "research_core\pcr_tw_project"
$a4Manifest = Join-Path $repoRoot "scripts\research_core_rp_a4_manifest.sha256"
$a4ManifestSha256 = "3daf2ab7c212b4f11c58883980d0ada3862400923c81a9bdedcc0500e59b1a9e"
$a4Revision = "c5a5f13e0efaf96c1a266c1016d3a1a54740859952ce21f9db3cf89d779d57b9"
$a4Semantic = "73bc25ab75e78f4e762c3afc902c53dfa47180a36a7359a102fbf5e173fb35bf"
$a4EvidenceToClaimSha256 = "6a589eb4eca59f94e52af22752d376be576c1b1562b28a43acadb2abfa219853"
$a4ClaimToEvidenceSha256 = "3c4450f90814fa78384d36d60434c665e1b3a2b7b247804ed324d223e7aeb12a"
$a5ManifestSha256 = "1826c8493d40f71a6d0bb9096f57b92fe4e839d52bddf021b0c51e0186dcbda7"
$a5Revision = "1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c"
$a5Semantic = "c77bc9893fa0b442832c1dff0c7c4a1c5e6d63ba9bce27c1c2f8078c5c2511b8"
$a5EvidenceToClaimSha256 = "84fea5ed4095dfcbb98cb52816c2e8a7a3d9fd1acd9ef225541ba27b8bcc192e"
$a5ClaimToEvidenceSha256 = "b0fefe463e3968266ed8a8378fd8b7f5c94817a4dd548f920facf7c182fa0e64"
$arenaTables = @(
    "arena_defenses",
    "arena_defense_members",
    "arena_counters",
    "arena_counter_members",
    "arena_counter_evidence",
    "arena_counter_claims"
)
$a5RowCounts = [ordered]@{
    stages = 3
    teams = 10
    team_members = 50
    characters = 35
    evidence = 64
    claims = 62
    operation_timelines = 15
    timeline_steps = 37
    arena_defenses = 1
    arena_defense_members = 5
    arena_counters = 2
    arena_counter_members = 10
    arena_counter_evidence = 4
    arena_counter_claims = 4
}
$a4RowCounts = [ordered]@{
    stages = 3
    teams = 10
    team_members = 50
    characters = 25
    evidence = 55
    claims = 53
    operation_timelines = 15
    timeline_steps = 37
}
$a5ServingCounts = [ordered]@{
    stages = 3
    teams = 10
    team_members = 50
    characters = 35
    evidence = 64
    claims = 62
    stage_evidence = 47
    stage_claims = 46
    team_evidence = 95
    claim_evidence = 150
    operation_timelines = 15
    timeline_steps = 37
    arena_defenses = 1
    arena_defense_members = 5
    arena_counters = 2
    arena_counter_members = 10
    arena_counter_evidence = 4
    arena_counter_claims = 4
}
$a4ServingCounts = [ordered]@{
    stages = 3
    teams = 10
    team_members = 50
    characters = 25
    evidence = 55
    claims = 53
    stage_evidence = 47
    stage_claims = 46
    team_evidence = 95
    claim_evidence = 141
    operation_timelines = 15
    timeline_steps = 37
}

foreach ($requiredFile in @($EnvFile, $a4Manifest, $VerifiedBackupPath)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Missing rollback drill input: $requiredFile"
    }
}
if (-not (Test-Path -LiteralPath $checkpointCore -PathType Container)) {
    throw "Missing RP-A4 research core: $checkpointCore"
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
$compose = @(
    "compose",
    "--project-name", $ProjectName,
    "--env-file", $EnvFile,
    "-f", $composeFile
)

function Invoke-Compose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & docker @compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose failed: $($Arguments -join ' ')"
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
    foreach ($serviceName in @("api", "importer", "migration", "role-provision")) {
        $service = Get-ResolvedService -Config $config -ServiceName $serviceName
        if ([string]$service.image -cne $ExpectedApiImage) {
            throw "Resolved $serviceName image is not the expected A5 API image"
        }
    }
    $scheduler = Get-ResolvedService -Config $config -ServiceName "scheduler"
    if ([string]$scheduler.image -cne $ExpectedSchedulerImage) {
        throw "Resolved scheduler image is not the expected A5 scheduler image"
    }
    $api = Get-ResolvedService -Config $config -ServiceName "api"
    $apiPorts = @($api.ports)
    if ($apiPorts.Count -ne 1) {
        throw "Resolved API must expose exactly one published port"
    }
    $apiBinding = $apiPorts[0]
    if (
        [int]$apiBinding.target -ne 8000 -or
        [int]$apiBinding.published -ne $ExpectedApiPort -or
        [string]$apiBinding.host_ip -cne "127.0.0.1" -or
        [string]$apiBinding.protocol -cne "tcp"
    ) {
        throw "Resolved API port binding does not match the expected loopback endpoint"
    }
    Write-Host "A5_COMPOSE_PREFLIGHT_OK project=$ProjectName api_image=$ExpectedApiImage scheduler_image=$ExpectedSchedulerImage api_port=$ExpectedApiPort"
}

function Get-ActualApiPort {
    $portOutput = & docker @compose port api 8000 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose could not resolve the running API port: $($portOutput -join [Environment]::NewLine)"
    }
    $portLines = @(
        $portOutput |
            ForEach-Object { ([string]$_).Trim() } |
            Where-Object { $_ }
    )
    if ($portLines.Count -ne 1) {
        throw "Docker Compose returned an ambiguous running API port"
    }
    $match = [regex]::Match($portLines[0], '^127\.0\.0\.1:(\d{1,5})$')
    if (-not $match.Success) {
        throw "Running API is not bound to the expected loopback endpoint"
    }
    $actualApiPort = [int]$match.Groups[1].Value
    if ($actualApiPort -ne $ExpectedApiPort) {
        throw "Running API port does not match ExpectedApiPort"
    }
    return $actualApiPort
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
    foreach ($table in $Expected.Keys) {
        if ([int]$Actual.$table -ne [int]$Expected[$table]) {
            throw "$Label row-count mismatch for $table"
        }
    }
}

function Assert-DatabaseCounts {
    param(
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Expected,
        [Parameter(Mandatory = $true)][string]$Label
    )
    foreach ($table in $Expected.Keys) {
        $actual = [int](Get-Scalar "SELECT COUNT(*) FROM $table")
        if ($actual -ne [int]$Expected[$table]) {
            throw "$Label database count mismatch for $table"
        }
    }
}

function Get-ImportResult {
    param(
        [Parameter(Mandatory = $true)][object[]]$Output,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $resultLines = @(
        $Output |
            ForEach-Object { [string]$_ } |
            Where-Object {
                $_ -match '^\{.*"activated"\s*:\s*(true|false)' -and
                $_ -match '"revision_id"\s*:'
            }
    )
    if ($resultLines.Count -ne 1) {
        throw "$Label importer did not emit exactly one ImportResult JSON object"
    }
    try {
        return ($resultLines[0].Trim() | ConvertFrom-Json)
    }
    catch {
        throw "$Label ImportResult JSON is invalid"
    }
}

function Assert-A5ImportResult {
    param(
        [Parameter(Mandatory = $true)]$Result,
        [Parameter(Mandatory = $true)][bool]$ExpectedActivated
    )
    if (
        $Result.created -ne $false -or
        $Result.activated -ne $ExpectedActivated -or
        $Result.fixture_sha256 -ne $a5Revision -or
        $Result.revision_id -ne $a5Revision -or
        $Result.raw_tree_sha256 -ne $a5Revision -or
        $Result.semantic_tree_sha256 -ne $a5Semantic -or
        [int]$Result.file_count -ne 48 -or
        [int]$Result.csv_file_count -ne 13 -or
        [int]$Result.csv_row_count -ne 356
    ) {
        throw "A5 restoration ImportResult identity is invalid"
    }
    Assert-CountObject -Actual $Result.row_counts -Expected $a5RowCounts -Label "A5 ImportResult"
}

function Assert-RevisionIdentity {
    param(
        [Parameter(Mandatory = $true)][string]$Revision,
        [Parameter(Mandatory = $true)][string]$ManifestSha256,
        [Parameter(Mandatory = $true)][string]$SemanticSha256,
        [Parameter(Mandatory = $true)][int]$CsvRowCount,
        [Parameter(Mandatory = $true)][int]$EvidenceToClaimCount,
        [Parameter(Mandatory = $true)][string]$EvidenceToClaimSha256,
        [Parameter(Mandatory = $true)][int]$ClaimToEvidenceCount,
        [Parameter(Mandatory = $true)][string]$ClaimToEvidenceSha256,
        [Parameter(Mandatory = $true)][string]$ImportRunId,
        [Parameter(Mandatory = $true)][string]$MaterializationSha256,
        [Parameter(Mandatory = $true)][int]$MaterializationSchemaVersion,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$RowCounts,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if ($ImportRunId -notmatch '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$') {
        throw "$Label import run ID is invalid"
    }
    if ($MaterializationSha256 -notmatch '^[0-9a-f]{64}$') {
        throw "$Label instance materialization SHA-256 is invalid"
    }
    $raw = Get-Scalar "SELECT raw_tree_sha256 FROM core_revisions WHERE revision_id='$Revision'"
    $semantic = Get-Scalar "SELECT semantic_tree_sha256 FROM core_revisions WHERE revision_id='$Revision'"
    $manifest = Get-Scalar "SELECT manifest_sha256 FROM core_revisions WHERE revision_id='$Revision'"
    $materialization = Get-Scalar "SELECT COALESCE(materialization_sha256, '') FROM core_revisions WHERE revision_id='$Revision'"
    $revisionRun = Get-Scalar "SELECT COALESCE(import_run_id, '') FROM core_revisions WHERE revision_id='$Revision'"
    $revisionStatus = Get-Scalar "SELECT status FROM core_revisions WHERE revision_id='$Revision'"
    $serialization = [int](Get-Scalar "SELECT serialization_version FROM core_revisions WHERE revision_id='$Revision'")
    $fileCount = [int](Get-Scalar "SELECT file_count FROM core_revisions WHERE revision_id='$Revision'")
    $csvFileCount = [int](Get-Scalar "SELECT csv_file_count FROM core_revisions WHERE revision_id='$Revision'")
    $storedCsvRows = [int](Get-Scalar "SELECT csv_row_count FROM core_revisions WHERE revision_id='$Revision'")
    $forwardCount = [int](Get-Scalar "SELECT evidence_to_claim_count FROM core_revisions WHERE revision_id='$Revision'")
    $forwardHash = Get-Scalar "SELECT evidence_to_claim_sha256 FROM core_revisions WHERE revision_id='$Revision'"
    $reverseCount = [int](Get-Scalar "SELECT claim_to_evidence_count FROM core_revisions WHERE revision_id='$Revision'")
    $reverseHash = Get-Scalar "SELECT claim_to_evidence_sha256 FROM core_revisions WHERE revision_id='$Revision'"
    $artifactSchema = [int](Get-Scalar "SELECT manifest->>'schema_version' FROM core_revisions WHERE revision_id='$Revision'")
    $artifactFileCount = [int](Get-Scalar "SELECT COUNT(*) FROM core_revisions AS revision CROSS JOIN LATERAL jsonb_object_keys(CASE WHEN jsonb_typeof(revision.manifest->'files') = 'object' THEN revision.manifest->'files' ELSE '{}'::jsonb END) AS file_key WHERE revision.revision_id='$Revision'")
    $artifactForwardCount = [int](Get-Scalar "SELECT manifest#>>'{edges,evidence_declared,count}' FROM core_revisions WHERE revision_id='$Revision'")
    $artifactForwardHash = Get-Scalar "SELECT manifest#>>'{edges,evidence_declared,sha256}' FROM core_revisions WHERE revision_id='$Revision'"
    $artifactReverseCount = [int](Get-Scalar "SELECT manifest#>>'{edges,claim_evidence,count}' FROM core_revisions WHERE revision_id='$Revision'")
    $artifactReverseHash = Get-Scalar "SELECT manifest#>>'{edges,claim_evidence,sha256}' FROM core_revisions WHERE revision_id='$Revision'"
    if (
        $raw -ne $Revision -or
        $semantic -ne $SemanticSha256 -or
        $manifest -ne $ManifestSha256 -or
        $materialization -ne $MaterializationSha256 -or
        $revisionRun -ne $ImportRunId -or
        $revisionStatus -ne "SUCCEEDED" -or
        $serialization -ne 1 -or
        $fileCount -ne 48 -or
        $csvFileCount -ne 13 -or
        $storedCsvRows -ne $CsvRowCount -or
        $forwardCount -ne $EvidenceToClaimCount -or
        $forwardHash -ne $EvidenceToClaimSha256 -or
        $reverseCount -ne $ClaimToEvidenceCount -or
        $reverseHash -ne $ClaimToEvidenceSha256 -or
        $artifactSchema -ne 1 -or
        $artifactFileCount -ne 48 -or
        $artifactForwardCount -ne $EvidenceToClaimCount -or
        $artifactForwardHash -ne $EvidenceToClaimSha256 -or
        $artifactReverseCount -ne $ClaimToEvidenceCount -or
        $artifactReverseHash -ne $ClaimToEvidenceSha256
    ) {
        throw "$Label CoreRevision portable or instance identity drifted"
    }
    $runStatus = Get-Scalar "SELECT status FROM import_runs WHERE id='$ImportRunId'"
    $fixture = Get-Scalar "SELECT fixture_sha256 FROM import_runs WHERE id='$ImportRunId'"
    $canonicalSource = Get-Scalar "SELECT canonical_source FROM import_runs WHERE id='$ImportRunId'"
    $runMaterialization = Get-Scalar "SELECT manifest#>>'{materialization,sha256}' FROM import_runs WHERE id='$ImportRunId'"
    $runSchema = [int](Get-Scalar "SELECT manifest#>>'{materialization,schema_version}' FROM import_runs WHERE id='$ImportRunId'")
    if (
        $runStatus -ne "SUCCEEDED" -or
        $fixture -ne $Revision -or
        $canonicalSource -ne "research_core_file_ssot" -or
        $runMaterialization -ne $MaterializationSha256 -or
        $runSchema -ne $MaterializationSchemaVersion
    ) {
        throw "$Label ImportRun identity drifted"
    }
    $runCountObject = (Get-Scalar "SELECT row_counts::text FROM import_runs WHERE id='$ImportRunId'") | ConvertFrom-Json
    Assert-CountObject -Actual $runCountObject -Expected $RowCounts -Label "$Label ImportRun"
}

function Assert-Activation {
    param(
        [Parameter(Mandatory = $true)][long]$Sequence,
        [Parameter(Mandatory = $true)][string]$FromRevision,
        [Parameter(Mandatory = $true)][string]$ToRevision,
        [Parameter(Mandatory = $true)][string]$Kind,
        [Parameter(Mandatory = $true)][long]$ExpectedEpoch,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $actualFrom = Get-Scalar "SELECT COALESCE(from_revision_id, '') FROM revision_activations WHERE sequence_no=$Sequence"
    $actualTo = Get-Scalar "SELECT to_revision_id FROM revision_activations WHERE sequence_no=$Sequence"
    $actualKind = Get-Scalar "SELECT kind FROM revision_activations WHERE sequence_no=$Sequence"
    $actualReason = Get-Scalar "SELECT reason FROM revision_activations WHERE sequence_no=$Sequence"
    $actualActor = Get-Scalar "SELECT actor FROM revision_activations WHERE sequence_no=$Sequence"
    $actualEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$Sequence")
    $expectedReasons = @{
        IMPORT = "activate manifest-pinned full-core import"
        ROLLBACK = "rollback to earlier verified immutable revision"
        REACTIVATE = "reactivate later verified immutable revision"
    }
    if (
        $actualFrom -ne $FromRevision -or
        $actualTo -ne $ToRevision -or
        $actualKind -ne $Kind -or
        $actualReason -ne $expectedReasons[$Kind] -or
        $actualActor -ne "pcr_pipeline.import_pve" -or
        $actualEpoch -ne $ExpectedEpoch
    ) {
        throw "$Label activation audit chronology drifted"
    }
}

function Get-ArenaCounts {
    return [ordered]@{
        arena_defenses = [int](Get-Scalar "SELECT COUNT(*) FROM arena_defenses")
        arena_defense_members = [int](Get-Scalar "SELECT COUNT(*) FROM arena_defense_members")
        arena_counters = [int](Get-Scalar "SELECT COUNT(*) FROM arena_counters")
        arena_counter_members = [int](Get-Scalar "SELECT COUNT(*) FROM arena_counter_members")
        arena_counter_evidence = [int](Get-Scalar "SELECT COUNT(*) FROM arena_counter_evidence")
        arena_counter_claims = [int](Get-Scalar "SELECT COUNT(*) FROM arena_counter_claims")
    }
}

function Assert-ArenaCounts {
    param(
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Actual,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Expected,
        [Parameter(Mandatory = $true)][string]$Label
    )
    foreach ($table in $arenaTables) {
        if ([int]$Actual[$table] -ne [int]$Expected[$table]) {
            throw "$Label Arena count mismatch for $table"
        }
    }
}

function Assert-A5DatabaseState {
    param(
        [Parameter(Mandatory = $true)][string]$ExpectedImportRunId,
        [Parameter(Mandatory = $true)][string]$ExpectedMaterializationSha256
    )
    $revision = Get-Scalar "SELECT version_num FROM alembic_version"
    $activeRevision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $activeImportRun = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $activeMaterialization = Get-Scalar "SELECT COALESCE(materialization_sha256, '') FROM materialization_state WHERE id=1"
    if (
        $revision -ne "v0006_arena_counter_slice" -or
        $activeRevision -ne $a5Revision -or
        $activeImportRun -ne $ExpectedImportRunId -or
        $activeMaterialization -ne $ExpectedMaterializationSha256
    ) {
        throw "A5 database state is not safe for rollback or service restart"
    }
    Assert-RevisionIdentity `
        -Revision $a5Revision `
        -ManifestSha256 $a5ManifestSha256 `
        -SemanticSha256 $a5Semantic `
        -CsvRowCount 356 `
        -EvidenceToClaimCount 111 `
        -EvidenceToClaimSha256 $a5EvidenceToClaimSha256 `
        -ClaimToEvidenceCount 277 `
        -ClaimToEvidenceSha256 $a5ClaimToEvidenceSha256 `
        -ImportRunId $ExpectedImportRunId `
        -MaterializationSha256 $ExpectedMaterializationSha256 `
        -MaterializationSchemaVersion 3 `
        -RowCounts $a5RowCounts `
        -Label "A5"
    $stateCountObject = (Get-Scalar "SELECT serving_counts::text FROM materialization_state WHERE id=1") | ConvertFrom-Json
    Assert-CountObject -Actual $stateCountObject -Expected $a5ServingCounts -Label "A5 MaterializationState"
    Assert-DatabaseCounts -Expected $a5ServingCounts -Label "A5"
}

function Assert-OriginActivationAnchor {
    $originKind = Get-Scalar "SELECT kind FROM revision_activations WHERE sequence_no=$originActivationSequence"
    if ($originKind -notin @("IMPORT", "REACTIVATE")) {
        throw "Origin A5 activation kind is not a forward activation"
    }
    if ($originActivationEpoch -le 0 -or $originActivationEpoch -gt $originEpoch) {
        throw "Origin A5 activation epoch is ahead of the current materialization state"
    }
    $originFrom = Get-Scalar "SELECT COALESCE(from_revision_id, '') FROM revision_activations WHERE sequence_no=$originActivationSequence"
    Assert-Activation `
        -Sequence $originActivationSequence `
        -FromRevision $originFrom `
        -ToRevision $a5Revision `
        -Kind $originKind `
        -ExpectedEpoch $originActivationEpoch `
        -Label "Origin A5"
}

function Assert-OriginApiReadiness {
    $actualApiPort = Get-ActualApiPort
    $readiness = Invoke-RestMethod `
        -Uri "http://127.0.0.1:${actualApiPort}/health/ready" `
        -TimeoutSec 30
    if (
        $readiness.status -ne "ok" -or
        $readiness.checks.database -ne "ok" -or
        $readiness.checks.fixture -ne "imported"
    ) {
        throw "Origin A5 API readiness did not verify the current materialization"
    }
    $epochAfterReadiness = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if ($epochAfterReadiness -ne $originEpoch) {
        throw "Origin A5 materialization epoch changed during readiness verification"
    }
    Write-Host "A5_ORIGIN_READINESS_OK api_port=$actualApiPort database=ok fixture=imported state_epoch=$epochAfterReadiness"
}

function Assert-A4RecoveryState {
    param(
        [Parameter(Mandatory = $true)][string]$AlembicRevision,
        [Parameter(Mandatory = $true)][string]$ImportRunId,
        [Parameter(Mandatory = $true)][string]$MaterializationSha256,
        [Parameter(Mandatory = $true)][long]$StateEpoch
    )
    if ($AlembicRevision -notin @("v0005_borrowed_tristate", "v0006_arena_counter_slice")) {
        throw "A4 recovery state is outside the supported schema boundary"
    }
    if ($StateEpoch -le $originEpoch) {
        throw "A4 recovery epoch did not advance beyond the origin A5 epoch"
    }
    Assert-Activation `
        -Sequence ($originActivationSequence + 1) `
        -FromRevision $a5Revision `
        -ToRevision $a4Revision `
        -Kind "ROLLBACK" `
        -ExpectedEpoch $StateEpoch `
        -Label "A4 recovery"
    Assert-RevisionIdentity `
        -Revision $a4Revision `
        -ManifestSha256 $a4ManifestSha256 `
        -SemanticSha256 $a4Semantic `
        -CsvRowCount 325 `
        -EvidenceToClaimCount 102 `
        -EvidenceToClaimSha256 $a4EvidenceToClaimSha256 `
        -ClaimToEvidenceCount 268 `
        -ClaimToEvidenceSha256 $a4ClaimToEvidenceSha256 `
        -ImportRunId $ImportRunId `
        -MaterializationSha256 $MaterializationSha256 `
        -MaterializationSchemaVersion 2 `
        -RowCounts $a4RowCounts `
        -Label "A4 recovery"
    $stateCountObject = (Get-Scalar "SELECT serving_counts::text FROM materialization_state WHERE id=1") | ConvertFrom-Json
    Assert-CountObject -Actual $stateCountObject -Expected $a4ServingCounts -Label "A4 recovery MaterializationState"
    Assert-DatabaseCounts -Expected $a4ServingCounts -Label "A4 recovery"
}

function Assert-A5RecoveryChain {
    $reactivationSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $stateEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    $rollbackEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$($originActivationSequence + 1)")
    $reactivationEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$($originActivationSequence + 2)")
    if (
        $reactivationSequence -ne ($originActivationSequence + 2) -or
        $rollbackEpoch -le $originEpoch -or
        $reactivationEpoch -le $rollbackEpoch -or
        $stateEpoch -ne $reactivationEpoch
    ) {
        throw "A5 recovery activation sequence or epoch chain is invalid"
    }
    Assert-Activation `
        -Sequence ($originActivationSequence + 1) `
        -FromRevision $a5Revision `
        -ToRevision $a4Revision `
        -Kind "ROLLBACK" `
        -ExpectedEpoch $rollbackEpoch `
        -Label "A4 rollback"
    Assert-Activation `
        -Sequence $reactivationSequence `
        -FromRevision $a4Revision `
        -ToRevision $a5Revision `
        -Kind "REACTIVATE" `
        -ExpectedEpoch $reactivationEpoch `
        -Label "A5 reactivation"
}

function Get-A5RecoveryMode {
    $alembicRevision = Get-Scalar "SELECT version_num FROM alembic_version"
    $activeRevision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $activeImportRun = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $activeMaterialization = Get-Scalar "SELECT COALESCE(materialization_sha256, '') FROM materialization_state WHERE id=1"
    $activationSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $stateEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")

    if ($activeRevision -eq $a5Revision) {
        if (
            $activeImportRun -ne $originA5ImportRunId -or
            $activeMaterialization -ne $originA5Materialization
        ) {
            throw "Active A5 recovery identity does not match the origin instance"
        }
        Assert-A5DatabaseState `
            -ExpectedImportRunId $originA5ImportRunId `
            -ExpectedMaterializationSha256 $originA5Materialization
        if (
            $activationSequence -eq $originActivationSequence -and
            $stateEpoch -eq $originEpoch
        ) {
            Assert-OriginActivationAnchor
            return "ORIGIN_NOOP"
        }
        if ($activationSequence -eq ($originActivationSequence + 2)) {
            Assert-A5RecoveryChain
            return "ALREADY_RESTORED_NOOP"
        }
        throw "Active A5 recovery chronology is neither origin nor already restored"
    }

    if ($activeRevision -eq $a4Revision) {
        if ($activationSequence -ne ($originActivationSequence + 1)) {
            throw "Active A4 recovery chronology is not the exact rollback successor"
        }
        Assert-A4RecoveryState `
            -AlembicRevision $alembicRevision `
            -ImportRunId $activeImportRun `
            -MaterializationSha256 $activeMaterialization `
            -StateEpoch $stateEpoch
        return "A4_REACTIVATE"
    }

    throw "Recovery state is neither the origin A5, exact A4 rollback, nor restored A5"
}

function Assert-A5RecoveryOutcome {
    param([Parameter(Mandatory = $true)][string]$Mode)
    if ($Mode -eq "ORIGIN_NOOP") {
        $sequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
        $epoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
        if ($sequence -ne $originActivationSequence -or $epoch -ne $originEpoch) {
            throw "Origin A5 no-op changed activation chronology or epoch"
        }
        Assert-OriginActivationAnchor
        return
    }
    if ($Mode -in @("A4_REACTIVATE", "ALREADY_RESTORED_NOOP")) {
        Assert-A5RecoveryChain
        return
    }
    throw "Unknown A5 recovery mode: $Mode"
}

function Restore-A5 {
    $recoveryMode = Get-A5RecoveryMode
    $expectedActivated = $recoveryMode -eq "A4_REACTIVATE"
    Write-Host "A5_RECOVERY_MODE_OK mode=$recoveryMode expected_activated=$($expectedActivated.ToString().ToLowerInvariant())"
    Invoke-Compose run --rm --no-deps migration `
        alembic -c database/alembic.ini upgrade head
    # V0006 recreates the Arena tables after a real downgrade. PostgreSQL does
    # not carry the old table grants onto those new objects, so reapply the
    # idempotent service-role contract before the importer touches them.
    Invoke-Compose run --rm --no-deps role-provision
    $restoreOutput = & docker @compose run --rm --no-deps importer 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Canonical A5 restoration import failed: $($restoreOutput -join [Environment]::NewLine)"
    }
    $baselineLines = @(
        $restoreOutput |
            ForEach-Object { [string]$_ } |
            Where-Object { $_ -match '^RESEARCH_BASELINE_OK\s*\|' }
    )
    if (
        $baselineLines.Count -ne 1 -or
        $baselineLines[0] -notmatch [regex]::Escape("manifest_sha256=$a5ManifestSha256")
    ) {
        throw "Canonical A5 restoration did not emit the expected baseline proof"
    }
    Write-Host $baselineLines[0].Trim()
    $restoreResult = Get-ImportResult -Output $restoreOutput -Label "A5 restoration"
    Assert-A5ImportResult `
        -Result $restoreResult `
        -ExpectedActivated $expectedActivated
    if ($restoreResult.import_run_id -ne $originA5ImportRunId) {
        throw "A5 restoration did not preserve the origin import run"
    }
    Write-Host ($restoreResult | ConvertTo-Json -Compress -Depth 8)
    Assert-A5DatabaseState `
        -ExpectedImportRunId $originA5ImportRunId `
        -ExpectedMaterializationSha256 $originA5Materialization
    Assert-A5RecoveryOutcome -Mode $recoveryMode
    Write-Host "A5_RESTORED_OK mode=$recoveryMode alembic=v0006_arena_counter_slice active_revision=$a5Revision import_run=$originA5ImportRunId arena_defenses=1 arena_counters=2"
}

Assert-ComposePreflight

$servicesStopped = $false
$needsA5Restore = $false
$leaveAtA4Completed = $false
$primaryError = $null
$originA5ImportRunId = ""
$originA5Materialization = ""
$originActivationSequence = [long]0
$originActivationEpoch = [long]0
$originEpoch = [long]0
$a4ActivationVerified = $false
$a4ActivationEpoch = [long]0
try {
    $originA5ImportRunId = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $originA5Materialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    $originActivationSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $originActivationEpoch = [long](Get-Scalar "SELECT epoch FROM revision_activations WHERE sequence_no=$originActivationSequence")
    $originEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    Assert-A5DatabaseState `
        -ExpectedImportRunId $originA5ImportRunId `
        -ExpectedMaterializationSha256 $originA5Materialization
    Assert-OriginActivationAnchor
    # Readiness recomputes the typed materialization manifest whenever the
    # monotonic state epoch changes.  This distinguishes fully cleaned runtime
    # smokes from same-count serving-row drift before any service is quiesced.
    Assert-OriginApiReadiness
    Write-Host "A5_ORIGIN_VERIFIED_OK alembic=v0006_arena_counter_slice active_revision=$a5Revision import_run=$originA5ImportRunId materialization=$originA5Materialization activation_sequence=$originActivationSequence activation_epoch=$originActivationEpoch state_epoch=$originEpoch arena_defenses=1 arena_counters=2"

    # Mark recovery before the native command. Docker may stop only a subset
    # before returning a non-zero exit, so finally must always attempt restart.
    $servicesStopped = $true
    Invoke-Compose stop web api scheduler
    $checkpointMount = "${CheckpointRoot}:/rollback:ro"
    # The importer commits atomically, but process/output handling can still
    # fail after the commit. Arm idempotent A5 restoration before invocation.
    $needsA5Restore = $true
    $rollbackOutput = & docker @compose run --rm --no-deps `
        --volume $checkpointMount `
        importer `
        python -m pcr_pipeline.import_pve `
        --research-core /rollback/research_core/pcr_tw_project `
        --manifest /app/scripts/research_core_rp_a4_manifest.sha256 `
        --manifest-sha256 $a4ManifestSha256 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Pinned RP-A4 activation failed: $($rollbackOutput -join [Environment]::NewLine)"
    }
    $proofLines = @(
        $rollbackOutput |
            ForEach-Object { [string]$_ } |
            Where-Object { $_ -match '"status"\s*:\s*"PINNED_ROLLBACK_SOURCE_OK"' }
    )
    if ($proofLines.Count -ne 1) {
        throw "RP-A4 activation did not emit the pinned-source proof"
    }
    $proofLine = $proofLines[0].Trim()
    $proof = $proofLine | ConvertFrom-Json
    if (
        $proof.status -ne "PINNED_ROLLBACK_SOURCE_OK" -or
        $proof.manifest_sha256 -ne $a4ManifestSha256 -or
        $proof.revision_id -ne $a4Revision -or
        [int]$proof.file_count -ne 48 -or
        [int]$proof.csv_row_count -ne 325
    ) {
        throw "RP-A4 pinned-source proof payload is invalid"
    }
    Write-Host $proofLine
    $a4Result = Get-ImportResult -Output $rollbackOutput -Label "RP-A4 activation"
    if (
        $a4Result.activated -ne $true -or
        $a4Result.fixture_sha256 -ne $a4Revision -or
        $a4Result.revision_id -ne $a4Revision -or
        $a4Result.raw_tree_sha256 -ne $a4Revision -or
        $a4Result.semantic_tree_sha256 -ne $a4Semantic -or
        [int]$a4Result.file_count -ne 48 -or
        [int]$a4Result.csv_file_count -ne 13 -or
        [int]$a4Result.csv_row_count -ne 325
    ) {
        throw "RP-A4 ImportResult identity is invalid"
    }
    Assert-CountObject -Actual $a4Result.row_counts -Expected $a4RowCounts -Label "RP-A4 ImportResult"
    $a4ImportRunId = [string]$a4Result.import_run_id
    $a4InstanceMaterialization = Get-Scalar "SELECT COALESCE(materialization_sha256, '') FROM core_revisions WHERE revision_id='$a4Revision'"
    Assert-RevisionIdentity `
        -Revision $a4Revision `
        -ManifestSha256 $a4ManifestSha256 `
        -SemanticSha256 $a4Semantic `
        -CsvRowCount 325 `
        -EvidenceToClaimCount 102 `
        -EvidenceToClaimSha256 $a4EvidenceToClaimSha256 `
        -ClaimToEvidenceCount 268 `
        -ClaimToEvidenceSha256 $a4ClaimToEvidenceSha256 `
        -ImportRunId $a4ImportRunId `
        -MaterializationSha256 $a4InstanceMaterialization `
        -MaterializationSchemaVersion 2 `
        -RowCounts $a4RowCounts `
        -Label "RP-A4"
    Write-Host ($a4Result | ConvertTo-Json -Compress -Depth 8)

    $borrowedNulls = [int](Get-Scalar "SELECT COUNT(*) FROM team_members WHERE is_borrowed IS NULL")
    $stageCount = [int](Get-Scalar "SELECT COUNT(*) FROM stages")
    $teamCount = [int](Get-Scalar "SELECT COUNT(*) FROM teams")
    $waterStages = [int](Get-Scalar "SELECT COUNT(*) FROM stages WHERE guide_id='TW_DEEP_WATER_08_10_20260808'")
    $activeRevision = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $activeImportRun = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $activeMaterialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    $revisionMaterialization = Get-Scalar "SELECT materialization_sha256 FROM core_revisions WHERE revision_id='$a4Revision' AND status='SUCCEEDED'"
    $arena = Get-ArenaCounts
    Assert-ArenaCounts -Actual $arena -Expected ([ordered]@{
        arena_defenses = 0
        arena_defense_members = 0
        arena_counters = 0
        arena_counter_members = 0
        arena_counter_evidence = 0
        arena_counter_claims = 0
    }) -Label "A4"
    if (
        $borrowedNulls -lt 1 -or
        $stageCount -ne 3 -or
        $teamCount -ne 10 -or
        $waterStages -ne 1 -or
        $activeRevision -ne $a4Revision -or
        $activeImportRun -ne $a4ImportRunId -or
        $activeMaterialization -ne $a4InstanceMaterialization -or
        $revisionMaterialization -ne $a4InstanceMaterialization
    ) {
        throw "RP-A4 legacy materialization is not downgrade-safe"
    }
    $a4StateCountObject = (Get-Scalar "SELECT serving_counts::text FROM materialization_state WHERE id=1") | ConvertFrom-Json
    Assert-CountObject -Actual $a4StateCountObject -Expected $a4ServingCounts -Label "RP-A4 MaterializationState"
    Assert-DatabaseCounts -Expected $a4ServingCounts -Label "RP-A4"
    $a4ActivationSequence = [long](Get-Scalar "SELECT MAX(sequence_no) FROM revision_activations")
    $a4ActivationEpoch = [long](Get-Scalar "SELECT epoch FROM materialization_state WHERE id=1")
    if (
        $a4ActivationSequence -ne ($originActivationSequence + 1) -or
        $a4ActivationEpoch -le $originEpoch
    ) {
        throw "RP-A4 activation sequence or epoch did not advance exactly"
    }
    Assert-Activation `
        -Sequence $a4ActivationSequence `
        -FromRevision $a5Revision `
        -ToRevision $a4Revision `
        -Kind "ROLLBACK" `
        -ExpectedEpoch $a4ActivationEpoch `
        -Label "RP-A4 rollback"
    $a4ActivationVerified = $true
    Write-Host "A4_LEGACY_MATERIALIZATION_OK stages=$stageCount teams=$teamCount borrowed_nulls=$borrowedNulls arena_rows=0 active_revision=$activeRevision import_run=$a4ImportRunId materialization=$activeMaterialization activation_sequence=$a4ActivationSequence epoch=$a4ActivationEpoch"

    Invoke-Compose run --rm --no-deps migration `
        alembic -c database/alembic.ini downgrade v0005_borrowed_tristate
    $downgradedRevision = Get-Scalar "SELECT version_num FROM alembic_version"
    if ($downgradedRevision -ne "v0005_borrowed_tristate") {
        throw "V0006 to V0005 downgrade did not complete"
    }
    $downgradedActive = Get-Scalar "SELECT active_revision_id FROM materialization_state WHERE id=1"
    $downgradedImportRun = Get-Scalar "SELECT active_import_run_id FROM materialization_state WHERE id=1"
    $downgradedMaterialization = Get-Scalar "SELECT materialization_sha256 FROM materialization_state WHERE id=1"
    $remainingArenaTables = [int](Get-Scalar "SELECT COUNT(*) FROM (VALUES ('arena_defenses'), ('arena_defense_members'), ('arena_counters'), ('arena_counter_members'), ('arena_counter_evidence'), ('arena_counter_claims')) AS arena_table(name) WHERE to_regclass('public.' || name) IS NOT NULL")
    if (
        $downgradedActive -ne $a4Revision -or
        $downgradedImportRun -ne $a4ImportRunId -or
        $downgradedMaterialization -ne $a4InstanceMaterialization -or
        $remainingArenaTables -ne 0
    ) {
        throw "A4 identity or schema boundary changed during V0006 downgrade"
    }
    Write-Host "A5_A4_ROLLBACK_READY_OK alembic=$downgradedRevision arena_tables=$remainingArenaTables"

    if ($LeaveAtA4) {
        # This is the sole successful permanent-rollback boundary. The exact
        # A4 data and V0005 schema were verified, but old services remain
        # quiesced until the operator deploys the rp-a4-1 images.
        $leaveAtA4Completed = $true
        $needsA5Restore = $false
    }
    else {
        Restore-A5
        $needsA5Restore = $false
    }
}
catch {
    $primaryError = $_
}
finally {
    if ($needsA5Restore) {
        try {
            Restore-A5
            $needsA5Restore = $false
        }
        catch {
            if ($null -eq $primaryError) {
                $primaryError = $_
            }
            else {
                $primaryError = [System.Exception]::new(
                    "$($primaryError.Exception.Message); A5 restore also failed: $($_.Exception.Message)"
                )
            }
        }
    }
    if ($servicesStopped -and $leaveAtA4Completed) {
        Write-Host "A4_SERVICES_QUIESCED_OK deploy_tag=rp-a4-1"
    }
    elseif ($servicesStopped -and -not $needsA5Restore) {
        try {
            Assert-A5DatabaseState `
                -ExpectedImportRunId $originA5ImportRunId `
                -ExpectedMaterializationSha256 $originA5Materialization
            Invoke-Compose up --detach --no-build --wait --wait-timeout 60 scheduler api web
            $actualApiPort = Get-ActualApiPort
            $ready = Invoke-RestMethod `
                -Uri "http://127.0.0.1:${actualApiPort}/health/ready" `
                -TimeoutSec 5
            if (
                $ready.status -ne "ok" -or
                $ready.checks.database -ne "ok" -or
                $ready.checks.fixture -ne "imported"
            ) {
                throw "A5 API readiness contract failed after service restart"
            }
            Write-Host "A5_SERVICES_READY_OK api_port=$actualApiPort database=ok fixture=imported"
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
                    "$($primaryError.Exception.Message); A5 service readiness also failed: $($restartError.Exception.Message)"
                )
            }
        }
    }
    elseif ($servicesStopped) {
        $quiescedMessage = "A5 restoration was not verified; services were left quiesced for manual recovery"
        Write-Warning "SERVICES_LEFT_QUIESCED: $quiescedMessage"
        if ($null -eq $primaryError) {
            $primaryError = [System.Exception]::new($quiescedMessage)
        }
    }
}

if ($null -ne $primaryError) {
    throw $primaryError
}
if ($LeaveAtA4) {
    Write-Host "A5_A4_ROLLBACK_COMPLETE_OK alembic=v0005_borrowed_tristate services=quiesced"
}
else {
    Write-Host "A5_A4_ROLLBACK_DRILL_OK"
}
