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
| sample_size | 實戰次數或紀錄筆數（可得時） |
| sources | 來源＋日期，逐條 |
| status | VERIFIED／PROVISIONAL／SINGLE_REPORT／STALE／REJECTED |
| stale_conditions | 何種環境變動觸發重驗 |

## status 定義

- **VERIFIED**：多來源一致或本人實測成功。
- **PROVISIONAL**：來源合理但未交叉驗證。
- **SINGLE_REPORT**：單一影片／留言；輸出必標【僅供參考】＋D。
- **STALE**：環境已變，待重驗。
- **REJECTED**：查證失敗或無法追溯（含無法確認伺服器的簡中紀錄）。

## 過期觸發（stale_conditions 常見值）

新競技場強角實裝／關鍵專武或六星實裝／防守核心角被強化或調整／台服與紀錄環境版本差距過大。
