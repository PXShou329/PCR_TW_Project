# API v1 contract (RP-A5 Arena exact slice + B3/D0 picker API)

All public strategy endpoints are read-only `GET` endpoints and return:

```json
{
  "data": {},
  "meta": {
    "api_version": "v1",
    "generated_at": "2026-08-08T00:00:00Z",
    "server": "TW",
    "environment_version": "TW-2026-05-25",
    "verified_at": null,
    "stale_status": "UNKNOWN",
    "confidence": "UNKNOWN",
    "evidence_ids": ["ev113"],
    "claim_ids": ["CLM-ARENA-DEF"],
    "data_revision": "<64 lowercase hex>",
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
- `GET /api/v1/pvp/characters`
- `GET /api/v1/pvp/counters?defense_signature=...`

`GET /api/v1/pvp/characters` returns only typed `Character` rows whose TW
availability is exactly `AVAILABLE`. Each row has `unit_key`, the stored TW
official name, the stored JP official name or explicit `UNKNOWN`, and
`tw_availability_status=AVAILABLE`. Results have a deterministic `(tw_name, unit_key)`
Unicode-code-point order; the API never substitutes a JP name for a missing TW
official name. Every returned AVAILABLE row must reference at least one Evidence
record that actually exists and is exactly `ACTIVE` / `TW` / `OFFICIAL` / `A`;
otherwise the endpoint fails closed with `503 FIXTURE_DRIFT`. The lookup loads the
referenced Evidence union in one batch rather than issuing one query per character.

The counter endpoint remains exact-only. `defense_signature` is five unique
semicolon-separated canonical unit keys; its identity is order-independent.
A four-of-five overlap never falls back to Similar. The current RP-A5 data may
return traceable `SINGLE_REPORT` rows together with `NO_VERIFIED_COUNTER` and
`SINGLE_REPORT_REFERENCE_ONLY`; these rows are not mature or `VERIFIED`.

Envelope metadata uses one conservative aggregation contract:

- `data_revision` is the active immutable CoreRevision and is identical to
  `source.revision_id`; import time is never used as content verification time.
- `server` and `environment_version` are concrete only when every returned
  record has the same known value. Distinct known values produce `MIXED`; an
  empty result or any missing/unknown contribution produces `UNKNOWN`.
- `verified_at` is the oldest verification date in a complete dated closure;
  it is `null` for an empty result or when any record lacks that fact.
- `stale_status` is `STALE` if every record has freshness information and at
  least one is stale, `CURRENT` only when all are current, otherwise `UNKNOWN`.
- `confidence` is the weakest A–E value only when every record has a known
  confidence; otherwise it is `UNKNOWN`.
- `evidence_ids` and `claim_ids` are de-duplicated, lexically sorted unions of
  typed relations available to the returned closure. A missing typed relation
  is represented by an empty list, never by an inferred identifier.

During D0, PVP characters expose only mechanically proven `server=TW` and their
referenced `evidence_ids`; PVP counters expose only homogeneous `server`,
`environment_version`, and their typed `evidence_ids` / `claim_ids`. Both keep
`verified_at=null`, `stale_status=UNKNOWN`, and `confidence=UNKNOWN` until the
complete character/defense + Claim + Evidence freshness and confidence closure is
typed and aggregated. Existing endpoints without an unambiguous closure expose the same
required metadata fields conservatively as `UNKNOWN`, `null`, and empty lists.
This sub-slice is contract preparation and does not declare Gate D passed.

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
