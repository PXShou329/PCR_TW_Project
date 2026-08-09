# RP-A6-0 backup／restore 與 A6→B5→A6 回滾手冊

日期：2026-08-10（Asia/Taipei）

## 適用範圍

本手冊只適用於 RP-A6-0 Princess Arena Gate-correctness 候選回退至 immutable RP-B5-1，
以及其後恢復 A6。兩代都是 V0007／materialization v4／23 張 typed serving tables；本演練
只切換經 pin 驗證的 data revision，不執行 Alembic downgrade／upgrade。

這不是一般性的 `docker compose down` 指南，也不能用 checkout 舊 tag 取代 data rollback。
RP-A6-0 沒有 P-Arena typed serving slice；回退不會創造或刪除 P-Arena tables。Data Gates
A／B／C、Application Gates D／E、Automation Gate F 與 Production Gate G 均未通過。

## Portable source identities

```text
RP-A6-0 manifest  fbcac9cb9aadcd1569f881469189dc791c68a4a329637cc9db2c0d7263d68ed1
RP-A6-0 raw       3f5e738a6a7f0463583b38d0fc2ca1ae35bdc563f3815cf436dfc10913764d97
RP-A6-0 semantic  82495781cca66b9ca3fc221e609a3cb6c06ebaa823f7a8613c9d5d1d01d9e1ee
RP-B5-1 manifest  e74814d6433ee327611f10322937bdfa9687b9887f139ba6e6158a291dd12989
RP-B5-1 raw       d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d
RP-B5-1 semantic  a7467a838c2a9cfdfe48bda4a3b158fb374dd023caa3478a84c07678532ea9f4
```

兩代都是 48 files／13 CSV／376 rows；Evidence→Claim 120、
`a2fa8f263d612cd393bbd25d29d01f9ffde4015ed924e7b28a8ed909b99c67af`，
Claim→Evidence 298、
`24c1cbce3588926d4efe657c8da94b968aa25dd288e764ebbed0f18c1203d43c`。

`artifact_mirror_sha256` 是 deterministic artifact diagnostic；typed
`materialization_sha256`、ImportRun、activation sequence／epoch 與 history digest 都是
instance state。這些值不得取代上述 portable source pins。

## 不可省略的前置條件

- 在 repository root 執行；PowerShell 7、Docker Compose v2 與 immutable tag `rp-b5-1`
  必須可用。
- 使用 Git 忽略的 private env file；不得將密碼、dump、receipt 或 checkpoint commit。
- ProjectName、API／Scheduler images、API／Web／Scheduler ports 必須明確傳入；腳本會在
  stop 或 DB mutation 前核對 resolved Compose config、container label、named volume 與
  loopback-only binding。
- 不得使用既有 `pcr-tw-b5-gacha`、`pcr-tw-a5-arena`、`pcr-tw-a4-water`、`pcr-tw-b1`
  等 project；回滾只能作用於明確指定的隔離 A6 stack。
- Scheduler 必須 `SCHEDULER_ENABLED=false`、`SHADOW_MODE=true`、
  `AUTO_PUBLISH=false`。
- 必須先取得且實際 restore 過的 backup receipt；沒有 exact path／SHA-256 不得開始。
- B5 rollback source 必須是完整 tag tree。Current importer 會在 quiesce 前以唯讀
  `_verify_import_source` 驗證整棵 tree，且驗證前後 origin sequence／epoch 必須完全不變。

本次已驗 staging target：

```text
project=pcr-tw-a6-parena-drill
api_image=pcr-tw-platform-api:a6
scheduler_image=pcr-tw-platform-scheduler:a6
api_port=8500 web_port=3500 scheduler_port=8581
```

## Verification profile 的固定串行邊界

`verification` profile 內的服務會操作 control tables、typed rows、cache epoch 或 revision
history。禁止執行 `docker compose --profile verification ... up`；該命令會讓 verifier 併發，
使 lock、epoch 與 chronology 證據失真。

先啟動不含 profile 的 base stack，再依序逐一執行：

1. ACL verifier。
2. `scheduler-smoke`。
3. `round-trip-smoke`。
4. `consistency-smoke`。
5. `cache-epoch-smoke`。
6. `artifact-lock-smoke`。
7. 本手冊的 backup／restore 與 A6→B5→A6 drill。
8. `revision-history-smoke`。
9. `revision-history-verify`。
10. Playwright real-stack E2E。

任一步失敗都停止，不得用重試掩蓋 deadlock、epoch rewind 或 activation chronology drift。

## 1. 啟動並核對 A6 origin

下列 private env path 是操作員輸入；不要把 secret 寫進命令紀錄或文件：

```powershell
$A6EnvFile = (Resolve-Path '<git-ignored-A6-env-file>')
$A6Project = 'pcr-tw-a6-parena-drill'
$env:PCR_API_IMAGE = 'pcr-tw-platform-api:a6'
$env:PCR_SCHEDULER_IMAGE = 'pcr-tw-platform-scheduler:a6'
$env:API_PORT = '8500'
$env:WEB_PORT = '3500'
$env:SCHEDULER_HEALTH_PORT = '8581'
$env:SCHEDULER_ENABLED = 'false'
$env:SHADOW_MODE = 'true'
$env:AUTO_PUBLISH = 'false'

docker compose --project-name $A6Project --env-file $A6EnvFile `
  -f infra/compose.yml config --quiet
docker compose --project-name $A6Project --env-file $A6EnvFile `
  -f infra/compose.yml up --detach --no-build --wait --wait-timeout 180
```

核對 API readiness、Web、Scheduler health；scheduler 必須 disabled＋Shadow Mode，且
`canonical_write_capable=false`。起點必須是 active A6 revision、V0007 與本 instance 的 exact
ImportRun／typed materialization。

## 2. 先做 backup／restore smoke

```powershell
.\scripts\backup_restore_smoke.ps1 `
  -EnvFile $A6EnvFile `
  -ProjectName $A6Project `
  -ExpectedApiImage 'pcr-tw-platform-api:a6' `
  -ExpectedSchedulerImage 'pcr-tw-platform-scheduler:a6' `
  -ExpectedApiPort 8500 `
  -ExpectedWebPort 3500 `
  -ExpectedSchedulerPort 8581 `
  -KeepBackup
```

成功必須包含：

```text
A6_COMPOSE_PREFLIGHT_OK
A6_DB_TARGET_OK
A6_ARTIFACT_DIAGNOSTIC_PINNED
BACKUP_ARTIFACT_VERIFIED
RESTORED_HISTORY_DIGEST_OK
RESTORED_ROUND_TRIP_OK
RESTORED_API_READINESS_OK
RESTORED_WEB_EVIDENCE_OK
GACHA_DOWNGRADE_BLOCKED_OK
BACKUP_RESTORE_OK
{"status":"BACKUP_RESTORE_VERIFIED",...}
```

最後一行 JSON 是唯一可交給 rollback drill 的 receipt。保存 `path`、`sha256`、`bytes`、
source revision／ImportRun／typed materialization／epoch，並另外重算檔案 size 與 SHA-256。
`-KeepBackup` 只保留成功 receipt 指向的 dump；失敗或沒有 verified receipt 的 artifact 不能用。

本次 verified receipt：

```text
path   .runtime/backups/pcr_tw_20260809204424_91fdb6.dump
sha256 910c5337c27f43aaf912701f8f4474870e6f2125e79b1e53052cb4bc85cfd3df
bytes  570879
```

這是本次 instance evidence，不是 portable release source。

## 3. 從 immutable tag 建立 RP-B5-1 checkpoint

不要複製目前 working tree，也不要只拿 manifest。目標必須是全新、Git 忽略且已人工確認
位於 repository `.runtime` 下的目錄：

```powershell
git rev-parse --verify 'refs/tags/rp-b5-1^{}'

$B5Checkpoint = Join-Path $PWD '.runtime/rp-b5-1-a6-checkpoint'
$B5Archive = Join-Path $PWD '.runtime/rp-b5-1-a6-checkpoint.tar'
if ((Test-Path -LiteralPath $B5Checkpoint) -or (Test-Path -LiteralPath $B5Archive)) {
  throw 'RP-B5 checkpoint target already exists'
}
New-Item -ItemType Directory -Path $B5Checkpoint | Out-Null
git archive --format=tar --output=$B5Archive rp-b5-1
if ($LASTEXITCODE -ne 0) { throw 'Could not export immutable rp-b5-1' }
tar -xf $B5Archive -C $B5Checkpoint
if ($LASTEXITCODE -ne 0) { throw 'Could not extract immutable rp-b5-1' }

Get-FileHash -LiteralPath $B5Archive -Algorithm SHA256
```

Checkpoint 內必須同時存在：

```text
research_core/pcr_tw_project/
scripts/research_core_rp_b5_1_manifest.sha256
```

本次 archive SHA-256 為
`38d069389ade48c374d205a476c5a9a2f85146faae662300a1b64e7139d38ecc`；另一個 deployment
仍必須重新匯出並自行驗證，不可只相信這個本機 path。

## 4. 執行 A6→B5→A6 演練

```powershell
.\scripts\a6_b5_rollback_drill.ps1 `
  -EnvFile $A6EnvFile `
  -ProjectName $A6Project `
  -ExpectedApiImage 'pcr-tw-platform-api:a6' `
  -ExpectedSchedulerImage 'pcr-tw-platform-scheduler:a6' `
  -ExpectedApiPort 8500 `
  -ExpectedWebPort 3500 `
  -ExpectedSchedulerPort 8581 `
  -B5CheckpointRoot $B5Checkpoint `
  -VerifiedBackupPath '<receipt.path>' `
  -VerifiedBackupSha256 '<receipt.sha256>'
```

腳本固定執行：

1. 在任何 Compose preflight、service stop 或 DB mutation 前重算 backup SHA，核對 A6／B5
   manifests 與 scheduler flags。
2. 核對 project、images、三個 loopback ports、internal backend network 與 exact DB named
   volume；禁止跨 project 操作。
3. 驗證 active A6 portable identity、instance ImportRun／materialization、serving counts、
   activation audit、state epoch 與 API／Web／scheduler public readiness。
4. 確認 immutable B5 release history 是 exact existing 或尚未建立；未知／殘缺 history 停止。
5. 在 quiesce 前對完整 B5 checkpoint 執行唯讀 pinned-source verification，要求唯一
   `PINNED_ROLLBACK_SOURCE_OK`，且 origin sequence／epoch 不得改變。
6. Quiesce Web、API、Scheduler，才以 current A6 importer activation B5；必須新增精確一筆
   `ROLLBACK`。Schema 維持 V0007，migration commands 必須為 0。
7. 以相同 A6 images 重新啟動 intermediate services，實際驗證 API／Web／scheduler 正在
   服務 B5 revision、Gacha 5／4 與 Shadow flags；隨後一定再次 quiesce intermediate services。
8. 恢復 A6：若 B5 activation 尚未 commit，只接受 exact `ORIGIN_NOOP`；若 B5 已 active，
   只接受 exact `B5_REACTIVATE` 與 ROLLBACK→REACTIVATE chronology。
9. 驗證 A6 portable／instance identity、ACL、API／Web／scheduler readiness 與 final epoch，
   全部成立才恢復服務。

成功至少出現：

```text
VERIFIED_BACKUP_INPUT_OK
A6_B5_MANIFEST_INPUTS_OK
A6_COMPOSE_PREFLIGHT_OK
A6_DB_TARGET_OK
A6_ORIGIN_VERIFIED_OK
B5_CHECKPOINT_PREFLIGHT_OK
A6_B5_DATA_ROLLBACK_OK
A6_B5_SAME_SCHEMA_ROLLBACK_OK alembic=v0007_gacha_timeline_slice migration_commands=0
B5_INTERMEDIATE_SERVICES_READY_OK
B5_INTERMEDIATE_SERVICES_STOPPED_OK
A6_RECOVERY_MODE_OK
A6_RESTORED_OK
A6_SERVICES_READY_OK
A6_B5_ROLLBACK_DRILL_OK
```

本次正常 chronology：

```text
seq=1  IMPORT      null → A6  epoch=1150
seq=2  ROLLBACK    A6 → B5    epoch=2325
seq=3  REACTIVATE  B5 → A6    epoch=3062
```

具體 sequence、epoch、ImportRun 與 materialization 僅屬本次 instance；其他環境必須從自身
DB 取得 exact origin，不能把這些數字硬編碼成 release Gate。

## 失敗與復原邊界

- B5 activation commit 前失敗：DB 必須仍為 exact origin A6，sequence／epoch 完全不變；只接受
  `ORIGIN_NOOP`，不能強迫產生兩筆 recovery activations。
- B5 已 active 後失敗：只接受 exact B5 rollback state，再 re-activate 原 A6 ImportRun，驗證
  `ROLLBACK → REACTIVATE` chronology 與原 typed materialization。
- Intermediate B5 services 若曾啟動，`finally` 必須再次停止它們，才可進入 A6 recovery。
- 任何其他 active revision、Alembic、history、port、volume、ACL、serving count 或 readiness
  都 fail closed，不得人工改 flag 或放寬 assertion。
- 若 A6 restoration 無法證明，輸出 `SERVICES_LEFT_QUIESCED`，保存 logs，使用 verified backup
  在全新 disposable target 復原；不得強制開流量。
- 腳本沒有 `LeaveAtB5`。永久回退 B5 必須另立 change window、B5 release images／routing
  計畫與獨立演練，不能把 round-trip drill 當 cutover。
- 不得刪除或覆寫 A6／B5 manifests，不得移動任何既有 tag。

## Release checklist

- Research wrapper 只有 Gate A／B／C 三個 ARTIFACT_READY FAIL；Mutation 122 ALL_OK。
- Full Python 封版重跑、API 81、Importer 115、operations、contract 28、typecheck／build、
  mock＋real E2E 全綠。
- Fresh V0007／v4／23 tables；A6 source identity與 47 header 24／0 精確。
- `DB_PRIVILEGES_OK matrix_checks=651 actual_denials=23 allowed_smokes=10`。
- Scheduler disabled、Shadow true、auto-publish false。
- Verified backup receipt 可讀，SHA／bytes 重新計算相同，restore cleanup 完成。
- B5 checkpoint preflight、intermediate services 與 A6 final readiness 實際通過。
- Revision-history smoke／verify 只能在 drill 後串行執行；最後才跑 real E2E。
- 私人 GitHub Actions 全綠後才建立新的 annotated `rp-a6-0` tag；既有 `rp-b5-1` 與其他
  tags 不移動。
- Data A／B／C 與 Gates D–G 仍依正式定義評估，不因本演練自動 PASS。
