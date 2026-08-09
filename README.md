# 公主連結台服 AI 攻略研究所

Guide-Only Strategy Platform v3.0 的 RP-B5-1 Gacha 垂直切片候選，建立在
B3／D0 exact picker、RP-A5 Arena typed slice、RP-A4 Water 成熟切片與已封存的 B1 full-core round-trip 里程碑之上。這是一個可部署的
**本機／私人 staging**，不是公開正式版，也尚未宣稱 Gates D–G 通過。

本切片以私人 tag `rp-b3-d0-1` 封存五角色 exact picker、保守 Strategy Metadata 與
Application/Data parity verifier；前一安全回滾點是 `rp-a5-2`。`rp-a5-1` 保留為 CI runtime
依賴安裝修正前的稽核 checkpoint。RP-A4 仍保留為 Water／A3 PVE content expansion 的
rollback checkpoint，不覆寫歷史 manifest。這個 release checkpoint
不等於整個 B3＋A5 content expansion 已完成：Arena mature defenses 目前仍為 0。RP-B5-1
完成私人 CI 後才建立新的 immutable tag；既有 tags 不移動。

目前端到端垂直切片包含「紅焰深域 8-10」與「蒼波深域 8-10」，各提供五支不同五人的實際通關隊伍、逐 Slot
條件、來源分離的操作軸、逐步 Evidence Drawer，以及誠實的 `UNKNOWN`／結構化操作軸缺口。競技場
research core 已加入同環境、實際勝利截圖支持的兩筆 `SINGLE_REPORT` exact counter；不把單次
回報包裝成勝率，也不建立示意隊。`/pvp` 現在以五個 AVAILABLE 台服官方名稱角色建立
可分享的 exact query；不足五人、重複角色與四人重疊都 fail closed，Similar 仍未啟用。
`/gacha` 把 5 筆 timeline 與 4 筆社群來源從 file SSOT 正規化到 PostgreSQL v4、FastAPI、
typed client 與 Next.js UI：2 筆 MATURE、3 筆 RESEARCH；三筆已知限定身分都有指定 JP
OFFICIAL／A Claim/Evidence，Vampy／Tia 維持 `UNKNOWN/null`。頁面不輸出個人寶石、
持有角色條件或帳號專屬抽取建議。

## 真相與安全邊界

- `research_core/pcr_tw_project/` 是唯一 canonical source；目前 RP-B5-1 的 48 個檔案
  由 `scripts/research_core_rp_b5_1_manifest.sha256` 逐檔 SHA-256 鎖定；RP-A2／RP-A3／RP-A4／RP-A5
  manifests 保留供 immutable rollback 相容驗證。
- PostgreSQL 同時保存 byte-preserved artifact mirror、lossless row mirror 與 normalized typed
  serving closure；只有 typed closure 供 API／UI 讀取，三者都不會回寫 research core。
- 台服是攻略主體；日服只作未來視與可轉用研究。中國服／B 服資料不作核心、
  替代或補洞依據。
- 不含帳號匯入、roster／owned、個人寶石或個人化推薦，也不登入或操作遊戲。
- Scheduler 預設停用且固定 Shadow Mode；目前 RP-B5-1 仍沒有 fetcher、publisher 或
  canonical writer。
- Migration、Importer、API、Scheduler 使用分離的 PostgreSQL roles；API 只有
  serving tables 的 `SELECT` 權限。

```mermaid
flowchart LR
  RC["B5-1 research core\nFile SSOT"] --> IM["Fail-closed importer"]
  IM --> DB["PostgreSQL\nbyte artifact + lossless rows\nnormalized typed closure"]
  DB --> API["FastAPI read API"]
  API --> WEB["Next.js Web UI"]
  SCH["Disabled shadow scheduler"] --> CTRL["Scheduler control tables only"]
```

## 快速驗證

需要 Python 3.13.14、Node.js 24 LTS／npm 11，以及 Docker Compose v2。

```powershell
python scripts/check_research_baseline.py
python scripts/check_application_data_parity.py --run-round-trip
python -m pytest -q
npm ci
npm run check:contract
npm run typecheck
npm run build:web
```

研究核心的原始五命令需在 `research_core/pcr_tw_project/` 執行：

```powershell
python tools/validate_project.py --mode PRE_SUITE --write
python tools/validate_project.py --mode PRE_SUITE
python tools/validate_project.py --mode OPERATIONAL
python tools/validate_project.py --mode ARTIFACT_READY
python tools/mutation_test.py
```

目前預期 ARTIFACT_READY 仍以 exit 1 誠實揭露 Gate A／B／C 三項缺口；本里程碑不會為了
讓測試變綠而降低研究 Gate。

目前 RP-B5-1 research-core 五命令由 `scripts/check_research_baseline.py` 在乾淨暫存副本
重現；immutable pin 的實跑輸出見
[`docs/operations/B5_1_VERIFICATION_REPORT.md`](docs/operations/B5_1_VERIFICATION_REPORT.md)。
本次 fresh V0007 stack、651 格 ACL、Shadow scheduler、backup／restore、B5→A5→B5
schema/data rollback，以及 mock／real desktop/mobile 實跑輸出亦收錄於該報告；操作順序見
[`docs/operations/B5_ROLLBACK_RUNBOOK.md`](docs/operations/B5_ROLLBACK_RUNBOOK.md)。歷史
A5→A4→A5 證據仍見
[`docs/operations/A5_VERIFICATION_REPORT.md`](docs/operations/A5_VERIFICATION_REPORT.md)。
本次 B3／D0 picker、metadata、重建 A5 stack、backup／restore 與 rollback 實跑輸出見
[`docs/operations/B3_D0_VERIFICATION_REPORT.md`](docs/operations/B3_D0_VERIFICATION_REPORT.md)。
RP-A4 的 round-trip、PostgreSQL、瀏覽器、E2E、restore 與 A4→A3 rollback drill 歷史輸出仍見
[`docs/operations/A4_VERIFICATION_REPORT.md`](docs/operations/A4_VERIFICATION_REPORT.md)；
B1 的歷史基線仍保留於
[`docs/operations/B1_VERIFICATION_REPORT.md`](docs/operations/B1_VERIFICATION_REPORT.md)。

## 啟動本機私人堆疊

先將 `.env.example` 複製為 Git 忽略的 `.env`，並把四組密碼替換為彼此不同、至少
16 字元的 URL-safe 值：

```powershell
docker compose --env-file .env -f infra/compose.yml config --quiet
docker compose --env-file .env -f infra/compose.yml up --build --wait
```

服務入口：

- Web：<http://127.0.0.1:3000>
- API 文件：<http://127.0.0.1:8000/docs>
- API readiness：<http://127.0.0.1:8000/health/ready>
- Scheduler health：<http://127.0.0.1:8081/health>

完整的權限實測、scheduler smoke 與備份還原流程請依
[`docs/operations/B1_RUNBOOK.md`](docs/operations/B1_RUNBOOK.md)；A4→A3 的版本回退與
重新前進請依 [`docs/operations/A4_ROLLBACK_RUNBOOK.md`](docs/operations/A4_ROLLBACK_RUNBOOK.md)；
A5→A4 的 backup-first 回退與重新前進請依
[`docs/operations/A5_ROLLBACK_RUNBOOK.md`](docs/operations/A5_ROLLBACK_RUNBOOK.md)；B5→A5
的 V0007／V0006 回退與重新前進請依
[`docs/operations/B5_ROLLBACK_RUNBOOK.md`](docs/operations/B5_ROLLBACK_RUNBOOK.md)。
架構決策與後續依賴順序見
[`docs/architecture/INTEGRATED_ROADMAP.md`](docs/architecture/INTEGRATED_ROADMAP.md)。
