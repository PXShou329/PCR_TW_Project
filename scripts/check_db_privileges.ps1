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
    "operation_timelines", "timeline_steps"
)
$controlTables = @("scheduler_leases", "scheduler_runs")
$matrixChecks = 0

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
    param([string]$Name, [string]$Sql)
    $output = & docker @compose exec -T db psql `
        --username=$PostgresUser `
        --dbname=$Database `
        --set=ON_ERROR_STOP=1 `
        --command=$Sql 2>&1
    if ($LASTEXITCODE -eq 0) {
        throw "Expected SQL denial did not occur: $Name"
    }
    Write-Host "DENY_OK $Name"
}

foreach ($role in @("pcr_api", "pcr_importer", "pcr_scheduler")) {
    $safeRole = Get-Scalar -Sql "SELECT rolcanlogin AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication FROM pg_roles WHERE rolname='$role'"
    if ($safeRole -ne "t") {
        throw "Unsafe or missing service role: $role"
    }
    $schemaUsage = Get-Scalar -Sql "SELECT has_schema_privilege('$role', 'public', 'USAGE')"
    $schemaCreate = Get-Scalar -Sql "SELECT has_schema_privilege('$role', 'public', 'CREATE')"
    if ($schemaUsage -ne "t" -or $schemaCreate -ne "f") {
        throw "Schema privilege mismatch for $role (USAGE=$schemaUsage CREATE=$schemaCreate)"
    }
}

foreach ($table in $servingTables) {
    foreach ($privilege in @("SELECT", "INSERT", "UPDATE", "DELETE")) {
        Assert-Privilege -Role "pcr_api" -Table $table -Privilege $privilege -Expected ($privilege -eq "SELECT")
        Assert-Privilege -Role "pcr_importer" -Table $table -Privilege $privilege -Expected $true
        Assert-Privilege -Role "pcr_scheduler" -Table $table -Privilege $privilege -Expected $false
    }
}
foreach ($table in $controlTables) {
    foreach ($privilege in @("SELECT", "INSERT", "UPDATE", "DELETE")) {
        Assert-Privilege -Role "pcr_api" -Table $table -Privilege $privilege -Expected $false
        Assert-Privilege -Role "pcr_importer" -Table $table -Privilege $privilege -Expected $false
        Assert-Privilege -Role "pcr_scheduler" -Table $table -Privilege $privilege -Expected ($privilege -in @("SELECT", "INSERT", "UPDATE"))
    }
}

# Real statements in transactions prevent a false PASS caused by metadata-only
# checks. WHERE FALSE and ROLLBACK guarantee that an accidentally allowed DML or
# DDL statement still leaves no data/schema change.
Assert-SqlDenied "api-serving-update" "BEGIN; SET LOCAL ROLE pcr_api; UPDATE stages SET notes=notes WHERE FALSE; ROLLBACK"
Assert-SqlDenied "api-scheduler-update" "BEGIN; SET LOCAL ROLE pcr_api; UPDATE scheduler_runs SET status=status WHERE FALSE; ROLLBACK"
Assert-SqlDenied "importer-scheduler-update" "BEGIN; SET LOCAL ROLE pcr_importer; UPDATE scheduler_runs SET status=status WHERE FALSE; ROLLBACK"
Assert-SqlDenied "scheduler-serving-update" "BEGIN; SET LOCAL ROLE pcr_scheduler; UPDATE stages SET notes=notes WHERE FALSE; ROLLBACK"
Assert-SqlDenied "scheduler-control-delete" "BEGIN; SET LOCAL ROLE pcr_scheduler; DELETE FROM scheduler_runs WHERE FALSE; ROLLBACK"
Assert-SqlDenied "api-schema-create" "BEGIN; SET LOCAL ROLE pcr_api; CREATE TABLE pcr_b0_forbidden_probe(id integer); ROLLBACK"

foreach ($allowedSql in @(
    "BEGIN; SET LOCAL ROLE pcr_api; SELECT 1 FROM stages LIMIT 0; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_importer; UPDATE stages SET notes=notes WHERE FALSE; ROLLBACK",
    "BEGIN; SET LOCAL ROLE pcr_scheduler; UPDATE scheduler_runs SET status=status WHERE FALSE; ROLLBACK"
)) {
    $null = Get-Scalar -Sql $allowedSql
}

Write-Host "DB_PRIVILEGES_OK matrix_checks=$matrixChecks actual_denials=6 allowed_smokes=3"
