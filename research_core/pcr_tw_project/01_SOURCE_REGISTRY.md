# 01 來源註冊表（SOURCE REGISTRY）

> 用途：定義本專案允許使用的資料來源、可靠度分級與使用注意。
> 新增來源時：填入表格＋標註查證日期；發現失效來源時：移入「失效／降級紀錄」。

## 來源層級與結論可靠度（v1.4 起雙軌制，禁止混用）

**Source Tier（來源類型，描述「這是什麼來源」）：**
OFFICIAL／MAJOR_GUIDE／STRUCTURED_DB／COMMUNITY_WIKI／MULTI_PLAYER_REPORT／SINGLE_PLAYER_REPORT／UNKNOWN／RESTRICTED

**Claim Confidence（結論可靠度，描述「這個結論被驗證到什麼程度」）：**

| 等級 | 定義 |
|---|---|
| A | 官方直接證實 |
| B | 至少兩個**彼此獨立**的大型來源一致，且版本相符 |
| C | 至少兩個獨立玩家實戰或社群紀錄一致 |
| D | 單一非官方來源 |
| E | 推測、資訊不完整或版本不明 |

**規則：**
- 單一 GameWith 頁面：Tier＝MAJOR_GUIDE，Confidence **最多 D**；GameWith＋AppMedia 一致才可 B，且須列兩筆 evidence_id。
- 官方公告＋攻略站解析：官方事實部分 A；隊伍／評價部分依非官方證據另評。
- 不得以來源網站名直接決定結論可靠度。
- **分工**：`92` 只記證據（Evidence，欄名 `evidence_confidence`＝該筆證據自身的可信度）、`93_CLAIM_REGISTER.csv` 只記結論（唯一的 `claim_confidence`，並以 `claim_type` 區分 SOURCE_FACT／DERIVED_CALCULATION／ANALYTICAL_JUDGMENT／FORECAST）；Source Tier 分布從 92 計、Claim Confidence 分布從 93 計，不得混算（15 由 validator 輸出同步）。B／C 級結論在 93 至少列兩筆 evidence_id 並通過獨立性檢查。
- 本檔來源表的「等級」欄自 v1.4 起讀作 Source Tier：官方列＝OFFICIAL；攻略站＝MAJOR_GUIDE；蘭德索爾圖書館・pcrdfans＝STRUCTURED_DB（pcrdfans 同時為 RESTRICTED）；wiki＝COMMUNITY_WIKI；巴哈整理串＝MULTI_PLAYER_REPORT；單篇心得／影片＝SINGLE_PLAYER_REPORT。
- **Arena A5 成熟度**：`VERIFIED` 暫只接受 B／C 的可機械驗證多來源結論；至少兩筆同服、`environment_match=EXACT`、同一 exact 配對的 Evidence 必須可追溯，並由 93 的獨立性檢查證明來源彼此獨立。39 只接受 canonical 強來源 tier，92 只接受本檔既定八種 tier 且成熟閉合不得使用 UNKNOWN／RESTRICTED；成熟閉合內每筆 Evidence 的 `source_url` 另須為具非空 hostname 的 HTTPS URL。ST49 為一般 B／C Claim 保留 locator／title 的離線 fallback，但不能以此替代 Arena 成熟 Evidence URL。單一 scalar `source_tier`、`source_record_count` 或 `source_platforms` 不構成獨立性證明。
- `source_record_count` 記來源紀錄數；`sample_size` 記來源明示的實戰觀測數。兩者不得互相代填，來源沒有試驗分母時 `sample_size` 保持 NULL。
- `SELF_TESTED` 尚無獨立 run registry；在 run ID、環境、結果 Evidence、樣本與 reviewer closure 可追溯前，本人實測不得升為 Arena `VERIFIED` 或進 Gate。

## 統一欄位標準（所有動態資料通用）

- 日期欄：`published_date`／`verified_date`／`last_checked`／`next_review_due`（不得只寫模糊的「日期」）
- 伺服器欄：`TW`／`JP`／`CROSS_SERVER_FORECAST`／`UNKNOWN`
- 攻略狀態：`VERIFIED`／`PROVISIONAL`／`SINGLE_REPORT`／`STALE`／`REJECTED`；Arena 的 A5 `VERIFIED` 另受上述多來源暫行邊界限制
- 測試狀態：`PASS`／`FAIL`／`PARTIAL`／`NOT_RUN`（Guide-Only，全部為公共測試）

## 官方來源（Source Tier＝OFFICIAL）

| 來源 | 伺服器 | 用途 | 存活查證 | 備註 |
|---|---|---|---|---|
| 台服官方網站／官方 Facebook | 台服 | 實裝日期、卡池、活動、維護公告 | 2026-07-16 ✔ | https://www.princessconnect.so-net.tw/ （公告：/news）；FB：facebook.com/SonetPCR；App Store 更新說明亦為 A 級版本資訊來源 |
| 台服遊戲內公告 | 台服 | 最權威的台服現況來源 | — | 需使用者截圖或轉述 |
| 日服官方網站／官方 X | 日服 | 日服實裝與卡池原始日期 | 2026-07-16 ✔ | https://priconne-redive.jp/ （情報：/news/information/；更新：/news/update/） |
| Cygames 官方直播／生放送情報 | 日服 | 未來系統與周年情報 | 【待查證】 | |

## 大型攻略與結構化資料（Source Tier＝MAJOR_GUIDE／STRUCTURED_DB）

| 來源 | URL | 語言 | 伺服器 | 用途 | 存活查證 |
|---|---|---|---|---|---|
| 蘭德索爾圖書館 | https://pcredivewiki.tw/ | 繁中 | 台服為主 | 角色資料、裝備、地圖、轉蛋模擬 | 2026-07-16 ✔ |
| AppMedia プリコネR | https://appmedia.jp/priconne-redive | 日文 | 日服 | 角色評價、關卡隊伍、競技場 | 2026-07-16 ✔ 活躍 |
| AppMedia アリーナ防衛突破編成検索ツール | appmedia.jp/priconne-redive/4466131 | 日文 | 日服 | **現役**反制檢索工具（玩家投稿制） | 2026-07-16 ✔（頁面更新 2026/07/15，ev016）；逐頁人工引用 |
| プリコネRe:Dive Wiki（rwiki）コンテンツ追加履歴 | priconne_redive.rwiki.jp | 日文 | 日服 | 內容實裝歷史（錨點挖掘用） | 2026-07-16 索引可見；COMMUNITY_WIKI |
| 巴哈：台版深域關卡備戰表格（snA=36083） | forum.gamer.com.tw | 繁中 | TW | 深域各關作業彙整 | 2026-07-16 ✔（標「暫停更新」，涵蓋區域需逐次確認） |
| 巴哈：2024.9 台服公競攻防構築（snA=34029）等實戰串 | forum.gamer.com.tw | 繁中 | TW | 台服競技場實戰（快照素材） | 2026-07-16 ✔（ev017；日期標註必附） |
| 第三方部落格（スマホゲームNavi／GamesInk 等） | — | 日文 | JP | 輔助交叉、概念解說 | Tier＝UNKNOWN～SINGLE；只作旁證，不單獨支撐結論 |
| GameWith プリコネR | https://gamewith.jp/pricone-re （角色一覽：article/show/92923） | 日文 | 日服 | 角色評價、環境分析、新角一覽、深域攻略 | 2026-07-16 ✔ 活躍（頁面更新至 2026/07）；直接抓取遭 bot 阻擋 → 經搜尋引擎摘要或人工逐頁引用，不批量抓取 |
| 神ゲー攻略 プリコネR | 【待查證】 | 日文 | 日服 | 輔助交叉驗證 | 【待查證】 |
| 台日進度對照表（社群 Google Sheets） | 見備註 | 繁中 | 台／日 | 台日差距錨點 | 【待查證】（連結出自 2020 巴哈整理文，存活待驗） |

## 社群與玩家資料（Source Tier＝COMMUNITY_WIKI／MULTI_PLAYER_REPORT／SINGLE_PLAYER_REPORT）

| 來源 | URL | 語言 | 伺服器 | 用途 | 存活查證 |
|---|---|---|---|---|---|
| 巴哈姆特・公主連結哈啦板 | https://forum.gamer.com.tw/B.php?bsn=30861 | 繁中 | 台服 | 台服實戰、未來視整理、活動心得 | 2026-07-16 ✔ |
| 巴哈「未來台服卡池開放整理」串（snA=37138） | forum.gamer.com.tw/C.php?bsn=30861&snA=37138 | 繁中 | 台服未來 | 社群未來視（卡池區間預測） | 2026-07-16 ✔（2026/6 仍在更新） |
| 巴哈「台服未來視」整理串（snA=37206） | forum.gamer.com.tw/C.php?bsn=30861&snA=37206 | 繁中 | 台服未來 | 卡池／專1／專2 未來視分類 | 2026-07-16 ✔（2025/11 更新） |
| nomae arenadb（日服競技場作業庫） | https://nomae.net/arenadb/ | 日文 | 日服 | 競技場進攻解（**歷史參考**） | 2026-07-16 站點存活，但社群回報約 2020/11 後停止更新 → 降級為歷史資料，不代表現行環境 |
| VIPでプリコネ Wiki | https://wikiwiki.jp/vipricone_re | 日文 | 日服 | 社群整理（競技場初動／アンチキャラ／用語） | 2026-07-16 索引可見 | 
| PriLog（クラバト TL 工具） | https://prilog.jp/ | 日文 | 日服 | 戰隊戰影片轉時間軸 | 【待查證】（存活未驗） |
| YouTube／X 實戰影片與戰報 | — | 日／繁中 | 依內容 | 深域時間軸、競技場反制、戰隊軸 | 逐案標註 |

## 受限來源（Source Tier＝RESTRICTED；依中國服排除規則處理）

| 來源 | 語言 | 預設處置 | 例外 |
|---|---|---|---|
| pcrdfans.com（簡中競技場作業庫） | 簡中 | 依 §9 逐筆確認 | 2026-07-16 查證：/jp/battle 現役；**站內篩選含 JP/CN/TW/Global（ev019）**——使用時必須逐筆確認紀錄伺服器與時間，僅日服／台服紀錄可降級 C–D 參考；不繞過任何存取限制 |
| bilibili／NGA 等簡中攻略 | 簡中 | 同上 | 能追溯至日服原始資料時，改引日服原始來源 |

## 日文搜尋詞庫

- 競技場／公主競技場詞庫：**以 Instructions §6.1 為準**（單一維護點，避免兩處失同步）。角色針對性搜尋格式：`プリコネ アリーナ ○○ 対策`（○○ 替換為敵方核心角色日文名）。
- 其他模組常用詞：`プリコネ 深域`、`プリコネ クランバトル 編成`、`プリコネ ガチャ スケジュール`、`プリコネ 専用装備2`。

## 失效／降級紀錄

| 日期 | 來源 | 事由 | 處置 |
|---|---|---|---|
| （尚無） | | | |
