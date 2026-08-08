# B1 全量 Research Core Mirror 維運手冊

## 適用範圍

B1 將 manifest 鎖定的 48 檔 research core 建成不可變 PostgreSQL read mirror，並保留
13 個 CSV／215 rows 的 lossless row projection。`research_core/pcr_tw_project/` 仍是唯一
可寫 SSOT；資料庫、API、exporter 與 scheduler 都不得回寫 canonical files。

本手冊適用本機／私人 staging。Data Gate A／B／C 仍未通過，Application／Automation／
Production Gates D–G 也尚未宣稱通過；不得把本里程碑當公開 production release。

## 固定安全邊界

- 只接受 `scripts/research_core_rp_a2_manifest.sha256` 鎖定的來源樹。
- Source loader 與 exporter 拒絕 symlink、Windows junction／reparse、path traversal、
  canonical tree 內目的地與既存目的地。
- ImportRun、terminal CoreRevision 與其 files／rows 不可覆寫；activation audit append-only。
- API 只用 `pcr_api` read-only role；Importer、Scheduler、Migration 各用不同角色。
- API 的 PostgreSQL transaction 使用 `REPEATABLE READ`；readiness cache 以 active
  revision、run、epoch 與 manifest 為 key，epoch 只能嚴格增加。
- Scheduler 固定 Shadow Mode，沒有 canonical writer。
- `-SeedRevisionHistory` 只可用於 CI／可丟棄 staging DB，不得對 durable 或 production DB
  執行；它會故意建立一筆 synthetic inactive revision 以測 A→B→A restore。

## 啟動與基本檢查

建立 Git 忽略的 `.env`，四組 DB 密碼必須互異且至少 16 字元。所有 Python runtime 與
verification services 共用同一個 `${PCR_API_IMAGE}`；這可防止 profile-only smoke 誤用
舊 image。

```powershell
docker compose --profile verification --env-file .env -f infra/compose.yml config --quiet
docker compose --env-file .env -f infra/compose.yml up --build --wait
docker compose --env-file .env -f infra/compose.yml ps --all
```

Readiness 必須為：

```json
{"status":"ok","checks":{"database":"ok","fixture":"imported"}}
```

若 migration 檔在本機已用相同 revision id 套過但內容又被開發中修改，Alembic 不會重跑。
測試 V0003 最終內容時必須使用全新 volume；只可刪除已核對名稱的 disposable project
volume，不得刪 durable DB。

## Research baseline 與 round-trip

Canonical 快速檢查：

```powershell
python scripts/check_research_baseline.py
```

隔離 round-trip（SQLite staging，五命令只在 disposable export copy 執行）：

```powershell
$env:PYTHONPATH = "apps/api;data_pipeline;database"
python -m pcr_pipeline.verify_round_trip --run-baseline
```

實際 PostgreSQL／`pcr_api` role：

```powershell
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps round-trip-smoke
```

成功條件包含：`ROUND_TRIP_OK`、48 files、13 CSV、215 rows、deterministic exports、
Evidence→Claim 75、Claim→Evidence 162，以及 exported copy 的
`RESEARCH_BASELINE_OK`。ARTIFACT_READY 目前仍應只有 Gate A／B／C 三個 FAIL。

## Revision 匯入、啟用與回退

正常啟動會先跑 baseline，再由 importer 在一個 transaction 完成：

1. 單次 capture selected source bytes，建立 typed closure。
2. 載入 immutable full-core snapshot，逐檔 cross-check selected hashes。
3. 建立 `RUNNING` ImportRun 與 `STAGING` CoreRevision。
4. 寫入 artifact／row mirror 與 typed serving closure。
5. 重算 raw、semantic、materialization digests。
6. 將 run／revision 終結為 `SUCCEEDED`，append activation audit。
7. 最後切 active pointer 並增加 epoch。

相同 active revision replay 是零寫入 no-op。新的 manifest-pinned revision 記為 `IMPORT`；
切回 chronology 較早 revision 記為 `ROLLBACK`；再往較晚 revision記為 `REACTIVATE`。
不得直接 UPDATE terminal history 或自行改 active pointer。

檢查所有 active／inactive revisions 與完整 audit digest：

```powershell
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps revision-history-verify
```

`REVISION_HISTORY_VERIFIED` 會在單一 `REPEATABLE READ` snapshot 內逐 revision 重建
materialized report，並把完整 CoreRevision、ImportRun、activation 與 MaterializationState
納入 canonical SHA-256。

## Cache、交易與權限 smoke

```powershell
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps consistency-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps cache-epoch-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps artifact-lock-smoke
./scripts/check_db_privileges.ps1 -EnvFile .env
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm scheduler-smoke
```

預期狀態：

- `REPEATABLE_READ_CONSISTENCY_OK`
- `CACHE_EPOCH_FAIL_CLOSED_OK`，HTTP 序列 `200 → 503 → 200`，epoch rewind 被 DB 拒絕
- `ARTIFACT_FINALIZE_LOCK_OK`，競爭中的 finalizer 得到 `55P03`，probe 清理為 0 rows
- `DB_PRIVILEGES_OK`，含實際 ACL、terminal immutability、epoch 與 composite FK probes
- `SCHEDULER_SHADOW_SMOKE_OK`，`SHADOW_NOOP` 後為 `DUPLICATE_SKIPPED`

## 備份、還原與歷史內容驗證

一般維運演練不修改來源 DB：

```powershell
./scripts/backup_restore_smoke.ps1 -EnvFile .env
```

CI／全新 disposable DB 才可加入：

```powershell
./scripts/backup_restore_smoke.ps1 -EnvFile .env -SeedRevisionHistory
```

演練會：

1. 建立 custom-format dump 並確保 local retention path 可讀。
2. 還原至全新 database。
3. 比對所有 public table row counts 與 Alembic revision。
4. 對 source／restore 的所有 revisions、ImportRuns、activation audit 與 state 比對
   canonical SHA-256，而不是只比 row count。
5. 在 restore DB 重跑 240 項 role matrix 與實際 denial probes。
6. 用 `pcr_api` role 做 round-trip，再啟動 disposable API／Web 驗 critical path。
7. 在 clone 上實跑 V0003→V0002 downgrade，確認 legacy latest 仍指向降版前 active run。
8. 即使主流程失敗，也逐一嘗試清理 Web、API、restore DB 與 dump，再彙整 cleanup error。

`BACKUP_DIR` 依 process env／EnvFile 解析，relative path 以 `infra/compose.yml` 所在目錄為
基準。`-KeepBackup` 會保留 dump。`-KeepRestoredDatabase` 只用於除錯，成功時留下的是
最後 rollback probe 的 V0002 database，不是 B1 clone。

## 回滾至 A2＋B2

`rp-a2-b2-2` 只固定程式碼；單獨 checkout tag **不是**安全回滾。已有 A→B→A 歷史時，
舊 API 的 `latest_import` 可能選到 inactive B。

### 路徑一：還原 pre-B1 backup（優先）

1. 停止 Web、API、Importer、Scheduler，保留 DB。
2. 驗證 pre-B1 dump hash 與 restore drill 紀錄。
3. 在新的空 DB 還原 dump並重套 service-role grants。
4. 部署 `rp-a2-b2-2` code/image，讓服務指向該 DB。
5. 驗證 V0002、readiness、紅焰 8-10、Evidence Drawer 與 E2E。
6. 原 B1 DB 保持唯讀，直到回滾觀察期結束。

### 路徑二：transactional downgrade reconciliation

1. Quiesce 所有 readers／writers。
2. 先建立並驗證當前 B1 backup；記錄 active revision/run。
3. 以 migration owner 執行：

```powershell
alembic -c database/alembic.ini downgrade v0002_operation_timelines
```

4. V0003 downgrade 會在移除 state 前，確認 active run 為 `SUCCEEDED`，並只在 downgrade
   transaction 中把其 `imported_at` 提升到 legacy latest；正常 B1 terminal guard不放寬。
5. 查詢舊排序必須等於原 active run：

```sql
SELECT id
FROM import_runs
WHERE status = 'SUCCEEDED'
ORDER BY imported_at DESC, id DESC
LIMIT 1;
```

6. 確認 Alembic 為 `v0002_operation_timelines` 且五個 B1 tables 已移除，再部署
   `rp-a2-b2-2`。

降版會失去 B1 artifact/history tables，且 reconciliation 會刻意改寫 active run 的 legacy
ordering timestamp。若需保留完整稽核，使用 pre-B1 backup 路徑。

### 降版後重新前進

不可只執行 `upgrade head` 再切回 B1 tag：V0002 保留的 terminal ImportRuns 與新建空
CoreRevision tables 會形成不完整歷史。只能：

- 還原降版前已驗證的 B1 backup並部署同版 B1 code/image；或
- 對明確核准可丟棄的 read mirror 重建空 DB，再由 canonical file SSOT 完整匯入。

## 立即停止條件

- Canonical 48-file manifest、raw tree 或 exported baseline 漂移。
- ARTIFACT_READY 出現 Gate A／B／C 以外 FAIL。
- Typed closure captured hash 與 full-core snapshot 不一致。
- 任一 terminal history、activation audit 或 epoch guard可被繞過。
- API readiness 在 core/typed drift 時仍回 200。
- Backup restore 的 revision-history digest、權限、API/Web 或 legacy rollback probe 不一致。
- Scheduler 非 Shadow Mode、具 canonical write capability，或任何 secret 出現在 repo/log。
