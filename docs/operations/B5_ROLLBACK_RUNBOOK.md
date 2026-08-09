# RP-B5-1 backup／restore 與 B5→A5→B5 回滾手冊

日期：2026-08-10（Asia/Taipei）

本手冊只適用於 RP-B5-1 的 V0007／materialization v4 候選與 immutable RP-A5
`rp-a5-2` checkpoint。它不是一般性的 `docker compose down` 指南，也不能用 checkout 舊
tag 取代 data／schema 回滾。

## Portable source identities

```text
RP-B5-1 manifest  e74814d6433ee327611f10322937bdfa9687b9887f139ba6e6158a291dd12989
RP-B5-1 raw       d117be193802d459102708424c4b7f2a7e852b793ff38356e1977f44d507466d
RP-B5-1 semantic  a7467a838c2a9cfdfe48bda4a3b158fb374dd023caa3478a84c07678532ea9f4
RP-A5 manifest    1826c8493d40f71a6d0bb9096f57b92fe4e839d52bddf021b0c51e0186dcbda7
RP-A5 raw         1962881faf1d84057efdcccb6e22c28de32ea4c47f5acbf57a5d48adc631555c
RP-A5 semantic    c77bc9893fa0b442832c1dff0c7c4a1c5e6d63ba9bce27c1c2f8078c5c2511b8
```

RP-B5-1 的 portable structure 是 48 files／13 CSV／376 rows，Evidence→Claim 120、
Claim→Evidence 298。`artifact_mirror_sha256`、typed `materialization_sha256`、import run、
activation sequence 與 epoch 都是重算值或 instance state，不得拿來取代上述 portable pins。

## 不可省略的前置條件

- 在 repo root 執行；PowerShell 7、Docker Compose v2、Git tag `rp-a5-2` 可用。
- 使用 Git 忽略的 env file；不得將密碼、dump 或 receipt commit。
- Compose project 不得使用 `pcr-tw-a5-arena`、`pcr-tw-a4-water`、`pcr-tw-b1`。
- B5 API／scheduler images、API／Web／scheduler ports 必須由操作員明確傳入；腳本在第一個
  DB mutation／stop 前核對 resolved config、實際 container label、named volume 與 loopback
  binding。
- Scheduler 必須 `SCHEDULER_ENABLED=false`、`SHADOW_MODE=true`、`AUTO_PUBLISH=false`。
- 先取得並驗證 backup receipt；沒有 backup SHA／path 不得開始 data rollback。

本機候選使用：

```text
project=pcr-tw-b5-gacha
api_image=pcr-tw-platform-api:b5
scheduler_image=pcr-tw-platform-scheduler:b5
api_port=8400 web_port=3400 scheduler_port=8481
```

## 1. 先做 backup／restore smoke

```powershell
.\scripts\backup_restore_smoke.ps1 `
  -EnvFile (Resolve-Path .env.b5.local) `
  -ProjectName pcr-tw-b5-gacha `
  -ExpectedApiImage pcr-tw-platform-api:b5 `
  -ExpectedSchedulerImage pcr-tw-platform-scheduler:b5 `
  -ExpectedApiPort 8400 `
  -ExpectedWebPort 3400 `
  -ExpectedSchedulerPort 8481 `
  -KeepBackup
```

Fresh seq=1 stack 不使用 `-SeedRevisionHistory`。成功必須同時出現：

```text
B5_COMPOSE_PREFLIGHT_OK
B5_DB_TARGET_OK
BACKUP_ARTIFACT_VERIFIED
RESTORED_HISTORY_DIGEST_OK
RESTORED_ROUND_TRIP_OK
RESTORED_API_READINESS_OK
RESTORED_WEB_EVIDENCE_OK
GACHA_DOWNGRADE_BLOCKED_OK
BACKUP_RESTORE_OK
{"status":"BACKUP_RESTORE_VERIFIED",...}
```

最後一行 JSON 是唯一可交給 rollback drill 的 receipt。逐欄保存 `path`、`sha256`、`bytes`、
source revision／import run／materialization／epoch；另外獨立重算：

```powershell
Get-Item -LiteralPath '<receipt.path>' | Select-Object FullName,Length
Get-FileHash -LiteralPath '<receipt.path>' -Algorithm SHA256
```

`-KeepBackup` 只保留成功 receipt 指向的 dump。失敗或沒有 verified receipt 的檔案不得作為
release rollback source。

## 2. 從 immutable tag 建立 RP-A5 checkpoint

不要複製目前 working tree，也不要手改 A5 core。使用全新、Git 忽略的目錄：

```powershell
git rev-parse --verify 'refs/tags/rp-a5-2^{}'

$checkpointRoot = Join-Path $PWD '.runtime/rp-a5-2-checkpoint'
$checkpointArchive = Join-Path $PWD '.runtime/rp-a5-2-checkpoint.tar'
if ((Test-Path -LiteralPath $checkpointRoot) -or (Test-Path -LiteralPath $checkpointArchive)) {
  throw 'RP-A5 checkpoint target already exists'
}
New-Item -ItemType Directory -Path $checkpointRoot | Out-Null
git archive --format=tar --output=$checkpointArchive rp-a5-2
tar -xf $checkpointArchive -C $checkpointRoot
```

確認 checkpoint 中存在：

```text
research_core/pcr_tw_project/
scripts/research_core_rp_a5_manifest.sha256
```

Rollback script 會自行重算 A5 manifest／raw／semantic／artifact structure；任一不符即停止。

## 3. 執行 B5→A5→B5 演練

```powershell
.\scripts\b5_a5_rollback_drill.ps1 `
  -EnvFile (Resolve-Path .env.b5.local) `
  -ProjectName pcr-tw-b5-gacha `
  -ExpectedApiImage pcr-tw-platform-api:b5 `
  -ExpectedSchedulerImage pcr-tw-platform-scheduler:b5 `
  -ExpectedApiPort 8400 `
  -ExpectedWebPort 3400 `
  -ExpectedSchedulerPort 8481 `
  -A5CheckpointRoot (Resolve-Path .runtime\rp-a5-2-checkpoint) `
  -VerifiedBackupPath '<receipt.path>' `
  -VerifiedBackupSha256 '<receipt.sha256>'
```

腳本固定執行：

1. 重算 backup SHA、核對 B5 project／images／ports／DB volume。
2. 驗證目前 active B5 portable identity、instance materialization、serving counts、activation
   audit、state epoch 與 API／Web／scheduler readiness，再 quiesce services。
3. 以 current B5 binary 匯入 pinned A5 v3；必須得到 `ROLLBACK` activation，並證明五張
   Gacha 表為 0。
4. 執行 V0007→V0006；只有完整 A5 v3 ownership closure 可通過。
5. 執行 V0006→V0007、重新 provision roles、re-activate 原 B5 revision。
6. 驗證 B5 原 import run／materialization、完整 chronology、651 格 ACL、public readiness，
   才重啟所有服務並輸出成功 marker。

成功必須出現：

```text
VERIFIED_BACKUP_INPUT_OK
B5_COMPOSE_PREFLIGHT_OK
B5_DB_TARGET_OK
B5_ORIGIN_VERIFIED_OK
A5_DATA_ROLLBACK_OK
B5_A5_SCHEMA_ROLLBACK_OK
B5_RECOVERY_MODE_OK
B5_RESTORED_OK
B5_PUBLIC_READINESS_OK
B5_SERVICES_READY_OK
B5_A5_ROLLBACK_DRILL_OK
```

正常 fresh chronology 必須是：

```text
S0    IMPORT/REACTIVATE  -> B5
S0+1  ROLLBACK           B5 -> A5
S0+2  REACTIVATE         A5 -> B5
```

各 activation epoch 嚴格遞增；final materialization state epoch 等於最後一筆 activation
epoch。具體 sequence／epoch／materialization 只屬該 instance，實測值記在
`B5_1_VERIFICATION_REPORT.md`，不硬寫成 portable gate。

## 失敗與復原邊界

- 在 A5 activation 前失敗：DB 必須仍是 exact origin B5；允許 idempotent no-op recovery，
  但 origin identity／sequence／epoch 必須完全一致。
- A5 已 activation 後失敗：finally 必須以原 B5 revision re-activate，驗證完整
  ROLLBACK→REACTIVATE chronology 與原 materialization，再重啟服務。
- 若 B5 identity、backup、actual port、A5 pins、migration ownership、ACL 或 readiness
  任何一項無法證明，不得人工改 flag 或放寬 assertion。保留 services quiesced、保存 logs，
  由 verified backup 在新的 disposable target 中復原。
- 本腳本沒有 `LeaveAtA5`。若產品決定永久回退 A5，應另立變更窗口、release image／routing
  計畫與獨立演練，不能把這個 round-trip drill 當永久 cutover。
- 不得刪除或覆寫 RP-B5-1／RP-A5 manifests，不得移動既有 tags。

## Release checklist

- Research wrapper：只有 Gate A／B／C 三個 ARTIFACT_READY FAIL；Mutation ALL_OK。
- Full Python、OpenAPI/client parity、typecheck、build、mock＋real E2E 全綠。
- Fresh V0007 import counts 與 Gacha 5／10／8／4／0 精確。
- `DB_PRIVILEGES_OK matrix_checks=651 actual_denials=23 allowed_smokes=10`。
- Verified backup receipt 可讀且 SHA／bytes 重算相同。
- B5→A5→B5 成功、服務回到 B5、Gacha events=5。
- 私人 GitHub Actions 全綠後才建立新的 annotated `rp-b5-1` tag；不移動舊 tag。
- Data A／B／C 與 Gates D–G 仍依其正式定義評估，不因本演練自動 PASS。
