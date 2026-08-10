# ADR-0007：Princess Arena Planner typed closure 與零成熟案例邊界

- 狀態：Accepted for RP-B4-0 candidate
- 日期：2026-08-10
- 前一安全回滾點：immutable `rp-a6-0`
- Release 狀態：`PENDING`；本 ADR 不代表 commit、tag、CI 或 Gate PASS

## 背景

RP-A6-0 已將 `47_PRINCESS_ARENA_CASE_REGISTRY.csv` 正規化為 24 欄，並以同一台服
environment、`hidden_team_mode=NONE`、敵我各三隊完整五人、我方十五人不重複、三個單隊
exact WIN Claim 與一個完整三戰 WIN Claim 定義成熟 case。現有 canonical 47 仍是 0 rows、
0 mature cases；這是資料真相，不是 importer 缺陷，也不能用理論隊伍、搜尋摘要、跨服資料或
前端 fixture 補洞。

產品仍需要一個可部署的 Princess Arena walking slice，證明未來第一筆成熟案例能沿唯一
file SSOT 經 importer、PostgreSQL、FastAPI、typed client 到 `/parena`，同時在目前零案例時
誠實 fail closed。

## 決策

### Canonical 與 projection

- `research_core/pcr_tw_project/` 仍是唯一 writable SSOT。B4 不新增、改寫或推測 47 的案例。
- RP-B4-0 current manifest 是
  `eda30340c02f2f470475e652786104c521faf2ea4cc20be44cf09f3798fe8c5f`：48 files、
  13 CSV、376 rows、Evidence→Claim 120 edges、Claim→Evidence 298 edges。
- PostgreSQL 只保存 byte mirror、lossless row mirror 與 typed serving projection；API／Web
  只讀 typed projection，任何一層都不得回寫 research core。
- Materialization manifest 由 v4／23 tables 升為 v5／29 tables。V0008 新增：
  `arena_source_records`、`parena_cases`、`parena_case_matchups`、
  `parena_case_sources`、`parena_case_evidence`、`parena_case_claims`。
- 零 canonical rows 會正規化成六張存在但無案例資料的 serving tables；空集合是有效 B4
  materialization，不是建立示意 case 的理由。

### 成熟 closure

Importer 只有在同一 case 同時滿足下列條件時才可 materialize：

- `server=TW`、environment 非空且一致、`hidden_team_mode=NONE`。
- 敵方三隊與我方三隊各為完整五人；我方 15 個 unit keys 全部不重複。
- 所有角色通過 TW AVAILABLE 與台服官方名稱 closure。
- 三個 matchup 都由同環境、exact defense/counter、直接 WIN Claim 閉合。
- case 本身另有完整三戰 WIN direct Claim；Evidence、Claim、source relation 都存在且符合
  hostname、HTTPS、日期、狀態與 confidence 契約。
- `status=VERIFIED`、`reproducibility=CONFIRMED`，且所有 39 predicates 閉合。

任一條件不完整時整個 case 不進 serving closure。相同五人多來源仍只算一隊；單次報告、
Similar match、跨服 mapping 或搜尋摘要不能升格成成熟 exact case。

### API、Web 與零案例語意

- `GET /api/v1/parena/environments` 只列有成熟 case 的台服 environment。
- `POST /api/v1/solver/parena` 只接受 `server=TW`、已知 environment、三隊各五人與 15 人不
  重複的 exact defense；不提供 Similar fallback。
- Current v5 materialization 但成熟案例為 0 時，合法查詢回傳 `200`、`cases=[]` 與
  `NO_MATURE_PARENA_CASE`。
- 未來已有成熟案例、但沒有 exact signature match 時，回傳 `200`、`cases=[]` 與
  `NO_EXACT_PARENA_PLAN`。
- Active v4/A6 projection 沒有 P-Arena typed ownership；P-Arena endpoints 必須以
  `NO_PARENA_MATERIALIZATION` fail closed，不得把「無表」包裝成「查無 exact plan」。
- `/parena` 只呈現 typed response、輸入契約、Evidence Drawer 與上述明確缺口；不嵌入
  hard-coded 隊伍或第二套 CSV parser。

### 權限、Shadow Mode 與 scope

- API role 對 29 張 serving tables 只有 `SELECT`；Importer 只擁有既定 DML；Migration 是
  schema owner；Scheduler 只可操作 control tables。
- Scheduler 保持 `SCHEDULER_ENABLED=false`、`SHADOW_MODE=true`、`AUTO_PUBLISH=false`。
- Account Layer、MAIN／ALT、roster／owned、個人寶石、帳號專屬推薦與自動登入遊戲永久排除。
- 台服是攻略主體；JP 只可作未來視或研究線索，中國服／B 服不得作核心、替代或補洞依據。

### V0008 downgrade 與 rollback

- V0008 downgrade 只接受全新無 revision 的空 DB，或由 exact active A6 v4／23
  materialization 擁有、六張 P-Arena tables 均為 0 rows 的狀態。
- Active B4 v5 即使 current 47 是空的也不得直接 downgrade；ownership 不能用 scalar row
  count 取代。負向 probe 必須在獨立 disposable database 證明交易式拒絕。
- B4→A6 的正確順序是：驗證 B4 identity 與 backup → 用 B4 binary 啟用 immutable A6
  v4／23 → 驗證 P-Arena tables 清空 → V0008 downgrade V0007 → 驗證 A6 public readiness。
- 重新前進先升回 V0008，再重新啟用 exact B4 v5／29；任何失敗都保持服務 quiesced，並以
  verified backup 作人工復原邊界。不得只 checkout 舊 tag。

## 選項比較

| 選項 | 優點 | 主要風險 | 決定 |
|---|---|---|---|
| 前端直接解析 47 | 快速展示 | 第二套 parser、無 DB/API parity、無 rollback ownership | 不採用 |
| 加入示意三隊 | 畫面有內容 | 偽造 Evidence、污染成熟計數與 Gate | 禁止 |
| v5 typed zero-case slice | 跨層可驗、保持資料真相、可安全納入未來案例 | 初期 UI 誠實為空 | 採用 |
| Similar／跨服 fallback | 看似提高命中率 | 冒充 exact verified counter | 禁止 |

## 後果與 Gate

- B4 交付的是 Planner structural slice，不是 Princess Arena content expansion。
- P-Arena 仍為 0 rows／0 mature cases；Data Gates A／B／C 必須維持 `NOT PASS`。
- Application Gate D 維持 `BLOCKED_BY_DATA_GATES`；E、Automation F、Production G 均維持
  `NOT PASS`。
- 即使 unit、API、Web、E2E、ACL、backup 與 rollback 全綠，也不能由 application 測試反推
  research Gates PASS。

## 驗收與停止條件

封版前必須實跑 research 五命令、Mutation、round-trip、V0008 migration、Importer、
OpenAPI/client parity、Web build、mock/real E2E、least-privilege ACL、backup/empty-DB restore、
active-v5 downgrade negative probe 與 B4→A6→B4 drill。任何未實跑項目都標 `PENDING`。

遇到 research blob/pin 漂移、非 Gate A/B/C 額外 ARTIFACT_READY FAIL、零案例被補成示意
case、active v5 可直接 downgrade、Scheduler 越過 Shadow Mode、未驗 backup 或 rollback 後
無法恢復 exact B4 identity，立即停止封版。
