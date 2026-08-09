# A5→A4 回滾與重新前進手冊

## 適用範圍

本手冊只處理 RP-A5 Arena 私人 staging 回退至 `rp-a4-1`，以及其後重新前進至 A5。
Research core 仍是 file SSOT；PostgreSQL 是可重建的不可變 read mirror。Data Gate A／B／C
目前仍為 false，Gates D–G 也未宣稱通過。Default A5→A4→A5 recovery path 已實跑；
`-LeaveAtA4` 尚未執行，屬 optional destructive boundary，不是 release blocker。

`rp-a4-1` 的 Alembic 程式碼不知道 V0006。因此，**不得先部署 A4 image，再對 V0006 DB
執行降版**。正確順序固定為：安全旗標先驗 → verified backup → quiesce → 以 A5 importer
啟用經 pin 驗證的 A4 revision → 證明六個 Arena 表全空 → 以 A5 migration 降至 V0005 →
再次驗證 → 才部署 A4 image。

## Identity model：portable pins 與 instance digest 分離

目前 A5 portable research-core identity 必須同時符合：

```text
manifest_sha256             1826c8493d40f71a6d0bb9096f57b92fe4e839d52bddf021b0c51e0186dcbda7
raw/revision_sha256         1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c
semantic_sha256             c77bc9893fa0b442832c1dff0c7c4a1c5e6d63ba9bce27c1c2f8078c5c2511b8
artifact_mirror_sha256      0d369f37cbf734582012e249e0cf48799a274a3d6f3100ac56c9c8388e945444
files / CSV / rows          48 / 13 / 356
Evidence→Claim / reverse    111 / 277
Alembic                     v0006_arena_counter_slice
Arena defense / counter     1 / 2
```

`artifact_mirror_sha256` 是 portable CoreFile／CSV row／edge 摘要。它不是 typed DB
materialization。這次 fresh A5 instance 的 DB materialization 為：

```text
39134bf690f4db147ae3bad1d764dc9486815c49a1b40bc836cdfdecb848126f
```

這個值只用來驗證本次 origin、revision、import run 與 restore 後 state 相互一致；不得寫成
portable research-core pin。未來另一個 deployment instance 必須從自身已驗證的
`core_revisions`／`import_runs`／`materialization_state` 取得 typed digest，不能盲用本次值。

回退目標 RP-A4 的 portable identity 必須同時符合：

```text
tag                         rp-a4-1
manifest_sha256             3daf2ab7c212b4f11c58883980d0ada3862400923c81a9bdedcc0500e59b1a9e
raw/revision_sha256         c5a5f13e0efaf96c1a266c1016d3a1a54740859952ce21f9db3cf89d779d57b9
semantic_sha256             73bc25ab75e78f4e762c3afc902c53dfa47180a36a7359a102fbf5e173fb35bf
files / CSV / rows          48 / 13 / 325
stages / teams              3 / 10
Arena 六表 row count        全部 0
```

本次 drill 的 A4 typed materialization 以 `f5d3ae8b…` 開頭；完整值在該次 import result、
`core_revisions` 與 `materialization_state` 間精確一致，但它仍是 instance-specific，不宣稱
固定 portable。任一 portable identity、instance 內 materialization、row count、active
revision 或 Alembic revision 不符就停止。若拿不到 `rp-a4-1` 的完整 raw tree，不能只靠
manifest 回滾；改走降版前已驗證的 backup。

## 必要前置條件：先建立並驗證備份

Rollback drill 不取代備份。執行任何 A4 activation 或 schema downgrade 前，先確認來源為
私人／disposable staging，並執行完整 restore smoke；`-KeepBackup` 只保留這次實際通過還原
驗證的 dump：

```powershell
./scripts/backup_restore_smoke.ps1 `
  -EnvFile .env `
  -KeepBackup
```

本次已驗證並供 default rollback drill 使用的 backup：

```text
path       .runtime/backups/pcr_tw_20260809135027_dc304a.dump
sha256     c4d89d9ac7a9554b7ce2fc08c749dbd6a379f4f02863559819913c3d527f59fc
bytes      1541961
```

必須保存命令輸出的 backup 絕對路徑與 SHA-256，並確認 restore、revision history、ACL、
round-trip、API/Web 關鍵路徑均通過。任何 restore failure、ACL 差異或 history digest 差異都
是立即停止條件。`a5_a4_rollback_drill.ps1` 會重新計算 dump SHA-256；缺少檔案、空檔或
digest 不符都會在 quiesce 前停止。不要在未驗證的 dump 上繼續。

## 路徑 A：還原 pre-A5 backup（優先）

1. Quiesce Web、API、Scheduler 與所有 importer；保留原 DB，不在原 DB 上覆寫。
2. 核對 pre-A5 dump 的 SHA-256、備份時間、Alembic revision 與最近一次 restore drill。
3. 還原到全新 DB，重套 service-role grants，並以唯讀方式核對上述 RP-A4 pins。
4. DB 必須已是 `v0005_borrowed_tristate`，才部署 `rp-a4-1` image。
5. 驗證 readiness、紅焰／蒼波各五隊、Evidence Drawer 與 desktop/mobile E2E。
6. 原 A5 DB 保持唯讀，直到回滾觀察期結束。

這條路徑保留最清楚的 A5 稽核邊界，也避免在來源 DB 上執行 schema downgrade。

## 路徑 B：使用 immutable A4 tree 就地受控回退

從可信任的 Git tag 產生完整 checkpoint；不要使用來源不明的 ZIP。以下路徑只應位於 repo
內可丟棄的 `.runtime`，執行前先核對絕對路徑：

```powershell
New-Item -ItemType Directory -Force .runtime/rp-a4-1-checkpoint | Out-Null
git archive --format=tar --output .runtime/rp-a4-1.tar rp-a4-1
tar -xf .runtime/rp-a4-1.tar -C .runtime/rp-a4-1-checkpoint
```

私人／disposable staging 的完整原子演練：

```powershell
$ProjectName = "<exact-compose-project-name>"
$ExpectedApiImage = "<exact-api-image-ref>"
$ExpectedSchedulerImage = "<exact-scheduler-image-ref>"
$ExpectedApiPort = 8000
$VerifiedBackupPath = (Resolve-Path ".runtime/backups/pcr_tw_20260809135027_dc304a.dump").Path
$VerifiedBackupSha256 = "c4d89d9ac7a9554b7ce2fc08c749dbd6a379f4f02863559819913c3d527f59fc"

./scripts/a5_a4_rollback_drill.ps1 `
  -EnvFile .env `
  -ProjectName $ProjectName `
  -ExpectedApiImage $ExpectedApiImage `
  -ExpectedSchedulerImage $ExpectedSchedulerImage `
  -ExpectedApiPort $ExpectedApiPort `
  -CheckpointRoot .runtime/rp-a4-1-checkpoint `
  -VerifiedBackupPath $VerifiedBackupPath `
  -VerifiedBackupSha256 $VerifiedBackupSha256
```

執行前必須把三個 `<exact-…>` 值換成這個 staging stack 的實值；image 與 API binding 以
同一 `ProjectName` 的 `docker compose ... config --format json`／`docker compose ... port`
結果為準，不可猜測或沿用另一個 stack。腳本會在第一次 DB access 與 quiesce 前 fail closed。

`materialization_state.epoch` 是 serving state 的單調 epoch；consistency／cache smoke 的
typed DML 與 cleanup 會合法推進它，但不新增 `revision_activations`。因此 preflight 要求
`0 < latest activation epoch <= current state epoch`，不要求兩者相等；latest activation
本身仍須精確指向 active A5 revision／import run／materialization。新 A5→A4 activation
epoch 必須嚴格大於演練起點的 current state epoch，後續 A4→A5 audit chain 仍須連續且
final state epoch 必須精確等於 reactivation audit epoch。Epoch 放寬前仍須由目前 A5 API
readiness 在 quiesce 前重算 typed materialization manifest，且精確回報
`database=ok／fixture=imported`；只有 stored digest、pointer 與 row count 相同不足以繼續。

演練腳本會：

1. 在任何服務或 DB mutation 前重新驗證 backup 檔案與 SHA-256，並要求
   `SCHEDULER_ENABLED=false`、`SHADOW_MODE=true`、`AUTO_PUBLISH=false`。
2. 確認起點為 V0006、A5 portable identity、該 instance 的 typed materialization，以及
   1 defense／2 counters 的完整 Arena closure；再從目標 Compose project 解析實際 API port，
   由 readiness 依目前 state epoch 重算 materialization，並確認檢查前後 epoch 未變。
3. 停止 Web、API、Scheduler。
4. 以 A5 importer 讀取完整 A4 raw tree，並要求唯一一筆 `PINNED_ROLLBACK_SOURCE_OK`；
   proof 必須是 48 files、325 CSV rows 與上述 A4 manifest／revision。
5. 驗證 active A4 revision、本次 A4 instance 的精確 materialization、3 stages、10 teams，
   以及六個 Arena 表 row count 全為 0。
6. 只有上述條件全部成立，才以 A5 migration 執行 V0006→V0005；降版後再次核對 A4
   identity，並證明六個 Arena 表已不存在。
7. 預設重新升至 V0006、匯入 canonical A5，驗證 A5 revision、materialization metadata、
   六表 closure（1 defense／2 counters），再檢查 API readiness 後恢復服務。

本次 default drill 的實際 chronology／final markers：

```text
A5_ORIGIN_READINESS_OK      api_port=8300 state_epoch=11348 database=ok fixture=imported
A5_ORIGIN_VERIFIED_OK       activation_sequence=15 activation_epoch=11348 state_epoch=11348
A4_LEGACY_MATERIALIZATION_OK activation_sequence=16 epoch=11962 materialization=f5d3ae8b…
A5_A4_ROLLBACK_READY_OK     alembic=v0005_borrowed_tristate arena_tables=0
A5_FINAL_DB_READBACK        activation_sequence=17 epoch=12634 active_revision=1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c
A5_RESTORED_OK              active_revision=1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c
A5_SERVICES_READY_OK
A5_A4_ROLLBACK_DRILL_OK
```

任一步驟失敗會嘗試恢復 A5；若 A5 DB identity、Arena closure 或 readiness 無法重新驗證，
服務保持 quiesced 並輸出 `SERVICES_LEFT_QUIESCED`，不得人工強制開流量。

### Optional destructive boundary：`-LeaveAtA4`（NOT_RUN）

正式維持 A4 可使用同一支腳本的明確 `-LeaveAtA4` 邊界；本輪**未執行**，且不是 release
blocker。它會在 exact A4 activation、六表歸零、V0005 downgrade 與降版後 identity 全部
通過後刻意不恢復 A5，僅可在 disposable staging 另行演練：

```powershell
./scripts/a5_a4_rollback_drill.ps1 `
  -EnvFile .env `
  -ProjectName $ProjectName `
  -ExpectedApiImage $ExpectedApiImage `
  -ExpectedSchedulerImage $ExpectedSchedulerImage `
  -ExpectedApiPort $ExpectedApiPort `
  -CheckpointRoot .runtime/rp-a4-1-checkpoint `
  -VerifiedBackupPath $VerifiedBackupPath `
  -VerifiedBackupSha256 $VerifiedBackupSha256 `
  -LeaveAtA4
```

未來若執行，成功輸出至少應包含；下列不是本輪實測證據：

```text
PINNED_ROLLBACK_SOURCE_OK
A4_LEGACY_MATERIALIZATION_OK
A5_A4_ROLLBACK_READY_OK alembic=v0005_borrowed_tristate arena_tables=0
A4_SERVICES_QUIESCED_OK deploy_tag=rp-a4-1
A5_A4_ROLLBACK_COMPLETE_OK alembic=v0005_borrowed_tristate services=quiesced
```

此時服務刻意保持停止。部署 `rp-a4-1` image 前，再以唯讀查核：

```sql
SELECT version_num FROM alembic_version;
SELECT active_revision_id, materialization_sha256
FROM materialization_state WHERE id = 1;
SELECT COUNT(*) FROM stages;
SELECT COUNT(*) FROM teams;
```

預期依序為 V0005、上述 A4 revision/materialization、3、10。部署 A4 後再跑 readiness、API
契約與 real-stack Playwright；任何不一致時不要開放流量。

## 重新前進至 A5

優先還原降版前已驗證的 A5 backup。若 read mirror 明確可重建，也可在 quiesce 狀態下用
A5 migration `upgrade head`，再由 canonical A5 tree 完整匯入；不得只升 schema 而沿用
A4 active materialization。

重新前進完成條件：

```text
alembic                     v0006_arena_counter_slice
active revision            1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c
this-run DB materialization 39134bf690f4db147ae3bad1d764dc9486815c49a1b40bc836cdfdecb848126f
Arena defense / counter     1 / 2
Arena member rows           5 / 10
Arena Evidence / Claim      4 / 4
baseline                    RESEARCH_BASELINE_OK（A5 manifest pin）
readiness                   database=ok, fixture=imported
```

`this-run DB materialization` 只適用本次已驗證 instance；其他 instance 必須核對自身 origin 與
restore 後 digest，不得把它當 portable pin。最後重跑 Python、contract/typecheck/build、
desktop/mobile E2E 與 backup/restore smoke。

## 立即停止條件

- 安全旗標不是 scheduler disabled、Shadow Mode enabled、Auto Publish disabled。
- 執行前 backup 無法 restore，或 backup 的 SHA-256／來源時間不明。
- 起點不是 V0006＋精確 A5 portable identity＋該 instance 的 typed materialization，或 A5
  Arena closure 不是 1 defense／2 counters。
- A4 manifest、raw、semantic portable identity 漂移，或本次 A4 instance 的 materialization
  未在 import result／revision／state 間精確一致。
- A4 raw tree 不完整，或 importer 沒有輸出唯一的 pinned-source proof。
- A4 activation 後任一 Arena 表仍有 row，或 V0006→V0005 降版前的 PVE closure 不符。
- 降版後 Alembic revision、active revision、materialization 或 Arena table absence 不符。
- ARTIFACT_READY 出現 Gate A／B／C 以外 FAIL。
- 任一服務未 quiesce，或 secret 出現在 repo／log。
- 預設演練無法精確恢復 A5，或 API readiness 失敗；此時保持服務 quiesced 並人工復原。
- 不得把未執行的 `-LeaveAtA4` 當成 default recovery 或 release 驗證證據。
