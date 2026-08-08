# ADR-0002：垂直切片匯入完整關卡 closure，不建立假正式案例

- 狀態：Accepted
- 日期：2026-08-08

## 決策

B0 使用 `TW_DEEP_FIRE_08_10_20260802` 作第一個真實切片。因 research core 宣告 `team_count=3`，fixture 必須包含三支隊伍、五名成員、相關角色可用性、Evidence 與 Claim closure；不得只匯入一隊。

Arena Registry 現為零筆。正式 API／UI 回傳結構化 no-result，不以理論隊或測試 fixture 冒充正式反制案例。若 contract test 需要資料，只能放在 `tests/fixtures` 並標為 `TEST_ONLY`，且不得進 production seed。

現有 `timeline_ref` 只能顯示「尚未結構化操作軸」。A2＋B2 會先在 file SSOT 建立 timeline／steps schema、Validator 與 Mutation，再由 importer 鏡像。

