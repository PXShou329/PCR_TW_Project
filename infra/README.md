# A3 local/private deployment

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
`AUTO_PUBLISH=true` or `SHADOW_MODE=false`; the scheduler rejects both in A3.
See `docs/operations/B1_RUNBOOK.md` for the still-valid full-core round-trip,
verification, backup restore and atomic rollback procedure inherited from the B1
foundation. V0004 additionally refuses a downgrade while any honest `UNKNOWN`
operation-mode row remains.
