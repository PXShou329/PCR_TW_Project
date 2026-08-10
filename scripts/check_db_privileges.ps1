[CmdletBinding()]
param(
    [string]$EnvFile,
    [string]$ProjectName,
    [string]$PostgresUser = "pcr_owner",
    [string]$Database = "pcr_tw"
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
if ($Database -notmatch '^[a-zA-Z][a-zA-Z0-9_]{0,62}$') {
    throw "Database contains unsupported characters"
}

$compose = @("compose")
if ($ProjectName) {
    if ($ProjectName -notmatch '^[a-z0-9][a-z0-9_-]{0,62}$') {
        throw "ProjectName contains unsupported characters"
    }
    $compose += @("--project-name", $ProjectName)
}
$compose += @("--env-file", $EnvFile, "-f", $composeFile)
$servingTables = @(
    "import_runs", "characters", "claims", "evidence", "stages", "teams",
    "team_members", "stage_evidence", "stage_claims", "team_evidence", "claim_evidence",
    "operation_timelines", "timeline_steps", "core_revisions", "core_files",
    "core_csv_rows", "materialization_state", "revision_activations",
    "arena_defenses", "arena_defense_members", "arena_counters", "arena_counter_members",
    "arena_counter_evidence", "arena_counter_claims", "gacha_timeline_events",
    "gacha_timeline_evidence", "gacha_timeline_claims", "gacha_community_sources",
    "gacha_timeline_community_sources", "arena_source_records", "parena_cases",
    "parena_case_matchups", "parena_case_sources", "parena_case_evidence",
    "parena_case_claims"
)
$appendOnlyTables = @("revision_activations")
$controlTables = @("scheduler_leases", "scheduler_runs")
$tablePrivileges = @(
    "SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"
)
$serviceRoles = @("pcr_api", "pcr_importer", "pcr_scheduler")
$expectedMatrixChecks = (
    ($servingTables.Count + $controlTables.Count) *
    $tablePrivileges.Count *
    $serviceRoles.Count
)
$matrixChecks = 0
$actualDenials = 0
$allowedSmokes = 0

function Get-Scalar {
    param([string]$Sql)
    $value = & docker @compose exec -T db psql `
        --username=$PostgresUser `
        --dbname=$Database `
        --tuples-only `
        --no-align `
        --set=ON_ERROR_STOP=1 `
        --command=$Sql
    if ($LASTEXITCODE -ne 0) {
        throw "Privilege query failed"
    }
    return ($value | Out-String).Trim()
}

function Assert-Privilege {
    param(
        [string]$Role,
        [string]$Table,
        [string]$Privilege,
        [bool]$Expected
    )
    $actual = Get-Scalar -Sql "SELECT has_table_privilege('$Role', 'public.$Table', '$Privilege')"
    $expectedText = if ($Expected) { "t" } else { "f" }
    if ($actual -ne $expectedText) {
        throw "Privilege mismatch role=$Role table=$Table privilege=$Privilege expected=$expectedText actual=$actual"
    }
    $script:matrixChecks += 1
}

function Assert-SqlDenied {
    param(
        [string]$Name,
        [string]$Sql,
        [string]$ExpectedPattern
    )
    $output = & docker @compose exec -T db psql `
        --username=$PostgresUser `
        --dbname=$Database `
        --set=ON_ERROR_STOP=1 `
        --command=$Sql 2>&1
    if ($LASTEXITCODE -eq 0) {
        throw "Expected SQL denial did not occur: $Name"
    }
    $outputText = ($output | Out-String)
    if ($ExpectedPattern -and $outputText -notmatch [regex]::Escape($ExpectedPattern)) {
        throw "SQL denial used the wrong guard: $Name expected=$ExpectedPattern output=$outputText"
    }
    $script:actualDenials += 1
    Write-Host "DENY_OK $Name"
}

foreach ($role in $serviceRoles) {
    $safeRole = Get-Scalar -Sql "SELECT rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolinherit AND NOT rolreplication AND NOT rolbypassrls FROM pg_roles WHERE rolname='$role'"
    if ($safeRole -ne "t") {
        throw "Unsafe or missing service role: $role"
    }
    $membershipCount = Get-Scalar -Sql "SELECT COUNT(*) FROM pg_auth_members membership JOIN pg_roles member ON member.oid=membership.member WHERE member.rolname='$role'"
    if ($membershipCount -ne "0") {
        throw "Service role has an unexpected role membership: $role count=$membershipCount"
    }
    $schemaUsage = Get-Scalar -Sql "SELECT has_schema_privilege('$role', 'public', 'USAGE')"
    $schemaCreate = Get-Scalar -Sql "SELECT has_schema_privilege('$role', 'public', 'CREATE')"
    if ($schemaUsage -ne "t" -or $schemaCreate -ne "f") {
        throw "Schema privilege mismatch for $role (USAGE=$schemaUsage CREATE=$schemaCreate)"
    }
}

foreach ($table in $servingTables) {
    foreach ($privilege in $tablePrivileges) {
        Assert-Privilege -Role "pcr_api" -Table $table -Privilege $privilege -Expected ($privilege -eq "SELECT")
        $importerExpected = if ($table -in $appendOnlyTables) {
            $privilege -in @("SELECT", "INSERT")
        } else {
            $privilege -in @("SELECT", "INSERT", "UPDATE", "DELETE")
        }
        Assert-Privilege -Role "pcr_importer" -Table $table -Privilege $privilege -Expected $importerExpected
        Assert-Privilege -Role "pcr_scheduler" -Table $table -Privilege $privilege -Expected $false
    }
}
foreach ($table in $controlTables) {
    foreach ($privilege in $tablePrivileges) {
        Assert-Privilege -Role "pcr_api" -Table $table -Privilege $privilege -Expected $false
        Assert-Privilege -Role "pcr_importer" -Table $table -Privilege $privilege -Expected $false
        Assert-Privilege -Role "pcr_scheduler" -Table $table -Privilege $privilege -Expected ($privilege -in @("SELECT", "INSERT", "UPDATE"))
    }
}

# Real statements in transactions prevent a false PASS caused by metadata-only
# checks. WHERE FALSE and ROLLBACK guarantee that an accidentally allowed DML or
# DDL statement still leaves no data/schema change.
Assert-SqlDenied "api-serving-update" "BEGIN; SET LOCAL ROLE pcr_api; UPDATE stages SET notes=notes WHERE FALSE; ROLLBACK"
Assert-SqlDenied "api-arena-update" "BEGIN; SET LOCAL ROLE pcr_api; UPDATE arena_counters SET notes=notes WHERE FALSE; ROLLBACK"
Assert-SqlDenied "api-gacha-update" "BEGIN; SET LOCAL ROLE pcr_api; UPDATE gacha_timeline_events SET status=status WHERE FALSE; ROLLBACK"
Assert-SqlDenied "api-gacha-truncate" "BEGIN; SET LOCAL ROLE pcr_api; TRUNCATE TABLE gacha_timeline_claims; ROLLBACK" -ExpectedPattern "permission denied for table gacha_timeline_claims"
Assert-SqlDenied "api-parena-update" "BEGIN; SET LOCAL ROLE pcr_api; UPDATE parena_cases SET notes=notes WHERE FALSE; ROLLBACK"
Assert-SqlDenied "api-parena-truncate" "BEGIN; SET LOCAL ROLE pcr_api; TRUNCATE TABLE parena_case_claims; ROLLBACK" -ExpectedPattern "permission denied for table parena_case_claims"
Assert-SqlDenied "api-core-update" "BEGIN; SET LOCAL ROLE pcr_api; UPDATE core_revisions SET status=status WHERE FALSE; ROLLBACK"
Assert-SqlDenied "api-scheduler-update" "BEGIN; SET LOCAL ROLE pcr_api; UPDATE scheduler_runs SET status=status WHERE FALSE; ROLLBACK"
Assert-SqlDenied "importer-scheduler-update" "BEGIN; SET LOCAL ROLE pcr_importer; UPDATE scheduler_runs SET status=status WHERE FALSE; ROLLBACK"
Assert-SqlDenied "importer-activation-update" "BEGIN; SET LOCAL ROLE pcr_importer; UPDATE revision_activations SET reason=reason WHERE FALSE; ROLLBACK"
Assert-SqlDenied "importer-activation-delete" "BEGIN; SET LOCAL ROLE pcr_importer; DELETE FROM revision_activations WHERE FALSE; ROLLBACK"
Assert-SqlDenied "scheduler-serving-update" "BEGIN; SET LOCAL ROLE pcr_scheduler; UPDATE stages SET notes=notes WHERE FALSE; ROLLBACK"
Assert-SqlDenied "scheduler-arena-update" "BEGIN; SET LOCAL ROLE pcr_scheduler; UPDATE arena_counters SET notes=notes WHERE FALSE; ROLLBACK"
Assert-SqlDenied "scheduler-gacha-update" "BEGIN; SET LOCAL ROLE pcr_scheduler; UPDATE gacha_timeline_events SET status=status WHERE FALSE; ROLLBACK"
Assert-SqlDenied "scheduler-parena-update" "BEGIN; SET LOCAL ROLE pcr_scheduler; UPDATE parena_cases SET notes=notes WHERE FALSE; ROLLBACK"
Assert-SqlDenied "scheduler-core-update" "BEGIN; SET LOCAL ROLE pcr_scheduler; UPDATE core_files SET size_bytes=size_bytes WHERE FALSE; ROLLBACK"
Assert-SqlDenied "scheduler-control-delete" "BEGIN; SET LOCAL ROLE pcr_scheduler; DELETE FROM scheduler_runs WHERE FALSE; ROLLBACK"
Assert-SqlDenied "api-schema-create" "BEGIN; SET LOCAL ROLE pcr_api; CREATE TABLE pcr_b0_forbidden_probe(id integer); ROLLBACK"
Assert-SqlDenied "activation-append-only-trigger" "BEGIN; UPDATE revision_activations SET reason=reason WHERE FALSE; ROLLBACK"
Assert-SqlDenied "materialization-singleton-delete-trigger" "BEGIN; DELETE FROM materialization_state WHERE FALSE; ROLLBACK"
Assert-SqlDenied "terminal-revision-immutable" "BEGIN; UPDATE core_revisions SET project_version=project_version WHERE revision_id=(SELECT active_revision_id FROM materialization_state WHERE id=1); ROLLBACK"
Assert-SqlDenied "terminal-core-file-immutable" "BEGIN; UPDATE core_files SET size_bytes=size_bytes WHERE revision_id=(SELECT active_revision_id FROM materialization_state WHERE id=1) AND relative_path='README.md'; ROLLBACK"
Assert-SqlDenied "terminal-core-row-immutable" "BEGIN; UPDATE core_csv_rows SET row_sha256=row_sha256 WHERE revision_id=(SELECT active_revision_id FROM materialization_state WHERE id=1) AND relative_path='92_EVIDENCE_LEDGER.csv' AND ordinal=1; ROLLBACK"
Assert-SqlDenied "terminal-import-run-immutable" "BEGIN; UPDATE import_runs SET canonical_source=canonical_source WHERE id=(SELECT active_import_run_id FROM materialization_state WHERE id=1); ROLLBACK" -ExpectedPattern "terminal import run"
Assert-SqlDenied "materialization-epoch-rewind" "BEGIN; UPDATE materialization_state SET epoch=epoch WHERE id=1; ROLLBACK" -ExpectedPattern "materialization_state epoch must strictly increase"
Assert-SqlDenied "active-revision-run-pair-fk" "BEGIN; INSERT INTO import_runs (id,fixture_sha256,canonical_source,research_core_version,application_version,imported_at,status,manifest,row_counts) VALUES ('00000000-0000-4000-8000-000000000002',repeat('0',64),'probe','probe','probe',CURRENT_TIMESTAMP,'RUNNING','{}'::jsonb,'{}'::jsonb); UPDATE materialization_state SET active_import_run_id='00000000-0000-4000-8000-000000000002', epoch=epoch+1 WHERE id=1; ROLLBACK" -ExpectedPattern "fk_materialization_state_active_revision_run"

foreach ($allowedSql in @(
    "BEGIN; SET LOCAL ROLE pcr_api; SELECT 1 FROM stages LIMIT 0; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_api; SELECT 1 FROM arena_counters LIMIT 0; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_api; SELECT 1 FROM gacha_timeline_events LIMIT 0; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_api; SELECT 1 FROM parena_cases LIMIT 0; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_api; SELECT 1 FROM core_revisions LIMIT 0; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_importer; UPDATE stages SET notes=notes WHERE FALSE; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_importer; UPDATE arena_counters SET notes=notes WHERE FALSE; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_importer; UPDATE gacha_timeline_events SET status=status WHERE FALSE; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_importer; UPDATE parena_cases SET notes=notes WHERE FALSE; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_importer; UPDATE core_files SET size_bytes=size_bytes WHERE FALSE; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_importer; INSERT INTO revision_activations (activation_id,sequence_no,to_revision_id,kind,reason,actor,epoch) SELECT '00000000-0000-0000-0000-000000000000',1,repeat('0',64),'IMPORT','probe','probe',0 WHERE FALSE; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_scheduler; UPDATE scheduler_runs SET status=status WHERE FALSE; ROLLBACK"
)) {
    $null = Get-Scalar -Sql $allowedSql
    $allowedSmokes += 1
}

if (
    $expectedMatrixChecks -ne 777 -or
    $matrixChecks -ne $expectedMatrixChecks -or
    $actualDenials -ne 26 -or
    $allowedSmokes -ne 12
) {
    throw "Privilege probe coverage drifted (matrix=$matrixChecks denials=$actualDenials allowed=$allowedSmokes)"
}
Write-Host "DB_PRIVILEGES_OK matrix_checks=$matrixChecks actual_denials=$actualDenials allowed_smokes=$allowedSmokes"
