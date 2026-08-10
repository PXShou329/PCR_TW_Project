# RP-B4-0 local/private deployment

`compose.yml`是production-shaped local/private staging stack，不是public production manifest。
PostgreSQL固定`18.4-bookworm`；published ports只綁`127.0.0.1`，DB位於internal Docker
network。Alembic是唯一schema migration owner。

Current application version是`3.0.0-b4`，Alembic head是
`v0008_parena_planner_slice`，typed materialization是v5／29 tables。B4 local runtime、ACL、
backup/restore與rollback第三輪已實跑；private CI、commit、PR與tag仍為`PENDING`。

啟動依賴鏈：

```text
db healthy -> migration(owner) -> role-provision -> importer(DML) -> api(SELECT) -> web
                                          `-------> scheduler(control tables only)
```

從repository root建立private `.env`後啟動base stack：

```powershell
docker compose --env-file .env -f infra/compose.yml config --quiet
docker compose --env-file .env -f infra/compose.yml up --build --wait
```

## 安全設定

- `POSTGRES_PASSWORD`、`PCR_API_DB_PASSWORD`、`PCR_IMPORTER_DB_PASSWORD`、
  `PCR_SCHEDULER_DB_PASSWORD`必須彼此不同。
- `SCHEDULER_ENABLED=false`、`SHADOW_MODE=true`、`AUTO_PUBLISH=false`。
- API-family runtime及所有profile-only verifier共用同一`${PCR_API_IMAGE}`，避免smoke使用
  stale code。
- Current image必須同時攜帶B4 current manifest與immutable A6/B5/A5/A4/A3/A2 rollback
  manifests。
- DB不得publish 5432；外部API/Web/Scheduler ports必須只綁loopback。

## 固定串行 verification pipeline

`verification` profile會操作control tables、typed rows、cache epoch與revision／activation
history，因此不得用 `docker compose --profile verification ... up` 併發啟動。Base stack
ready且ACL驗證完成後，固定執行下列前五個verifiers：

```powershell
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps scheduler-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps round-trip-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps consistency-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps cache-epoch-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps artifact-lock-smoke
```

前五個全部成功後，依[`B4_ROLLBACK_RUNBOOK.md`](../docs/operations/B4_ROLLBACK_RUNBOOK.md)：

1. 執行`scripts/backup_restore_smoke.ps1 -KeepBackup`，取得唯一
   `BACKUP_RESTORE_VERIFIED` receipt。
2. 由immutable `rp-a6-0` tag用`git archive`匯出新的read-only checkpoint。
3. 將receipt path/SHA與checkpoint交給`scripts/b4_a6_rollback_drill.ps1`，完成
   V0008 B4→V0008 A6 data activation→V0007 A6→V0008→B4的演練。

對應命令必須明確帶入同一個project、images與ports：

```powershell
./scripts/backup_restore_smoke.ps1 `
  -EnvFile (Resolve-Path .env) `
  -ProjectName <exact-project> `
  -ExpectedApiImage <exact-api-image> `
  -ExpectedSchedulerImage <exact-scheduler-image> `
  -ExpectedApiPort <api-port> `
  -ExpectedWebPort <web-port> `
  -ExpectedSchedulerPort <scheduler-port> `
  -KeepBackup

./scripts/b4_a6_rollback_drill.ps1 `
  -EnvFile (Resolve-Path .env) `
  -ProjectName <exact-project> `
  -ExpectedApiImage <exact-api-image> `
  -ExpectedSchedulerImage <exact-scheduler-image> `
  -ExpectedApiPort <api-port> `
  -ExpectedWebPort <web-port> `
  -ExpectedSchedulerPort <scheduler-port> `
  -A6CheckpointRoot <exact-checkpoint-root> `
  -VerifiedBackupPath <receipt.path> `
  -VerifiedBackupSha256 <receipt.sha256>
```

Rollback完全恢復B4後，才可依序執行兩個history verifiers：

```powershell
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps revision-history-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps revision-history-verify
```

最後才執行browser E2E：

```powershell
npm run test:e2e
```

固定順序是：

```text
前五個 verifier
-> backup_restore_smoke + b4_a6_rollback_drill
-> 兩個 history verifier
-> E2E
```

這與current private CI一致。任一步失敗必須停止後續驗證、保存logs及instance identity；不可
重試掩蓋lock、deadlock、epoch chronology或rollback failure。

## B4 backup與rollback邊界

`backup_restore_smoke.ps1`必須證明：

- exact Compose project/image/port/DB volume preflight；
- current B4 portable與typed instance identity；
- empty-DB restore、history digest、round-trip、API/Web Evidence；
- 在獨立disposable probe DB中，active B4 v5即使零成熟case也不能直接V0008 downgrade；
- source DB在backup與probes後identity完全不變。

B4與A6不是same-schema rollback。正確順序是先以B4 binary啟用immutable A6 v4／23並清空
P-Arena ownership，再V0008 downgrade到V0007；回復時先upgrade V0008，再啟用exact B4
v5／29。不得把歷史A6→B5→A6 zero-Alembic流程套到B4，也不得只checkout `rp-a6-0`。

必要markers、失敗處理、permanent A6 rollback核准條件與cleanup規則見
[`B4_ROLLBACK_RUNBOOK.md`](../docs/operations/B4_ROLLBACK_RUNBOOK.md)。實際Docker IDs、ACL
counts、backup path/SHA/bytes、chronology、E2E與CI只記錄於
[`B4_0_VERIFICATION_REPORT.md`](../docs/operations/B4_0_VERIFICATION_REPORT.md)；尚未實跑或
尚未提供的欄位保持`PENDING`／不得猜測。

## 已驗證的本機實例

- Compose project：`pcr-tw-b4-parena`；Web `3600`、API `8600`、Scheduler `8681`均healthy。
- Final identity：revision
  `1ba25a73df01ca8d9b161c60836d997f6db202a18d140ee1e92a7d96f62d7a17`，ImportRun
  `c9c3156c-3d99-45e9-8148-a8d43280d578`，materialization
  `a18eb4e3283015108f6b7e8ccc069f8dad0639e4a613753ca47274ffd5adb91d`。
- ACL：`DB_PRIVILEGES_OK matrix_checks=777 actual_denials=26 allowed_smokes=12`。
- Backup：`.runtime/backups/pcr_tw_20260810005908_e07535.dump`，SHA-256
  `9ec827da424be4fb3295ba4604f4dd93d567ebba5136f42f118c5388f6c57441`，599041 bytes。
- Third drill：B4 `5@4584`→A6 `ROLLBACK 6@5327`→V0007 public readiness與P-Arena 503→
  V0008→B4 `REACTIVATE 7@6076`→`B4_A6_ROLLBACK_DRILL_OK`。
- History verifiers後：sequence 9／epoch 7997，revisions/runs/activations=`3/3/9`，history
  SHA-256 `e9ed63221d6500e9db213eeb720074c7e93f4eb093f3a4b03dac8a71958b6bc0`。
- E2E：targeted mock `4/4`、real stack `28/28`；P-Arena維持`NO_MATURE_PARENA_CASE`。
- Final non-Docker regression：collect `404`、Python `404/404`（96.520s）、operations `97/97`
  （13.911s）、contract schemas 34、typecheck/build PASS、full mock `30/30`。

第一輪physical V7 `UndefinedTable`與第二輪public baseline 19/25 shape mismatch都觸發
fail-closed recovery；分別完成sequences 2/3與4/5後才修正。不得刪除這兩段稽核歷史或只記
第三輪成功。

## Gate與release語意

RP-B4-0只交付Princess Arena Planner structural slice；canonical 47仍為0 rows／0 mature
cases。A／B／C／E／F／G維持`NOT PASS`，D維持`BLOCKED_BY_DATA_GATES`。Local health、
ACL、backup、rollback、E2E或private CI成功都不能自行提升Gate。

Annotated `rp-b4-0`只能在exact final commit完成private CI後建立；既有A6/B5/A5/A4 tags與
歷史reports/scripts/tests保持immutable。
