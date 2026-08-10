# RP-B4-0 Verification Report

- 狀態：`CANDIDATE / LOCAL RUNTIME+ROLLBACK VERIFIED / PRIVATE CI PENDING`
- 日期：2026-08-10
- 範圍：Princess Arena Planner typed structural closure
- 前一 immutable rollback target：`rp-a6-0`
- Gates：A／B／C／E／F／G `NOT PASS`；D `BLOCKED_BY_DATA_GATES`

本報告分開記錄 portable identity、已實跑的 local/private instance，以及尚未發生的 release
identity。Local Docker health、ACL、backup／restore、B4→A6→B4、Python／operations、
contract／typecheck／build與mock／real E2E均已取得實證；CI、commit、PR與tag仍為
`PENDING`。不得由local PASS、A6歷史報告或目前程式碼存在推論release／Gate PASS。

## 1. Release identity

| 欄位 | 狀態／值 |
|---|---|
| application version | `3.0.0-b4` |
| Python version | `3.0.0b4` |
| candidate commit | `PENDING` |
| private branch CI | `PENDING` |
| annotated tag `rp-b4-0` | `PENDING / NOT CREATED BY THIS REPORT` |
| tag CI | `PENDING` |
| local working tree cleanliness | `PENDING` |

Tag 只能在 exact final commit 的 private CI 實際成功後建立。Tag-triggered CI 必須另列，不得
用 branch run、A6 run 或未發生的 run number替代。

## 2. Portable research identity

以下值由 current B4 pinned snapshot 重算；final candidate 封版時仍須重新執行 baseline，並
確認沒有漂移：

| 項目 | Pin |
|---|---|
| manifest SHA-256 | `eda30340c02f2f470475e652786104c521faf2ea4cc20be44cf09f3798fe8c5f` |
| raw/revision SHA-256 | `1ba25a73df01ca8d9b161c60836d997f6db202a18d140ee1e92a7d96f62d7a17` |
| semantic SHA-256 | `46000a4a6f9ee70067876c7c1a73fd61d4d06a6f93c5b61831c15d41c9d8811e` |
| artifact diagnostic SHA-256 | `bb71dce87b8a651de794672741a5481a6b754861d694561974ce534e17eb9720` |
| Evidence→Claim | 120; `a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af` |
| Claim→Evidence | 298; `24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c` |
| corpus | 48 files／13 CSV／376 rows |
| Mutation contract | 122 active scenarios |

Artifact diagnostic 是可重算診斷，不是 PostgreSQL instance 的 materialization identity。
ImportRun、typed materialization digest、activation sequence 與 epoch 必須在 local/CI instance
小節另行記錄。

## 3. Current B4 design facts

- Alembic head：`v0008_parena_planner_slice`。
- Materialization：v5／29 typed serving tables。
- 新增 6 tables：`arena_source_records`、`parena_cases`、`parena_case_matchups`、
  `parena_case_sources`、`parena_case_evidence`、`parena_case_claims`。
- Current 47：0 rows／0 mature cases。
- API：`GET /api/v1/parena/environments`、`POST /api/v1/solver/parena`。
- UI：`/parena`；零案例顯示 `NO_MATURE_PARENA_CASE`，沒有 Similar 或理論隊 fallback。

## 4. Required verification commands

### Research baseline

```powershell
python scripts/check_research_baseline.py
```

該 wrapper 必須在 disposable copy 實際執行五命令：

```powershell
python tools/validate_project.py --mode PRE_SUITE --write
python tools/validate_project.py --mode PRE_SUITE
python tools/validate_project.py --mode OPERATIONAL
python tools/validate_project.py --mode ARTIFACT_READY
python tools/mutation_test.py
```

Final disposable-copy actual：

| Mode | Exit | Checks／Fail／Warn | Gate contract |
|---|---:|---:|---|
| PRE_SUITE `--write`＋no-write | 0 | `166／0／22` | A/B/C皆False；blocking=14 |
| OPERATIONAL | 0 | `165／0／21` | A/B/C皆False；blocking=14 |
| ARTIFACT_READY | 1 | `168／3／21` | 只有Gate A、B、C三個FAIL |
| Mutation | 0 | 122 active scenarios | `MUTATION_TESTS ALL_OK` |

Wrapper final marker：`RESEARCH_BASELINE_OK files=48 mutation_scenarios=122`；manifest
`eda30340c02f2f470475e652786104c521faf2ea4cc20be44cf09f3798fe8c5f`。

### Application and static verification

```powershell
python scripts/check_application_data_parity.py --run-round-trip
python -m pytest tests apps/scheduler/tests
npm ci
npm run check:contract
npm run typecheck
npm run build:web
```

Final local regression：

| Verification | Actual |
|---|---|
| pytest collect | `404` |
| full `tests apps/scheduler/tests` | `404/404`，96.520s |
| complete `tests/operations` | `97/97`，13.911s |
| OpenAPI／typed client | `OPENAPI_CLIENT_PARITY_OK schemas=34` |
| TypeScript | typecheck `PASS` |
| Next.js | production build `PASS`；包含`/api/v1/solver/parena`與`/parena` |
| full mock Playwright | `30/30`，desktop＋mobile |

### Local/private Compose verification

```powershell
docker compose --env-file .env -f infra/compose.yml config --quiet
docker compose --env-file .env -f infra/compose.yml up --build --wait
./scripts/check_db_privileges.ps1 -EnvFile .env -ProjectName <exact-project>
```

Base stack 啟動後，stateful verification 必須嚴格串行：

1. `scheduler-smoke`
2. `round-trip-smoke`
3. `consistency-smoke`
4. `cache-epoch-smoke`
5. `artifact-lock-smoke`
6. `backup_restore_smoke.ps1`，接著 `b4_a6_rollback_drill.ps1`
7. `revision-history-smoke`
8. `revision-history-verify`
9. `npm run test:e2e`

不得用 verification profile-wide `up` 併發執行。

## 5. Local instance evidence — VERIFIED

| Evidence | Final actual |
|---|---|
| Compose project、ports | `pcr-tw-b4-parena`；Web `3600`、API `8600`、Scheduler `8681` |
| service health | Web／API／Scheduler `healthy` |
| API／scheduler image IDs/digests | 本輪提供的證據未列出；不得猜測 |
| db/api/web/scheduler container IDs、DB volume identity | 本輪提供的證據未列出；不得猜測 |
| application／schema | `3.0.0-b4`；`v0008_parena_planner_slice`；materialization v5／29 tables |
| active revision／raw | `1ba25a73df01ca8d9b161c60836d997f6db202a18d140ee1e92a7d96f62d7a17` |
| active ImportRun | `c9c3156c-3d99-45e9-8148-a8d43280d578` |
| active materialization SHA-256 | `a18eb4e3283015108f6b7e8ccc069f8dad0639e4a613753ca47274ffd5adb91d` |
| final activation state | active B4；sequence `9`；epoch `7997` |
| P-Arena serving counts | `arena_source_records=6`；cases／matchups／sources／evidence／claims皆為 `0` |
| API truth contract | `NO_MATURE_PARENA_CASE`；沒有 Similar fallback |
| ACL | `DB_PRIVILEGES_OK matrix_checks=777 actual_denials=26 allowed_smokes=12` |
| targeted mock E2E | `4/4` |
| full mock E2E | `30/30` |
| real-stack E2E | `28/28` |

## 6. Backup/restore evidence — VERIFIED

本機實跑已通過下列 marker contract：

```text
B4_COMPOSE_PREFLIGHT_OK
B4_DB_TARGET_OK
B4_ARTIFACT_DIAGNOSTIC_PINNED
BACKUP_ARTIFACT_VERIFIED
RESTORED_REVISION_HISTORY_OK
RESTORED_HISTORY_DIGEST_OK
RESTORED_DB_GUARDS_OK
RESTORED_ROUND_TRIP_OK
RESTORED_API_READINESS_OK
RESTORED_WEB_EVIDENCE_OK
PARENA_DOWNGRADE_BLOCKED_OK
BACKUP_RESTORE_OK
{"status":"BACKUP_RESTORE_VERIFIED", ...}
```

Retained verified backup：

| 欄位 | 實際值 |
|---|---|
| repository-relative path | `.runtime/backups/pcr_tw_20260810005908_e07535.dump` |
| SHA-256 | `9ec827da424be4fb3295ba4604f4dd93d567ebba5136f42f118c5388f6c57441` |
| bytes | `599041` |
| source epoch at backup | `1171` |

Empty-DB restore、history digest、round-trip、API/Web Evidence與獨立 disposable DB 的 active-v5
downgrade拒絕均已完成；`PARENA_DOWNGRADE_BLOCKED_OK`證明來源B4 DB沒有被負向probe改動。
Backup仍保留，不在本文件更新中刪除。

## 7. B4→A6→B4 rollback evidence — VERIFIED ON THIRD RUN

Final report 必須貼出至少以下實際 markers 與 chronology：

```text
VERIFIED_BACKUP_INPUT_OK
B4_A6_MANIFEST_INPUTS_OK
B4_COMPOSE_PREFLIGHT_OK
B4_DB_TARGET_OK
A6_IMMUTABLE_RELEASE_INPUT_OK
B4_ORIGIN_VERIFIED_OK
A6_CHECKPOINT_PREFLIGHT_OK
B4_A6_DATA_ROLLBACK_OK
B4_A6_SCHEMA_DOWNGRADE_OK
A6_PUBLIC_READINESS_OK
A6_INTERMEDIATE_SERVICES_READY_OK
A6_INTERMEDIATE_SERVICES_STOPPED_OK
A6_B4_SCHEMA_UPGRADE_OK
B4_RECOVERY_MODE_OK
B4_RESTORED_OK
B4_PUBLIC_READINESS_OK
B4_SERVICES_READY_OK
B4_A6_ROLLBACK_DRILL_OK
```

### Immutable A6 input

- Extracted checkpoint：`.runtime/rp-a6-0-b4-checkpoint-exact`
- Checkpoint archive SHA-256：
  `fb0c2e1a2b016962c068590c20ea5ae03ae19165a79bb6f298c3aa81bf848768`
- Archive inventory：217 tag files；其中research core 48 files。

### 第一輪：physical V7 missing-table failure，安全復原

- B4 data先誠實回退A6，physical schema再由V0008降至V0007。
- 中繼public readiness觸發對V0008-only P-Arena table的存取，PostgreSQL以
  `UndefinedTable` fail closed；本輪沒有宣稱成功。
- Recovery重新升回V0008並恢復B4，留下A6 `ROLLBACK` sequence `2`與B4
  `REACTIVATE` sequence `3`；服務只在exact B4 identity恢復後重啟。
- Root cause修正為：physical V7必須在讀取不存在的P-Arena tables前以materialization
  ownership分流，P-Arena endpoints回`NO_PARENA_MATERIALIZATION`／HTTP 503。Regression
  contract鎖定真實503、V7 state驗證、服務停止與後續B4 recovery順序。

### 第二輪：public baseline 19/25 shape failure，安全復原

- Physical V7 readiness已可到達，但immutable A6 v4 baseline只有19個既有count keys，而
  current `BaselineCounts` response schema要求25個keys，因此比較器fail closed；本輪沒有宣稱成功。
- Recovery再次恢復exact B4，留下A6 `ROLLBACK` sequence `4`與B4
  `REACTIVATE` sequence `5`。
- 修正建立獨立`a6PublicRowCounts`：保留immutable A6 v4／23 identity的19個實際counts，
  只在public response將6個B4-only P-Arena欄位誠實zero-fill。Importer、CoreRevision與
  materialization assertions仍使用原始v4／23 counts，沒有把A6偽裝成v5。
- Regression test
  `test_a6_public_baseline_zero_fills_v5_fields_without_widening_v4_identity`鎖定此邊界。

### 第三輪：成功

| 階段 | Activation／schema evidence |
|---|---|
| B4 origin | sequence `5`、epoch `4584`、V0008 |
| A6 rollback | sequence `6`、epoch `5327`、`ROLLBACK`；先完成B4→A6 data activation |
| Physical A6 | V0008→V0007；`A6_PUBLIC_READINESS_OK`；兩個P-Arena endpoints均HTTP 503 |
| B4 preparation | V0007→V0008 |
| B4 reactivation | sequence `7`、epoch `6076`、`REACTIVATE` |
| Completion | `B4_A6_ROLLBACK_DRILL_OK` |

Rollback後再執行兩個history verifiers，產生synthetic sequences `8`／`9`；最終狀態為：

- active B4 epoch `7997`
- revisions `3`、ImportRuns `3`、activations `9`
- history SHA-256
  `e9ed63221d6500e9db213eeb720074c7e93f4eb093f3a4b03dac8a71958b6bc0`
- active revision／ImportRun／materialization與第5節final IDs完全一致。

## 8. Gate declaration

| Gate | RP-B4-0 declaration |
|---|---|
| Data A | `NOT PASS` |
| Data B | `NOT PASS` |
| Data C | `NOT PASS` |
| Application D | `BLOCKED_BY_DATA_GATES` |
| Application E | `NOT PASS` |
| Automation F | `NOT PASS` |
| Production G | `NOT PASS` |

Current P-Arena mature case count是 0。B4 structural slice、綠色 application tests、local Docker
health 或 private CI 都不能改寫這個 Gate 結論。

## 9. Finalization checklist

- [x] Final tree重跑 portable baseline且 pins完全一致。
- [x] Python／operations／contract／typecheck／Web build實跑。
- [x] Local B4 stack health與 exact instance identity實錄。
- [x] ACL exact matrix實錄。
- [x] Backup／empty-DB restore／V0008 negative probe實錄。
- [x] B4→A6→B4 rollback與 recovery實錄。
- [x] Full/targeted mock與real-stack desktop/mobile E2E實錄。
- [ ] Final candidate commit及 private CI實錄。
- [ ] Annotated `rp-b4-0` 指向 exact commit，tag CI另行實錄。
- [ ] GitHub repository保持 private。

任何 release checkbox未完成時，RP-B4-0仍是candidate，不可改寫為release PASS。Local
runtime/rollback已驗證不改變Gates A–G狀態。
