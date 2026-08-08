# API v1 contract (A3 Fire maturity slice)

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
      "revision_id": "<64 lowercase hex>",
      "imported_at": "2026-08-08T00:00:00Z",
      "research_core_version": "v1.5",
      "raw_tree_sha256": "<64 lowercase hex>",
      "semantic_tree_sha256": "<64 lowercase hex>",
      "materialization_sha256": "<64 lowercase hex>"
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
- `GET /api/v1/teams/{team_id}/timelines`
- `GET /api/v1/evidence/{evidence_id}`
- `GET /api/v1/claims/{claim_id}`
- `GET /api/v1/pvp/counters?defense_signature=...`

The PVP endpoint intentionally returns an empty `data` array and the warning
`NO_VERIFIED_COUNTER` until a formal registry case exists.

`TeamDetail.timeline` and the dedicated timeline endpoint expose a
source-separated aggregate:

```json
{
  "status": "STRUCTURED|PARTIAL|SOURCE_GAP|MISSING",
  "structured_sources": 1,
  "registered_sources": 4,
  "sources": [],
  "references": [],
  "steps": []
}
```

Each `sources[]` item is exactly one `source_axis_id` and is either
`STRUCTURED` with only that source's ordered steps, or `SOURCE_GAP` with zero
steps and a non-null `gap_reason`. Sources and steps are never merged across
evidence. The top-level `steps` field is deprecated and permanently empty;
`references` is the unchanged legacy parser projection; after the canonical
`timeline_ref` normalization its `raw` and `source_id` values are source-axis
ids and its locator is `UNKNOWN`.

CSV sentinels that represent absent structure or numbers are normalized at the
serving boundary: gap `timeline_id`, gap clock/auto fields, unknown battle
duration, unknown step clocks, and unknown tolerance serialize as `null`.
Textual source statements such as `UNKNOWN` criticality and operation mode remain unchanged.
`time_state=NOT_STATED` requires null clocks; clients must not infer a standard
battle duration. Cross-server reproducibility such as `UNVERIFIED_ON_TW` is
passed through unchanged.

Unknown resources return `404` with:

```json
{"detail":{"code":"NOT_FOUND","resource":"team","id":"..."}}
```

Every `/api/v1/*` request first resolves the active revision pointer, verifies
the full-core file/CSV-row mirror, and verifies the complete typed serving
materialization. If any revision, artifact, normalized row, or relation link
drifts, the API returns `503` and does not serialize strategy data:

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

Database connectivity/query failures use one strategy-route envelope with
`503` and `detail.code=DATABASE_UNAVAILABLE`; `/health/ready` remains a
`HealthResponse` with `database=error` and `fixture=unknown`.

The running FastAPI application publishes the executable OpenAPI contract at
`/openapi.json`.

Run `npm run check:contract` from the repository root after changing a response
schema or the TypeScript API client. The check generates OpenAPI from the
FastAPI app, compares the mapped domain property sets, required fields, and
nullability against `packages/api-client/src/types.ts`, and fails closed on
drift. Set `PCR_OPENAPI_PYTHON` only when the project Python interpreter cannot
be discovered automatically.

Browser access uses an explicit read-only CORS allowlist. Current defaults are
`http://localhost:3000` and `http://127.0.0.1:3000`; deployments may replace it
with the comma-separated `PCR_CORS_ORIGINS` environment value. Wildcards,
credentialed requests, and non-GET preflights are rejected.
