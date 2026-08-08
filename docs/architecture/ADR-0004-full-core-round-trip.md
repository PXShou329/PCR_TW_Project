# ADR-0004：B1 全量 artifact mirror 與 deterministic round-trip

- 狀態：Accepted for B1
- 日期：2026-08-08
- 前一安全回滾點：`rp-a2-b2-2`

## 背景

A2＋B2 的 typed importer 只 materialize 紅焰 8-10 選取 closure；即使八個輸入檔的
hash 完整，也不能由現有 typed tables 重建 48 檔 research core。B1 必須證明
current file SSOT 可完整匯入、確定性匯出並通過既有 Validator／Mutation，同時不能
提前形成第二個 writable SSOT。

Validator 的 `PRE_SUITE --write` 使用執行日更新生成報告。若 exporter 把這次寫入
納入 revision hash，同一筆 revision 會跨日漂移，因此 export 與 validation write
必須分離。

## 決策

### 三層 read mirror

1. **Artifact mirror**：逐 byte 保存 manifest 鎖定的 48 個檔案、POSIX relative path、
   raw SHA-256、encoding／newline profile 與檔案角色。
2. **Row mirror**：將 13 個 CSV 的 header、順序、215 筆原始字串 cell、自然鍵與 row
   digest 分別保存。空字串、`UNKNOWN`、`NONE` 與 `—` 不互換。
3. **Typed serving closure**：保留現有 PVE 正規化 tables 與 relation tables，供 API／UI
   唯讀查詢；它不是完整 research-core exporter 的唯一輸入。

Artifact bytes 讓 48 檔可精確重建；Row mirror 另行重新 parse 與比對，避免把「blob
原樣吐回」誤報為 row parity。Typed closure 再獨立核對 normalized columns、
`source_payload` 與 relation edges。

`file_role`、`encoding_profile`、`newline_profile` 不另建可獨立修改的 DB 欄位，而是
由每筆 `CoreFile.relative_path` 與 `CoreFile.content` 確定性推導後寫入
`CoreRevision.manifest.files`。從 DB 重建 snapshot 時必須再次由 exact bytes 推導並與
revision manifest 比對；不一致即 fail-closed。`CoreFile.content`、raw SHA-256 與
semantic SHA-256 仍是 authoritative artifact values。

### Digest 與關聯

- `raw_tree_sha256`：依 POSIX path 排序，聚合 path 與原始 bytes。
- `semantic_tree_sha256`：CSV 以 header、row order 與原始 cell canonical JSON 計算；
  `.json` 必須先通過嚴格 UTF-8 JSON parse，再以 sorted-key canonical JSON 計算；
  其餘檔案使用 raw digest。Semantic tree entry 的 `kind` 分別為 `csv`、`json`、
  `raw`；無法解碼、語法無效、重複 object key、非有限數值，或 `1e400` 這類 parse 後
  overflow 成非有限浮點數的 JSON 一律 fail-closed；canonical serializer 禁止 NaN。
- `materialization_sha256`：由 DB 重新查詢 active typed closure 計算。
- Evidence 宣告 Claim 的 75 條 edge 與 Claim 宣告 Evidence 的 162 條 edge 分開保存與
  比對；不要求兩方向集合完全相等，也不自動修補 `ev053` 的既有合法不對稱。

### Export 與驗證

- Source loader 對 research-core root、pinned manifest 與兩者所有 lexical ancestors 使用
  `lstat`，walk 時亦逐一檢查目錄與檔案；POSIX symlink 與 Windows junction／reparse
  point 一律拒絕，不能在 resolve 後遺失來源路徑邊界。
- Exporter 只接受 canonical tree 外的新目的地；拒絕原始 core、其子目錄、symlink、
  path traversal、非空或既存目的地。
- Destination 以 lexical `lexists`／`lstat` 檢查；dangling symlink 也視為既存，且從
  destination parent 到 filesystem root 的每一層 lexical ancestor 都不得是 symlink
  或 Windows junction／reparse point，通過後才可 resolve 與做 canonical boundary 比對。
- 先在同一檔案系統的 staging directory 完整寫入並重新驗證，再以 atomic rename
  發布；失敗不得留下半套 candidate。
- 相同 active revision 連續匯出兩次，檔案集合、逐檔 SHA-256、raw／semantic tree
  hash 必須完全相同。
- 原始五命令在 exported tree 的 **disposable copy** 執行；`--write` 產物不回寫
  exported revision，也不改變其 tree hash。

### Revision 與 readiness

- B1 可保存不可變 core revisions，但任何時點只有 file core 可寫；DB revisions 只由
  importer 建立 read mirror，API 沒有 write／export endpoint。
- Active pointer 與 append-only activation audit 在 importer 的單一 transaction 最後
  切換。新建 revision 記為 `IMPORT`；切回首次 `IMPORT` chronology 較早的既存 revision
  記為 `ROLLBACK`；再切向 chronology 較晚的既存 revision 記為 `REACTIVATE`。Chronology
  使用 activation sequence，不使用可能相同或漂移的牆鐘時間。
- PostgreSQL statement triggers 在 mirror DML 後增加 epoch。Readiness cache 以
  active revision、import run、epoch 與 manifest digest 為 key；epoch 改變即重算，
  drift 仍 fail-closed，不能用 TTL 掩蓋變更。

### 部署回滾與舊版 latest projection

Git tag 只固定程式碼，不會回復 PostgreSQL schema 或 active pointer；因此單獨 checkout
`rp-a2-b2-2` **不是**完整 rollback。尤其已有 A → B → A 歷史時，A2／B2 的
`latest_import` 只依 `SUCCEEDED ImportRun.imported_at DESC, id DESC` 查詢，若直接啟動
舊程式會誤選建立時間較晚的 B，而不是 B1 active pointer 指向的 A。

回退舊版前必須擇一：

1. 先在同一維護交易執行 DB downgrade 至 V0002。V0003 downgrade 會在刪除
   `materialization_state` 前確認 active run 為 `SUCCEEDED`，再把它的 `imported_at`
   提升至所有成功 run 之後，使舊版 latest query 投影到相同 active run；或
2. 還原經驗證的 pre-B1 database backup。

Reconciliation 只存在於 transactional downgrade，正常 B1 terminal-history guard 不會
放寬。它刻意改寫 active run 的 legacy ordering timestamp，因此若必須保留原始時間與
完整 activation audit，應採 pre-B1 backup／另存稽核證據，而不能只依 tag 回退。

## 檔案角色

- `*.csv`：STRUCTURED_DATA，同時保存 bytes 與 row projection。
- `13_ACCEPTANCE_RESULTS.md`、`15_DATA_QUALITY_REPORT.md`、
  `16_STATIC_VALIDATION_REPORT.md`、`tools/stats.json`：VALIDATOR_GENERATED，但在 B1
  revision 中仍逐 byte 保存；exporter 不自行重算。
- `tools/*.py`：VALIDATOR_TOOL，必須受 manifest hash 保護後才可在隔離副本執行。
- 其餘 Markdown／JSON：VERSIONED_STATIC_ASSET。

Encoding profile 由 bytes 推導為 `UTF-8`、`UTF-8-BOM` 或 `BINARY`。可解碼文字的
newline profile 依實際換行 bytes 推導為 `LF`、`CRLF`、`CR`、`MIXED` 或 `NONE`；
`BINARY` 使用 `NOT_APPLICABLE`。上述角色與 profiles 均存在 revision manifest，
exporter 不採信 manifest 文字，而以 DB 保存的 path／bytes 重算後核對。

## 明確不做

- 不就地修改 research core，不雙寫，不切換 DB writable SSOT；B8 前仍適用
  ADR-0001。
- 不把 byte-preserved artifact mirror 宣稱成所有 domain 都已正規化；Arena、
  P-Arena、Gacha 的 typed models 仍由後續 tracks 完成。
- 不更改研究事實、不補隊伍、不提高 confidence，不降低 Gate／Validator。
- 不把 `tools/reports/*` 或執行期暫存檔納入 canonical export。

## 驗收與停止條件

只有在 48 files、13 CSV、215 rows、兩組 Evidence／Claim edge、typed closure、兩次
export tree、exported-tree 五命令、least privilege、backup restore 與 serving drift
全部實測一致後，B1 才可完成。任一差異、額外 ARTIFACT_READY FAIL、雙 SSOT、
半套 migration／export 或 canonical tree 被修改，都立即停止並回退
依 B1 runbook 以 pre-B1 backup，或 V0003 transactional downgrade reconciliation
搭配 `rp-a2-b2-2` 完成原子回滾；不得只切 Git tag。
