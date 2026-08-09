# 30 競技場研究流程（ARENA RESEARCH WORKFLOW）

> 用途：接到競技場／反制問題後的研究與回答流程。硬規則見 Instructions §6；
> 資料格式見 `31_ARENA_COUNTER_SCHEMA.md`；環境快照見 `32_ARENA_META_SNAPSHOT.md`；
> 研究記錄於 `33_ARENA_COUNTER_LOG.md`；來源地圖見 `34_ARENA_SOURCE_MAP.md`。

## 1. 敵方隊伍辨識

- 確認五名成員與**角色版本**（原版／季節版／公主型態等），截圖辨識時回述結果供確認。
- 記錄站位順序（前→後）；可見時記錄星數、專武、六星狀態。
- 資訊不足 → 依 Instructions §6.5：指出缺少項目，初步方向標【待查證】，不得虛構（對應 T26）。

## 2. 防守分析

- 防守核心（成立支點）：坦克類型、先手控制、TP 加速、反傷／迴避、隊伍勝利條件。
- 初動判斷：誰先出手、控制鏈起點、UB 順序、速度差異。
- 標示對隨機因素的依賴（暴擊、閃避、目標選擇）。

## 3. 理論反制搜尋

1. 依 Instructions §6.1 詞庫＋敵方核心角日文名搜尋。
2. 依 34 來源地圖選擇來源；注意 nomae arenadb 為歷史資料、pcrdfans 需逐筆確認伺服器。
3. 多來源交叉：至少兩個彼此獨立來源一致才可標 claim_confidence B／C（單一大型攻略站最多 D），逐筆在 92 登錄 Evidence，並由 93 通過獨立性檢查。
4. A5 升為 `VERIFIED` 前，敵我必須是同服、`environment_match=EXACT` 的同一 exact 配對，且反制核心結論已有上述 B／C 多來源閉合；39 與 92 的 tier 必須在 canonical whitelist 內，每筆核心 Evidence 的 `source_url` 必須是具非空 hostname 的 HTTPS URL。一般 ST49 對離線 B／C Claim 的 locator／title fallback 不構成 Arena 成熟證據。`source_record_count` 只記來源紀錄數，不得取代 Evidence 獨立性；`sample_size` 只記來源明示的實戰觀測數，不得用來源筆數補值。
5. 尚未建立 Arena 實測 run registry，因此「本人實測」或手填 `CONFIRMED` 不能單獨升為 `VERIFIED`／計入 Gate；先留 `PROVISIONAL`，若僅有單一影片或留言則為 `SINGLE_REPORT / D /【僅供參考】`（對應 T27）。
6. 舊環境資料（新角／專武／六星已改變環境）→ status＝STALE，不得當現行解（對應 T28）。
7. 簡中來源 → 依 §9 排除或追溯日服原始來源（對應 T29）。
8. **台服實裝檢查**：反制隊每名角色與關鍵強化（專武／六星）確認台服已實裝；未實裝標【日服現況】／【台服未來】並另尋台服現行替代解。

## 4. 輸出

輸出規範（Guide-Only）：

依 Instructions §6.3：候選反制 1～10 支（不足只列實際數量），每支標敵方五人／進攻五人／台服可用性（依 18：TW_AVAILABLE／JP_ONLY）／來源數／紀錄日期／初動／風險／信心。JP_ONLY 不得作台服最終推薦（對應 T30／T48）。每次解陣記錄 searched／matched／unavailable／result_count（依 46；對應 T49）。

## 5. 建檔與維護

- 有價值的反制 → 依 31 Schema 建檔；每次研究 → 33 記一筆。
- Arena Gate 的計數單位是**成熟防守案例**，不是 39 的資料列數：同一 TW 環境、同一敵方五人必須至少有兩支不同的成熟 `VERIFIED` exact counters，才算一個 defense。
- 環境變動（新角實裝、大改版）→ 更新 32 快照並重驗相關反制。
