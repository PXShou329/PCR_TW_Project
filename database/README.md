# Database

PostgreSQL is a read mirror in B0. The research-core files remain the only
writable canonical source.

Apply the only migration chain with:

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

B0 accepts an exact-fingerprint replay as an idempotent no-op. If the source
fixture fingerprint changes, it stops and requires rebuilding the disposable
read mirror; revision-aware incremental synchronization belongs to B1.
