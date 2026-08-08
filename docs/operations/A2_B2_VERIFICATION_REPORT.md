# A2＋B2 operation timeline 驗證報告 — 2026-08-08

## 結論

A2＋B2 已完成一個真實的紅焰深域 8-10 source→file SSOT→PostgreSQL→API→Web
垂直切片。操作軸以來源分離保存，不跨來源拼接；來源沒有提供的時間、戰鬥長度、
容錯與錯位後果維持 UNKNOWN。TM-F810-02 僅揭露 `PARTIAL 1/4`，其餘三個來源仍
明確標為 gap，沒有把局部 GameWith 操作軸冒充成四來源共識。

本里程碑是可部署的本機／私人 staging，不代表 Data Gate A／B／C 或應用、
自動化、Production Gates D–G 已通過。

## Research-core 實際輸出

`python scripts/check_research_baseline.py` 在乾淨暫存副本依序實跑：

```text
PRE_SUITE --write  exit=0  CHECKS=128 FAIL=0 WARN=16
PRE_SUITE          exit=0  CHECKS=128 FAIL=0 WARN=16
OPERATIONAL        exit=0  CHECKS=127 FAIL=0 WARN=15
ARTIFACT_READY     exit=1  CHECKS=130 FAIL=3 WARN=15
```

ARTIFACT_READY 的三個 FAIL 仍恰為 Gate A、Gate B、Gate C；沒有新增 FAIL。

```text
MUTATION_TESTS ALL_OK | active_scenarios=66
RESEARCH_BASELINE_OK | files=48 | mutation_scenarios=66 | manifest_sha256=3a242b521d830af12ce8559d88b733068fb1b6cb503219395d2986b89e5dc352
```

## 應用回歸

```text
Python／API／Importer／Scheduler: 56 passed
OpenAPI／TypeScript parity:       OPENAPI_CLIENT_PARITY_OK schemas=16
TypeScript typecheck:             exit 0
Next.js production build:         exit 0
Mock Playwright desktop/mobile:   12 passed
pip check:                        No broken requirements found
```

兩次獨立 Maintainer 複驗均批准：後端資料閉包、migration、冪等與 fail-closed
邊界無 blocker；Web 的逐步 locator、focus trap、mock closure 與 16-schema parity
無剩餘 blocker。

## 真實 PostgreSQL／Compose 驗證

- 隔離 Compose project `pcr-tw-a2b2-final` 的 PostgreSQL、API、Web、Scheduler
  全部 healthy，Alembic 由 `v0001_b0_read_mirror` 升至
  `v0002_operation_timelines`。
- Fixture SHA-256：
  `11712d3eede5c3a0f9b5e2c42e92f33e815ecc02f1904b717ffa8d002ea04e69`。
- Materialized counts：stage／teams／members／characters／evidence／claims／
  timelines／steps = `1/3/15/8/18/13/8/14`。
- 完全相同 fixture 重播回傳 `created=false`，fingerprint 與各表 counts 不變。
- TM-F810-01=`SOURCE_GAP 0/3`、TM-F810-02=`PARTIAL 1/4`、
  TM-F810-03=`SOURCE_GAP 0/1`；TM-F810-02 的 14 個步驟只屬於 ev073 來源軸。
- PostgreSQL least privilege：
  `matrix_checks=180 actual_denials=6 allowed_smokes=3`。
- Scheduler：`SHADOW_NOOP → DUPLICATE_SKIPPED`，且
  `canonical_write_capable=false`。
- Backup → 空資料庫 → restore 驗證 16 tables、Alembic
  `v0002_operation_timelines`、8 timelines、14 steps、API readiness 與 Web Evidence。

## Serving drift 與真實瀏覽器驗收

在主 read mirror 暫時移除 `AX-F810-01-EV050` 後，API readiness 實際回傳
`503 FIXTURE_DRIFT reason=row_count_drift`；精確還原該列後恢復 healthy，沒有降低
closure 約束。

真實 production Web 以桌面 1440×1000 與 Pixel 7 尺寸驗收：

- 14 個步驟完整呈現，前四步保持「時間未確認」。
- Evidence Drawer 同時顯示登錄 locator 與本次逐步 locator
  `2025年9月魔法半自動／手順1`。
- Shift+Tab 焦點留在 dialog；Escape 關閉後回到原 trigger。
- 桌面與手機均無水平溢位；瀏覽器 console 的 warn／error 為 0。

## 回滾與保留資料

- Research A2 回滾點：`rp-a2-2`。
- A2＋B2 完整垂直切片回滾點：`rp-a2-b2-1`。
- Compose 容器於驗證後停止；不刪除可重建的
  `pcr-tw-a2b2-final_pg_data` checkpoint volume。
- canonical SSOT 仍是 48 檔 research core；PostgreSQL 永遠只是可重建 read mirror。
