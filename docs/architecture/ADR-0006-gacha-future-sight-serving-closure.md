# ADR-0006：Gacha 未來視 typed serving closure 與未知值邊界

- 狀態：Accepted for A4／B5-1
- 日期：2026-08-10
- 前一安全回滾點：`rp-b3-d0-1`

## 背景

Research core 已有 `41_GACHA_TIMELINE.csv` 與
`45_GACHA_COMMUNITY_SOURCE_INDEX.csv`，但 RP-B3-D0 的 PostgreSQL、API 與 Web 尚未把
Gacha 正規化成 typed serving closure。2026-08-09 Freshness 重驗又新增兩筆日服官方直播
事件；官方投影片只直接支持角色登場、池名與日期，沒有直接明示兩角的限定身分、台服中文名
或角色價值。若 serving layer 以卡池名稱、社群中文翻譯或既有角色慣例補值，就會把研究中的
`UNKNOWN` 轉成產品層臆測。

社群未來視的用途也與官方 Evidence 不同。兩筆現行社群來源可支持月份／順序研究，但精確日期
仍可能只有單一來源；另外兩筆來源已過時。`CHECKED` 只代表正文實開並完成維護狀態核對，不能
升格為 OFFICIAL／A，也不能把個人寶石門檻、社群自譯名或帳號持有條件帶回 Active Scope。

## 決策

### Canonical 與 typed closure

- File research core 仍是唯一 writable SSOT。`41` 與 `45` 連同 referenced `92`／`93`
  由 immutable manifest 鎖定；PostgreSQL 只保存 read mirror 與 typed serving projection。
- V0007 新增 `gacha_timeline_events`、`gacha_timeline_evidence`、
  `gacha_timeline_claims`、`gacha_community_sources`、
  `gacha_timeline_community_sources` 五表，materialization schema version 由 3 升為 4。
- Gacha event 與其 Evidence／Claim／community relation 必須在同一 importer transaction
  驗證、寫入與啟用。ID 不存在、module／server／status 不合、relation 重複、日期區間或
  method shape 不一致即整批拒絕。
- RP-A5 及更早的 immutable source 仍可由 B5 binary 回放成既有 v3／v2 projection；歷史
  manifest 不因 B5 current pin 而改寫。

### 未知值、名稱與研究成熟度

- `source_server` 固定為 JP、`target_server` 固定為 TW。跨服日期是模型輸出，不是台服官方
  公告。
- `tw_name` 只有在 typed closure 能直接證明台服 OFFICIAL／A 中文名時才可具值；否則為
  `null`，Web 顯示「台服官方名稱待公告」。不得 fallback 到社群翻譯或自行翻譯。
- `limited_status` 只接受 `YES`、`NO`、`UNKNOWN`。池名含 Anniversary、Princess Fes 或
  Prize 不足以自行推出限定身分。`YES`／`NO` 必須帶同列 `limited_claim_id`，且該 Claim
  必須是 ACTIVE／JP／gacha／SOURCE_FACT／A，並由同列 relation 直接連到 ACTIVE／JP／
  OFFICIAL／A Evidence；`UNKNOWN` 則必須為 `limited_claim_id=null`。自由文字與 transitive
  relation 都不能替代這個 closure。
- `OFFICIAL_OVERRIDE` 同樣必須由同列指定的 ACTIVE／TW／gacha／SOURCE_FACT／A Claim 與
  ACTIVE／TW／OFFICIAL／A Evidence 直接閉合，不能只靠 override label 提升可信度。
- `maturity=RESEARCH` 時，四個模式價值與 `relative_priority` 必須全部為
  `NOT_EVALUATED`；`future_upgrade` 只允許 `UNKNOWN` 或 `NOT_EVALUATED`。自由文字不得
  夾帶「必抽／建議抽」來規避結構化守門。
- `MATURE` 只表示既有公共價值研究已完成其 schema closure，不代表日期成為台服官方排程，
  也不代表帳號專屬推薦。

### 社群來源邊界

- Community `confidence_cap` 只允許 C／D／E；A／B／UNKNOWN 皆由 Validator、Importer、
  ORM 與 OpenAPI 同步拒絕。
- `CHECKED`、`STALE`、`PENDING_FETCH` 保存來源維護狀態；`CHECKED` 不會自動增加 timeline
  event 的 `community_source_count`。只有逐 event 建立可驗 relation 後才可連結。
- MONTH precision 不得倒推出 DAY interval。兩來源只在月份／順序層級一致時，不能宣稱
  共同支持其中一方的精確日區間。
- 個人寶石、roster／owned、MAIN／ALT 與帳號專屬推薦永久排除。UI 只呈現公共相對評估、
  通用公式或資料缺口。

### API、metadata 與 Web

- 新增唯讀 `GET /api/v1/gacha/timeline` 與
  `GET /api/v1/gacha/community-sources`；不新增 Gacha write endpoint，也不讓一般
  `/api/v1/gacha/*` POST 通過 D0 allowlist。
- Event、Evidence、Claim 與 community IDs 都去重並 lexical sort。API 不以 CSV 列順序或
  DB collation 製造不穩定輸出。
- Timeline 同時含 JP source 與 TW target，因此集合 metadata 的 `server=MIXED`。在全部
  Evidence／Claim freshness 與 A–E confidence 尚未成為 typed aggregation input 前，
  envelope 的 `verified_at=null`、`stale_status=UNKNOWN`、`confidence=UNKNOWN`；單列
  `last_verified` 可如實顯示，但不能冒充整個 response closure。
- Web `/gacha` 呈現 MATURE／RESEARCH、模型區間、未知限定身分、社群 freshness 與
  Evidence Drawer；已知限定身分同時顯示 `limited_claim_id`，UNKNOWN 明示沒有限定依據。
  頁面明示模型是日期參考而非個人抽卡指令。Desktop 與 mobile 使用同一 typed client
  contract。

### Schema downgrade 與 rollback

- V0007 downgrade 只接受兩種起點：全新無 revision 的空 DB，或 active、SUCCEEDED、
  pointer／digest／18-table manifest 全部精確一致的 v3 materialization，且五張 Gacha 表
  都是空表。
- Active v4 即使有人手動清空 Gacha rows 仍不得降版；scalar row count 不是 ownership
  證明。
- B5 回退 A5 的正確順序是：驗證備份與 B5 identity → 以 B5 binary 啟用 pinned A5 v3
  projection → 證明 Gacha 五表為 0 → V0007 降至 V0006。重新前進時先升 V0007、重新
  provision roles，再啟用 B5；不能只 checkout 舊 tag。

## 選項比較

| 選項 | 優點 | 主要風險 | 決定 |
|---|---|---|---|
| 只在 Web 解析 41／45 | 最快顯示 | 形成第二套 parser，無 DB/API parity 與 rollback 邊界 | 不採用 |
| 把社群中文名／池型推成完整資料 | 畫面較少 UNKNOWN | 違反官方名稱與 Evidence 規則，製造假精度 | 禁止 |
| Typed v4＋保守 null／UNKNOWN | 可稽核、跨層一致、可安全回放 | 初期資料較少且 metadata 保守 | 採用 |
| 同時建立個人寶石建議器 | 功能看似完整 | 重新引入永久排除的 Account Layer | 禁止 |

## 後果與後續

- RP-B5-1 只完成第一個 Gacha source→DB→API→Web 垂直切片。正式 A4 的 Timeline Gate
  仍只有 2/6 MATURE；新增三筆 RESEARCH 不計成熟分子。
- Community Gate 可如實由 0/2 進到 2/2，但 Data Gates A／B／C 仍因其他內容與 14 個
  blocking warnings 未通過；Application Gates D／E、Automation F、Production G 亦不得
  因此升級。
- 未來若要以 community consensus 調整日期，必須先建立逐 event relation、保存 precision
  與 disagreement，不能直接改 `tw_estimate_*`。
- Gacha／News 自動更新仍須先進 B6 Shadow candidate queue；不得直接寫 canonical data。

## 驗收與停止條件

只有在 research 五命令、Mutation、V0007／Importer、OpenAPI client parity、Web build、
desktop/mobile mock 與 real-stack E2E、least-privilege ACL、backup／restore、V0007 lossless
downgrade guard，以及 B5→A5→B5 rollback 全部實跑後，RP-B5-1 才可封存。若任何台服名或
限定身分由推測補入、RESEARCH 偷渡抽取建議、mock 與 real Evidence 漂移、active v4 可被
直接降版、ARTIFACT_READY 出現 Gate A／B／C 以外 FAIL，立即停止並回到
`rp-b3-d0-1`／已驗證 backup。
