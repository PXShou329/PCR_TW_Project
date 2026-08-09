# RP-A6-0 Princess Arena Gate correctness 候選驗證報告

日期：2026-08-10（Asia/Taipei）

RP-A6-0 修正 Princess Arena 成熟案例的 Gate correctness，並把新的 research-core
generation 設為 current snapshot contract。這不是 P-Arena content expansion 或 Planner
垂直切片：`47_PRINCESS_ARENA_CASE_REGISTRY.csv` 仍為 0 rows／0 mature cases，尚未新增
P-Arena typed tables、API、UI 或 Planner；Alembic 仍為 V0007，materialization 仍為 v4／
23 張 typed serving tables。

本文件目前是 release candidate 證據。私人 CI、候選 commit 與 annotated `rp-a6-0` tag
尚未完成，因此不宣稱 tag 已封存。Data Gates A／B／C、Application Gates D／E、Automation
Gate F 與 Production Gate G 均未通過。

## Portable source identities

```text
manifest_sha256      fbcac9cb9aadcd1569f881469189dc791c68a4a329637cc9db2c0d7263d68ed1
raw/revision_sha256  3f5e738a6a7f0463583b38d0fc2ca1ae35bdc563f3815cf436dfc10913764d97
semantic_sha256      82495781cca66b9ca3fc221e609a3cb6c06ebaa823f7a8613c9d5d1d01d9e1ee
files / CSV / rows   48 / 13 / 376
Evidence→Claim       120  sha256=a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af
Claim→Evidence       298  sha256=24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c
```

`artifact_mirror_sha256=e44a9fa38a89a5672d00c0a58d8b8946fecd41e541c08c9733fb3d06fbc1b88a`
是 loader 對 byte artifact／lossless rows／directed edges 的 deterministic diagnostic；它不
取代 manifest／raw／semantic rollback pins，也不是 PostgreSQL typed serving
`materialization_sha256`。

CSV rows 的實際分布：

```text
17=0, 18=35, 24=3, 25=10, 26=15, 27=37, 39=2,
41=5, 45=4, 46=6, 47=0, 92=122, 93=137
```

RP-A6-0 與 RP-B5-1 的 CSV row counts 相同，但 `47` 的 header 從 20 欄擴為 24 欄，且
Validator／Mutation／規範文件 bytes 已改變，因此兩代 manifest／raw／semantic identities
不同。RP-B5-1 保留為 explicit historical contract，不是 current contract 的 alias。

## Princess Arena Gate correctness

`47_PRINCESS_ARENA_CASE_REGISTRY.csv` 新增四個 designated result fields：

```text
team1_result_claim_id
team2_result_claim_id
team3_result_claim_id
case_win_claim_id
```

一列只有在下列 closure 全部成立時才是成熟 P-Arena case：

- `status=VERIFIED`、`server=TW`、相同 `environment_version`、
  `hidden_team_mode=NONE`、`tw_availability_check=PASS`、
  `non_overlap_check=PASS`、`reproducibility=CONFIRMED`。
- 敵我各三隊完整五人；每一側 15 位角色都不重複，且所有角色都在 18 為 `AVAILABLE`。
- 三個隊位各自對到同一台服 environment 的唯一成熟 39 exact result row；每個 child row 的
  `required_upgrade_check` 都必須為 `PASS`。
- 三個 `team*_result_claim_id` 分別保存 exact 單隊結果；另以一個 direct、ACTIVE、TW、
  `parena`、SOURCE_FACT `case_win_claim_id` 保存完整三戰 WIN。三筆單隊勝利不得反推整體 WIN。
- `claim_ids` 精確等於四個 designated Claims，`evidence_ids` 精確等於這四個 Claims 的 direct
  Evidence 聯集；不可夾帶無關合法資料。
- `source_ids` 必須引用 46 中 ACTIVE／TW／未過期的來源，且 hostname 覆蓋 case WIN direct
  Evidence hostname；published／verified chronology 必須成立。
- 同環境、同三隊防守即使同步重排三組配對仍只算一個 case；同一 `case_win_claim_id` 不得
  支撐兩個不同防守案例。

Evidence confidence 全域為 A–E closed vocabulary，但成熟 case WIN direct Evidence 只接受
A–D。D 級完整 case WIN 可計 Gate B，但會精確新增一個 blocking warning 而不能支撐 Gate C；
B／C 才能通過該項 Gate C maturity boundary。

Mutation 新增 M109–M124，包含 label-only shell、錯 module／superseded WIN、不同 environment、
JP 冒充 TW、重排重複、防守來源與日期漂移、child upgrade UNKNOWN、缺完整 WIN、非法
confidence、E 級 case Evidence、WIN Claim 重用、aggregate 夾帶資料、hostname 不覆蓋與
published-after-verified。M116 是一個合法 exact closure 的正向案例。沒有新增 V0008，也沒有
為通過測試降低既有 Gate。

## Research baseline wrapper

`python scripts/check_research_baseline.py` 在乾淨暫存副本實際依序執行：

```text
PRE_SUITE --write  exit=0  CHECKS=166 FAIL=0 WARN=22  blk=14 canonical=Y
PRE_SUITE          exit=0  CHECKS=166 FAIL=0 WARN=22  blk=14 canonical=Y
OPERATIONAL        exit=0  CHECKS=165 FAIL=0 WARN=21  blk=14 canonical=N
ARTIFACT_READY     exit=1  CHECKS=168 FAIL=3 WARN=21  blk=14 canonical=N
MUTATION           exit=0  MUTATION_TESTS ALL_OK active_scenarios=122
RESEARCH_BASELINE_OK files=48 mutation_scenarios=122
```

ARTIFACT_READY 的三個 FAIL 只有 Gate A、Gate B、Gate C；沒有額外 FAIL。Canonical stats
仍是 41 個 public acceptance tests 全部未執行、P-Arena mature rows=0、不同 mature cases=0、
blocking warnings=14。

## Snapshot／Importer replay

- RP-A6-0 是 current `DEFAULT_MANIFEST`／`CURRENT_SNAPSHOT_CONTRACT`；RP-B5-1 保持
  immutable historical full-platform contract。
- checkpoint lineage 固定為 B5=6、A6=7；未知或未核准 manifest 仍 fail closed。
- B5→A6→B5→A6 replay 的 activation kinds 為
  `IMPORT → IMPORT → ROLLBACK → REACTIVATE`；歷史 B5 ImportRun 不會被改寫。
- B5 與 A6 共用 V0007／materialization v4 projection；Gacha closure 保持 timeline events=5、
  community sources=4。

實跑 focused 結果：Importer 115 passed；source／snapshot focused 34 passed。納入最新 2 個
CI serial-order regression tests 後，封版完整 Python 為 340/340 passed，Operations 為
83/83 passed。

## Application／DB closure

- Application version：`3.0.0-a6`；Python distribution：`3.0.0a6`。
- Alembic current：`v0007_gacha_timeline_slice`。
- Materialization schema／table set：version 4／23 張 typed serving tables。
- `47` schema 是 24 fields／0 rows，尚未建立 P-Arena normalized serving closure。
- `python scripts/check_application_data_parity.py --run-round-trip` 實際回報
  `APPLICATION_DATA_PARITY_STRUCTURAL_OK`、`ROUND_TRIP_OK`、Data A／B／C FAIL 與 Gate D
  `BLOCKED_BY_DATA_GATES`。

Fresh A6 typed serving counts：

```text
stages=3 teams=10 team_members=50 characters=35 evidence=73 claims=69
operation_timelines=15 timeline_steps=37
arena_defenses=1 arena_defense_members=5 arena_counters=2
arena_counter_members=10 arena_counter_evidence=4 arena_counter_claims=4
gacha_timeline_events=5 gacha_timeline_evidence=10 gacha_timeline_claims=8
gacha_community_sources=4 gacha_timeline_community_sources=0
```

## Test matrix

| 驗證 | 最新實際結果 |
|---|---|
| Full Python final regression | 340/340 passed |
| Operations focused | 83/83 passed |
| Importer full suite | 115 passed |
| API full suite | 81 passed |
| OpenAPI／typed client | `OPENAPI_CLIENT_PARITY_OK schemas=28` |
| Web typecheck | PASS |
| Next.js 16.3 production build | PASS；8 routes |
| Playwright mock desktop／mobile | 26 passed |
| Playwright real-stack desktop／mobile | 26 passed |

CI／本機 release pipeline 固定串行：base stack → ACL → 五個 verifier（scheduler、round-trip、
consistency、cache epoch、artifact lock）→ backup＋A6→B5→A6 drill → revision-history smoke＋
verify → browser E2E。`verification` profile 不能用 `up` 併發啟動，避免 control rows、typed rows
與 epoch chronology 互相干擾。

## Fresh private-stack evidence

本機隔離 stack 的精確 target：

```text
Compose project        pcr-tw-a6-parena-drill
API image              pcr-tw-platform-api:a6
Scheduler image        pcr-tw-platform-scheduler:a6
API / Web / Scheduler  127.0.0.1:8500 / 3500 / 8581
application version    3.0.0-a6
alembic / projection   V0007 / v4 / 23 tables
```

API、Web、Scheduler 與 DB 全部 healthy；API readiness 為 database=ok／fixture=imported，
Web 與 real-stack desktop/mobile E2E 26 passed。Scheduler 維持 disabled、Shadow Mode、
`canonical_write_capable=false`，Gacha 仍為 events=5／community sources=4。

Rollback drill 完成後、history smokes 完成前的 canonical A6 origin／restore identity：

```text
active revision       3f5e738a6a7f0463583b38d0fc2ca1ae35bdc563f3815cf436dfc10913764d97
active import run     11ef4d2b-f45c-4876-9f80-d1f63a7da553
typed materialization 501d314ad4730003de29ebeb06b336f5e0def61bd16144e221573753d12079b1
drill restore epoch   3062
final state epoch     4965（含後續 revision-history smoke）
```

`typed materialization`、ImportRun 與 epochs 只識別這個 PostgreSQL instance；不得當作
portable research pin。Least-privilege verifier 實際輸出：

```text
DB_PRIVILEGES_OK matrix_checks=651 actual_denials=23 allowed_smokes=10
```

矩陣為 31 tables × 3 runtime roles × 7 PostgreSQL table privileges；這是一輪 staging 證據，
不等於 14 天 Shadow 觀察或 Gate F PASS。

## Backup／restore evidence

通過 restore smoke 且保留供本次 drill 使用的 verified backup：

```text
path                   .runtime/backups/pcr_tw_20260809204424_91fdb6.dump
sha256                 910c5337c27f43aaf912701f8f4474870e6f2125e79b1e53052cb4bc85cfd3df
bytes                  570879
source revision        3f5e738a6a7f0463583b38d0fc2ca1ae35bdc563f3815cf436dfc10913764d97
source import run      11ef4d2b-f45c-4876-9f80-d1f63a7da553
source materialization 501d314ad4730003de29ebeb06b336f5e0def61bd16144e221573753d12079b1
source state epoch     1159
restored history       revisions=1 / activations=1
restored history sha   41956711d60096bf38ca0d8eb15b5fb88a29fa975ec7e037ed2976d98abfbcd9
```

Restore 的 disposable database 與 downgrade probe 均完成 cleanup；成功包含 artifact／history
digest、48 files／13 CSV／376 rows round-trip、DB guards、API／Web Evidence 與 V0007
downgrade fail-closed probe。Backup path 是本機 release evidence，不應 commit dump 本體。

## A6→B5→A6 same-schema rollback evidence

RP-B5-1 checkpoint 由 immutable `rp-b5-1` tag 匯出；archive identity：

```text
path   .runtime/rp-b5-1-a6-checkpoint-exact.tar
sha256 38d069389ade48c374d205a476c5a9a2f85146faae662300a1b64e7139d38ecc
bytes  2385920
```

腳本先在 quiesce 前以 current importer 唯讀驗證完整 B5 tree，再執行 data activation。A6 與
B5 同為 V0007／v4，所以沒有 Alembic migration command。實際 release chronology：

```text
seq=1  IMPORT      null → A6            epoch=1150
seq=2  ROLLBACK    A6 → B5              epoch=2325
seq=3  REACTIVATE  B5 → A6              epoch=3062
```

Intermediate B5 identity：

```text
revision        d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d
import run      ffa63921-db92-40ed-a45c-1fb420b39701
materialization 45b5189c6203765dec6bff40fe2841ec0d3f7e08aff311faae0094b3926dab6b
```

以相同 A6 images 啟動 intermediate services 後，API／Web／scheduler 實際服務 B5 identity、
Gacha 5／4 與 Shadow safety；確認後再次 quiesce，再 re-activate A6。成功 markers 包含：

```text
B5_CHECKPOINT_PREFLIGHT_OK
A6_B5_DATA_ROLLBACK_OK
A6_B5_SAME_SCHEMA_ROLLBACK_OK migration_commands=0
B5_INTERMEDIATE_SERVICES_READY_OK
B5_INTERMEDIATE_SERVICES_STOPPED_OK
A6_RESTORED_OK mode=B5_REACTIVATE
A6_SERVICES_READY_OK chronology=ROLLBACK_REACTIVATE
A6_B5_ROLLBACK_DRILL_OK
```

後續 history smoke 另建立 synthetic revision，驗證 generic rollback audit，不是 portable release
source：

```text
seq=4  IMPORT    A6 → synthetic test revision  epoch=4228
seq=5  ROLLBACK  synthetic test revision → A6  epoch=4965
final revisions/import runs/activations  3 / 3 / 5
final history_sha256 7f8bf9d617071fabd5ff9b3b72a24b001edba6f16ee22fd340f3107be6922806
```

完整操作與 fail-closed recovery boundary 見
[`A6_ROLLBACK_RUNBOOK.md`](A6_ROLLBACK_RUNBOOK.md)。

## Gate status 與 release boundary

```text
Data Gate A   NOT PASS (41 acceptance executions = 0/41)
Data Gate B   NOT PASS
Data Gate C   NOT PASS
Gate D        BLOCKED_BY_DATA_GATES
Gate E        NOT PASS
Gate F        NOT PASS
Gate G        NOT PASS
P-Arena       mature rows=0 / mature cases=0
Blocking warnings 14
```

Validator correctness、healthy stack、ACL、backup／restore、same-schema rollback 與 E2E 都不能
補出成熟 P-Arena content，也不能取代正式 Data／Application／Automation／Production Gate
驗收。私人 GitHub Actions 尚未完成，候選 commit／PR／run 尚未記錄；只有 private workflow
全綠後才可建立新的 annotated `rp-a6-0` tag，且不得移動 `rp-b5-1` 或其他既有 tags。
