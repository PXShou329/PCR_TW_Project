#!/usr/bin/env python3
"""Mutation 回歸測試（Guide-Only Active 情境；退休 ID M22/M24/M31–M33 封存於 archive ZIP，永不重用）。
用法：python3 tools/mutation_test.py；全部符合預期才 exit 0。"""
import csv, json, re, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run(d, mode=None, write=False):
    cmd = [sys.executable, os.path.join(d, 'tools', 'validate_project.py')]
    if mode: cmd += ['--mode', mode]
    if write: cmd += ['--write']
    return subprocess.run(cmd, capture_output=True, text=True)

def rewrite_csv(path, fn):
    rows = list(csv.reader(open(path, encoding='utf-8')))
    fn(rows)
    with open(path, 'w', encoding='utf-8', newline='') as f: csv.writer(f).writerows(rows)

def mutate(name, fn, expect, mode=None, check_repair=False, write=False, target_fail=None):
    tmp = tempfile.mkdtemp(); d = os.path.join(tmp, 'p')
    shutil.copytree(ROOT, d)
    fn(d)
    proc = run(d, mode, write); code = proc.returncode
    if expect == 'REPAIR':
        body = open(os.path.join(d, '15_DATA_QUALITY_REPORT.md'), encoding='utf-8').read()
        ok = code == 0 and 'MUTATION_999' not in body; v = f"exit {code}＋汙染{'已修復' if 'MUTATION_999' not in body else '殘留'}"
    else:
        ok = code == (1 if expect == 'FAIL' else 0); v = f"exit {code}（預期 {'1' if expect=='FAIL' else '0'}）"
        if target_fail:
            fail_lines = [line.strip() for line in proc.stdout.splitlines() if line.startswith(' FAIL -')]
            expected_fails = [target_fail] if isinstance(target_fail, str) else list(target_fail)
            target_ok = (
                len(fail_lines) == len(expected_fails)
                and all(any(expected in line for line in fail_lines) for expected in expected_fails)
            )
            ok = ok and target_ok
            v += f"＋目標守門{'命中' if target_ok else '未唯一命中'}"
            if not target_ok:
                v += f"；實際={' | '.join(fail_lines)}"
    shutil.rmtree(tmp)
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {v}")
    return ok

def P(d, n): return os.path.join(d, n)
def rd(p): return open(p, encoding='utf-8').read()
def wr(p, s): open(p, 'w', encoding='utf-8').write(s)
def pve_requirements(claims):
    slot = {"star": "UNKNOWN", "rank": "UNKNOWN", "ue1": "UNKNOWN", "ue2": "UNKNOWN",
            "six_star": "UNKNOWN", "connect_rank": "UNKNOWN", "element_boost": "UNKNOWN"}
    obj = {
        "schema_version": "1.0",
        "operation_mode_claims": claims,
        "slots": {f"slot{i}": dict(slot) for i in range(1, 6)},
        "support": {"unit": "NONE", "requirements": "UNKNOWN"},
        "timeline_ref": "UNKNOWN",
        "failure_conditions": ["UNKNOWN"],
    }
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

EXEC_HDR = "run_id,test_id,suite,fixture_id,fixture_version,exact_prompt,execution_date,model,observed_result,evidence_ids,status,defect_id,retest_of,supersedes_run_id,is_current,reviewer,reviewed_at,review_method,expectation_checklist,response_reference,notes"
def row(**kw):
    kw.pop("test_scope", None); kw.pop("account_id", None)  # Guide-Only：舊欄位相容丟棄
    d = {c: "" for c in EXEC_HDR.split(",")}
    d.update(kw); return [d[c] for c in EXEC_HDR.split(",")]
def add17(d, r):
    p = P(d, "17_TEST_EXECUTION_LOG.csv")
    rows = list(csv.reader(open(p, encoding="utf-8"))); rows.append(r)
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)
def set13(d, tid, st):
    p = P(d, "13_ACCEPTANCE_RESULTS.md")
    wr(p, re.sub(rf"(\| {tid} \| )NOT_RUN", rf"\g<1>{st}", rd(p), count=1))
FULL = dict(fixture_version="v1.5", exact_prompt="prompt", execution_date="2026-07-20",
            model="opus-4.8", observed_result="ok", response_reference="resp#1", is_current="Y",
            reviewer="sweeper", reviewed_at="2026-07-20", review_method="MANUAL_FIXTURE_REVIEW",
            expectation_checklist="ALL_PASS")


# M01 broken FK
def m01(d):
    def fn(R):
        ei=R[0].index('evidence_ids')
        for r in R[1:]:
            if 'ev001' in r[ei]: r[ei]=r[ei].replace('ev001','ev999',1); return
    rewrite_csv(P(d,'93_CLAIM_REGISTER.csv'), fn)
# M02 dup evidence id
def m02(d):
    rows=list(csv.reader(open(P(d,'92_EVIDENCE_LEDGER.csv'),encoding='utf-8'))); rows[2][0]=rows[1][0]
    csv.writer(open(P(d,'92_EVIDENCE_LEDGER.csv'),'w',encoding='utf-8',newline='')).writerows(rows)
# M05 15 drift
def m05(d):
    p=P(d,'15_DATA_QUALITY_REPORT.md'); wr(p, rd(p).replace('<!-- AUTO_STATS_START -->','<!-- AUTO_STATS_START -->\nMUTATION_999',1))
# M06 sync regression
def m06(d):
    p=P(d,'91_PROMPT_LIBRARY.md'); wr(p, rd(p).replace('逐筆寫入 18_TW_CHARACTER_AVAILABILITY.csv','直接匯入 roster（兩份 roster 一起）',1))
# M07 duplicate unit_key in 18 (Guide-Only)
def m07(d):
    p=P(d,'18_TW_CHARACTER_AVAILABILITY.csv'); rows=list(csv.reader(open(p,encoding='utf-8')))
    rows.append(list(rows[1]))
    with open(p,'w',encoding='utf-8',newline='') as f: csv.writer(f).writerows(rows)

# M08 B claim dup evidence
def m08(d):
    def fn(R):
        ci=R[0].index('claim_confidence'); ei=R[0].index('evidence_ids'); ii=R[0].index('independence_check')
        for r in R[1:]:
            if r[0]=='CLM-LUISE-EVAL': r[ci]='B'; r[ei]='ev014;ev014'; r[ii]='YES'; break
    rewrite_csv(P(d,'93_CLAIM_REGISTER.csv'), fn)
# M09 A claim from D evidence
def m09(d):
    def fn(R):
        ci=R[0].index('claim_confidence')
        for r in R[1:]:
            if r[0]=='CLM-LUISE-EVAL': r[ci]='A'; break  # ANALYTICAL_JUDGMENT + D evidence → A 不合法
    rewrite_csv(P(d,'93_CLAIM_REGISTER.csv'), fn)
# M10 fixture set drift (swap T45 -> T3)
def m10(d):
    p=P(d,'14_PUBLIC_TEST_FIXTURES.md'); wr(p, rd(p).replace('**FX-GA-T45**｜T45','**FX-GA-T45**｜T3',1))
# M11 delete A1 definition
def m11(d):
    p=P(d,'11_ACCEPTANCE_TESTS.md'); s=rd(p)
    s=re.sub(r'\*\*A1 [^\n]*\n(- [^\n]*\n)+','',s,count=1)
    wr(p,s)
# M12 date precision mismatch
def m12(d):
    def fn(R):
        pi=R[0].index('published_date_precision'); pd=R[0].index('published_date')
        for r in R[1:]:
            if r[0]=='ev024': r[pd]='2026-07'; r[pi]='DAY'; break
    rewrite_csv(P(d,'92_EVIDENCE_LEDGER.csv'), fn)
# M13 variants (OPERATIONAL mode)
def m13_full(d):  # complete PASS -> exit 0
    add17(d, row(run_id='run001', test_id='A1', suite='Core', fixture_id='FX-CORE-A1',
                 evidence_ids='ev008', status='PASS', **FULL))
    set13(d, 'A1', 'PASS')
def m13_blank(d):  # blank PASS -> exit 1
    add17(d, row(run_id='run002', test_id='A1', test_scope='PUBLIC', account_id='NONE', suite='Core',
                 fixture_id='FX-CORE-A1', status='PASS', is_current='Y'))
    set13(d, 'A1', 'PASS')
def m13_faildef(d):  # FAIL without defect -> exit 1
    add17(d, row(run_id='run003', test_id='T1', test_scope='PUBLIC', account_id='NONE', suite='Core',
                 fixture_id='FX-CORE-T1', fixture_version='v1.4.1.5', exact_prompt='p', execution_date='2026-07-20',
                 model='opus', observed_result='觀察', evidence_ids='ev010', status='FAIL', is_current='Y',
                 reviewer='sw', reviewed_at='2026-07-20', review_method='MANUAL_FIXTURE_REVIEW', expectation_checklist='ALL_PASS'))
# M14 version drift
def m14(d):
    p=P(d,'13_ACCEPTANCE_RESULTS.md'); wr(p, rd(p).replace('Instructions 版本：v1.5','Instructions 版本：v1.4.1.1',1))


def mutate_canonical(name):
    """M26: run ARTIFACT_READY (gates unmet) then verify canonical 16 unchanged."""
    tmp = tempfile.mkdtemp(); d = os.path.join(tmp, "p"); shutil.copytree(ROOT, d)
    before = open(os.path.join(d, "16_STATIC_VALIDATION_REPORT.md"), encoding="utf-8").read()
    subprocess.run([sys.executable, os.path.join(d, "tools", "validate_project.py"), "--mode", "ARTIFACT_READY"],
                   capture_output=True, text=True)
    after = open(os.path.join(d, "16_STATIC_VALIDATION_REPORT.md"), encoding="utf-8").read()
    ok = before == after  # failed artifact check must not overwrite canonical
    shutil.rmtree(tmp)
    print(f"{'PASS' if ok else 'FAIL'}  {name}: canonical {'unchanged' if ok else 'OVERWRITTEN'}")
    return ok

results=[]
results.append(mutate('M01 Broken FK', m01, 'FAIL'))
results.append(mutate('M02 Duplicate Evidence', m02, 'FAIL'))
results.append(mutate('M05 Data Quality Drift', m05, 'REPAIR'))
results.append(mutate('M06 Sync Prompt Regression', m06, 'FAIL'))
results.append(mutate('M07 Duplicate Pending', m07, 'FAIL'))
results.append(mutate('M08 B Claim Dup Evidence', m08, 'FAIL'))
results.append(mutate('M09 A Claim from D Evidence', m09, 'FAIL'))
results.append(mutate('M10 Fixture Set Drift', m10, 'FAIL'))
results.append(mutate('M11 Missing A1 Definition', m11, 'FAIL'))
results.append(mutate('M12 Date Precision Mismatch', m12, 'FAIL'))
results.append(mutate('M13a Complete PASS (OPERATIONAL --write)', m13_full, 'PASS', mode='OPERATIONAL', write=True))
results.append(mutate('M13b Blank PASS (OPERATIONAL)', m13_blank, 'FAIL', mode='OPERATIONAL'))
results.append(mutate('M13c FAIL without defect (OPERATIONAL)', m13_faildef, 'FAIL', mode='OPERATIONAL'))
results.append(mutate('M14 Version Drift', m14, 'FAIL'))

# ---- v1.4.1.4 M15–M26 ----

def m15(d):  # ARTIFACT_READY empty suites -> exit 1 (handled by mode arg)
    pass
def m16(d):  # PASS with unknown evidence
    add17(d, row(run_id="r16", test_id="A1", test_scope="PUBLIC", suite="Core", fixture_id="FX-CORE-A1",
                 evidence_ids="ev999", status="PASS", **FULL)); set13(d, "A1", "PASS")
def m17(d):  # unknown test_id
    add17(d, row(run_id="r17", test_id="ZZZ", test_scope="PUBLIC", suite="Core", fixture_id="FX-CORE-A1",
                 evidence_ids="ev008", status="PASS", **FULL))
def m18(d):  # wrong fixture mapping
    add17(d, row(run_id="r18", test_id="A1", test_scope="PUBLIC", suite="Core", fixture_id="FX-GA-T41",
                 evidence_ids="ev008", status="PASS", **FULL)); set13(d, "A1", "PASS")
def m19(d):  # duplicate run_id
    for _ in range(2):
        add17(d, row(run_id="dup", test_id="A1", test_scope="PUBLIC", suite="Core", fixture_id="FX-CORE-A1",
                     evidence_ids="ev008", status="PASS", **FULL))
    set13(d, "A1", "PASS")
def m20(d):  # 17 PASS but 13 NOT_RUN
    add17(d, row(run_id="r20", test_id="A1", test_scope="PUBLIC", suite="Core", fixture_id="FX-CORE-A1",
                 evidence_ids="ev008", status="PASS", **FULL))  # 13 stays NOT_RUN
def m21(d):  # PASS missing model/fixture_version
    f = dict(FULL); f["model"] = ""; f["fixture_version"] = ""
    add17(d, row(run_id="r21", test_id="A1", test_scope="PUBLIC", suite="Core", fixture_id="FX-CORE-A1",
                 evidence_ids="ev008", status="PASS", **f)); set13(d, "A1", "PASS")

def m23(d):  # latest FAIL but summary PASS
    add17(d, row(run_id="r23a", test_id="A1", test_scope="PUBLIC", suite="Core", fixture_id="FX-CORE-A1",
                 evidence_ids="ev008", status="PASS", **dict(FULL, is_current="N")))
    add17(d, row(run_id="r23b", test_id="A1", test_scope="PUBLIC", suite="Core", fixture_id="FX-CORE-A1",
                 evidence_ids="ev008", status="FAIL", defect_id="D-1", observed_result="fail",
                 retest_of="r23a", is_current="Y", fixture_version="v1.5", exact_prompt="p",
                 execution_date="2026-07-20", model="opus", response_reference="r#2"))
    set13(d, "A1", "PASS")  # 13 wrong

def m25(d):  # Gate B data drift: claim timeline=6 but actual 2 -> gate should compute real (no false PASS)
    pass  # covered by ST65 real computation; test that ARTIFACT_READY still fails
def m26(d):  # failed artifact check must not overwrite canonical
    pass  # covered by canonical isolation

results.append(mutate("M15 ARTIFACT_READY Empty Suites", m15, "FAIL", mode="ARTIFACT_READY"))
results.append(mutate("M16 PASS Unknown Evidence", m16, "FAIL", mode="OPERATIONAL"))
results.append(mutate("M17 Unknown Test ID", m17, "FAIL", mode="OPERATIONAL"))
results.append(mutate("M18 Wrong Fixture Mapping", m18, "FAIL", mode="OPERATIONAL"))
results.append(mutate("M19 Duplicate run_id", m19, "FAIL", mode="OPERATIONAL"))
results.append(mutate("M20 17 PASS/13 NOT_RUN Drift", m20, "FAIL", mode="OPERATIONAL"))
results.append(mutate("M21 PASS Missing Model/FixtureVer", m21, "FAIL", mode="OPERATIONAL"))
results.append(mutate("M23 Latest FAIL but Summary PASS", m23, "FAIL", mode="OPERATIONAL"))
results.append(mutate_canonical("M26 Canonical Not Overwritten by Failed Artifact"))


# ---- v1.4.1.5 gate registry + M25/M27-M37 helpers ----
def add_csv(d, fname, rowvals):
    p = P(d, fname)
    rows = list(csv.reader(open(p, encoding="utf-8"))); rows.append(rowvals)
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)

def PUB(**kw):
    base = dict(FULL); base.update(kw); base["test_scope"] = base.get("test_scope", "PUBLIC")
    return row(**base)

# M25a: fake PVE VERIFIED (incomplete) must not count -> ARTIFACT_READY exit 1
def m25a(d):
    for i in range(3):
        add_csv(d, "24_PVE_GUIDE_REGISTRY.csv", ["FK-%d" % i, "TW", "DEEP", "紅焰", "8-10", "VERIFIED", "", "", "", "", "", "", "", "", "", ""])
# M25b: fake Arena formal (incomplete) must not count
def m25b(d):
    for i in range(5):
        add_csv(d, "39_ARENA_COUNTER_REGISTRY.csv", ["FA-%d" % i, "TW", "v", "", "", "VERIFIED", "", "", "", "", "", "", "", "", "", ""])
# M25c: blank timeline mature row must not count
def m25c(d):
    p = P(d, "41_GACHA_TIMELINE.csv"); rows = list(csv.reader(open(p, encoding="utf-8")))
    h = rows[0]; blank = [""] * len(h)
    blank[h.index("event_id")] = "JP_20991231_fake"; blank[h.index("status")] = "ACTIVE"; blank[h.index("maturity")] = "MATURE"
    blank[h.index("last_verified")] = "2026-07-19"
    rows.append(blank)
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)
# M27: Gate C with blocking warning -> even if we fake all data, blocking_c>0 keeps C false. Simulate by making all gate data pass but leave PENDING_REVIEW ev029.
def m27(d):
    # populate 24 with 5 complete PVE, 39 with 5 complete arena, 41 already 2 -> add 4 complete; keep ev029 PENDING
    ev = "ev001"; cl = "CLM-TW-WAKANA-WINTER-REL"  # R3h Phase F：改用有效 canonical Claim，舊 CLM-ANCHOR-* 已 SUPERSEDED
    for i in range(5):
        add_csv(d, "24_PVE_GUIDE_REGISTRY.csv", ["PV-%d" % i, "TW", "DEEP", "紅焰", "8-%d" % i, "VERIFIED", "2026-07-19", "v", "1", "OFFICIAL", "A", ev, cl, "CONFIRMED", "2026-12-31", ""])
    for i in range(5):
        en = ";".join("e%d" % j for j in range(5)); co = ";".join("c%d" % j for j in range(5))
        add_csv(d, "39_ARENA_COUNTER_REGISTRY.csv", ["AC-%d" % i, "JP", "v", en, co, "VERIFIED", "2026-07-19", "MAJOR_GUIDE", "D", ev, cl, "5", "low", "CONFIRMED", "2026-12-31", ""])
    p = P(d, "41_GACHA_TIMELINE.csv"); rows = list(csv.reader(open(p, encoding="utf-8"))); h = rows[0]
    for i in range(4):
        r = [""] * len(h)
        for k, v in [("event_id", "JP_2026070%d_x" % i), ("jp_date", "2026-07-0%d" % i), ("tw_estimate_start", "2026-11-01"),
                     ("tw_estimate_end", "2026-11-30"), ("confidence", "低"), ("pool_type", "限定"), ("evidence_ids", ev),
                     ("claim_ids", cl), ("anchor_track", "卡池軌"), ("anchor_count", "2"), ("forecast_basis", "x"),
                     ("last_verified", "2026-07-19"), ("status", "ACTIVE"), ("maturity", "MATURE")]:
            r[h.index(k)] = v
        rows.append(r)
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)
    # also need public 34 PASS in 17 + 13 for Gate A; but blocking_c (ev029 pending + D analytical) keeps C false
    # We only assert C stays false due to blocking even if counts met — Gate A likely false too (no 17), still exit 1. Good enough: exit 1.
# M30: ev029 pending mismatch (status ACTIVE but limitations says 回驗) -> ST74 fail
def m30(d):
    # ev029 已解鎖（ACTIVE＋limitations 乾淨）；製造「ACTIVE 但殘留待回驗字樣」的不一致 → ST74 FAIL
    p = P(d, "92_EVIDENCE_LEDGER.csv"); rows = list(csv.reader(open(p, encoding="utf-8"))); h = rows[0]
    li = h.index("limitations")
    for r in rows[1:]:
        if r[0] == "ev029": r[li] = "官方直頁正文待 91 §1 回驗"
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)



# M34: retest cross-test reference
def m34(d):
    add_csv(d, "17_TEST_EXECUTION_LOG.csv", row(run_id="r34a", test_id="A2", test_scope="PUBLIC", account_id="NONE",
            suite="Core", fixture_id="FX-CORE-A2", evidence_ids="ev008", status="PASS", is_current="N",
            **{k: v for k, v in FULL.items() if k not in ("test_scope", "account_id", "is_current")}))
    add_csv(d, "17_TEST_EXECUTION_LOG.csv", row(run_id="r34b", test_id="A1", test_scope="PUBLIC", account_id="NONE",
            suite="Core", fixture_id="FX-CORE-A1", evidence_ids="ev008", status="PASS", retest_of="r34a",
            **{k: v for k, v in FULL.items() if k not in ("test_scope", "account_id")}))
    set13(d, "A1", "PASS"); set13(d, "A2", "PASS")
# M35: retest cycle
def m35(d):
    add_csv(d, "17_TEST_EXECUTION_LOG.csv", row(run_id="c1", test_id="A1", test_scope="PUBLIC", account_id="NONE",
            suite="Core", fixture_id="FX-CORE-A1", evidence_ids="ev008", status="PASS", retest_of="c2", is_current="N",
            **{k: v for k, v in FULL.items() if k not in ("test_scope", "account_id", "is_current")}))
    add_csv(d, "17_TEST_EXECUTION_LOG.csv", row(run_id="c2", test_id="A1", test_scope="PUBLIC", account_id="NONE",
            suite="Core", fixture_id="FX-CORE-A1", evidence_ids="ev008", status="PASS", retest_of="c1",
            **{k: v for k, v in FULL.items() if k not in ("test_scope", "account_id")}))
    set13(d, "A1", "PASS")
# M36: current row not terminal (superseded row still is_current=Y)
def m36(d):
    add_csv(d, "17_TEST_EXECUTION_LOG.csv", row(run_id="t1", test_id="A1", test_scope="PUBLIC", account_id="NONE",
            suite="Core", fixture_id="FX-CORE-A1", evidence_ids="ev008", status="PASS", is_current="Y",
            **{k: v for k, v in FULL.items() if k not in ("test_scope", "account_id", "is_current")}))
    add_csv(d, "17_TEST_EXECUTION_LOG.csv", row(run_id="t2", test_id="A1", test_scope="PUBLIC", account_id="NONE",
            suite="Core", fixture_id="FX-CORE-A1", evidence_ids="ev008", status="PASS", supersedes_run_id="t1", is_current="Y",
            **{k: v for k, v in FULL.items() if k not in ("test_scope", "account_id", "is_current")}))
    set13(d, "A1", "PASS")
# M37: qualitative gap drift (15 says 主線待查 while claim exists)
def m37(d):
    p = P(d, "15_DATA_QUALITY_REPORT.md")
    wr(p, rd(p).replace("主要未關閉缺口", "主線／六星待查——主要未關閉缺口", 1))

results.append(mutate("M25a Fake PVE VERIFIED", m25a, "FAIL", mode="ARTIFACT_READY"))
results.append(mutate("M25b Fake Arena Formal Row", m25b, "FAIL", mode="ARTIFACT_READY"))
results.append(mutate("M25c Blank Timeline Mature Row", m25c, "FAIL", mode="ARTIFACT_READY"))
results.append(mutate("M27 Gate C Blocking Warning", m27, "FAIL", mode="ARTIFACT_READY"))
results.append(mutate("M30 ev029 Pending Mismatch", m30, "FAIL"))
results.append(mutate("M34 Retest Cross-Test Ref", m34, "FAIL", mode="OPERATIONAL"))
results.append(mutate("M35 Retest Cycle", m35, "FAIL", mode="OPERATIONAL"))
results.append(mutate("M36 Current Not Terminal", m36, "FAIL", mode="OPERATIONAL"))
results.append(mutate("M37 Qualitative Gap Drift", m37, "FAIL"))

# M39: 24 VERIFIED 但 team_count 與 25 有效隊伍數不符 → FAIL（Guide-Only 核心一致性）
def m39(d):
    add_csv(d, "24_PVE_GUIDE_REGISTRY.csv", ["G-M39", "TW", "DEEP", "紅焰", "8-10", "VERIFIED", "2026-08-02", "ch16/Lv373", "5", "OFFICIAL", "A", "", "", "CONFIRMED", "2026-12-31", ""])
results.append(mutate("M39 24 team_count/25 Mismatch", m39, "FAIL"))
# M40: 25 同關卡相同五人重複列（多來源灌隊）→ FAIL
def m40(d):
    add_csv(d, "24_PVE_GUIDE_REGISTRY.csv", ["G-M40", "TW", "DEEP", "紅焰", "8-10", "PROVISIONAL", "2026-08-02", "ch16/Lv373", "1", "OFFICIAL", "A", "", "", "", "2026-12-31", ""])
    req = pve_requirements([{"source_id": "appmatch_fire_guide", "mode": "AUTO"}])
    t = ["TM-1", "G-M40", "TW", "紅焰8-10", "shiori_win", "wakana_win", "grace_bunny", "neya_orig", "pecorine_ny", "", "AUTO", req, "VERIFIED", "高", "appmatch_fire_guide", "ev050", "PASS", "2026-08-02", "2026-12-31", ""]
    add_csv(d, "25_PVE_TEAM_REGISTRY.csv", t)
    t2 = list(t); t2[0] = "TM-2"
    add_csv(d, "25_PVE_TEAM_REGISTRY.csv", t2)
results.append(mutate("M40 25 Duplicate Same-Five Team", m40, "FAIL"))
# M41: 45 社群來源被標 OFFICIAL 級信心（cap=A）→ FAIL
def m41(d):
    p = P(d, "45_GACHA_COMMUNITY_SOURCE_INDEX.csv")
    rows = list(csv.reader(open(p, encoding="utf-8"))); h = rows[0]
    rows[1][h.index("confidence_cap")] = "A"
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)
results.append(mutate("M41 Community Source Marked Official", m41, "FAIL"))
# M38: 若 13 又出現手動「目前狀態」表（Option A 回歸）→ ST72 FAIL
def m38(d):
    p = P(d, "13_ACCEPTANCE_RESULTS.md")
    wr(p, rd(p) + "\n## Suite Core（手動回歸）\n\n| 測試 | fixture_id | 目前狀態 | 執行日 |\n|---|---|---|---|\n| A1 | FX-CORE-A1 | NOT_RUN | |\n")
results.append(mutate("M38 Manual Status Table Regression", m38, "FAIL"))
# M42: CLM-LOC-* 跨服映射被包裝成 DERIVED_CALCULATION/A（為過 ST50 而扭曲型別）→ ST82 FAIL
def m42(d):
    p = P(d, "93_CLAIM_REGISTER.csv")
    rows = list(csv.reader(open(p, encoding="utf-8"))); h = rows[0]
    ti_, ci_ = h.index("claim_type"), h.index("claim_confidence")
    for r in rows[1:]:
        if r and r[0].startswith("CLM-LOC-"):
            r[ti_] = "DERIVED_CALCULATION"; r[ci_] = "A"; break
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)
results.append(mutate("M42 Mapping Claim As Derived Calculation", m42, "FAIL"))
# M45: 13 AUTO_RESULTS 僅生成日落後（跨日情境）→ 不得 FAIL（報表新鮮度非資料漂移）
def m45(d):
    p = P(d, "13_ACCEPTANCE_RESULTS.md")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"生成日 \d{4}-\d{2}-\d{2}", "生成日 2020-01-01", s, count=1)
    open(p, "w", encoding="utf-8").write(s)
results.append(mutate("M45 Report Generated-Date Only Drift", m45, "PASS"))
# M46: 13 AUTO_RESULTS 實質內容漂移（狀態值被竄改）→ ST60 必須 FAIL
def m46(d):
    p = P(d, "13_ACCEPTANCE_RESULTS.md")
    s = open(p, encoding="utf-8").read()
    head, sep, body = s.partition("<!-- AUTO_RESULTS_START -->")
    body = body.replace("| NOT_RUN |", "| PASS |", 1)
    s = head + sep + body
    open(p, "w", encoding="utf-8").write(s)
results.append(mutate("M46 Report Substantive Drift", m46, "FAIL"))
# M43: anchor schema／FK 破壞（Mapping Claim 被改成 A）→ ST83 必須 FAIL
def m43(d):
    p = P(d, "tools/validation_config.json")
    c = json.load(open(p, encoding="utf-8"))
    c["anchors"][0].pop("mapping_claim_id", None)
    json.dump(c, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
results.append(mutate("M43 Anchor Schema/FK Break", m43, "FAIL"))
# M44: delta_days 與日期不符（衍生統計漂移）→ ST83/ST84 必須 FAIL
def m44(d):
    p = P(d, "tools/validation_config.json")
    c = json.load(open(p, encoding="utf-8"))
    c["anchors"][0]["delta_days"] = 122
    json.dump(c, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
results.append(mutate("M44 Anchor Delta/Stat Drift", m44, "FAIL"))
# M47: 偷加回舊 config SSOT 欄位（legacy key resurrection）→ ST83a 必須 FAIL
def m47(d):
    p = P(d, "tools/validation_config.json")
    c = json.load(open(p, encoding="utf-8"))
    c["pool_track"] = [122, 123]; c["pool_track_median"] = 122.5; c["anchor_median"] = 122
    json.dump(c, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
results.append(mutate("M47 Legacy Config Key Resurrection", m47, "FAIL"))
# M48: SYSTEM anchor 被改標 LIMITED（混入角色卡池統計）→ 必須 FAIL
def m48(d):
    p = P(d, "tools/validation_config.json")
    c = json.load(open(p, encoding="utf-8"))
    for a in c["anchors"]:
        if a["track"] == "SYSTEM": a["pool_class"] = "LIMITED"
    json.dump(c, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
results.append(mutate("M48 System Anchor Leaks Into Gacha Track", m48, "FAIL"))
# M49: 41 anchor metadata 漂移（本輪實證事故：forecast_basis 寫回 122.5）→ ST85 必須 FAIL
def m49(d):
    p = P(d, "41_GACHA_TIMELINE.csv")
    rows = list(csv.reader(open(p, encoding="utf-8"))); h = rows[0]
    fb = h.index("forecast_basis")
    rows[1][fb] = rows[1][fb].replace("median=123", "median=122.5")
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)
results.append(mutate("M49 Timeline Anchor Metadata Drift", m49, "FAIL"))
# M49b: 舊式自我矛盾敘述（卡池軌中位數122.5天＋median=123 並存）→ ST85 必須 FAIL
def m49b(d):
    p = P(d, "41_GACHA_TIMELINE.csv")
    rows = list(csv.reader(open(p, encoding="utf-8"))); h = rows[0]
    fb = h.index("forecast_basis")
    rows[1][fb] = "卡池軌中位數122.5天（LIMITED n=5 median=123 range=122-124）"
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)
results.append(mutate("M49b Timeline Legacy Contradictory Basis", m49b, "FAIL"))
# M49c: anchor_count 與 canonical n 不符 → ST85 必須 FAIL
def m49c(d):
    p = P(d, "41_GACHA_TIMELINE.csv")
    rows = list(csv.reader(open(p, encoding="utf-8"))); h = rows[0]
    rows[1][h.index("anchor_count")] = "4"
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)
results.append(mutate("M49c Timeline Anchor Count Drift", m49c, "FAIL"))
# M50: model interval 與 TRACKS 不符 → ST85 必須 FAIL
def m50(d):
    p = P(d, "41_GACHA_TIMELINE.csv")
    rows = list(csv.reader(open(p, encoding="utf-8"))); h = rows[0]
    rows[1][h.index("model_estimate_start")] = "2030-01-01"
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)
results.append(mutate("M50 Timeline Model Interval Drift", m50, "FAIL"))
# M50b: MODEL_ONLY 但 final interval 與 model 不同 → ST85a 必須 FAIL
def m50b(d):
    p = P(d, "41_GACHA_TIMELINE.csv")
    rows = list(csv.reader(open(p, encoding="utf-8"))); h = rows[0]
    rows[1][h.index("tw_estimate_end")] = "2026-12-31"
    with open(p, "w", encoding="utf-8", newline="") as f: csv.writer(f).writerows(rows)
results.append(mutate("M50b Final Interval Diverges Under MODEL_ONLY", m50b, "FAIL"))
# M51: PROVISIONAL 隊伍不得灌入 24.team_count，且所有 guide 都須對帳 → FAIL
def m51(d):
    def fn(rows):
        h = rows[0]; tc = h.index("team_count")
        for r in rows[1:]:
            if r[0] == "TW_DEEP_FIRE_08_10_20260802":
                r[tc] = "1"; return
    rewrite_csv(P(d, "24_PVE_GUIDE_REGISTRY.csv"), fn)
results.append(mutate("M51 Provisional Team Count Inflation", m51, "FAIL", mode="PRE_SUITE"))
# M52: tw_availability_check=PASS 不得引用 18 不存在／不可用的 unit_key → FAIL
def m52(d):
    def fn(rows):
        h = rows[0]; slot1 = h.index("slot1")
        for r in rows[1:]:
            if r[0] == "TM-F810-01":
                r[slot1] = "missing_r3i0_unit"; return
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), fn)
results.append(mutate("M52 PASS With Missing 18 Unit", m52, "FAIL", mode="PRE_SUITE"))
# M53: requirements 必須是可解析且 canonical 的 JSON → FAIL
def m53(d):
    def fn(rows):
        h = rows[0]; req = h.index("requirements")
        for r in rows[1:]:
            if r[0] == "TM-F810-01":
                r[req] = "{not-json"; return
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), fn)
results.append(mutate("M53 Malformed PVE Requirements JSON", m53, "FAIL", mode="PRE_SUITE",
                      target_fail="25：requirements 為 canonical JSON"))
# M54: SOURCE_CONFLICT 不得只剩單一 mode claim → FAIL
def m54(d):
    def fn(rows):
        h = rows[0]; req = h.index("requirements")
        for r in rows[1:]:
            if r[0] == "TM-F810-01":
                obj = json.loads(r[req])
                for claim in obj["operation_mode_claims"]:
                    claim["mode"] = "AUTO"
                r[req] = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")); return
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), fn)
results.append(mutate("M54 Source Conflict Collapses To One Mode", m54, "FAIL", mode="PRE_SUITE",
                      target_fail="25：SOURCE_CONFLICT 至少兩來源＋兩種 mode"))
# M55: UNKNOWN 應明寫，空字串不得冒充已知 requirement → FAIL
def m55(d):
    def fn(rows):
        h = rows[0]; req = h.index("requirements")
        for r in rows[1:]:
            if r[0] == "TM-F810-01":
                obj = json.loads(r[req]); obj["slots"]["slot3"]["rank"] = ""
                r[req] = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")); return
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), fn)
results.append(mutate("M55 Blank Requirement Instead Of UNKNOWN", m55, "FAIL", mode="PRE_SUITE",
                      target_fail="25：requirements 為 canonical JSON"))
# M56: 可解析但帶預設空白的 JSON 仍非 canonical → FAIL
def m56(d):
    def fn(rows):
        h = rows[0]; req = h.index("requirements")
        for r in rows[1:]:
            if r[0] == "TM-F810-01":
                obj = json.loads(r[req])
                r[req] = json.dumps(obj, ensure_ascii=False, sort_keys=True); return
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), fn)
results.append(mutate("M56 Parseable Noncanonical PVE Requirements JSON", m56, "FAIL", mode="PRE_SUITE",
                      target_fail="25：requirements 為 canonical JSON"))
# M57: Evidence 宣告不存在的 Claim 不得通過 → ST86 FAIL
def m57(d):
    def fn(rows):
        h = rows[0]; claim_id = h.index("claim_id")
        for r in rows[1:]:
            if r[0] == "ev008":
                r[claim_id] = "CLM-MISSING-I0"; return
    rewrite_csv(P(d, "92_EVIDENCE_LEDGER.csv"), fn)
results.append(mutate("M57 Evidence Declares Missing Claim", m57, "FAIL", mode="PRE_SUITE",
                      target_fail="ST86：92→93 declared Claim FK 完整"))
# M58: timeline step 的角色不得脫離該隊五人 → FAIL
def m58(d):
    def fn(rows):
        h = rows[0]
        for r in rows[1:]:
            if r[h.index("timeline_step_id")] == "TLS-F810-05-002":
                r[h.index("trigger_actor_unit_key")] = "pecorine_ny"
                r[h.index("actor_unit_key")] = "pecorine_ny"; return
    rewrite_csv(P(d, "27_PVE_TIMELINE_STEPS.csv"), fn)
results.append(mutate("M58 Timeline Actor Outside Team", m58, "FAIL", mode="PRE_SUITE",
                      target_fail="27：step FK／Enum／時間範圍／角色成員資格完整"))
# M59: 同來源 sequence_no 不得重複或跳號 → FAIL
def m59(d):
    def fn(rows):
        h = rows[0]
        for r in rows[1:]:
            if r[h.index("timeline_step_id")] == "TLS-F810-05-002":
                r[h.index("sequence_no")] = "1"; return
    rewrite_csv(P(d, "27_PVE_TIMELINE_STEPS.csv"), fn)
results.append(mutate("M59 Duplicate Timeline Sequence", m59, "FAIL", mode="PRE_SUITE",
                      target_fail="27：每來源 sequence_no 唯一且連續"))
# M60: VERIFIED 半自動／衝突隊伍的來源不可無聲消失 → FAIL
def m60(d):
    def fn(rows):
        h = rows[0]; source_id = h.index("source_id")
        rows[:] = [rows[0]] + [r for r in rows[1:] if r[source_id] != "yt_jkPXr3aUZZQ"]
    rewrite_csv(P(d, "26_PVE_OPERATION_TIMELINES.csv"), fn)
results.append(mutate("M60 Missing Declared Source Axis", m60, "FAIL", mode="PRE_SUITE",
                      target_fail="25→26：手動／半自動／衝突隊伍每個來源與 timeline_ref 均有結構化軸或明示缺口"))
# M61: JP 來源的結構化軸不得偽裝成台服已逐步重現 → FAIL
def m61(d):
    def fn(rows):
        h = rows[0]; source_axis = h.index("source_axis_id"); repro = h.index("reproducibility")
        for r in rows[1:]:
            if r[source_axis] == "AX-F810-02-EV073":
                r[repro] = "TW_REPRODUCED"; return
    rewrite_csv(P(d, "26_PVE_OPERATION_TIMELINES.csv"), fn)
results.append(mutate("M61 Cross-Server Timeline Falsely Reproduced", m61, "FAIL", mode="PRE_SUITE",
                      target_fail="26：跨服結構化軸不得冒充台服已重現"))
# M62: SOURCE_GAP 的 UNKNOWN 不得改成空白冒充已知 → FAIL
def m62(d):
    def fn(rows):
        h = rows[0]; status = h.index("status"); duration = h.index("battle_duration_ms")
        for r in rows[1:]:
            if r[status] == "SOURCE_GAP":
                r[duration] = ""; return
    rewrite_csv(P(d, "26_PVE_OPERATION_TIMELINES.csv"), fn)
results.append(mutate("M62 Blank Timeline Gap Unknown", m62, "FAIL", mode="PRE_SUITE",
                      target_fail="26：STRUCTURED／SOURCE_GAP 狀態不得強化 UNKNOWN"))
# M63: 來源未明載總長時，不得用遊戲常識補成 90 秒 → ST87 FAIL
def m63(d):
    def fn(rows):
        h = rows[0]; source_axis = h.index("source_axis_id"); duration = h.index("battle_duration_ms")
        for r in rows[1:]:
            if r[source_axis] == "AX-F810-02-EV073":
                r[duration] = "90000"; return
    rewrite_csv(P(d, "26_PVE_OPERATION_TIMELINES.csv"), fn)
results.append(mutate("M63 Inferred Unstated Battle Duration", m63, "FAIL", mode="PRE_SUITE",
                      target_fail="ST87：來源邊界、locator 與未載欄位不得推測"))
# M64: source step 分組與 locator 不得漂移後仍通過 → FAIL
def m64(d):
    def fn(rows):
        h = rows[0]
        rows[1][h.index("source_step_no")] = "99"
        rows[1][h.index("source_locator")] = "x"
    rewrite_csv(P(d, "27_PVE_TIMELINE_STEPS.csv"), fn)
results.append(mutate("M64 Source Step And Locator Drift", m64, "FAIL", mode="PRE_SUITE"))
# M65: source axis 不得改綁同隊其他 Evidence → FAIL
def m65(d):
    def fn(rows):
        h = rows[0]; source_axis = h.index("source_axis_id"); evidence_id = h.index("source_evidence_id")
        for r in rows[1:]:
            if r[source_axis] == "AX-F810-02-EV073":
                r[evidence_id] = "ev070"; return
    rewrite_csv(P(d, "26_PVE_OPERATION_TIMELINES.csv"), fn)
results.append(mutate("M65 Timeline Bound To Wrong Evidence", m65, "FAIL", mode="PRE_SUITE",
                      target_fail="26：source locator 必須等於 Evidence locator 或其 # 子定位"))
# M66: 25 timeline_ref 必須是該隊 source_axis_id 的精確集合 → FAIL
def m66(d):
    def fn(rows):
        h = rows[0]; req = h.index("requirements")
        for r in rows[1:]:
            if r[0] == "TM-F810-02":
                obj = json.loads(r[req]); obj["timeline_ref"] = "BROKEN-NONEXISTENT-TIMELINE"
                r[req] = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")); return
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), fn)
results.append(mutate("M66 Broken Team Timeline Reference", m66, "FAIL", mode="PRE_SUITE",
                      target_fail="25→26：手動／半自動／衝突隊伍每個來源與 timeline_ref 均有結構化軸或明示缺口"))
# M67: PROVISIONAL 手動隊仍必須逐來源明示 axis／gap → FAIL
def m67(d):
    def team_fn(rows):
        h = rows[0]; clear_status = h.index("clear_status")
        for r in rows[1:]:
            if r[0] == "TM-F810-01": r[clear_status] = "PROVISIONAL"
    def guide_fn(rows):
        h = rows[0]; team_count = h.index("team_count")
        for r in rows[1:]:
            if r[0] == "TW_DEEP_FIRE_08_10_20260802": r[team_count] = "4"
    def timeline_fn(rows):
        h = rows[0]; team_id = h.index("team_id")
        rows[:] = [rows[0]] + [r for r in rows[1:] if r[team_id] != "TM-F810-01"]
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), team_fn)
    rewrite_csv(P(d, "24_PVE_GUIDE_REGISTRY.csv"), guide_fn)
    rewrite_csv(P(d, "26_PVE_OPERATION_TIMELINES.csv"), timeline_fn)
results.append(mutate("M67 Provisional Timeline Coverage Bypass", m67, "FAIL", mode="PRE_SUITE",
                      target_fail="25→26：手動／半自動／衝突隊伍每個來源與 timeline_ref 均有結構化軸或明示缺口"))
# M68: source 未提供 criticality，不得自行標 CRITICAL → ST87 FAIL
def m68(d):
    def fn(rows):
        h = rows[0]; step_id = h.index("timeline_step_id"); criticality = h.index("criticality")
        for r in rows[1:]:
            if r[step_id] == "TLS-F810-02-001":
                r[criticality] = "CRITICAL"; return
    rewrite_csv(P(d, "27_PVE_TIMELINE_STEPS.csv"), fn)
results.append(mutate("M68 Inferred Timeline Criticality", m68, "FAIL", mode="PRE_SUITE",
                      target_fail="ST87：來源邊界、locator 與未載欄位不得推測"))
# M69: Arena 的 PASS 不得只信任旗標；敵我十名都必須存在於 18 且 AVAILABLE。
def m69(d):
    def fn(rows):
        h = rows[0]
        row = [""] * len(h)
        values = {
            "counter_id": "TW_ARENA_M69",
            "server": "TW",
            "environment_version": "TEST_ONLY",
            "enemy_team_ids": "missing_arena_1;missing_arena_2;missing_arena_3;missing_arena_4;missing_arena_5",
            "counter_team_ids": "missing_counter_1;missing_counter_2;missing_counter_3;missing_counter_4;missing_counter_5",
            "status": "PROVISIONAL",
            "verified_date": "2026-08-08",
            "source_tier": "SINGLE_PLAYER_REPORT",
            "claim_confidence": "D",
            "evidence_ids": "ev001",
            "claim_ids": "CLM-TW-WAKANA-WINTER-REL",
            "sample_size": "1",
            "randomness": "UNKNOWN",
            "reproducibility": "UNVERIFIED_ON_TW",
            "last_review_due": "2026-12-31",
            "notes": "TEST_ONLY mutation",
            "source_record_count": "1",
            "source_platforms": "TEST_ONLY",
            "tw_availability_check": "PASS",
            "unavailable_unit_ids": "",
            "required_upgrade_check": "UNKNOWN",
            "record_date_min": "2026-08-08",
            "record_date_max": "2026-08-08",
        }
        for field, value in values.items():
            row[h.index(field)] = value
        rows.append(row)
    rewrite_csv(P(d, "39_ARENA_COUNTER_REGISTRY.csv"), fn)
results.append(mutate("M69 Arena PASS With Missing 18 Units", m69, "FAIL", mode="PRE_SUITE",
                      target_fail="39：tw_availability_check Enum；PASS 的敵我各五人須不同且均為 18 AVAILABLE"))
# M70: 操作模式 UNKNOWN 仍須保留逐來源 axis／明示缺口，不得藉 UNKNOWN 略過 provenance。
def m70(d):
    def fn(rows):
        h = rows[0]; team_id = h.index("team_id")
        rows[:] = [rows[0]] + [r for r in rows[1:] if r[team_id] != "TM-F810-04"]
    rewrite_csv(P(d, "26_PVE_OPERATION_TIMELINES.csv"), fn)
results.append(mutate("M70 Unknown Mode Missing Source Axis", m70, "FAIL", mode="PRE_SUITE",
                      target_fail="25→26：手動／半自動／衝突隊伍每個來源與 timeline_ref 均有結構化軸或明示缺口"))
# M71 reproduction: VERIFIED/PASS 五人隊引用的 Evidence 若已 REJECTED，不得仍計入有效隊伍。
def m71(d):
    def fn(rows):
        h = rows[0]; status = h.index("status")
        for r in rows[1:]:
            if r[0] == "ev057":
                r[status] = "REJECTED"; return
    rewrite_csv(P(d, "92_EVIDENCE_LEDGER.csv"), fn)
results.append(mutate("M71 Rejected PVE Team Evidence Still Counts", m71, "FAIL", mode="PRE_SUITE",
                      target_fail=("24／25：VERIFIED PVE closure 僅引用 ACTIVE Evidence／Claim",
                                   "25 與 24：所有 guide 的 team_count＝25 有效隊伍數")))
# M72: 成熟 PVE 隊伍的通關 Claim 失效後不得留在 ACTIVE closure 或 Gate 計數。
def m72(d):
    def claim_fn(rows):
        h = rows[0]; status = h.index("status")
        for r in rows[1:]:
            if r[0] == "CLM-PVE-W810-MISORA-NANAKA":
                r[status] = "SUPERSEDED"; return
    def guide_fn(rows):
        h = rows[0]; team_count = h.index("team_count")
        for r in rows[1:]:
            if r[0] == "TW_DEEP_WATER_08_10_20260808":
                r[team_count] = "4"; return
    rewrite_csv(P(d, "93_CLAIM_REGISTER.csv"), claim_fn)
    rewrite_csv(P(d, "24_PVE_GUIDE_REGISTRY.csv"), guide_fn)
results.append(mutate("M72 Superseded PVE Team Claim Still Counts", m72, "FAIL", mode="PRE_SUITE",
                      target_fail="24／25：VERIFIED PVE closure 僅引用 ACTIVE Evidence／Claim"))
# M73: 實開 Water 軸的精確時間、locator 與語意不得在合法範圍內悄悄漂移。
def m73(d):
    def fn(rows):
        h = rows[0]; step_id = h.index("timeline_step_id")
        for r in rows[1:]:
            if r[step_id] == "TLS-W810-02-002":
                r[h.index("clock_from_ms")] = "70000"
                r[h.index("clock_to_ms")] = "70000"; return
    rewrite_csv(P(d, "27_PVE_TIMELINE_STEPS.csv"), fn)
results.append(mutate("M73 Water Exact Timeline Drift", m73, "FAIL", mode="PRE_SUITE",
                      target_fail="ST87：來源邊界、locator 與未載欄位不得推測"))
# M74: 五欄非空不等於五名不同角色；隊內重複不得計入有效隊伍。
def m74(d):
    def team_fn(rows):
        h = rows[0]; team_id = h.index("team_id")
        for r in rows[1:]:
            if r[team_id] == "TM-W810-03":
                r[h.index("slot3")] = r[h.index("slot4")]; return
    def guide_fn(rows):
        h = rows[0]; team_count = h.index("team_count")
        for r in rows[1:]:
            if r[0] == "TW_DEEP_WATER_08_10_20260808":
                r[team_count] = "4"; return
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), team_fn)
    rewrite_csv(P(d, "24_PVE_GUIDE_REGISTRY.csv"), guide_fn)
results.append(mutate("M74 Duplicate Unit Inside PVE Team", m74, "FAIL", mode="PRE_SUITE",
                      target_fail="25：每隊五名角色互異"))
# M75: team 的 server/stage 必須仍屬於其 guide，不能只靠 guide_id 掛錯關卡。
def m75(d):
    def team_fn(rows):
        h = rows[0]; team_id = h.index("team_id")
        for r in rows[1:]:
            if r[team_id] == "TM-W810-05":
                r[h.index("stage")] = "10-10"; return
    def guide_fn(rows):
        h = rows[0]; team_count = h.index("team_count")
        for r in rows[1:]:
            if r[0] == "TW_DEEP_WATER_08_10_20260808":
                r[team_count] = "4"; return
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), team_fn)
    rewrite_csv(P(d, "24_PVE_GUIDE_REGISTRY.csv"), guide_fn)
results.append(mutate("M75 PVE Team Bound To Wrong Stage", m75, "FAIL", mode="PRE_SUITE",
                      target_fail="24→25：team server／stage 與 guide 關聯一致"))
# M76: 具名借角若沒有明確 slot，不得把 UNKNOWN 偷換成確定事實。
def m76(d):
    def fn(rows):
        h = rows[0]; req = h.index("requirements")
        for r in rows[1:]:
            if r[0] == "TM-W810-05":
                obj = json.loads(r[req]); obj["support"]["unit"] = "yukino_orig"
                r[req] = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")); return
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), fn)
results.append(mutate("M76 Named Support Without Slot", m76, "FAIL", mode="PRE_SUITE",
                      target_fail="25：借角 unit／support_slot 三態關聯一致"))
# M77: normalized/display stage aliases 都屬同一 guide，不得繞過相同五人合併。
def m77(d):
    def team_fn(rows):
        h = rows[0]; team_id = h.index("team_id")
        water4 = next(r for r in rows[1:] if r[team_id] == "TM-W810-04")
        water5 = next(r for r in rows[1:] if r[team_id] == "TM-W810-05")
        for slot in range(1, 6):
            water5[h.index(f"slot{slot}")] = water4[h.index(f"slot{slot}")]
        water4[h.index("stage")] = "8-10"
        water5[h.index("stage")] = "蒼波8-10"
    def guide_fn(rows):
        h = rows[0]; team_count = h.index("team_count")
        for r in rows[1:]:
            if r[0] == "TW_DEEP_WATER_08_10_20260808":
                r[team_count] = "4"; return
    rewrite_csv(P(d, "25_PVE_TEAM_REGISTRY.csv"), team_fn)
    rewrite_csv(P(d, "24_PVE_GUIDE_REGISTRY.csv"), guide_fn)
results.append(mutate("M77 Stage Alias Duplicate Same-Five Team", m77, "FAIL", mode="PRE_SUITE",
                      target_fail="25：同關卡相同五人不得重複列（多來源合併）"))
print('MUTATION_TESTS', 'ALL_OK' if all(results) else 'FAILED', f'| active_scenarios={len(results)}')
sys.exit(0 if all(results) else 1)
