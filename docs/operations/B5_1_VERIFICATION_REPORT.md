# RP-B5-1 Gacha 垂直切片候選驗證報告

日期：2026-08-10（Asia/Taipei）

RP-B5-1 將 2026-08-09 Freshness 與 Gacha research rows 固化為新的 current
research-core checkpoint，並把五筆 timeline／四筆 community source 完成
source→V0007／materialization v4→API→Web／Evidence Drawer 的第一個真實垂直切片。
`research_core_rp_a5_manifest.sha256` 與 RP-A5 `SnapshotContract` 完全保留，沒有覆寫或
移動歷史 pin。本文件在私人 CI 完成前是 release candidate 證據，不宣稱 tag 已封存。

## Portable identities

```text
manifest_sha256      e74814d6433ee327611f10322937bdfa9687b9887f139ba6e6158a291dd12989
raw/revision_sha256  d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d
semantic_sha256      a7467a838c2a9cfdfe48bda4a3b158fb374dd023caa3478a84c07678532ea9f4
files / CSV / rows   48 / 13 / 376
Evidence→Claim       120  sha256=a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af
Claim→Evidence       298  sha256=24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c
```

`artifact_mirror_sha256=b0ac64c328d7fdb77f3e3cf88447287ee560bb415d4a4433c48361fb5857dacd`
是本次 loader 實際重算的 diagnostic；它不是 portable source pin，也沒有硬編碼進
`SnapshotContract`、部署參數或 rollback allowlist。

CSV rows 的實際分布：

```text
17=0, 18=35, 24=3, 25=10, 26=15, 27=37, 39=2,
41=5, 45=4, 46=6, 47=0, 92=122, 93=137
```

## Generator 與 loader

`python scripts/generate_research_manifest.py --output <new-tree-out-path>` 實際輸出：

```text
status=RESEARCH_MANIFEST_CANDIDATE_READY
manifest_sha256=e74814d6433ee327611f10322937bdfa9687b9887f139ba6e6158a291dd12989
raw_tree_sha256=d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d
semantic_tree_sha256=a7467a838c2a9cfdfe48bda4a3b158fb374dd023caa3478a84c07678532ea9f4
file_count=48 csv_file_count=13 csv_row_count=376
evidence_to_claim_count=120 claim_to_evidence_count=298
```

新產生的 tree-out candidate 與
`scripts/research_core_rp_b5_1_manifest.sha256` 逐 byte 相同；預設
`load_research_core_snapshot()` 亦以同一 manifest、raw、semantic 與 directed-edge
identities 成功載入。

## Research baseline wrapper

`python scripts/check_research_baseline.py` 在乾淨暫存副本實際依序執行：

```text
PRE_SUITE --write  exit=0  CHECKS=156 FAIL=0 WARN=22  blk=14 canonical=Y
PRE_SUITE          exit=0  CHECKS=156 FAIL=0 WARN=22  blk=14 canonical=Y
OPERATIONAL        exit=0  CHECKS=155 FAIL=0 WARN=21  blk=14 canonical=N
ARTIFACT_READY     exit=1  CHECKS=158 FAIL=3 WARN=21  blk=14 canonical=N
MUTATION           exit=0  MUTATION_TESTS ALL_OK active_scenarios=106
RESEARCH_BASELINE_OK files=48 mutation_scenarios=106
```

ARTIFACT_READY 的三個 FAIL 僅為 Gate A、Gate B、Gate C；沒有額外 FAIL。

## Focused pin／replay tests

以下 focused suite 實跑通過：

```text
python -m pytest -q \
  tests/importer/test_research_core_round_trip.py \
  tests/importer/test_import_pve_source_verification.py

31 passed
```

測試同時證明：

- RP-B5-1 是 current `DEFAULT_MANIFEST`／`EXPECTED_MANIFEST_SHA256`／
  `CURRENT_SNAPSHOT_CONTRACT`。
- RP-A5 與 RP-A4 manifest digest／structural contract 保持 immutable。
- RP-A5 已加入 approved historical rollback allowlist；未知 manifest 仍 fail closed。
- API image 同時攜帶 current B5-1 與 A5／A4／A3／A2 rollback manifests。

## Canonical Gacha truth

本切片的 canonical／typed rows 為：

```text
timeline events                 5
timeline Evidence relations     10
timeline Claim relations        8
community sources               4
event→community relations       0
maturity                        MATURE=2 / RESEARCH=3
community update status         CHECKED=2 / STALE=2
```

已知限定身分只接受 direct Claim／Evidence closure：

```text
シェフィ（ヴァードラッヘ）  YES      CLM-SHEFI-POOL
ルイズマリー（サマー）       YES      CLM-LUISE-DATE
フブキ（サマー）              YES      CLM-JP-FUBUKI-DATE
ヴァンピィ（サマー）          UNKNOWN  null
ティア                         UNKNOWN  null
```

每個已知 `limited_claim_id` 都是同列 ACTIVE／JP／gacha／SOURCE_FACT／A Claim，並由
同列 relation 直接閉合 ACTIVE／JP／OFFICIAL／A Evidence。池名、社群翻譯與自由文字都
不能替代這個 closure。五筆 `tw_name` 目前全為 `null`；UI 顯示台服官方名稱待公告，不自行
翻譯。三筆 RESEARCH 的抽取價值欄與 `relative_priority` 維持 `NOT_EVALUATED`，頁面不帶
個人寶石、roster／owned、MAIN／ALT 或帳號專屬推薦。

## Application／DB closure

- Alembic current：`v0007_gacha_timeline_slice`。
- Materialization schema／table set：version 4／23 張 typed serving tables。
- 新增五張 Gacha typed tables；Importer 在單一 transaction 驗證 Evidence／Claim／
  community relations、限定身分 direct provenance 與 unknown/null shape。
- 唯讀 API：`GET /api/v1/gacha/timeline`、
  `GET /api/v1/gacha/community-sources`；沒有 Gacha write endpoint。
- `/gacha` 使用 typed client 顯示 timeline、community freshness、限定依據與 Evidence
  Drawer。Timeline envelope 的完整 freshness／confidence closure 尚未 typed 化，因此
  `verified_at=null`、`stale_status=UNKNOWN`、`confidence=UNKNOWN`，不以單列日期冒充整體。
- V0007 downgrade 只接受 fresh empty DB，或 active、SUCCEEDED、pointer／digest／18-table
  manifest 精確一致的 v3 projection 且五張 Gacha 表為空；active v4 即使手動清空 rows
  仍 fail closed。

本機 fresh import 的 serving counts：

```text
stages=3 teams=10 team_members=50 characters=35 evidence=73 claims=69
operation_timelines=15 operation_steps=37
arena_defenses=1 arena_defense_members=5 arena_counters=2
arena_counter_members=10 arena_counter_evidence=4 arena_counter_claims=4
gacha_events=5 gacha_evidence=10 gacha_claims=8
gacha_community_sources=4 gacha_community_links=0
```

## Test matrix

| 驗證 | 最新工作樹實際結果 |
|---|---|
| Full Python `tests apps/scheduler/tests` | 320 passed；exit 0；wall 78.1s |
| API full suite | 81 passed |
| DB／Importer／ACL focused | 137 passed |
| Backup／rollback／ACL operations focused | 25 passed |
| OpenAPI／typed client | `OPENAPI_CLIENT_PARITY_OK schemas=28` |
| Web typecheck | PASS |
| Next.js 16.3 production build | PASS |
| Playwright mock desktop／mobile | 26 passed |
| Playwright real-stack desktop／mobile | 26 passed |
| PowerShell backup／rollback AST | PASS |

`python scripts/check_application_data_parity.py --run-round-trip` 實際輸出
`APPLICATION_DATA_PARITY_STRUCTURAL_OK` 與 `ROUND_TRIP=ROUND_TRIP_OK`，並誠實回報
`DATA_GATE_A/B/C=FAIL`、`APPLICATION_GATE_D_STATUS=BLOCKED_BY_DATA_GATES`。這個本機命令
沒有執行 runtime ACL／unique-writer／admin authorization，所以三項維持 `NOT_RUN`；ACL 的
真實證據來自下節隔離 PostgreSQL 的專用 verifier，不把兩種證據混寫。

Mock 與 real-stack E2E 均逐筆打開九個 Gacha Evidence Drawer；mock 的 title、URL、locator、
日期、摘要與 limitations 已對齊 canonical 92 ledger，不以改寫文案掩蓋 parity drift。

## Fresh private-stack evidence

本機隔離 stack 的精確 target：

```text
Compose project        pcr-tw-b5-gacha
API image              pcr-tw-platform-api:b5
Scheduler image        pcr-tw-platform-scheduler:b5
API / Web / Scheduler  127.0.0.1:8400 / 3400 / 8481
application version    3.0.0-b5
```

API readiness 實際為 `status=ok / database=ok / fixture=imported`；Web `/gacha` HTTP 200，
scheduler 為 disabled＋Shadow Mode，`canonical_write_capable=false`。以下 smoke 均實跑成功：

```text
ROUND_TRIP_OK files=48 csv=13 rows=376 evidence_to_claim=120 claim_to_evidence=298
REPEATABLE_READ_CONSISTENCY_OK
ARTIFACT_FINALIZE_LOCK_OK
CACHE_EPOCH_FAIL_CLOSED_OK
SCHEDULER_SHADOW_SMOKE_OK first=SHADOW_NOOP second=DUPLICATE_SKIPPED
DB_PRIVILEGES_OK matrix_checks=651 actual_denials=23 allowed_smokes=10
```

權限矩陣為 31 tables × 3 runtime roles × 7 PostgreSQL table privileges；除 SELECT／DML
契約外，也逐項驗證 `TRUNCATE`／`REFERENCES`／`TRIGGER`，包含 API 對 Gacha 表的真實
TRUNCATE denial。這些是一次 staging 證據，不等於 14 天 Shadow 或 Gate F PASS。

## Backup／restore evidence

成功 receipt：

```text
path                  .runtime/backups/pcr_tw_20260809165808_3f8843.dump
sha256                2aee3cf109bfcc14007ef3a963eaa4da1b1055ce1665a013488002235e63a4f7
bytes                 557866
source_import_run     2fccc21a-da78-4114-902a-611e3bb87302
source_materialization 74bb5ad349f9f18a6511c5e8317ac2a029ab58ea8051ac5caf4d4c0ca6461b05
source_state_epoch    1150
history_sha256        44053f47410f72c2b3a6dba61b83cd830011a62cf639ea10eca9d6b20611be9e
history               revisions=1 / activations=1
```

成功 markers：

```text
BACKUP_ARTIFACT_VERIFIED
RESTORED_HISTORY_DIGEST_OK
RESTORED_ROUND_TRIP_OK
RESTORED_API_READINESS_OK
RESTORED_WEB_EVIDENCE_OK gacha_events=5 gacha_ssr=ok
GACHA_DOWNGRADE_BLOCKED_OK gacha_rows=0
BACKUP_RESTORE_OK
BACKUP_RESTORE_VERIFIED
```

`source_materialization` 與 epoch 是這個 PostgreSQL instance 的 typed serving closure
證據，不是 portable research pin。Restore 與 destructive empty-Gacha downgrade probe
使用不同 disposable database；probe cleanup 成功後才會輸出 verified receipt。

## B5→A5→B5 rollback evidence

RP-A5 來源由 immutable `rp-a5-2` 匯出並逐 pin 驗證；演練使用上節 verified backup，沒有
只 checkout 舊 tag。實際 chronology：

```text
seq=1 kind=IMPORT      from=null       to=d117be19… epoch=1150
seq=2 kind=ROLLBACK    from=d117be19…  to=1962881f… epoch=2244
seq=3 kind=REACTIVATE  from=1962881f…  to=d117be19… epoch=2978
```

```text
A5 revision             1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c
A5 materialization      339b415dd2d9725f7cd7dd815b7269f1b3bf1318a72d19e520ba4d547d563334
final B5 revision       d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d
final B5 import run     2fccc21a-da78-4114-902a-611e3bb87302
final B5 materialization 74bb5ad349f9f18a6511c5e8317ac2a029ab58ea8051ac5caf4d4c0ca6461b05
final state epoch       2978
```

成功順序是：B5 identity／backup → pinned A5 v3 activation（Gacha rows=0）→
V0007→V0006 → V0006→V0007 → role reprovision → 原 B5 reactivation → ACL／API／Web／
scheduler readiness。成功 markers 包含：

```text
VERIFIED_BACKUP_INPUT_OK
B5_ORIGIN_VERIFIED_OK
A5_DATA_ROLLBACK_OK
B5_A5_SCHEMA_ROLLBACK_OK
B5_RESTORED_OK
B5_PUBLIC_READINESS_OK
B5_SERVICES_READY_OK
B5_A5_ROLLBACK_DRILL_OK
```

腳本沒有 `LeaveAtA5`；任何 identity、chronology、epoch、實際 port、backup SHA、服務 readiness
或 ACL 無法證明時，必須復原到已驗 B5，否則維持 services quiesced 並停止人工判讀。

## Gate status 與 release boundary

```text
Data Gate A   NOT PASS (41 acceptance executions = 0/41)
Data Gate B   NOT PASS
Data Gate C   NOT PASS
Gate D        BLOCKED_BY_DATA_GATES
Gate E        NOT PASS
Gate F        NOT PASS
Gate G        NOT PASS
Timeline      MATURE 2/6
Community     CHECKED 2/2
Blocking warnings 14
```

Community 2/2 與 Gacha walking slice 不會補出 Arena、P-Arena、PVE、Timeline 或 Gate A 的
其餘缺口。`17_TEST_EXECUTION_LOG.csv` 仍是 header-only；在沒有 response artifact／人工 reviewer
與 P-Arena／Gacha 內容前，不會語法性填入 41 個假 PASS。

私人 GitHub CI／commit／annotated tag：**PENDING**。只有 branch 的最終 private Actions run
全綠後，才可建立新的 immutable `rp-b5-1`；既有 `rp-a5-*`／`rp-b3-d0-1` tags 不移動。
