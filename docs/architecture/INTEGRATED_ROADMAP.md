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
  8 條來源操作軸與 14 個原子步驟已納入 file SSOT。

## 實作順序

1. ✅ B0a：monorepo、contracts、Compose、health skeleton。
2. ✅ B0b：紅焰 8-10 完整三隊 closure → DB mirror → API → Web → Evidence Drawer。
3. ✅ I0：逐筆裁決七個 Evidence→Claim 懸空引用，新增 Validator 與 Mutation。
4. ✅ A2＋B2：file-SSOT 結構化操作軸與真實深域垂直切片。
5. ✅ B1：完整 importer／exporter／round-trip parity；資料邊界見
   [`ADR-0004`](ADR-0004-full-core-round-trip.md)。
6. A3–A6 與 B3–B5 配對完成 PVE、Gacha、Arena、P-Arena。
7. B6 Shadow → B7 Review／Audit／Rollback。
8. A7：Data Gate A／B／C PASS。
9. B8：writable SSOT 原子切換。
10. B9／B10：效能、安全、備援與 Production Gate G。

## B1 明確保留的非阻斷債務

- B1 已導入 revision-aware cache、嚴格單調 epoch 與 `REPEATABLE READ`，同時保留
  core／typed drift 的 fail-closed 語意。
- B1 已將策略路由的 DB unavailable／mirror drift 統一為結構化 503；Production Gate
  前仍需加入不含 secret 的 structured root-cause class／path／correlation id，避免
  `--no-access-log` 環境缺少可診斷訊號。
- Production Gate 前以 OpenAPI generator 取代手寫 client types，並產生 Python
  transitive dependency lock／SBOM；B0 先以可執行 schema parity check 守住漂移。

## A2＋B2 交付邊界

- TM-F810-01 為 `SOURCE_GAP 0/3`、TM-F810-02 為 `PARTIAL 1/4`、
  TM-F810-03 為 `SOURCE_GAP 0/1`；局部來源軸不會被合併成虛構共識軸。
- PostgreSQL read mirror 新增 8 條 timeline、14 個 atomic steps；import replay、
  完整 fixture fingerprint 與 serving-boundary drift 均 fail-closed。
- 下一固定里程碑為 A3＋B3；Data Gate A／B／C 與 Gates D–G 仍未宣稱通過。
- 回滾點：A2 research core 使用 `rp-a2-2`；A2＋B2 通過 Compose CI 的完整切片使用
  `rp-a2-b2-2`。`rp-a2-b2-1` 僅保留作 CI parity 修正前的稽核 checkpoint。

## 不可突破的停止條件

- research-core blob 或五命令出現未解釋漂移。
- Importer 的 FK、team count、Evidence closure、Enum 或 metadata 不一致。
- ARTIFACT_READY 出現 Gate A／B／C 以外的新 FAIL。
- Scheduler 在無 lock、idempotency、Shadow 隔離時準備啟用。
- Migration／cutover 前沒有可驗 restore。
- Secret 進入 repository、image 或 log。
- 未實際取得正文的頁面被準備升為 Evidence。
