# I0 Evidence→Claim closure 驗證報告 — 2026-08-08

## 結論

I0 已完成並可作為下一階段 A2＋B2 的回滾點。原先 7 筆
Evidence→Claim 懸空引用已逐筆裁決：6 筆改綁既有 canonical Claim，`ev008`
新增 `CLM-TW-DEEP-A8`。Evidence 正文、來源層級、信心、Gate、PVE 隊伍數與
lifecycle 均未提高或改寫。

本輪新增的 ST86 只檢查「92 Evidence 已宣告的 `claim_id` 必須存在於 93」；
沒有把 Claim 反向列舉所有 Evidence 強制成雙向完全相等，也沒有降低既有
Validator／Gate 約束。M57 以單一缺失 Claim 變異確認 ST86 可獨立命中。

## Research-core 實際輸出

以下由 `python scripts/check_research_baseline.py` 在乾淨暫存副本依序實跑：

```text
PRE_SUITE --write  exit=0  CHECKS=113 FAIL=0 WARN=16
PRE_SUITE          exit=0  CHECKS=113 FAIL=0 WARN=16
OPERATIONAL        exit=0  CHECKS=112 FAIL=0 WARN=15
ARTIFACT_READY     exit=1  CHECKS=115 FAIL=3 WARN=15
```

ARTIFACT_READY 的三個 FAIL 仍恰為 Gate A、Gate B、Gate C：

```text
FAIL - ST55：ARTIFACT_READY 需 Gate A
FAIL - ST55：ARTIFACT_READY 需 Gate B
FAIL - ST67(Gate)：ARTIFACT_READY 需 Gate C（含 blocking_c=0）
```

```text
MUTATION_TESTS ALL_OK | active_scenarios=55
RESEARCH_BASELINE_OK | files=46 | mutation_scenarios=55 | manifest_sha256=80e6be16fbfbbef1c676def920348aa006d6608a0900f2e62ba4d5cac2d62bcb
```

衍生統計：Evidence 75 列不變；Claim 84→85；A confidence 49→50；
SOURCE_FACT 56→57。Gate A／B／C、blocking warning 7、WARN 數量均不變。

## 應用回歸

```text
Python／API／Importer／Scheduler: 41 passed
OpenAPI／TypeScript parity:       OPENAPI_CLIENT_PARITY_OK schemas=11
TypeScript typecheck:             exit 0
Next.js production build:         exit 0
Real Compose Playwright:          8 passed（desktop＋mobile）
```

## 真實 PostgreSQL／Compose 驗證

- 使用隔離的 `pcr-tw-i0-final` project 與全新 read-mirror volume 建置；較早的
  `pcr-tw-i0` 僅為 EOL 修正前的稽核，不支撐下列最終 fingerprint。
- API、Web、PostgreSQL、Scheduler 全部 healthy。
- Importer 接受的新 fixture SHA-256：
  `22ead5af3c2036f1e6ef99a5511d1763419fc4400a558e3706fc30824f563809`。
- Materialized counts 未被 I0 非選取 Claim 影響：stage／teams／members／characters／
  evidence／claims = `1/3/15/8/18/13`。
- API 回報 Gate A／B／C 仍為 `false`。
- PostgreSQL least-privilege：`matrix_checks=156 actual_denials=6 allowed_smokes=3`。
- Scheduler：`SHADOW_NOOP → DUPLICATE_SKIPPED`，
  `enabled=false`、`shadow_mode=true`、`canonical_write_capable=false`。
- Backup → 空資料庫 → restore 驗證 14 tables、Alembic
  `v0001_b0_read_mirror`、API readiness、PROVISIONAL 三隊、`ev052` 與 Web Evidence
  proxy，輸出 `BACKUP_RESTORE_OK`。

## 清理與回滾

所有 I0 容器已停止，測試 dump 與暫存 env 檔已移除。未刪除可重建的
`pcr-tw-i0-final_pg_data` 最終 checkpoint volume；較早的 pre-EOL 稽核 volume
`pcr-tw-i0_pg_data` 亦保留但不代表最終 fingerprint。兩者都不是 canonical data，
canonical SSOT 仍是 46 檔 research core。
