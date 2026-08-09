# B3／D0 exact picker 與保守 Metadata 驗證報告

- 日期：2026-08-09
- checkpoint：`rp-b3-d0-1`
- 前一安全回滾點：`rp-a5-2`
- schema：V0006，無 migration

## 結論

本切片完成五角色 Battle Arena exact picker、AVAILABLE 台服官方名稱 Evidence closure、
required-but-conservative Strategy Metadata、OpenAPI／typed client parity，以及可執行的
Application/Data structural verifier。真實 A5 PostgreSQL／API／Web stack 已重建並通過
desktop/mobile E2E、ACL、Shadow scheduler、backup／restore 與 A5→A4→A5 演練。

這不代表 Gate D 通過。Data Gate A／B／C 仍為 `False`，verifier 精確回報
`APPLICATION_GATE_D_STATUS=BLOCKED_BY_DATA_GATES`；runtime ACL、unique-writer 與 admin
authorization 若未在同一次 verifier 執行，仍明列 `NOT_RUN`。Arena 仍是 0 mature
defenses／0 VERIFIED rows／2 SINGLE_REPORT rows，Similar 未啟用。

## Research 與不可升級結論

本輪實際開啟既有 May-25 巴哈正文與兩張 WIN 原圖，並對兩張原圖執行反向圖片 discovery。
兩個 exact counter 都來自同一 Bahamut 討論串與同一回覆者；沒有找到另一個可實際開啟、
明示 TW 同環境、完整 exact 5v5、明確 WIN 且 hostname 獨立的正文。另實際開啟的影片候選
沒有同時閉合 TW、defense 5、attack 5 與 WIN。

因此本輪新增 Evidence＝0；兩列維持 `SINGLE_REPORT`、confidence D、sample/source/wins＝1，
沒有修改 research core、manifest 或 pins。搜尋摘要與反向圖片結果只作 discovery，不作
Evidence；中國服／B服結果全部排除。

## Portable research identity 與 instance serving digest

```text
manifest sha256       1826c8493d40f71a6d0bb9096f57b92fe4e839d52bddf021b0c51e0186dcbda7
raw/revision sha256   1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c
semantic sha256       c77bc9893fa0b442832c1dff0c7c4a1c5e6d63ba9bce27c1c2f8078c5c2511b8
artifact mirror       0d369f37cbf734582012e249e0cf48799a274a3d6f3100ac56c9c8388e945444
files / CSV / rows    48 / 13 / 356
Evidence→Claim        111  sha256=84fea5ed4095dfcbb98cb52816c2e8a7a3d9fd1acd9ef225541ba27b8bcc192e
Claim→Evidence        277  sha256=b0fefe463e3968266ed8a8378fd8b7f5c94817a4dd548f920facf7c182fa0e64
```

本次 A5 instance typed serving materialization：
`39134bf690f4db147ae3bad1d764dc9486815c49a1b40bc836cdfdecb848126f`。
它不是 portable research pin，不得拿來取代 manifest／raw／semantic identity。

## Research 五命令（實跑）

```text
PRE_SUITE --write   exit=0  CHECKS=154 FAIL=0 WARN=24
PRE_SUITE           exit=0  CHECKS=154 FAIL=0 WARN=24
OPERATIONAL         exit=0  CHECKS=153 FAIL=0 WARN=23
ARTIFACT_READY      exit=1  CHECKS=156 FAIL=3 WARN=23
MUTATION            exit=0  ALL_OK active_scenarios=103
```

ARTIFACT_READY 的三個 FAIL 恰為 Gate A、Gate B、Gate C；沒有新增其他 FAIL。

## Application／Web 驗證（實跑）

```text
Python full suite                 239 passed
rollback focused                  15 passed；PowerShell parse OK
OpenAPI/client contract           OPENAPI_CLIENT_PARITY_OK schemas=26
TypeScript typecheck              exit 0
Next.js 16.3 production build     exit 0；3/3 static pages
Playwright mock desktop/mobile    24 passed
Playwright real desktop/mobile    24 passed
post-rollback PVP real E2E        6 passed
```

真實 API smoke：

```text
readiness                         ok
AVAILABLE picker characters       35
character meta                    server=TW verified_at=null stale=UNKNOWN confidence=UNKNOWN
exact defense result              2 SINGLE_REPORT rows
exact warnings                    NO_VERIFIED_COUNTER,SINGLE_REPORT_REFERENCE_ONLY
four-of-five result               0 rows；NO_EXACT_COUNTER,NO_VERIFIED_COUNTER
```

所有 AVAILABLE picker 角色都必須有儲存的台服官方名稱，且自身
`source_evidence_ids` 至少引用一筆實際存在的 `ACTIVE/TW/OFFICIAL/A` Evidence。API 使用
固定兩次批次查詢；Importer 對所有 AVAILABLE 角色使用同一 predicate。community、inactive、
missing Evidence 與 placeholder name 均有負向測試。

Counter envelope 只聚合可機械證明的 server、environment 與 typed Evidence／Claim IDs；在
完整 defense＋Claim＋Evidence freshness/confidence closure 尚未 typed 前，
`verified_at=null`、`stale_status=UNKNOWN`、`confidence=UNKNOWN`。

## D0 structural verifier（實跑）

```text
APPLICATION_DATA_PARITY_STRUCTURAL_OK
DATA_GATE_A=FAIL
DATA_GATE_B=FAIL
DATA_GATE_C=FAIL
ROUND_TRIP=ROUND_TRIP_OK
RUNTIME_ACL=NOT_RUN
UNIQUE_WRITER_RUNTIME=NOT_RUN
ADMIN_AUTHORIZATION=NOT_RUN
APPLICATION_GATE_D_STATUS=BLOCKED_BY_DATA_GATES
```

Verifier 會檢查 public strategy envelope、required ResponseMeta 欄位、禁止的 write methods，
以及 `/pvp/characters`＝`list[PvpCharacterData]`、`/pvp/counters`＝
`list[ArenaCounterData]` 的精確 response binding。把 characters 錯接成 Baseline envelope 的
mutation 現在會 fail closed。

## Runtime safety、backup 與 rollback（實跑）

```text
least privilege             matrix_checks=312 actual_denials=20 allowed_smokes=8
scheduler shadow            SHADOW_NOOP → DUPLICATE_SKIPPED；canonical_write_capable=false
round trip                  48 files / 13 CSV / 356 rows；deterministic exports
snapshot consistency        REPEATABLE_READ_CONSISTENCY_OK
cache epoch                 CACHE_EPOCH_FAIL_CLOSED_OK
artifact lock               ARTIFACT_FINALIZE_LOCK_OK
```

本輪 verified backup：

```text
path       .runtime/backups/pcr_tw_20260809135027_dc304a.dump
sha256     c4d89d9ac7a9554b7ce2fc08c749dbd6a379f4f02863559819913c3d527f59fc
bytes      1541961
restore    BACKUP_RESTORE_OK；4 revisions／11 activations；ARENA_DOWNGRADE_BLOCKED_OK
```

第一次 rollback preflight 在 quiesce 前安全停止，重現到 serving `state_epoch=8776` 大於
latest activation audit epoch `8767`。Consistency/cache smoke 會以 typed DML＋cleanup 合法
推進 state epoch，但不新增 activation；原腳本錯把兩者要求相等。修正後分開驗證：
`0 < activation_epoch <= state_epoch`、active A5 identity 精確相符，而且新 rollback epoch 必須
大於起點 state epoch；quiesce 前先由目標 Compose project 解析實際 API port，再要求 API
readiness 依目前 epoch 重算 typed materialization 並回 `database=ok／fixture=imported`，最後
重讀 epoch 確認檢查期間未變，避免錯 stack 或同 row-count 未清理 drift 被接受。

完整重跑結果：

```text
origin A5   seq=15 activation_epoch=11348 state_epoch=11348；actual-port readiness OK
A4 rollback seq=16 epoch=11962 materialization=f5d3ae8b…
A5 restore  seq=17 epoch=12634 revision=1962881f… materialization=39134bf6…
markers     A5_ORIGIN_READINESS_OK / A5_RESTORED_OK / A5_SERVICES_READY_OK /
            A5_A4_ROLLBACK_DRILL_OK
```

`-LeaveAtA4` 仍是 optional destructive boundary，本輪 **NOT_RUN**，不是 release blocker。

## Gate 與回滾狀態

| 項目 | 狀態 |
|---|---|
| Data Gates A／B／C | NOT PASS |
| Application Gate D | BLOCKED_BY_DATA_GATES／NOT PASS |
| Application Gate E | NOT PASS；P-Arena、Gacha 與完整搜尋仍缺 |
| Automation Gate F | NOT PASS；只有 inert Shadow safety skeleton，無 14 日觀測 |
| Production Gate G | NOT PASS |
| Arena mature defenses／VERIFIED rows | 0／0 |
| 回滾點 | `rp-a5-2`；V0006 不變 |

任何未實際取得正文、非 TW／environment 不精確、缺完整 5v5＋WIN、同 hostname 重貼，或
只有搜尋摘要的候選，均不得升為 VERIFIED。下一個 Gate-bearing content slice 仍需為同一 TW
exact defense 的每支 counter 補足可機械驗證的獨立 HTTPS 多來源 closure；找不到就維持實際 N。
