# ADR-0003：逐來源操作軸與跨服重現邊界

- 狀態：Accepted
- 日期：2026-08-08
- 回滾點：`rp-a2-1`（commit `86fddc1`）

## 背景

25 Registry 已保存隊伍與逐來源 operation mode 聲明，但既有 `timeline_ref` 只是
Evidence locator。若把不同影片／攻略站的內容攤平成單一 steps 陣列，UI 會掩蓋
來源衝突，也可能把缺少正文的播放區間誤呈現成可執行操作軸。

紅焰深域 8-10 的 TM-F810-02 有三份通關影片與一份 GameWith 正文。只有
GameWith 已實開頁面的 2025 年 9 月段落提供完整有序手順；同隊雖有台服通關
影片，仍沒有證據證明該日服手順已逐步在台服重現。

## 決策

1. `26_PVE_OPERATION_TIMELINES.csv` 以 `source_axis_id` 表示每一個來源。
2. `STRUCTURED` source 才能擁有 `timeline_id` 與 27 steps；`SOURCE_GAP` 的
   `timeline_id` 在 file SSOT 固定為 `UNKNOWN`，鏡像至 DB／API 時為 `NULL`。
3. 不同來源永不合併、平均、排序成「綜合軸」。Team API 的頂層 `steps` 保留為
   deprecated 空陣列；正式步驟只存在於各 `sources[]` 內。
   25 的 legacy `timeline_ref` 欄改存該隊完整 `source_axis_id` 集合，locator 只由
   26／27 保存，避免雙重權威。
4. v3.0 初稿 action enum 補入遊戲實際需要的 `SET_ON`／`SET_OFF`；這兩個動作
   不以 AUTO 切換取代。
5. 來源未載的容錯、HP 門檻、重要度與漏按結果明寫 `UNKNOWN`。複合來源手順可拆成
   原子動作，但以 `source_step_no` 保留原分組。來源未明載戰鬥總長時，
   `battle_duration_ms` 維持未知；只有 `time_state=STATED` 的步驟可填來源時間。
6. TW 隊伍使用 JP source axis 且未逐步於台服重現時，必須標
   `UNVERIFIED_ON_TW`；同隊另有台服通關證據不能自動提升該軸。
7. Timeline status 不改變 24／25 的 team count、clear status、reproducibility
   或 Data Gate。

## 結果

- API／Web 能同時呈現 structured source 與未結構化 source，整體標為
  `PARTIAL`，使用者可直接辨識證據邊界。
- Importer、materialization manifest、readiness、backup restore 與 least
  privilege 必須把 source axes／steps 視為完整 serving closure。
- 未來從影片取得完整操作軸時，新增或更新該來源自己的 axis，不修改其他來源
  的 steps，也不建立推測式共識軸。

## 未採用方案

- 只保留一條 team-level timeline：會消除來源衝突與來源層級。
- 將影片播放秒數當戰鬥倒數：兩者不是同一時間座標。
- 因同隊在台服通關就把 JP 軸標為已重現：通關隊伍相同不代表操作點相同。
- 省略 gap rows：會讓「尚未抽取」與「來源根本沒有步驟」無法稽核。
