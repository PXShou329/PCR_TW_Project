# 91 提示範本庫（PROMPT LIBRARY）

> 所有可直接貼入 Project 對話的提示，單一維護點。README 只保留指引。

## §1 版本基準更新（初始化＋例行）

```text
請執行版本基準更新（02_SERVER_BASELINE.md）：
1. 查證台服官網 news：最新卡池、活動、系統；2. 查證日服官網 information/update 同項目；
3. 有雙邊官方日期的內容 → 建立/更新錨點，重算差距區間與信心；
4. 官方事實、攻略站整理、社群推測分開標示；
5. 輸出可直接取代 02 對應段落的 Markdown＋99 紀錄列。不得以中國服資料補缺。
本輪另需補查（依 02 OPEN_GAPS SSOT）：ev045／ev046／ev047／ev049／#3943 官方直頁正文例行回驗；確認 2026/08/02 後台服主線／深域／專1/專2／六星是否有新更新（現況已驗證：主線第 3 部第 16 章、Lv373、深域第 10 區、最新六星涅婭）；候選 #4 的 JP 側官方化（TW 側已由 ev029 完成）；2–4 個新錨點、1–2 筆排程調整案例。無法直頁回驗者維持 PENDING_REVIEW。
```

## §2 術語查證

```text
請查證 03_NAME_GLOSSARY.md 內所有【待查證】名稱。
優先使用台服官方公告與日服官方遊戲用語；只有玩家俗稱時保留俗稱但不得標為官方譯名。
輸出可直接替換的表格列與來源。
```

## §3 新角色同步

```text
執行新角色同步（依 12_CHARACTER_SYNC.md 硬規則；本專案不保存帳號資料）：
1. 台服官網 news：上次同步日（____）後是否實裝新角色或開放專1／專2／六星／連結RANK？
   有 → 逐筆寫入 18_TW_CHARACTER_AVAILABILITY.csv：unit_key＋台服官方名＋tw_release_date＋
   availability_status=AVAILABLE＋source_evidence_ids；強化開放則逐項更新對應欄位。
   同一 unit_key 已存在時只更新欄位與 last_checked，不新增重複列。另確認 03 版本代碼是否需新增。
2. 日服官網：新實裝且台服未出的角色 → 更新 12「日服待實裝追蹤清單」（區間＋信心＋依據；
   同一角色已存在時只更新 last_checked 與狀態欄，不新增重複列）。
3. 全部標來源與查證日期；變更記 99。
```

## §4 PVE 案例簡報（Phase 2B 首三案，在 Project 內執行）

```text
Case P1｜當前深域標準關卡：
選擇台服當前深域一個代表性關卡（先查證台服深域進度），依 20 全流程研究：
關卡識別→多來源標準隊伍→Rank/專武/操作條件→依 21 建檔→登錄 22→23 記日誌。
不建立帳號分析段，直接輸出公共攻略（5–10 隊或不足揭露）。同時執行 T22、T23，結果寫入 17 後 `--mode OPERATIONAL --write` 生成 13。
```

```text
Case P2｜手動/時間軸關卡：
選擇一個需要手動或時間軸的高難關卡，重點驗證 YouTube/X/論壇來源：
單一來源標 D+【僅供參考】，兩來源以上一致升 C；記錄隨機因素。執行 T17（PVE 情境）並記 13。
```

```text
Case P3｜過期攻略：
取一筆舊 Rank 環境的攻略，依 21 過期條件判定：標過期風險→搜新版資料→比較差異。
執行 T24，結果寫入 17 後 `--mode OPERATIONAL --write` 生成 13。
```

## §5 競技場反制研究

```text
敵方防守隊如下（截圖/文字）：____
請依 30 流程：辨識五人與版本（不足先問）→防守核心→依 §6.1 詞庫+34 來源地圖搜尋理論反制
→多來源交叉→台服實裝檢查→輸出（目前為一般研究模式，只出【理論反制】）→33 記日誌。
```

## §6 公主競技場策略研究

```text
對手三隊資訊如下（含隱藏情況）：____
請依 35 流程：已知/推測分開→理論三隊（不重複、含出隊順序與理由、田忌賽馬評估）
→38 記日誌。純公共輸出：三隊全員 TW_AVAILABLE（依 18）、不重複、含來源；不宣稱任何帳號可用。
```

## §7 未來視更新／角色評估

```text
請依 40 流程評估：____（角色或時段）
1. 日服日期與來源；2. 套用 02 錨點輸出台服區間+信心；3. 依 42 各維度評估（含台服落地
時環境修正）；4. 卡池相對排序；5. 輸出四欄未來視＋通用資源規劃（§11；不套用任何個人資料）；
6. 寫入 41 的資料列＋44 日誌。
```

## §8 過期攻略重驗

```text
請重驗：____（guide_id 或 counter_id）
依 21/31 的過期條件檢查環境變化→重新搜尋現行資料→更新狀態（VERIFIED/STALE/REJECTED）
與 verified_date→同步 22/32 索引→99 留痕。
```

## §9 台服可用性補查（18 Registry）

```text
針對下列角色／強化執行 18 補查：（角色清單）
1. 台服官網 news 逐筆查證：實裝日、專1／專2、六星、連結RANK 開放狀態。
2. 查得 → 更新 18 對應欄位＋source_evidence_ids＋last_verified；查不得 → 維持 UNVERIFIED 並記 last_review_due。
3. 不推論、不假設可用；不詢問任何人的持有狀況。變更記 99。
```

## §10 驗收執行（v1.4 起分四個 Suite，各自獨立對話執行；輸入一律用 14 的 Fixture）

### §10.1 Suite Core

```text
執行 Suite Core 驗收（A1、A2、A3、T1、T2、T13、T16、T17）。
逐條使用 14_PUBLIC_TEST_FIXTURES.md 的 FX-CORE-* 固定輸入，對照 11 的必須／不得。
每條完成後輸出一列可直接貼入 17_TEST_EXECUTION_LOG.csv 的紀錄（21 欄）：
run_id,test_id,suite,fixture_id,fixture_version,exact_prompt,execution_date,model,
observed_result,evidence_ids,status,defect_id,retest_of,supersedes_run_id,is_current,reviewer,reviewed_at,
review_method,expectation_checklist,response_reference,notes
規則：run_id 唯一；test_id 屬 definition_set（Guide-Only 41）；suite／fixture_id 依 config 映射；
PASS 必填 fixture_version／model／exact_prompt／execution_date／observed_result／evidence_ids（存在於 92）／
reviewer／review_method=MANUAL_FIXTURE_REVIEW／expectation_checklist=ALL_PASS；FAIL 必附 defect_id；
唯一鍵＝test_id，每測試僅一列 is_current=Y（重測時 retest_of 指同測試前列、舊列改 N）。
**13 由 validator 依 17 的 current result 自動覆寫其 AUTO_RESULTS 區——使用者只貼 17，不手動改 13 狀態。**
主要檢索檔案：00、02、03、12、41、92、93。
```

### §10.2 Suite PVE

```text
執行 Suite PVE 驗收（T18、T22、T23、T24、T46、T47），輸入用 FX-PVE-*。
記錄格式同 §10.1。主要檢索檔案：18、20、21、22、23、24、25、02、92。
```

### §10.3 Suite Arena

```text
執行 Suite Arena 驗收（T25–T34、T48–T50），輸入用 FX-AR-*。
記錄格式同 §10.1。主要檢索檔案：18、30、31、32、33、34、35、36、37、38、46、01。
Guide-Only 紅線：任何宣稱「帳號可用」或把 JP_ONLY 當台服最終解，即為 FAIL。
```

### §10.4 Suite Gacha

```text
執行 Suite Gacha 驗收（T14、T35–T45、T51、T52），輸入用 FX-GA-*。
記錄格式同 §10.1。主要檢索檔案：40、41、42、43、44、45、12、02、92、93。
T41 數值必須精確等於 120。
T43 必須**即時讀取 02 的最新錨點統計**，不得在提示或回答中硬編碼舊 n 值；
目前基準應揭露：總 A/A 錨點 n、所採用軌道與該軌 n、差距範圍、中位數、信心、排程異動風險
（02 日後更新時，一律以 02 最新值為準）。
```

