# ADR-0001：Research Core 為唯一可寫 SSOT，PostgreSQL 先作唯讀鏡像

- 狀態：Accepted for B0–B7
- 日期：2026-08-08

## 背景

R3i 的 46-file research core 已有獨立 Validator、Mutation 與 Gate 語意。v3 應用需要 PostgreSQL 查詢能力，但在 importer/exporter parity、備份還原與審核流程完成前，同時開放檔案與資料庫寫入會形成雙 SSOT。

## 決策

1. B0–B7 期間，`research_core/pcr_tw_project/` 是唯一可寫 canonical data。
2. PostgreSQL 僅由 deterministic importer 建立 read mirror；公開 API 全部唯讀。
3. Scheduler 使用 Shadow candidate／sync tables，不得寫入 canonical tables。
4. B8 只有在 Data Gate A／B／C、100% parity、restore drill、rollback 與單一 writer 證明全部通過後，才可原子切換 writable SSOT。

## 後果

- B0 資料庫可以直接丟棄並由 research core 重建。
- Importer 必須 fail-closed；任何 FK、Enum、team count 或 Evidence closure 差異都整批 rollback。
- API 與 UI 不得補推論值，也不得把 `UNKNOWN`、`PROVISIONAL` 或低信心資料升級。

