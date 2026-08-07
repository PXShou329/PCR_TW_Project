# 21 關卡攻略資料 Schema（STAGE GUIDE SCHEMA）

> 用途：定義每筆已驗證攻略的唯一識別、標準資料模板、可靠度與過期條件。
> 只有經 `20_PVE_GUIDE_WORKFLOW.md` 流程驗證過的攻略才依本 Schema 建檔。

## 1. 唯一識別（guide_id）

```text
<TW或JP>_<模式代碼>_<區域或屬性>_<關卡>_<版本日期YYYYMMDD>
例：TW_DEEP_FIRE_03_10_20260716
```

### 模式代碼建議表（2026-08-02 首筆建檔定案：DEEP＝深域冒險（台服官方名）、屬性 FIRE＝紅焰；guide_id 範例＝TW_DEEP_FIRE_08_10_20260802。其餘模式／屬性代碼於各自首筆建檔時依同法定案）

| 模式 | 建議代碼 |
|---|---|
| 深域冒險 | DEEP |
| 主線關卡 | MAIN |
| 活動高難度 | EVHI |
| 活動 SP／EX | EVSP |
| 地下城 | DGN |
| 露娜之塔 | LUNA |
| 次元斷層 | DIMEN |
| 六星解放關卡 | SIX |

區域／屬性代碼（如 FIRE／WATER 等）同樣於首筆建檔時以官方名稱定案。

## 2. 標準資料模板

```markdown
# 關卡名稱

## Metadata
- guide_id：
- server：
- mode：
- area：
- stage：
- boss：
- implemented_status：（台服已實裝／台服未實裝／僅日服）
- borrow_allowed：
- borrow_limit：
- published_date：（來源發布日）
- verified_date：／last_checked：／next_review_due：
- server：（TW／JP／CROSS_SERVER_FORECAST）
- applicable_version：（Rank／系統環境）
- source_tier：（依 01 雙軌制，如 OFFICIAL／MAJOR_GUIDE／MULTI_PLAYER_REPORT）
- claim_confidence：（B／C／D／E；單一大型攻略站最多 D）
- evidence_ids：（B／C 級須列兩筆以上，見 92）
- claim_id：（關鍵結論登錄於 93 後回填）
- stale_after：（觸發重驗條件或預估日期）
- sources：（來源＋日期，逐條）

## 敵人與關卡機制
- 敵人：
- 主要傷害類型：
- 控制／Debuff：
- 擊殺條件：
- 常見失敗原因：

## 隊伍 A（隊伍 B、C 依同格式增列）
- 標籤：（依 Instructions §7 標籤）
- 成員：（含角色版本）
- 操作：（`AUTO`／`SEMI_AUTO`／`MANUAL_TIMELINE`／`SOURCE_CONFLICT`）
- 星數／等級／Rank／專武／六星／突破／屬性強化：
- 穩定度：
- 已知隨機因素：
- 角色功能：
- 替代角色：（每缺位最多 2 名、需來源依據）
- 來源：

## 隊伍清單（Team 01～Team 10）

- 每筆攻略允許登錄 1～10 支隊伍（25 Registry 逐隊一列）。
- 每隊：team_id／五人與版本／操作模式／需求練度／台服可用性檢查（依 18）／通關證據／來源／查證日期。
- 不足 5 支時在本檔與 22 索引標「僅 N 支可追溯」。

### 2.1 25 Registry 的 operation_mode／requirements 契約（R3i）

- `operation_mode` 合法值：`AUTO`、`SEMI_AUTO`、`MANUAL_TIMELINE`、`SOURCE_CONFLICT`。
- 無法在來源間裁決操作模式時必須用 `SOURCE_CONFLICT`，不得自行選 AUTO 或 SEMI_AUTO。
- `requirements` 保留在 25 的單一欄位，但內容必須是可 `json.loads()` 且以 UTF-8、keys 排序、無多餘空白序列化的 canonical JSON。
- top-level keys 必須精確包含：`schema_version`、`operation_mode_claims`、`slots`、`support`、`timeline_ref`、`failure_conditions`；`schema_version` 固定為 `1.0`。
- `operation_mode_claims` 每項必須有 `source_id` 與 `mode`；`source_id` 須存在於同列 `source_ids`。`SOURCE_CONFLICT` 至少兩個不同來源且至少兩種 mode；非衝突模式的 claims 必須與列級 mode 相同。
- `slots` 必須精確含 `slot1`～`slot5`；每格必須含 `star`、`rank`、`ue1`、`ue2`、`six_star`、`connect_rank`、`element_boost`。
- `support` 必須含 `unit` 與 `requirements`；無支援角時 `unit=NONE`。`failure_conditions` 必須是非空陣列。
- 未知條件一律明寫 `UNKNOWN`；空字串不得冒充已知，也不得將泛化練度或記憶推定填入逐 slot 欄位。
- 來源 claim 只保存「該來源聲明了什麼」，不等於來源已實開或通關已驗證；證據層級與 `clear_status` 仍依 20、92、93 的規則獨立判定。

## 失敗排查
- 坦克過早倒下：
- 輸出不足：
- 後排被擊殺：
- 時間軸錯位：
- 借角練度不足：

## 更新紀錄
- 建立日期：
- 最後重驗日期：
- 失效原因：
```

## 3. 可靠度

A 官方可直接證明的機制或數值／B 多個大型攻略來源一致／C 多個玩家實戰一致／
D 單一影片或單一玩家／E 推測。

**隊伍可靠度通常為 B、C 或 D**；官方不提供隊伍解，故隊伍一般不會達 A。

## 4. 過期條件（觸發重驗）

- 新 Rank 實裝
- 新專武（專1／專2）改變隊伍成立條件
- 新六星改變標準解
- 新突破／強化系統
- 新角色改變標準解
- 台服實裝版本與攻略適用版本差距過大
- 關卡機制修正
- 玩家（含使用者本人）回報無法重現

觸發後：攻略標「待重驗」（22 索引同步），重驗結果更新 verified_date 或標記失效並登記 99。
