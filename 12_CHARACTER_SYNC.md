# 12 新角色同步流程（CHARACTER SYNC）

> 用途：台服實裝／強化同步＝逐筆寫入 `18_TW_CHARACTER_AVAILABILITY.csv`（公共角色可用性 Registry）；日服新角＝未來視追蹤（評估後遷 41）。本專案不保存帳號資料。不依賴對攻略站的整站爬蟲。
>
> 背景決策（ADR-9，2026-07-16）：否決「爬取 GameWith 全角色圖示與資訊」方案。理由：
> 該站阻擋自動抓取（實測 bot 偵測擋下）；角色圖示為 Cygames 遊戲素材、評價文字為攻略站
> 編輯內容，整站複製轉存有版權與使用條款風險；違反企劃非目標「未經查證直接建立完整遊戲
> 資料庫」；圖示在 Claude Project 階段無用途；日文名機翻違反 03 台服官方譯名規則；HTML
> 爬蟲維護成本觸及停止條件。攻略站正確用法：查詢時逐頁引用＋標來源日期（見 01）。

## 兩個資料入口

| 事件 | 動作 | 目的檔 |
|---|---|---|
| 台服實裝新角色 | **逐筆寫入 18**（unit_key＋tw_release_date＋availability_status=AVAILABLE＋evidence）；專1／專2／六星／連結RANK 開放時逐項更新對應欄位並更新 last_checked。另確認 03 版本代碼 | 12 → 18、03 |
| 日服實裝新角色（台服未出） | 新增至「日服待實裝追蹤清單」；完成官方驗證與價值評估後**逐筆**遷移至 41，成功後 timeline_status=MIGRATED_TO_41 | 12 → 41 |

## 同步節奏

- 台服每次改版或新卡池公告後執行；或隨 `02_SERVER_BASELINE.md` 的更新節奏（每 1–2 週）一起跑。
- 每次執行後在 `99_CHANGELOG.md` 記一行（含同步截止日期）。

## 同步提示範本

提示一律取自 `91_PROMPT_LIBRARY.md` §3（單一維護點；v1.4.1.1 起本檔不再保留副本——
副本漂移正是 F04 衝突的成因）。硬規則以本檔「兩個資料入口」表為準，提示不得繞過。

## 同步狀態（v1.4 生命週期制）

```text
最後同步截止日（last_checked）：2026-08-02
本輪檢查範圍：2026/05–08 日服新角＋台服官網公告至 **2026-08-02**（六直頁完整抓取＋官方列表確認；詳見 02）
使用來源：ev010 / ev013 / ev024 / ev025 / ev027–ev034 / **ev043–ev049**（第 16 章／Lv373、深域第 10 區、格蕾斯（兔女郎）、フブキ（サマー）、8/1 系統批次；見 92）
狀態欄允許值：
  verification_status：CANDIDATE／OFFICIAL_VERIFIED／CONFLICTED／REJECTED
  future_value_status：NOT_EVALUATED／IN_RESEARCH／EVALUATED
  timeline_status：NOT_MIGRATED／MIGRATED_TO_41／ARCHIVED
  tw_announcement_status：NOT_ANNOUNCED／ANNOUNCED／RELEASED
去重規則：同一角色（sync_id）僅一列；重複同步只更新 last_checked 與狀態（對應 T44）。
```

## 日服待實裝追蹤清單

| sync_id | 角色（日文名／台服名） | jp_release_date | pool_type | verification | future_value | timeline | tw_announce | last_checked | notes（含 Tier/Conf 與 evidence） |
|---|---|---|---|---|---|---|---|---|---|
| SYNC-001 | ワカナ（ウィンター）／若菜（冬日） | 2026/03/03 | 限定 | OFFICIAL_VERIFIED | NOT_EVALUATED | ARCHIVED | **RELEASED**（台 2026/07/04 開池；公告 07/03） | 2026-07-16 | 已轉為 canonical anchor POOL-WAKANA-WINTER（LIMITED，delta 123；ev001;ev002），自追蹤關閉 |
| SYNC-002 | シェフィ（ヴァードラッヘ）／【待查證】 | 2026/06/30 | プリフェス限定 | OFFICIAL_VERIFIED（日期 ev010；**池型 OFFICIAL／A＝ev032**，F04 修正） | EVALUATED | MIGRATED_TO_41 | NOT_ANNOUNCED | 2026-07-17 | PVE 評價依 F03 修正為 D（41/44）；41 event_id＝JP_20260630_shefi_vardrache |
| SYNC-003 | ルイズマリー（サマー）／【待查證】 | 2026/07/03 | 限定（泳裝，官網明載「期間限定」） | OFFICIAL_VERIFIED（ev013） | EVALUATED（D 級單源） | MIGRATED_TO_41 | NOT_ANNOUNCED | 2026-07-17 | 評估 ev014（單一 MAJOR_GUIDE → D）；41 event_id＝JP_20260703_luisemarie_summer |
| SYNC-004 | ルルィ／【待查證】 | 2026/05/22【D】 | 【待查證】 | CANDIDATE | NOT_EVALUATED | NOT_MIGRATED | NOT_ANNOUNCED | 2026-07-16 | 單一攻略站側欄來源；注意與マナリア聯動角「ルゥ」為不同名稱，需消歧義後升級 |
| SYNC-005 | リリ（ヴァルキュリア）／【待查證】 | 2026/05 前後【D】 | 【待查證】 | CANDIDATE | NOT_EVALUATED | NOT_MIGRATED | NOT_ANNOUNCED | 2026-07-16 | 官方日期待日服官網回查（注意與既存「リリ（サマー）」為不同版本） |
| SYNC-006 | クレジッタ（サマー）／【待查證】 | 2026/07/15 | 限定（泳裝，官網明載） | OFFICIAL_VERIFIED（ev031，官網直驗；池期 07/15–07/31 已結束） | NOT_EVALUATED | NOT_MIGRATED | NOT_ANNOUNCED | 2026-08-02 | 評估後遷移 41；台服預估依卡池軌 2026/11 中旬前後（信心低～中） |
| SYNC-008 | フブキ（サマー）／【待查證】 | 2026/07/31 | 限定（泳裝，官網明載「期間限定」） | OFFICIAL_VERIFIED（ev048，2026-08-02 官網直頁 #37049 完整抓取） | NOT_EVALUATED | MIGRATED_TO_41 | NOT_ANNOUNCED | 2026-08-02 | 41 event_id＝JP_20260731_fubuki_summer（maturity=RESEARCH；價值研究完成前不設 MATURE）；池期 07/31 12:00–08/15 11:59 |
| SYNC-007 | シオリ（ウィンター）／栞（冬日） | 2026/03/16 | 限定 | OFFICIAL_VERIFIED（ev027;ev028） | NOT_EVALUATED | ARCHIVED | **RELEASED**（台 2026/07/17） | 2026-07-17 | 已轉為 02 錨點 #3，自追蹤關閉 |

## 台服實裝落點（Guide-Only）

台服新實裝角色不再暫存於本檔：**直接逐筆寫入 `18_TW_CHARACTER_AVAILABILITY.csv`**（近例：栞（冬日）07/17、若菜（冬日）07/03、格蕾斯（兔女郎）08/01，皆已在 18）。本檔僅保留日服側追蹤與同步紀錄。


## 技術債登記（v1.4.1.4）

- Guide-Only：本檔不再涉及任何角色池驗證；台服可用性一律以 18 為準（unit_key 唯一、逐筆證據、last_checked 維護）。
