# Database

PostgreSQL is an immutable multi-revision read mirror. The research-core files remain the only
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

`V0004` extends the operation-mode contract with `UNKNOWN`, preserving an honest
source gap instead of inventing `AUTO`, `SEMI_AUTO`, or `MANUAL`. A downgrade to
V0003 is allowed only when no persisted operation timeline uses `UNKNOWN`.

If an `UNKNOWN` row exists, the downgrade refuses the lossy operation
transactionally: the database remains at V0004 and the row is retained intact.
Never coerce the value merely to make rollback succeed. Before a real downgrade,
either restore a verified pre-V0004/B1 backup or resolve every `UNKNOWN` from
admissible evidence, then repeat validation and the backup/restore smoke test.

`V0005` makes `team_members.is_borrowed` tri-state: `true` and `false` are used
only when the source establishes the fact, while `NULL` preserves
`UNKNOWN`/`SOURCE_CONFLICT`. A downgrade to V0004 applies `SET NOT NULL` and is
therefore allowed only when no honest `NULL` remains. PostgreSQL rejects the
downgrade transaction without updating or deleting rows, so the database stays
at V0005. Never turn an unknown into `false` merely to cross the migration
boundary; restore a verified pre-V0005 backup or resolve the fact from
admissible evidence and re-run the full validation and restore drill.

`V0006` additively creates normalized Battle Arena defenses, counters, their
ordered five-slot members, and counter-to-Evidence/Claim relations. Defense and
counter identities retain an order-insensitive five-unit signature while the
member tables preserve source display order. A single observed win may record
`sample_size=1`, `wins=1`, and `losses=0`, but its empirical win-rate field must
remain `NULL`; the database rejects a percentage inferred from a one-match
sample.
Arena claim confidence is limited to `B/C/D/E`: `SINGLE_REPORT` is exactly
`D`, while `VERIFIED` accepts `B/C/D` only and also requires
`reproducibility=CONFIRMED`. Arena reproducibility deliberately excludes the
Timeline-only `TW_REPRODUCED` vocabulary.

Materialization manifest version 3 hashes all six Arena tables. Previously
finalized rp-a4 runs retain their version-2 manifest and can still be replayed:
the materializer projects the exact legacy table set only when every Arena
table is empty. Any Arena row outside that legacy hash forces current-closure
drift instead of being ignored. For the same reason, the V0006 downgrade
transaction refuses to drop non-empty Arena tables; reactivate and verify the
legacy closure first, then downgrade.
