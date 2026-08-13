# 私人本機資料定期更新 Runbook

- 適用範圍：私人 PVE XLSX、角色頭像人工覆核／mapped catalog，以及私人 Gacha
  DOCX candidate。
- 執行環境：Windows PowerShell 7，由目前 checkout 的 repository root 執行。
- 原始來源與 `.runtime` 衍生資料只在本機使用；更新週期不會 commit、push、開 PR、建 tag
  或建立排程。程式碼與本手冊本身仍依 repository 的一般審查流程版本化。
- 本手冊不授權修改原始 XLSX／DOCX、不重新判斷隊伍能否通關，也不授權把私人資料寫入
  canonical research core。

本流程採「來源快照 -> 全新 candidate -> 離線驗證 -> 短暫停機切換」；在切換前，現行
`.runtime/private_pve` 與 `.runtime/gacha_forecast` 不會被改動。任何守門失敗均停在
candidate，不用修改現行資料來取得綠燈。

## 1. 不可變條件與角色分工

1. 原始檔永遠唯讀；同一更新週期開始與結束時，長度及 SHA-256 必須一致。
2. `research_core/pcr_tw_project/**` 在整個週期內必須 byte-for-byte 不變。
3. PVE 隊伍仍標示 `SOURCE_PROVIDED`／未獨立驗證通關；`O=SET`、`X=不SET`，且操作軸
   不得推定綁定五位角色。
4. 頭像只有在 exact unit variant、台服正式名稱、EsterTion exact base、素材存在及台服
   六星證據全部閉合時才能使用外部圖。`PENDING`、`REVIEWED_UNKNOWN`、`UNRESOLVED` 或
   任一證據缺漏一律顯示 exact Excel 內嵌頭像。
5. Gacha DOCX 永遠是 `GACHA-COMM-002` 的私人社群預測；所有 candidate 必須
   `PENDING`、`promotion_eligible=false`、`canonical_write_count=0`。
6. Maintainer 負責來源／runtime inventory、備份、驗證、切換及回復；角色身分與六星判定
   必須交由人工內容覆核。若新 catalog 讓 review registry 失去雜湊閉合，Maintainer 不得
   只改 `base_catalog_sha256` 來繞過守門。

設計依據：`ADR-0008-private-pve-xlsx-ingestion.md`、
`ADR-0009-private-gacha-docx-ingestion.md` 及
`PRIVATE_PVE_DEVELOPMENT_PLAN.md`。

## 2. Operational inventory

| 類型 | 唯讀來源／輸入 | 衍生 candidate | 現行 serving closure | 失敗如何被看見 | 回復路徑 |
|---|---|---|---|---|---|
| PVE workbook 1 | `Downloads/深域關卡備戰所有屬性1~7.xlsx` | `workbook-1.catalog.json` | `.runtime/private_pve/mapped/catalog.json` | importer non-zero、summary/runtime schema 不符 | 保留 candidate；現行 runtime 不動 |
| PVE workbook 2 | `Downloads/深域關卡8~10&追憶&露娜塔.xlsx` | `workbook-2.catalog.json` | 同上 | 同上 | 同上 |
| PVE 圖片 | 兩份 XLSX 的 exact embedded bytes | candidate `assets/` | `.runtime/private_pve/assets/` | asset 數量、長度或 digest 不符即 API 503 | 還原整組 catalog + assets |
| 人工頭像判定 | `review/portrait-overrides.json`、EsterTion index、`review/evidence/` | mapping、mapped catalog、materialization manifest | `.runtime/private_pve/mapped/` | registry/base hash、exact variant、證據或 material hash 不閉合 | 回到 Excel 圖；不可猜角色 |
| Gacha | `Downloads/卡池未來視.docx` | `docx-candidates.json` + content-addressed DOCX | `.runtime/gacha_forecast/` | deterministic replay、DOCX 安全檢查或 source hash 不符即 API 503 | 還原 catalog + 同 hash DOCX |
| Local API/Web | 上述兩個 read-only runtime | 無 DB write | compose base + `infra/private/compose.local-libraries.yml` | structured 503、health、desktop/mobile smoke | 停止 API/Web，整組目錄回復後重啟 |
| Canonical SSOT | `research_core/pcr_tw_project/**` | 不適用 | 既有 DB read mirror／canonical UI | 更新前後全樹 hash manifest 差異 | 立即中止；私人更新不得修寫 canonical |

目前已知 checkpoint（只用於第一次執行的 sanity check，不得硬編碼成未來上限）：

- 來源：workbook 1 `9a53ab1af4b1333d7e846e38fd84e89b35b08f6ece01f374b7db2eecae71a5f0`；
  workbook 2 `e09b3c6c4d6a6c240e40a68aa724122bfdc7ad409521c011f25db0f3e7887789`；
  Gacha DOCX `0600faf911747c6df1a98afddfe1fe8e5af585ff72af11e2d34299f5e70c4cfe`。
- PVE：2 workbooks、26 sheets、653 sections、4,291 teams、4,448 axes、647 assets；
  base catalog SHA-256 `20764c142b1798f8629155a2562bdffbed624722c2bbf87970eb530a7602f5e7`；
  mapped catalog SHA-256 `78017de65c86fc8455ac6f0f4d979fa9bb503eae6b6e230bd2d0a99fe22ef540`。
- 頭像：582 `RESOLVED`、37 `REVIEWED_UNKNOWN`；未確認者均為 workbook fallback。
- Gacha：17 pools、39 raw names、17 images、0 canonical writes；candidate SHA-256
  `beb41b049f995c5894219e78a883f23430f782b47699b0d4e8fdd234aefed79c`。
- Canonical Gacha 必須維持 5 events、4 community sources、0 contributing relations。

## 3. 每次更新的 preflight 與可回復快照

由 repository root 執行。先設定本次實際收到的三個來源；只更新其中一類時，另一類仍做
hash guard，但不要替換它的 runtime。

```powershell
$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path -LiteralPath ((git rev-parse --show-toplevel).Trim())).Path
$RequiredRepoPaths = @('pyproject.toml', 'apps', 'data_pipeline', 'research_core')
foreach ($relativePath in $RequiredRepoPaths) {
  if (-not (Test-Path -LiteralPath (Join-Path $Repo $relativePath))) {
    throw "Repository marker is missing: $relativePath"
  }
}
Set-Location -LiteralPath $Repo

$Downloads = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads'
$PveWorkbook1 = Join-Path $Downloads '深域關卡備戰所有屬性1~7.xlsx'
$PveWorkbook2 = Join-Path $Downloads '深域關卡8~10&追憶&露娜塔.xlsx'
$GachaDocx = Join-Path $Downloads '卡池未來視.docx'
$LivePve = Join-Path $Repo '.runtime\private_pve'
$LiveGacha = Join-Path $Repo '.runtime\gacha_forecast'
$RefreshPve = $true       # 本週期不更新 PVE 時改為 $false
$RefreshGacha = $false   # 本週期更新 Gacha 時改為 $true
if (-not ($RefreshPve -or $RefreshGacha)) { throw 'Select at least one refresh type' }

function Assert-NoReparsePoint([string] $Path) {
  $root = Get-Item -LiteralPath $Path -Force
  $items = @($root) + @(Get-ChildItem -LiteralPath $root.FullName -Force -Recurse)
  $reparse = @($items | Where-Object {
    ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
  })
  if ($reparse.Count -gt 0) {
    $reparse | Select-Object FullName,Attributes | Format-Table
    throw "Reparse point is not allowed in refresh input: $Path"
  }
}

foreach ($source in @($PveWorkbook1, $PveWorkbook2, $GachaDocx)) {
  if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing source: $source" }
  Assert-NoReparsePoint $source
}
foreach ($runtime in @($LivePve, $LiveGacha)) {
  if (-not (Test-Path -LiteralPath $runtime -PathType Container)) {
    throw "Missing live runtime: $runtime"
  }
  Assert-NoReparsePoint $runtime
}

$Branch = (git branch --show-current).Trim()
if ($Branch -ne 'local/pve-private-xlsx-ingest') { throw "Unexpected branch: $Branch" }
$CycleId = Get-Date -Format 'yyyyMMdd-HHmmss'
$CycleRoot = Join-Path $Repo ".runtime\private_refresh\$CycleId"
$AllowedCycleRoot = Join-Path $Repo '.runtime\private_refresh'
if (-not $CycleRoot.StartsWith($AllowedCycleRoot, [StringComparison]::OrdinalIgnoreCase)) {
  throw 'Unsafe cycle path'
}

# Conservative capacity gate: four copies of both live runtimes covers rollback,
# candidate, replay/audit and one safety copy; two source copies cover snapshot/replay.
$LiveBytes = [int64](Get-ChildItem -LiteralPath $LivePve,$LiveGacha -File -Recurse |
  Measure-Object -Property Length -Sum).Sum
$SourceBytes = [int64](Get-Item -LiteralPath $PveWorkbook1,$PveWorkbook2,$GachaDocx |
  Measure-Object -Property Length -Sum).Sum
$RequiredFreeBytes = [int64](4 * $LiveBytes + 2 * $SourceBytes)
$CycleDrive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($CycleRoot))
if (-not $CycleDrive.IsReady -or $CycleDrive.AvailableFreeSpace -lt $RequiredFreeBytes) {
  throw "Insufficient free space: need $RequiredFreeBytes bytes, have $($CycleDrive.AvailableFreeSpace)"
}
New-Item -ItemType Directory -Path $CycleRoot | Out-Null

function Get-TreeManifest([string] $Root) {
  $resolved = (Resolve-Path -LiteralPath $Root).Path
  @(Get-ChildItem -LiteralPath $resolved -File -Recurse | Sort-Object FullName | ForEach-Object {
    [pscustomobject]@{
      path = $_.FullName.Substring($resolved.Length + 1).Replace('\', '/')
      bytes = $_.Length
      sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    }
  })
}

function Assert-SameManifest([string] $BeforeFile, [string] $Root) {
  $before = @(Get-Content -LiteralPath $BeforeFile -Raw | ConvertFrom-Json)
  $after = @(Get-TreeManifest $Root)
  $delta = Compare-Object -ReferenceObject $before -DifferenceObject $after `
    -Property path,bytes,sha256
  if ($delta) { $delta | Format-Table; throw "Manifest drift: $Root" }
}

$GuardDir = New-Item -ItemType Directory -Path (Join-Path $CycleRoot 'guards')
$SourceDir = New-Item -ItemType Directory -Path (Join-Path $CycleRoot 'source')
$RollbackDir = New-Item -ItemType Directory -Path (Join-Path $CycleRoot 'rollback')

git status --short | Set-Content -LiteralPath (Join-Path $GuardDir 'git-status-before.txt') -Encoding utf8NoBOM
git remote -v | Set-Content -LiteralPath (Join-Path $GuardDir 'git-remotes-before.txt') -Encoding utf8NoBOM
[pscustomobject]@{ branch=$Branch; head=(git rev-parse HEAD).Trim() } |
  ConvertTo-Json | Set-Content -LiteralPath (Join-Path $GuardDir 'git-before.json') -Encoding utf8NoBOM

Get-TreeManifest (Join-Path $Repo 'research_core\pcr_tw_project') |
  ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $GuardDir 'canonical-before.json') -Encoding utf8NoBOM

$sourceRows = @($PveWorkbook1, $PveWorkbook2, $GachaDocx) | ForEach-Object {
  $item = Get-Item -LiteralPath $_
  [pscustomobject]@{
    path=$item.FullName; bytes=$item.Length
    sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $item.FullName).Hash.ToLowerInvariant()
  }
}
$sourceRows | ConvertTo-Json -Depth 4 |
  Set-Content -LiteralPath (Join-Path $GuardDir 'sources-before.json') -Encoding utf8NoBOM

# Exact source snapshots; parsers read these copies, never rewrite Downloads.
$PveSourceDir = New-Item -ItemType Directory -Path (Join-Path $SourceDir 'pve')
Copy-Item -LiteralPath $PveWorkbook1 -Destination $PveSourceDir
Copy-Item -LiteralPath $PveWorkbook2 -Destination $PveSourceDir
$PveSnapshot1 = Join-Path $PveSourceDir (Split-Path -Leaf $PveWorkbook1)
$PveSnapshot2 = Join-Path $PveSourceDir (Split-Path -Leaf $PveWorkbook2)

# A verified recovery copy exists before any cutover.
Copy-Item -LiteralPath $LivePve -Destination $RollbackDir -Recurse
Copy-Item -LiteralPath $LiveGacha -Destination $RollbackDir -Recurse
Copy-Item -LiteralPath (Join-Path $Repo 'infra\private\compose.local-libraries.yml') -Destination $RollbackDir

$pveBackupDelta = Compare-Object @(Get-TreeManifest $LivePve) `
  @(Get-TreeManifest (Join-Path $RollbackDir 'private_pve')) -Property path,bytes,sha256
$gachaBackupDelta = Compare-Object @(Get-TreeManifest $LiveGacha) `
  @(Get-TreeManifest (Join-Path $RollbackDir 'gacha_forecast')) -Property path,bytes,sha256
if ($pveBackupDelta -or $gachaBackupDelta) { throw 'Recovery snapshot verification failed' }

$env:PYTHONPATH = 'apps/api;data_pipeline;database;apps/scheduler/src'
```

Preflight 停止條件：branch 不符、來源不存在、來源或 runtime 是 symlink/reparse point、快照
manifest 不一致、空間不足以同時容納 current + rollback + candidate，或 dirty worktree 中已有
與本週期要改的 overlay 重疊且無法辨識。既有 dirty changes 本身不是失敗，不得 reset。

## 4. PVE XLSX candidate 更新

### 4.1 確定性抽取、media export 與 merge

```powershell
$CandidatePve = Join-Path $CycleRoot 'candidate\private_pve'
$CandidateAssets = Join-Path $CandidatePve 'assets'
$CandidateMapped = Join-Path $CandidatePve 'mapped'
$CandidateAudit = Join-Path $CycleRoot 'audit\pve'
New-Item -ItemType Directory -Path $CandidatePve,$CandidateAssets,$CandidateMapped,$CandidateAudit | Out-Null

python -m pcr_pipeline.private_pve.cli extract `
  --input $PveSnapshot1 --output (Join-Path $CandidatePve 'workbook-1.catalog.json')
python -m pcr_pipeline.private_pve.cli extract-workbook-2 `
  --input $PveSnapshot2 --output (Join-Path $CandidatePve 'workbook-2.catalog.json')

# 第二次抽取寫到 audit 位置；兩次輸出必須 byte-identical。
python -m pcr_pipeline.private_pve.cli extract `
  --input $PveSnapshot1 --output (Join-Path $CandidateAudit 'workbook-1.replay.json')
python -m pcr_pipeline.private_pve.cli extract-workbook-2 `
  --input $PveSnapshot2 --output (Join-Path $CandidateAudit 'workbook-2.replay.json')
foreach ($name in @('workbook-1','workbook-2')) {
  $a = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $CandidatePve "$name.catalog.json")).Hash
  $b = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $CandidateAudit "$name.replay.json")).Hash
  if ($a -ne $b) { throw "Non-deterministic extraction: $name" }
}

python -m pcr_pipeline.private_pve.cli export-media `
  --input $PveSnapshot1 --catalog (Join-Path $CandidatePve 'workbook-1.catalog.json') `
  --output-dir $CandidateAssets
python -m pcr_pipeline.private_pve.cli export-media `
  --input $PveSnapshot2 --catalog (Join-Path $CandidatePve 'workbook-2.catalog.json') `
  --output-dir $CandidateAssets
python -m pcr_pipeline.private_pve.cli merge-catalogs `
  --input (Join-Path $CandidatePve 'workbook-1.catalog.json') `
  --input (Join-Path $CandidatePve 'workbook-2.catalog.json') `
  --output (Join-Path $CandidatePve 'catalog.json')

$OldPveSummary = (Get-Content -LiteralPath (Join-Path $LivePve 'catalog.json') -Raw |
  ConvertFrom-Json -Depth 100).summary
$NewPveSummary = (Get-Content -LiteralPath (Join-Path $CandidatePve 'catalog.json') -Raw |
  ConvertFrom-Json -Depth 100).summary
[pscustomobject]@{ old=$OldPveSummary; candidate=$NewPveSummary } |
  ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $CandidateAudit 'summary-delta.json') -Encoding utf8NoBOM
$NewPveSummary | Format-List
if ($NewPveSummary.source_workbook_count -ne 2) { throw 'PVE must close over exactly two workbooks' }
```

任何 count 下降、模式／屬性／區域消失、diagnostic 增加或 team/axis 比例異常，都先對照新
XLSX 的可見資料。數字改變可以是合法更新，但不能只因「預期會增加」而略過說明。

### 4.2 頭像覆核守門

先建立不含 override 的完整 queue，確認本次 formation asset universe：

```powershell
# 保留舊人工證據作為參考；這只是 candidate copy，不會改 live registry。
Copy-Item -LiteralPath (Join-Path $LivePve 'review') -Destination $CandidatePve -Recurse
$CandidateReview = Join-Path $CandidatePve 'review'
python -m pcr_pipeline.private_pve.cli build-review-queue `
  --catalog (Join-Path $CandidatePve 'catalog.json') `
  --output (Join-Path $CandidateAudit 'portrait-review-queue.unreviewed.json')

$NewBaseSha = (Get-FileHash -Algorithm SHA256 -LiteralPath `
  (Join-Path $CandidatePve 'catalog.json')).Hash.ToLowerInvariant()
$OldRegistry = Get-Content -LiteralPath (Join-Path $LivePve 'review\portrait-overrides.json') -Raw |
  ConvertFrom-Json -Depth 100
"candidate base catalog: $NewBaseSha"
"old registry base:      $($OldRegistry.base_catalog_sha256)"
```

- 若兩者相同，可重用 exact 舊 registry；仍要重新執行下方 strict validation。
- 若不同，**停止自動流程並交給人工覆核**。同 SHA-256 portrait 的舊決定可作為參考，但
  registry 必須明確綁定新 base catalog；新增／變更的 portrait 在未確認前不得取得 unit。
- 人工可把未確認項目留為沒有 override 的 `PENDING`，或明確標為
  `REVIEWED_UNKNOWN`；兩者都必須 materialize 成 workbook fallback。不得為追求「0 pending」
  猜測名稱或 unit variant。
- `CONFIRMED` 與六星只可使用已 pin、SHA-256 閉合且語意 verifier 接受的台服官方證據。
  新公告必須另存 exact snapshot；搜尋 snippet、EsterTion 有圖或日服資訊都不夠。

人工覆核完成後，將新 registry 放在
`$CandidateReview/portrait-overrides.json`，再執行：

```powershell
python -m pcr_pipeline.private_pve.cli build-review-queue `
  --catalog (Join-Path $CandidatePve 'catalog.json') `
  --overrides (Join-Path $CandidateReview 'portrait-overrides.json') `
  --output (Join-Path $CandidateReview 'portrait-review-queue.json')

python -m pcr_pipeline.private_pve.cli materialize-character-catalog `
  --catalog (Join-Path $CandidatePve 'catalog.json') `
  --overrides (Join-Path $CandidateReview 'portrait-overrides.json') `
  --estertion-index (Join-Path $CandidateReview 'estertion-unit-index.html') `
  --evidence-dir (Join-Path $CandidateReview 'evidence') `
  --output (Join-Path $CandidateMapped 'catalog.json') `
  --mapping-output (Join-Path $CandidateMapped 'character-mapping.json') `
  --manifest-output (Join-Path $CandidateMapped 'materialization.json')

$Queue = Get-Content -LiteralPath (Join-Path $CandidateReview 'portrait-review-queue.json') -Raw |
  ConvertFrom-Json -Depth 100
$Mapping = Get-Content -LiteralPath (Join-Path $CandidateMapped 'character-mapping.json') -Raw |
  ConvertFrom-Json -Depth 100
$Queue.summary | Format-List
$Mapping.summary | Format-List

# Full real-candidate load validates schema, counts, every asset byte and every member reference.
python -c "from pathlib import Path; from pcr_api.private_pve.runtime import PveLibraryRuntime; s=PveLibraryRuntime(Path(r'$CandidateMapped\catalog.json'),Path(r'$CandidateAssets')).snapshot(); print({'dataset_sha256':s.dataset_sha256,'stages':len(s.stages),'assets':len(s.assets_by_sha256)})"
```

人工覆核接受條件：所有非 `RESOLVED` mapping 的 `display_source` 皆為
`WORKBOOK_EMBEDDED`；所有 `SIX_STAR` icon id 與 exact base 一致且以 `61` 結尾；materialization
manifest 的 input/output SHA 必須等於實際檔案。任何一項不符，candidate 不可切換。

## 5. Gacha DOCX candidate 更新

Gacha 可獨立於 PVE 更新。DOCX 必須以自己的 SHA-256 作為 runtime filename；新 hash 不能
覆寫舊 hash 檔。

```powershell
$CandidateGacha = Join-Path $CycleRoot 'candidate\gacha_forecast'
$CandidateGachaSource = Join-Path $CandidateGacha 'source'
$GachaAudit = Join-Path $CycleRoot 'audit\gacha'
New-Item -ItemType Directory -Path $CandidateGacha,$CandidateGachaSource,$GachaAudit | Out-Null

$NewGachaSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $GachaDocx).Hash.ToLowerInvariant()
$GachaSnapshot = Join-Path $CandidateGachaSource "$NewGachaSha.docx"
Copy-Item -LiteralPath $GachaDocx -Destination $GachaSnapshot
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $GachaSnapshot).Hash.ToLowerInvariant() -ne $NewGachaSha) {
  throw 'Gacha source snapshot mismatch'
}

python -m pcr_pipeline.private_gacha.cli `
  --input $GachaSnapshot --source-id GACHA-COMM-002 `
  --output (Join-Path $CandidateGacha 'docx-candidates.json')
python -m pcr_pipeline.private_gacha.cli `
  --input $GachaSnapshot --source-id GACHA-COMM-002 `
  --output (Join-Path $GachaAudit 'docx-candidates.replay.json')
$first = (Get-FileHash -Algorithm SHA256 -LiteralPath `
  (Join-Path $CandidateGacha 'docx-candidates.json')).Hash
$replay = (Get-FileHash -Algorithm SHA256 -LiteralPath `
  (Join-Path $GachaAudit 'docx-candidates.replay.json')).Hash
if ($first -ne $replay) { throw 'Non-deterministic Gacha extraction' }

python -c "from pathlib import Path; from pcr_api.private_gacha.runtime import GachaLibraryRuntime; s=GachaLibraryRuntime(Path(r'$CandidateGacha\docx-candidates.json'),Path(r'$GachaSnapshot')).snapshot(); assert s.source['source_id']=='GACHA-COMM-002'; assert all(x['review_status']=='PENDING' and x['promotion_eligible'] is False and x['proposed_event_id'] is None for x in s.candidates); print({'dataset_sha256':s.dataset_sha256,'forecasts':len(s.candidates),'assets':len(s.assets_by_sha256)})"
```

更新 DOCX 後，17／39 等舊數字可以合法變動；但 raw names 不得被自動校正，圖片上的日服
日期不得 OCR 成台服日期，且 `canonical_write_count` 必須仍為 0。若 parser warning 增加，
必須保留在 UI 並列入人工覆核，不得為消除 warning 修改原文。

因 `infra/private/compose.local-libraries.yml` 目前 pin 住 content-addressed filename，只有 Gacha hash
變更時才調整該檔的一處 `PCR_GACHA_LIBRARY_DOCX_PATH`。先保存的 rollback copy 是回復依據；
overlay 即使尚未被 Git 追蹤，也要由 rollback 原始 bytes 推導 expected replacement，並確認
實際寫入 bytes 完全相等；因此不依賴 `git diff` 判定變更範圍。

## 6. 切換前共同驗證

```powershell
python -m pytest `
  tests/importer/private_pve/test_private_pve_xlsx_ingest.py `
  tests/importer/private_pve/test_private_pve_xlsx_workbook_2.py `
  tests/importer/private_pve/test_private_pve_catalog.py `
  tests/importer/private_pve/test_private_pve_character_mapping.py `
  tests/importer/private_pve/test_private_pve_portrait_review.py `
  tests/importer/private_gacha/test_gacha_docx_ingest.py `
  tests/api/private_pve/test_library_api.py `
  tests/api/private_gacha/test_library_api.py
npm run typecheck --workspaces --if-present
npm run check:contract
npx playwright test tests/e2e/private-libraries/pve-library.spec.ts tests/e2e/private-libraries/gacha-library.spec.ts
git diff --check
```

E2E 中有目前真實資料的 golden assertions。合法資料更新若讓舊 golden 失敗，交給 Builder
依新來源更新測試；不得刪除以下不變 assertions：五位頭像、O/X 原文、未驗證標籤、
reviewed-unknown fallback、三種 PVE 頁面分離、Deep Zone 選單只顯示實際開放區域／關卡、
Gacha 非官方標籤，以及 canonical timeline 仍獨立存在。後端可容納未來新增區域，但 UI
選項必須從當前 dataset facets 產生，不顯示尚無資料的預留值。

再執行 no-write guards：

```powershell
Assert-SameManifest (Join-Path $GuardDir 'canonical-before.json') `
  (Join-Path $Repo 'research_core\pcr_tw_project')

$sourceBefore = @(Get-Content -LiteralPath (Join-Path $GuardDir 'sources-before.json') -Raw |
  ConvertFrom-Json)
$sourceAfter = @($PveWorkbook1,$PveWorkbook2,$GachaDocx) | ForEach-Object {
  $item = Get-Item -LiteralPath $_
  [pscustomobject]@{ path=$item.FullName; bytes=$item.Length; sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $_).Hash.ToLowerInvariant() }
}
if (Compare-Object $sourceBefore $sourceAfter -Property path,bytes,sha256) {
  throw 'Original source bytes changed during refresh'
}
if ((Import-Csv 'research_core/pcr_tw_project/41_GACHA_TIMELINE.csv').Count -ne 5) {
  throw 'Canonical Gacha timeline changed'
}
if ((Import-Csv 'research_core/pcr_tw_project/45_GACHA_COMMUNITY_SOURCE_INDEX.csv').Count -ne 4) {
  throw 'Canonical Gacha community index changed'
}
```

## 7. 短暫停機切換

一次只切換已完成全部守門的資料類型。先驗證 overlay，再停止 API/Web；不可在已載入的
process 中直接替換檔案，否則 immutable runtime 會正確進入 `*_LIBRARY_DRIFT` 503。

```powershell
# Gacha refresh 才更新一個 content-addressed compose path；0 或 >1 match 都停止。
if ($RefreshGacha) {
  $Overlay = Join-Path $Repo 'infra\private\compose.local-libraries.yml'
  $OverlayBaseline = Join-Path $RollbackDir 'compose.local-libraries.yml'
  $utf8 = [Text.UTF8Encoding]::new($false, $true)
  $baselineBytes = [IO.File]::ReadAllBytes($OverlayBaseline)
  $preEditBytes = [IO.File]::ReadAllBytes($Overlay)
  if ($baselineBytes.Length -ne $preEditBytes.Length -or
      [Convert]::ToBase64String($baselineBytes) -cne [Convert]::ToBase64String($preEditBytes)) {
    throw 'Compose overlay drifted after its rollback snapshot was captured'
  }

  $baselineText = $utf8.GetString($baselineBytes)
  $pattern = '/app/gacha-forecast/source/[0-9a-f]{64}\.docx'
  $pathRegex = [regex]::new($pattern)
  if ($pathRegex.Matches($baselineText).Count -ne 1) {
    throw 'Expected exactly one pinned Gacha DOCX path in compose overlay'
  }
  $replacement = "/app/gacha-forecast/source/$NewGachaSha.docx"
  $expectedText = $pathRegex.Replace($baselineText, $replacement, 1)
  $expectedBytes = $utf8.GetBytes($expectedText)
  [IO.File]::WriteAllBytes($Overlay, $expectedBytes)

  $actualBytes = [IO.File]::ReadAllBytes($Overlay)
  if ($expectedBytes.Length -ne $actualBytes.Length -or
      [Convert]::ToBase64String($expectedBytes) -cne [Convert]::ToBase64String($actualBytes)) {
    throw 'Compose overlay is not the exact one-path replacement derived from rollback bytes'
  }
}

docker compose --env-file .env -f infra/compose.yml -f infra/private/compose.local-libraries.yml config --quiet
docker compose --env-file .env -f infra/compose.yml -f infra/private/compose.local-libraries.yml stop web api

$RetiredDir = New-Item -ItemType Directory -Path (Join-Path $CycleRoot 'retired')
$PveSwitched = $false
$GachaSwitched = $false

# Boolean 只能在該 candidate 完成全部守門後維持 $true。
if ($RefreshPve) {
  Move-Item -LiteralPath $LivePve -Destination $RetiredDir
  Move-Item -LiteralPath $CandidatePve -Destination $LivePve
  $PveSwitched = $true
}

if ($RefreshGacha) {
  Move-Item -LiteralPath $LiveGacha -Destination $RetiredDir
  Move-Item -LiteralPath $CandidateGacha -Destination $LiveGacha
  $GachaSwitched = $true
}

docker compose --env-file .env -f infra/compose.yml -f infra/private/compose.local-libraries.yml up --build --wait api web
```

若第二個 `Move-Item` 失敗，不要繼續啟動；立即把 `$RetiredDir/private_pve` 或
`$RetiredDir/gacha_forecast` 移回原路徑。切換後 smoke：

```powershell
$pve = Invoke-RestMethod 'http://127.0.0.1:8600/api/v1/pve-library/stages'
$gacha = Invoke-RestMethod 'http://127.0.0.1:8600/api/v1/gacha-library/forecasts'
if ($pve.data.total -lt 1 -or $gacha.data.total -lt 1) { throw 'Empty private library' }
if ($gacha.meta.canonical_write_count -ne 0) { throw 'Gacha canonical write guard failed' }

$env:PLAYWRIGHT_BASE_URL = 'http://127.0.0.1:3600'
$env:PLAYWRIGHT_PRIVATE_LIBRARIES_REAL = '1'
try {
  npx playwright test tests/e2e/private-libraries/pve-library.spec.ts tests/e2e/private-libraries/gacha-library.spec.ts `
    --project=desktop-chromium --project=mobile-chromium
} finally {
  Remove-Item Env:PLAYWRIGHT_PRIVATE_LIBRARIES_REAL -ErrorAction SilentlyContinue
  Remove-Item Env:PLAYWRIGHT_BASE_URL -ErrorAction SilentlyContinue
}
```

保留本週期的 `guards/`、`rollback/`、`audit/`、`retired/` 與驗證輸出；不要在同一更新
週期清除。清理舊週期屬於另一次經確認的 retention 工作。

## 8. Failure detection、處置與 rollback

| 訊號 | 判定 | 立即處置 | 永久修正歸屬 |
|---|---|---|---|
| importer non-zero／layout error | 新來源或 parser contract 不相容 | 停在 candidate；保留 stdout/stderr 與來源 hash | Builder；不可 partial import |
| PVE `PVE_LIBRARY_INVALID`／asset mismatch | catalog、asset 或 summary 不閉合 | 不切換；若已切換則 rollback 整組 | Builder／資料覆核 |
| PVE `PVE_LIBRARY_DRIFT` | process 載入後檔案被改 | 停止 API，確認來源後 restart 或 rollback | Maintainer |
| Gacha `GACHA_LIBRARY_INVALID` | replay、OOXML、hash 或 content-addressed name 失敗 | 不切換；不可手改 candidate JSON | Builder／文件提供者 |
| Gacha `GACHA_LIBRARY_DRIFT` | catalog/DOCX 被替換 | 停止 API，整組 rollback | Maintainer |
| external EsterTion 圖載入失敗 | 外部服務可用性問題 | 確認 Excel fallback 正常；不改 unit mapping | Maintainer；持續失敗再交 Builder |
| Excel fallback 亦 404／digest 不符 | 私人 PVE 核心顯示路徑中斷 | rollback；視為高影響資料事故 | Maintainer -> Builder |
| canonical manifest 或來源 hash 漂移 | 越界寫入 | 立即中止，不以私人 candidate 修復 canonical/source | Maintainer，必要時向使用者升級 |
| fixture-specific E2E 失敗 | 可能是合法資料更新，也可能是回歸 | 先分類；不可直接放寬 assertion | Builder |

已切換後的 rollback：

```powershell
docker compose --env-file .env -f infra/compose.yml -f infra/private/compose.local-libraries.yml stop web api
$FailedDir = New-Item -ItemType Directory -Path (Join-Path $CycleRoot ('failed-' + (Get-Date -Format 'yyyyMMdd-HHmmss')))

# 若是另開 PowerShell，先按 cycle log 與 retired/ 內容把這兩個值設成實際切換狀態。
if ($PveSwitched) {
  Move-Item -LiteralPath $LivePve -Destination $FailedDir
  Copy-Item -LiteralPath (Join-Path $RollbackDir 'private_pve') -Destination $LivePve -Recurse
}
if ($GachaSwitched) {
  Move-Item -LiteralPath $LiveGacha -Destination $FailedDir
  Copy-Item -LiteralPath (Join-Path $RollbackDir 'gacha_forecast') -Destination $LiveGacha -Recurse
  Copy-Item -LiteralPath (Join-Path $RollbackDir 'compose.local-libraries.yml') `
    -Destination (Join-Path $Repo 'infra\private\compose.local-libraries.yml') -Force
}

docker compose --env-file .env -f infra/compose.yml -f infra/private/compose.local-libraries.yml config --quiet
docker compose --env-file .env -f infra/compose.yml -f infra/private/compose.local-libraries.yml up --build --wait api web
Invoke-RestMethod 'http://127.0.0.1:8600/api/v1/pve-library/stages' | Out-Null
Invoke-RestMethod 'http://127.0.0.1:8600/api/v1/gacha-library/forecasts' | Out-Null
```

回復成功的證據是舊 dataset SHA、API 200、desktop/mobile 核心頁可開及 canonical/source
manifest 仍一致；「檔案已複製」本身不算 restore 成功。記錄回復耗時與失敗原因。

## 9. Ranked risk register

分數為 likelihood（1–3）× impact（1–3），同分先處理 detection gap。

| ID | 風險 | L | I | 分數 | 現有偵測 | Safe path／owner |
|---|---|---:|---:|---:|---|---|
| R1 | 新 base catalog 與舊 portrait registry 不閉合，卻被人工改 hash 強行套用 | 2 | 3 | 6 | strict registry/materialization；本手冊人工停損 | 新 queue + 人工 exact review；Content reviewer |
| R2 | 切換只換 catalog 或只換 assets，造成混合 revision | 2 | 3 | 6 | API full-load、fingerprint/drift 503 | candidate 整組驗證，停機 rename；Maintainer |
| R3 | Gacha DOCX hash 更新但 compose 仍指舊 content-address | 3 | 2 | 6 | API not found/invalid、compose diff | 一處 exact 64-hex 更新 + overlay rollback；Maintainer |
| R7 | 新資料合法改變而固定 E2E golden 被錯當成 parser defect | 2 | 2 | 4 | source delta + fixture-specific test 分類 | Builder 更新 golden，不刪 invariant |
| R8 | EsterTion 服務或素材 URL 漂移 | 2 | 2 | 4 | UI error -> workbook fallback | 保留 exact Excel assets；Maintainer |
| R9 | `.runtime` 增長導致快照／切換空間不足 | 2 | 2 | 4 | preflight free-space、cycle size review | 先停止；使用者確認後才做 retention cleanup |
| R10 | 備份存在但未實際 restore | 2 | 2 | 4 | 季度 restore drill log | restore 到隔離路徑並 full-load；Maintainer |
| R4 | 私人更新污染 canonical research core | 1 | 3 | 3 | 更新前後全樹 SHA manifest、5/4 direct guard | 立即中止，不從 candidate 回寫；Maintainer |
| R5 | 未確認 variant／台服六星被誤換成外部圖 | 1 | 3 | 3 | exact registry/evidence verifier、workbook fallback tests | fail closed；Content reviewer + Builder |
| R6 | 原始 XLSX/DOCX 被工具或人工覆寫 | 1 | 3 | 3 | source before/after length + SHA | parser 只讀 cycle snapshot；Maintainer |

## 10. Maintenance calendar

| 頻率／觸發 | 工作 | 完成證據 |
|---|---|---|
| 每次收到新 XLSX／DOCX | 完整執行 preflight、candidate、hash/canonical guards、focused tests、desktop/mobile smoke | cycle directory + source/candidate SHA + test output |
| 每週（有使用本機服務時，15 分鐘） | 呼叫兩個 list endpoints；檢查 structured 503、API/Web log 與 `.runtime` 磁碟成長 | 無未分類 503；有問題附 incident note |
| 每月第一週（30–60 分鐘） | 檢查是否有新 PVE/Gacha 文件；盤點 `PENDING`／`REVIEWED_UNKNOWN`；只把人工確認需求排入內容覆核 | queue summary、決定「更新／不更新」及理由 |
| 台服官方六星／角色公告後 | 保存 exact So-net TW snapshot、pin SHA、人工核對 exact variant，再 materialize candidate | evidence id、locator、hash、unit key、before/after mapping |
| 每月第二週（30 分鐘） | dependency/CVE 與 external source 可用性唯讀盤點；不在資料 refresh 中升級版本 | finding list；升級另開有 rollback 的 Maintainer cycle |
| 每季（60–90 分鐘） | 從最近 rollback snapshot restore 到隔離目錄，分別用兩個 Runtime full-load；不取代 live | 日期、snapshot、pass/fail、restore time、gaps、下次日期 |
| 每次 incident 後 48 小時內 | 記錄 detect -> mitigate -> diagnose -> route；更新 risk ranking/runbook | incident note 與 prevention action owner |
| 每半年 | 檢視 retention；先證明至少兩份已驗證快照仍可 restore，再向使用者請求清理舊 cycle | 使用者核准與保留清單；沒有核准不刪 |

Maintenance 不應默默擴張成常駐排程。若每月維運超過半天，先把風險 register 重新排序，
再由使用者決定是否投資 Builder 工具化；身分／六星人工 gate 永遠不得自動化略過。

## 11. Cycle log 與 handoff

每次結束在 `$CycleRoot/audit/cycle-result.md` 記錄：

```text
日期／執行者：
更新類型：PVE | Gacha | portraits only
來源檔名、bytes、SHA-256：
舊／新 dataset SHA-256：
count delta 與理由：
portrait queue：CONFIRMED / REVIEWED_UNKNOWN / PENDING
六星變更與 exact evidence ids：
Gacha：candidate / raw-name / warning / canonical-write counts
測試：focused / contract / desktop / mobile
canonical + original-source no-write guard：PASS | FAIL
切換：未執行 | PASS | ROLLED_BACK
restore time（若有）：
未解風險、owner、下次檢查日期：
```

需要 Builder 的情況：workbook layout/parser 不相容、API contract 或 UI golden 需合法更新、
restore 需要新設計。需要內容覆核的情況：任一新 portrait、variant/name/evidence 不確定，或
台服六星狀態改變。Maintainer 不在這兩類問題上代做猜測。
