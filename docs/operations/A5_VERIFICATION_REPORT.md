# A5 verification report — 2026-08-09

## 目前結論

RP-A5 已完成 Arena `SINGLE_REPORT` 端到端切片的研究核心、byte-preserved artifact mirror、
lossless row mirror、normalized typed serving closure、typed API 與 UI／Evidence Drawer 實作；
fresh PostgreSQL／Compose、least-privilege ACL、Shadow scheduler、backup/restore、真實 API／Web
與 A5→A4→A5 rollback drill 均已在私人 staging 實跑。

本 checkpoint 不代表 Data Gate A／B／C 或 Gates D–G 通過。兩筆 exact counter 都只是同一
來源作者的單次勝利回報，因此保存為 `SINGLE_REPORT / D / sample_size=1`；沒有臆造勝率、
沒有提升為 `VERIFIED`。目前 Arena mature defenses＝0、`VERIFIED` rows＝0、
`SINGLE_REPORT` rows＝2。

## Immutable research-core pins

```text
files / CSV / rows          48 / 13 / 356
manifest_sha256             1826c8493d40f71a6d0bb9096f57b92fe4e839d52bddf021b0c51e0186dcbda7
raw/revision_sha256         1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c
semantic_sha256             c77bc9893fa0b442832c1dff0c7c4a1c5e6d63ba9bce27c1c2f8078c5c2511b8
artifact_mirror_sha256      0d369f37cbf734582012e249e0cf48799a274a3d6f3100ac56c9c8388e945444
Evidence→Claim / reverse    111 / 277
```

RP-A2／RP-A3／RP-A4 manifests 仍保留為 immutable rollback checkpoints；A5 沒有覆寫歷史
manifest。上述 artifact mirror 是可攜、可由 research core 重算的 CoreFile／CSV row／edge
摘要，不是 PostgreSQL typed serving materialization digest。

## Instance-specific DB identity

本次 fresh import 的 typed DB materialization SHA-256 為：

```text
39134bf690f4db147ae3bad1d764dc9486815c49a1b40bc836cdfdecb848126f
```

它只識別本次 schema／projection／instance 的 serving materialization；不得當成 portable
research-core pin，也不得與 `artifact_mirror_sha256` 混用。A4 activation 在本次 rollback
drill 觀測到的 materialization 以 `f5d3ae8b…` 開頭，同樣是 instance-specific；完整值由該次
import result、`core_revisions` 與 `materialization_state` 相互核對，不宣稱為固定 portable pin。

## Research core 五命令（已實跑）

`python scripts/check_research_baseline.py` 在乾淨暫存副本實際重現：

```text
PRE_SUITE --write  exit=0  CHECKS=154 FAIL=0 WARN=24
PRE_SUITE          exit=0  CHECKS=154 FAIL=0 WARN=24
OPERATIONAL        exit=0  CHECKS=153 FAIL=0 WARN=23
ARTIFACT_READY     exit=1  CHECKS=156 FAIL=3 WARN=23
MUTATION_TESTS ALL_OK | active_scenarios=103
```

ARTIFACT_READY 的三個 FAIL 恰為 Gate A／B／C；16 個 blocking warnings 保留，其中新增的
`BASELINE-REVIEW` 是 2026-08-09 到期而誠實出現，未直接延後日期。沒有為了讓
測試變綠而降低 Gate 或 Validator 約束。

## 已完成的程式驗證

```text
Python pytest                         205 passed
OpenAPI / TypeScript parity           OPENAPI_CLIENT_PARITY_OK schemas=24
TypeScript typecheck                  exit 0
Next.js production build              exit 0
Mock-stack Playwright                 20 passed
Real-stack Playwright                 20 passed
```

Mock 與 real-stack E2E 均覆蓋桌面／行動版關鍵路徑；Arena exact defense 查詢、完整 5＋5、
`SINGLE_REPORT` 警告與 Evidence Drawer 在真實 API／Web stack 亦已實測。這些結果是本次
私人 staging 的 deployment evidence，不等於 Gates D–G 通過。

## Fresh Compose 與 typed import（已實跑）

V0006 fresh import 後的 canonical row counts：

```text
stages / teams / team_members              3 / 10 / 50
characters / evidence / claims             35 / 64 / 62
operation_timelines / timeline_steps       15 / 37
arena_defenses / arena_defense_members     1 / 5
arena_counters / arena_counter_members     2 / 10
arena_counter_evidence / claims            4 / 4
```

API readiness、Web、Evidence Drawer 與 real-stack E2E 均在這份 materialization 上通過；
Arena 資料庫的 1 defense／2 counters 是 read mirror row count，不得誤稱為成熟攻略：研究核心
仍是 0 mature defenses／0 `VERIFIED` rows／2 `SINGLE_REPORT` rows。

## ACL、scheduler 與 automation safety（已實跑）

```text
least-privilege matrix     matrix_checks=312 actual_denials=20 allowed_smokes=8
scheduler shadow smoke     SCHEDULER_SHADOW_SMOKE_OK
```

Scheduler smoke 維持 Shadow Mode／no-publish 邊界；它證明安全控制與重複執行行為，不代表
Automation Gate F 通過或允許自動發布 canonical data。

## Backup／restore 與 downgrade guard（已實跑）

本次通過 restore smoke 且保留的 verified backup：

```text
path       .runtime/backups/pcr_tw_20260809115858_dca6bb.dump
sha256     511c36816cd5ff3a3551f78e096c8017b973e3dbc09e34c6844b88d8b68cefb9
bytes      1541877
```

Restore 結果包含 4 revisions／11 activations 的 revision history、history digest、完整
48 files／13 CSV／356 rows round-trip、DB guards、API readiness、Web Evidence Drawer，以及
非空 Arena 六表下的 V0006 downgrade rejection。`ARENA_DOWNGRADE_BLOCKED_OK` 後 Alembic、
active revision、borrowed tri-state 與 Arena rows 均保持 transactionally unchanged。

## A5→A4→A5 rollback drill（已實跑）

Default recovery path 完成下列 chronology：

```text
A5 origin      activation_sequence=9   epoch=7481
A4 activated   activation_sequence=10  epoch=8095  materialization=f5d3ae8b…
A5 restored    revision=1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c
final          A5_RESTORED_OK + A5_SERVICES_READY_OK + A5_A4_ROLLBACK_DRILL_OK
```

A4 的六個 Arena 表在 downgrade 前皆為 0，降至 V0005 後表已不存在；重新升級／匯入 A5
後，portable identity、instance materialization、完整 counts 與 API readiness 均重新核對。

`-LeaveAtA4` 是會刻意停留 V0005 且保持服務 quiesced 的 optional destructive boundary；本輪
狀態為 **NOT_RUN**。它不是本次 release blocker，也不得由 default restore drill 推論已驗證。

## Gate 狀態與未宣稱事項

| 項目 | 狀態 | 說明 |
|---|---|---|
| Data Gates A／B／C | **NOT PASS** | ARTIFACT_READY 恰有這三個 FAIL |
| Application／Automation／Production Gates D–G | **NOT PASS** | operational evidence 完成不等於產品 Gate 驗收 |
| Arena mature defenses／VERIFIED rows | **0／0** | 兩筆 counter 均為 `SINGLE_REPORT` |
| `-LeaveAtA4` optional destructive boundary | **NOT_RUN** | 非 release blocker；只可在 disposable staging 另行演練 |

## Rollback point 與停止條件

- 回退目標是完整 `rp-a4-1` checkpoint，不是只拿 manifest 或手工重建資料。
- A4 activation 必須精確符合 manifest、raw revision、48 files、325 CSV rows、
  本次 instance 內相互一致的 materialization SHA-256，且六個 Arena 表全為 0，才可由
  V0006 降至 V0005。A4 DB digest 不是 portable pin。
- 預設 drill 必須重新 upgrade/import A5，驗證 1 defense／2 counters 與 readiness 才可恢復
  服務；否則服務保持 quiesced。
- backup-first 流程、固定 pins 與完整停止條件見
  [`A5_ROLLBACK_RUNBOOK.md`](A5_ROLLBACK_RUNBOOK.md)。

本報告只記錄上述實際輸出；不以 operational smoke 取代 Data／Application／Automation／
Production Gate 驗收，也不把未執行的 `-LeaveAtA4` 標成 PASS。
