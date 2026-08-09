# 34 競技場來源地圖（ARENA SOURCE MAP）

> 日本競技場資料來源的專門整理（2026-07-16 初始化查證）。通用來源規則見 01；簡中處置見 Instructions §9。

## 資料庫類

| 來源 | 現況（2026-07-16） | 用法與限制 |
|---|---|---|
| nomae.net/arenadb（アリーナ編成記録DB） | 存活但社群回報約 2020/11 後停更（**已登錄 99 Stale Register**） | **僅歷史參考**；查到的編成一律視為舊環境（STALE 起手），不得當現行解 |
| pcrdfans.com（/jp/battle） | 日服玩家現役使用的作業庫（簡中站台） | 依 §9 逐筆確認紀錄伺服器與時間；日服紀錄可降級 C–D 參考；無法辨識伺服器 → REJECTED；不繞過任何存取限制 |

## 攻略站類

| 來源 | 用途 | 限制 |
|---|---|---|
| GameWith プリコネR | 環境解說、角色競技場評價 | 直接抓取被 bot 阻擋；經搜尋摘要或人工逐頁引用 |
| AppMedia プリコネR | アリーナ環境／編成頁 | 逐頁可讀性待驗 |
| VIPでプリコネ Wiki（wikiwiki.jp/vipricone_re） | 初動概念、アンチキャラ、用語 | 社群 wiki，C–D 級；日期常不明，需自行標註 |

## 影片與社群

- **YouTube 頻道類型**：アリーナ実況／防衛崩し解説／編成紹介。單一影片＝D＋【僅供參考】；找 2 部以上獨立影片一致可升 C。
- **X 搜尋法**：`プリコネ アリーナ ＜敵核心角日文名＞ 対策`、`プリコネ アリーナ 最新環境`；注意發文日期，超過當期環境即 STALE 候選。
- **掲示板／まとめ**：5ch 系まとめ站可提供線索，一律 D 級、需回溯原始出處。
- **巴哈公連板**（台服）：台服環境實戰與作業串；台服快照的主要 C 級來源。
- **ARENA-SRC-006／巴哈 2026-05-25 問答串**：主文與 B1／B2 原始圖片於 2026-08-08 實開；可支持兩筆 exact screenshot win，但兩筆同一回覆者、各一次，因此逐筆上限 `SINGLE_PLAYER_REPORT / D / SINGLE_REPORT`，不得合併成多來源 C 或勝率。
- **DEFERRED_NOT_CANONICAL／巴哈樓層 2198（2025-01-14）**：2026-08-09 已實開[討論串頁](https://forum.gamer.com.tw/C.php?bsn=30861&snA=674&page=110)、[樓層直頁](https://forum.gamer.com.tw/Co.php?bsn=30861&sn=480801&subbsn=3&bPage=0)、[防守圖](https://truth.bahamut.com.tw/s01/202501/26eb8fb8772264e340b4c12ef169b75d.JPG)、[反制 1 Win 圖](https://truth.bahamut.com.tw/s01/202501/forum/30861/fea6b8b9eb636fbcb65c497d4b2ef1fc.JPG)與[反制 2 Win 圖](https://truth.bahamut.com.tw/s01/202501/forum/30861/5c885a0592381a5d87429df2024bc0f3.JPG)。兩名不同回覆者各提供一支完整五人 Win 候選，操作均為 UNKNOWN；另已實開台服官方 [#3721](https://www.princessconnect.so-net.tw/news/newsDetail/3721) 與 [#3728](https://www.princessconnect.so-net.tw/news/newsDetail/3728)，確認 `エキドナ（サマー）` 的官方名為「艾姬多娜（夏日）」且已實裝。敵我 11 個 role key 目前仍均不在 18，其中「禊（夏日）」尚缺可實開的台服官方正文，其餘逐角可用性／Evidence 也未完成 canonical 閉合，故只作待辦線索，不進 39／Evidence／Claim／Gate。

## 更新頻率與舊版本可查性

- 資料庫類可查舊紀錄但**無環境版本標籤**——時間即版本，引用時必附紀錄日期。
- 攻略站環境頁通常只保留現行版；歷史環境需靠 32 快照自行累積。

## 禁止事項

不繞過 bot 防護／不整站爬取／不批量複製；簡中來源不得作為主要依據（§9）。
