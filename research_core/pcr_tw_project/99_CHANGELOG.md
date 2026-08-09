# 99 更新紀錄與過期登記（CHANGELOG）

> 用途：所有知識檔變更的單一紀錄點＋過期資料登記簿。每次更新任何檔案，在此記一行。

## 更新紀錄

| 日期 | 檔案 | 變更摘要 | 來源 |
|---|---|---|---|
| 2026-08-09 | A5 Arena VERIFIED HTTPS Evidence：00、01、30、31、99、tools/* | Arena 成熟列新增 fail-closed URL 邊界：每筆核心 Evidence 必須具有可解析的非空 HTTPS hostname；一般 ST49 對離線 B／C Claim 的 locator／title fallback 保持不變，但不足以讓 Arena 列成熟或進 Gate。Validator 與 Gate 共用 VERIFIED-only URL predicate；新增 M105，以兩筆空 URL、不同 locator／title 證明 offline fallback 不得繞過成熟度。全程未執行 `--write`；disposable copy 實跑 PRE_SUITE CHECKS 154／FAIL 0／WARN 24、OPERATIONAL CHECKS 153／FAIL 0／WARN 23、ARTIFACT_READY CHECKS 156／FAIL 3／WARN 23（僅 Gate A／B／C），Mutation ALL_OK／active scenarios 103。 | Builder 最小 fail-closed 修正 |
| 2026-08-09 | A5 Arena VERIFIED fail-closed：00、01、30、31、33、README、99、tools/* | Arena `VERIFIED` 暫只承認一筆 B／C 結果 Claim 與至少兩筆獨立同服 ACTIVE Win Evidence 的精確閉合；同時要求 canonical source tiers、`source_record_count`／`sample_size`／`wins` 各至少 2、`CONFIRMED`、非 UNKNOWN verification 與 `environment_match=EXACT`。SELF_TESTED 在獨立 run registry 建立前不得升級或進 Gate。Validator Gate 共用同一 predicate；M85 為合法雙獨立來源正控；M100–M104 分別攔截 label-only 自升級、同 host 不同 port、弱 counter tier、環境不符與自造 Evidence tier。實跑 PRE_SUITE CHECKS 153／FAIL 0／WARN 24；Mutation ALL_OK／active scenarios 102；Gate 統計單位正名為成熟反制列與 mature defenses，現值仍 0／0，未降低 Gate。 | Builder＋Maintainer fail-closed 稽核 |
| 2026-08-09 | A5 Arena 正規化：18、32–34、39、46、92、93、99、tools/* | 39 由舊版最小欄位擴為 35 欄 source-truth schema，首兩筆台服 exact screenshot win 保存 outcome／verification／樣本形狀／RNG／操作與環境 UNKNOWN、來源平台與日期，單筆固定 `SINGLE_REPORT / D / empirical win rate=NULL`；敵我 11 個不同角色完成 18 AVAILABLE 與台服官方名稱 Evidence 閉合，但同防守仍只有同一回覆者的兩筆單次觀測，Arena Gate 維持 0。Validator 新增 counter identity、無序 5v5 配對去重、ACTIVE 同服 Arena Evidence／Claim、樣本與單筆勝率、EXACT-only、來源真值欄位及台服可用性三態雙向閉合；Mutation 新增 **M78–M99**（含正向 Gate control、跨環境／跨服隔離、UNKNOWN 不得冒充 unavailable、PASS 不得輸出台服名稱 placeholder），active scenarios 由 75 增至 97，未降低 Gate。 | Builder＋Maintainer 邊界稽核＋實開戰果與台服官方正文 |
| 2026-08-08 | B3＋A5 Arena：18、32–34、39、46、92、93、99；platform DB／importer／API／Web | **首個台服 Arena exact 垂直切片**：實開巴哈主文、防守圖與同一作者兩張 Win／Lose 原圖，登錄同防守兩支完整五人反制；逐筆固定 `SINGLE_REPORT / D / sample_size=1 / empirical win rate=NULL`，Arena Gate 維持 0。角色圖示裁決為「埃拉」而非秋乃，`ユキ` 採台服官方「雪」；敵我可用性只以實開台服官方頁補 18，未明示欄位保持 UNKNOWN。AppMedia 日服同防守只留研究脈絡，不冒充台服交叉驗證。 | Builder＋原始戰果圖逐格核對＋台服官方正文 |
| 2026-08-08 | A4 Maintainer 修正：21、23、26、93、99、tools/*；platform importer／DB V0005／API | Water 五軸加入 18-step exact ST87 semantic boundary，固定時間、locator、trigger／action／AUTO／raw pattern 且新增 mutation；第 3～5 隊 Claim 與 axis 說明更正為實際的 `WAVE_START／NO_ACTION`。PVE effective predicate 追加隊內五人互異、guide server／stage 關聯及 ACTIVE Claim closure；借角 `UNKNOWN／SOURCE_CONFLICT` 跨 DB／API 保持 `null`，不得強化成 `false`。 | Maintainer 發現＋Builder 最小修正與 regression |
| 2026-08-08 | A4：03、18、22–27、92、93、99 | **蒼波 8-10 五隊單一來源 closure**：逐隊實播 `w3My0QHcoTA`，確認五種不同完整五人及 CLEAR／Boss HP=0（剩 13／22／3／5／17 秒），新增 5 支 VERIFIED teams、5 條 source axes 與 18 個保守原子步驟；操作模式固定為 MANUAL_TIMELINE／SEMI_AUTO／AUTO／AUTO／AUTO。`_jmHoggmlNY` 兩隊分別為 Boss 仍存活與 TIME UP，改存 ev089／ev090 `REJECTED` 且不進 Gate。新增八角台服 availability 與雙官方 mapping；「水堇」正規化為薇歐莉特（黃泉鯨命）、「阿法晶」正規化為拉比林斯達（始源）且不是克莉絲提娜。逐 slot 養成與借角維持 UNKNOWN；同一玩家／host 的五個通關 Claim 均為 D，blocking Warning 如實保留。 | Builder＋實播逐隊核對＋台日官方正文 |
| 2026-08-08 | A3：03、18、21–27、92、93、99、tools/*；platform importer／DB V0004／tests | **紅焰 8-10 五隊成熟 closure＋誠實 UNKNOWN**：實開 ev082／ev083 後新增兩支不同五人實際通關隊，24 升為 `VERIFIED/team_count=5/CONFIRMED`；安＆古蕾婭、未央（NGs）均以台日官方正文建立 availability／mapping，映射最高 B。TM-F810-04 的 operation mode 不由 UI 臆測，固定 UNKNOWN＋SOURCE_GAP；TM-F810-05 的五條來源文字以 SOURCE_TEXT_ONLY／NO_ACTION 保存，未定義 `[〇〇…]` 圖樣不拆 slot。Importer 同步 full-PVE projection、guide relation fail-closed、legacy B1 projection-aware rollback，DB V0004 只擴充 UNKNOWN enum；validator runtime reports 明定非 canonical。Gate 約束未降低，成熟列的 D 級單一玩家來源 blocking Warning 如實保留。 | Builder＋Maintainer 審查＋實開來源逐格核對 |
| 2026-08-08 | A2 Maintainer 修正：21、23、25–27、99、README、tools/* | 逐字複核 ev073 後移除未載的 `battle_duration=90000`、開場 1:30 與 `criticality` 推論；新增 `time_state` 並將手順 1 時間保持 UNKNOWN，手順 6／8 移除「下一次 UB」解釋。25 `timeline_ref` 原子切換為完整 source_axis 集合，coverage 納入 PROVISIONAL；新增 Evidence locator 子定位、source_step 分組／locator、來源邊界 ST87 與 M63–M68，並將 27 `min_rows=0`，由 STRUCTURED 語意決定是否必須有 steps。Gate／lifecycle 未提高。 | Maintainer 發現＋Builder 修正 |
| 2026-08-08 | A2：21、23、26、27、93、99、README、tools/* | **逐來源操作軸 SSOT**：新增 26（8 個 source axes）與 27（ev073／TM-F810-02 的 14 個原子步驟）；GameWith 正文手順 1–8 已實開核對並新增獨立 `CLM-PVE-TL-F810-SHIZURU`。其他來源逐一保留 `SOURCE_GAP`，未把影片區間或操作次數冒充步驟；不同來源不合併。ev073 為 JP 軸，固定 `UNVERIFIED_ON_TW`；24／25 lifecycle、team_count 與 Gate 均不提高。Validator 新增 source FK／狀態／step／coverage／跨服重現守門及對應 Mutation。 | Builder＋Maintainer 邊界稽核 |
| 2026-08-08 | I0：92、93、99、tools/validate_project.py、tools/mutation_test.py | **Evidence→Claim closure 正規化**：依 evidence_id 逐筆將 6 筆舊 Claim 別名改綁既有 Claim，並為 ev008 新增 `CLM-TW-DEEP-A8`；新增單向 declared Claim FK 守門 ST86 與獨立 mutation M57。Evidence 正文、來源層級、信心、Gate 與 lifecycle 均未變更；未擴張為 Claim 反向 evidence_ids 完全相等檢查。 | Builder＋Maintainer 稽核 |
| 2026-08-08 | R3i 封版稽核：22、23、25、92、93、99、tools/mutation_test.py | 兩份獨立唯讀稽核後的窄修：ev073 Source Tier 更正為 `MAJOR_GUIDE/D`；明列排除 `K=6`；TM-F810-03 補【僅供參考】、精確通關後 UI 與來源角色分工，移除 ev074 錯引；SOURCE_CONFLICT 改逐來源描述。M53–M56 除 exit code 外再要求唯一命中各自目標 FAIL，避免測試被其他守門遮蔽；未改 Validator、Gate、N=3 或 lifecycle。 | Builder＋雙人獨立稽核 |
| 2026-08-08 | R3i-B：03、18、22–25、92、93、99、README、tools/mutation_test.py | **紅焰 8-10 實開研究完成**：固定候選來源逐頁／逐幀核對後取得 3 支不同五人的 VERIFIED effective teams；同五人多來源以 signature 去重，24 改 `team_count=3` 但因未達 5 支仍維持 `PROVISIONAL/PENDING`。18 On-Demand 新增靜流（情人節）／真步（夏日）／優衣（聖誕節）之官方可用性；#3805 單次重試成功，萊拉耶爾（聖誕節）UE1 改 AVAILABLE。GameWith 全自動②因無可定位 WIN／結算證據只留研究日誌；niconico 直頁 FAILED_TO_OPEN；未補理論隊。M54 只因第三筆 mode claim 使舊變異器未真正壓平而更新為遍歷全部 claims，Validator 約束不變。 | Builder（R3i-B） |
| 2026-08-08 | R3i-0/A：21–23、25、README、tools/* | **PVE Gate coverage 修補＋TM-F810-01 正規化**：有效隊限定 VERIFIED／TW PASS／五 slot 均為 18 AVAILABLE／Evidence FK／合法日期，所有 24 team_count 對帳且同關卡同五人以 signature set 計數；新增 M51/M52。25 維持 20 欄，TM-F810-01 改 SOURCE_CONFLICT，requirements 改 canonical JSON 且逐 slot 未知值全保留 UNKNOWN；新增三項 schema/mode 守門與 M53–M56。22 lifecycle／成熟門檻與 README 41 欄數 drift 同步；clear_status、24 status/team_count 均未升級。 | Builder（R3i-0/A） |
| 2026-07-16 | 全部 | v1 檔案包初始建立（Phase 0＋1） | Builder 交付 |
| 2026-07-16 | 00 | 新增 §6 競技場與公主競技場研究規範；原 §6–§11 順移為 §7–§12；§12 回答規範新增第 6 條 | 使用者提供＋Builder 整合 |
| 2026-07-16 | 12 | 新增：角色同步流程（ADR-9 否決整站爬蟲） | Builder |
| 2026-07-16 | 01 | 競技場詞庫改指向 §6.1；GameWith 列回填查證結果（bot 阻擋） | Builder |
| 2026-07-16 | 04、06 | 進度區新增「屬性強化概況」（§12.6 資料落點） | Builder |
| 2026-07-16 | 11 | 新增 T16、T17（競技場規範驗收） | Builder |
| 2026-07-16 | README | v1.2：修正標題、驗收範圍與 Knowledge 檔數描述（v1.1.1 修正併入 v1.2）；檔案表升級為唯一權威清單；新增 Phase 1 完成條件、初始化與術語查證提示 | Sweeper 稽核＋Builder |
| 2026-07-16 | README | ADR-3 改寫為不硬寫檔數；新增 ADR-10、ADR-11 | Sweeper 稽核 |
| 2026-07-16 | 12 | 新角色同步來源優先序依台服／日服任務拆分 | Builder |
| 2026-07-16 | 00 | §5 新增第 5 條（PVE 檔案引用）；§7 新增【帳號可直接組成，但練度可行性待確認】等標籤登錄 | Builder |
| 2026-07-16 | 10 | 新增匯入順序建議與副帳號硬性要求 | Builder |
| 2026-07-16 | 11 | 新增 Phase 2 測試 T18–T24；驗收紀錄表移除，改指向 13 | Builder |
| 2026-07-16 | 13、20、21、22、23 | 新增：驗收結果紀錄簿＋Phase 2 關卡攻略框架四檔 | Builder |
| 2026-07-16 | 00 | v1.3：§3 帳號延後模式（data_status／一般研究模式／不反問帳號）；§6.6、§11、§12 新增模組檔引用；§7 補標籤 | Builder（依 v1.3 計畫） |
| 2026-07-16 | 04、06 | 新增資料狀態區（data_status: NOT_IMPORTED） | Builder |
| 2026-07-16 | 05、07 | 移除 EXAMPLE_ 範例列，出廠 header-only；範例移至 10 | Sweeper 稽核＋Builder |
| 2026-07-16 | 02 | 首輪初始化：台日現況＋A/A 錨點（若菜冬日：日 2026/03/03 vs 台 2026/07/03，約 4 個月）＋排程調整紀錄 | Builder（實際查證） |
| 2026-07-16 | 03 | 回填：深域クエスト、次元断層、黎明界ラビリンス、キャラ交換Pt（200）、専用装備2、女神の秘石、マスターピース等 | Builder（實際查證） |
| 2026-07-16 | 01 | 回填官方 URL（台／日官網）；nomae 降級歷史參考；pcrdfans 現況與處置；新增 VIPでプリコネ Wiki、PriLog | Builder（實際查證） |
| 2026-07-16 | 12 | 來源優先序已拆分（v1.2）；本輪填入日服待實裝首批 4 筆＋若菜錨點落地註記 | Builder（實際查證） |
| 2026-07-16 | 30–34 | 新增：Phase 3 競技場公共研究模組 | Builder |
| 2026-07-16 | 35–38 | 新增：Phase 4 公主競技場公共策略模組 | Builder |
| 2026-07-16 | 40–44 | 新增：Phase 5 未來視公共模組（41 header-only；43 帳號欄 BLOCKED） | Builder |
| 2026-07-16 | 90、91 | 新增：維運 Runbook＋提示範本庫（README 提示遷入 91） | Builder |
| 2026-07-16 | 11、13 | 新增 A1–A3、T25–T40；13 重建為含狀態值之唯一紀錄簿（BLOCKED 預標） | Builder |
| 2026-07-16 | README | v1.3 全面改版：Phase 拆分狀態、權威檔案表、帳號延後說明、ADR 12–16 | Builder |
| 2026-07-16 | 43 | **P0**：寶石公式單位修正＋保底口徑（免費抽計入Pt=台服官方）＋三情境示例；修正計畫稿缺口公式重複扣除 | Builder（v1.4） |
| 2026-07-16 | 00、01、21、31、42 | **P0**：Source Tier／Claim Confidence 雙軌制＋統一日期/伺服器/狀態欄位；§11 錨點揭露義務 | Builder（v1.4） |
| 2026-07-16 | 02 | 錨點#2（交換Pt機制，A/A，75天）＋差距統計 n=2 雙軌；台服深域第8區（A）；未達3錨點原因記錄 | Builder（實際查證） |
| 2026-07-16 | 03 | 交換Pt 升 A/A（200Pt 雙邊官方；2019 舊制 300）；星素／同步功能／連結商店；ライラエル・ネフィ＝ネラ 別名登錄 | Builder（實際查證） |
| 2026-07-16 | 12 | 生命週期制（sync_id＋四狀態＋去重＋截止日）；SYNC-001 關閉（RELEASED）；002/003 OFFICIAL_VERIFIED；004/005 CANDIDATE | Builder |
| 2026-07-16 | 14、92、15 | 新增：公共測試 Fixtures×24、證據帳 26 列、資料品質報告（Gate=未通過，如實） | Builder |
| 2026-07-16 | 11、13、91 | T41–T45 新增；13 重建（四 Suite＋fixture/evidence 可追溯欄）；91 §10 拆四 Suite | Builder |
| 2026-07-16 | 32、33 | JP 快照初版＋TW PROVISIONAL；反制 8 原型簡報＋停止條件回報（不虛構紀錄） | Builder（實際查證） |
| 2026-07-16 | 22、23、38、41、44 | P1 前置登錄（紅焰8-10，IN_RESEARCH）；PA1–PA3 理論案例；Timeline 2 筆成熟＋評估日誌 | Builder |
| 2026-07-16 | 01、34、90 | AppMedia 工具（2026/07/15 活躍）；pcrdfans TW 篩選；rwiki；證據帳維護與 Suite 回歸節奏 | Builder（實際查證） |
| 2026-07-17 | 稽核 | v1.4 稽核受理：P24 項通過確認；F01–F16 全數屬實並修正如下 | Sweeper（使用者稽核）＋Builder |
| 2026-07-17 | 02 | **F01**：更新至 7/17 官方（栞（冬日）池／深域第 10 區／專2 新年御三家／クレジッタ）；新增 official_news_checked_through 與事件觸發規則；錨點 #3（栞：123 天）＋分軌統計 n=3 | Builder（部分官網直驗＋使用者稽核） |
| 2026-07-17 | 92 | 遷移 15 欄（source_url＋source_locator，F16）；新增 ev027–ev036（含 F04 之 ev032 官方池型證據） | Builder |
| 2026-07-17 | 93、15、16 | 新增 Claim SSOT（F02／F15）；15 統計改程式化；16 靜態驗證報告（FAIL=0） | Builder |
| 2026-07-17 | 41、43、44、03、32 | **F03**：シェフィ PVE 評價 C→D、單抽成本 C→D、Arena 結構事實 C→D；41 拆 evidence_ids／anchor_track／anchor_count／forecast_basis（20 欄） | Builder |
| 2026-07-17 | 11、13、14 | **F05／F07／F08／F14**：Enum 合法化、標題與範圍修正、真實性聲明＋實體證據對照表；Fixture 統一為 30 覆蓋 34（F06） | Builder |
| 2026-07-17 | 01 | **F09**：章節標題改 Source Tier 命名；92／93 分工規則 | Builder |
| 2026-07-17 | 12 | **F12／F13**：TW_ROSTER_PENDING 硬規則＋暫存表（栞、若菜）；逐筆遷移敘述；SYNC-006（クレジッタ）／007（栞，RELEASED） | Builder |
| 2026-07-17 | 99 | **F10／F11**：Stale Register 登記 3 項；待辦改狀態值制 | Builder |
| 2026-07-17 | v1.4.1.1 | Hotfix：13 環境更新（v1.4.1.1／n=3）；12 用途·截止日·來源更新＋提示移除副本改指 91 §3（data_status 分流四步版）；README n=3 對齊；44 舊紀錄標 SUPERSEDED＋刪除線 | Builder（依 v1.4.1 稽核 F03–F11） |
| 2026-07-17 | v1.4.1.1 | 新增 tools/validate_project.py＋validation_config.json（可重跑驗證；16 唯一生成路徑；CURRENT／HISTORICAL 雙掃描域）；15 統計改由 validator 輸出同步 | Builder（F01／F02／F12／F16） |
| 2026-07-17 | v1.4.1.1 | 92 遷移 16 欄（claim_confidence→evidence_confidence＋published_date_precision）；93 遷移 14 欄（claim_type：SOURCE_FACT／DERIVED_CALCULATION／ANALYTICAL_JUDGMENT／FORECAST，衍生統計改標）；01／90／15 措辭同步 | Builder（F13／F14／F15，§6 拉前） |
| 2026-07-18 | v1.4.1.2 | Static Guard：Validator 擴至 ST38–ST43（15 AUTO 區生成核對、Sync 語意守門、T43 動態錨點、tools 數一致、41 驗證日、Evidence↔Claim 限制一致）；新增 tools/mutation_test.py（M01/M02/M05/M06 回歸驗證） | Builder（依 v1.4.1.1 稽核） |
| 2026-07-18 | v1.4.1.2 | 91 §10.4 移除硬編碼 n=2 改動態讀 02；32 台日落後敘述改分軌讀取；41 last_verified→07-17；92 依稽核 §4.7 逐筆更新（ev027/028/030/031/032 直頁確認、ev029/ev033 保留待回驗）；93 附註對齊；02 栞池期間 07/17–08/01＋核對日 07-18 | Builder（部分依 2026-07-18 稽核官方直頁確認） |
| 2026-07-18 | v1.4.1.3 | Gate-Readiness：Validator 重構為三階段＋Validation Mode（PRE_SUITE／OPERATIONAL／ARTIFACT_READY）；完整 PASS 放行、空白 PASS／無 defect 之 FAIL 攔截（ST51）；版本 SSOT 精確比對（ST44）；A1–A3＋T1–T45 定義與 Fixture 覆蓋改精確集合（ST45／46）；日期精度格式檢查（ST47）；Pending 表錨定解析（ST48）；B／C 證據唯一＋來源獨立（ST49）；A Claim 相容規則（ST50）；Warning 機制實裝（ST54）；16 版本與日期動態生成（ST53） | Builder（依 v1.4.1.2 稽核 §5–§9） |
| 2026-07-18 | v1.4.1.3 | 新增 17_TEST_EXECUTION_LOG.csv（執行紀錄 SSOT）；13 改人讀摘要並升版 v1.4.1.3；91 §10 紀錄格式改 17 優先；92 ev028 公告日 2026-07-16／DAY；mutation_test 擴至 M01–M14 | Builder |
| 2026-07-19 | v1.4.1.4 | Release-Gate Enforcement：ARTIFACT_READY 強制 Gate A/B/C（ST55）；Gate 數量由 22／33／38／41 計算（ST65）；Mode 輸出隔離（未達 Gate 只寫 tools/reports/*.json，不覆寫 canonical 15/16/stats，ST64） | Builder（依 v1.4.1.3 稽核 §4／§8／§9） |
| 2026-07-19 | v1.4.1.4 | 17 全面守門：run_id 唯一（ST56）、test/suite/fixture 精確映射（ST57）、Evidence FK（ST58）、PASS 必填 model/fixture_version/response_reference（ST59）、13↔17 current result 雙向同步（ST60）、重測鏈 is_current（ST61）、帳號測試須 READY（ST62）；17 增 test_scope／supersedes_run_id／is_current（18 欄） | Builder |
| 2026-07-19 | v1.4.1.4 | roster 驗證依 04／06 data_status 動態切換（ST63，NOT_IMPORTED=header-only／PARTIAL・READY・STALE 允許資料列並驗 account・唯一・必填）；Warning 分類含 blocks_gate_c（ST66）；mutation 擴至 M01–M26 | Builder |
| 2026-07-19 | v1.4.1.4 | 02 回填台服主線（第3部15章／NORMAL 79-9／Lv370）與最新已確認六星（涅婭 ★6），均 2026/06/15 官方＋須 91 §1 查 6/15 後更新；92 +ev037/ev038；93 +CLM-TW-MAINLINE/SIXSTAR；12 登記 T14/T18 帳號段技術債 | Builder（依稽核 §12） |
| 2026-07-19 | v1.4.1.5 | Gate-Integrity：Gate 數量改由結構化 Registry 成熟列計算（新增 24_PVE_GUIDE_REGISTRY.csv／39_ARENA_COUNTER_REGISTRY.csv；41 加 status/maturity/claim_ids/last_review_due→24 欄）；假 PVE/Arena/Timeline 不計 Gate（ST68/69/70／M25a-c） | Builder（依 v1.4.1.4 稽核 §5–§7） |
| 2026-07-19 | v1.4.1.5 | Warning 於 Gate 前計算；Gate C 納入 blocking_gate_c_warnings=0＋新鮮度（ST67／M27）；13 由 validator 依 17 current result 自動生成 AUTO_RESULTS 區（ST72／M29） | Builder |
| 2026-07-19 | v1.4.1.5 | 17 增 account_id／reviewer／reviewed_at／review_method／expectation_checklist（23 欄）；Account suite＋14 個帳號 Fixture；test_scope／account_id／evidence_status Enum（ST73/77/78）；ev029/ev033 status=PENDING_REVIEW（ST74）；Evidence Policy（ST71）；retest chain 同 test/scope/account＋無循環＋terminal（ST67-69）；02 OPEN_GAPS SSOT＋質性漂移守門（ST75）；mutation 擴至 M25a-c＋M27–M37 | Builder |
| 2026-07-20 | v1.5-cp0 | Guide-First Checkpoint 0：17→13 自動摘要順序修正——Gate A 只讀 17 current result（唯一權威），13 降為由 17 生成的人讀報告；ST60 改為比對 AUTO_RESULTS 與 17（--write 重生成、read 模式偵測過期），解決「只貼 17、狀態欄仍 NOT_RUN 誤判不一致」的 bug | Builder（依帳號凍結與攻略優先計畫 §6/§8） |
| 2026-07-20 | v1.5-cp0 | Gate C 警告分類優化：只有支撐成熟 Registry 資料（24/39/41）的 PENDING evidence 與被引用 claim 才阻擋 Gate C；未被成熟資料引用的研究層 D 級 ANALYTICAL_JUDGMENT 僅顯示 Warning、不阻擋（blocking_c 12→6）；不強迫升級或刪除 D 結論 | Builder（§16） |
| 2026-07-20 | v1.5-cp0 | 帳號層凍結 ACCOUNT_LAYER_STATUS＝FROZEN_OPTIONAL：00 Scope Reset（保留全部隔離規則、僅重述帳號為選用凍結＋三條保留產品規則）；README/15 加凍結宣告；帳號匯入／Account Suite／第三帳號／泛用多帳號遷移／帳號 Artifact 移至 Deferred；roster Schema 與帳號檔案不變、帳號測試維持 BLOCKED | Builder（§4） |
| 2026-07-20 | v1.5-cp0 | Deferred 登記：Generic Multi-Account Migration（未來 accounts.csv＋rosters.csv＋泛用 account_id，新增帳號只加資料列）；15 移除過期部署版本字串改指 v1.5；版本 SSOT 由 v1.4.1.5 升 v1.5；M13a 改 --write（貼 17→重生成 13 流程）；M01–M37 全綠 | Builder |
| 2026-07-20 | v1.5-cp1 | **資料更正（誠實揭露）**：v1.4.1.4 回填的 ev037（主線第3部第15章/Lv370/NORMAL79-9，引 newsDetail/3888）與 ev038（涅婭★6）**未經官方直頁驗證**，經 2026-07-20 實際查證官方站無法證實且與官方頁不符——ev037 更正為 2026/01/15 官方已驗證狀態（第14章/Lv355/NORMAL78，引 newsDetail/3685）；ev038 與 CLM-TW-SIXSTAR 移除，六星回歸【待查證】 | Builder（依 §16 錯誤更正） |
| 2026-07-20 | v1.5-cp1 | 公共資料刷新（Checkpoint 1D 部分）：新增 ev039／CLM-TW-DEEP-A9——台服深域第 9 區 2026/01/15 追加（官方直頁 newsDetail/3686 已驗證），關閉「第 9 區開放日待查」OPEN_GAP；02 official_news_checked_through→2026-07-20 | Builder |
| 2026-07-20 | v1.5-cp1A | **Correction of Correction（誠實揭露）**：v1.4.1.4 將第15章/Lv370 引到 newsDetail/3888 確實是錯誤來源映射（3888 為活動公告），且當時未經驗證；但 Checkpoint 1 只因查不到 3888 就把事實整個撤回（退回第14章/Lv355、刪六星）屬**過度更正**——把「來源錯誤」誤當「事實必錯」。本輪實際官方直頁驗證：ev040（第15章，newsDetail/3813 已驗證）、ev042（Lv370，newsDetail/3890 已驗證）、ev041（涅婭★6，newsDetail/3895 完整抓取）；ev037 保留為 01/15 第14章歷史快照 | Builder（依 §6 Baseline Integrity Patch） |
| 2026-07-20 | v1.5-cp1A | ev029 Trust Model 一致化（§9 方案A）：CLM-TW-DEEP-A10 由 ACTIVE/A 改 PENDING_REVIEW，與 ev029=PENDING 一致，回驗前不作 10-10 VERIFIED 依據；02 深域列標「有官方URL但正文待回驗」；移除 ev029/CLM 的「第9區待查」殘留（ev039 已關閉）| Builder |
| 2026-07-20 | v1.5-cp1A | 文件殘留清理（§8）：README→Checkpoint 1、Evidence/Claim 列數改由 validator 生成不硬編碼、待辦更新為 ev029/ev033直頁；15→Checkpoint 1；mutation docstring→M01–M38、helper fixture_version→v1.5；16 由 validator 生成標 M01–M38 | Builder |
| 2026-08-02 | v1.5-gw1-refresh | **公共資料刷新至 2026/08/02**（六直頁完整抓取）：主線第3部第16章/Lv373/NORMAL 80-1~80-3+80-EX1/HARD 79-3（#3937＝ev043）；深域第10區五屬性10-1~10-10 07/15 16:00（#3938＝**ev029 PENDING→ACTIVE**）；台服當期池格蕾斯（兔女郎）08/01~08/11（#3963＝ev044）、栞（冬日）移前池；日服ルイズマリー直頁（#36850＝**ev033 PENDING→ACTIVE**）；日服當期池フブキ（サマー）07/31~08/15（#37049＝ev048） | Builder（依 20260802 稽核 §6/§10） |
| 2026-08-02 | v1.5-gw1-refresh | 官方列表確認（標題級，直頁待例行回驗）：聖跡Lv10/神殿Lv5（#3966＝ev045）、8月挑戰冒險（#3968＝ev046，v1.6 Backlog）、次元斷層（#3969＝ev047，Backlog）、8周年系列（#3970/3971）、VILLAINESS（#3960）、8.5周年直前生放送（#36601＝ev049）；#3943 專2追加角色明細待直頁 | Builder |
| 2026-08-02 | v1.5-gw1-refresh | Claim 汰換：CLM-TW/JP-CURRENT-0717→SUPERSEDED（歷史保留），新建 CURRENT-0802×2；CLM-TW-MAINLINE→第16章（歷史鏈 ev037→040→042→043）；CLM-TW-DEEP-A10→ACTIVE（僅解除關卡存在阻塞）；+GRACE-POOL/SANCTUM-TEMPLE-LV/CHALLENGE-AUG/RIFT-AUG/JP-FUBUKI-DATE；41 +フブキ RESEARCH 列；12 +SYNC-008＋格蕾斯入 PENDING 表；ST74 改狀態↔限制一致性 | Builder |
| 2026-08-02 | v1.5-gw1-refresh | 02 verified_date/official_news_checked_through→2026-08-02；next_review_due→2026-08-09；登記事件觸發：2026/08/08 日服 8.5 直播後立即刷新；候選 #4（TW 側已官方化，待 JP 側） | Builder |
| 2026-08-02 | v1.5-guide-only | **Guide-Only Scope Reset（產品重定位：台服公共攻略資訊整合系統）**：帳號層 **REMOVED_FROM_ACTIVE_SCOPE**——04／05／06／07／10 移出 Active 並完整封存於 `PCR_TW_Project_account_layer_archive_v1_5.zip`（含 ADR、帳號測試定義、Fixture、Mutation 原始碼；不上傳 Project） | Builder（依 Guide-Only 稽核 §3–§4） |
| 2026-08-02 | v1.5-guide-only | **RETIRED_ACCOUNT_SCOPE**：T3–T12／T15／T19–T21 自 Active 定義退休（ID 永不重用）；帳號 Mutation M22／M24／M31／M32／M33 封存停用；17 移除 test_scope／account_id（21 欄）；BLOCKED_BY_ACCOUNT_DATA 狀態移除 | Builder |
| 2026-08-02 | v1.5-guide-only | 新增 Registry：**18 台服公共角色可用性**（7 筆證據種子：栞／若菜／格蕾斯／涅婭★6／新年三人專2）、**25 PVE 隊伍層**（同五人去重＋24 team_count 一致）、**45 Gacha 社群來源索引**（GACHA-COMM-001~004，PENDING_FETCH）、**46 Arena 來源 Registry**（ARENA-SRC-001~005，nomae STALE-only）；39 +7 欄、41 +7 社群共識欄 | Builder（稽核 §5–§8、§15） |
| 2026-08-02 | v1.5-guide-only | 測試集改 Guide-Only 41：改寫 A1／A2／A3／T18／T30／T33／T38／T39，新增 T46–T52；14 Fixtures 37 個全覆蓋；Gate 重定義（B：PVE 2關×5隊＋Arena 5×2＋PA 3＋TL 6＋社群 2；C：PVE 5＋Arena 10＋PA 5）；Validator 新增 ST80 帳號指令掃描＋18/25/45/46 檢查；新 Mutation M39–M41 | Builder（稽核 §10–§12） |
| 2026-08-02 | v1.5-guide-only-fixed | **Scope Closure Patch**：清除 Active 帳號語意殘留（37 帳號三隊段／90 帳號維運項／91 §4§6§7 account_status·帳號三隊·未套用帳號／44 模板／12 T14-T18 帳號段技術債／15 Deferred 矛盾／README FROZEN 殘留）；T14 改四層公共結構、Section H 改名 Guide-Only 個人問題處理、T45 改 17 為追溯 SSOT；ST80 語意守門擴充（account_status/data_status/帳號三隊/帳號個人化/未載入角色池/roster Schema） | Builder（依 guide_only_wave1 稽核 §4／§9） |
| 2026-08-02 | v1.5-guide-only-fixed | Baseline Metadata 對齊：config baseline/release→2026-08-02；ST42 改僅約束 MATURE 列；シェフィ列完成 08/02 重驗（官方列表頁1–4實抓、台服未公告、預估維持；紀錄於 41 forecast_basis＋44）→ Timeline MATURE 維持 2；16 INFO 改動態列出 PENDING Evidence（不再硬寫 ev029/ev033）；ST74 改通用 status↔limitations 一致性 | Builder（稽核 §4.4–§4.5） |
| 2026-08-07 | v1.5-pve-wave1-r3h-p0 | **R3h-P0**：41 schema 31→**35** 欄（model_estimate_start／end、forecast_method、forecast_notes）；**forecast_basis 改為 canonical 機器生成字串**，人工說明移入 forecast_notes；三列改 MODEL_ONLY 且 final＝model（Shefi 10/30–11/01、Luise 11/02–11/04、Fubuki 11/30–12/02），移除無 provenance 的人工寬區間；csv_specs 41 cols→35；新增 **ST85／ST85a**（CHECKS 107→**109**）與 **M49／M49b／M49c／M50／M50b**（43→**48**）；40 欄位定義、README current-state、44 歷史段 SUPERSEDED 指向同步。**#3805 仍 FAILED_TO_OPEN**（搜尋 5 次失敗＋列表分頁硬上限 page=5，2026-04 批次結構性不可達）｜**metadata correction：2026-08-04 該列原標 `v1.5-pve-wave1-r3h-phase-f` 為版本標籤誤植，實際交付 artifact 為 R3g；已更正標籤並保留本說明留痕** | Builder（R3h-P0） |
| 2026-08-04 | v1.5-pve-wave1-r3g-phase-f（原標 r3h-phase-f，見下列 metadata correction） | **Phase F 原子遷移完成**：config `anchors` 物件化為八筆 canonical objects，一次移除 anchor_median／pool_track／pool_track_median（歷史 schema 僅存本 changelog）；新增 ST83／ST83a／ST84／ST84a（CHECKS 106→**107**）並改寫 ST40 與 02 口徑檢查為派生式；stats.json 改輸出 anchors_n＋anchor_tracks 四軌；Mutation 新增 M43／M44／M47／M48 且 M27 遷離已 SUPERSEDED 的 CLM-ANCHOR-WAKANA（39→**43**）；02／12／18／40／41 同步四軌口徑與若菜開池日 2026-07-04；舊五筆統計／錨點 Claim 全標 SUPERSEDED，新增 CLM-GAP-LIMITED／PERMANENT／ALL-NEW／SYSTEM（DERIVED_CALCULATION／B）。**#3805 仍 FAILED_TO_OPEN**（分頁參數被箝制於 page=5） | Builder（R3h Phase F） |
| 2026-08-04 | v1.5-pve-wave1-r3g-claims-ready | **R3g claims-ready（Phase F 未啟動）**：ST60 拆分修正（純生成日漂移→info WARN 不阻 Gate；實質漂移仍 FAIL）＋M45／M46，Mutation 37→**39**；**JP #35568 與 TW #3925 均實開**（#3925 改以官方新聞列表 ?page=5 導覽取得，關鍵字搜尋已證實不可靠）；ev001 日期精度 2026-02/MONTH→**2026-03-03/DAY**；ev002 由新聞列表首頁→**#3925 直頁**＋locator；新增 CLM-TW-WAKANA-WINTER-REL（A）與 CLM-LOC-WAKANA-WINTER（B）；若菜開池日確認 **2026-07-04**、delta **123**（獨立驗算）；八筆 anchor FK 全數齊備，Phase F 前置成立。**config 未動**，02／12／18／40／41 統計待 Phase F 原子修正 | Builder（R3g Phase 0–3） |
| 2026-08-03 | v1.5-pve-wave1-r3f-pre-phase-f | **R3f pre-Phase-F（未啟動遷移）**：Phase 0 基線重現（46 檔／FAIL=0／Mutation 37）＋工作樹外回滾快照；**TW #3925 兩次搜尋仍 URL_NOT_SURFACED → 依 §13 停止條件不修 ev002、不建 Wakana TW／Mapping Claim、不啟動 Phase F**；新增日期語意複核結論：ev028／ev003／ev004 早已分離公告日與開池日（語意正確），缺陷僅限 ev002（若菜）與 ev001（精度 MONTH）；config／validator／mutation 全未變動 | Builder（R3f 工單 Phase 0–1） |
| 2026-08-03 | v1.5-pve-wave1-r3f-phase-e-checkpoint | **R3f Phase A–E checkpoint**：JP #31835 實開 → ev068／CLM-JP-LUISE-ORIG-REL（A）／CLM-LOC-LUISE-ORIG（B），**JP 官方頁 5/5 完成**（獨立驗算 124 天）；TW #3805 第4次嘗試仍 FAILED_TO_OPEN，UE1 維持 UNVERIFIED；Phase C 清 ev056–ev058 跨服污染與五筆 TW Claim stale notes；Phase E 依 eligibility check 沿用既有 A 級 Evidence 建立 CLM-JP-SHIORI-WINTER-REL／CLM-LOC-SHIORI-WINTER／CLM-JP-EXPT-REL／CLM-TW-EXPT-REL／CLM-LOC-EXPT-MECHANISM／CLM-JP-WAKANA-WINTER-REL；**ev002 判定不合格**（新聞列表首頁非直頁）→ 若菜 anchor 不完整、Phase F 前置未滿足；03 增露易絲瑪莉映射、README 移除「18 現 7 筆」stale count。**config 未動**，Phase F/G/H 未開始 | Builder（R3f 工單 Phase A–E） |
| 2026-08-03 | v1.5-pve-wave1-r3e | **R3e（Phase A–E）**：Phase D 修正 Mapping Claim 型別錯誤——CLM-LOC-LIND／VURM／CROCE-AERIAL 由 DERIVED_CALCULATION／A 改 **ANALYTICAL_JUDGMENT／B**＋server=CROSS_SERVER_MAPPING；新增 **ST82**（CLM-LOC 邊界規則，CHECKS 105→106）與 **M42** Mutation（36→37）；P0-2 修正過度宣稱（共同解鎖條件僅鎖定角色對）；P0-5 清除 TW Claim 內跨服映射；Phase C JP #29527 實開 → ev066／CLM-JP-LAILAEL-XMAS-REL（A）／CLM-LOC-LAILAEL-XMAS（B），JP 累計 4/5；Phase E 清 03／18／23 stale notes 並將舊段標 SUPERSEDED_BY_R3e。**未完成**：#3805 FAILED_TO_OPEN（3 次搜尋未浮現）、JP #31835 未嘗試、Phase F/G/H 範圍外 | Builder（R3e 工單 Phase A–E） |
| 2026-08-03 | v1.5-pve-wave1-r3d | **R3 JP 台日映射第一批**：JP 官方直頁實開 3/5（#28945 リンド／#29132 ヴルム／#31430 クローチェ（エアリアル））→ 92 增 ev063–ev065（OFFICIAL/A）；93 增 3 筆 JP 事實＋3 筆 A 級映射（CLM-LOC-LIND／VURM／CROCE-AERIAL，改用劇情解鎖條件等非譯名證據）；**修正稽核§4.1 矛盾**（CLM-TW-CROCE-AERIAL-REL 拆分為實裝事實＋獨立映射）；獨立驗算 123／122／123；**錨點未升級**（僅3/5，n 維持 2，02／40／41／Config 未動） | Builder（R3） |
| 2026-08-03 | v1.5-pve-wave1-r3c | **R3 報表殘留清除**：產生器修正（15「（38）」→「（47）」、16 來源清單→24／39／41／45／47）；15 移除全部手寫統計數字（含錯誤的「P-Arena 3/3 ✔」與「Arena 0/2」「目標 4」）；44 去帳號用語；14 A3／T33 措辭改公共資料聲明（A1／A2 產品邊界保留）；**自我更正 ev061 OFFICIAL/A→UNKNOWN/D/PENDING_REVIEW**（僅摘要層卻誤享官方A級） | Sweeper（R3・使用者指定「報表」） |
| 2026-08-03 | v1.5-pve-wave1-r3b | **R3 Step 1 續**：#3742 實開 → ev062／CLM-TW-LIND-VURM-UE1（OFFICIAL/A），18 之 lind_orig／vurm_orig ue1_status→AVAILABLE（2026/02/22 起）；#3805（萊拉耶爾專1）兩次搜尋未使 URL 浮現＝FAILED_TO_OPEN，維持 UNVERIFIED 不升級。TW 4 頁：3 驗證／1 失敗；JP 5 頁未動；錨點 n 仍為 2 | Builder（R3） |
| 2026-08-03 | v1.5-pve-wave1-r3a | **R3 Step 1（部分）**：TW 官方直頁實開 2/4 → 18 增 lind_orig（2025/02/10・#3247）／vurm_orig（2025/02/17・#3257），10→12 筆；92 增 ev059／ev060（OFFICIAL/A）與 ev061（火屬性・摘要層D／PENDING_REVIEW）；93 增三筆；**TM-F810-01 台服可用性 5/5 PASS**，clear_status 仍 PROVISIONAL（練度全 UNKNOWN＋單一來源）；25 改逐格結構化欄位；**24 lifecycle 對調修正**（8-10→PROVISIONAL、10-10→IN_RESEARCH）；03 增琳德／烏爾姆官方譯名。**未做**：#3742／#3805 專1、JP 五頁、錨點升級（n 維持 2）、隊伍搜尋 | Builder（R3・使用者 Q1/Q2/Q3 指令） |
| 2026-08-02 | v1.5-pve-wave1-r2 | **Checkpoint B 第二輪（18 首批 On-Demand）**：台服官方直頁實抓三筆 → 18 增 luisemarie_orig（2025/09/04・#3529）／croce_aerial（2025/08/09・#3500）／lailael_xmas（2025/04/01・#3313），7→10 筆；92 增 ev056–ev058（OFFICIAL/A）、93 增三筆 A 級 SOURCE_FACT；03 確立 ライラエル＝萊拉耶爾（解除待查證）；24／25 回填 FK 與可用性進度（3/5 已 AVAILABLE，ヴルム／リンド 未查 → 整隊仍 UNVERIFIED 不計有效） | Builder（HANDOFF §8 Checkpoint B） |
| 2026-08-02 | v1.5-pve-wave1-r1 | **Checkpoint B 第一輪（部分）**：24 首建 2 關（TW_DEEP_FIRE_08_10／10_10＝IN_RESEARCH／PROVISIONAL・team_count=0 誠實揭露）；25 首筆候補隊 TM-F810-01（PROVISIONAL＋UNVERIFIED 不計有效）；92 增 ev050–ev055、93 增 CLM-PVE-F810-STD／F1010-SCARCE（皆 D）；22 索引兩列＋23 完整搜尋帳（GameWith／rwiki／wikiwiki／巴哈直頁阻擋、YouTube 限流明細）；21 模式／屬性代碼定案 DEEP／FIRE；18 未動（無官方級可 PASS 查證・不建 UNVERIFIED 半資料庫）；更正：原版ルイズマリー≠41 サマー版（ev033）不得逕標 JP_ONLY | Builder（HANDOFF §8 Checkpoint B） |
| 2026-08-02 | v1.5-guide-only-fixed | **P-Arena Gate 誠實歸零**：新增 47_PRINCESS_ARENA_CASE_REGISTRY.csv（20 欄；VERIFIED＋15 人不重複＋全員 TW_AVAILABLE＋FK＋freshness 才計 Gate）；38 PA1–PA3 標 THEORY／EXAMPLE 永不計 Gate；validator parena 改由 47 成熟列計算（現＝0）＋GATE-PARENA 警告；Mutation 報告改標實際 Active 情境數 | Builder（稽核 §4.3／§7） |

## 過期資料登記（STALE REGISTER）

> 發現「曾經正確、現已失效」的內容時登記於此；修正後標記處理狀態。
> 常見觸發：新角實裝改變環境、Rank／系統更新使攻略失效、台服排程變動推翻預測、帳號資料超過 30 天未更新。

| 登記日期 | 項目 | 所在檔案／位置 | 過期原因 | 處理狀態 |
|---|---|---|---|---|
| 2026-07-17 | nomae arenadb 全庫 | 34;01（CLM-NOMAE-STALE） | 約 2020/11 後停止更新 | STALE——僅供歷史反制概念，不可作現行解 |
| 2026-07-17 | 台服競技場 2024/9 攻防素材（ev017） | 32（CLM-TWARENA-2409） | 距 2026 現行環境約 10 個月 | STALE／HISTORICAL——歷史結構參考；首次台服競技場研究時重建快照 |
| 2026-07-17 | 02 之 2026-07-16 版台服基準 | 02 | 被 7/15–7/17 官方公告超越（F01） | 已於 v1.4.1 修正（SUPERSEDED） |

## 待辦（規則層；狀態值：NOT_STARTED／IN_PROGRESS／PARTIAL／DONE／BLOCKED）

| 登記日期 | 事項 | 狀態 |
|---|---|---|
| 2026-07-16 | 02 版本基準初始化 | **PARTIAL**——雙邊現況與 3 個 A/A 錨點完成；剩餘：台服主線／六星進度、第 9 區開放日、候選錨點 #4 日服官方化 |
| 2026-07-16 | 01 來源 URL 查證 | **PARTIAL**——官方雙邊／GameWith／AppMedia／pcrdfans／nomae 完成；剩餘：神ゲー、台日對照表 Sheets、PriLog 存活 |
| 2026-07-16 | 03 待查證術語 | **PARTIAL**——交換Pt／深域／星素／栞シオリ等完成；剩餘：追憶之戰域等日文名、母豬石台服官方名、台服譯名×5 |
| 2026-07-16 | 21 模式／屬性代碼定案 | **DONE**（2026-08-02 首筆建檔定案：DEEP＝深域冒險、FIRE＝紅焰；其餘屬性沿用同法於各屬首筆時定案） |
| 2026-07-17 | 四 Suite 實跑（結果寫 17，validator 生成 13） | NOT_STARTED（v1.5 核心） |
| 2026-07-17 | P1a／P1b、Arena 簡報 1–8、Timeline 補至 6+ | NOT_STARTED（v1.5；Gate 分層見 15） |
| 2026-07-16 | 帳號匯入與帳號批次驗收 | BLOCKED（等待使用者截圖） |
| 2026-07-17 | SYNC-004／005／006 官方確認與評估 | IN_PROGRESS（006 日期已官方化，評估未做） |
