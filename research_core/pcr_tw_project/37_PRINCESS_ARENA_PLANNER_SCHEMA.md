# 37 公主競技場規劃 Schema（PLANNER SCHEMA）

> 定義公主競技場規劃的輸入／約束／輸出格式（Guide-Only：只依台服公共可用性 18，不讀任何角色池）。

## 輸入

- 敵方三隊（已知者逐隊五人；隱藏者標推測池）
- 環境版本與查證日期

## 硬性約束

1. 全部角色與必要強化已在台服實裝（依 18；JP_ONLY 不得放入台服最終三隊）
2. 三隊角色不得重複
3. 每隊五人完整
4. 每隊有可追溯解陣來源
5. 隱藏隊伍推測標信心
6. 組合求解：說明為何選這三支而非各自最高分卻角色衝突的組合
7. 成熟案例的三組敵我配對，各自對到同一台服 environment 的唯一成熟 39 exact row
8. `case_win_claim_id` 直接支持完整三戰結果；三筆單隊勝利不得反推整體 WIN

## 三隊輸出

- 每隊：五人與版本／針對敵隊／來源與日期／初動與風險／信心
- 取捨說明（組合層）：核心角色分配、田忌賽馬選項
- 隱藏敵隊：Meta 對策池＋保留核心角，推測與已知分開

## 停止條件

不得虛構敵方隱藏隊伍；無來源三隊不得標穩定；JP_ONLY 不得進台服最終三隊。

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
