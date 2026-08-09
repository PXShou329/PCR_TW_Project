# RP-A6-0 local/private deployment

`compose.yml` is a production-shaped local/private staging stack, not a public
production manifest. PostgreSQL is pinned to `18.4-bookworm`; every published
port binds only to `127.0.0.1`, and the database lives on an internal Docker
network. Alembic is the sole schema migration owner.

The startup dependency chain is:

```text
db healthy -> migration(owner) -> role-provision -> importer(DML) -> api(SELECT) -> web
                                          `-------> scheduler(control tables only)
```

Run it from the repository root after creating a private `.env` from
`.env.example`:

```powershell
docker compose --env-file .env -f infra/compose.yml up --build --wait
```

`verification` profile 包含會操作 control tables、typed rows、cache epoch 與
revision／activation 狀態的 verifier，因此不得用
`docker compose --profile verification ... up` 併發啟動。先以上述命令啟動
不含 profile 的 base stack，再依固定順序逐一執行完整 verification pipeline：

```powershell
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps scheduler-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps round-trip-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps consistency-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps cache-epoch-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps artifact-lock-smoke
```

此時 latest A6 activation 仍須為正常部署的 `IMPORT`／`REACTIVATE`。在執行會留下
測試性 `ROLLBACK` activation 的 history smoke 前，必須依 A6 rollback runbook 完成：

1. `./scripts/backup_restore_smoke.ps1`，取得並驗證 backup receipt。
2. 匯出 immutable `rp-b5-1` checkpoint。
3. `./scripts/a6_b5_rollback_drill.ps1`，完成 A6→B5→A6 演練。

以上 release operations 全部成功後，才可執行：

```powershell
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps revision-history-smoke
docker compose --profile verification --env-file .env -f infra/compose.yml run --rm --no-deps revision-history-verify
```

最後才執行 real-stack browser E2E：

```powershell
npm run test:e2e
```

固定順序是「前五個 verifier → backup＋A6→B5→A6 drill → 兩個 history verifier → E2E」；
不得把任何 verification service 改回 profile-wide `up`。

任一步失敗都必須停止後續驗證並保留現場；不可用重試掩蓋 lock、deadlock 或
epoch chronology 錯誤。

API-family runtime and profile-only verification services share one
`${PCR_API_IMAGE}` so a smoke cannot silently run stale code. Do not set
`AUTO_PUBLISH=true` or `SHADOW_MODE=false`; the scheduler rejects both in RP-A6-0.
See `docs/operations/B1_RUNBOOK.md` for the still-valid full-core round-trip,
verification, backup restore and atomic rollback procedure inherited from the B1
foundation. The rollback chain has two independent fail-closed boundaries:
V0005 refuses V0004 while any honest `is_borrowed IS NULL` remains, and V0004
refuses V0003 while any honest `UNKNOWN` operation-mode row remains.
The current image carries the RP-A6-0 current manifest plus immutable RP-B5-1／RP-A5／
RP-A4／RP-A3／RP-A2 rollback checkpoints. A6 and B5 share V0007／materialization v4／
23 typed tables, so A6→B5→A6 is a same-schema data activation with zero Alembic
commands. Follow `docs/operations/A6_ROLLBACK_RUNBOOK.md` for the exact
backup-first procedure, image／project／port preflight, intermediate B5 serving
proof and fail-closed A6 recovery boundary. For the historical RP-A4 to RP-A3 deployment order and
roll-forward procedure, follow `docs/operations/A4_ROLLBACK_RUNBOOK.md`. For the
V0007／V0006 B5→A5→B5 backup-first procedure, exact image／project／port preflight,
and fail-closed recovery boundary, follow `docs/operations/B5_ROLLBACK_RUNBOOK.md`.

The A6 candidate does not claim Data／Application／Automation／Production Gates
A–G PASS. Private CI must complete before an annotated `rp-a6-0` tag is created;
existing tags remain immutable.
