# Scheduler walking skeleton

This B0 service is deliberately inert by default:

- `SCHEDULER_ENABLED=false`
- `SHADOW_MODE=true`
- `AUTO_PUBLISH=false`
- no source adapter, network fetch, or canonical-data writer exists

When explicitly enabled, it exercises the PostgreSQL lease and idempotency
contracts and records a `SHADOW_NOOP` run. Alembic in `apps/api` remains the
only schema migration owner.

Health endpoints are `GET /live`, `GET /ready`, and `GET /health` on port 8081.
The health payload never returns `DATABASE_URL` and explicitly reports
`canonical_write_capable=false`.
