# Database

PostgreSQL is a read mirror in B0. The research-core files remain the only
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

B0 accepts an exact-fingerprint replay as an idempotent no-op. If the source
fixture fingerprint changes, it stops and requires rebuilding the disposable
read mirror. Because 26/27 are now part of the full fingerprint and serving
manifest, an existing V0001/B0 mirror must be rebuilt after applying V0002;
the importer intentionally refuses a partial in-place backfill.
