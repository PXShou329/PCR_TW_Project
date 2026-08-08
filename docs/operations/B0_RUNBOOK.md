# B0 local/private staging runbook

## Safety boundary

B0 is a deployable walking skeleton, not a public production release.

- The R3i files under `research_core/pcr_tw_project` remain the only writable
  canonical source. PostgreSQL is a disposable read mirror.
- Scheduler defaults are `SCHEDULER_ENABLED=false`, `SHADOW_MODE=true`, and
  `AUTO_PUBLISH=false`.
- The scheduler has no source adapter, network fetcher, or canonical publisher.
- No administrative write endpoint is exposed.
- All host ports bind to `127.0.0.1`; PostgreSQL also uses an internal network.
- Database credentials are separated: migration owner, serving-table DML
  importer, read-only API, and scheduler-control-only scheduler.
- `.env` and `.runtime/` are ignored. Never commit credentials or backup data.

## Preconditions

1. Docker Engine with Compose v2, Python 3.13.14, Node 24.18 LTS, and npm 11.
2. A private `.env` copied from `.env.example`; replace all four password
   placeholders with distinct URL-safe values of at least 16 characters.
3. Ports 3000, 8000, and 8081 available on loopback. PostgreSQL has no host
   port and is reachable only on the internal Compose network.

Validate the immutable data baseline before starting services:

```powershell
python scripts/check_research_baseline.py
```

The final line must be:

```text
RESEARCH_BASELINE_OK | files=46 | mutation_scenarios=55 | manifest_sha256=80e6be16fbfbbef1c676def920348aa006d6608a0900f2e62ba4d5cac2d62bcb
```

This is the current RP-I0 byte lock: `scripts/research_core_rp_i0_manifest.sha256`
contains every expected relative path and file SHA-256, and the verifier also
pins the manifest's canonical-LF SHA-256. File-count or validator-summary
agreement alone cannot satisfy the baseline check.

The historical B0 tag retains RP-B0-0 (`mutation_scenarios=54`, manifest
`c9aa323626b453afb7f694dd526f90121ce0bf59eda90b3a30a9d955157a773a`)
and `scripts/research_core_rp_b0_0_manifest.sha256`; do not compare that
historical output to the current branch verifier.

## Deploy

Render configuration first. This detects missing variables and Compose errors
without creating containers:

```powershell
docker compose --env-file .env -f infra/compose.yml config --quiet
```

Build and wait for health:

```powershell
docker compose --env-file .env -f infra/compose.yml up --build --wait
docker compose --env-file .env -f infra/compose.yml ps
```

Expected dependency flow:

```text
db healthy -> migration(owner) exit 0 -> role-provision exit 0
            -> importer(DML) exit 0 -> api(SELECT) healthy -> web healthy
                              `-----> scheduler(control-only) healthy (disabled)
```

Verify endpoints:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-RestMethod http://127.0.0.1:8081/health
Invoke-RestMethod http://127.0.0.1:3000/api/health
```

The scheduler response must include:

```json
{
  "status": "disabled",
  "ready": true,
  "enabled": false,
  "shadow_mode": true,
  "canonical_write_capable": false
}
```

Verify the full PostgreSQL privilege matrix plus real denied statements:

```powershell
pwsh -File scripts/check_db_privileges.ps1 -EnvFile .env
```

This must end with `DB_PRIVILEGES_OK`. Metadata checks alone are insufficient;
the script also executes transaction-wrapped UPDATE/DELETE/DDL probes that must
be denied, while permitted no-op SELECT/UPDATE probes must succeed.

Browser Evidence requests stay same-origin at
`/api/v1/evidence/{evidence_id}`. The Web server forwards only validated GET
requests to the fixed, server-only `API_BASE_URL=http://api:8000`; no public
upstream URL is embedded in browser JavaScript.

## Data checks

The importer is deterministic and runs after the one-shot migration. Re-run it
to confirm idempotency:

```powershell
docker compose --env-file .env -f infra/compose.yml run --rm importer
docker compose --env-file .env -f infra/compose.yml run --rm importer
```

Both runs must report the same fixture hash and row counts. API metadata must
keep application version `3.0.0-b0` distinct from research-core version `1.5`.

Exercise the scheduler database contract exactly once without enabling the
long-running scheduler or any publisher:

```powershell
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm scheduler-smoke
```

The result must end with `SCHEDULER_SHADOW_SMOKE_OK`, followed by a duplicate
skip for the same bucket. This writes only scheduler control/audit rows.

For B0, Fire Deep Zone 8-10 imports as one complete closure: one stage, three
distinct verified teams, their fifteen team-member slots, required character
rows, claims, and evidence. A one-team partial import is not acceptable.
Selected Evidence whose declared Claim does not exist rejects the entire import;
it is not downgraded into a nullable public relation. Each successful ImportRun
also stores a deterministic materialization manifest containing every serving
table's exact primary-key set and complete normalized-row hashes. API readiness
recomputes that manifest, so a deleted relation row or normalized/source-payload
parity drift returns 503 even when top-level row counts are unchanged. The same
check guards every `/api/v1/*` serving route; liveness stays available for
diagnosis, but drifted strategy data is never returned with HTTP 200.

## Structured logs and first-response triage

Container stdout/stderr is the only B0 log sink. Scheduler messages are JSON
objects with `timestamp`, `level`, `logger`, `event`, and safe identifiers. URLs
with credentials are never logged.

```powershell
docker compose --env-file .env -f infra/compose.yml logs --since 10m --no-color api scheduler
docker compose --env-file .env -f infra/compose.yml ps
```

Triage order:

1. `db` unhealthy: inspect `pg_isready`, disk space, and the DB log.
2. `migration` non-zero: stop; do not start API against a partial schema.
3. `importer` non-zero: stop; the transaction must roll back completely.
4. API not ready: confirm Alembic revision and read-mirror row counts.
5. Scheduler degraded: keep it disabled; API/Web remain independent.
6. Web unhealthy: check server-side API URL is `http://api:8000` and verify the
   same-origin Evidence proxy separately from the upstream API.

Do not “fix” a failing import by disabling FK/check constraints or by editing
derived counts. Correct the source mapping and add a regression test.

## Backup and empty-restore drill

Run after the stack is healthy:

```powershell
pwsh -File scripts/backup_restore_smoke.ps1 -EnvFile .env
```

The script creates a unique disposable database, restores a custom-format dump,
compares every public table row count and the Alembic revision, reapplies the
least-privilege grants, and launches disposable API and Web containers against
the restored database. It verifies API readiness, baseline counts, stage and
Evidence reads, Web health, SSR content, and the same-origin Evidence proxy.
Only then does it remove both containers, the restore database, and the dump.
A valid run includes `RESTORED_API_READINESS_OK`,
`RESTORED_WEB_EVIDENCE_OK`, and `BACKUP_RESTORE_OK`.

Use `-KeepBackup` only when an operator intentionally needs the local artifact.
Backups contain platform data and must remain under ignored `.runtime/backups`.

## Rollback

Rollback triggers include a research-core baseline drift, a new
`ARTIFACT_READY` failure, importer parity/FK failure, scheduler canonical write
attempt, migration failure, secret exposure, or failed restore drill.

1. Stop the inert scheduler first:

   ```powershell
   docker compose --env-file .env -f infra/compose.yml stop scheduler
   ```

2. Capture non-secret logs and `docker compose ps` for diagnosis.
3. Stop application services without deleting the DB volume:

   ```powershell
   docker compose --env-file .env -f infra/compose.yml stop web api
   ```

4. Return code/images to the preceding `RP-B0-*` checkpoint.
5. Because PostgreSQL is only a read mirror, rebuild it from the unchanged R3i
   fixture after the cause is corrected. Do not downgrade or write back into
   research-core files.

Deleting the Docker volume is intentionally not part of this runbook. If a
clean mirror rebuild is required, an operator must separately approve that
destructive action after confirming the exact Compose project and volume.

## Promotion gate

B0 may be tagged only after baseline, Python, Web, E2E, Compose health,
idempotent importer, and backup/restore checks all pass. It must still be named
`local/private staging`; it does not satisfy application, automation, or
production Gates D-G by itself.
