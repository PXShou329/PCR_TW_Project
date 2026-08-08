# 15 資料品質報告（DATA QUALITY REPORT）

> 本版：v1.5（Guide Wave 1 — 2026/08/02 公共資料刷新完成）。AUTO_STATS 區塊**由 `tools/validate_project.py` 每次執行時覆寫並核對**
> （ST38）；區塊外的敘述不得重複統計數字。手改 AUTO 區會被自動修復並記錄。

<!-- AUTO_STATS_START -->
**程式化統計（validator 生成即核對；生成日 2026-08-08／版本 v1.5／Release 2026-08-02／Mode PRE_SUITE）**

- 檔案 44（編號 43＋README）＋tools×4｜Knowledge 42｜Fixture 37
- Gate 成熟資料：PVE VERIFIED 1（24）｜Arena VERIFIED 0（39）｜P-Arena 0（47）｜Timeline MATURE 2（41）
- 92 Evidence 81 列｜Tier {'OFFICIAL': 51, 'MAJOR_GUIDE': 10, 'SINGLE_PLAYER_REPORT': 11, 'MULTI_PLAYER_REPORT': 5, 'STRUCTURED_DB': 1, 'UNKNOWN': 3}｜evidence_confidence {'A': 51, 'D': 30}｜PENDING_REVIEW 1
- 93 Claim 93 列｜claim_confidence {'A': 52, 'D': 22, 'C': 2, 'B': 17}｜claim_type {'SOURCE_FACT': 61, 'DERIVED_CALCULATION': 6, 'ANALYTICAL_JUDGMENT': 26}
- Gate A=FAIL｜B=FAIL｜C=FAIL｜阻擋 Gate C 警告 10
- 靜態檢查 129 項｜FAIL 0｜WARN 18
<!-- AUTO_STATS_END -->

## 帳號層狀態

**產品範圍：Guide-Only**——帳號層 **REMOVED_FROM_ACTIVE_SCOPE**（封存於外部 archive ZIP，見 99），**不是 v1.5 Deferred**；
如未來重啟個人化，需新 ADR 與獨立 Migration。產品邊界：本專案不保存帳號資料。Gate A/B/C 只計公共攻略資料。

## 資料現況（質性）

- 台服基準為 **2026-08-02** 官方狀態；官方公告核對至 **2026-08-02**（六直頁完整抓取：ev029／ev033／ev043／ev044／ev048 等均 ACTIVE；ev045–047／ev049 標題級官方確認、細節待例行回驗）。
- 錨點採分軌口徑（卡池軌信心中、系統軌信心低）；候選 #4（深域 10 區）待日服官方化。
- 成熟資料數量一律以 AUTO 區為唯一權威（PVE＝24／Arena＝39／P-Arena＝47／Timeline＝41／社群來源＝45）；依本檔開頭規則，區塊外不重複統計數字。
- Stale Register 現役 2 項＋SUPERSEDED 1 項。
- 主要未關閉缺口（與 02 OPEN_GAPS 一致）：ev045/ev046/ev047/ev049 與 #3943 直頁正文例行回驗（標題級已官方確認）、候選 #4 的 JP 側官方化（TW 側已由 ev029 完成）、台服 08/02 後例行檢查、台服譯名（フブキ待台服公告）。**ev029／ev033 已於 2026-08-02 直頁完整抓取解鎖（ACTIVE）；主線已刷新至第 16 章／Lv373。**

## 驗收現況

41 項公共測試全 NOT_RUN（部署後執行）；靜態檢查結果見 AUTO 區與 16
（重跑：`python3 tools/validate_project.py`；回歸攔截驗證：`python3 tools/mutation_test.py`）。

## Release Gate：未通過（分層）

Gate A：四 Suite 待實跑｜Gate B／C：各項達成度見 AUTO 區與 16，門檻定義於 tools/validation_config.json（gate_thresholds），本行不重複數字｜Gate C：未達。**Phase 6＝BLOCKED_BY_RELEASE_GATE**。

## 下一步

Scope Closure（本輪）→ Checkpoint B（紅焰 8-10／10-10 各 5–10 隊）→ C（Gacha 社群整合）→ D（Arena 解陣）→ E（P-Arena 47 案例）→ 四 Suite → Gate 重評。
