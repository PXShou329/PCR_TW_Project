# v3.0 整合 Roadmap

## 已鎖定基線

- RP-B0-0：R3i commit `6918afa13f3acd63e0563b078f60f8c4d5f41ee8`
- Research ZIP SHA-256：`4c57ad31be4a2ef41471a70090f5058978dab41a4e1087eba5d0e403e5b66eaa`
- A0 與 A1 已完成，只做 conformance regression。
- RP-I0：46 檔 manifest SHA-256
  `80e6be16fbfbbef1c676def920348aa006d6608a0900f2e62ba4d5cac2d62bcb`；
  Evidence→Claim declared FK 已閉合，實測結果見
  [`I0_VERIFICATION_REPORT.md`](../operations/I0_VERIFICATION_REPORT.md)。

## 實作順序

1. ✅ B0a：monorepo、contracts、Compose、health skeleton。
2. ✅ B0b：紅焰 8-10 完整三隊 closure → DB mirror → API → Web → Evidence Drawer。
3. ✅ I0：逐筆裁決七個 Evidence→Claim 懸空引用，新增 Validator 與 Mutation。
4. A2＋B2：file-SSOT 結構化操作軸與真實深域垂直切片。
5. B1：完整 importer／exporter／round-trip parity。
6. A3–A6 與 B3–B5 配對完成 PVE、Gacha、Arena、P-Arena。
7. B6 Shadow → B7 Review／Audit／Rollback。
8. A7：Data Gate A／B／C PASS。
9. B8：writable SSOT 原子切換。
10. B9／B10：效能、安全、備援與 Production Gate G。

## B0 明確保留的非阻斷債務

- B1 將每請求完整重算 closure manifest 改為 revision-aware cache，同時保留
  fail-closed 語意。
- 將策略路由的 DB unavailable 例外統一為結構化 503；目前不會洩漏或回傳漂移
  資料，但連線層錯誤仍由框架形成一般 500。
- Production Gate 前以 OpenAPI generator 取代手寫 client types，並產生 Python
  transitive dependency lock／SBOM；B0 先以可執行 schema parity check 守住漂移。

## 不可突破的停止條件

- research-core blob 或五命令出現未解釋漂移。
- Importer 的 FK、team count、Evidence closure、Enum 或 metadata 不一致。
- ARTIFACT_READY 出現 Gate A／B／C 以外的新 FAIL。
- Scheduler 在無 lock、idempotency、Shadow 隔離時準備啟用。
- Migration／cutover 前沒有可驗 restore。
- Secret 進入 repository、image 或 log。
- 未實際取得正文的頁面被準備升為 Evidence。
