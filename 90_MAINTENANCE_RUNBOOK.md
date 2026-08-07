# 90 維運 Runbook（MAINTENANCE RUNBOOK）

> 用途：例行維運節奏與觸發式處置。所有例行任務的提示範本取自 `91_PROMPT_LIBRARY.md`。

## 每 1–2 週例行

1. 更新 `02_SERVER_BASELINE.md`：台服官網 news＋日服官網 information／update（91 §1）。
2. 執行 `12_CHARACTER_SYNC.md` 新角色同步（91 §3）。
3. 檢查 `32_ARENA_META_SNAPSHOT.md` 是否需要新快照（新強角／改版後必查）。
4. 檢查 `41_GACHA_TIMELINE.csv`：官方公告落地的預測改實際日、02 增錨點、信心調整。
5. 掃 `99_CHANGELOG.md` 過期登記（STALE）與待辦，處理或展期。
5b. 維護 `92`（證據；evidence_confidence＋日期精度）與 `93`（結論；claim_confidence＋claim_type）：新結論先入 93 並掛 evidence_id；失效改 status；B／C 級抽查獨立性；15／16 一律由 `tools/validate_project.py` 重跑產生，禁止手填、禁止部分重跑後不重生成報告。
5c. 驗收回歸：規則檔（00／20／30／35／40／43）有修改時，重跑受影響 Suite（91 §10），結果覆寫 13 對應列。

## 大型改版後（新 Rank／專武／六星／新系統／新深域區域）

- 02 全面重查證；03 補新系統術語。
- 22 深域索引：受影響攻略標「待重驗」；31 反制資料掃 stale_conditions。
- 32 建新快照；41 受影響角色 future_upgrade／價值欄重評。
- 全部變更 99 記錄。

## 使用者回報失敗後

1. 記入對應研究日誌（23／33／38／44）。
2. 調查版本差異（攻略練度條件 vs 台服環境版本；台服可用性依 18）。
3. 降級可靠度或標 STALE；更新 22 索引狀態。
4. 修正後重驗；99 留痕。

## 檔案健康（Sweeper 檢查點）

- Knowledge 檔案數異常膨脹、單檔逼近 100 KB、檢索混淆 → 依 22 分割策略處理；四本研究日誌（23／33／38／44）若造成碎片化可評估合併（先提 ADR）。
- 任何 Schema 變更：先 ADR、說明 migration、更新驗收，不得無聲修改。

## 狀態儀表（每次維運後自查）

02 最後查證日／12 最後同步日／32 最新快照日／13 未關閉的 FAIL／99 未處理 STALE 數。
