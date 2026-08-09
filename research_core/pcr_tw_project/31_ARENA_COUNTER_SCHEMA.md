# 31 競技場反制資料 Schema（ARENA COUNTER SCHEMA）

> 每筆經 30 流程驗證的反制資料依本格式記錄（初期記於 33 研究日誌內；量大後獨立成庫）。

## 欄位

| 欄位 | 說明 |
|---|---|
| counter_id | `<server>_ARENA_<日期YYYYMMDD>_<流水>`，例：JP_ARENA_20260716_01 |
| server | JP／TW（紀錄出處環境） |
| published_date／verified_date／last_checked／next_review_due | 統一日期欄（依 01 標準） |
| environment_version | 環境版本描述（當期關鍵角／專武／六星） |
| enemy_team | 敵方五人（含版本、站位） |
| enemy_core | 防守核心與成立機制 |
| counter_team | 反制五人（含版本、練度條件） |
| mechanism | 反制原理（初動、控制鏈、勝利條件） |
| required_investment | 必要練度（星／Rank／專武／六星） |
| initial_action | 初動與時間軸要點 |
| randomness | 隨機因素與失敗模式 |
| source_tier | 依 01 雙軌制（單一大型攻略站＝MAJOR_GUIDE） |
| claim_confidence | B／C／D／E（單一 MAJOR_GUIDE 最多 D；升 B 需兩獨立大型來源） |
| evidence_ids | B／C 級至少兩筆（見 92） |
| claim_id | 關鍵結論登錄於 93 後回填 |
| source_record_count／source_platforms | 來源紀錄筆數與平台集合；只描述來源涵蓋，不等於來源獨立性或實戰樣本 |
| sample_size | 來源明示的實戰觀測次數；與 source_record_count 分離，無分母時保持 NULL |
| sources | 來源＋日期，逐條 |
| status | VERIFIED／PROVISIONAL／SINGLE_REPORT／STALE／REJECTED |
| stale_conditions | 何種環境變動觸發重驗 |
| match_type／outcome／verification | 固定 EXACT，以及來源實際戰果與佐證形式 |
| wins／losses／empirical_win_rate | 明示樣本計數；單筆結果不計算勝率 |
| rng_risk／operation_mode／environment_match | 可驗證的類別欄位；來源未述時固定 UNKNOWN |
| arena_bracket／speed_conditions／initial_action_notes | 來源條件；未知必須明示 UNKNOWN，不得留白或推測 |
| reproducibility | CONFIRMED／UNVERIFIED_REPEATABILITY／UNVERIFIED_ON_TW／UNKNOWN；不得沿用 PVE timeline 的 TW_REPRODUCED |

## Exact 與單筆戰果的發布契約

- `enemy_team_ids` 與 `counter_team_ids` 必須各為五個不同且存在於 18 的 `unit_key`；exact signature 比對不受輸入順序影響，但來源列順序仍須保留。
- `match_type=EXACT` 只表示敵方五人完全相同，**不等於** `status=VERIFIED`。
- 一張明示 Win／Lose 的完整戰果圖可記 `sample_size=1` 與 `SINGLE_REPORT / D`；沒有多次試驗分母時，`empirical win rate` 必須為 `NULL`，不得寫成 100%。
- 同一作者提供兩支不同反制，只是兩個 counter signature；作者獨立性仍為一，不得互相交叉驗證。
- `SINGLE_REPORT` 可在 UI 作【僅供參考】的可追溯研究資料，但不得計入 Arena Gate，亦不得使用「穩定解」「已驗證反制」等文案。
- A5 的 `VERIFIED` 暫只接受可機械驗證的多來源閉合：39 列及其反制核心 Claim 為 B／C，`environment_match=EXACT`，至少兩筆同服、同一 exact 配對的 ACTIVE Arena Evidence 可追溯，且 93 已通過以 hostname 判定的來源獨立性檢查（不同 port 不算不同來源）；每筆核心 Evidence 的 `source_url` 必須是具非空 hostname 的 HTTPS URL。一般 ST49 可為離線 B／C Claim 使用 locator／title fallback，但該 fallback 不得使 Arena 列成熟。39 的 source tier 必須為 OFFICIAL／MAJOR_GUIDE／STRUCTURED_DB／COMMUNITY_WIKI／MULTI_PLAYER_REPORT，92 Evidence tier 另可為 SINGLE_PLAYER_REPORT，但不得 UNKNOWN／RESTRICTED／自造值。`source_record_count>=2` 仍只是必要 metadata，不能取代 Evidence closure。
- `VERIFIED` 另須使用 `reproducibility=CONFIRMED`；但在獨立 Arena run registry 建立前，手填 CONFIRMED 或聲稱本人實測都不能作為 `SELF_TESTED` 捷徑。`SINGLE_REPORT` 固定為 D，且仍須有同服 `arena` module 的 ACTIVE Evidence／Claim closure。
- `sample_size` 只保存明示戰果觀測；不得把兩個來源當成兩次試驗。未取得分母時保持 NULL；有明示計數時才保存 wins／losses，單筆不計 empirical win rate。

## Arena Gate 成熟防守定義

- Gate 統計的是 mature defenses，不是 `VERIFIED` counter rows。
- 同一個 TW `environment_version` 與同一敵方五人 signature，至少有兩支不同反制五人 signature，且每支均滿足 A5 多來源 `VERIFIED`、台服可用性、同服 ACTIVE Evidence／Claim、日期與新鮮度條件，才計一個成熟防守案例。
- 多個來源記錄同一敵我五人只合併 Evidence，不得製造第二支 counter；不同反制若仍由同一作者提供，也不構成彼此的獨立來源。

## status 定義

- **VERIFIED**：A5 暫限定為上述可機械驗證的 B／C 多來源閉合；SELF_TESTED 分支尚未開放。
- **PROVISIONAL**：來源合理但未完成多來源閉合；包含尚無獨立 run registry 可追溯的本人實測聲明。
- **SINGLE_REPORT**：單一影片／留言；輸出必標【僅供參考】＋D。
- **STALE**：環境已變，待重驗。
- **REJECTED**：查證失敗或無法追溯（含無法確認伺服器的簡中紀錄）。

## 過期觸發（stale_conditions 常見值）

新競技場強角實裝／關鍵專武或六星實裝／防守核心角被強化或調整／台服與紀錄環境版本差距過大。
