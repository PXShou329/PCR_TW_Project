# 公主連結台服 AI 攻略研究所 — v1.5 檔案包使用說明

**版本定位**：v1.5 Guide-Only ── **台服公共攻略資訊整合系統（帳號層 REMOVED_FROM_ACTIVE_SCOPE）**。
產品只做：PVE 通關隊伍（每關 5–10 支）、競技場解陣、公主競技場三隊、抽卡未來視、來源追溯。
**本專案不保存帳號資料**；帳號層完整封存於外部 `PCR_TW_Project_account_layer_archive_v1_5.zip`（不上傳）。
已完成：17→13 Option A（13 全部狀態由 17 生成單一 AUTO_RESULTS；Gate A 只讀 17）、Gate C 警告分類優化、
流程清理（全專案不再手動回填 13）、**Baseline Integrity Patch**
（主線第 15 章／Lv370／涅婭★6 以官方直頁重新驗證：ev040 第15章、ev041 涅婭★6、ev042 Lv370；
ev037 保留為 01/15 第14章歷史快照）。
**2026/08/09 Freshness-0**：台／日官方索引核對至 08/09；ev045–047／ev049／#3943 已補齊官方正文，
新增台服深淵討伐戰／阿斯特朗復刻／艾爾皮斯活動（ev116–118）、日服三名夏日角色專1（ev119），並以
ev122 確認 8.5 周年直播已配信。直播內容未逐段核對，未據此新增卡池或價值結論；CURRENT-0802 歷史保留並由
CURRENT-0809 取代，next_review_due=2026-08-16。
攻略內容（PVE／Arena／P-Arena／Timeline）與四個公共 Suite 實跑為部署後 Guide Wave 1–3 工作，
本輪未虛構任何攻略或 Suite PASS。Gate A/B/C 未通過（正確）；Phase 6＝BLOCKED_BY_RELEASE_GATE。

**Guide-Only Scope Reset（2026-08-02）**
- 移出 Active：04／05／06／07／10 與 T3–T12／T15／T19–T21（ID 永久退休）；帳號 Mutation M22／M24／M31–M33 封存。
- 新增：18 公共角色可用性（PVE／Arena／P-Arena 可用性唯一來源）、25 PVE 隊伍層、45 Gacha 社群來源索引、46 Arena 來源 Registry。
- 測試集＝Guide-Only 41（A1–A3、T1、T2、T13、T14、T16–T18、T22–T52）；17 為 21 欄公共 Schema。

**Phase 狀態**：Baseline Current through 2026/08/08｜PVE Registry 10 VERIFIED（紅焰／蒼波 8-10 均為 VERIFIED／CONFIRMED，各 5 隊成熟結構門檻已達；紅焰 10-10 仍 IN_RESEARCH）｜Arena 39 現有 2 筆 SINGLE_REPORT、成熟防守案例 0（Checkpoint D）
｜P-Arena 理論模型 3（Checkpoint E 組合求解）｜Gacha MATURE 2＋RESEARCH 3（Checkpoint C 社群整合）｜Suite 全 NOT_RUN（部署後）。

**R3i（2026/08/08）**：PVE Gate 已封住 PROVISIONAL／缺失 unit_key 灌水路徑；TM-F810-01 已以
`SOURCE_CONFLICT`＋canonical requirements JSON 正規化；紅焰 8-10 第一階段實開候選來源後取得 3 支不同五人的
VERIFIED effective teams（詳見 22／23／25）。相同五人多來源只計一隊；該階段因少於 5 支，24 當時未升 `VERIFIED`。

**A2（2026/08/08）**：新增 26／27 逐來源操作軸 SSOT。TM-F810-02 的 GameWith
2025 年 9 月半自動正文已拆為 14 個原子步驟；其餘已登錄來源均明列 `SOURCE_GAP`，不把影片區間、
操作次數或多來源摘要冒充逐步操作。該軸來源為日服，雖同隊另有台服通關影片，仍標
`UNVERIFIED_ON_TW`，Gate 與關卡 lifecycle 均未提高。

**A3（2026/08/08）**：另以兩支已實際開啟並核對關卡、完整五人與通關結果的玩家影片補足
`TM-F810-04`／`TM-F810-05`，紅焰 8-10 現為 5 支不同五人的 VERIFIED effective teams，24 升為
`VERIFIED／CONFIRMED`。第四隊未取得足以判定全程操作模式的來源聲明，故保留 `UNKNOWN`＋`SOURCE_GAP`；
第五隊只將來源明載的五條時間／AUTO 狀態保存為 `SOURCE_TEXT_ONLY／NO_ACTION`，未把括號圖樣或全域養成條件
臆測成逐 slot／玩家操作事實。

**A4（2026/08/08）**：完成蒼波 8-10 五支不同五人的台服實戰 closure；五章均實際播放核對完整五人、
關卡與 Boss HP 歸零，模式依序為 `MANUAL_TIMELINE／SEMI_AUTO／AUTO／AUTO／AUTO`。五隊仍只有同一玩家來源，
所以 Claim 固定 D 並保留 Gate C blocking warnings；另將一支未清場及一支 `TIME UP` 影片明列為 `REJECTED`，
不得進有效隊伍。有效隊 predicate 同步要求所有 Team Evidence 均為 `ACTIVE`，並由 Mutation M71 鎖定。

**A5 Arena 暫行成熟度（2026/08/09）**：`VERIFIED` 只承認 B／C 的可機械驗證多來源閉合；`source_record_count` 與實戰 `sample_size` 分離，scalar Tier／筆數不代表來源獨立。SELF_TESTED 尚無可追溯 run registry，因此不得以本人實測聲明或手填 CONFIRMED 升級。Arena Gate 計 mature defenses：同環境同防守至少兩支不同成熟 exact counters 才算一案；目前兩筆同作者單次 Win 均維持 SINGLE_REPORT，Gate 為 0。

**B4-0 P-Arena structural candidate（2026/08/10）**：v5 typed serving 只承接完整成熟 47 closure；canonical 47 仍為 header-only，實際 mature case `N=0`。本輪實開 2021 巴哈 `LOSE／WIN／WIN` 圖組、2024 模板／部分防守、2026 問答與 YouTube 候選後，均因缺完整 case WIN、三筆 mature 39、18／必要強化或獨立性而標 `DEFERRED_NOT_CANONICAL`；JP／Bilibili 亦依台服核心與禁用中國服資料規則排除。未新增 39／47／92／93 資料，Gate A／B／C 與 blocking warnings 不變；0-case 由 Planner 誠實 fail closed，不生成 Similar 或理論隊。

## 檔案清單（唯一權威清單）

> ZIP 內 48 檔＝編號 43＋README＋tools×4（validate_project.py／validation_config.json／stats.json／
> mutation_test.py）；**42 檔**上傳 Knowledge（00 貼設定欄；README 與 `tools/` 皆不上傳）。
> 本地驗證：`python3 tools/validate_project.py`（生成 15 AUTO 區＋16＋stats.json）；
> 回歸攔截驗證：`python3 tools/mutation_test.py`（檢查數以 16 為準，README 不重述）。
> v1.4 交付規則：**單一權威 ZIP**，不外包 ZIP、不附鬆散副本。

| 檔案 | 用途 | 上傳 |
|---|---|---|
| 00_PROJECT_INSTRUCTIONS.md | 貼設定欄；v1.4 雙軌制＋錨點揭露更新 | 否 |
| 01_SOURCE_REGISTRY.md | 雙軌制定義＋統一欄位標準＋來源現況（v1.4 查證） | 是 |
| 02_SERVER_BASELINE.md | canonical anchors＝8 筆（LIMITED 5／PERMANENT 2／SYSTEM 1）＋四軌統計（由 tools/validation_config.json 即時派生）＋台日現況 | 是 |
| 03_NAME_GLOSSARY.md | 術語（交換Pt 升 A/A、星素、深域雙邊沿革等） | 是 |
| 11_ACCEPTANCE_TESTS.md | 測試定義（Guide-Only 41 測試） | 是 |
| 12_CHARACTER_SYNC.md | 同步生命週期（台服→18、日服→41；去重／截止日） | 是 |
| 18_TW_CHARACTER_AVAILABILITY.csv | 台服公共角色可用性 Registry（unit_key SSOT，15 欄） | 是 |
| 13_ACCEPTANCE_RESULTS.md | 驗收紀錄簿（四 Suite＋可追溯欄位） | 是 |
| 14_PUBLIC_TEST_FIXTURES.md | 公共測試固定輸入（37 個 Fixture 覆蓋 41 個測試） | 是 |
| 15_DATA_QUALITY_REPORT.md | 資料品質報告＋Release Gate 分層判定 | 是 |
| 16_STATIC_VALIDATION_REPORT.md | 靜態驗證報告（程式化統計） | 是 |
| 17_TEST_EXECUTION_LOG.csv | 測試執行紀錄 SSOT（21 欄公共 Schema；reviewer／review_method／expectation_checklist） | 是 |
| 20_PVE_GUIDE_WORKFLOW.md | PVE 流程（每關 5–10 隊＋去重＋公共借角） | 是 |
| 21_STAGE_GUIDE_SCHEMA.md | 攻略 Schema（統一欄位＋雙軌制） | 是 |
| 22_DEEP_ZONE_GUIDE_INDEX.md | 深域人讀索引（隊數／全自動／手動；Gate SSOT 為 24） | 是 |
| 24_PVE_GUIDE_REGISTRY.csv | PVE 關卡層 Registry（Gate SSOT，16 欄；team_count↔25） | 是 |
| 25_PVE_TEAM_REGISTRY.csv | PVE 隊伍層 Registry（20 欄；五 slot＋requirements canonical JSON＋來源模式聲明＋台服可用性＋去重） | 是 |
| 26_PVE_OPERATION_TIMELINES.csv | PVE 逐來源操作軸（16 欄；STRUCTURED／SOURCE_GAP 不跨來源合併） | 是 |
| 27_PVE_TIMELINE_STEPS.csv | PVE 原子操作步驟（20 欄；time_state／時間／觸發／角色／動作／locator） | 是 |
| 23_PVE_RESEARCH_LOG.md | PVE 研究日誌（P1 前置已登錄） | 是 |
| 30_ARENA_RESEARCH_WORKFLOW.md | 競技場研究流程 | 是 |
| 31_ARENA_COUNTER_SCHEMA.md | 反制 Schema（雙軌制＋evidence_ids） | 是 |
| 32_ARENA_META_SNAPSHOT.md | JP 初版＋TW PROVISIONAL 快照 | 是 |
| 33_ARENA_COUNTER_LOG.md | 反制日誌＋8 原型簡報＋停止條件回報 | 是 |
| 34_ARENA_SOURCE_MAP.md | 競技場來源地圖 | 是 |
| 35_PRINCESS_ARENA_WORKFLOW.md | 公競流程 | 是 |
| 36_PRINCESS_ARENA_STRATEGY_LIBRARY.md | 一般策略庫 | 是 |
| 37_PRINCESS_ARENA_PLANNER_SCHEMA.md | 三隊規劃 Schema | 是 |
| 38_PRINCESS_ARENA_RESEARCH_LOG.md | 公競日誌（PA1–PA3 理論案例） | 是 |
| 39_ARENA_COUNTER_REGISTRY.csv | 競技場反制 Registry（Gate SSOT，35 欄；exact 戰果、樣本、來源真值、台服可用性與成熟防守派生） | 是 |
| 40_GACHA_FUTURE_SIGHT.md | 未來視公共流程 | 是 |
| 41_GACHA_TIMELINE.csv | 時間線（36 欄含模型區間／方法／社群共識與 limited direct-Claim provenance；MATURE 2＋RESEARCH 3） | 是 |
| 42_CHARACTER_FUTURE_VALUE_SCHEMA.md | 價值評估 Schema | 是 |
| 43_GEM_FORECAST_TEMPLATE.md | 寶石模型（v1.4 單位修正＋三情境示例） | 是 |
| 44_GACHA_RESEARCH_LOG.md | 未來視日誌 | 是 |
| 45_GACHA_COMMUNITY_SOURCE_INDEX.csv | 台服社群未來視來源索引（14 欄；cap≤C） | 是 |
| 46_ARENA_SOURCE_REGISTRY.csv | Arena 解陣來源 Registry（12 欄；nomae STALE-only） | 是 |
| 47_PRINCESS_ARENA_CASE_REGISTRY.csv | P-Arena 成熟案例 Registry（Gate SSOT，24 欄；三組 exact 39 result Claim＋唯一整體 WIN Claim direct closure；A–D Evidence／source hostname／日期守門；敵我各 15 人不重複＋TW 可用） | 是 |
| 90_MAINTENANCE_RUNBOOK.md | 維運（＋證據帳與 Suite 回歸） | 是 |
| 91_PROMPT_LIBRARY.md | 提示庫（§10 四 Suite） | 是 |
| 92_EVIDENCE_LEDGER.csv | 證據帳（16 欄；列數以 validator 生成統計為準，見 16／stats.json） | 是 |
| 93_CLAIM_REGISTER.csv | 結論登錄簿（Claim SSOT，14 欄含 claim_type；列數見 16／stats.json） | 是 |
| 99_CHANGELOG.md | 更新紀錄 | 是 |
| README.md | 本檔 | 否 |

## 建置／升級步驟

1. 新建：照表上傳＋貼 00 → 跑 91 §1（08/09 後新公告、8.5 直播內容精確段落、候選 #4 JP 側）→ Checkpoint B–E（PVE 5–10 隊→社群未來視→Arena 來源→P-Arena 組合）→ 依 91 §10 逐 Suite 實跑。
2. **測試結果一律寫入 `17_TEST_EXECUTION_LOG.csv`（21 欄），再執行 `python tools/validate_project.py --mode OPERATIONAL --write`，由 validator 自動更新 13 的 AUTO_RESULTS——不手動修改 13 的測試狀態。**
2. 自 refresh_20260802 升級：重貼 00；移除 04／05／06／07／10；新增 18／25／45／46；替換 01、03、11–17、20–23、30、33、35、37、38、40、41、43、91、99、README；tools 全量更換。
3. 台服可用性補查：91 §9（18 Registry 逐筆查證）。

## ADR（v1.4 新增）

| # | 決策 | 理由 |
|---|---|---|
| 17 | Source Tier 與 Claim Confidence 雙軌制；單一大型攻略站最多 D | 修正來源／結論混用（P0） |
| 18 | 14 Fixtures＋92 證據帳＋四 Suite；PASS 必附 fixture/observed/evidence/日期 | 驗收可追溯（P0） |
| 19 | 單一權威 ZIP 交付 | 消除多副本失同步 |
| 20 | 寶石模型單位修正；並修正計畫稿缺口公式的免費抽重複扣除 | P0；有效抽數已含免費抽與券 |
| 21 | 內容量未達標時如實回報＋交付執行簡報，不灌水不虛構 | 停止條件 §17（3/5/8/10） |
| 22 | 錨點依 pool_class 四軌（LIMITED／PERMANENT／ALL_NEW／SYSTEM），統計必揭露軌道別與 n | 由 canonical anchor objects 即時重算，ST83／ST84／ST85 守門 |
| 23 | 92（證據）／93（結論）雙 SSOT；15 分布一律程式化計算 | 稽核 F02／F15：混算導致統計錯誤 |
| 24 | Evidence URL 標準化（source_url＋source_locator） | 稽核 F16 |
| 25 |（已由 ADR 39 取代）台服新角改逐筆入 18 | Guide-Only Scope Reset |
| 26 | 16 只能由 tools/validate_project.py 生成；打包以 exit 0 為前置 | v1.4.1 稽核 F01／F12：報告不可重現且曾與實際不符 |
| 27 | 驗證分 CURRENT_SPEC_SCAN／HISTORICAL_RECORD_SCAN；歷史只報告不 FAIL | v1.4.1 稽核 F16：不得刪歷史規避檢查 |
| 28 | 92 欄名 evidence_confidence；93 增 claim_type（含 DERIVED_CALCULATION） | v1.4.1 稽核 §6.1／6.2（F14／F15） |
| 29 | Validator 升級為回歸守門（ST38–ST43）＋mutation_test.py 隨附；15 AUTO_STATS 區由 validator 生成核對 | v1.4.1.1 稽核 M05／M06：關鍵字檢查不等於語意保護 |
| 30 | 提示不硬編碼會過期的統計值（T43 動態讀 02）；Evidence 限制逐筆處置、ev029 未直驗不解鎖 | v1.4.1.1 稽核 §4.1／§4.7 |
| 31 | Validation Mode（PRE_SUITE／OPERATIONAL／ARTIFACT_READY）：完整 PASS 放行、空白 PASS 攔截、FAIL 必附 defect | v1.4.1.2 稽核 M13：禁止一切 PASS 會阻擋 v1.5 |
| 32 | 17 為執行紀錄 SSOT（exact_prompt 機器可讀）；13 為人讀摘要；版本 SSOT 於 config 精確比對 | v1.4.1.2 稽核 §6／§7.2 |
| 33 | ARTIFACT_READY 強制 Gate A/B/C（未達 exit 1）；Gate 數量由 22／33／38／41 直接計算 | v1.4.1.3 稽核 §4／§8：ARTIFACT_READY 空專案仍 exit 0 |
| 34 | 17 全面守門（run_id 唯一／test-suite-fixture 映射／Evidence FK／PASS 必填 model・fixture_version／current result） | v1.4.1.3 稽核 §5 X01–X09 |
| 35 |（帳號段已由 ADR 39 移除）Mode 輸出隔離（未達 Gate 不覆寫 canonical，改寫 tools/reports/*.json） | v1.4.1.3 稽核 §6／§9 |
| 36 | Gate 數量改由結構化 Registry（24 PVE／39 Arena／41 Timeline）成熟且可追溯的列計算，假列不計 | v1.4.1.4 稽核 §5／§6：幾行假資料即可通過 Gate |
| 37 | Gate C 納入 blocking_gate_c_warnings=0＋新鮮度；warnings 於 Gate 計算前產生 | v1.4.1.4 稽核 §5：Gate C 未檢查阻擋警告 |
| 38 | 13 由 validator 依 17 current result 自動覆寫 AUTO_RESULTS 區；retest chain 語意守門 | v1.4.1.4 稽核 §8–§15 |
| 39 | **Guide-Only Scope Reset**：帳號層 REMOVED_FROM_ACTIVE_SCOPE（封存 archive ZIP）；18 為台服可用性唯一來源；25 隊伍層＋同五人去重＋24 team_count 一致；45／46 來源 Registry（社群 cap≤C）；Gate 重定義（B：PVE 2 關×5 隊＋Arena 5 防守×2 反制＋P-Arena 3＋Timeline 6＋社群來源 2；C：PVE 5 關＋Arena 10＋P-Arena 5） | 20260802 Guide-Only 稽核 §3–§12 |
| 40 | **逐來源操作軸**：26 以 `source_axis_id` 同時保存 STRUCTURED 與 SOURCE_GAP；只有 STRUCTURED 可擁有 `timeline_id` 與 27 steps。相同隊伍的不同來源不得合併或平均；跨服軸未在台服逐步重現時固定標 `UNVERIFIED_ON_TW` | v3.0 A2＋B2 信任邊界 |

## 已知債務（v1.4）

候選 #4 JP 側官方化＋8.5 直播內容精確段落＋08/09 後例行檢查（91 §1）；ev045–047／ev049／#3943 已完成正文回驗
｜Checkpoint B：紅焰／蒼波 8-10 均為 5/5，紅焰 10-10 現 0/5；Gate C 尚需至少 3 個成熟 PVE 關卡及解除 D 級單一來源 blocking warnings｜Checkpoint C：45 來源抓取＋41 社群共識欄
｜Checkpoint D：46 來源實測＋逐防守解陣（39）｜Checkpoint E：P-Arena 組合求解（成熟案例入 47）
｜18 On-Demand Registry 依需求擴充（採需求驅動，不建全角色 roster；筆數以 AUTO 統計為準）｜SYNC-004/005 官方確認｜Timeline 補至 6+｜台服官方譯名回填。

## Removed from Active Scope（封存於 archive ZIP；重啟條件見 ADR）

- 帳號資料匯入與個人化（含多帳號）：REMOVED_FROM_ACTIVE_SCOPE，非 Deferred
- 公開 Production Web／Artifact 發佈：BLOCKED_BY_RELEASE_GATE（私人 staging walking skeleton 已存在；Gate C 與應用 Gates 通過後才可公開）

## 維運

依 90；提示一律 91；證據一律 92；品質與 Gate 一律 15。
