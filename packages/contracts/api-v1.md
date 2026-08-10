# API v1 contract (Arena, P-Arena exact planner, and Gacha timeline)

All public strategy endpoints are read-only queries. Most use `GET`; the P-Arena
solver uses `POST` solely because a complete 3×5 query does not fit safely in a
URL. It never mutates serving or canonical data. Every successful query returns:

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
- `GET /api/v1/gacha/timeline`
- `GET /api/v1/gacha/community-sources`
- `GET /api/v1/pvp/characters`
- `GET /api/v1/pvp/counters?defense_signature=...`
- `GET /api/v1/parena/environments`
- `POST /api/v1/solver/parena`

`POST /api/v1/solver/parena` requires `server=TW`, a known non-empty
`environment_version`, exactly three defense teams of five distinct `unit_key`s,
15 globally distinct characters, and every character must be in the same
TW `AVAILABLE` picker closure as `/pvp/characters`. Team and member order do not
change exact identity. Results are always `match_type=EXACT` and
`similar_enabled=false`; each mature case has exactly three matchups, returned in
the caller's defense-team order. Hidden teams, partial teams, Similar reuse, and
theoretical counters are never inferred.

Every returned case carries the designated WIN Claim's stored
`case_win_confidence` (`B|C|D`). `B` and `C` require the research validator's
independent multi-host closure and are presented as `VERIFIED`. `D` remains a
single-report reference: the response adds `CASE_WIN_SINGLE_SOURCE_REFERENCE`
and `CASE_WIN_CONFIDENCE_D_BLOCKS_GATE_C`, and the Web UI must visibly label it
`SINGLE_REPORT` / `BLOCKS GATE C`. The API never derives or upgrades this value.
Referenced file-46 source rows must be `ACTIVE` to serve a case; the typed source
registry itself preserves only canonical `ACTIVE|PARTIAL|BLOCKED|STALE|ARCHIVED`
access statuses and `C|D|E` confidence caps.

When a v5 typed P-Arena materialization contains zero mature cases, any otherwise
valid query returns `200`, `cases=[]`, and `NO_MATURE_PARENA_CASE`. When mature
cases exist but the requested environment or exact three-team signature does not
match, it returns `200`, `cases=[]`, and `NO_EXACT_PARENA_PLAN`. An active v4
snapshot has no typed P-Arena closure, so both P-Arena endpoints fail closed with
`503 NO_PARENA_MATERIALIZATION`; they never present a normal empty result.

`GET /api/v1/pvp/characters` returns only typed `Character` rows whose TW
availability is exactly `AVAILABLE`. Each row has `unit_key`, the stored TW
official name, the stored JP official name or explicit `UNKNOWN`, and
`tw_availability_status=AVAILABLE`. Results have a deterministic `(tw_name, unit_key)`
Unicode-code-point order; the API never substitutes a JP name for a missing TW
official name. Every returned AVAILABLE row must reference at least one Evidence
record that actually exists and is exactly `ACTIVE` / `TW` / `OFFICIAL` / `A`;
otherwise the endpoint fails closed with `503 FIXTURE_DRIFT`. The lookup loads the
referenced Evidence union in one batch rather than issuing one query per character.

`GET /api/v1/gacha/timeline` returns the typed projection of
`41_GACHA_TIMELINE.csv` in deterministic `(jp_date, event_id)` order. Every row
states `source_server=JP` and `target_server=TW`; `tw_name` is nullable and the
API never substitutes `character_name_jp`, a community translation, or a
placeholder. `limited_status` is exactly `YES|NO|UNKNOWN`; the required nullable
`limited_claim_id` carries the exact Claim provenance for `YES|NO` and is null
for `UNKNOWN`. The API never derives it from `pool_type`, names, or chronology. The API preserves
`MATURE|RESEARCH` and literal `NOT_EVALUATED` values rather than upgrading a
research row into a recommendation. `evidence_ids`, `claim_ids`, and
`community_source_ids` are independently de-duplicated by the relational model
and returned in lexical order. There is no personal gem, roster, Similar, or
write endpoint in this slice.

`GET /api/v1/gacha/community-sources` returns the reviewed registry from
`45_GACHA_COMMUNITY_SOURCE_INDEX.csv` in stable `source_id` order. A
`CHECKED` community source remains community evidence with its stored
`confidence_cap` (`C|D|E` only); it is never promoted to `A|B`, `UNKNOWN`, or
official evidence by the API.

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

Gacha timeline records expose only the mechanically proven cross-server scope
(`server=MIXED`) plus linked Evidence/Claim ID unions. Until the complete
Evidence/Claim freshness, environment, and A–E confidence closure is typed,
`environment_version=UNKNOWN`, `verified_at=null`, `stale_status=UNKNOWN`, and
`confidence=UNKNOWN`. Community-source metadata remains fully `UNKNOWN` because
the registry has no typed server/environment freshness closure. Both envelopes
still use the concrete active immutable `data_revision`.

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

Browser access uses an explicit origin and method CORS allowlist. Current defaults are
`http://localhost:3000` and `http://127.0.0.1:3000`; deployments may replace it
with the comma-separated `PCR_CORS_ORIGINS` environment value. Wildcards,
credentialed requests, and methods other than `GET` / read-only solver `POST`
are rejected. Resources without a POST route still return `405`.
