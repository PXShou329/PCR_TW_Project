# 23 PVE 研究日誌（PVE RESEARCH LOG）

> 用途：每次關卡研究的稽核紀錄——搜尋詞、採用與拒絕的來源、攻略版本、去重與台服過濾結果、失敗與修正。
> 本檔是**研究稽核紀錄，不是回答模板**；回答格式依 `20_PVE_GUIDE_WORKFLOW.md`、資料格式依 `21_STAGE_GUIDE_SCHEMA.md`。

## 紀錄模板

```markdown
## YYYY-MM-DD — 關卡名稱

- 使用者問題：
- 查證伺服器：
- 搜尋詞：
- 採用來源：（含日期與可靠度）
- 拒絕來源與原因：（含中國服排除案例）
- 標準隊伍：（A／B／C 摘要）
- 台服可用性過濾（18）：
- 去重結果（相同五人合併數）：
- 實測結果：（使用者回報）
- 待處理：
```

## 日誌

## 2026-07-16 — Case P1 前置研究（紅焰的深域 8-10）

- 使用者問題：v1.4 Checkpoint D（開發輪，非使用者提問）
- 查證伺服器：TW（實裝確認）＋JP（攻略來源）
- 搜尋詞：公主連結 台服 深域冒險 進度 區域
- 採用來源：台服官網 3614（OFFICIAL／A，ev008）、2868（ev007）、日服官網深域頁（ev006）
- 候補來源（隊伍層，待逐頁讀取）：GameWith 深域各區攻略頁（MAJOR_GUIDE）、巴哈「台版深域關卡備戰表格」snA=36083（MULTI_PLAYER_REPORT，暫停更新、涵蓋區域待確認）
- 標準隊伍：未產出（搜尋摘要層無法取得完整五人＋條件；不虛構）
- 台服可用性過濾／去重：未進行（範例）
- 待處理：於 Project 內執行 91 §4 Case P1 → 完成後建 22 正式條目＋92 證據

（P2、P3 簡報見 91 §4；執行後於此登錄）

## 2026-08-02 — 紅焰深域 8-10（Checkpoint B 第一輪）

- 使用者問題：v1.5 Checkpoint B（開發輪・依 HANDOFF §8）
- 查證伺服器：TW（實裝＝ev008 第8區 2025/11/15）＋JP（攻略來源）
- 搜尋詞（節錄）：プリコネ 深域クエスト 8-10 攻略 編成／紅焔の深域 8-10 クリア編成／appmedia 深域 火 8-10／"火屬性深域" "8-10"（含 半自動・目壓 變體）／深域クエスト火 8-10 攻略編成動画／kamigame 紅焔／"ようやく属性スキルが6P"
- 採用來源：ev050（スマホゲームNavi全文開啟・旁證級D）；ev051／ev052（YouTube專片・摘要層D）；ev053（niconico實戰TL・開頁D）
- 無法存取（僅供發現・未作證據）：GameWith #507373／#507370（bot阻擋・01已註記此常態）；rwiki 編成801-810（robots禁抓）；wikiwiki yabaidesune（bot阻擋）；forum.gamer snA=37595／36479／36083 與 home.gamer aatwxd系列（bot阻擋）；YouTube直頁本輪速率限制（jkPXr3aUZZQ／tYwLvHHbKXo／ZXUDJm_AsSA／F39PkRIg0T4 待冷卻）
- 拒絕來源：Scribd之GameWith盜錄PDF（版權疑慮・非可重驗原始定位）；wikiwiki摘要層隊伍（無法歸屬關卡）
- 標準隊伍：候補1支（TM-F810-01＝ルイズマリー／ライラエル（クリスマス）／クローチェ（エアリアル）／ヴルム／リンド・魔法全自動）；另2支變體（ルイズなし軸＝ZXUDJm_AsSA、Corki JG軸＝tYwLvHHbKXo）已定位待成員確認
- 台服可用性過濾（18）：未執行PASS判定（五人皆不在18種子・無官方級查證→UNVERIFIED）；重要更正：原版ルイズマリー在專案內無台服狀態紀錄（41僅有サマー版ev033）→不得逕標JP_ONLY
- 去重結果：n/a（僅1支入檔）
- 待處理：(1)YouTube冷卻後開頁ev051／ev052／tYwLvHHbKXo補成員→有望3–4支 (2)逐人18補查（原版ルイズマリー台服實裝日優先）(3)定位煌靈台服8-10專片（Odysee鏡像頻道為替代管道）(4)8-10通關數<5之不足揭露已同步22／24

## 2026-08-02 — 紅焰深域 10-10（Checkpoint B 第一輪）

- 查證伺服器：TW（實裝＝ev029 2026/07/15）＋JP（2026/03/16・ev009）
- 搜尋詞（節錄）：プリコネ 深域 10-10 ボス 編成 2026／深域 火10-10 クリア／煌靈 深域 火 10-10／公主連結 深域 10-10 通關 台版
- 採用來源：ev029（關卡存在）；ev054（nicozon標籤73件全量清點＝火10-10缺席・風／闇10-10存在）；ev055（台服煌靈止步10-9）
- 無法存取：同上清單＋wikiwiki 紅焔の深域10（摘要層見多支五人隊但無法歸屬10-10・依鐵則不採）
- 標準隊伍：0支可追溯（不足揭露）；24列PROVISIONAL＋CLM-PVE-F1010-SCARCE
- 待處理：(1)持續監測JP側10-10影片（鬼たそ風／闇模式顯示火屬為最後缺口）(2)wikiwiki／rwiki開頁替代管道（例：Odysee型鏡像或人工引用）(3)台服第一批通關預期需追蹤巴哈

## 2026-08-02 — 火 8-10 候補隊逐人 On-Demand 補 18（Checkpoint B 第二輪）

- 目的：依 HANDOFF §8.3 對 TM-F810-01 五人逐筆查台服官方（不建全角色資料庫）
- 台服官方直頁**實際開啟**（三筆・OFFICIAL/A）：
  - #3529（2025/09/03）→ 露易絲瑪莉 2025/09/04 16:00 實裝＝ev056
  - #3500（2025/08/08）→ 克蘿茜（航空）2025/08/09 16:00 實裝＝ev057
  - #3313（2025/03/31）→ 萊拉耶爾（聖誕節）2025/04/01 16:00 實裝＝ev058
- 譯名解析：クローチェ→克蘿茜（≠クロエ→克蘿依，兩者為不同角色，勿混）；エアリアル→（航空）。台日對應以角色名＋同期劇情活動名（超鋼少女巨型克蘿茜）推論，日服直頁未取得→僅實裝日部分作 A 級事實，對應部分記於 93 備註
- 03 更新：ライラエル 台服官方譯名「萊拉耶爾」確立（原標社群譯待查證）
- 尚未查得：ヴルム、リンド（台服官方譯名未知；候選查法＝先取日服角色頁確認正式ローマ字／台服公主介紹頁比對）→ 整隊 tw_availability_check 維持 UNVERIFIED、不計有效隊
- 強化欄（專1／專2／六星／CR）全部未查證＝UNVERIFIED：本輪只解「有沒有這隻角」，未解「練度條件是否可達」
- 待處理：(1) ヴルム／リンド 台服查證 → 五人齊備才可能翻 PASS (2) YouTube 仍全面 429（jkPXr3aUZZQ 本輪再試仍限流）→ 成員層第二來源續等 (3) 41 的 ルイズマリー（サマー）與本輪原版為不同版本，兩者不得互相引用

## 2026-08-03 — R3 Step 1（TW 官方九頁計畫・逐頁實開）【歷史狀態；SUPERSEDED_BY_R3e — 請以本檔最末 R3e 區塊為準】

- 指令依據：使用者 Q1 選項1（九頁全部逐頁實開，不得依稽核文件或搜尋摘要採信）＋Q3 優先序（官方化五人 5/5 排第一）
- 指令衝突揭露與處置：Q1 規則7「本輪只處理九個官方 URL、不擴張搜尋」與 Q3 第2順位「找第2～5支隊伍」相衝突 → 依「具體執行規則優先」，九頁先行，隊伍搜尋本輪未啟動（誠實留待下輪）
- 技術限制紀錄：web_fetch 不接受未曾在對話出現的 URL（直接以稽核文件的 newsDetail/3247 組址被拒），故每頁須先以角色名搜尋使官方 URL 浮現再實開；此為流程成本，非資料問題
- **OPENED_AND_VERIFIED**：
  - #3247｜標題【轉蛋】《精選轉蛋》新角色「琳德」登場！機率UP活動舉辦預告！｜公告 2025.02.09｜轉蛋 2025/02/10 16:00～02/17 15:59｜官方角色名＝琳德（新角色・非期間限定）｜查證日 2026-08-03｜ev059／CLM-TW-LIND-REL
  - #3257｜標題【轉蛋】《精選轉蛋》新角色「烏爾姆」登場！機率UP活動舉辦預告！｜公告 2025.02.16｜轉蛋 2025/02/17 16:00～02/26 15:59（含02/21補充）｜官方角色名＝烏爾姆（新角色・非期間限定）｜查證日 2026-08-03｜ev060／CLM-TW-VURM-REL
- **NOT_ATTEMPTED（配額未及・非失敗）**：#3742（琳德／烏爾姆專1）、#3805（萊拉耶爾（聖誕節）專1）、JP information/28945・29132・29527・31430・31835
- 額外發現（未列入稽核文件）：
  1. 琳德／烏爾姆均為**常駐**新角（正文載明精選期後仍可能出現於白金轉蛋）→ 台服可用性比稽核假設更穩定，不需擔心限定復刻週期
  2. 官方 #3576（火屬性★3必中白金轉蛋・2025/10/10）出現角色清單同列琳德與烏爾姆 → 兩者為火屬性★3，與紅焰深域屬性需求相符；惟本輪僅取得搜尋摘要層，依 Q1 規則4 記為 ev061／D／PENDING_REVIEW，未作 A 級事實
  3. 部分媒體（technice）將「烏爾姆」誤植為「爾姆」，官方名以 #3257 為準
- 判定變更：TM-F810-01 之 tw_availability_check UNVERIFIED→**PASS**（5/5 皆 OFFICIAL/A）；clear_status 仍 **PROVISIONAL**，理由＝五人強化條件全 UNKNOWN＋通關證據僅 ev050 單一旁證級來源
- 25 結構化：依稽核 §6.3 要求，將整隊泛化句改為逐格欄位（slot1–5／support／timeline_ref／failure_conditions），未知一律標 UNKNOWN，不再以整隊概述代替
- 24 lifecycle 修正（稽核未抓到的一項）：依稽核 §8.5 自訂定義，8-10 有1支完整候選應為 PROVISIONAL、10-10 零候選應為 IN_RESEARCH，原檔兩者對調 → 已互換；team_count 均為0，Gate 不受影響
- 台日映射：**本輪一組都未建立**。TW 官方頁只能證明台服名稱與台服實裝，JP 頁未開 → 依 Q1 規則5 與 Q2 條件2，錨點升級整體延後，n 維持 2，未寫入任何 n=7 敘述

## 2026-08-03 — R3 Step 1 續（專用裝備1 兩頁）【歷史狀態；SUPERSEDED_BY_R3e】

- **OPENED_AND_VERIFIED**：
  - #3742｜標題【更新】角色專用裝備1追加！｜公告 2026.02.21｜生效 2026/02/22 16:00｜追加對象＝望（鍊金術師）／琳德／烏爾姆（官方註明「角色名無特定排序」）｜查證日 2026-08-03｜ev062／CLM-TW-LIND-VURM-UE1｜18 之 lind_orig／vurm_orig ue1_status UNVERIFIED→AVAILABLE
- **FAILED_TO_OPEN**：#3805（萊拉耶爾（聖誕節）專1）
  - 兩次精準搜尋（「角色專用裝備1追加 萊拉耶爾 2026」、「"2026/04/10 16:00起" 角色專用裝備１」）皆未使該 so-net URL 浮現；web_fetch 不接受未浮現之 URL → 無法實開
  - 僅取得間接線索：GNN sn=303152 轉載「2026/04/10 16:00 起追加角色專用裝備1」但角色清單被截斷、未點名萊拉耶爾；官方 #3813（2026/04/15 更新）提及大師商店追加「萊拉耶爾（聖誕節）的記憶碎片」為相關但非同一事實
  - 處置：依 Q1 規則4，**不建立 Evidence、不標 A**，18 之 lailael_xmas.ue1_status 維持 UNVERIFIED；稽核文件 §3.5 之假設保留為待驗證項，下輪可改由官方最新消息列表逐頁翻找或等該頁被搜尋引擎重新索引
- 重要邊界（同稽核 §3.4）：#3742 只證明 UE1「存在且可製作」，**未**載明任何等級數值 → 不得推論隊伍所需 UE1 等級、專2、六星、CR 或全自動可重現性；25 逐格欄位中 ue1 仍為 UNKNOWN（「可取得」≠「已達隊伍需求等級」）
- 本輪 TW 官方頁累計：4 頁計畫中 **3 頁 OPENED_AND_VERIFIED、1 頁 FAILED_TO_OPEN**；JP 五頁 NOT_ATTEMPTED（配額）

## 2026-08-03 — R3 報表殘留清除（稽核 §8.1–8.4）＋一項自我更正

- **產生器層修正（稽核未指出的關鍵）**：15 的「P-Arena n（38）」與 16 的「數量由 24／39／41 成熟列計算」皆由 tools/validate_project.py 第491／503行生成，改 .md 會被 --write 覆寫 → 已改產生器：（38）→（47）、來源清單→24／39／41／45／47（對應 PVE_V／ARENA_F／TIMELINE／community_checked／parena 五個實際輸入）
- **15 手動敘述**：依本檔開頭「區塊外不得重複統計數字」規則，移除全部手寫數字改為指向 AUTO 區與 config。清除的錯誤比稽核清單更多：
  - 「P-Arena 3/3 ✔」→ 實際門檻 gate_thresholds.B.parena=3、現值 0，原文把**未達標示為已達**（最嚴重的一項）
  - 「Arena 0/2」→ 實際 B.arena=5（2 是 counters_per_defense，被誤當關卡數）
  - 「Timeline 目標 4」→ 實際 B.timeline=6
  - 「P-Arena 理論案例 3」→ 現行由 47 計算＝0
- **44**：「帳號模式：一般研究模式」→「評估範圍：公共評價範圍（Guide-Only，不涉個人帳號）」；「未套用帳號資料」→「通用資源規劃（非個人化建議）」
- **14**：A3「尚未套用帳號資料」→「公共角色評價範圍」；T33「未載入聲明」→「資料範圍聲明（公共資料，非帳號可用性）」。A1／A2 的產品邊界測試（禁止要求帳號、本專案不保存帳號資料）**依稽核 §8.4 保留**
- **自我更正（§16）**：ev061（火屬性★3清單）上一輪誤標 OFFICIAL／A，但其 limitations 同時自承僅搜尋摘要層 → 與 CLM-TW-CROCE-AERIAL-REL 被稽核指出的內部矛盾同型。依 Q1 規則4 改為 UNKNOWN／D／PENDING_REVIEW。影響：琳德與烏爾姆之火屬性目前無 A 級支撐，不得作為隊伍合理性的正式依據；#3576 直頁回驗後可升級
- 殘留掃描（帳號模式／未套用帳號資料／（38）／3/3 ✔／理論案例 3）於 15／16／44／14／產生器全部歸零

## 2026-08-03 — R3 JP 官方頁（台日映射）第一批【歷史狀態；SUPERSEDED_BY_R3e — 該段所述「Mapping＝A」與「JP 3/5」均已被下方 R3e 取代】

- 指令依據：Q1（九頁逐頁實開）＋Q2（五組全數完成才升 n=7）
- **OPENED_AND_VERIFIED（3／5）**：
  - #28945｜新キャラ「リンド」登場！ピックアップガチャ開催！｜2024.10.10｜PU 2024/10/10 12:00～10/18 11:59｜常駐（PU後續留プラチナガチャ）｜ev063
  - #29132｜新キャラ「ヴルム」登場！…【2024/10/24追記】｜2024.10.18｜PU 2024/10/18 12:00～10/28 11:59｜常駐｜ev064
  - #31430｜期間限定キャラ「クローチェ（エアリアル）」登場！…｜2025.04.08｜PU 2025/04/08 12:00～04/15 14:59｜期間限定｜ev065
- **NOT_ATTEMPTED（2／5）**：information/29527（ライラエル（クリスマス））、information/31835（ルイズマリー）——配額未及
- **映射方法升級（本輪最重要成果）**：不再靠譯名相似，改用**非譯名鎖定證據**
  - リンド／琳德・ヴルム／烏爾姆：兩服角色劇情解鎖條件完全相同＝「メインストーリー第3部 第9章 第9話」／「主線劇情第3部第9章 第9話」；且兩服皆為常駐新角、成對推出、順序一致（JP リンド→ヴルム 間隔8日；TW 琳德→烏爾姆 間隔7日）→ CLM-LOC-LIND／CLM-LOC-VURM（A）
  - クローチェ（エアリアル）／克蘿茜（航空）：解鎖條件為同一劇情活動第6話，活動名逐字對應且含特徵數字「4.1秒前」→ CLM-LOC-CROCE-AERIAL（A）
- **稽核 §4.1 矛盾修正**：CLM-TW-CROCE-AERIAL-REL 原併含「台服實裝＋日服對應」卻在 notes 自承對應非 A。已拆分：該 Claim 現僅含台服實裝事實（A／ev057），映射獨立為 CLM-LOC-CROCE-AERIAL（A／ev057+ev065）。R3 驗收條件「不再存在 Claim=A 但 notes 說部分不是 A」就此項達成
- **獨立驗算（未抄稽核數字）**：リンド 2024-10-10→2025-02-10＝**123**；ヴルム 2024-10-18→2025-02-17＝**122**；クローチェ 2025-04-08→2025-08-09＝**123**。三值與稽核 §5 表一致
- **錨點未升級**：依 Q2 條件2，五組僅完成三組 → **不得宣稱 n=7**，02／40／41／Config／stats 一字未動，n 維持 2；三組已驗證 Evidence／Claim 先行保存
- **方法論風險（稽核未提，提請下輪決策）**：待補的五組中，リンド／ヴルム 為**常駐新角**，クローチェ（エアリアル）／ライラエル（クリスマス）／ルイズマリー 為**期間限定**。若現行「卡池軌」未區分常駐與限定，將兩類延遲混入同一統計可能是方法論錯誤（代理商對限定角的排程彈性通常不同）。建議升級前先確認現有 n=2 錨點的角色類型，必要時拆為「常駐軌」與「限定軌」兩條

### 補記：映射 Claim 型別更正（validator 攔截）

- 首次寫入將 CLM-LOC-LIND／VURM／CROCE-AERIAL 標為 ANALYTICAL_JUDGMENT／A，被 **ST50** 攔下（FAIL=1）：A 級 Claim 僅允許 SOURCE_FACT（需 OFFICIAL＋A 證據）或 DERIVED_CALCULATION（全 A 證據＋推導註記），分析判斷不得為 A
- 更正為 **DERIVED_CALCULATION／A** 並補推導註記。判斷理由：映射非任一官方頁直接陳述，而是由兩筆 A 級官方事實推導；此為 schema 中對應「雙官方輸入之確定性推導」的型別
- **提請覆核**：若使用者認為映射仍應視為分析判斷，正確作法是降為 B（ANALYTICAL_JUDGMENT／B），ST49 之雙獨立來源條件已滿足（so-net 與 priconne-redive.jp 為不同 host）。此選擇會影響錨點是否符合「A/A 對照」門檻，故列為決策點而非逕行決定


# ===== R3e 狀態區塊【SUPERSEDED_BY_R3f — 請以本檔最末 R3f 區塊為準】 =====

## R3e Phase B — TW #3805（萊拉耶爾聖誕專1）

- 狀態：**FAILED_TO_OPEN（URL_NOT_SURFACED）**
- 嘗試紀錄（2026-08-03）：累計 3 次搜尋，用詞＝「角色專用裝備1追加 萊拉耶爾 2026」／「"2026/04/10 16:00起" 角色專用裝備１」／「專用裝備 萊拉耶爾 伊緒 琪愛兒 追加 2026年4月」；三次皆未使 so-net #3805 浮現（僅浮現 #3742／#3890／#3891），web_fetch 不接受未浮現 URL
- 依使用者裁決（最嚴格）：**不依開發工單引述建立 Evidence**、不建 PENDING_REVIEW／D、不標 OFFICIAL/A。lailael_xmas.ue1_status 維持 **UNVERIFIED**
- 本輪不再重試；下輪可換管道（官方最新消息列表逐月翻頁）

## R3e Phase C — JP 官方頁

- **OPENED_AND_VERIFIED（4/5 累計）**：#28945 リンド（2024-10-10）／#29132 ヴルム（2024-10-18）／#31430 クローチェ（エアリアル）（2025-04-08）／**#29527 ライラエル（クリスマス）（2024-11-30，本輪新增）**
- **NOT_ATTEMPTED（1/5）**：#31835 ルイズマリー — 本輪配額用於 Phase D／E 收尾，未嘗試；不得視為已驗證
- 獨立驗算：ライラエル 2024-11-30→2025-04-01＝**122** 天

## R3e Phase D — Mapping Claim 邊界修正

- CLM-LOC-LIND／VURM／CROCE-AERIAL：DERIVED_CALCULATION／A → **ANALYTICAL_JUDGMENT／B**，server＝CROSS_SERVER_MAPPING，independence_check＝YES
- 新增 CLM-LOC-LAILAEL-XMAS（B）
- **P0-2 誠實修正**：リンド與ヴルム共用同一劇情解鎖條件、琳德與烏爾姆亦同 → 該證據僅能鎖定角色**對**{リンド,ヴルム}↔{琳德,烏爾姆}，個別配對改由名稱音譯、兩服推出順序、成對脈絡與常駐屬性完成。原「非譯名證據已鎖定個別角色」為過度宣稱，已於 notes 全面改寫
- **P0-5**：CLM-TW-LAILAEL-XMAS-REL 與 CLM-TW-LUISE-ORIG-REL 移除混入之跨服映射內容，改為純台服事實
- **新規則 ST82**（CHECKS 105→106）：CLM-LOC-* 必須 ANALYTICAL_JUDGMENT、不得為 A、independence_check＝YES、須同時引用 TW 與 JP Evidence 且來自不同 host、notes 不得以「計算」描述且須載明比對依據
- **新 Mutation M42**（36→37）：將任一 CLM-LOC-* 改為 DERIVED_CALCULATION/A → 必須 FAIL（已驗證攔截成功）
- 自我攔截紀錄：ST82 首次執行即擋下我自己撰寫的 notes（含「非計算」字樣觸發禁字檢查），改寫為「record linkage 判斷，非數學運算」後通過

## R3e 未完成（明確揭露）

1. TW #3805 未實開 → lailael_xmas UE1 仍 UNVERIFIED，TW 官方頁 **3/4** 非 4/4
2. JP #31835 ルイズマリー 未嘗試 → JP **4/5** 非 5/5；CLM-JP-LUISE-ORIG-REL 與 CLM-LOC-LUISE-ORIG **未建立**
3. Phase F（卡池三軌 ALL_NEW／LIMITED／PERMANENT、anchors 物件化）：本輪範圍外，n 維持 2，02／40／41／config 未動
4. Phase G（TM-F810-01 operation_mode＝SOURCE_CONFLICT、逐 slot requirements）：本輪範圍外，維持原狀
5. Phase H（紅焰 8-10 第 2～5 支隊伍搜尋）：本輪範圍外，未執行


# ===== R3f Phase E 區塊【SUPERSEDED_BY_R3f_PRE_PHASE_F — 請以本檔最末區塊為準】 =====

## R3f Phase B1 — TW #3805（萊拉耶爾聖誕專1）

- 狀態：**FAILED_TO_OPEN（URL_NOT_SURFACED）**，累計第 4 次嘗試
- 本輪搜尋詞：「so-net 超異域公主連結 最新消息 【更新】角色專用裝備1追加！ 萊拉耶爾（聖誕節） 琪愛兒（冬日）」
- 結果：浮現同標題之其他期別（#3882／#3742／#3533）與 #3813、#3890／#3891，唯獨 #3805 未浮現；web_fetch 不接受未浮現 URL
- 間接線索（不作證據）：官方 #3813（2026/04/15 更新）載明大師商店追加「萊拉耶爾（聖誕節）的記憶碎片」「琪愛兒（冬日）的記憶碎片」，與 UE1 開放時序相符但非同一事實
- 依裁決：不建立 Evidence、不採信工單引述、`lailael_xmas.ue1_status` 維持 **UNVERIFIED**

## R3f Phase B2 — JP #31835（ルイズマリー）

- 狀態：**OPENED_AND_VERIFIED** → **JP 官方角色頁 5/5 完成**
- 正文：公告日 2025.05.03｜PU 2025/05/03(土) **19:00** ～ 2025/05/15(木) 14:59（開池 19:00，非慣例 12:00）｜期間限定
- Evidence／Claim：ev068／CLM-JP-LUISE-ORIG-REL（SOURCE_FACT／A）／CLM-LOC-LUISE-ORIG（ANALYTICAL_JUDGMENT／B）
- Mapping discriminator：兩服同期自選獎勵轉蛋候補**六人逐一同序對應**（JP ワカナ／ヤマト／フブキ／ノゾミ（アルケミスト）／キョウカ（スプリング）／スズメ（スプリング）＝TW 若菜／倭／布武機／望（鍊金術師）／鏡華（春日）／鈴莓（春日））；另有大師碎片×3、記憶碎片×200 規則一致
- 獨立驗算：2025-05-03 → 2025-09-04 ＝ **124** 天

## R3f Phase C — Evidence／Claim 邊界清理

- ev056 移除 summary 內「（＝ルイズマリー原版）」跨服推論；ev057／ev058 limitations 改為「本頁僅確立台服事實，跨服對應由 CLM-LOC-* 獨立判斷」
- CLM-TW-CROCE-AERIAL-REL（不再稱 Mapping 為 A）／CLM-TW-LIND-REL／CLM-TW-VURM-REL（移除「日服未證實」）／CLM-TW-LAILAEL-XMAS-REL（移除條件式舊敘述）／CLM-TW-LUISE-ORIG-REL（dangling reference 解除）

## R3f Phase D／E — 舊錨點 Claim SSOT

- **Evidence eligibility check（六筆）**：ev001／ev003／ev004／ev027／ev028 皆為官方直頁＋完整 locator＋A／ACTIVE → 合格沿用；**ev002 不合格**（source_url 僅 https://princessconnect.so-net.tw/news 新聞列表首頁、locator 空白）
- 新增（沿用既有已驗證 Evidence，**本輪未重新開啟直頁**，verified_date 保留原值，未宣稱 OPENED_AND_VERIFIED_IN_R3F）：
  - CLM-JP-SHIORI-WINTER-REL（A／ev027）＋CLM-LOC-SHIORI-WINTER（B／ev027+ev028）；TW fact 沿用既有 CLM-TW-SHIORI-POOL
  - CLM-JP-EXPT-REL（A／ev003）＋CLM-TW-EXPT-REL（A／ev004）＋CLM-LOC-EXPT-MECHANISM（B／ev003+ev004）
  - CLM-JP-WAKANA-WINTER-REL（A／ev001）
- **若菜（冬日）anchor 目前不完整**：因 ev002 不合格，未建立 CLM-TW-WAKANA-WINTER-REL 與 CLM-LOC-WAKANA-WINTER。Phase F 前必須先實開台服 #3925 修正 ev002，否則該 anchor 不得納入有效統計（將使 LIMITED 由 n=5 降為 n=4、ALL_NEW 由 n=7 降為 n=6）
- 舊 CLM-ANCHOR-WAKANA／SHIORI／EXPT **維持 ACTIVE 未切 SUPERSEDED**：依 checkpoint 條件，替代 Claims 完整前不正式切換（WAKANA 一組尚未完整）
- config **未動**（仍為 R3e 舊 schema：裸陣列＋anchor_median／pool_track／pool_track_median）；Phase F 一次性原子遷移留待下輪

## R3f 未完成（明確揭露）

1. TW #3805 → UE1 仍 UNVERIFIED；TW 計畫頁 3/4
2. ev002 未修正 → 若菜 anchor 不完整，**Phase F 前置未滿足**
3. Phase F（anchors 物件化、三軌統計、config 舊鍵移除、ST83／ST84、M43／M44）：本輪範圍外，未開始
4. Phase G（TM-F810-01 operation_mode／逐 slot requirements）：未做
5. Phase H（紅焰 8-10 第 2～5 支隊伍）：未做


# ===== R3f pre-Phase-F 區塊【SUPERSEDED_BY_R3g】 =====

## Phase 0 — 基線與快照

- 由 checkpoint ZIP 重新解壓乾淨副本：46 檔、單一根目錄
- 五命令基線：PRE_SUITE --write／read exit=0（CHECKS=106 FAIL=0 WARN=16 canonical=Y）｜OPERATIONAL exit=0 FAIL=0｜ARTIFACT_READY exit=1 且僅 3 個 Gate FAIL｜Mutation ALL_OK 37/37
- 已建立 pre_phase_f 回滾快照，**置於工作樹外**（避免變動 46 檔約束）；Account Archive 未進入工作樹

## Phase 1.2 — TW #3925（若菜（冬日）官方直頁）

- 狀態：**FAILED_TO_OPEN（URL_NOT_SURFACED）**
- 本輪嘗試（2026-08-03，共 2 次）：
  1. 「so-net 超異域公主連結 「若菜（冬日）」 精選轉蛋 期間限定角色 登場 2026年7月」→ 浮現 #3294（若菜原版 2025/03/19）、#3526、新聞列表首頁，未見 #3925
  2. 「"若菜（冬日）" 精選轉蛋 機率UP 舉辦預告 超異域公主連結 newsDetail」→ 僅浮現 GNN sn=301102（日版 2026/03/03 追加報導）與 App Store 頁，未見 #3925
- web_fetch 僅接受曾於對話中浮現之 URL，故無法實開
- 依裁決與工單 §13：**不修正 ev002 為直頁**、**不建立 CLM-TW-WAKANA-WINTER-REL**、**不建立 CLM-LOC-WAKANA-WINTER**、**不啟動 Phase F**
- 觀察：2026 年份之 so-net newsDetail 頁（#3805、#3925）在本工具環境搜尋索引中反覆無法浮現，而 2025 年份頁（#3294、#3526、#3742）可正常浮現。下輪建議改以官方新聞列表分頁（https://www.princessconnect.so-net.tw/news）逐月導覽方式取得直頁連結，而非關鍵字搜尋

## 本輪未執行（配額）

- #3805（萊拉耶爾專1）：本輪未再嘗試；前 4 次皆 URL_NOT_SURFACED，`lailael_xmas.ue1_status` 維持 UNVERIFIED
- #35568（JP 若菜）：未嘗試 → **ev001 的 published_date=2026-02／MONTH 缺陷未修**
- #3940（栞 TW）／#34623（JP 交換Pt）／#3765（TW 交換Pt）：未嘗試

## 日期語意風險複核（本輪唯一實質新增結論）

實查 92 現值後，先前對「公告日誤用為開池日」可能擴散的疑慮**大部分解除**：

| Evidence | published_date（公告日） | 錨點使用日期 | 判定 |
|---|---|---|---|
| ev028（栞 TW #3940） | 2026-07-16 | 2026-07-17 | 已分離，語意正確 |
| ev003（JP #34623） | 2025-12-26 | 2025-12-31 | 已分離，語意正確 |
| ev004（TW #3765） | 2026-03-15 | 2026-03-16 | 已分離，語意正確 |
| ev001（JP #35568） | 2026-02（MONTH） | 2026-03-03 | **精度缺陷，待實開修正** |
| ev002（TW，無直頁） | — | 2026-07-03 | **語意錯誤，待 #3925 修正** |

另佐證：本對話實開之 5 筆台服直頁（#3247／#3257／#3313／#3500／#3529）公告日皆為開池日前一日，18 內對應 5 筆 tw_release_date 全部取開池日，正確。故日期語意問題**僅侷限於若菜一筆**，不需為其餘 anchors 重開頁面湊數。

## Phase F 啟動條件現況

```
#3925 成功            → 否（FAILED_TO_OPEN）
若菜 TW Fact 完整      → 否
CLM-LOC-WAKANA-WINTER → 未建立
七筆卡池 anchors 齊備  → 否（6/7）
```
**結論：Phase F 前置未滿足，本輪不啟動，config 維持 R3e 舊 schema 未動一字。**


# ===== R3g claims-ready 區塊【SUPERSEDED_BY_R3h】 =====

## ST60 跨日語意修正（本輪 P1，與 Phase F 無關）

- **誠實限制**：本執行環境容器日期為 2026-08-03，落後真實日期一日，**無法自然重現**工單 §2 所述跨日 FAIL。改以人工將 13 生成日改為過去日期進行等價測試
- 修正內容：ST60 比對前先正規化「生成日 YYYY-MM-DD」；實質內容一致而僅生成日落後 → 產生 `REPORT-STALE-DATE`（severity=info、blocks_gate_c=False）並提示執行 --write；任何實質 canonical drift 仍 FAIL
- ARTIFACT_READY **未**新增「必須當日生成」硬要求（依裁決，否則交付包仍會隔夜失效）
- 自我攔截紀錄：初版將 blocks_gate_c 傳字串 "N"（truthy）導致 blk 由 7 誤增為 8，已改傳 False；初版 M46 替換目標在 AUTO 區外未命中，改為竄改區內 NOT_RUN→PASS（偽造通過狀態，最危險漂移型態）
- 新增 Mutation：M45（純生成日漂移→須 PASS）、M46（實質狀態竄改→須 FAIL）；active_scenarios 37→**39**

## Phase 1 官方頁

- **JP #35568 OPENED_AND_VERIFIED**（2026-08-04）：公告日 2026.03.03｜PU 2026/03/03(火)12:00～03/16(月)09:59｜期間限定｜角色劇情第1話需活動「爆熱！ピーチクラッシュ・トーナメント ワカナ＆シオリのHIP＆SPLASH」エンディング
- **TW #3925 OPENED_AND_VERIFIED**（2026-08-04）：公告日 2026.07.03｜精選轉蛋 **2026/07/04 16:00**～07/17 15:59｜期間限定｜角色劇情第1話需活動「爆熱！蜜桃碰撞淘汰賽 若菜＆栞的HIP＆SPLASH」終幕
  - **取得方法（關鍵經驗）**：關鍵字搜尋累計失敗 3 次後停用，改以官方新聞列表分頁導覽 `https://www.princessconnect.so-net.tw/news?page=5` 一次命中 2026.07.03 批次並取得 #3925 直頁連結。2026 年份 so-net 頁在搜尋索引中不可靠，**列表導覽為正確管道**，僅耗 2 次 fetch
- **TW #3805 NOT_ATTEMPTED**（配額）：`lailael_xmas.ue1_status` 維持 UNVERIFIED。下輪可循同一列表管道翻至 2026 年 4 月批次取得
- 獨立驗算：JP 2026-03-03 → TW 2026-07-04 ＝ **123** 天

## Phase 2 Evidence／Claim

- ev001：`published_date` 2026-02／MONTH → **2026-03-03／DAY**；補 locator `jp_official_35568`；verified_date→2026-08-04
- ev002：URL 由新聞列表首頁 → **#3925 官方直頁**；locator 空白 → `tw_official_notice_3925`；claim_summary 分離公告日 2026-07-03 與開池日 2026-07-04
- 新增 `CLM-TW-WAKANA-WINTER-REL`（SOURCE_FACT／A／ev002）
- 新增 `CLM-LOC-WAKANA-WINTER`（ANALYTICAL_JUDGMENT／B／ev001+ev002／independence=YES），discriminator 為活動名逐字對應＋自選候補四人同序對應

## Phase 3 Phase F 遷移 manifest（規格，非 current SSOT）

八筆 anchor objects 預定值；**本輪未寫入 validation_config，config 仍為舊 schema**：

| anchor_id | track | pool_class | JP | TW | delta | FK 三件是否齊備 |
|---|---|---|---|---|---:|---|
| POOL-WAKANA-WINTER | GACHA | LIMITED | 2026-03-03 | **2026-07-04** | **123** | ✅（本輪補齊）|
| POOL-SHIORI-WINTER | GACHA | LIMITED | 2026-03-16 | 2026-07-17 | 123 | ✅ |
| POOL-LAILAEL-XMAS | GACHA | LIMITED | 2024-11-30 | 2025-04-01 | 122 | ✅ |
| POOL-CROCE-AERIAL | GACHA | LIMITED | 2025-04-08 | 2025-08-09 | 123 | ✅ |
| POOL-LUISE-ORIG | GACHA | LIMITED | 2025-05-03 | 2025-09-04 | 124 | ✅ |
| POOL-LIND | GACHA | PERMANENT | 2024-10-10 | 2025-02-10 | 123 | ✅ |
| POOL-VURM | GACHA | PERMANENT | 2024-10-18 | 2025-02-17 | 122 | ✅ |
| SYSTEM-EXCHANGE-PT-ITEMS | SYSTEM | SYSTEM | 2025-12-31 | 2026-03-16 | 75 | ✅ |

**Phase F 前置條件現況：八筆 FK 全部齊備 → 下輪可啟動原子遷移。**

## 本輪明確未做（Phase F 全段）

config 仍含 `anchors` 裸陣列／`anchor_median`／`pool_track`／`pool_track_median`；四軌統計未啟用；ST83／ST84／M43／M44 不存在；M27 未遷移；02／12／18／40／41／44 的若菜日期仍為 07/03、卡池軌仍 n=2／median 122.5——**這些必須在 Phase F 同一原子切片內一次修正**，本輪刻意不做部分修改以免產生新舊口徑並存。


# ===== R3g Phase F 原子遷移完成區塊（2026-08-04）【版本標籤更正：原記 R3h Phase F，實際交付 artifact 為 R3g】【SUPERSEDED_BY_R3h_P0】 =====

## 遷移範圍（單一原子切片，全部在同輪完成）

1. `validation_config.json`：`anchors` 由裸陣列 → **八筆 canonical anchor objects**；一次移除 `anchor_median`／`pool_track`／`pool_track_median`，無雙寫、無 DEPRECATED 並存
2. Validator：移除舊裸陣列解析與三個舊 key 依賴；新增 **ST83**（schema／enum 組合／FK 三件／delta 重算／anchor_id 唯一）、**ST83a**（舊 key 復活即 FAIL）、**ST84**（四軌即時統計並比對 02／40 口徑）、**ST84a**（SYSTEM 不得混入卡池軌）
3. 舊硬編碼檢查替換：`ST40` 由「02 須含 n＝3」改為「須含 ALL_NEW：n＝」；`02＝n=3 分軌` 改為 **舊口徑殘留掃描**（卡池軌：122、123／n＝3／中位數 122 天／pool_track／07-03 122 天 任一殘留即 FAIL）
4. 報表模板的 `{anch}`／「中位數 122／122.5」硬字串 → 改為由 TRACKS 即時派生
5. `stats.json`：`pool_track_n`／`sys_track_n` → **`anchors_n` + `anchor_tracks`（四軌完整 values/n/median/min/max/range）**
6. Mutation：新增 M43（缺 mapping_claim_id）／M44（delta 與日期不符）／M47（偷加回三個舊 key）／M48（SYSTEM 改標 LIMITED）；**M27 由已 SUPERSEDED 的 CLM-ANCHOR-WAKANA 遷移至 CLM-TW-WAKANA-WINTER-REL**。37→**43** 情境全通過
7. 文件同步：02（錨點#1 改 2026/07/04＋123 天、統計改四軌區塊）、12（SYNC-001 開池日與 anchor 名）、18（wakana_win 2026-07-03→**2026-07-04**）、40（引用須指明軌道別＋四軌區塊；預估區間**未**擅自收窄）、41（anchor_track→LIMITED、anchor_count→5、forecast_basis 揭露 median/range/mapping_conf=B）
8. Claims：`CLM-ANCHOR-WAKANA`／`SHIORI`／`EXPT`、`CLM-GAP-POOLTRACK`／`SYSTRACK` 全部 **SUPERSEDED**；新增 `CLM-GAP-LIMITED`／`PERMANENT`／`ALL-NEW`／`SYSTEM`（DERIVED_CALCULATION／**B**，notes 載明計算式、輸入 anchor IDs、非官方直接公布、上限 B 之理由）

## 遷移過程的自我攔截（四次）

- `collections.Counter` 未 import → 改用檔內既有 `Counter`
- ST84 首次 FAIL：02／40 尚未同步 → 這正是設計意圖（文件與 anchors 必須同口徑）
- 兩個舊硬編碼檢查（ST40、02＝n=3）在移除舊 key 後 FAIL → 依 §16.3 改寫為派生式
- 報表模板殘留 `{anch}` 造成 NameError → 一併遷移

## #3805（順手項，未成功）

- 循列表管道嘗試 `?page=13` 意圖跳至 2026 年 4 月批次，**伺服器將 page 參數箝制回 page=5**（回應 destination_url 為 page=5 可證），分頁上限為 5，無法直接跳頁
- 逐頁走訪（page=6,7,8…）成本過高，本輪停止 → **FAILED_TO_OPEN**，`lailael_xmas.ue1_status` 維持 UNVERIFIED
- 下輪建議：以 `下一頁` 連續導覽並在單輪預留 4–6 次 fetch，或改由官方 FB 貼文回溯

## 四軌統計（由 anchors 即時重算）

```
LIMITED   values=[122,123,123,123,124] n=5 median=123   min=122 max=124 range=2
PERMANENT values=[122,123]             n=2 median=122.5 min=122 max=123 range=1
ALL_NEW   values=[122,122,123,123,123,123,124] n=7 median=123 min=122 max=124 range=2
SYSTEM    values=[75]                  n=1 median=75    min=75  max=75  range=0
```


# ===== R3h-P0 現行區塊（2026-08-07；本檔以下為最新） =====

## Phase A 基線（自本次實際 R3g ZIP 解壓）

- 輸入 ZIP SHA-256＝`5fff94c3c0c9520cc46ff5bc993d9621d4e4b144b6baa5619837ea98d706f25a`｜46 檔｜單一根目錄
- PRE_SUITE exit=0（CHECKS=107 FAIL=0 WARN=16）｜OPERATIONAL exit=0｜ARTIFACT_READY exit=1 僅 Gate A/B/C｜Mutation 43/43
- 註：本輪 tree hash 演算法（path＋sha256 串接後再雜湊）與稽核端不同，數值不可直接比對，非內容差異

## Phase B — TW #3805：**FAILED_TO_OPEN（結構性不可達）**

- 關鍵字搜尋累計 5 次失敗（本輪 1 次：「so-net 公主連結 newsDetail 3805 角色專用裝備1追加 萊拉耶爾 伊緒 琪愛兒」→ 浮現 #3244／#2609／#3891／#3813／#3105 等同類公告，唯獨 #3805 未浮現）
- 列表導覽本輪確認**存在硬上限**：`?page=13` 與 `?page=17` 皆被伺服器箝制回 `page=5`（回應 destination_url 可證），列表僅暴露最近約 50 則（最舊到 2026-06-30），2026-04-10 的 #3805 **無法經此管道到達**
- 依裁決：不建立 Evidence、不採信工單引述，`lailael_xmas.ue1_status` 維持 **UNVERIFIED**
- 下輪唯一可行方向：官方 FB 貼文回溯、或取得可直接指向 #3805 的外部連結後再實開

## Phase C — 41 schema 遷移（31→35 欄）

- 新增：`model_estimate_start`／`model_estimate_end`（緊接 jp_date）、`forecast_method`（緊接 tw_estimate_end）、`forecast_notes`（末欄）
- **forecast_basis 改為機器生成 canonical provenance 字串**，唯一生成函式 `build_forecast_basis(track)`：
  `LIMITED track | n=5 | median=123 | range=122-124 | mapping_conf=B | source=canonical anchors`
- 人工說明全數移入 `forecast_notes`，該欄不得寫統計數字
- 三列 model interval（jp_date＋[122,124]，獨立計算）：
  | event_id | JP | model | final（MODEL_ONLY） |
  |---|---|---|---|
  | JP_20260630_shefi_vardrache | 2026-06-30 | 2026-10-30～11-01 | 同左 |
  | JP_20260703_luisemarie_summer | 2026-07-03 | 2026-11-02～11-04 | 同左 |
  | JP_20260731_fubuki_summer | 2026-07-31 | 2026-11-30～12-02 | 同左 |
- 舊人工寬區間（10/25–11/10、10/28–11/15、11/30–12/01）**無 provenance**，依方法論移除並記於 forecast_notes 與本日誌
- `csv_specs['41_GACHA_TIMELINE.csv'].cols` 31→**35**
- **Fixture dependency 精確搜尋結果：11／14 完全未引用 41**（grep `41_GACHA_TIMELINE`／`forecast_basis`／`tw_estimate_start`／`anchor_count`／`anchor_track` 命中檔為 00／23／40／90／99／README／tools/*），依裁決選 2 **不動 Fixture**

## Phase D — Validator（CHECKS 107→109）

- **ST85**：ACTIVE 列之 anchor_track 合法、anchor_count＝TRACKS[n]、forecast_basis **完全等值** canonical、model interval 由 jp_date＋TRACK.min／max 重算、start≤end
- **ST85a**：forecast_method enum；MODEL_ONLY 時 final 必須等於 model 且不得有 community source；MODEL_PLUS_COMMUNITY 需 community 區間且 final 至少為 union；OFFICIAL_OVERRIDE 需引用 TW SOURCE_FACT/A Claim
- ST84 職責不變（anchors → 四軌 → 02／40），row-level 交由 ST85，責任邊界分離

## Phase E — Mutation（43→48）

M49（median 改 122.5）／M49b（舊式自我矛盾敘述）／M49c（anchor_count 漂移）／M50（model interval 改 2030）／M50b（MODEL_ONLY 下 final≠model）全部實測 FAIL＝預期。**M49b 直接覆蓋本輪實證事故**：R3g 我以 `replace('n=2', …)` 盲目替換，只換數字未換前半句，留下「中位數122.5天」與「median=123」並存。此類文字從此不可能再通過。

## 版本命名更正

- current 文件之「R3h Phase F」已改為「R3g Phase F」；99 另立 metadata correction 列留痕，不無痕改寫歷史
- 定名：R3g＝claims ready＋Phase F canonical anchors；R3h＝#3805＋Timeline semantics/validator hardening；R3i＝TM-F810-01＋8-10 隊伍搜尋

## Baseline freshness

02 之後已有 2026-08-04「深淵討伐戰」與 08-07 停權公告，本輪**未**擴張為全面刷新；02 既定刷新點為 2026-08-08 日服 8.5 周年直播後或 08-09 例行刷新，留給該次 maintenance pass。


# ===== R3i-0 PVE Gate coverage gap（2026-08-08） =====

## Disposable characterization（未進入 current SSOT）

- RP0：由輸入 ZIP 重新解壓；SHA-256＝`bac89daf13d8002b8947eb6a541b8a49254f0cf76e552f62c4c7921bdab8d0ec`，單一根目錄 `pcr_tw_project/`，46 檔。
- Probe：保留 `TM-F810-01`，另加 4 支使用不存在於 18 的 unit_key；5 支皆為 `PROVISIONAL`／`tw_availability_check=PASS`／合法 Evidence FK 與日期；24 暫改 `VERIFIED/team_count=5/reproducibility=CONFIRMED`。
- **修正前實測**：`MODE=PRE_SUITE CHECKS=109 FAIL=0 WARN=17`，exit=0；`tools/reports/pre_suite.json` 顯示 `gate.pve_verified=1`。證實 PROVISIONAL 與不存在於 18 的角色均可灌入有效隊數。
- **同一 probe 修正後實測**：`MODE=PRE_SUITE CHECKS=109 FAIL=2 WARN=16`，exit=1；`gate.pve_verified=0`。兩項 FAIL 分別為 PASS 隊伍五 slot 未全屬 18 AVAILABLE，以及 24 宣告 team_count=5 但有效隊數=0。

## 最小修正與回歸

- `tools/validate_project.py`：有效 PVE 隊伍必須同時滿足五 slot 完整、`clear_status=VERIFIED`、`tw_availability_check=PASS`、五 slot 皆在 18 且為 AVAILABLE、Evidence 非空且 FK 全合法、`verified_date` 合法。
- 同關卡同五人去重 signature 改為 `(server, stage, sorted five)`；Gate 計數以 signature set 計算，重複列不再污染統計。
- 24 的 `team_count` 改為所有 guide 都必須與 25 有效隊數一致，不再只檢查 `status=VERIFIED` 的列。
- Mutation：M40 改用 18 中真實 AVAILABLE keys，避免新 unit FK 守門遮蔽 duplicate oracle；新增 M51（PROVISIONAL count inflation）與 M52（PASS＋缺失 unit_key）。
- **Mutation 實測**：原 48 案與新增 2 案全部 PASS，`MUTATION_TESTS ALL_OK | active_scenarios=50`。
- Current SSOT 未增假隊伍：8-10 與 10-10 的有效隊數仍為 0／0；`TM-F810-01` 仍為 PROVISIONAL，24 的 8-10 仍為 PROVISIONAL／team_count=0。


# ===== R3i-A TM-F810-01 語意正規化（2026-08-08） =====

- 25 維持 20 欄，不擴欄；`operation_mode` 由混合自然語言改為 `SOURCE_CONFLICT`。
- 分來源保留 current 聲明：`appmatch_fire_guide=AUTO`（ev050 直頁已於前輪完整開啟）；`yt_jkPXr3aUZZQ=SEMI_AUTO`（ev052 目前仍只到標題／摘要層，**discovery-only**，本地正規化不得把它升為已實開 Evidence）。
- `requirements` 改為 canonical JSON；slot1～slot5 的 star／rank／ue1／ue2／six_star／connect_rank／element_boost 全部明寫 `UNKNOWN`，support=`NONE/UNKNOWN`、timeline_ref=`UNKNOWN`、failure_conditions=`[UNKNOWN]`。原泛化「專用約350級／R37–39／屬性技能約6P」未能逐 slot 驗證，未搬入結構化欄位。
- Validator 新增 operation mode Enum、requirements JSON schema/canonical/非空守門，以及 SOURCE_CONFLICT 的不同來源＋不同 mode 守門；M53～M55 分別覆蓋 malformed JSON、衝突塌成單一 mode、空字串冒充 UNKNOWN。
- 狀態刻意不變：`TM-F810-01.clear_status=PROVISIONAL`；24 的 8-10 仍為 `PROVISIONAL/team_count=0`。此切片不提供新通關證據，也不讓來源 claim 改變 Gate。
- 人讀 drift 同步：22 的 8-10／10-10 lifecycle 改回與 24 一致，成熟門檻由舊 `team_count≥1` 更正為每關至少 5 支有效隊；README 的 41 欄數由 31 更正為 35。


# ===== R3i-B 紅焰深域 8-10 實開研究（2026-08-08） =====

## 執行邊界

- 依工單固定順序逐一處理 `jkPXr3aUZZQ` → `tYwLvHHbKXo` → `ZXUDJm_AsSA` → `F39PkRIg0T4` → 煌靈／LongTimeNoC 火屬性播放清單 → `sm45195754`。
- 只有實際打開的頁面與畫面才可成為本輪 Evidence；搜尋摘要只用來定位，不升 OFFICIAL／A。
- 相同五人以 `(server, stage, sorted five)` 去重；來源可合併，隊數不可重複增加。
- 本輪台北時間為 `2026-08-08 04:49 +08:00`，尚未到 08/08 19:00 直播後刷新點；Baseline Refresh 未觸發，未擴張為全站重建。

## 固定候選逐頁結果

1. `jkPXr3aUZZQ`（ev052，**實開／採用**）
   - 標題明確為火 8-10；00:45 戰鬥列顯示完整五人；05:50 顯示「初回クリア」。
   - 五人＝露易絲瑪莉／萊拉耶爾（聖誕節）／克蘿茜（航空）／烏爾姆／琳德。
   - 影片聲明目押し 3 回，故為 `SEMI_AUTO` 來源聲明；與 appmatch 的 AUTO 聲明並存，TM-F810-01 維持 `SOURCE_CONFLICT`。
2. `tYwLvHHbKXo`（ev069，**實開／合併來源**）
   - 00:00 傷害報告顯示同一完整五人；05:05 顯示 `WIN!`；說明標示 4 Manuals。
   - 與 TM-F810-01 完全同五人，僅增加第二個實戰來源；不重複計隊。影片顯示琳德為支援角色。
3. `ZXUDJm_AsSA`（ev051，**實開／採用為 TM-F810-03**）
   - 標題明確為火 8-10 且載明克蘿茜（航空）支援借角想定；00:12 可辨識完整五人；03:15 顯示角色 EXP／等級上升與取得報酬的通關後 UI。
   - 五人＝真步（夏日）／萊拉耶爾（聖誕節）／克蘿茜（航空）／烏爾姆／優衣（聖誕節）；留言中的 SET 切換只作操作定位，五人仍以影片畫面辨識，不由留言推定。
4. `F39PkRIg0T4`（ev070，**實開／採用為 TM-F810-02**）
   - 章節 02:34 明確標示火 8-10；側欄逐名列 `バレシズ／ヴルム／エアクロ／クリラエル／ルイズマリー`；05:27 為勝利演出。
   - 完整五人＝靜流（情人節）／萊拉耶爾（聖誕節）／克蘿茜（航空）／烏爾姆／露易絲瑪莉。
5. 煌靈／LongTimeNoC（ev071，**頻道搜尋與影片均實開／合併來源**）
   - 頻道內實際搜尋命中 `OtiJrk3jacg`「火屬性深域 8-10 半自動刀」；00:58 顯示完整五人、04:37 為擊破後勝利演出。
   - 與 TM-F810-02 同五人，作台服創作者交叉來源，不另計新隊。說明載全員 Lv357／R37 五件與「情姊」專1／專2滿。
6. `sm45195754`（**FAILED_TO_OPEN**）
   - 直開 niconico 被瀏覽器 site-safety policy 阻擋；依政策未改用另一瀏覽器表面繞過。
   - 既有 ev053 僅保留 2026-08-02 曾開啟 nicozon 鏡像的歷史紀錄；本輪無法由可辨識畫面取得完整五人，故不建隊。

## 交叉來源與排除

- `i4pE3GxTMMA`（ev072）實開：04:11 完整五人、07:18 明示 `WIN!`，與 TM-F810-02 同五人；合併來源。
- `YTZHtUe4EOc` 實開：同 TM-F810-02；相同五人，不另建 Evidence／Team。
- `izvop5BXGL8` 實開：同 TM-F810-01；相同五人，不另建 Evidence／Team。
- GameWith 火 8-10 頁（ev073）全文實開：2025 年 9 月完整列出 TM-F810-02 與操作步驟；2025 年 12 月另列一套「真步（夏日）／露易絲瑪莉／萊拉耶爾（聖誕節）／克蘿茜（航空）／優衣（聖誕節）」全自動②候選，但頁面沒有可定位的 WIN／結算證據，依工單 §5.2(3) **不建立正式隊**。
- **排除 K=6**：tYw、Oti、i4p、YTZ、izvo 共 5 筆為同五人重複來源；GameWith 全自動② 1 筆缺可定位的實際通關結果。這些來源沒有拿來湊數；niconico `FAILED_TO_OPEN` 另列，不併入 K。

## 台服可用性與官方譯名

- ev074：官方 #3873 實開，2026/06/01 起精選候補列「靜流（情人節）」；18 新增 `shizuru_valentine=AVAILABLE`，初次實裝日不由本頁推定。
- ev075：官方 #2873 實開，火屬性限定候補列「靜流（情人節）」與「真步（夏日）」；18 新增 `maho_summer=AVAILABLE`，初次實裝日保留空白。
- ev076：官方 #3795 實開，「優衣（聖誕節）」於 2026/04/01 16:00 實裝；18 新增 `yui_xmas=AVAILABLE`。
- 舊公告 #2319 直開會轉址到 So-net 遊戲中心，未作 Evidence；改採上述可實開官方直頁，未把搜尋摘要升 A。
- #3805 依工單只試一次即成功：ev077／`CLM-TW-LAILAEL-XMAS-UE1` 建立，18 的 `lailael_xmas.ue1_status` 改為 `AVAILABLE`；裝備等級需求仍 `UNKNOWN`。

## 本輪停止交付

- `VERIFIED` 不同五人：**N=3**（TM-F810-01～03）；其中 TM-F810-03 僅一支玩家實戰，維持可靠度 D 並標示【僅供參考】。
- 正式 `PROVISIONAL` 隊：**M=0**（缺實際通關結果的 GameWith 候選只留 Research Log）。
- 24：`team_count=3`；因未達 5 支成熟門檻，`status=PROVISIONAL`、`reproducibility=PENDING` 均不升級。
- `FAILED_TO_OPEN`：niconico `sm45195754` 直頁 1 筆。
- 停止原因：工單預定來源已全部處理；剩餘已開影片只重複既有五人，或僅有理論／攻略編成而缺可定位通關結果。
- 下一次可重試條件：niconico 直頁在允許的安全政策下可開、GameWith 候選出現實戰影片／WIN frame，或新來源提供不同完整五人＋明確 8-10＋實際通關畫面。

## R3i-B 回歸備註

- 第一輪 Mutation 為 53/54 案通過、M54 失敗：原因不是 Validator 放寬，而是 TM-F810-01 新增第三筆 mode claim 後，舊 mutation 只改第二筆，沒有真正把全部 claims 壓成同一 mode。
- `tools/mutation_test.py` 只作直接相關修正：M54 改為遍歷全部 `operation_mode_claims` 並設為 AUTO；Validator 約束未降低。
- 封版稽核再讓 M53–M56 斷言「唯一命中目標 FAIL」，不再只看 exit code，避免其他守門遮蔽測試目的。
- 修正後實測：`MUTATION_TESTS ALL_OK | active_scenarios=54`。

## 2026-08-08 A2＋B2：紅焰 8-10 逐來源操作軸

### 實際開頁與採用邊界

- 已實際開啟 ev073 的 GameWith 正文，而非採用搜尋摘要或交接文件轉述；採用位置為「火 8-10 攻略編成例（2025 年 9 月）→ 魔法半自動 → 手順 1–8」。
- 正文的該段完整對應 TM-F810-02 五人，並提供八組有順序的手順。26 以 `AX-F810-02-EV073` 保存此來源，27 將複合 SET 操作拆為 14 個原子動作；每列 `source_step_no` 保留與原八組手順的對應。
- 本地繁中指令皆為正文內容的短句轉述，未保存長段日文原文；來源定位記在各 step 的 `source_locator`。
- 頁面另提醒養成進度／TP 變化會影響時間點；本輪不把該提醒改寫成數值容錯。因此 `tolerance_ms`、`hp_threshold`、`failure_if_missed` 均維持 `UNKNOWN`。
- GameWith 是日服攻略。TM-F810-02 雖有 ev071 台服同隊通關影片，ev071 沒有完整逐步文字軸，不能證明 ev073 的每個操作點已於台服重現；故 ev073 軸固定 `UNVERIFIED_ON_TW`。

### 未結構化來源

- TM-F810-01 的 ev050／ev052／ev069、TM-F810-02 的 ev070／ev071／ev072、TM-F810-03 的 ev051 各自建立 `SOURCE_GAP` source axis。
- 影片播放區間只作 Evidence locator；「目押三次」、「四次手動」、「半自動」、「可見操作表」均不足以推導 actor／trigger／clock／action，不建立假 step。
- ev073 對 TM-F810-03 僅作角色圖示／版本旁證，沒有為該隊建立操作軸。
- TM-F810-02 因一個 STRUCTURED source 加三個 SOURCE_GAP source，應用層整體狀態為 `PARTIAL`；不同來源不得攤平為單一 `steps` 陣列。

### 不變項

- 24 的 `team_count=3`、`status=PROVISIONAL`、`reproducibility=PENDING` 均不變；新增 timeline 不計入 PVE 隊數或 Data Gate。
- 25 的三隊 `clear_status` 不變；逐來源 operation mode claims 仍由 25 保存，26 必須逐一覆蓋或明示缺口。
- 新增 `CLM-PVE-TL-F810-SHIZURU`（SOURCE_FACT／D）只支撐 ev073 操作手順的存在與結構化邊界，不提高隊伍或關卡 Claim 信心。
