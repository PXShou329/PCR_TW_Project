# 16 靜態驗證報告（STATIC VALIDATION REPORT）

> 由 `tools/validate_project.py` 生成（唯一路徑）；回歸驗證：`python3 tools/mutation_test.py`（Active 情境數見其輸出；退休 ID 見 Archive）。
> 生成日：2026-08-10｜版本：v1.5｜Release：2026-08-09｜Mode：PRE_SUITE

## 檢查結果（166 項）

| 檢查 | 結果 | 明細 |
|---|---|---|
| 檔案數（非 tools） | PASS | 44 |
| 編號檔數 | PASS | 43 |
| Knowledge 檔數 | PASS | 42 |
| tools 檔存在 | PASS |  |
| 跨檔引用完整 | PASS |  |
| README 權威表與磁碟一致 | PASS | 44／44 |
| Instructions §1–§12 連續 | PASS |  |
| ST44：版本 SSOT 精確一致（v1.5） | PASS | 漂移: |
| ST80：Active 檔無帳號匯入指令（Guide-Only） | PASS |  |
| 41：欄數 36＋列數 ≥2 | PASS | 5 列 |
| 92：欄數 16＋列數 ≥36 | PASS | 122 列 |
| 93：欄數 14＋列數 ≥34 | PASS | 137 列 |
| 17：欄數 21＋列數 ≥0 | PASS | 0 列 |
| 24：欄數 16＋列數 ≥0 | PASS | 3 列 |
| 39：欄數 35＋列數 ≥0 | PASS | 2 列 |
| 18：欄數 15＋列數 ≥1 | PASS | 35 列 |
| 25：欄數 20＋列數 ≥0 | PASS | 10 列 |
| 26：欄數 16＋列數 ≥1 | PASS | 15 列 |
| 27：欄數 20＋列數 ≥0 | PASS | 37 列 |
| 45：欄數 14＋列數 ≥2 | PASS | 4 列 |
| 46：欄數 12＋列數 ≥2 | PASS | 6 列 |
| 47：欄數 24＋列數 ≥0 | PASS | 0 列 |
| ID 唯一（evidence／claim／event／sync／unit／team／counter／source） | PASS |  |
| 92：evidence_confidence 欄名 | PASS |  |
| 92：evidence_confidence Enum | PASS |  |
| 92：URL 標準化 | PASS |  |
| ST73：92 status Enum | PASS |  |
| 92：source_tier Enum | PASS |  |
| ST47：92 日期精度與格式一致 | PASS |  |
| 93：claim_type／confidence Enum | PASS |  |
| 93→92 FK 完整 | PASS |  |
| ST86：92→93 declared Claim FK 完整 | PASS |  |
| ST49：B／C 證據唯一＋來源獨立（27 筆） | PASS |  |
| ST50：A Claim 與 A Evidence 相容 | PASS |  |
| DERIVED_CALCULATION 附推導註記 | PASS |  |
| ST82：CLM-LOC 跨服映射邊界（21 筆） | PASS |  |
| ST74：所有 Evidence status 與 limitations 一致（PENDING⟺回驗註記；ACTIVE⟺無解鎖級殘留） | PASS |  |
| 18：欄位標頭符合規格 | PASS |  |
| 18：availability Enum | PASS |  |
| 18：強化欄位 Enum | PASS |  |
| 18：Evidence FK | PASS |  |
| 18：日期格式 | PASS |  |
| 39：tw_availability_check Enum；PASS 的敵我各五人須不同且均為 18 AVAILABLE | PASS |  |
| 39：Arena TW availability 三態須與 18 雙向一致 | PASS |  |
| 39：unavailable_unit_ids 精確列出 18 NOT_RELEASED 成員 | PASS |  |
| 39：PASS 成員皆有台服官方名與 ACTIVE TW OFFICIAL／A Evidence | PASS |  |
| 39：同 server／environment 的相同敵我五人配對不得重複 | PASS |  |
| 39：canonical Arena registry 僅保存 EXACT 配對 | PASS |  |
| 39：Arena status／source tier／confidence／reproducibility enums | PASS |  |
| 39：required_upgrade_check Enum | PASS |  |
| 39：Arena outcome／verification／risk／environment enums | PASS |  |
| 39：Arena operation_mode Enum | PASS |  |
| 39：Arena bracket／speed／initial action 明示 UNKNOWN 而非留白 | PASS |  |
| 39：Arena source-truth metadata 不得留白 | PASS |  |
| 39：Arena source record／日期 metadata 合法 | PASS |  |
| 39：Arena sample_size＝wins＋losses 且皆為非負整數 | PASS |  |
| 39：單筆 Arena 戰果不得宣稱 empirical win rate | PASS |  |
| 39：SINGLE_REPORT claim_confidence 固定 D | PASS |  |
| 39：WIN／LOSS outcome 與明示計數一致 | PASS |  |
| 39：VERIFIED Arena 列需 environment_version | PASS |  |
| 39：VERIFIED Arena 列需 CONFIRMED reproducibility | PASS |  |
| 39：publishable Arena closure 僅引用同服 arena ACTIVE Evidence／Claim | PASS |  |
| 39：VERIFIED Arena 僅承認獨立多來源 WIN Evidence／Claim closure | PASS |  |
| 39：VERIFIED Arena 成熟 Evidence 皆須具 nonempty HTTPS hostname | PASS |  |
| 25：欄位標頭符合規格 | PASS |  |
| 25：guide_id FK→24 | PASS |  |
| 25：五 slot 完整 | PASS |  |
| 25：clear_status Enum | PASS |  |
| 25：每隊五名角色互異 | PASS |  |
| 24→25：team server／stage 與 guide 關聯一致 | PASS |  |
| 25：tw_availability_check Enum；PASS 的五 slot 均須為 18 AVAILABLE | PASS |  |
| 25：Evidence FK | PASS |  |
| 25：operation_mode Enum | PASS |  |
| 25：requirements 為 canonical JSON；必要 key／slot1–5 完整且無空字串 | PASS |  |
| 25：借角 unit／support_slot 三態關聯一致 | PASS |  |
| 25：SOURCE_CONFLICT 至少兩來源＋兩種 mode；非衝突 mode 與來源聲明一致 | PASS |  |
| 25：同關卡相同五人不得重複列（多來源合併） | PASS |  |
| 26：欄位標頭符合規格 | PASS |  |
| 27：欄位標頭符合規格 | PASS |  |
| 26：team／Evidence FK 與逐來源 operation mode 聲明一致 | PASS |  |
| 26：source locator 必須等於 Evidence locator 或其 # 子定位 | PASS |  |
| 26：同隊同來源只保留一條 source axis；結構化 timeline_id 唯一 | PASS |  |
| 26：STRUCTURED／SOURCE_GAP 狀態不得強化 UNKNOWN | PASS |  |
| 27：step FK／Enum／時間範圍／角色成員資格完整 | PASS |  |
| 27：每來源 sequence_no 唯一且連續 | PASS |  |
| 27：source_step_no 依序且分組連續 | PASS |  |
| 26／27：STRUCTURED 必有步驟；SOURCE_GAP 必為零步驟 | PASS |  |
| ST87：來源邊界、locator 與未載欄位不得推測 | PASS |  |
| 25→26：手動／半自動／衝突隊伍每個來源與 timeline_ref 均有結構化軸或明示缺口 | PASS |  |
| 26：跨服結構化軸不得冒充台服已重現 | PASS |  |
| 24／25：VERIFIED PVE closure 僅引用 ACTIVE Evidence／Claim | PASS |  |
| 45：欄位標頭符合規格 | PASS |  |
| 45：source_type Enum | PASS |  |
| 45：社群來源信心上限 ≤C（不得標 OFFICIAL／A／B） | PASS |  |
| 45：update_status Enum | PASS |  |
| 46：欄位標頭符合規格 | PASS |  |
| 46：access_status Enum | PASS |  |
| 46：來源信心上限 ≤C | PASS |  |
| 41：社群共識欄存在（官方／錨點／社群分欄） | PASS |  |
| ST45：定義精確集合（Guide-Only 41 測試）＋各僅一次 | PASS |  |
| ST46：Fixture 覆蓋公共測試精確集合 | PASS | 缺[] |
| Fixture 數 | PASS | 37/37 |
| ST48：12 台服新角導向 18（無 TW_ROSTER_PENDING 殘留） | PASS |  |
| ST39a：91 §3 必含語意 | PASS |  |
| ST39b：91 §3／12 無繞過語句 | PASS |  |
| ST39c：12 截止日＝各列最新 | PASS |  |
| ST39d：RELEASED 無 NOT_ANNOUNCED 矛盾 | PASS |  |
| ST39e：MIGRATED_TO_41 有對應 event_id | PASS |  |
| ST40：T43 動態錨點（02 須揭露軌道別 n 值，數值由 anchors 派生） | PASS |  |
| ST41：tools 數一致 | PASS | 實4 |
| ST42：41 MATURE 列 last_verified ≥ 基準日（非成熟列可保留誠實舊日期） | PASS |  |
| ST43：待回驗 Evidence 的 Claim 附註一致 | PASS |  |
| ST75：15／README 不再宣稱主線／六星完全待查 | PASS |  |
| ST75b：02 OPEN_GAPS SSOT 存在 | PASS |  |
| 17 欄位標頭符合規格 | PASS |  |
| ST56：17 run_id 唯一 | PASS | 0 列 |
| ST57a：17 test_id 屬 definition_set | PASS |  |
| ST57b：17 suite 與 test_id 對應 | PASS |  |
| ST57c：17 fixture 與 test_id 對應 | PASS |  |
| ST57d：17 fixture_id 存在 | PASS |  |
| ST58：17 Evidence FK 完整 | PASS |  |
| 17 status Enum | PASS |  |
| ST59：PASS 必填欄位（含 reviewer／review_method／expectation_checklist） | PASS |  |
| ST59b：PASS review_method=MANUAL_FIXTURE_REVIEW＋checklist=ALL_PASS | PASS |  |
| ST51：FAIL 必附 defect_id＋observed_result | PASS |  |
| ST71：Execution Evidence Policy（server／count／confidence） | PASS |  |
| ST61a：每 test/scope/account 恰一 is_current | PASS |  |
| ST61b：retest_of／supersedes 引用既有 run_id | PASS |  |
| ST67：retest_of 同 test/scope/account | PASS |  |
| ST68：retest chain 無循環 | PASS |  |
| ST69：current 為 terminal node | PASS |  |
| 25 與 24：所有 guide 的 team_count＝25 有效隊伍數 | PASS |  |
| 47：欄位標頭符合規格 | PASS |  |
| 47：all-row status／server／hidden／check／reproducibility enums | PASS |  |
| 47：all-row team shape／unit FK／hidden relation | PASS |  |
| 47：all-row source／Evidence／Claim FK 與 ID 不重複 | PASS |  |
| 47：case WIN direct Evidence confidence 僅 A／B／C／D | PASS |  |
| 47：source_ids hostname 覆蓋 case WIN direct Evidence | PASS |  |
| 47：case WIN Evidence published_date 不晚於 verified_date | PASS |  |
| ST81：P-Arena VERIFIED 需四 designated Claim＋三組 mature exact 39 closure | PASS |  |
| 47：同 TW environment／相同三隊防守不得重複 VERIFIED case（重排亦同案） | PASS |  |
| 47：VERIFIED case_win_claim_id 不得跨 case 重用 | PASS |  |
| ST68：PVE Gate Row 完整性（24 registry 成熟列） | PASS | 2 成熟 |
| ST69：Arena Gate Row 完整性（39 registry 5v5） | PASS | 0 成熟反制列／0 成熟防守 |
| ST70：Timeline Maturity Row 完整性（41） | PASS | 2 MATURE |
| 13：AUTO_RESULTS 列出全部 41 測試（由 validator 生成） | PASS | 缺[] |
| ST72：13 具 AUTO_RESULTS 區＋無殘留手動狀態表 | PASS |  |
| ST60：13 AUTO_RESULTS 與 17 current 實質一致（生成日不列入比對） | PASS |  |
| CURRENT_SPEC_SCAN 無禁用字串 | PASS |  |
| ST83a：舊 config 統計 SSOT 欄位不得復活 | PASS |  |
| ST83：Anchor Schema／FK／日期（8 筆） | PASS |  |
| ST84a：SYSTEM 軌不得混入角色卡池統計 | PASS |  |
| ST84：四軌統計由 anchors 即時計算且與 02／40 口徑一致 | PASS |  |
| ST85：41 anchor semantics（5 ACTIVE 列） | PASS |  |
| ST85a：41 final interval method（5 列） | PASS |  |
| ST85b：41 RESEARCH 不得夾帶抽取優先級 | PASS |  |
| ST85c：41 limited 必須具 JP OFFICIAL／A direct Claim closure | PASS |  |
| T41 單位分離 | PASS |  |
| 三情境 | PASS |  |
| 缺口公式 | PASS |  |
| 02：舊統計口徑不得殘留（改由四軌 anchors 派生） | PASS |  |
| 44 SUPERSEDED 標記 | PASS |  |
| 99 Stale 非空 | PASS |  |
| ST54／ST66：Warning 機制分類運作 | PASS |  |
| ST52：Validation Mode 合法 | PASS | PRE_SUITE |
| ST51(PRE_SUITE)：17 為空（無執行紀錄，權威） | PASS | 17=0 |

## Release Gate（由結構化 Registry 計算成熟列）

| Gate | 狀態 | 依據 |
|---|---|---|
| A Guide Behavior | 未通過 | Guide-Only 41 項 current result 全 PASS＋Static FAIL=0＋無帳號指令（ST80） |
| B 最低可用攻略 | 未通過 | PVE 關卡 2/≥2（每關≥5隊）｜Arena 防守 0/≥5（各≥2反制）｜P-Arena 0/≥3｜Timeline 2/≥6｜社群來源 2/≥2 |
| C 攻略整合可發布 | 未通過 | Gate A＋B＋PVE≥5／Arena≥10／P-Arena≥5＋阻擋警告 14＝0＋新鮮度 |

## 統計（程式化）

- 檔案 44（編號 43＋README）＋tools×4；Knowledge 42
- 92：122 列｜Tier {'OFFICIAL': 82, 'MAJOR_GUIDE': 10, 'SINGLE_PLAYER_REPORT': 21, 'MULTI_PLAYER_REPORT': 5, 'STRUCTURED_DB': 1, 'UNKNOWN': 3}｜93：137 列｜claim_type {'SOURCE_FACT': 92, 'DERIVED_CALCULATION': 6, 'ANALYTICAL_JUDGMENT': 39}
- 數學重驗：canonical anchors 8 筆｜LIMITED n=5 median=123｜PERMANENT n=2 median=122.5｜ALL_NEW n=7 median=123｜SYSTEM n=1 median=75｜T41=120、三情境、缺口式——全部由 anchors 即時重算

## FAIL：0｜WARN：22（阻擋 Gate C：14）

（無 FAIL）

## WARN（分類；blocks_gate_c＝Y 者會阻擋 Gate C）

| warning_id | category | severity | blocks_C | module | detail | next_action |
|---|---|---|---|---|---|---|
| EV-ev061 | evidence_pending | info | N | 92 | ev061 待直頁回驗（未被成熟資料引用） | 91 §1 回驗 |
| CLM-CLM-SHEFI-EVAL-PVE | confidence_low | warn | Y | 93 | CLM-SHEFI-EVAL-PVE＝D（成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-LUISE-EVAL | confidence_low | warn | Y | 93 | CLM-LUISE-EVAL＝D（成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-JPARENA-META | confidence_low | info | N | 93 | CLM-JPARENA-META＝D（研究中，未被成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-JPARENA-TOOL | confidence_low | info | N | 93 | CLM-JPARENA-TOOL＝D（研究中，未被成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-ARENA-DEFENSE-STRUCT | confidence_low | info | N | 93 | CLM-ARENA-DEFENSE-STRUCT＝D（研究中，未被成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-TWARENA-2409 | confidence_low | info | N | 93 | CLM-TWARENA-2409＝D（研究中，未被成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-SEASONPASS | confidence_low | info | N | 93 | CLM-SEASONPASS＝D（研究中，未被成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-PVE-F1010-SCARCE | confidence_low | info | N | 93 | CLM-PVE-F1010-SCARCE＝D（研究中，未被成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-PVE-F810-NOLUISE | confidence_low | warn | Y | 93 | CLM-PVE-F810-NOLUISE＝D（成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-PVE-F810-ANNEGREA | confidence_low | warn | Y | 93 | CLM-PVE-F810-ANNEGREA＝D（成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-PVE-F810-MIO | confidence_low | warn | Y | 93 | CLM-PVE-F810-MIO＝D（成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-PVE-W810-MISORA-NANAKA | confidence_low | warn | Y | 93 | CLM-PVE-W810-MISORA-NANAKA＝D（成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-PVE-W810-SONO-NINON | confidence_low | warn | Y | 93 | CLM-PVE-W810-SONO-NINON＝D（成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-PVE-W810-LABYRISTA-SONO | confidence_low | warn | Y | 93 | CLM-PVE-W810-LABYRISTA-SONO＝D（成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-PVE-W810-SONO-NANAKA | confidence_low | warn | Y | 93 | CLM-PVE-W810-SONO-NANAKA＝D（成熟資料引用） | 補第二獨立來源或維持研究層 |
| CLM-CLM-PVE-W810-MISORA-SONO | confidence_low | warn | Y | 93 | CLM-PVE-W810-MISORA-SONO＝D（成熟資料引用） | 補第二獨立來源或維持研究層 |
| GATE-PVE | gate_c_data | warn | Y | 24 | PVE 成熟關卡 2<5（每關≥5隊） | Checkpoint B PVE Wave |
| GATE-ARENA | gate_c_data | warn | Y | 39 | Arena 防守案例 0<10（各≥2 TW_AVAILABLE 反制） | Checkpoint D Arena Ingestion |
| GATE-TIMELINE | gate_c_data | warn | Y | 41 | Timeline MATURE 2<6 | Checkpoint C Gacha Integration |
| GATE-PARENA | gate_c_data | warn | Y | 47 | P-Arena 成熟案例 0<3（THEORY 不計） | Checkpoint E 組合求解入 47 |
| SUITE-NOTRUN | pre_suite | info | N | 17 | 四 Suite 尚未實跑 | v1.5 部署後執行 |

## INFO

- Mode＝PRE_SUITE（PRE_SUITE／OPERATIONAL 增量／ARTIFACT_READY 強制 Gate A/B/C＋blocking_c=0）
- Gate A/B/C＝False/False/False（數量由 24／39／41／45／47 成熟列計算，非計數全部列）
- 目前 PENDING_REVIEW Evidence：ev061
- 回歸攔截由 tools/mutation_test.py 驗證（Active 情境數以其執行輸出為準；歷史／退休 ID 見 Account Archive）
- Canonical 15/16/13/stats 寫入：是

## HISTORICAL_RECORD_SCAN（資訊性；不 FAIL、不刪除）

- 99_CHANGELOG.md（歷史區）：Fixtures×24
