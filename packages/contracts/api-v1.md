# API v1 contract (B0)

All public strategy endpoints are read-only `GET` endpoints and return:

```json
{
  "data": {},
  "meta": {
    "api_version": "v1",
    "generated_at": "2026-08-08T00:00:00Z",
    "source": {
      "canonical_source": "research_core_file_ssot",
      "fixture_sha256": "<64 lowercase hex>",
      "import_run_id": "<uuid>",
      "imported_at": "2026-08-08T00:00:00Z",
      "research_core_version": "v1.5"
    },
    "warnings": []
  }
}
```

Endpoints:

- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/baseline`
- `GET /api/v1/stages`
- `GET /api/v1/stages/{guide_id}`
- `GET /api/v1/teams/{team_id}`
- `GET /api/v1/evidence/{evidence_id}`
- `GET /api/v1/claims/{claim_id}`
- `GET /api/v1/pvp/counters?defense_signature=...`

The PVP endpoint intentionally returns an empty `data` array and the warning
`NO_VERIFIED_COUNTER` until a formal registry case exists. A team with only a
source locator exposes `timeline.status=SOURCE_GAP`, `references`, and an empty
`steps` list; a locator is never represented as an operation step.

Unknown resources return `404` with:

```json
{"detail":{"code":"NOT_FOUND","resource":"team","id":"..."}}
```

Every `/api/v1/*` request first verifies the complete materialization manifest.
If any normalized row or relation link differs from the successful ImportRun,
the API returns `503` and does not serialize strategy data:

```json
{
  "detail": {
    "code": "FIXTURE_DRIFT",
    "resource": "import_run",
    "id": "<uuid>",
    "reason": "materialization_team_evidence_drift"
  }
}
```

The running FastAPI application publishes the executable OpenAPI contract at
`/openapi.json`.

Run `npm run check:contract` from the repository root after changing a response
schema or the TypeScript API client. The check generates OpenAPI from the
FastAPI app, compares the mapped domain property sets, required fields, and
nullability against `packages/api-client/src/types.ts`, and fails closed on
drift. Set `PCR_OPENAPI_PYTHON` only when the project Python interpreter cannot
be discovered automatically.

Browser access uses an explicit read-only CORS allowlist. B0 defaults to
`http://localhost:3000` and `http://127.0.0.1:3000`; deployments may replace it
with the comma-separated `PCR_CORS_ORIGINS` environment value. Wildcards,
credentialed requests, and non-GET preflights are rejected.
