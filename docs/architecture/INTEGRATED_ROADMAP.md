# v3.0 整合 Roadmap

## 已鎖定基線

- RP-B0-0：R3i commit `6918afa13f3acd63e0563b078f60f8c4d5f41ee8`
- Research ZIP SHA-256：`4c57ad31be4a2ef41471a70090f5058978dab41a4e1087eba5d0e403e5b66eaa`
- A0 與 A1 已完成，只做 conformance regression。
- RP-I0：46 檔 manifest SHA-256
  `80e6be16fbfbbef1c676def920348aa006d6608a0900f2e62ba4d5cac2d62bcb`；
  Evidence→Claim declared FK 已閉合，實測結果見
  [`I0_VERIFICATION_REPORT.md`](../operations/I0_VERIFICATION_REPORT.md)。
- RP-A2：48 檔 manifest SHA-256
  `3a242b521d830af12ce8559d88b733068fb1b6cb503219395d2986b89e5dc352`；
  8 條來源操作軸與 14 個原子步驟已納入 file SSOT。這是 RP-A2 歷史邊界，非目前
  RP-A5 serving closure。
- RP-A5：48 檔 manifest SHA-256
  `1826c8493d40f71a6d0bb9096f57b92fe4e839d52bddf021b0c51e0186dcbda7`；15 條來源操作軸、
  37 個原子步驟與首個 Arena exact defense slice 已完成 research→DB→API→UI 實測。

## 實作順序

1. ✅ B0a：monorepo、contracts、Compose、health skeleton。
2. ✅ B0b：紅焰 8-10 完整三隊 closure → DB mirror → API → Web → Evidence Drawer。
3. ✅ I0：逐筆裁決七個 Evidence→Claim 懸空引用，新增 Validator 與 Mutation。
4. ✅ A2＋B2：file-SSOT 結構化操作軸與真實深域垂直切片。
5. ✅ B1：完整 importer／exporter／round-trip parity；資料邊界見
   [`ADR-0004`](ADR-0004-full-core-round-trip.md)。
6. ✅ 正式 A3 PVE expansion 的 RP-A3：紅焰 8-10 五隊成熟切片；✅ RP-A4：蒼波
   8-10 五隊與來源操作軸切片。這兩個 `RP-*` 是 release checkpoint，不等於企劃書的
   B3／A4 milestone。
7. ✅ RP-A5：Arena Gate correctness 與首個 exact defense→typed DB→API→UI／Evidence
   Drawer 垂直切片。
8. ⏳ B3＋A5 content expansion：目前 2 筆 counter 都是 `SINGLE_REPORT`，Arena mature
   defenses 仍為 0；擴充到具多來源 VERIFIED closure 的 Gate B／C 成熟案例。
9. B4＋A6：Princess Arena Planner 與成熟三隊案例。
10. 正式 A4＋B5：Gacha／News data 與 UI。
11. B6 Shadow → B7 Review／Audit／Rollback。
12. A7：Data Gate A／B／C PASS；其中 A3 expansion 尚須把 PVE 由 2 個成熟關卡擴至 5。
13. B8：writable SSOT 原子切換。
14. B9／B10：效能、安全、備援與 Production Gate G。

## B1 明確保留的非阻斷債務

- B1 已導入 revision-aware cache、嚴格單調 epoch 與 `REPEATABLE READ`，同時保留
  core／typed drift 的 fail-closed 語意。
- B1 已將策略路由的 DB unavailable／mirror drift 統一為結構化 503；Production Gate
  前仍需加入不含 secret 的 structured root-cause class／path／correlation id，避免
  `--no-access-log` 環境缺少可診斷訊號。
- Production Gate 前以 OpenAPI generator 取代手寫 client types，並產生 Python
  transitive dependency lock／SBOM；B0 先以可執行 schema parity check 守住漂移。

## RP-A2 歷史交付邊界與目前狀態

- TM-F810-01 為 `SOURCE_GAP 0/3`、TM-F810-02 為 `PARTIAL 1/4`、
  TM-F810-03 為 `SOURCE_GAP 0/1`；局部來源軸不會被合併成虛構共識軸。
- RP-A2 當時的 PostgreSQL typed closure 為 8 條 timeline、14 個 atomic steps；目前 RP-A5
  已是 15／37。Artifact／row mirror 保存原始內容，只有 typed serving closure 正規化；
  import replay、完整 fixture fingerprint 與 serving-boundary drift 均 fail-closed。
- 正式 A3 PVE expansion 已交付 RP-A3／RP-A4 兩個成熟關卡；PVE Gate B 的數量條件
  為 2/2，Gate C 仍為 2/5。RP-A5 首切片已完成，但 Arena Gate 仍為 0；下一步是
  B3＋A5 content expansion，並依賴其後 B4＋A6 的 Princess Arena 成熟案例。Data Gate
  A／B／C 與 Gates D–G 仍未宣稱通過。
- 回滾點：A2 research core 使用 `rp-a2-2`；A2＋B2 通過 Compose CI 的完整切片使用
  `rp-a2-b2-2`；A3 使用 `rp-a3-1`；本次 A4 通過完整驗證後使用 `rp-a4-1`。
  `rp-a2-b2-1` 僅保留作 CI parity 修正前的稽核 checkpoint；RP-A5 使用 `rp-a5-1`，
  A5→A4→A5 依 [`A5_ROLLBACK_RUNBOOK.md`](../operations/A5_ROLLBACK_RUNBOOK.md)。任何已有
  較新 schema 的資料庫都不得只 checkout 舊 tag，必須同時依版本回滾手冊處理 DB。

## 不可突破的停止條件

- research-core blob 或五命令出現未解釋漂移。
- Importer 的 FK、team count、Evidence closure、Enum 或 metadata 不一致。
- ARTIFACT_READY 出現 Gate A／B／C 以外的新 FAIL。
- Scheduler 在無 lock、idempotency、Shadow 隔離時準備啟用。
- Migration／cutover 前沒有可驗 restore。
- Secret 進入 repository、image 或 log。
- 未實際取得正文的頁面被準備升為 Evidence。
