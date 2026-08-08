# B0 verification report — 2026-08-08

## Verdict

The v3.0 B0 walking skeleton is accepted as **local/private staging**. It is a
deployable end-to-end slice, not a declaration that research Data Gates A–C or
application／automation／production Gates D–G have passed.

## Research-core baseline (disposable copy)

```text
PRE_SUITE --write  exit=0  CHECKS=112 FAIL=0 WARN=16
PRE_SUITE          exit=0  CHECKS=112 FAIL=0 WARN=16
OPERATIONAL        exit=0  CHECKS=111 FAIL=0 WARN=15
ARTIFACT_READY     exit=1  CHECKS=114 FAIL=3 WARN=15
```

The three ARTIFACT_READY failures were exactly Gate A, Gate B, and Gate C.

```text
MUTATION_TESTS ALL_OK | active_scenarios=54
RESEARCH_BASELINE_OK | files=46 | mutation_scenarios=54 | manifest_sha256=c9aa323626b453afb7f694dd526f90121ce0bf59eda90b3a30a9d955157a773a
```

## Application checks

```text
Python:                         41 passed
OpenAPI / TypeScript parity:    OPENAPI_CLIENT_PARITY_OK schemas=11
TypeScript typecheck:           exit 0
Next.js production build:       exit 0
Mock Playwright desktop/mobile: 8 passed
Real Compose desktop/Pixel 7:   8 passed
pip check:                      No broken requirements found
npm audit --omit=dev:           found 0 vulnerabilities
```

Browser QA also inspected the responsive stage, team, SOURCE_CONFLICT,
UNKNOWN requirements, Evidence Drawer, and PVP no-result states. The UI did
not promote a source locator into a fabricated operation timeline.

## Real PostgreSQL／Compose checks

- Migration and role provision exited 0.
- Service roles: migration owner, serving-table DML importer, read-only API,
  and scheduler-control-only scheduler.
- Privilege verification:
  `matrix_checks=156 actual_denials=6 allowed_smokes=3`.
- Import replay:
  `created=false`, fixture
  `743e4558c86eb445377f8284b12d01f3c49179702dafff1a6ef3a4dda7611ff6`,
  counts `1/3/15/8/18/13` for stage／teams／members／characters／evidence／claims.
- Scheduler remained disabled／ready／Shadow Mode with
  `canonical_write_capable=false`; its smoke path produced
  `SHADOW_NOOP -> DUPLICATE_SKIPPED`.
- Backup → empty restore verified 14 tables, Alembic
  `v0001_b0_read_mirror`, read-only API readiness, PROVISIONAL three-team stage,
  `ev052`, Web SSR, and the same-origin Evidence proxy.

## Serving-boundary drift drill

An isolated restored PostgreSQL database deleted only the
`TM-F810-01 / ev050` relation. Results:

```text
/health/ready -> 503 materialization_team_evidence_drift
SERVING_BOUNDARY_DRIFT_ALL_OK strategy_endpoints=7
```

All seven `/api/v1/*` strategy routes returned `503 / FIXTURE_DRIFT`; none
returned drifted strategy data. The disposable API, database, and dump were
then removed. The main mirror remained healthy and retained the original link.

## Cleanup and retained rollback data

All B0 test containers were stopped. No Docker volume was deleted. These
rebuildable read-mirror volumes remain for rollback／audit:

- `pcr-tw-b0-finalcheck_pg_data`
- `pcr-tw-b0-lpcheck_pg_data`
- `pcr-tw-b0_pg_data`

Known non-blocking B0 debts and their target milestones are recorded in
`docs/architecture/INTEGRATED_ROADMAP.md`.
