# 40 抽卡未來視・公共層（GACHA FUTURE SIGHT）

> 用途：公共未來視研究流程與回答規範（四欄輸出：日服官方日期／模型錨點預估／台服社群整理共識／最終整合區間＋分歧原因）。硬規則見 Instructions §11；
> 時間線資料在 `41_GACHA_TIMELINE.csv`（欄位定義見下）；角色未來價值評估依 `42_CHARACTER_FUTURE_VALUE_SCHEMA.md`；
> 寶石預測模板見 `43_GEM_FORECAST_TEMPLATE.md`；研究記錄於 `44_GACHA_RESEARCH_LOG.md`。

## 1. 推估方法

1. 取日服原始日期（A 級：日服官網）。
2. 套用 `02_SERVER_BASELINE.md` 錨點差距，並**指明軌道別**（限定角引用 LIMITED、常駐角引用 PERMANENT、系統功能引用 SYSTEM；ALL_NEW 僅作整體參考）。

```text
四軌統計（由 tools/validation_config.json 之 canonical anchor objects 即時重算；ST84 守門）
LIMITED：n＝5｜中位數 123｜範圍 122–124
PERMANENT：n＝2｜中位數 122.5｜範圍 122–123
ALL_NEW：n＝7｜中位數 123｜範圍 122–124
SYSTEM：n＝1｜中位數 75｜範圍 75–75
說明：ALL_NEW＝LIMITED＋PERMANENT 之合併集合，SYSTEM 不併入角色卡池統計。
Mapping confidence 上限 B（跨服 identity 屬 record linkage 判斷）→ 任何以此統計推導之日期預測，信心不得高於 B。
所有未來視回答必須引用本段並揭露軌道別與 n 值。
```
3. 檢查台服排程調整紀錄與巴哈未來視串（C 級交叉參考）。
4. 輸出**區間＋信心等級**，附推估依據；不得給確切日期（對應 T35／T36）。
5. 台服官方公告出現順序異動時：降低相關預測信心並更新 02 與 41（對應 T40）。

## 2. 回答結構（三層）

1. **角色本身**：依 42 Schema 評估。
2. **卡池相對排序**：與前一池、後續重要池、周年／公主祭比較，不得只回答「值得抽」（對應 T37）。
3. **通用資源規劃**：提供通用寶石公式（43）與情境化建議；個人寶石問題回答「本專案不保存帳號資料」＋公式（對應 T38／T39）。

## 3. 【一般建議】必含

角色價值摘要／卡池相對順序／建議存石程度（定性）／哪類玩家需要（新手・競技場向・戰隊向・收藏向）。

## 4. 資料維護

- 每次未來視研究：44 記一筆；成熟結論寫入 41 時間線（一列一池／一角）。
- 12 的日服待實裝清單是 41 的上游：新角先進 12，評估完成後補齊價值欄位進 41。
- 台服官方公告落地一筆預測 → 41 標記實際日期、02 增錨點。

### 研究中未來視（maturity=RESEARCH；不作成熟預估輸出）

- JP_20260731_fubuki_summer｜フブキ（サマー）｜日期 OFFICIAL／A（ev048）｜台服預估 2026/11/30–12/02（MODEL_ONLY；LIMITED 軌 n=5，model interval＝jp_date＋[122,124]；信心低～中）｜**價值 NOT_EVALUATED——回答未來視時只給日期區間與「價值研究未完成」聲明，不給抽取優先級**

## 5. 41_GACHA_TIMELINE.csv 欄位定義

| 欄位 | 說明 |
|---|---|
| event_id | `JP_<YYYYMMDD>_<slug>`（以日服日期為準） |
| jp_date | 日服開池日 |
| model_estimate_start／model_estimate_end | **模型核心區間**，完全由 canonical anchor track 派生（jp_date＋TRACK.min／TRACK.max），不得手寫 |
| tw_estimate_start／tw_estimate_end | **最終整合區間**（final integrated interval）；官方落地後改填實際日 |
| forecast_method | MODEL_ONLY／MODEL_PLUS_COMMUNITY／OFFICIAL_OVERRIDE。MODEL_ONLY 時最終區間必須等於模型區間，不得加無依據人工 buffer |
| forecast_basis | **由程式生成的 canonical provenance 字串**，須完全等於 validator 之 build_forecast_basis(track) 輸出；禁止人工輸入第二套統計數字 |
| forecast_notes | 人工補充說明（軌道選用理由、排程風險等）；不得寫入統計數字 |
| confidence | 高／中／低 |
| character_name_jp／tw_temp_name | 日文名／台服名（未公布時空白或【待查證】） |
| pool_type | 限定／常駐／公主祭／復刻 |
| limited | 是／否 |
| arena_value／p_arena_value／pve_value／clan_value | 高／中／低／待查證（依 42 評估） |
| future_upgrade | 未來專武／六星等強化摘要 |
| relative_priority | 相對優先級（與前後池比較的定性結論） |
| sources | 來源摘要 |
| last_verified | 最後查證日 |
