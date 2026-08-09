# ADR-0003：Scheduler 預設停用並以 Shadow Mode fail-closed

- 狀態：Accepted for B0
- 日期：2026-08-08

## 決策

- `SCHEDULER_ENABLED=false`
- `SHADOW_MODE=true`
- `AUTO_PUBLISH=false`

B0 scheduler 僅提供 process health、heartbeat 與可重入 fixture-check skeleton，不連接 live source、不發佈 canonical data。任何未設定、解析失敗或重啟情境均回到上述安全值。

正式啟用前必須具備 PostgreSQL lock／lease、`unique(job_name, scheduled_for)`、crash/restart/concurrency tests、結構化 audit log、持久化 kill switch，以及無 canonical write 權限的 DB role。Auto-publish 必須在至少 14 天 Shadow observation、人工審核與 rollback 演練後另行放行。

