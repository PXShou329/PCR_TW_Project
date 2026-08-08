# B1 verification report — 2026-08-08

## 結論

B1 full-core round-trip parity 可接受為 **本機／私人 staging**。本里程碑證明
research core 可 lossless 匯入不可變 PostgreSQL revision mirror、由唯讀 API 供應、
確定性匯出，並可完成備份還原與受控降版；它不代表 Data Gate A／B／C 或
Application／Automation／Production Gates D–G 已通過。

驗證全程未修改 `research_core/pcr_tw_project/`。最終 `git status` 對該目錄為空，
canonical baseline 仍為：

```text
PRE_SUITE --write  exit=0  CHECKS=128 FAIL=0 WARN=16
PRE_SUITE          exit=0  CHECKS=128 FAIL=0 WARN=16
OPERATIONAL        exit=0  CHECKS=127 FAIL=0 WARN=15
ARTIFACT_READY     exit=1  CHECKS=130 FAIL=3 WARN=15
```

ARTIFACT_READY 的三個 FAIL 恰為 Gate A、Gate B、Gate C，沒有其他 FAIL。

```text
MUTATION_TESTS ALL_OK | active_scenarios=66
RESEARCH_BASELINE_OK | files=48 | mutation_scenarios=66 | manifest_sha256=3a242b521d830af12ce8559d88b733068fb1b6cb503219395d2986b89e5dc352
```

## Lossless mirror 與 round-trip

本機隔離 DB 與實際 PostgreSQL／`pcr_api` role 均回傳 `ROUND_TRIP_OK`；實際 DB replay
為 `created=false`，兩次 export 完全一致，export copy 的五命令 exit 符合上述基線。

```text
files=48
csv_files=13
csv_rows=215
raw_tree_sha256=fd3f1a0a102873ad4a0f0248e24f52cfc0e4e2e7f371e3abe35fd6848ba00900
semantic_tree_sha256=00c9fdacbcbf07ae5b499241d3bc245056a682f11ef99d3489f64852746c1ca4
manifest_sha256=3a242b521d830af12ce8559d88b733068fb1b6cb503219395d2986b89e5dc352
evidence_to_claim=75 sha256=4f6d1705932c75aa5cc7e4b2f801bd1802d4ce9299e22a3bd8168af0cf4c6a9d
claim_to_evidence=162 sha256=edd12292d4e7e345db474b13cf07623507a702ef42da653978747aca92e89d1b
deterministic_exports=true
```

Loader／exporter 的 negative tests 包含 duplicate JSON key、NaN／Infinity、overflow number、
path traversal、symlink、Windows junction／reparse、canonical-tree destination 與既存目的地。
Importer 只 capture source bytes 一次，typed closure 與 full-core snapshot 在 DB transaction
前逐檔 cross-check；確定性 source drift test 證明失敗時 DB 寫入為 0。

## Application checks

```text
Python API/importer/database/scheduler/operations: 111 passed
OpenAPI / TypeScript parity:                     OPENAPI_CLIENT_PARITY_OK schemas=16
TypeScript typecheck:                            exit 0
Next.js production build:                        exit 0
Playwright mock desktop/mobile:                  12 passed
Playwright real Compose desktop/mobile:          12 passed
Compose config / PowerShell parse / diff check:  exit 0
```

真實 Compose E2E 覆蓋 PROVISIONAL 3/5、關卡→隊伍→Evidence Drawer、guide/team path
拒絕、TM-F810-01 純 SOURCE_GAP、TM-F810-02 分來源 PARTIAL 軸，以及 PVP 空結果；沒有
生成不存在的攻略、步驟或 counter。

## Fresh PostgreSQL／Compose checks

精確刪除可丟棄的 `pcr-tw-b1-final_pg_data` 後，由空 volume 實跑
V0001→V0002→V0003。資料庫中的 Alembic revision 為
`v0003_core_revision_mirror`，artifact guard function 含 `FOR SHARE`，history／epoch
關鍵 triggers 均存在。API readiness 實際輸出：

```json
{"status":"ok","checks":{"database":"ok","fixture":"imported"}}
```

交易與 cache smoke：

```text
REPEATABLE_READ_CONSISTENCY_OK isolation="REPEATABLE READ" epoch=445→446→447
CACHE_EPOCH_FAIL_CLOSED_OK http=200→503→200 epoch=447→448→449
ARTIFACT_FINALIZE_LOCK_OK denial_sqlstate=55P03 cleanup_rows=0
```

Artifact writer 在 transaction 內取得 parent revision 的 row-share lock；競爭中的 finalizer
因 `lock_timeout` 被 PostgreSQL 拒絕，rollback 後沒有暫存 revision／run 殘留。

角色漂移演練先把 `pcr_api` 改為 `INHERIT=true`、`BYPASSRLS=true` 並加入暫時群組；
重跑 role provision 後實際讀回 `false／false`、membership count `0`，暫時群組已刪除。

```text
DB_PRIVILEGES_OK matrix_checks=240 actual_denials=18 allowed_smokes=6
SCHEDULER_SHADOW_SMOKE_OK first=SHADOW_NOOP second=DUPLICATE_SKIPPED
canonical_write_capable=false
```

不可變歷史建立 A→B→A，最後 source DB 為 2 revisions／7 activations；inactive revision
仍可完整驗證，active pointer 回到 canonical A。最終 verifier：

```text
REVISION_HISTORY_VERIFIED revisions=2 inactive=1 import_runs=2 activations=7
history_sha256=8f09c8c1675564de8ede61977d6ea886b53652a2fa2e40c9315c6f2a4b18e5ab
```

## Backup／restore／downgrade drill

第一次完整 drill 成功完成 restore guards、round-trip、API 與 Web，並在真正 downgrade 時
揭露腳本把 Alembic owner URL 寫成 `postgresql://`，導致 SQLAlchemy 嘗試載入未安裝的
`psycopg2`。失敗路徑仍刪除了 restore API／Web、restore DB 與 dump。修正為專用
`postgresql+psycopg://` migration URL，加入 regression test，再從頭重跑全部步驟。

第二次實際結果：

```text
SOURCE_REVISION_HISTORY_OK revisions=2 activations=7
RESTORED_REVISION_HISTORY_OK revisions=2 inactive=1 activations=7 rollbacks=3
RESTORED_HISTORY_DIGEST_OK sha256=8f09c8c1675564de8ede61977d6ea886b53652a2fa2e40c9315c6f2a4b18e5ab
DB_PRIVILEGES_OK matrix_checks=240 actual_denials=18 allowed_smokes=6
RESTORED_DB_GUARDS_OK
RESTORED_ROUND_TRIP_OK role=pcr_api files=48 csv=13 rows=215
RESTORED_API_READINESS_OK role=pcr_api stage=PROVISIONAL teams=3 timelines=8 steps=14 evidence=ev052
RESTORED_WEB_EVIDENCE_OK stage=PROVISIONAL evidence=ev052
LEGACY_ROLLBACK_OK alembic=v0002_operation_timelines b1_tables=0
BACKUP_RESTORE_OK tables=21 source_alembic=v0003_core_revision_mirror rollback_alembic=v0002_operation_timelines
```

V0003 downgrade 前記錄的 active ImportRun 與 V0002 legacy latest query 相同。成功後以
database name pattern、container name pattern、backup filename pattern 三路查核：restore DB、
restore containers、smoke dump 均為零殘留；原 B1 API readiness 仍為 `ok`。

## 回滾點與尚未宣稱通過的項目

- Code 回滾基準為 `rp-a2-b2-2`，但已有 B1 DB 時不能只 checkout tag；必須依
  `B1_RUNBOOK.md` 使用 pre-B1 backup，或先 quiesce 再做 transactional downgrade。
- B1 release tag 只在本報告、CI 與獨立 Maintainer review 全部通過後建立；tag 不取代 DB
  backup／restore runbook。
- Data Gate A／B／C 仍為 false，blocking warnings 仍為 7；不得宣稱 ARTIFACT_READY。
- Gates D–G 仍依 roadmap 後續里程碑驗收。自動化仍只在 Shadow Mode，沒有 canonical
  publisher；正式 observability／alerting 仍是後續 production debt。
