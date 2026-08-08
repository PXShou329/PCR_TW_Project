# A4→A3 回滾與重新前進手冊

## 適用範圍

本手冊只處理 RP-A4「蒼波深域 8-10」私人 staging 回退至 `rp-a3-1`，以及其後重新前進
至 `rp-a4-1`。Research core 仍是 file SSOT；PostgreSQL 是可重建的不可變 read mirror。
Data Gate A／B／C 與 Gates D–G 均未宣稱通過。

`rp-a3-1` 的 Alembic 程式碼不知道 V0005。因此，**不得先部署 A3 image，再對 V0005 DB
執行降版**。正確順序一定是：quiesce → verified backup → 以 A4 importer 啟用經 pin
驗證的 A3 revision → 以 A4 migration 降至 V0004 → 驗證 → 才部署 A3 image。

## 固定 pin 與停止條件

RP-A3 必須同時符合：

```text
tag                         rp-a3-1
manifest_sha256             ab62e07483dfea07c992b950b9c05c74fa0e3767fa0b3bce64b20193a1860333
raw/revision_sha256         46d4fea8c1c5cd92e2fd5cb71a7a3ca232d872b1c6d56ce6cd100971250bde45
semantic_sha256             981ca38db9d2fbd416937ba875266d4c18e54a692a77146f698669b8f7871285
materialization_sha256      67e8f2c5435ab70af951e94daab814cf524cb09853b2ab0008d9f32499bfa2b1
files / CSV / rows          48 / 13 / 239
stages / teams              2 / 5
borrowed NULL               0
```

任一 pin、row count、active revision、materialization、stage/team count 不符就停止。
若拿不到 `rp-a3-1` 的完整 raw tree，不能只靠 manifest 回滾；改走已驗證的 pre-A4 backup。
不可把未知借角狀態補成 `false` 來通過 V0005→V0004。

## 路徑 A：還原 pre-A4 backup（優先）

1. Quiesce Web、API、Scheduler 與所有 importer；保留原 DB，不在原 DB 上覆寫。
2. 核對 pre-A4 dump 的 SHA-256、備份時間、Alembic revision 與最近一次 restore drill。
3. 還原到全新 DB，重套 service-role grants，並以唯讀方式核對上述 RP-A3 pins。
4. DB 必須已是 `v0004_unknown_operation_mode`，才部署 `rp-a3-1` image。
5. 驗證 readiness、紅焰 8-10 五隊、Evidence Drawer、desktop/mobile E2E。
6. 原 A4 DB 保持唯讀，直到回滾觀察期結束。

這條路徑保留清楚的 A4 稽核邊界，也避免在來源 DB 上執行 schema downgrade。

## 路徑 B：使用 immutable A3 tree 就地受控回退

先建立並驗證當前 A4 backup。接著從可信任的 Git tag 產生完整 checkpoint；不要使用來源
不明的 ZIP。以下路徑是範例，執行刪除或覆寫前必須核對為 repo 內可丟棄的 `.runtime`：

```powershell
New-Item -ItemType Directory -Force .runtime/rp-a3-1-checkpoint | Out-Null
git archive --format=tar --output .runtime/rp-a3-1.tar rp-a3-1
tar -xf .runtime/rp-a3-1.tar -C .runtime/rp-a3-1-checkpoint
```

私人／disposable staging 的完整原子演練：

```powershell
./scripts/a4_a3_rollback_drill.ps1 `
  -EnvFile .env `
  -CheckpointRoot .runtime/rp-a3-1-checkpoint
```

演練腳本會：

1. 確認起點為 A4 revision `c5a5f13e...d57b9` 與 V0005。
2. 停止 Web、API、Scheduler。
3. 以 A4 importer 讀取完整 A3 raw tree，並要求 `PINNED_ROLLBACK_SOURCE_OK`。
4. 驗證 active A3 revision、materialization、2 stages、5 teams、borrowed NULL=0。
5. 以 A4 migration 執行 V0005→V0004；任何 honest NULL 都會 transactionally fail closed。
6. 再升回 V0005、重新匯入 canonical A4，驗證 active A4 revision與 honest NULL。
7. 只有 DB identity、Compose health 與 API readiness 全部通過才重啟完成並輸出
   `A4_SERVICES_READY_OK`；否則重新 quiesce。

預設演練為了不讓 staging 留在舊版，成功或失敗後都會嘗試恢復 A4。正式回退使用同一支
經測試腳本的明確 `-LeaveAtA3` 邊界；命令要求目前 checkout 仍是 A4、已完成 verified
backup，且 checkpoint 已核對位於預期目錄：

```powershell
./scripts/a4_a3_rollback_drill.ps1 `
  -EnvFile .env `
  -CheckpointRoot .runtime/rp-a3-1-checkpoint `
  -LeaveAtA3
```

腳本使用 fail-closed command wrapper，任何 stop／import／migration 非零 exit 都不會繼續；
它在 downgrade **之前**核對完整 A3 manifest、active revision、materialization、2 stages、
5 teams 與 borrowed NULL=0，並在 downgrade 後再次核對 V0004 與 A3 identity。只有全部成功
才輸出：

```text
PINNED_ROLLBACK_SOURCE_OK
A3_LEGACY_MATERIALIZATION_OK
A4_A3_ROLLBACK_READY_OK
A3_SERVICES_QUIESCED_OK deploy_tag=rp-a3-1
A4_A3_ROLLBACK_COMPLETE_OK alembic=v0004_unknown_operation_mode services=quiesced
```

任一步失敗時會嘗試恢復 A4；若 A4 DB 身分、Compose health 或 API readiness 無法重新
驗證，服務維持 quiesced 並輸出 `SERVICES_LEFT_QUIESCED`，不得人工強制開流量。
成功後，部署 `rp-a3-1` image 前再次以唯讀查核：

```sql
SELECT version_num FROM alembic_version;
SELECT active_revision_id, materialization_sha256
FROM materialization_state WHERE id = 1;
SELECT COUNT(*) FROM stages;
SELECT COUNT(*) FROM teams;
SELECT COUNT(*) FROM team_members WHERE is_borrowed IS NULL;
```

預期依序為 V0004、上述 A3 revision/materialization、2、5、0。部署 A3 後再跑 readiness、
API 契約與 Playwright real-stack E2E；任何不一致時不要開放流量。

## 重新前進至 A4

優先還原降版前已驗證的 A4 backup。若 read mirror 明確可重建，也可在 quiesce 狀態下用
A4 migration `upgrade head`，再由 canonical A4 tree 完整匯入；不得只升 schema 而沿用
A3 active materialization。

重新前進完成條件：

```text
alembic                    v0005_borrowed_tristate
active revision            c5a5f13e0efaf96c1a266c1016d3a1a54740859952ce21f9db3cf89d779d57b9
Water guide count          1
borrowed NULL              > 0（保留真實 UNKNOWN）
baseline                   RESEARCH_BASELINE_OK
readiness                  database=ok, fixture=imported
```

最後重跑 Python、contract/typecheck/build、desktop/mobile E2E 與 backup/restore smoke。

## 立即停止條件

- A3/A4 manifest、raw、semantic 或 materialization pin 漂移。
- A3 raw tree 不完整，或 importer 沒有輸出 pinned-source proof。
- V0005 降版前仍有 `is_borrowed IS NULL`。
- ARTIFACT_READY 出現 Gate A／B／C 以外 FAIL。
- 備份無法 restore，或 restore 後 history／ACL／API/Web 驗證不一致。
- 任一服務未 quiesce、scheduler 非 Shadow Mode、或 secret 出現在 repo/log。
