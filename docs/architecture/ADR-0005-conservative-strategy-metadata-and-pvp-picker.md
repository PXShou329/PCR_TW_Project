# ADR-0005：保守 Strategy Metadata 與 Arena exact picker 邊界

- 狀態：Accepted for B3／D0
- 日期：2026-08-09
- 前一安全回滾點：`rp-a5-2`

## 背景

RP-A5 已有 typed Arena closure、order-insensitive exact signature API、結果卡與 Evidence
Drawer，但 `/pvp` 尚無五角色輸入；API envelope 也只有 artifact／revision source pins，尚未
包含 v3.0 企劃要求的 `server`、`environment_version`、`verified_at`、`stale_status`、
`confidence`、`evidence_ids`、`claim_ids` 與 `data_revision`。

這些欄位不能用 importer 執行時間、單一代表列或 UI 猜測補值。集合型 response 可能同時含
多個 server、environment、日期與 confidence；若聚合規則沒有先固定，後續 PVE、Arena、
P-Arena 與 Gacha 會各自產生不同語意。另一方面，research core 已明定 exact formation identity
不受輸入順序影響；member slot 仍須原樣保存供顯示，不能為了 picker 改寫封存語意。

## 決策

### Required-but-conservative metadata

所有 `/api/v1/*` envelope 都必須出現完整 v3.0 metadata 欄位；無法由該 response closure
機械證明時，使用 `UNKNOWN`、`null` 或空集合，不得以 revision import 時間或任意一列代替。
`source` pins 與既有 `warnings` 保留，兩者和 strategy metadata 是不同層次。

聚合規則固定如下：

- `data_revision` 永遠等於 active `CoreRevision.revision_id`。
- `server`、`environment_version`：所有 record 皆有值且完全相同才回具體值；多個不同值回
  `MIXED`；空集合或任一 record 缺值回 `UNKNOWN`。
- `verified_at`：只有所有 record 都有可驗證日期時，回其中最舊日期，代表整個 closure 的
  最弱 freshness；否則為 `null`。`ImportRun.imported_at` 不得冒充資料查證日。
- `stale_status`：任一 record 無法判定即 `UNKNOWN`；有任一 `STALE` 即 `STALE`；全部
  `CURRENT` 才可回 `CURRENT`。
- `confidence`：只有所有 record 都有合法 A–E 值時，回最弱的一級；否則 `UNKNOWN`。
- `evidence_ids`、`claim_ids`：只取 response closure 實際引用 ID 的去重、穩定排序聯集。

D0 先只為 Arena character picker 提供可機械證明的 `server=TW` 與 referenced Evidence IDs，
並為 counter results 提供同質 `server`、`environment_version` 與 typed Evidence／Claim IDs。
兩者的 `verified_at`、`stale_status`、`confidence` 仍固定為 `null`／`UNKNOWN`／`UNKNOWN`，
直到完整 character／defense＋Claim＋Evidence freshness/confidence closure 也成為 typed aggregation
輸入；不得再用 Character 或 counter 單列代表整個 response。其他既有 route 先遵守
required-but-conservative 形狀，後續各垂直切片再接上自己的 typed closure。欄位存在不等於
Gate D 已通過；在 Data Gate A／B／C 與全 endpoint 聚合尚未閉合前，Gate D 仍為
`NOT PASS`。

### Picker 與 exact query

- 新增唯讀 `GET /api/v1/pvp/characters`，只列 typed mirror 中
  `availability_status=AVAILABLE` 的角色，以 Python `(tw_name, unit_key)` 穩定排序。
- AVAILABLE 角色若沒有可用的台服 canonical name，serving fail-closed；不得 fallback 成
  自行翻譯的中文名。日文 alias 只回傳 DB 已保存的官方日文名。除此之外，每個 AVAILABLE
  角色至少要有一筆自身 `source_evidence_ids` 實際引用、且為 `ACTIVE/TW/OFFICIAL/A` 的
  Evidence；API 以單次 union batch query 驗證，Importer 對所有 AVAILABLE 角色使用同一
  fail-closed predicate，不只檢查 Arena PASS 成員。
- Web 以五個角色欄位建立可分享的 GET query；必須剛好五個不同 `unit_key` 才呼叫 exact
  counter API。
- 這個唯讀、可分享的 exact lookup 沿用 `GET /api/v1/pvp/counters`；企劃中的
  `POST /api/v1/solver/pvp` 留給日後包含 Similar 解釋與更多求解條件的 B3 完整 solver，
  本切片不建立兩個意義重疊的查詢入口。
- exact identity 沿用 research schema 的 order-insensitive canonical signature；來源 member
  slot 與畫面順序仍保留，不混入 identity。
- 本切片不啟用 Similar。找不到 exact result 時回結構化 no-result，UI 繼續明示
  `NO_VERIFIED_COUNTER`／`NO_EXACT_COUNTER`，不得自行用四人重疊或相似隊補洞。
- Character endpoint 是目前 research typed mirror 的可選集合，不宣稱為全角色百科。

## 選項比較

| 選項 | 優點 | 主要風險 | 決定 |
|---|---|---|---|
| 只保留既有 source pins | 不改 contract | Gate D metadata 持續缺漏，前端容易猜值 | 不採用 |
| 用 import time／第一列填滿欄位 | 實作最少、看似完整 | 製造錯誤 freshness 與代表性，違反 UNKNOWN 鐵則 | 禁止 |
| Required 欄位＋保守 closure 聚合 | 語意一致、可逐 endpoint 擴充、fail-closed | 初期會出現 UNKNOWN/null，需多寫測試 | 採用 |
| 本輪同時啟用 Similar | UI 一次到位 | 尚無 core tags／機制檢索與成熟資料，容易把近似當 exact | 延後 |

## 後果與後續

- OpenAPI、TypeScript client、contract checker 與 desktop/mobile E2E 必須同時驗證新增欄位及
  picker；任何 client drift 都 fail closed。
- Arena 成熟度仍完全由 research Validator／typed maturity predicate 決定；picker 不提高
  confidence，也不改 0 mature defenses 的事實。
- Similar 必須另立可解釋的 matching contract，至少回傳差異角色、核心機制、environment
  與「非完全同陣」警示後才可開啟。
- 回滾不涉及 schema downgrade：停止新 revision／服務，驗證備份後回到 `rp-a5-2` 的程式與
  immutable research pins；DB V0006 保持不變。

## 驗收與停止條件

只有在 API focused tests、OpenAPI client parity、typecheck、production build、desktop/mobile
mock 與 real-stack E2E 全部通過，且 research 五命令與 Mutation 無回歸後，B3／D0 切片才可
封存。若 picker 可送出重複／不足五人、API 發生 Similar fallback、metadata 使用猜測值、
AVAILABLE 名稱不具台服 closure，或 ARTIFACT_READY 新增 Gate A／B／C 以外 FAIL，立即停止並
回到 `rp-a5-2`。
