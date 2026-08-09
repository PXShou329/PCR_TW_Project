# RP-A5 local/private deployment

`compose.yml` is a production-shaped local/private staging stack, not a public
production manifest. PostgreSQL is pinned to `18.4-bookworm`; every published
port binds only to `127.0.0.1`, and the database lives on an internal Docker
network. Alembic is the sole schema migration owner.

The startup dependency chain is:

```text
db healthy -> migration(owner) -> role-provision -> importer(DML) -> api(SELECT) -> web
                                          `-------> scheduler(control tables only)
```

Run it from the repository root after creating a private `.env` from
`.env.example`:

```powershell
docker compose --env-file .env -f infra/compose.yml up --build --wait
```

API-family runtime and profile-only verification services share one
`${PCR_API_IMAGE}` so a smoke cannot silently run stale code. Do not set
`AUTO_PUBLISH=true` or `SHADOW_MODE=false`; the scheduler rejects both in RP-A5.
See `docs/operations/B1_RUNBOOK.md` for the still-valid full-core round-trip,
verification, backup restore and atomic rollback procedure inherited from the B1
foundation. The rollback chain has two independent fail-closed boundaries:
V0005 refuses V0004 while any honest `is_borrowed IS NULL` remains, and V0004
refuses V0003 while any honest `UNKNOWN` operation-mode row remains.
The current image carries the immutable RP-A5 manifest plus RP-A2／RP-A3／RP-A4
rollback checkpoints. For the historical RP-A4 to RP-A3 deployment order and
roll-forward procedure, follow `docs/operations/A4_ROLLBACK_RUNBOOK.md`.
