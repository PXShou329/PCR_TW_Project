# Scheduler lease and idempotency contract

## B0 guarantees

The scheduler process is disabled by default and rejects either
`SHADOW_MODE=false` or `AUTO_PUBLISH=true`. Its runnable job performs zero
network requests and zero canonical writes; it only validates scheduler-control
state in PostgreSQL.

The health payload exposes `canonical_write_capable=false`. It never exposes a
database URL or credentials.

The runtime login is `pcr_scheduler`, not the migration owner. PostgreSQL grants
it only `SELECT`, `INSERT`, and `UPDATE` on `scheduler_leases` and
`scheduler_runs`; it has no serving-table DML, DELETE, schema CREATE, or DDL
authority. `scripts/check_db_privileges.ps1` verifies both the privilege matrix
and real denied statements.

## Migration ownership

Alembic under `database/` is the sole migration owner. The scheduler consumes,
but never creates or alters, these tables:

```text
scheduler_leases
  name PRIMARY KEY
  owner_id
  acquired_at
  expires_at
  updated_at

scheduler_runs
  id PRIMARY KEY
  idempotency_key UNIQUE
  UNIQUE(job_name, scheduled_for)
  job_name
  scheduled_for
  source_fingerprint
  status
  shadow_mode
  owner_id
  started_at
  finished_at
  detail JSONB
```

## Lease algorithm

One atomic `INSERT ... ON CONFLICT ... DO UPDATE ... WHERE` statement acquires or
renews a lease. Another owner may take it only when database time says the old
lease has expired. Database time avoids cross-container clock comparisons.

The production owner ID combines host identity with a random UUID. The lease
TTL must be longer than the polling interval; configuration validation enforces
that invariant.

## Idempotency algorithm

The run key is SHA-256 of:

```text
job_name + UTC schedule bucket + source_fingerprint
```

Run insertion uses `ON CONFLICT DO NOTHING`. Both the run key and
`(job_name, scheduled_for)` are unique, so retry, restart, and fingerprint drift
inside one schedule bucket cannot create a second execution. B0 persists
`STARTED -> SKIPPED` with `scheduler_result=SHADOW_NOOP`; the health state keeps
the more descriptive `SHADOW_NOOP` result.

Tests cover deterministic bucketing, same-bucket duplicate suppression,
unexpired lease exclusion, safe defaults, unsafe configuration rejection, and
liveness/readiness behavior. The Compose `scheduler-smoke` profile additionally
exercises the real PostgreSQL constraints.

## Failure semantics

- Database unavailable: the worker becomes unready/degraded; API and Web stay
  independent.
- Lease held: this instance reports standby and does no work.
- Duplicate run: it reports `DUPLICATE_SKIPPED` and does no work.
- Process death: the lease becomes reclaimable after TTL.
- Invalid safety flags: the process exits before opening a worker loop.

## Required before live source adapters

B0's lease is sufficient only because there are no external or canonical side
effects. Before any later Track B source adapter or publisher is enabled, add:

1. a monotonically increasing fencing token checked by every side-effect path;
2. bounded retries with jitter and a dead-letter/review state;
3. source allowlisting, SSRF controls, timeouts, body limits, and robots/policy
   review;
4. content hashing and revision provenance;
5. an outbox or equivalent atomic publish boundary;
6. per-source rate limits and kill switches;
7. metrics/alerts for stale heartbeat, lease contention, failure rate, and
   review backlog;
8. a 14-day Shadow Mode observation window before any canonical cutover.

Until all eight are implemented and reviewed, scheduler output must remain a
candidate/review artifact and never modify the research-core SSOT.
