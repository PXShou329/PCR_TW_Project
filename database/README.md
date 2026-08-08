# Database

PostgreSQL is an immutable multi-revision read mirror in B1. The research-core files remain the only
writable canonical source.

Apply the migration chain with:

```powershell
$env:PCR_DATABASE_URL = "postgresql+psycopg://<owner>:<password>@<host>:5432/<database>"
alembic -c database/alembic.ini upgrade head
```

There is no built-in username/password fallback. Compose supplies the private
owner URL to the one-shot migration container; direct runs must set it
explicitly and must not commit the value.

`V0001` is additive. It creates the read-model tables plus the scheduler lease
and run-control tables. The importer writes one fixture closure in one database
transaction and never writes back to the research core.

`V0002` additively creates `operation_timelines` and `timeline_steps`.
`source_axis_id` is the timeline-row identity; gap rows retain a null database
`timeline_id`, and structured steps remain attached to exactly one source
timeline. Downgrading from V0002 drops only these two serving tables (steps
first), so use it only before V0002 data is relied upon or after a verified
backup.

`V0003` additively creates the lossless core revision/file/CSV-row mirror, active
materialization singleton and append-only activation audit. Exact active replay is a
zero-write no-op; a different reviewed manifest becomes a new immutable revision and
is atomically activated after artifact and typed parity pass. Existing terminal history
is never updated in place.

Downgrading V0003 is not equivalent to switching a Git tag. Its transactional
reconciliation projects the B1 active run into the V0002 legacy `latest_import`
ordering before removing B1 tables. Follow `docs/operations/B1_RUNBOOK.md`; roll-forward
after downgrade requires a verified B1 backup restore or a deliberately rebuilt
disposable mirror.
