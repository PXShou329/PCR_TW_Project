# 37 公主競技場規劃 Schema（PLANNER SCHEMA）

> 定義公主競技場規劃的輸入／約束／輸出格式（Guide-Only：只依台服公共可用性 18，不讀任何角色池）。

## 輸入

- typed v5 Planner 只接受敵方三隊各五名、合計 15 名不同角色的完整可見輸入
- 台服 environment version 與查證日期；`UNKNOWN` environment 不得查詢 mature case
- 隱藏／部分可見防守只能留研究層，不得送入 mature-only typed lookup，也不得產生 Similar fallback

## 硬性約束

1. 全部角色與必要強化已在台服實裝（依 18；JP_ONLY 不得放入台服最終三隊）
2. 三隊角色不得重複
3. 每隊五人完整
4. 每隊有可追溯解陣來源
5. typed v5 不接受隱藏隊伍；研究層推測即使標信心也不得物化為 mature case
6. 組合求解：說明為何選這三支而非各自最高分卻角色衝突的組合
7. 成熟案例的三組敵我配對，各自對到同一台服 environment 的唯一成熟 39 exact row
8. `case_win_claim_id` 直接支持完整三戰結果；三筆單隊勝利不得反推整體 WIN

## 三隊輸出

- 每隊：五人與版本／針對敵隊／來源與日期／初動與風險／信心
- 取捨說明（組合層）：核心角色分配、田忌賽馬選項
- 隱藏敵隊：Meta 對策池＋保留核心角，推測與已知分開

## 停止條件

不得虛構敵方隱藏隊伍；無來源三隊不得標穩定；JP_ONLY 不得進台服最終三隊。

## B4-0 typed v5 serving 邊界

- v5 只物化通過本檔、31、39、46、47、18 與 92／93 完整成熟 predicate 的 `VERIFIED` case；47 的研究列、模板與 deferred leads 不得進 typed tables。
- canonical 47 目前是 header-only，實際 mature case `N=0`。這是合法、可部署的 fail-closed 狀態：環境清單為空；合法 3×5／15 人／TW AVAILABLE 查詢回傳空 exact 結果與 `NO_MATURE_PARENA_CASE`，不得生成示意隊、理論隊或 Similar。
- 若 active snapshot 不是擁有 P-Arena closure 的 v5，P-Arena endpoint 必須 `503 NO_PARENA_MATERIALIZATION`；不得把缺 table 說成正常 0 case。
- 查詢的隊伍順序與隊內順序只影響回傳對應位置，不改變 canonical identity；相同三隊重排仍是同一 defense case。
- 三筆獨立 Arena 勝利，即使各自顯示 `WIN`，也不能推出整體公主競技場勝利；缺少直接支持完整三戰結果的唯一 `case_win_claim_id` 時，typed case 必須為 0。

## 來源與可靠度

- 47 為 24 欄案例 Registry；`team1_result_claim_id`／`team2_result_claim_id`／`team3_result_claim_id` 分別綁定三組 exact 39 結果，`case_win_claim_id` 綁定完整三戰 WIN。
- 三筆 team result Claim 固定為 ACTIVE／TW／`arena`／SOURCE_FACT／B 或 C，並沿用 A5 多來源 mature closure。
- case WIN Claim 固定為 ACTIVE／TW／`parena`／SOURCE_FACT／version match YES；D 至少一筆 direct ACTIVE TW parena HTTPS Evidence，B／C 至少兩個獨立 hostname；direct Evidence confidence 只接受 A／B／C／D，不接受 E。
- 47 的 `claim_ids` 精確等於上述四個 designated Claims，`evidence_ids` 精確等於四個 Claim 的 direct Evidence 聯集。
- `source_ids` 只引用 46 中 ACTIVE／TW／未過期的來源索引，其 URL hostname 必須覆蓋 case WIN direct Evidence hostname；仍不能取代 Evidence 獨立性。
- case WIN 為 D 時可計 Gate B，但明確阻擋 Gate C；沒有完整 case WIN 時不得 VERIFIED。
- 每個 VERIFIED `case_win_claim_id` 全域只能支撐一個 case；不同防守不得共用完整勝利 Claim，warning 亦以 Claim 去重。

## 47 VERIFIED 日期與狀態

- `hidden_team_mode=NONE`、`tw_availability_check=PASS`、`non_overlap_check=PASS`、`reproducibility=CONFIRMED`。
- `verified_date` 不得晚於今日，且不得早於四個 designated Claims、其 direct Evidence 與三筆 39 rows 的驗證日。
- case WIN Evidence 的 DAY 發布日必須 ≤ Evidence verified date；MONTH／YEAR 依既有 precision 保守比較，不得明顯晚於驗證年月／年。
- `last_review_due` 不得早於今日，且不得晚於四 Claims 與三筆 39 rows 中最早的到期日。
- 相同 TW environment 與相同三隊防守 signature 只存一個 VERIFIED case；同時重排三組配對或提供多個解都不能製造第二個 Gate 案例。

## 禁止

不得宣稱任何「帳號可用」三隊；個人化問題依 Instructions §1 回答「本專案不保存帳號資料」＋公共組合與所需條件。
