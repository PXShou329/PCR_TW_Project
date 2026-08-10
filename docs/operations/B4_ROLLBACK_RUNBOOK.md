# RP-B4-0 Rollback Runbook

- Current candidate：RP-B4-0，V0008／materialization v5／29 typed tables
- Immutable rollback target：`rp-a6-0`，V0007／materialization v4／23 typed tables
- Scope：本機／私人 staging
- 實跑狀態：第三輪 `VERIFIED`；前兩輪fail-closed與安全復原均保留稽核紀錄

本手冊定義 backup-first 的 B4→A6→B4 演練與永久回退安全邊界。第三輪已在
`pcr-tw-b4-parena`實跑成功；實際digests、ACL、backup、兩次安全失敗與final chronology見
`B4_0_VERIFICATION_REPORT.md`。這不代表private CI、tag或Gates PASS。

## 1. 不可省略的前置條件

- 使用 exact B4 candidate tree、`scripts/research_core_rp_b4_0_manifest.sha256` 與同一份已
  build 的 API/scheduler image。
- `rp-a6-0` 必須是真實 immutable annotated tag；以 `git archive rp-a6-0` 匯出到新的、
  不存在的 checkpoint 目錄，不接受工作樹 copy。
- `.env` 不進 Git；三個 runtime role passwords彼此不同，owner password不得交給 API。
- 明確傳入 Compose project、API/scheduler image、API/Web/Scheduler ports。
- DB container 必須唯一屬於 exact Compose project、使用單一預期 volume，且沒有外部 DB
  port exposure。
- Scheduler 必須 disabled、Shadow Mode enabled、auto-publish disabled。
- 任何 destructive migration 前都要有已驗證、非空、SHA-256相符的 backup receipt。

若 tag、checkpoint、manifest、image、port、DB target、volume或backup identity不一致，立即
停止；不得以 checkout、重試或手動 SQL 繞過。

## 2. 建立並驗證 backup

```powershell
$backupOutput = @(
  ./scripts/backup_restore_smoke.ps1 `
    -EnvFile (Resolve-Path .env) `
    -ProjectName <exact-project> `
    -ExpectedApiImage <exact-api-image> `
    -ExpectedSchedulerImage <exact-scheduler-image> `
    -ExpectedApiPort <api-port> `
    -ExpectedWebPort <web-port> `
    -ExpectedSchedulerPort <scheduler-port> `
    -KeepBackup
)
$backupOutput | ForEach-Object { Write-Host $_ }
```

只接受恰好一筆 JSON receipt，且 `status=BACKUP_RESTORE_VERIFIED`。在 receipt 的 path、sha256、
bytes 回讀並核對前，不得開始 rollback。

此 smoke 使用兩個不同的 disposable databases：一個驗證 empty-DB restore，另一個驗證 active
B4 v5 不能直接 downgrade。來源 DB 不應被 negative probe 改動。必要 markers 見 B4
verification report。

## 3. 匯出 immutable A6 checkpoint

```powershell
$checkpointRoot = Join-Path $env:TEMP "rp-a6-0-checkpoint-<unique>"
$checkpointArchive = Join-Path $env:TEMP "rp-a6-0-checkpoint-<unique>.tar"
git archive --format=tar --output=$checkpointArchive rp-a6-0
New-Item -ItemType Directory -Path $checkpointRoot
tar -xf $checkpointArchive -C $checkpointRoot
```

目標目錄與 archive 必須事前不存在。Rollback script會重新核對 A6/B4 manifest digests與
checkpoint內的 canonical research core；搜尋摘要、working tree 或非 pinned ZIP不能替代。

## 4. 執行 B4→A6→B4 drill

```powershell
./scripts/b4_a6_rollback_drill.ps1 `
  -EnvFile (Resolve-Path .env) `
  -ProjectName <exact-project> `
  -ExpectedApiImage <exact-api-image> `
  -ExpectedSchedulerImage <exact-scheduler-image> `
  -ExpectedApiPort <api-port> `
  -ExpectedWebPort <web-port> `
  -ExpectedSchedulerPort <scheduler-port> `
  -A6CheckpointRoot $checkpointRoot `
  -VerifiedBackupPath <receipt.path> `
  -VerifiedBackupSha256 <receipt.sha256>
```

### Phase 1：證明 B4 origin

Script 必須驗證：

- Alembic=`v0008_parena_planner_slice`。
- Active revision、ImportRun、materialization v5／29、portable pins與serving counts一致。
- 6 張 P-Arena tables存在；current mature cases為0且 API/UI回報
  `NO_MATURE_PARENA_CASE`。
- ACL為B4 exact 7-privilege contract；public readiness不改 activation chronology或epoch。

成功邊界：`B4_ORIGIN_VERIFIED_OK`。

### Phase 2：資料先回退 A6，再降 schema

1. 停止 public services並保持 Scheduler disabled。
2. 用 current B4 binary及 read-only checkpoint啟用 pinned A6 v4／23 projection。
3. 驗證 active revision是 exact A6，6 張 P-Arena tables均為0 rows。
4. 只有此時才執行 `alembic downgrade v0007_gacha_timeline_slice`。
5. 驗證 V0007、A6 revision／ImportRun／materialization／epoch不漂移。
6. 啟動中繼 A6 services並驗證 P-Arena endpoints以 `NO_PARENA_MATERIALIZATION` fail closed。
7. 再次停止中繼 services。

關鍵 markers：

```text
B4_A6_DATA_ROLLBACK_OK
B4_A6_SCHEMA_DOWNGRADE_OK
A6_PUBLIC_READINESS_OK
A6_INTERMEDIATE_SERVICES_READY_OK
A6_INTERMEDIATE_SERVICES_STOPPED_OK
```

不可在 active B4 v5 ownership下直接 downgrade；即使 47 是0 rows也不例外。

### Phase 3：恢復 exact B4

1. 在 services quiesced 狀態執行 `alembic upgrade head`。
2. 驗證 V0008與6張空的P-Arena tables已恢復。
3. 用 canonical B4 source與pinned manifest重新啟用exact B4 v5／29。
4. 驗證只允許 exact origin identity或一條 A6 `ROLLBACK`＋B4 `REACTIVATE` chronology。
5. Provision roles、啟動B4 services，重驗ACL、API、Web、P-Arena zero-case語意與epoch。

成功邊界：

```text
A6_B4_SCHEMA_UPGRADE_OK
B4_RECOVERY_MODE_OK
B4_RESTORED_OK
B4_PUBLIC_READINESS_OK
B4_SERVICES_READY_OK
B4_A6_ROLLBACK_DRILL_OK
```

## 5. 失敗處理

- Backup尚未驗證：禁止任何資料或schema變更。
- A6 data activation失敗但仍為B4 origin：驗證 exact B4後才可恢復服務。
- 已啟用A6或已降V0007：服務保持quiesced；script先嘗試升V0008並恢復exact B4。
- 自動恢復失敗：不得啟動public services；保留DB、logs、checkpoint與verified backup，依
  receipt從backup人工復原。
- Intermediate services停止失敗：視為rollback失敗，不可繼續對外服務。
- 不允許用手動刪P-Arena rows、修改`materialization_state`或偽造activation history解鎖。

## 6. 永久回退到 A6

Drill預設一定重新前進B4。若要永久停在A6，必須另有明確發布決策，且只能在下列條件全部
成立時停止：

- verified backup仍可讀且digest相符；
- exact A6 v4／23已啟用，V0007 downgrade成功；
- A6 public readiness與ACL通過；
- 中繼狀態被記錄為新的操作事件，而不是移動`rp-a6-0` tag；
- 所有B4-only endpoint在A6語意下fail closed；
- 使用者明確核准永久回退。

否則一律完成B4 reactivation。

## 7. CI／local串行順序

Base stack完成health與ACL後，完整順序固定為：

```text
scheduler-smoke
round-trip-smoke
consistency-smoke
cache-epoch-smoke
artifact-lock-smoke
backup_restore_smoke + b4_a6_rollback_drill
revision-history-smoke
revision-history-verify
npm run test:e2e
```

任一階段失敗即停止後續階段並保存現場；不得以profile-wide併發執行、不得先跑history smoke
污染origin chronology，也不得在rollback尚未恢復B4前執行E2E。

## 8. 清理

只有在B4完全恢復且所有證據已保存後，才可清理checkpoint archive、extracted checkpoint與
disposable restore/probe databases。保留backup時必須在verification report記錄path、SHA-256、
bytes與retention決策；刪除實質backup需要另行明確授權。

## 9. 本次實跑稽核摘要

- Verified backup：`.runtime/backups/pcr_tw_20260810005908_e07535.dump`，SHA-256
  `9ec827da424be4fb3295ba4604f4dd93d567ebba5136f42f118c5388f6c57441`，599041 bytes。
- Immutable A6 checkpoint：`.runtime/rp-a6-0-b4-checkpoint-exact`；archive SHA-256
  `fb0c2e1a2b016962c068590c20ea5ae03ae19165a79bb6f298c3aa81bf848768`。
- 第一輪在physical V7 public readiness以`UndefinedTable`停止，之後安全升V8並完成
  sequences 2/3 recovery；沒有對外宣稱成功。
- 第二輪因A6 v4 public baseline 19 keys與current response要求25 keys不一致而停止，之後
  完成sequences 4/5 recovery；修正只zero-fill 6個public P-Arena欄位，不改A6 v4／23 identity。
- 第三輪成功：origin `5@4584`→A6 `ROLLBACK 6@5327`→physical V7 readiness＋P-Arena
  HTTP 503→V8→B4 `REACTIVATE 7@6076`→`B4_A6_ROLLBACK_DRILL_OK`。
- History verifiers完成後為sequence 9／epoch 7997，history SHA-256
  `e9ed63221d6500e9db213eeb720074c7e93f4eb093f3a4b03dac8a71958b6bc0`。
- 同一final tree的companion regression：collect `404`、完整Python `404/404`（96.520s）、
  operations `97/97`（13.911s）、contract schemas 34、typecheck/build PASS、full mock
  `30/30`、real stack `28/28`。
