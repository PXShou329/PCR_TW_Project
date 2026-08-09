# A4 verification report — 2026-08-08

## 結論

RP-A4「蒼波深域 8-10」可接受為 **本機／私人 staging**。它新增五支不同五人的實際
通關隊伍、來源分離的操作軸、逐步 Evidence Drawer，以及 `is_borrowed` 的
`true／false／UNKNOWN` 三態保存；不代表 Data Gate A／B／C 或 Gates D–G 已通過。

唯一攻略來源為實際開啟並核對正文／畫面的 YouTube 影片
`https://www.youtube.com/watch?v=w3My0QHcoTA`。五隊均保留 D 級 claim；八筆跨服角色
mapping 最高 B。另一候選影片因 boss 存活且顯示 TIME UP，記為 REJECTED，未計入隊數。

Canonical RP-A4 pins：

```text
files / CSV / rows          48 / 13 / 325
manifest_sha256             3daf2ab7c212b4f11c58883980d0ada3862400923c81a9bdedcc0500e59b1a9e
raw/revision_sha256         c5a5f13e0efaf96c1a266c1016d3a1a54740859952ce21f9db3cf89d779d57b9
semantic_sha256             73bc25ab75e78f4e762c3afc902c53dfa47180a36a7359a102fbf5e173fb35bf
Evidence→Claim / reverse    102 / 268
```

## Research core 五命令

`python scripts/check_research_baseline.py` 從 canonical tree 實際執行五命令，結果為：

```text
PRE_SUITE --write  exit=0  CHECKS=133 FAIL=0 WARN=23
PRE_SUITE          exit=0  CHECKS=133 FAIL=0 WARN=23
OPERATIONAL        exit=0  CHECKS=132 FAIL=0 WARN=22
ARTIFACT_READY     exit=1  CHECKS=135 FAIL=3 WARN=22
MUTATION_TESTS ALL_OK | active_scenarios=75
RESEARCH_BASELINE_OK | files=48 | mutation_scenarios=75 | manifest_sha256=3daf2ab7c212b4f11c58883980d0ada3862400923c81a9bdedcc0500e59b1a9e
```

ARTIFACT_READY 的三個 FAIL 恰為 Gate A／B／C；15 個 blocking warnings 保留，沒有藉由
降低 Gate 或 Validator 約束取得綠燈。

Validator／mutation 新增或鎖定：有效 PVE 隊伍 closure、同五人去重、guide/server/stage
關聯、五個不同 slot、Evidence/Claim active closure、三態借角支援關聯，以及蒼波來源軸的
18 個精確步驟邊界。Mutation 總數由 RP-A3 的 68 增至 75。

## Import、API 與應用驗證

```text
Python pytest                         exit 0（100%）
Maintainer independent Python run     exit 0
OpenAPI / TypeScript parity           OPENAPI_CLIENT_PARITY_OK schemas=22
TypeScript typecheck                  exit 0
Next.js production build              exit 0
Playwright desktop/mobile             20 passed
Docker context allowlist probe        .env.example exit 0
Docker private-env exclusion probe    .env.a4.local exit 1（預期拒絕）
Docker nested-env exclusion probe     apps/web/.env.local exit 1（預期拒絕）
```

E2E 覆蓋紅焰與蒼波關卡、五隊 distinct closure、操作軸與 Evidence Drawer；mock 的 support
欄位誤接到 `requirements.support` 已修正為 canonical `support`，未以放寬 assertion 解決。

## Fresh Compose 與三態語意

隔離 project `pcr-tw-a4-water` 以 PostgreSQL 18.4、V0005、API、Web 與 disabled shadow
scheduler 實際啟動；所有公開 port 只綁 `127.0.0.1`。Readiness：

```json
{"status":"ok","checks":{"database":"ok","fixture":"imported"}}
```

Rollback command 在任何 DB／service 變更前，另以 Compose 同等環境變數優先序要求
`SCHEDULER_ENABLED=false`、`SHADOW_MODE=true`、`AUTO_PUBLISH=false`。

```text
ROLLBACK_FLAG_REJECTED_OK SCHEDULER_ENABLED=true
ROLLBACK_FLAG_REJECTED_OK SHADOW_MODE=false
ROLLBACK_FLAG_REJECTED_OK AUTO_PUBLISH=true
ROLLBACK_FLAG_REJECTION_NO_SIDE_EFFECT_OK
```

API 實際回傳「蒼波8-10」五隊，五隊 `is_borrowed` 均為 `null`，不臆測借角；蒼波共
5 條 timeline／18 個原子步驟，其中手動隊 endpoint 精確回傳 9 個步驟。Current/new A4
run 記錄 `source_truth_tristate_v1`；歷史 RP-A2/A3
run 使用 `legacy_blank_false_v1`。未知、null 或非字串的 semantics metadata 一律 fail closed。

## Backup／restore 與降版邊界

完整 restore drill 實際成功：

```text
revision history=2, activations=3
DB_PRIVILEGES_OK matrix_checks=240 actual_denials=18 allowed_smokes=6
RESTORED_ROUND_TRIP_OK files=48 csv=13 rows=325
BORROWED_TRISTATE_DOWNGRADE_BLOCKED_OK alembic=v0005_borrowed_tristate borrowed_nulls=45 unknown_timelines=1
BACKUP_RESTORE_OK tables=21 source_alembic=v0005_borrowed_tristate restored_alembic=v0005_borrowed_tristate
```

V0005→V0004 在任何 honest borrowed `NULL` 存在時 transactionally fail closed；V0004→V0003
在 `UNKNOWN` operation mode 存在時亦 fail closed。兩條 migration 都有 offline SQL
regression，明確禁止把未知值強制改成 `false` 或任一 operation mode。

## A4→A3→A4 rollback drill

實際演練使用 `git archive rp-a3-1` 產生完整 immutable A3 tree，而非只拿 manifest。
A4 importer 先驗 exact A3 pins，接著啟用 A3 materialization、降 V0005→V0004，再升回
V0005 並重匯 canonical A4。結果：

```text
{"csv_row_count": 239, "file_count": 48, "manifest_sha256": "ab62e07483dfea07c992b950b9c05c74fa0e3767fa0b3bce64b20193a1860333", "revision_id": "46d4fea8c1c5cd92e2fd5cb71a7a3ca232d872b1c6d56ce6cd100971250bde45", "status": "PINNED_ROLLBACK_SOURCE_OK"}
A3_LEGACY_MATERIALIZATION_OK stages=2 teams=5 borrowed_nulls=0
active_revision=46d4fea8c1c5cd92e2fd5cb71a7a3ca232d872b1c6d56ce6cd100971250bde45
materialization=67e8f2c5435ab70af951e94daab814cf524cb09853b2ab0008d9f32499bfa2b1
A4_A3_ROLLBACK_READY_OK alembic=v0004_unknown_operation_mode borrowed_nulls=0
A4_RESTORED_OK alembic=v0005_borrowed_tristate active_revision=c5a5f13e0efaf96c1a266c1016d3a1a54740859952ce21f9db3cf89d779d57b9 borrowed_nulls=45
A4_SERVICES_READY_OK database=ok fixture=imported
A4_A3_ROLLBACK_DRILL_OK
```

完整部署順序、backup-first 優先路徑與停止條件見
[`A4_ROLLBACK_RUNBOOK.md`](A4_ROLLBACK_RUNBOOK.md)。

## 回滾點與未宣稱項目

- A3 code/data checkpoint 為 `rp-a3-1`；A4 全部驗證與 Maintainer review 通過後建立
  `rp-a4-1`。Tag 不取代 DB backup／restore drill。
- Data Gate A／B／C 仍為 false；ARTIFACT_READY 預期 exit 1。
- Gates D–G 尚未宣稱，scheduler 仍 disabled Shadow Mode，沒有 canonical publisher。
- 下一正式里程碑依 v3 企劃為 B3＋A5 Arena；剩餘三個成熟 PVE 關卡仍屬 A3 content
  expansion，日後加入時須沿用同一 Evidence 與 fail-closed 規則。
