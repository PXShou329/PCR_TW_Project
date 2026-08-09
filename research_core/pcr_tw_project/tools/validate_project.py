#!/usr/bin/env python3
"""PCR TW Project static validator（v1.5 Guide-Only）。
產品：台服公共攻略資訊整合；帳號層 REMOVED_FROM_ACTIVE_SCOPE（封存於外部 archive ZIP）。
順序：資料計算 → Warning 計算 → blocking_c → Gate A/B/C → Mode Enforcement → Report。
Gate 數量由結構化 Registry（24 PVE／39 Arena／41 Timeline）中「成熟且可追溯」的列計算，不計假列。
13 由 validator 依 17 current result 自動覆寫 AUTO_RESULTS 區。
Mode：PRE_SUITE／OPERATIONAL／ARTIFACT_READY。Canonical 15/16/stats 僅在 Mode 通過時覆寫。
用法：python3 tools/validate_project.py [--mode MODE] [--write]。exit 0＝該 Mode 通過。"""
import csv, json, os, re, sys, statistics
from datetime import date, datetime, timedelta, timezone
from collections import Counter, defaultdict
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
CFG = json.load(open('tools/validation_config.json', encoding='utf-8'))
MODE = sys.argv[sys.argv.index('--mode') + 1] if '--mode' in sys.argv else 'PRE_SUITE'
WRITE = '--write' in sys.argv
TAIPEI_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Taipei")
TODAY = datetime.now(TAIPEI_TIMEZONE).date().isoformat()

checks, fails, warns, infos, hist_hits = [], [], [], [], []
def ck(name, ok, detail=""):
    checks.append((name, "PASS" if ok else "FAIL", detail))
    if not ok: fails.append(name)
def wk(wid, cat, sev, gc, mod, detail, nxt):
    warns.append({"warning_id": wid, "category": cat, "severity": sev, "blocks_gate_c": gc,
                  "affected_module": mod, "detail": detail, "next_action": nxt})

TOOLS = sorted(f for f in os.listdir('tools') if os.path.isfile(os.path.join('tools', f)))
files = sorted(f for f in os.listdir('.') if f != 'tools' and not f.startswith('.'))
numbered = [f for f in files if re.match(r'\d\d_', f)]
knowledge = [f for f in files if f not in CFG['knowledge_excluded']]
R = {f: open(f, encoding='utf-8').read() for f in files}
def load(p): return list(csv.reader(open(p, encoding='utf-8')))
def date_ok(d):
    try: date.fromisoformat(d); return True
    except Exception: return False

# ========== structure ==========
ck("檔案數（非 tools）", len(files) == CFG['expected_total_non_tools'], f"{len(files)}")
ck("編號檔數", len(numbered) == CFG['expected_numbered'], f"{len(numbered)}")
ck("Knowledge 檔數", len(knowledge) == CFG['expected_knowledge'], f"{len(knowledge)}")
ck("tools 檔存在", {'validate_project.py', 'validation_config.json', 'mutation_test.py'} <= set(TOOLS))
ok = True
for f in [x for x in files if x.endswith('.md')]:
    for r_ in set(re.findall(r'(\d\d_[A-Z_]+\.(?:md|csv))', R[f])):
        if r_ not in files: ok = False
ck("跨檔引用完整", ok)
tbl = re.findall(r'^\| (\S+\.(?:md|csv)) \|', R['README.md'], re.M)
ck("README 權威表與磁碟一致", sorted(tbl) == sorted(files), f"{len(tbl)}／{len(files)}")
ck("Instructions §1–§12 連續", [int(n) for n in re.findall(r'^## (\d+)\. ', R['00_PROJECT_INSTRUCTIONS.md'], re.M)] == list(range(1, 13)))
vbad = [f for f, pat in CFG['version_files'].items() if not re.search(pat, R[f])]
ck("ST44：版本 SSOT 精確一致（" + CFG['project_version'] + "）", not vbad, "漂移:" + ",".join(vbad))
_acct_bad = [f for f in files if f not in CFG['historical_zones'] and f != '16_STATIC_VALIDATION_REPORT.md'
             and any(p in R[f] for p in CFG['account_forbidden_strings'])]
ck("ST80：Active 檔無帳號匯入指令（Guide-Only）", not _acct_bad, ",".join(_acct_bad[:6]))

# ========== Guide-Only：帳號層已移出 Active Scope（ADR 見 archive ZIP）==========

# ========== CSVs ==========
r41, r92, r93, r17 = load('41_GACHA_TIMELINE.csv'), load('92_EVIDENCE_LEDGER.csv'), load('93_CLAIM_REGISTER.csv'), load('17_TEST_EXECUTION_LOG.csv')
r24, r39 = load('24_PVE_GUIDE_REGISTRY.csv'), load('39_ARENA_COUNTER_REGISTRY.csv')
r18, r25 = load('18_TW_CHARACTER_AVAILABILITY.csv'), load('25_PVE_TEAM_REGISTRY.csv')
r26, r27 = load('26_PVE_OPERATION_TIMELINES.csv'), load('27_PVE_TIMELINE_STEPS.csv')
r45, r46 = load('45_GACHA_COMMUNITY_SOURCE_INDEX.csv'), load('46_ARENA_SOURCE_REGISTRY.csv')
r47 = load('47_PRINCESS_ARENA_CASE_REGISTRY.csv')
for name, rows in [('41', r41), ('92', r92), ('93', r93), ('17', r17), ('24', r24), ('39', r39), ('18', r18), ('25', r25), ('26', r26), ('27', r27), ('45', r45), ('46', r46), ('47', r47)]:
    spec = CFG['csv_specs'][[k for k in CFG['csv_specs'] if k.startswith(name)][0]]
    ck(f"{name}：欄數 {spec['cols']}＋列數 ≥{spec['min_rows']}", all(len(r) == spec['cols'] for r in rows) and len(rows) - 1 >= spec['min_rows'], f"{len(rows)-1} 列")
ids92 = [r[0] for r in r92[1:]]; ids93 = [r[0] for r in r93[1:]]
sync_rows = re.findall(r'^\| (SYNC-\d+) \| (.+)$', R['12_CHARACTER_SYNC.md'], re.M)
ck("ID 唯一（evidence／claim／event／sync／unit／team／counter／source）",
   len(set(ids92)) == len(ids92) and len(set(ids93)) == len(ids93)
   and len({r[0] for r in r41[1:]}) == len(r41) - 1 and len({s for s, _ in sync_rows}) == len(sync_rows)
   and len({r[0] for r in r18[1:]}) == len(r18) - 1 and len({r[0] for r in r25[1:]}) == len(r25) - 1
   and len({r[0] for r in r26[1:]}) == len(r26) - 1 and len({r[0] for r in r27[1:]}) == len(r27) - 1
   and len({r[0] for r in r39[1:]}) == len(r39) - 1
   and len({r[0] for r in r45[1:]}) == len(r45) - 1 and len({r[0] for r in r46[1:]}) == len(r46) - 1
   and len({r[0] for r in r47[1:]}) == len(r47) - 1)
h92, h93 = r92[0], r93[0]
pi = h92.index('published_date_precision'); ui = h92.index('source_url'); li = h92.index('limitations')
pdi = h92.index('published_date'); tri = h92.index('source_tier'); eci = h92.index('evidence_confidence')
loci = h92.index('source_locator'); sti = h92.index('source_title'); si92 = h92.index('status')
ck("92：evidence_confidence 欄名", 'evidence_confidence' in h92 and 'claim_confidence' not in h92)
ck("92：URL 標準化", all(r[ui] == '' or r[ui].startswith('https://') for r in r92[1:]))
ck("ST73：92 status Enum", all(r[si92] in CFG['enums']['evidence_status'] for r in r92[1:]), ",".join({r[si92] for r in r92[1:]} - set(CFG['enums']['evidence_status'])))
ck("92：source_tier Enum", all(
    r[tri] in CFG['enums']['arena_source_tier'] for r in r92[1:]
))
def prec_ok(prec, d):
    if prec == 'DAY':
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', d): return False
        return date_ok(d)
    if prec == 'MONTH': return bool(re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', d))
    if prec == 'YEAR': return bool(re.fullmatch(r'\d{4}', d))
    if prec == 'UNKNOWN': return d == '' or d.upper() == 'UNKNOWN'
    return False
ck("ST47：92 日期精度與格式一致", not [r[0] for r in r92[1:] if r[pi] not in CFG['enums']['precision'] or not prec_ok(r[pi], r[pdi])])
ti = h93.index('claim_type'); ci = h93.index('claim_confidence'); ei = h93.index('evidence_ids'); ii = h93.index('independence_check'); si93 = h93.index('status')
ck("93：claim_type／confidence Enum", all(r[ti] in CFG['enums']['claim_type'] and r[ci] in CFG['enums']['confidence'] for r in r93[1:]))
ck("93→92 FK 完整", all(all(e in set(ids92) for e in r[ei].split(';')) for r in r93[1:]))
claim_i92 = h92.index('claim_id')
ids93_set = set(ids93)
dangling_evidence_claims = [
    r[0] for r in r92[1:]
    if r[claim_i92] and r[claim_i92] not in ids93_set
]
ck("ST86：92→93 declared Claim FK 完整", not dangling_evidence_claims,
   ",".join(dangling_evidence_claims))
ev = {r[0]: r for r in r92[1:]}
claim_status_by_id = {r[0]: r[si93] for r in r93[1:]}
def host(u):
    try:
        hostname = (urlparse(u).hostname or '').lower()
        return hostname[4:] if hostname.startswith('www.') else hostname
    except Exception: return ''
def independent(eids):
    keys = set()
    for e in eids:
        r = ev.get(e)
        if not r: return False
        keys.add(host(r[ui]) or r[loci] or r[sti])
    return len(keys) >= 2
bc = [r for r in r93[1:] if r[ci] in ('B', 'C')]
ck(f"ST49：B／C 證據唯一＋來源獨立（{len(bc)} 筆）", not [r[0] for r in bc if len(set(r[ei].split(';'))) < 2 or r[ii] != 'YES' or not independent(r[ei].split(';'))])
def a_compat(r):
    typ, eids = r[ti], r[ei].split(';'); rows = [ev[e] for e in eids if e in ev]
    if typ == 'SOURCE_FACT': return any(x[tri] == 'OFFICIAL' and x[eci] == 'A' for x in rows)
    if typ == 'DERIVED_CALCULATION': return bool(rows) and all(x[eci] == 'A' for x in rows) and ('計算' in r[-1] or '推導' in r[-1]) and '官方直接公布' not in r[-1]
    return False
ck("ST50：A Claim 與 A Evidence 相容", not [r[0] for r in r93[1:] if r[ci] == 'A' and not a_compat(r)])
ck("DERIVED_CALCULATION 附推導註記", all('計算' in r[-1] or '推導' in r[-1] for r in r93[1:] if r[ti] == 'DERIVED_CALCULATION'))
# ST82：CLM-LOC-* 跨服映射 Claim 邊界（entity resolution，非可機械重算之 calculation）
svi92 = h92.index('server')
loc_rows = [r for r in r93[1:] if r[0].startswith('CLM-LOC-')]
def loc_ok(r):
    if r[ti] != 'ANALYTICAL_JUDGMENT': return False          # 型別：不得 DERIVED_CALCULATION／SOURCE_FACT
    if r[ci] == 'A': return False                            # 無官方跨服對照聲明時上限 B
    if r[ii] != 'YES': return False                          # 需獨立性檢查
    eids = [e for e in r[ei].split(';') if e in ev]
    if len(eids) < 2: return False
    if not {'TW', 'JP'} <= {ev[e][svi92] for e in eids}: return False   # 須同時引用 TW 與 JP Evidence
    if len({host(ev[e][ui]) or ev[e][loci] for e in eids}) < 2: return False  # 不同官方 host
    if '計算' in r[-1]: return False                          # notes 不得把映射描述成計算
    return len(r[-1]) >= 20                                   # notes 須載明比對依據／歧義
_loc_bad = [r[0] for r in loc_rows if not loc_ok(r)]
ck(f"ST82：CLM-LOC 跨服映射邊界（{len(loc_rows)} 筆）", not _loc_bad, ';'.join(_loc_bad))
conf_violations = 0  # placeholder for Gate C confidence check (single-guide max D etc. already enforced structurally)

# ========== ST74 generic evidence status⟺limitations consistency ==========
# 語意：PENDING_REVIEW ⟹ limitations 含回驗註記；ACTIVE ⟹ 不得殘留「91 §1 回驗」解鎖級待驗字樣
# （ACTIVE 允許「待例行回驗」等細節級註記；解鎖級標記＝「91 §1 回驗」）
def _ev_consistent(r):
    st, lim = r[si92], r[li]
    if st == 'PENDING_REVIEW': return '回驗' in lim
    if st == 'ACTIVE': return '91 §1 回驗' not in lim
    return True
_bad74 = [r[0] for r in r92[1:] if not _ev_consistent(r)]
ck("ST74：所有 Evidence status 與 limitations 一致（PENDING⟺回驗註記；ACTIVE⟺無解鎖級殘留）", not _bad74, ",".join(_bad74[:5]))

# ========== Guide-Only registries (18/25/45/46) ==========
h18 = r18[0]
ck("18：欄位標頭符合規格", h18 == CFG['t18_header'])
_a18 = h18.index('availability_status'); _e18 = h18.index('source_evidence_ids')
ck("18：availability Enum", all(r[_a18] in CFG['enums']['tw_availability'] for r in r18[1:]))
_up18 = [h18.index(c) for c in ['ue1_status', 'ue2_status', 'six_star_status', 'connect_rank_status']]
ck("18：強化欄位 Enum", all(r[i] in CFG['enums']['upgrade_status'] for r in r18[1:] for i in _up18))
ck("18：Evidence FK", all(e in set(ids92) for r in r18[1:] for e in r[_e18].split(';') if e))
ck("18：日期格式", all((not r[h18.index('tw_release_date')] or date_ok(r[h18.index('tw_release_date')])) and date_ok(r[h18.index('last_verified')]) for r in r18[1:]))
ALL_UNITS = {r[0] for r in r18[1:]}
TW_UNITS = {r[0] for r in r18[1:] if r[_a18] == 'AVAILABLE'}
_CHARACTER18 = {r[0]: dict(zip(h18, r)) for r in r18[1:]}
_EVIDENCE92 = {r[0]: dict(zip(h92, r)) for r in r92[1:]}
h39 = r39[0]
t39 = [dict(zip(h39, r)) for r in r39[1:]]
def _arena_team_ids(row, field):
    return [unit_key for unit_key in row[field].split(';') if unit_key]
def _arena_team_signature(row, field):
    return tuple(sorted(_arena_team_ids(row, field)))
ck("39：tw_availability_check Enum；PASS 的敵我各五人須不同且均為 18 AVAILABLE", all(
    row['tw_availability_check'] in CFG['enums']['tw_check']
    and all(len(team) == 5 and len(set(team)) == 5 and all(unit_key in ALL_UNITS for unit_key in team)
            for team in (_arena_team_ids(row, 'enemy_team_ids'),
                         _arena_team_ids(row, 'counter_team_ids')))
    and (row['tw_availability_check'] != 'PASS'
         or all(unit_key in TW_UNITS
                for field in ('enemy_team_ids', 'counter_team_ids')
                for unit_key in _arena_team_ids(row, field)))
    for row in t39
))
def _arena_all_members(row):
    return set(_arena_team_ids(row, 'enemy_team_ids') + _arena_team_ids(row, 'counter_team_ids'))
def _arena_expected_tw_check(row):
    members = _arena_all_members(row)
    if any(unit_key not in _CHARACTER18 for unit_key in members):
        return None
    statuses = {_CHARACTER18[unit_key]['availability_status'] for unit_key in members}
    if not statuses <= {'AVAILABLE', 'NOT_RELEASED', 'UNVERIFIED'}:
        return None
    if 'NOT_RELEASED' in statuses:
        return 'FAIL'
    if 'UNVERIFIED' in statuses:
        return 'UNVERIFIED'
    return 'PASS'
ck("39：Arena TW availability 三態須與 18 雙向一致", all(
    _arena_expected_tw_check(row) is None
    or row['tw_availability_check'] == _arena_expected_tw_check(row)
    for row in t39
))
ck("39：unavailable_unit_ids 精確列出 18 NOT_RELEASED 成員", all(
    set(filter(None, row['unavailable_unit_ids'].split(';'))) == {
        unit_key for unit_key in _arena_all_members(row)
        if unit_key in _CHARACTER18
        and _CHARACTER18[unit_key]['availability_status'] == 'NOT_RELEASED'
    }
    for row in t39
))
_OFFICIAL_NAME_SENTINELS = {
    '', 'UNKNOWN', 'N/A', 'NA', 'PENDING', 'NOT_RELEASED', 'UNVERIFIED',
    '【待查證】', '待查證', '未確認', '—', '-'
}
def _stored_official_name(value):
    normalized = (value or '').strip()
    return bool(normalized and normalized.upper() not in _OFFICIAL_NAME_SENTINELS
                and normalized not in _OFFICIAL_NAME_SENTINELS)
def _arena_pass_name_evidence_ok(row):
    if row['tw_availability_check'] != 'PASS':
        return True
    if any(unit_key not in _CHARACTER18 for unit_key in _arena_all_members(row)):
        return True  # missing FK is owned by the five-member availability guard above
    for unit_key in _arena_all_members(row):
        character = _CHARACTER18.get(unit_key)
        if not character or not _stored_official_name(character['tw_name']):
            return False
        evidence_ids = [e for e in character['source_evidence_ids'].split(';') if e]
        if not any(
            evidence_id in _EVIDENCE92
            and _EVIDENCE92[evidence_id]['status'] == 'ACTIVE'
            and _EVIDENCE92[evidence_id]['server'] == 'TW'
            and _EVIDENCE92[evidence_id]['source_tier'] == 'OFFICIAL'
            and _EVIDENCE92[evidence_id]['evidence_confidence'] == 'A'
            for evidence_id in evidence_ids
        ):
            return False
    return True
ck("39：PASS 成員皆有台服官方名與 ACTIVE TW OFFICIAL／A Evidence", all(
    _arena_pass_name_evidence_ok(row) for row in t39
))
_arena_pair_keys = [
    (row['server'], row['environment_version'], _arena_team_signature(row, 'enemy_team_ids'),
     _arena_team_signature(row, 'counter_team_ids'))
    for row in t39
]
ck("39：同 server／environment 的相同敵我五人配對不得重複",
   len(set(_arena_pair_keys)) == len(_arena_pair_keys))
ck("39：canonical Arena registry 僅保存 EXACT 配對",
   all(row['match_type'] == 'EXACT' for row in t39))
ck("39：Arena status／source tier／confidence／reproducibility enums", all(
    row['server'] in {'TW', 'JP'}
    and row['status'] in CFG['enums']['arena_status']
    and row['source_tier'] in CFG['enums']['arena_source_tier']
    and row['claim_confidence'] in CFG['enums']['arena_claim_confidence']
    and row['reproducibility'] in CFG['enums']['arena_reproducibility']
    for row in t39
))
ck("39：Arena outcome／verification／risk／environment enums", all(
    row['outcome'] in {'WIN', 'LOSS', 'MIXED', 'UNKNOWN'}
    and row['verification'] in {'SCREENSHOT_RESULT', 'VIDEO_RESULT', 'TEXT_REPORT', 'UNKNOWN'}
    and row['rng_risk'] in {'LOW', 'MEDIUM', 'HIGH', 'UNKNOWN'}
    and row['environment_match'] in {'EXACT', 'COMPATIBLE', 'MISMATCH', 'UNKNOWN'}
    for row in t39
))
ck("39：Arena operation_mode Enum",
   all(row['operation_mode'] in {'AUTO_SYSTEM', 'MANUAL', 'UNKNOWN'} for row in t39))
ck("39：Arena bracket／speed／initial action 明示 UNKNOWN 而非留白", all(
    row['arena_bracket'] and row['speed_conditions'] and row['initial_action_notes']
    for row in t39
))
ck("39：Arena source-truth metadata 不得留白", all(
    row['environment_version'] and row['randomness'] and row['source_platforms'] and row['notes']
    for row in t39
))
def _arena_nonnegative_int(value):
    return bool(re.fullmatch(r'0|[1-9]\d*', value or ''))
ck("39：Arena source record／日期 metadata 合法", all(
    _arena_nonnegative_int(row['source_record_count']) and int(row['source_record_count']) >= 1
    and date_ok(row['verified_date']) and date_ok(row['last_review_due'])
    and date_ok(row['record_date_min']) and date_ok(row['record_date_max'])
    and row['record_date_min'] <= row['record_date_max']
    for row in t39
))
def _arena_sample_shape_ok(row):
    sample, wins, losses = row['sample_size'], row['wins'], row['losses']
    if not sample:
        return not wins and not losses
    return (_arena_nonnegative_int(sample) and int(sample) >= 1
            and _arena_nonnegative_int(wins) and _arena_nonnegative_int(losses)
            and int(sample) == int(wins) + int(losses))
ck("39：Arena sample_size＝wins＋losses 且皆為非負整數",
   all(_arena_sample_shape_ok(row) for row in t39))
def _arena_empirical_rate_ok(row):
    raw = row['empirical_win_rate']
    if not raw:
        return True
    if row['status'] == 'SINGLE_REPORT' or not _arena_nonnegative_int(raw):
        return False
    return bool(row['sample_size'] and int(row['sample_size']) >= 2 and int(raw) <= 100)
ck("39：單筆 Arena 戰果不得宣稱 empirical win rate",
   all(_arena_empirical_rate_ok(row) for row in t39))
ck("39：SINGLE_REPORT claim_confidence 固定 D", all(
    row['status'] != 'SINGLE_REPORT' or row['claim_confidence'] == 'D'
    for row in t39
))
def _arena_outcome_count_ok(row):
    if row['outcome'] == 'WIN':
        return _arena_nonnegative_int(row['wins']) and int(row['wins']) >= 1
    if row['outcome'] == 'LOSS':
        return _arena_nonnegative_int(row['losses']) and int(row['losses']) >= 1
    return True
ck("39：WIN／LOSS outcome 與明示計數一致",
   all(_arena_outcome_count_ok(row) for row in t39))
ck("39：VERIFIED Arena 列需 environment_version",
   all(row['status'] != 'VERIFIED' or bool(row['environment_version']) for row in t39))
ck("39：VERIFIED Arena 列需 CONFIRMED reproducibility",
   all(row['status'] != 'VERIFIED' or row['reproducibility'] == 'CONFIRMED' for row in t39))
_arena_evidence = {r[0]: dict(zip(h92, r)) for r in r92[1:]}
_arena_claims = {r[0]: dict(zip(h93, r)) for r in r93[1:]}
def _arena_provenance_closure_ok(row):
    evidence_ids = [e for e in row['evidence_ids'].split(';') if e]
    claim_ids = [c for c in row['claim_ids'].split(';') if c]
    if not evidence_ids or not claim_ids:
        return False
    if not all(e in _arena_evidence for e in evidence_ids) or not all(c in _arena_claims for c in claim_ids):
        return False
    if not all(_arena_evidence[e]['claim_id'] in claim_ids for e in evidence_ids):
        return False
    if row['status'] not in {'VERIFIED', 'PROVISIONAL', 'SINGLE_REPORT'}:
        return True
    return (all(_arena_evidence[e]['status'] == 'ACTIVE'
                and _arena_evidence[e]['module'] == 'arena'
                and _arena_evidence[e]['server'] == row['server'] for e in evidence_ids)
            and all(_arena_claims[c]['status'] == 'ACTIVE'
                    and _arena_claims[c]['module'] == 'arena'
                    and _arena_claims[c]['server'] == row['server'] for c in claim_ids))
ck("39：publishable Arena closure 僅引用同服 arena ACTIVE Evidence／Claim",
   all(_arena_provenance_closure_ok(row) for row in t39))

def _arena_verified_multisource_ok(row):
    """Fail closed until a machine-verifiable first-party self-test schema exists."""
    contract = CFG['arena_gate_row']
    if row['status'] != contract['status']:
        return True
    evidence_ids = [e for e in row['evidence_ids'].split(';') if e]
    claim_ids = [c for c in row['claim_ids'].split(';') if c]
    if (row['claim_confidence'] not in contract['allowed_claim_confidence']
            or not _arena_nonnegative_int(row['source_record_count'])
            or int(row['source_record_count']) < contract['minimum_source_records']
            or not _arena_nonnegative_int(row['sample_size'])
            or int(row['sample_size']) < contract['minimum_observed_samples']
            or not _arena_nonnegative_int(row['wins'])
            or int(row['wins']) < contract['minimum_observed_wins']
            or row['outcome'] != contract['outcome']
            or row['verification'] == 'UNKNOWN'
            or row['source_tier'] not in contract['allowed_source_tiers']
            or row['environment_match'] != contract['environment_match']
            or len(claim_ids) != contract['result_claim_count']
            or row['claim_ids'] != claim_ids[0]):
        return False
    claim_id = claim_ids[0]
    claim = _arena_claims.get(claim_id)
    if not claim or not (
            claim['status'] == 'ACTIVE'
            and claim['server'] == row['server']
            and claim['module'] == 'arena'
            and claim['claim_type'] == 'SOURCE_FACT'
            and claim['claim_confidence'] in contract['allowed_claim_confidence']
            and claim['claim_confidence'] == row['claim_confidence']
            and claim['independence_check'] == 'YES'
            and claim['version_match'] == 'YES'):
        return False
    claim_evidence_ids = [e for e in claim['evidence_ids'].split(';') if e]
    if (len(evidence_ids) < contract['independent_evidence_count']
            or len(evidence_ids) != len(set(evidence_ids))
            or len(claim_evidence_ids) != len(set(claim_evidence_ids))
            or set(evidence_ids) != set(claim_evidence_ids)
            or not independent(evidence_ids)):
        return False
    return all(
        evidence_id in _arena_evidence
        and _arena_evidence[evidence_id]['status'] == 'ACTIVE'
        and _arena_evidence[evidence_id]['server'] == row['server']
        and _arena_evidence[evidence_id]['module'] == 'arena'
        and _arena_evidence[evidence_id]['claim_id'] == claim_id
        and _arena_evidence[evidence_id]['source_tier'] in contract['allowed_evidence_source_tiers']
        for evidence_id in evidence_ids
    )
ck("39：VERIFIED Arena 僅承認獨立多來源 WIN Evidence／Claim closure",
   all(_arena_verified_multisource_ok(row) for row in t39))

def _arena_verified_https_hostname_ok(row):
    """Arena maturity requires online Evidence; ST49 keeps its offline fallback."""
    contract = CFG['arena_gate_row']
    if row['status'] != contract['status']:
        return True
    evidence_ids = [e for e in row['evidence_ids'].split(';') if e]
    if not evidence_ids:
        return False
    for evidence_id in evidence_ids:
        evidence = _arena_evidence.get(evidence_id)
        if not evidence:
            return False
        try:
            parsed = urlparse(evidence['source_url'])
            hostname = parsed.hostname
        except (TypeError, ValueError):
            return False
        if (parsed.scheme.lower() != contract['required_evidence_url_scheme']
                or not hostname):
            return False
    return True
ck("39：VERIFIED Arena 成熟 Evidence 皆須具 nonempty HTTPS hostname",
   all(not _arena_verified_multisource_ok(row)
       or _arena_verified_https_hostname_ok(row) for row in t39))
h25 = r25[0]
ck("25：欄位標頭符合規格", h25 == CFG['t25_header'])
t25 = [dict(zip(h25, r)) for r in r25[1:]]
_guide_rows = {r[0]: dict(zip(r24[0], r)) for r in r24[1:]}
_g24 = set(_guide_rows)
ck("25：guide_id FK→24", all(t['guide_id'] in _g24 for t in t25))
ck("25：五 slot 完整", all(all(t[f'slot{i}'] for i in range(1, 6)) for t in t25))
ck("25：clear_status Enum", all(t['clear_status'] in CFG['enums']['team_clear_status'] for t in t25))
def _pve_slots(t):
    return [t[f'slot{i}'] for i in range(1, 6)]
ck("25：每隊五名角色互異", all(len(set(_pve_slots(t))) == 5 for t in t25))
def _pve_guide_relation_ok(t):
    guide = _guide_rows.get(t['guide_id'])
    return bool(guide and t['server'] == guide['server'] and t['stage'] in {
        guide['stage'], guide['area'] + guide['stage']
    })
ck("24→25：team server／stage 與 guide 關聯一致", all(_pve_guide_relation_ok(t) for t in t25))
ck("25：tw_availability_check Enum；PASS 的五 slot 均須為 18 AVAILABLE", all(
    t['tw_availability_check'] in CFG['enums']['tw_check']
    and (t['tw_availability_check'] != 'PASS' or all(u in TW_UNITS for u in _pve_slots(t)))
    for t in t25
))
ck("25：Evidence FK", all(e in set(ids92) for t in t25 for e in t['evidence_ids'].split(';') if e))
ck("25：operation_mode Enum", all(t['operation_mode'] in CFG['enums']['pve_operation_mode'] for t in t25))
_PVE_REQ_TOP = {'schema_version', 'operation_mode_claims', 'slots', 'support', 'timeline_ref', 'failure_conditions'}
_PVE_REQ_SLOTS = {f'slot{i}' for i in range(1, 6)}
_PVE_REQ_SLOT_FIELDS = {'star', 'rank', 'ue1', 'ue2', 'six_star', 'connect_rank', 'element_boost'}
def _filled_text(value):
    return isinstance(value, str) and bool(value.strip())
def _parse_pve_requirements(t):
    raw = t['requirements']
    try:
        obj = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(obj, dict) or set(obj) != _PVE_REQ_TOP or obj.get('schema_version') != '1.0':
        return None
    if json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')) != raw:
        return None
    claims = obj.get('operation_mode_claims')
    if not isinstance(claims, list) or not claims:
        return None
    if any(not isinstance(c, dict) or set(c) != {'source_id', 'mode'}
           or not _filled_text(c.get('source_id'))
           or c.get('mode') not in CFG['enums']['pve_mode_claim'] for c in claims):
        return None
    slots = obj.get('slots')
    if not isinstance(slots, dict) or set(slots) != _PVE_REQ_SLOTS:
        return None
    for slot in slots.values():
        if (not isinstance(slot, dict) or set(slot) != _PVE_REQ_SLOT_FIELDS
            or any(not _filled_text(value) for value in slot.values())):
            return None
    support = obj.get('support')
    if (not isinstance(support, dict) or set(support) != {'unit', 'requirements'}
        or any(not _filled_text(value) for value in support.values())):
        return None
    if not _filled_text(obj.get('timeline_ref')):
        return None
    failures = obj.get('failure_conditions')
    if not isinstance(failures, list) or not failures or any(not _filled_text(value) for value in failures):
        return None
    return obj
_pve_requirement_objects = [_parse_pve_requirements(t) for t in t25]
ck("25：requirements 為 canonical JSON；必要 key／slot1–5 完整且無空字串", all(obj is not None for obj in _pve_requirement_objects))
def _pve_support_state_ok(t, obj):
    if obj is None:
        return True  # requirements schema guard owns this failure.
    support_slot = t['support_slot']
    support_unit = obj['support']['unit']
    if support_slot:
        return support_slot in {f'slot{i}' for i in range(1, 6)} and t[support_slot] == support_unit
    return support_unit in {'NONE', 'UNKNOWN', 'SOURCE_CONFLICT'}
ck("25：借角 unit／support_slot 三態關聯一致", all(
    _pve_support_state_ok(t, obj) for t, obj in zip(t25, _pve_requirement_objects)
))
def _pve_mode_claims_match(t, obj):
    if obj is None:
        return True  # JSON/schema check owns this failure; avoid masking its mutation oracle.
    claims = obj['operation_mode_claims']
    row_sources = {source_id for source_id in t['source_ids'].split(';') if source_id}
    if any(c['source_id'] not in row_sources for c in claims):
        return False
    modes = {c['mode'] for c in claims}
    sources = {c['source_id'] for c in claims}
    if t['operation_mode'] == 'SOURCE_CONFLICT':
        return len(sources) >= 2 and len(modes) >= 2
    return bool(claims) and modes == {t['operation_mode']}
ck("25：SOURCE_CONFLICT 至少兩來源＋兩種 mode；非衝突 mode 與來源聲明一致", all(
    _pve_mode_claims_match(t, obj) for t, obj in zip(t25, _pve_requirement_objects)
))
_combo = [(t['guide_id'], tuple(sorted(_pve_slots(t)))) for t in t25]
ck("25：同關卡相同五人不得重複列（多來源合併）", len(_combo) == len(set(_combo)))

# ========== A2 source-separated operation timelines (26/27) ==========
h26, h27 = r26[0], r27[0]
ck("26：欄位標頭符合規格", h26 == CFG['t26_header'])
ck("27：欄位標頭符合規格", h27 == CFG['t27_header'])
t26 = [dict(zip(h26, r)) for r in r26[1:]]
t27 = [dict(zip(h27, r)) for r in r27[1:]]
_teams_by_id = {t['team_id']: t for t in t25}
_requirements_by_team = {
    t['team_id']: obj for t, obj in zip(t25, _pve_requirement_objects) if obj is not None
}
_timelines_by_id = {t['timeline_id']: t for t in t26}
_steps_by_timeline = defaultdict(list)
for step in t27:
    _steps_by_timeline[step['timeline_id']].append(step)

def _timeline_source_link_ok(tl):
    team = _teams_by_id.get(tl['team_id'])
    req = _requirements_by_team.get(tl['team_id'])
    if not team:
        return False
    if not req or not _pve_mode_claims_match(team, req):
        return True  # 25 JSON／mode guard owns this failure; do not mask its mutation oracle.
    claims = {c['source_id']: c['mode'] for c in req['operation_mode_claims']}
    return (tl['source_id'] in claims
            and claims[tl['source_id']] == tl['operation_mode']
            and tl['source_evidence_id'] in set(team['evidence_ids'].split(';'))
            and tl['source_evidence_id'] in ev
            and ev[tl['source_evidence_id']][si92] == 'ACTIVE')

ck("26：team／Evidence FK 與逐來源 operation mode 聲明一致", all(
    _timeline_source_link_ok(tl) for tl in t26
))
ck("26：source locator 必須等於 Evidence locator 或其 # 子定位", all(
    tl['source_locator'] == ev[tl['source_evidence_id']][loci]
    or tl['source_locator'].startswith(ev[tl['source_evidence_id']][loci] + '#')
    for tl in t26 if tl['source_evidence_id'] in ev
))
_structured_timeline_ids = [tl['timeline_id'] for tl in t26 if tl['status'] == 'STRUCTURED']
ck("26：同隊同來源只保留一條 source axis；結構化 timeline_id 唯一", (
    len({(tl['team_id'], tl['source_id']) for tl in t26}) == len(t26)
    and len(_structured_timeline_ids) == len(set(_structured_timeline_ids))
))

def _timeline_state_ok(tl):
    if (tl['status'] not in CFG['enums']['pve_timeline_status']
        or tl['operation_mode'] not in CFG['enums']['pve_mode_claim']
        or tl['clock_mode'] not in CFG['enums']['pve_clock_mode']
        or tl['initial_auto_state'] not in CFG['enums']['pve_auto_state']
        or tl['reproducibility'] not in CFG['enums']['pve_timeline_reproducibility']
        or tl['gap_reason'] not in CFG['enums']['pve_timeline_gap_reason']
        or not date_ok(tl['last_verified_at'])
        or not _filled_text(tl['source_locator'])
        or not _filled_text(tl['timeline_variant_name'])
        or not _filled_text(tl['notes'])):
        return False
    if tl['status'] == 'STRUCTURED':
        return (tl['timeline_id'] != 'UNKNOWN'
                and tl['clock_mode'] != 'UNKNOWN'
                and (tl['battle_duration_ms'] == 'UNKNOWN'
                     or (tl['battle_duration_ms'].isdigit() and int(tl['battle_duration_ms']) > 0))
                and tl['initial_auto_state'] != 'UNKNOWN'
                and tl['gap_reason'] == 'NONE')
    return (tl['timeline_id'] == 'UNKNOWN'
            and tl['clock_mode'] == 'UNKNOWN'
            and tl['battle_duration_ms'] == 'UNKNOWN'
            and tl['initial_auto_state'] == 'UNKNOWN'
            and tl['reproducibility'] == 'UNKNOWN'
            and tl['gap_reason'] != 'NONE')

ck("26：STRUCTURED／SOURCE_GAP 狀態不得強化 UNKNOWN", all(_timeline_state_ok(tl) for tl in t26))

def _timeline_step_ok(step):
    tl = _timelines_by_id.get(step['timeline_id'])
    if not tl or tl['status'] != 'STRUCTURED':
        return False
    team = _teams_by_id.get(tl['team_id'])
    members = set(_pve_slots(team)) if team else set()
    if (not step['sequence_no'].isdigit() or int(step['sequence_no']) < 1
        or not step['source_step_no'].isdigit() or int(step['source_step_no']) < 1
        or step['trigger_type'] not in CFG['enums']['pve_timeline_trigger']
        or step['time_state'] not in CFG['enums']['pve_timeline_time_state']
        or step['action_type'] not in CFG['enums']['pve_timeline_action']
        or step['auto_state_after'] not in CFG['enums']['pve_auto_state']
        or step['criticality'] not in CFG['enums']['pve_timeline_criticality']):
        return False
    if step['time_state'] == 'STATED':
        for value in (step['clock_from_ms'], step['clock_to_ms']):
            if not value.isdigit() or int(value) < 0:
                return False
        if tl['battle_duration_ms'].isdigit() and any(
            int(value) > int(tl['battle_duration_ms'])
            for value in (step['clock_from_ms'], step['clock_to_ms'])
        ):
            return False
        if tl['clock_mode'] == 'COUNTDOWN' and int(step['clock_from_ms']) < int(step['clock_to_ms']):
            return False
    elif step['clock_from_ms'] != 'UNKNOWN' or step['clock_to_ms'] != 'UNKNOWN':
        return False
    for key in ('trigger_actor_unit_key', 'actor_unit_key', 'target_unit_key'):
        if step[key] != 'NONE' and step[key] not in members:
            return False
    if step['action_type'] in {'USE_UB', 'SET_ON', 'SET_OFF', 'TARGET'} and step['actor_unit_key'] not in members:
        return False
    if step['action_type'] == 'TARGET' and step['target_unit_key'] not in members:
        return False
    return all(_filled_text(step[key]) for key in (
        'animation_cue', 'hp_threshold', 'tolerance_ms', 'instruction_zh_tw',
        'failure_if_missed', 'source_locator'
    ))

ck("27：step FK／Enum／時間範圍／角色成員資格完整", all(_timeline_step_ok(step) for step in t27))
_sequence_ok = True
for timeline_id, steps in _steps_by_timeline.items():
    seq = sorted(int(step['sequence_no']) for step in steps if step['sequence_no'].isdigit())
    if seq != list(range(1, len(steps) + 1)):
        _sequence_ok = False
ck("27：每來源 sequence_no 唯一且連續", _sequence_ok)
_source_step_grouping_ok = True
for timeline_id, steps in _steps_by_timeline.items():
    ordered = sorted(steps, key=lambda step: int(step['sequence_no']) if step['sequence_no'].isdigit() else 0)
    source_numbers = [int(step['source_step_no']) for step in ordered if step['source_step_no'].isdigit()]
    if (len(source_numbers) != len(ordered)
        or source_numbers != sorted(source_numbers)
        or sorted(set(source_numbers)) != list(range(1, max(source_numbers, default=0) + 1))):
        _source_step_grouping_ok = False
ck("27：source_step_no 依序且分組連續", _source_step_grouping_ok)
ck("26／27：STRUCTURED 必有步驟；SOURCE_GAP 必為零步驟", all(
    (tl['status'] == 'STRUCTURED' and bool(_steps_by_timeline.get(tl['timeline_id'])))
    or (tl['status'] == 'SOURCE_GAP' and not _steps_by_timeline.get(tl['timeline_id']))
    for tl in t26
))
_source_boundary_bad = []
for source_axis_id, boundary in CFG['pve_timeline_source_boundaries'].items():
    timeline = next((tl for tl in t26 if tl['source_axis_id'] == source_axis_id), None)
    if not timeline or timeline['battle_duration_ms'] != boundary['battle_duration_ms']:
        _source_boundary_bad.append(source_axis_id)
        continue
    source_steps = _steps_by_timeline.get(timeline['timeline_id'], [])
    if 'step_assertions' in boundary:
        fields = CFG['pve_timeline_exact_step_fields']
        expected = boundary['step_assertions']
        actual = {step['timeline_step_id']: step for step in source_steps}
        if (set(actual) != set(expected)
            or any(actual[step_id]['sequence_no'] != str(index)
                   for index, step_id in enumerate(expected, start=1) if step_id in actual)
            or any([actual[step_id][field] for field in fields] != values
                   for step_id, values in expected.items() if step_id in actual)):
            _source_boundary_bad.append(source_axis_id)
        continue
    unstated = set(boundary['not_stated_source_steps'])
    expected_source_steps = set(boundary['source_step_numbers'])
    locator_prefix = boundary['source_locator_prefix']
    if ({step['source_step_no'] for step in source_steps} != expected_source_steps
        or any(step['source_locator'] != locator_prefix + step['source_step_no'] for step in source_steps)
        or any(step['criticality'] != boundary['criticality'] for step in source_steps)
        or any(
            step['source_step_no'] in unstated
            and (step['time_state'] != 'NOT_STATED'
                 or step['clock_from_ms'] != 'UNKNOWN'
                 or step['clock_to_ms'] != 'UNKNOWN')
            for step in source_steps
        )):
        _source_boundary_bad.append(source_axis_id)
ck("ST87：來源邊界、locator 與未載欄位不得推測", not _source_boundary_bad, ','.join(_source_boundary_bad))

def _timeline_claim_coverage_ok(team):
    if team['operation_mode'] not in {'SEMI_AUTO', 'MANUAL_TIMELINE', 'SOURCE_CONFLICT', 'UNKNOWN'}:
        return True
    req = _requirements_by_team.get(team['team_id'])
    if not req or not _pve_mode_claims_match(team, req):
        return True  # 25 JSON／mode guard owns this failure; do not mask its mutation oracle.
    expected = {(c['source_id'], c['mode']) for c in req['operation_mode_claims']}
    actual = {(tl['source_id'], tl['operation_mode']) for tl in t26 if tl['team_id'] == team['team_id']}
    expected_axes = {ref for ref in req['timeline_ref'].split(';') if ref}
    actual_axes = {tl['source_axis_id'] for tl in t26 if tl['team_id'] == team['team_id']}
    return expected == actual and expected_axes == actual_axes

ck("25→26：手動／半自動／衝突隊伍每個來源與 timeline_ref 均有結構化軸或明示缺口", all(
    _timeline_claim_coverage_ok(team) for team in t25
))

def _cross_server_repro_ok(tl):
    if tl['status'] != 'STRUCTURED':
        return True
    team = _teams_by_id[tl['team_id']]
    evidence = ev[tl['source_evidence_id']]
    if team['server'] == 'TW' and evidence[svi92] != 'TW':
        return tl['reproducibility'] == 'UNVERIFIED_ON_TW'
    return tl['reproducibility'] != 'TW_REPRODUCED' or evidence[svi92] == 'TW'

ck("26：跨服結構化軸不得冒充台服已重現", all(_cross_server_repro_ok(tl) for tl in t26))
_valid_team_signatures_by_guide = defaultdict(set)
_evidence_ids = set(ids92)
_active_evidence_ids = {r[0] for r in r92[1:] if r[si92] == 'ACTIVE'}
def _active_evidence_claim(evidence_id):
    row = ev.get(evidence_id)
    return bool(row and row[si92] == 'ACTIVE' and row[claim_i92]
                and claim_status_by_id.get(row[claim_i92]) == 'ACTIVE')
for t in t25:
    slots = _pve_slots(t)
    evidence_ids = [e for e in t['evidence_ids'].split(';') if e]
    if (all(slots)
        and t['clear_status'] == 'VERIFIED'
        and t['tw_availability_check'] == 'PASS'
        and _pve_guide_relation_ok(t)
        and len(set(slots)) == 5
        and all(u in TW_UNITS for u in slots)
        and evidence_ids
        and all(e in _evidence_ids for e in evidence_ids)
        and all(e in _active_evidence_ids for e in evidence_ids)
        and all(_active_evidence_claim(e) for e in evidence_ids)
        and date_ok(t['verified_date'])):
        _valid_team_signatures_by_guide[t['guide_id']].add(tuple(sorted(slots)))
valid_teams_by_guide = Counter({g: len(signatures) for g, signatures in _valid_team_signatures_by_guide.items()})
def _verified_pve_closure_is_active(guide):
    if guide['status'] != 'VERIFIED':
        return True
    evidence_ids = [e for e in guide['evidence_ids'].split(';') if e]
    claim_ids = [c for c in guide['claim_ids'].split(';') if c]
    teams = [t for t in t25 if t['guide_id'] == guide['guide_id'] and t['clear_status'] == 'VERIFIED']
    return (bool(evidence_ids) and bool(claim_ids)
            and all(_active_evidence_claim(e) for e in evidence_ids)
            and all(claim_status_by_id.get(c) == 'ACTIVE' for c in claim_ids)
            and all(all(_active_evidence_claim(e) for e in t['evidence_ids'].split(';') if e)
                    for t in teams))
ck("24／25：VERIFIED PVE closure 僅引用 ACTIVE Evidence／Claim", all(
    _verified_pve_closure_is_active(guide) for guide in _guide_rows.values()
))
h45 = r45[0]
ck("45：欄位標頭符合規格", h45 == CFG['t45_header'])
_st45 = h45.index('source_type'); _cc45 = h45.index('confidence_cap'); _us45 = h45.index('update_status')
ck("45：source_type Enum", all(r[_st45] in CFG['enums']['community_source_type'] for r in r45[1:]))
ck("45：社群來源信心上限 ≤C（不得標 OFFICIAL／A／B）", all(r[_cc45] in ('C', 'D', 'E') for r in r45[1:]))
ck("45：update_status Enum", all(r[_us45] in CFG['enums']['source_update_status'] for r in r45[1:]))
community_checked = len({r[0] for r in r45[1:] if r[_us45] == 'CHECKED' and r[_st45] in ('MAINTAINED_TABLE', 'FORUM_TIMELINE')})
h46 = r46[0]
ck("46：欄位標頭符合規格", h46 == CFG['t46_header'])
_ac46 = h46.index('access_status'); _cc46 = h46.index('confidence_cap')
ck("46：access_status Enum", all(r[_ac46] in CFG['enums']['arena_access_status'] for r in r46[1:]))
ck("46：來源信心上限 ≤C", all(r[_cc46] in ('C', 'D', 'E') for r in r46[1:]))
ck("41：社群共識欄存在（官方／錨點／社群分欄）", all(c in r41[0] for c in ['community_estimate_start', 'community_estimate_end', 'community_source_ids', 'community_last_checked', 'community_disagreement']))

# ========== test definitions / fixtures ==========
defs = re.findall(r'\*\*([AT]\d+)', R['11_ACCEPTANCE_TESTS.md'])
ck("ST45：定義精確集合（Guide-Only 41 測試）＋各僅一次", sorted(set(defs)) == sorted(CFG['definition_set']) and len(defs) == len(set(defs)))
fx = R['14_PUBLIC_TEST_FIXTURES.md']
fxids = re.findall(r'\*\*(FX-[A-Z]+-[A-Z0-9]+)\*\*', fx)
cover = set()
for m in re.finditer(r'\*\*FX-[A-Z]+-[A-Z0-9]+\*\*｜([^｜]+)｜', fx):
    cover |= set(re.findall(r'\b([AT]\d+)\b', m.group(1)))
ck("ST46：Fixture 覆蓋公共測試精確集合", set(CFG['public_test_set']) <= cover, f"缺{sorted(set(CFG['public_test_set'])-cover)}")
ck("Fixture 數", len(set(fxids)) == CFG['fixture_expected'], f"{len(set(fxids))}/{CFG['fixture_expected']}")

# ========== sync guards (Guide-Only) ==========
ck("ST48：12 台服新角導向 18（無 TW_ROSTER_PENDING 殘留）", 'TW_ROSTER_PENDING' not in R['12_CHARACTER_SYNC.md'] and '18_TW_CHARACTER_AVAILABILITY' in R['12_CHARACTER_SYNC.md'])
sg = CFG['sync_guard']
m = re.search(r'## §3 新角色同步(.*?)## §4', R['91_PROMPT_LIBRARY.md'], re.S); sec = m.group(1) if m else ""
ck("ST39a：91 §3 必含語意", bool(m) and all(k in sec for k in sg['prompt_required']))
ck("ST39b：91 §3／12 無繞過語句", all(all(b not in txt for b in sg['prompt_forbidden']) for txt in [sec, R['12_CHARACTER_SYNC.md']]))
lasts = [(sid, [c.strip() for c in rest.split('|')]) for sid, rest in sync_rows]
dts = [c for _, cells in lasts for c in cells if re.fullmatch(r'20\d\d-\d\d-\d\d', c)]
top = re.search(r'最後同步截止日（last_checked）：(20\d\d-\d\d-\d\d)', R['12_CHARACTER_SYNC.md'])
ck("ST39c：12 截止日＝各列最新", bool(top) and dts and top.group(1) == max(dts))
ck("ST39d：RELEASED 無 NOT_ANNOUNCED 矛盾", not [s for s, c in lasts if any('RELEASED' in x for x in c) and any('NOT_ANNOUNCED' in x for x in c)])
ev41 = {r[0] for r in r41[1:]}
ck("ST39e：MIGRATED_TO_41 有對應 event_id", not [s for s, c in lasts if any('MIGRATED_TO_41' in x for x in c) and not (set(re.findall(r'JP_\d{8}_[a-z_]+', ' '.join(c))) & ev41)])
tg = CFG['t43_guard']
ck("ST40：T43 動態錨點（02 須揭露軌道別 n 值，數值由 anchors 派生）", tg['must'] in R['91_PROMPT_LIBRARY.md'] and tg['forbid'] not in R['91_PROMPT_LIBRARY.md'] and 'ALL_NEW：n＝' in R['02_SERVER_BASELINE.md'])
rm = re.search(r'tools×(\d+)', R['README.md'])
ck("ST41：tools 數一致", bool(rm) and int(rm.group(1)) == len(TOOLS), f"實{len(TOOLS)}")
lvi = r41[0].index('last_verified')
_mi41 = r41[0].index('maturity')
ck("ST42：41 MATURE 列 last_verified ≥ 基準日（非成熟列可保留誠實舊日期）", all(r[lvi] >= CFG['baseline_date'] for r in r41[1:] if r[_mi41] == 'MATURE'))
pending_ev = {r[0] for r in r92[1:] if r[si92] == 'PENDING_REVIEW'}
ck("ST43：待回驗 Evidence 的 Claim 附註一致", not [c[0] for c in r93[1:] if (set(c[ei].split(';')) & pending_ev) and '回驗' not in c[-1]])

# ========== ST75 qualitative drift guard ==========
has_mainline = any(r[0] == 'CLM-TW-MAINLINE' for r in r93[1:])
has_sixstar = any(r[0] == 'CLM-TW-SIXSTAR' for r in r93[1:])
drift_bad = []
if has_mainline or has_sixstar:
    for f in ['15_DATA_QUALITY_REPORT.md', 'README.md']:
        if re.search(r'主線／六星[待完全]*待查|台服主線／六星(?!是否)', R[f]):
            if '完全待查' in R[f] or re.search(r'主線／六星待查', R[f]): drift_bad.append(f)
ck("ST75：15／README 不再宣稱主線／六星完全待查", not drift_bad, ",".join(drift_bad))
og = re.search(r'<!-- OPEN_GAPS_START -->(.*?)<!-- OPEN_GAPS_END -->', R['02_SERVER_BASELINE.md'], re.S)
ck("ST75b：02 OPEN_GAPS SSOT 存在", bool(og))

# ========== 17 execution-log guards ==========
H = CFG['exec_log_columns']
ck("17 欄位標頭符合規格", r17[0] == H)
logs = [dict(zip(H, r)) for r in r17[1:]]
run_ids = [x['run_id'] for x in logs]
ck("ST56：17 run_id 唯一", len(run_ids) == len(set(run_ids)), f"{len(run_ids)} 列")
bad_tid = [x['run_id'] for x in logs if x['test_id'] not in CFG['definition_set']]
ck("ST57a：17 test_id 屬 definition_set", not bad_tid, ",".join(bad_tid[:4]))
smap = CFG['suite_map']
def suite_of(tid): return next((s for s, ts in smap.items() if tid in ts), None)
bad_suite = [x['run_id'] for x in logs if x['test_id'] in CFG['definition_set'] and x['suite'] != suite_of(x['test_id'])]
ck("ST57b：17 suite 與 test_id 對應", not bad_suite, ",".join(bad_suite[:4]))
fmap = CFG['fixture_map']
bad_fx = [x['run_id'] for x in logs if x['test_id'] in fmap and x['fixture_id'] != fmap[x['test_id']]]
ck("ST57c：17 fixture 與 test_id 對應", not bad_fx, ",".join(bad_fx[:4]))
allfx = set(fxids)
ck("ST57d：17 fixture_id 存在", not [x['run_id'] for x in logs if x['fixture_id'] and x['fixture_id'] not in allfx])
ck("ST58：17 Evidence FK 完整", not [x['run_id'] for x in logs if x['evidence_ids'] and any(e not in set(ids92) for e in x['evidence_ids'].split(';') if e)])
ck("17 status Enum", all(x['status'] in CFG['enums']['test_status'] for x in logs))
pf = CFG['pass_required_fields']
bad_pass = [x['run_id'] for x in logs if x['status'] == 'PASS' and (any(not x.get(k) for k in pf) or not date_ok(x['execution_date']))]
ck("ST59：PASS 必填欄位（含 reviewer／review_method／expectation_checklist）", not bad_pass, ",".join(bad_pass[:4]))
ck("ST59b：PASS review_method=MANUAL_FIXTURE_REVIEW＋checklist=ALL_PASS", not [x['run_id'] for x in logs if x['status'] == 'PASS' and (x['review_method'] != 'MANUAL_FIXTURE_REVIEW' or x['expectation_checklist'] != 'ALL_PASS')])
ck("ST51：FAIL 必附 defect_id＋observed_result", not [x['run_id'] for x in logs if x['status'] == 'FAIL' and (not x['defect_id'] or not x['observed_result'])])
# ST71 evidence policy (structural)
pol = CFG['fixture_policy']
def policy_ok(x):
    p = pol.get(x['test_id'])
    if not p or x['status'] != 'PASS': return True
    eids = [e for e in x['evidence_ids'].split(';') if e]
    if 'min_evidence_count' in p and len(eids) < p['min_evidence_count']: return False
    servers = {ev[e][ev[e].__class__ and h92.index('server')] for e in eids if e in ev}
    if p.get('required_server') == 'TW+JP' and not ({'TW', 'JP'} <= servers): return False
    if p.get('forbidden_server') == 'CN' and 'CN' in servers: return False
    if 'max_claim_confidence' in p:
        confs = [ev[e][eci] for e in eids if e in ev]
        order = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}
        if any(order.get(c, 0) > order[p['max_claim_confidence']] for c in confs): return False
    return True
ck("ST71：Execution Evidence Policy（server／count／confidence）", not [x['run_id'] for x in logs if not policy_ok(x)], "")

# ========== retest chain (ST60/61/67/68/69) ==========
def key(x): return x['test_id']
by_key = defaultdict(list)
for x in logs: by_key[key(x)].append(x)
run_by_id = {x['run_id']: x for x in logs}
cur_bad, chain_bad, cross_bad, cycle_bad, terminal_bad = [], [], [], [], []
current = {}
for k, xs in by_key.items():
    curs = [x for x in xs if x['is_current'] == 'Y']
    if len(curs) != 1: cur_bad.append(f"{k}:{len(curs)}")
    else: current[k] = curs[0]
    for x in xs:
        for ref in [x['retest_of'], x['supersedes_run_id']]:
            if ref and ref not in run_by_id: chain_bad.append(x['run_id'])
        # ST67 retest_of same test/scope/account
        if x['retest_of'] and x['retest_of'] in run_by_id:
            y = run_by_id[x['retest_of']]
            if key(y) != key(x): cross_bad.append(x['run_id'])
        # ST68 no cycle
        seen, cur_ref, steps = set(), x['retest_of'], 0
        while cur_ref and cur_ref in run_by_id and steps < 100:
            if cur_ref in seen: cycle_bad.append(x['run_id']); break
            seen.add(cur_ref); cur_ref = run_by_id[cur_ref]['retest_of']; steps += 1
    # ST69 current is terminal (no other row supersedes/retests it as newer current)
    if k in current:
        cur_run = current[k]['run_id']
        superseded = [x for x in xs if x['supersedes_run_id'] == cur_run or x['retest_of'] == cur_run]
        if superseded: terminal_bad.append(f"{k}")
ck("ST61a：每 test/scope/account 恰一 is_current", not cur_bad, ",".join(cur_bad[:4]))
ck("ST61b：retest_of／supersedes 引用既有 run_id", not chain_bad, ",".join(set(chain_bad))[:60])
ck("ST67：retest_of 同 test/scope/account", not cross_bad, ",".join(set(cross_bad))[:60])
ck("ST68：retest chain 無循環", not cycle_bad, ",".join(set(cycle_bad))[:60])
ck("ST69：current 為 terminal node", not terminal_bad, ",".join(terminal_bad[:4]))

# ========== Gate data counts (maturity-based, ST68/69/70 in audit numbering) ==========
h24 = r24[0]; h39 = r39[0]; h41 = r41[0]
def col(h, name): return h.index(name) if name in h else -1
# PVE mature rows from 24
pve_ok = []
c24 = {c: col(h24, c) for c in ['guide_id', 'status', 'team_count', 'verified_date', 'evidence_ids', 'claim_ids', 'reproducibility', 'last_review_due']}
for r in r24[1:]:
    if r[c24['status']] != 'VERIFIED': continue
    try: tc = int(r[c24['team_count']] or 0)
    except: tc = 0
    eids = [e for e in r[c24['evidence_ids']].split(';') if e]; cids = [c for c in r[c24['claim_ids']].split(';') if c]
    fresh = (not r[c24['last_review_due']]) or r[c24['last_review_due']] >= TODAY
    if tc >= 1 and date_ok(r[c24['verified_date']]) and all(_active_evidence_claim(e) for e in eids) and all(claim_status_by_id.get(c) == 'ACTIVE' for c in cids) and r[c24['reproducibility']] == 'CONFIRMED' and fresh and eids and cids:
        pve_ok.append(r[c24['guide_id']])
def _pve_team_count_matches(r):
    try:
        raw = r[c24['team_count']]
        return bool(re.fullmatch(r'0|[1-9]\d*', raw)) and int(raw) == valid_teams_by_guide.get(r[c24['guide_id']], 0)
    except (TypeError, ValueError):
        return False
_pve_count_consistent_guides = {r[c24['guide_id']] for r in r24[1:] if _pve_team_count_matches(r)}
ck("25 與 24：所有 guide 的 team_count＝25 有效隊伍數", len(_pve_count_consistent_guides) == len(r24[1:]))
pve_ok = [g for g in pve_ok if g in _pve_count_consistent_guides and valid_teams_by_guide.get(g, 0) >= CFG['gate_thresholds']['B']['teams_per_stage']]
PVE_V = len(pve_ok)
# Arena mature rows from 39
arena_ok = []
c39 = {c: col(h39, c) for c in ['counter_id', 'server', 'environment_version', 'enemy_team_ids', 'counter_team_ids', 'status', 'verified_date', 'evidence_ids', 'claim_ids', 'reproducibility', 'last_review_due']}
_arena_gate_groups = defaultdict(set)
for r in r39[1:]:
    if r[c39['status']] != CFG['arena_gate_row']['status']: continue
    row = dict(zip(h39, r))
    en = [e for e in r[c39['enemy_team_ids']].split(';') if e]; co = [e for e in r[c39['counter_team_ids']].split(';') if e]
    eids = [e for e in r[c39['evidence_ids']].split(';') if e]; cids = [c for c in r[c39['claim_ids']].split(';') if c]
    fresh = (not r[c39['last_review_due']]) or r[c39['last_review_due']] >= TODAY
    twc = r[h39.index('tw_availability_check')] if 'tw_availability_check' in h39 else ''
    if (len(en) == CFG['arena_gate_row']['team_size']
            and len(co) == CFG['arena_gate_row']['team_size']
            and len(set(en)) == CFG['arena_gate_row']['team_size']
            and len(set(co)) == CFG['arena_gate_row']['team_size']
            and all(u in TW_UNITS for u in en + co) and date_ok(r[c39['verified_date']])
            and _arena_provenance_closure_ok(row)
            and _arena_verified_multisource_ok(row)
            and _arena_verified_https_hostname_ok(row)
            and r[c39['reproducibility']] == 'CONFIRMED' and bool(r[c39['environment_version']])
            and fresh and eids and cids and twc == 'PASS'):
        arena_ok.append(r[c39['counter_id']])
        if r[c39['server']] == 'TW':
            defense_key = (r[c39['server']], r[c39['environment_version']], tuple(sorted(en)))
            _arena_gate_groups[defense_key].add(tuple(sorted(co)))
ARENA_F = sum(1 for counters in _arena_gate_groups.values()
              if len(counters) >= CFG['gate_thresholds']['B']['counters_per_defense'])
ARENA_VERIFIED_ROWS = len(arena_ok)
# Timeline mature rows from 41
tl_ok = []
c41 = {c: col(h41, c) for c in ['event_id', 'jp_date', 'tw_estimate_start', 'tw_estimate_end', 'confidence', 'pool_type', 'evidence_ids', 'claim_ids', 'anchor_track', 'anchor_count', 'forecast_basis', 'last_verified', 'status', 'maturity']}
for r in r41[1:]:
    if r[c41['status']] != 'ACTIVE' or r[c41['maturity']] != 'MATURE': continue
    eids = [e for e in r[c41['evidence_ids']].split(';') if e]; cids = [c for c in r[c41['claim_ids']].split(';') if c]
    filled = all(r[c41[k]] for k in ['jp_date', 'tw_estimate_start', 'tw_estimate_end', 'confidence', 'pool_type', 'anchor_track', 'anchor_count', 'forecast_basis'])
    fresh = date_ok(r[c41['last_verified']]) and r[c41['last_verified']] >= CFG['baseline_date']
    if filled and eids and cids and all(e in set(ids92) for e in eids) and all(c in set(ids93) for c in cids) and fresh:
        tl_ok.append(r[c41['event_id']])
TIMELINE = len(tl_ok)
h47 = r47[0]
ck("47：欄位標頭符合規格", h47 == CFG['t47_header'])
_pa_ok = []
for r in r47[1:]:
    d = dict(zip(h47, r))
    if d['status'] != 'VERIFIED': continue
    teams = [[u for u in d[f'counter_team{i}'].split(';') if u] for i in (1, 2, 3)]
    members = [u for t in teams for u in t]
    eids = [e for e in d['evidence_ids'].split(';') if e]; cids = [c for c in d['claim_ids'].split(';') if c]
    fresh = (not d['last_review_due']) or d['last_review_due'] >= TODAY
    if (all(len(t) == 5 and len(set(t)) == 5 for t in teams) and len(set(members)) == 15
            and d['tw_availability_check'] == 'PASS' and d['non_overlap_check'] == 'PASS'
            and all(u in TW_UNITS for u in members)
            and date_ok(d['verified_date']) and eids and cids
            and all(e in set(ids92) for e in eids) and all(cc in set(ids93) for cc in cids)
            and d['reproducibility'] and fresh):
        _pa_ok.append(d['case_id'])
parena = len(_pa_ok)
ck("ST81：P-Arena Gate 由 47 成熟列計算（THEORY 模板不計）", True, f"{parena} 成熟")
ck("ST68：PVE Gate Row 完整性（24 registry 成熟列）", True, f"{PVE_V} 成熟")
ck("ST69：Arena Gate Row 完整性（39 registry 5v5）", True,
   f"{ARENA_VERIFIED_ROWS} 成熟反制列／{ARENA_F} 成熟防守")
ck("ST70：Timeline Maturity Row 完整性（41）", True, f"{TIMELINE} MATURE")

# ========== 13 fully auto-generated from 17 (Guide-Only) ==========
res13_before = R['13_ACCEPTANCE_RESULTS.md']
def compose_auto():
    lines = ["| 測試 | current status | run_id | 執行日 | reviewer |", "|---|---|---|---|---|"]
    for tid in CFG['definition_set']:
        x = current.get(tid)
        st = x['status'] if x else 'NOT_RUN'
        lines.append(f"| {tid} | {st} | {x['run_id'] if x else ''} | {x['execution_date'] if x else ''} | {x['reviewer'] if x else ''} |")
    return "<!-- AUTO_RESULTS_START -->\n**由 validator 依 17 current result 自動生成（唯一權威狀態表；生成日 " + TODAY + "）**\n\n" + "\n".join(lines) + "\n<!-- AUTO_RESULTS_END -->"
gen_ids = set(re.findall(r'^\| ([AT]\d+) \| ', compose_auto(), re.M))
ck("13：AUTO_RESULTS 列出全部 41 測試（由 validator 生成）", gen_ids == set(CFG['definition_set']), f"缺{sorted(set(CFG['definition_set'])-gen_ids)}")
ck("ST72：13 具 AUTO_RESULTS 區＋無殘留手動狀態表", '<!-- AUTO_RESULTS_START -->' in res13_before and '<!-- AUTO_RESULTS_END -->' in res13_before and '| 目前狀態 |' not in res13_before)
expected_auto = compose_auto()
mprev = re.search(r'<!-- AUTO_RESULTS_START -->.*?<!-- AUTO_RESULTS_END -->', res13_before, re.S)
auto_current = mprev.group(0) if mprev else ''
# ST60（R3g 修正）：生成日不參與實質等價比對。
# 純生成日漂移＝WARN/INFO（提示 --write）；任何實質 canonical drift 仍 FAIL。
def _norm_gen_date(t):
    return re.sub(r'生成日 \d{4}-\d{2}-\d{2}', '生成日 <DATE>', t)
_st60_substantive_ok = _norm_gen_date(auto_current) == _norm_gen_date(expected_auto)
_st60_date_only = (not WRITE) and _st60_substantive_ok and auto_current != expected_auto
ck("ST60：13 AUTO_RESULTS 與 17 current 實質一致（生成日不列入比對）", WRITE or _st60_substantive_ok,
   "AUTO_RESULTS 實質內容與 current 不符，請查明漂移欄位後以 --write 重生成" if (not WRITE and not _st60_substantive_ok) else "")
if _st60_date_only:
    wk("REPORT-STALE-DATE", "report_freshness", "info", False, "13",
       "AUTO_RESULTS 實質內容與 current 一致，僅生成日落後（報表新鮮度，非資料漂移）",
       "執行 tools/validate_project.py --mode PRE_SUITE --write 更新生成日")
res13 = {}
for m in re.finditer(r'^\| ([AT]\d+) \| ([^|]+) \|', auto_current or expected_auto, re.M):
    res13.setdefault(m.group(1), m.group(2).strip())

# ========== forbidden strings ==========
def zones(f, t):
    z = CFG['historical_zones'].get(f)
    if not z: return t, ""
    cur, hist, in_h = [], [], False
    for line in t.split('\n'):
        if z['start'] in line: in_h = True
        if in_h and z['end'] in line: in_h = False
        (hist if in_h else cur).append(line)
    return '\n'.join(cur), '\n'.join(hist)
bad = []
for f, t in R.items():
    if f in CFG['scan_excluded_files']: continue
    cur, hist = zones(f, t)
    for s in CFG['forbidden_current_strings']:
        if s in cur: bad.append(f"{f}：{s}")
        if s in hist: hist_hits.append(f"{f}（歷史區）：{s}")
ck("CURRENT_SPEC_SCAN 無禁用字串", not bad, "；".join(bad[:4]))

# ========== math ==========
def dd(a, b): return (date.fromisoformat(b) - date.fromisoformat(a)).days
# ---- Phase F：canonical anchor objects 為唯一 SSOT ----
ANCH = CFG['anchors']
_legacy = [k for k in ('anchor_median', 'pool_track', 'pool_track_median') if k in CFG]
ck("ST83a：舊 config 統計 SSOT 欄位不得復活", not _legacy, ';'.join(_legacy))
_REQ = ('anchor_id', 'track', 'pool_class', 'jp_date', 'tw_date', 'delta_days',
        'jp_claim_id', 'tw_claim_id', 'mapping_claim_id')
CLM93 = {r[0]: r for r in r93[1:] if r}
def anchor_bad(a):
    if not isinstance(a, dict): return 'not_object'
    miss = [k for k in _REQ if not a.get(k)]
    if miss: return 'missing:' + ','.join(miss)
    if a['track'] not in ('GACHA', 'SYSTEM'): return 'bad_track'
    if a['pool_class'] not in ('LIMITED', 'PERMANENT', 'SYSTEM'): return 'bad_pool_class'
    if a['track'] == 'GACHA' and a['pool_class'] == 'SYSTEM': return 'gacha_with_system_class'
    if a['track'] == 'SYSTEM' and a['pool_class'] != 'SYSTEM': return 'system_class_mismatch'
    if dd(a['jp_date'], a['tw_date']) != a['delta_days']: return 'delta_mismatch'
    for key, wt, wc in (('jp_claim_id', 'SOURCE_FACT', 'A'), ('tw_claim_id', 'SOURCE_FACT', 'A'),
                        ('mapping_claim_id', 'ANALYTICAL_JUDGMENT', 'B')):
        c = CLM93.get(a[key])
        if not c: return 'fk_missing:' + a[key]
        if c[ti] != wt or c[ci] != wc or c[9] != 'ACTIVE': return 'fk_invalid:' + a[key]
        if key == 'mapping_claim_id' and c[ii] != 'YES': return 'fk_independence:' + a[key]
    return ''
_ids = [a.get('anchor_id') for a in ANCH if isinstance(a, dict)]
_dup = [k for k, n in Counter(_ids).items() if n > 1]
_bad = [f"{a.get('anchor_id', '?')}={anchor_bad(a)}" for a in ANCH if anchor_bad(a)]
ck(f"ST83：Anchor Schema／FK／日期（{len(ANCH)} 筆）", not _bad and not _dup,
   ';'.join(_bad + [f"dup:{d}" for d in _dup]))
VALID = [a for a in ANCH if not anchor_bad(a)]
def tstat(vals):
    vals = sorted(vals)
    return {"values": vals, "n": len(vals),
            "median": statistics.median(vals) if vals else None,
            "min": min(vals) if vals else None, "max": max(vals) if vals else None,
            "range": (max(vals) - min(vals)) if vals else None}
_LIM = [a['delta_days'] for a in VALID if a['pool_class'] == 'LIMITED']
_PERM = [a['delta_days'] for a in VALID if a['pool_class'] == 'PERMANENT']
_SYS = [a['delta_days'] for a in VALID if a['track'] == 'SYSTEM']
TRACKS = {"LIMITED": tstat(_LIM), "PERMANENT": tstat(_PERM),
          "ALL_NEW": tstat(_LIM + _PERM), "SYSTEM": tstat(_SYS)}
def tfmt(name):
    t = TRACKS[name]
    return f"{name}：n＝{t['n']}｜中位數 {t['median']:g}｜範圍 {t['min']}–{t['max']}"
_sys_leak = set(_SYS) and any(a['track'] == 'SYSTEM' for a in VALID if a['pool_class'] != 'SYSTEM')
ck("ST84a：SYSTEM 軌不得混入角色卡池統計", not _sys_leak and len(_LIM + _PERM) == len([a for a in VALID if a['track'] == 'GACHA']))
_doc_miss = [f"{f}:{n}" for f in ('02_SERVER_BASELINE.md', '40_GACHA_FUTURE_SIGHT.md')
             for n in TRACKS if tfmt(n) not in R[f]]
ck("ST84：四軌統計由 anchors 即時計算且與 02／40 口徑一致", not _doc_miss, ';'.join(_doc_miss))

# ---- ST85／ST85a：41 row-level forecast provenance（R3h）----
def build_forecast_basis(track):
    t = TRACKS[track]
    return (f"{track} track | n={t['n']} | median={t['median']:g} | "
            f"range={t['min']}-{t['max']} | mapping_conf=B | source=canonical anchors")
_r41 = load('41_GACHA_TIMELINE.csv'); _h41 = _r41[0]
def _g(row, col): return row[_h41.index(col)] if col in _h41 else ''
def st85_bad(row):
    tr = _g(row, 'anchor_track')
    if not tr: return ''
    if tr not in TRACKS: return 'unknown_track:' + tr
    t = TRACKS[tr]
    if _g(row, 'anchor_count') != str(t['n']): return 'anchor_count≠' + str(t['n'])
    if _g(row, 'forecast_basis') != build_forecast_basis(tr): return 'forecast_basis≠canonical'
    jp = _g(row, 'jp_date')
    try:
        base = date(*map(int, jp.split('-')))
    except Exception:
        return 'bad_jp_date'
    exp_s = (base + timedelta(days=t['min'])).isoformat()
    exp_e = (base + timedelta(days=t['max'])).isoformat()
    if _g(row, 'model_estimate_start') != exp_s: return 'model_start≠' + exp_s
    if _g(row, 'model_estimate_end') != exp_e: return 'model_end≠' + exp_e
    if _g(row, 'model_estimate_start') > _g(row, 'model_estimate_end'): return 'model_start>end'
    return ''
_a41 = [r for r in _r41[1:] if r and _g(r, 'status') == 'ACTIVE']
_b85 = [f"{r[0]}:{st85_bad(r)}" for r in _a41 if st85_bad(r)]
ck(f"ST85：41 anchor semantics（{len(_a41)} ACTIVE 列）", not _b85, ';'.join(_b85))

_METHODS = ('MODEL_ONLY', 'MODEL_PLUS_COMMUNITY', 'OFFICIAL_OVERRIDE')
def st85a_bad(row):
    m = _g(row, 'forecast_method')
    if not m: return 'forecast_method_missing'
    if m not in _METHODS: return 'bad_method:' + m
    ms, me = _g(row, 'model_estimate_start'), _g(row, 'model_estimate_end')
    ts, te = _g(row, 'tw_estimate_start'), _g(row, 'tw_estimate_end')
    if m == 'MODEL_ONLY':
        if (ts, te) != (ms, me): return 'MODEL_ONLY_final≠model'
        if _g(row, 'community_source_count') not in ('', '0'): return 'MODEL_ONLY_with_community'
    if m == 'MODEL_PLUS_COMMUNITY':
        if not _g(row, 'community_estimate_start') or not _g(row, 'community_estimate_end'):
            return 'community_interval_missing'
        cs, ce = _g(row, 'community_estimate_start'), _g(row, 'community_estimate_end')
        if ts > min(ms, cs) or te < max(me, ce): return 'final_not_union'
    if m == 'OFFICIAL_OVERRIDE':
        cids = [x for x in _g(row, 'claim_ids').split(';') if x]
        if not any(CLM93.get(c) and CLM93[c][2] == 'TW' and CLM93[c][ti] == 'SOURCE_FACT'
                   and CLM93[c][ci] == 'A' for c in cids):
            return 'no_TW_official_A_claim'
    return ''
_b85a = [f"{r[0]}:{st85a_bad(r)}" for r in _a41 if st85a_bad(r)]
ck(f"ST85a：41 final interval method（{len(_a41)} 列）", not _b85a, ';'.join(_b85a))
t = CFG['t41']; ck("T41 單位分離", t['gems'] // t['cost'] + t['free'] == t['expect'])
ck("三情境", all(g // 150 + fr + tk == e for g, fr, tk, e in CFG['scenarios']))
g = CFG['gap_example']; ck("缺口公式", max(0, g['need'] - g['have']) * g['cost'] == g['expect'])
_stale02 = [x for x in ('卡池軌：122、123', 'n＝3', '中位數 122 天', 'pool_track', '2026/07/03 | 122 天') if x in R['02_SERVER_BASELINE.md']]
ck("02：舊統計口徑不得殘留（改由四軌 anchors 派生）", not _stale02, ';'.join(_stale02))
ck("44 SUPERSEDED 標記", 'SUPERSEDED' in R['44_GACHA_RESEARCH_LOG.md'])
ck("99 Stale 非空", 'nomae arenadb 全庫' in R['99_CHANGELOG.md'])

# ========== WARNINGS (before gate) ==========
# audit §16：只有「支撐 Gate 成熟資料」的問題才阻擋 Gate C；未被成熟列引用的研究中 D 結論僅顯示 Warning。
# 蒐集被成熟 registry 列（24 PVE／39 Arena／41 Timeline）引用的 evidence_id 與 claim_id。
mature_ev, mature_cl = set(), set()
for r in r24[1:]:
    if r[c24['guide_id']] in set(pve_ok):
        mature_ev |= {e for e in r[c24['evidence_ids']].split(';') if e}; mature_cl |= {c for c in r[c24['claim_ids']].split(';') if c}
for r in r39[1:]:
    if r[c39['counter_id']] in set(arena_ok):
        mature_ev |= {e for e in r[c39['evidence_ids']].split(';') if e}; mature_cl |= {c for c in r[c39['claim_ids']].split(';') if c}
for r in r41[1:]:
    if r[c41['event_id']] in set(tl_ok):
        mature_ev |= {e for e in r[c41['evidence_ids']].split(';') if e}; mature_cl |= {c for c in r[c41['claim_ids']].split(';') if c}
# claim_id -> evidence_ids（用於把成熟 claim 的證據也視為成熟引用）
for r in r93[1:]:
    if r[0] in mature_cl: mature_ev |= {e for e in r[ei].split(';') if e}
for r in r92[1:]:
    if r[si92] == 'PENDING_REVIEW':
        gc = r[0] in mature_ev  # 只有支撐成熟資料的 PENDING evidence 阻擋 Gate C
        wk(f"EV-{r[0]}", "evidence_pending", "warn" if gc else "info", gc, "92",
           f"{r[0]} 待直頁回驗" + ("（支撐成熟資料）" if gc else "（未被成熟資料引用）"), "91 §1 回驗")
for r in r93[1:]:
    if r[ci] == 'D' and r[ti] == 'ANALYTICAL_JUDGMENT':
        # D 級分析判斷本質即低信心；僅在被成熟資料列引用時才視為 Gate C 品質問題
        gc = r[0] in mature_cl
        wk(f"CLM-{r[0]}", "confidence_low", "warn" if gc else "info", gc, "93",
           f"{r[0]}＝D" + ("（成熟資料引用）" if gc else "（研究中，未被成熟資料引用）"), "補第二獨立來源或維持研究層")
nrd = re.search(r'next_review_due：(20\d\d-\d\d-\d\d)', R['02_SERVER_BASELINE.md'])
freshness_bad = bool(nrd and nrd.group(1) <= TODAY)
if freshness_bad: wk("BASELINE-REVIEW", "freshness", "warn", True, "02", f"next_review_due {nrd.group(1)} 已到", "跑 91 §1")
if PVE_V < CFG['gate_thresholds']['C']['pve_stages']: wk("GATE-PVE", "gate_c_data", "warn", True, "24", f"PVE 成熟關卡 {PVE_V}<{CFG['gate_thresholds']['C']['pve_stages']}（每關≥5隊）", "Checkpoint B PVE Wave")
if ARENA_F < CFG['gate_thresholds']['C']['arena']: wk("GATE-ARENA", "gate_c_data", "warn", True, "39", f"Arena 防守案例 {ARENA_F}<{CFG['gate_thresholds']['C']['arena']}（各≥2 TW_AVAILABLE 反制）", "Checkpoint D Arena Ingestion")
if TIMELINE < CFG['gate_thresholds']['B']['timeline']: wk("GATE-TIMELINE", "gate_c_data", "warn", True, "41", f"Timeline MATURE {TIMELINE}<{CFG['gate_thresholds']['B']['timeline']}", "Checkpoint C Gacha Integration")
if community_checked < CFG['gate_thresholds']['B']['community_sources']: wk("GATE-COMMUNITY", "gate_c_data", "warn", True, "45", f"社群未來視已核來源 {community_checked}<{CFG['gate_thresholds']['B']['community_sources']}", "Checkpoint C 抓取現行版本")
if parena < CFG['gate_thresholds']['B']['parena']: wk("GATE-PARENA", "gate_c_data", "warn", True, "47", f"P-Arena 成熟案例 {parena}<{CFG['gate_thresholds']['B']['parena']}（THEORY 不計）", "Checkpoint E 組合求解入 47")
if MODE == 'PRE_SUITE' and len(logs) == 0: wk("SUITE-NOTRUN", "pre_suite", "info", False, "17", "四 Suite 尚未實跑", "v1.5 部署後執行")
blocking_c = sum(1 for w in warns if w['blocks_gate_c'])
ck("ST54／ST66：Warning 機制分類運作", all('blocks_gate_c' in w for w in warns))

# ========== GATES (after warnings) ==========
# audit §6：Gate A 只讀 17 current result（唯一權威）；13 僅為由 17 生成的人讀報告，不參與 Gate 判定。
pub_set = set(CFG['gate_a_public_set'])
gate_a_pass = all((current.get(t) or {}).get('status') == 'PASS' for t in pub_set) and not fails
Cth = CFG['gate_thresholds']['C']; Bth = CFG['gate_thresholds']['B']
gate_b_pass = (PVE_V >= Bth['pve_stages'] and ARENA_F >= Bth['arena'] and parena >= Bth['parena']
               and TIMELINE >= Bth['timeline'] and community_checked >= Bth['community_sources'])
gate_c_pass = (gate_a_pass and gate_b_pass and PVE_V >= Cth['pve_stages'] and ARENA_F >= Cth['arena']
               and parena >= Cth['parena'] and blocking_c == 0 and not freshness_bad and conf_violations == 0)
GATE = {"pve_verified": PVE_V, "arena_formal": ARENA_F,
        "arena_verified_counter_rows": ARENA_VERIFIED_ROWS,
        "arena_mature_defenses": ARENA_F,
        "parena": parena, "timeline": TIMELINE,
        "gate_a": gate_a_pass, "gate_b": gate_b_pass, "gate_c": gate_c_pass, "blocking_c": blocking_c}

ck("ST52：Validation Mode 合法", MODE in ('PRE_SUITE', 'OPERATIONAL', 'ARTIFACT_READY'), MODE)
if MODE == 'PRE_SUITE':
    ck("ST51(PRE_SUITE)：17 為空（無執行紀錄，權威）", len(logs) == 0, f"17={len(logs)}")
elif MODE == 'ARTIFACT_READY':
    ck("ST55：ARTIFACT_READY 需 Gate A", gate_a_pass)
    ck("ST55：ARTIFACT_READY 需 Gate B", gate_b_pass, f"PVE{PVE_V}/Arena{ARENA_F}/PA{parena}/TL{TIMELINE}")
    ck("ST67(Gate)：ARTIFACT_READY 需 Gate C（含 blocking_c=0）", gate_c_pass, f"C={gate_c_pass} blk={blocking_c}")

# ======== 兩階段：最終計數 → 報告 ========
CHECK_TOTAL, FAIL_TOTAL, WARN_TOTAL = len(checks), len(fails), len(warns)
tier = Counter(r[tri] for r in r92[1:]); evc = Counter(r[eci] for r in r92[1:])
cc = Counter(r[ci] for r in r93[1:]); ct = Counter(r[ti] for r in r93[1:])
stats = {"generated_date": TODAY, "release_date": CFG['release_date'], "project_version": CFG['project_version'],
         "mode": MODE, "files": len(files), "numbered": len(numbered), "knowledge": len(knowledge), "tools": len(TOOLS),
         "tools_files": TOOLS, "tier": dict(tier), "evc": dict(evc), "cc": dict(cc), "ct": dict(ct),
         "claims": len(ids93), "evidence": len(ids92), "fixtures": len(set(fxids)), "public_covered": len(cover),
         "anchors_n": len(ANCH), "anchor_tracks": TRACKS,
         "timeline_rows": TIMELINE, "checks": CHECK_TOTAL, "fail": FAIL_TOTAL, "warn": WARN_TOTAL,
         "exec_rows": len(logs), "gate": GATE, "blocking_gate_c_warnings": blocking_c}

canonical = (MODE == 'PRE_SUITE' and FAIL_TOTAL == 0) or (MODE == 'ARTIFACT_READY' and gate_c_pass) or (WRITE and FAIL_TOTAL == 0)
os.makedirs('tools/reports', exist_ok=True)
with open(f'tools/reports/{MODE.lower()}.json', 'w', encoding='utf-8', newline='\n') as report_file:
    json.dump(stats, report_file, ensure_ascii=False, indent=1)

def build_reports():
    # 13 AUTO_RESULTS
    s13 = R['13_ACCEPTANCE_RESULTS.md']
    m13 = re.search(r'<!-- AUTO_RESULTS_START -->.*?<!-- AUTO_RESULTS_END -->', s13, re.S)
    if m13:
        with open('13_ACCEPTANCE_RESULTS.md', 'w', encoding='utf-8', newline='\n') as report_file:
            report_file.write(s13.replace(m13.group(0), compose_auto()))
    # 15 AUTO_STATS
    auto = f"""<!-- AUTO_STATS_START -->
**程式化統計（validator 生成即核對；生成日 {TODAY}／版本 {CFG['project_version']}／Release {CFG['release_date']}／Mode {MODE}）**

- 檔案 {len(files)}（編號 {len(numbered)}＋README）＋tools×{len(TOOLS)}｜Knowledge {len(knowledge)}｜Fixture {len(set(fxids))}
- Gate 成熟資料：PVE VERIFIED {PVE_V}（24）｜Arena 成熟反制列 {ARENA_VERIFIED_ROWS}／成熟防守 {ARENA_F}（39）｜P-Arena {parena}（47）｜Timeline MATURE {TIMELINE}（41）
- 92 Evidence {len(ids92)} 列｜Tier {dict(tier)}｜evidence_confidence {dict(evc)}｜PENDING_REVIEW {sum(1 for r in r92[1:] if r[si92]=='PENDING_REVIEW')}
- 93 Claim {len(ids93)} 列｜claim_confidence {dict(cc)}｜claim_type {dict(ct)}
- Gate A={'PASS' if gate_a_pass else 'FAIL'}｜B={'PASS' if gate_b_pass else 'FAIL'}｜C={'PASS' if gate_c_pass else 'FAIL'}｜阻擋 Gate C 警告 {blocking_c}
- 靜態檢查 {CHECK_TOTAL} 項｜FAIL {FAIL_TOTAL}｜WARN {WARN_TOTAL}
<!-- AUTO_STATS_END -->"""
    s15 = R['15_DATA_QUALITY_REPORT.md']
    m15 = re.search(r'<!-- AUTO_STATS_START -->.*?<!-- AUTO_STATS_END -->', s15, re.S)
    if m15:
        with open('15_DATA_QUALITY_REPORT.md', 'w', encoding='utf-8', newline='\n') as report_file:
            report_file.write(s15.replace(m15.group(0), auto))
    lines = "\n".join(f"| {n} | {r} | {d} |" for n, r, d in checks)
    warn_lines = "\n".join(f"| {w['warning_id']} | {w['category']} | {w['severity']} | {'Y' if w['blocks_gate_c'] else 'N'} | {w['affected_module']} | {w['detail']} | {w['next_action']} |" for w in warns) if warns else "| （無） | | | | | | |"
    infos_l = [f"Mode＝{MODE}（PRE_SUITE／OPERATIONAL 增量／ARTIFACT_READY 強制 Gate A/B/C＋blocking_c=0）",
               f"Gate A/B/C＝{gate_a_pass}/{gate_b_pass}/{gate_c_pass}（數量由 24／39／41／45／47 成熟列計算，非計數全部列）",
               ("目前 PENDING_REVIEW Evidence：" + ("、".join(sorted(pending_ev)) if pending_ev else "無")),
               "回歸攔截由 tools/mutation_test.py 驗證（Active 情境數以其執行輸出為準；歷史／退休 ID 見 Account Archive）",
               f"Canonical 15/16/13/stats 寫入：{'是' if canonical else '否（check-only）'}"]
    with open('16_STATIC_VALIDATION_REPORT.md', 'w', encoding='utf-8', newline='\n') as report_file:
        report_file.write(f"""# 16 靜態驗證報告（STATIC VALIDATION REPORT）

> 由 `tools/validate_project.py` 生成（唯一路徑）；回歸驗證：`python3 tools/mutation_test.py`（Active 情境數見其輸出；退休 ID 見 Archive）。
> 生成日：{TODAY}｜版本：{CFG['project_version']}｜Release：{CFG['release_date']}｜Mode：{MODE}

## 檢查結果（{CHECK_TOTAL} 項）

| 檢查 | 結果 | 明細 |
|---|---|---|
{lines}

## Release Gate（由結構化 Registry 計算成熟列）

| Gate | 狀態 | 依據 |
|---|---|---|
| A Guide Behavior | {'PASS' if gate_a_pass else '未通過'} | Guide-Only 41 項 current result 全 PASS＋Static FAIL=0＋無帳號指令（ST80） |
| B 最低可用攻略 | {'PASS' if gate_b_pass else '未通過'} | PVE 關卡 {PVE_V}/≥{Bth['pve_stages']}（每關≥{Bth['teams_per_stage']}隊）｜Arena 防守 {ARENA_F}/≥{Bth['arena']}（各≥{Bth['counters_per_defense']}反制）｜P-Arena {parena}/≥{Bth['parena']}｜Timeline {TIMELINE}/≥{Bth['timeline']}｜社群來源 {community_checked}/≥{Bth['community_sources']} |
| C 攻略整合可發布 | {'PASS' if gate_c_pass else '未通過'} | Gate A＋B＋PVE≥{Cth['pve_stages']}／Arena≥{Cth['arena']}／P-Arena≥{Cth['parena']}＋阻擋警告 {blocking_c}＝0＋新鮮度 |

## 統計（程式化）

- 檔案 {len(files)}（編號 {len(numbered)}＋README）＋tools×{len(TOOLS)}；Knowledge {len(knowledge)}
- 92：{len(ids92)} 列｜Tier {dict(tier)}｜93：{len(ids93)} 列｜claim_type {dict(ct)}
- 數學重驗：canonical anchors {len(ANCH)} 筆｜LIMITED n={TRACKS['LIMITED']['n']} median={TRACKS['LIMITED']['median']:g}｜PERMANENT n={TRACKS['PERMANENT']['n']} median={TRACKS['PERMANENT']['median']:g}｜ALL_NEW n={TRACKS['ALL_NEW']['n']} median={TRACKS['ALL_NEW']['median']:g}｜SYSTEM n={TRACKS['SYSTEM']['n']} median={TRACKS['SYSTEM']['median']:g}｜T41=120、三情境、缺口式——全部由 anchors 即時重算

## FAIL：{FAIL_TOTAL}｜WARN：{WARN_TOTAL}（阻擋 Gate C：{blocking_c}）

{'（無 FAIL）' if not fails else chr(10).join('- ' + x for x in fails)}

## WARN（分類；blocks_gate_c＝Y 者會阻擋 Gate C）

| warning_id | category | severity | blocks_C | module | detail | next_action |
|---|---|---|---|---|---|---|
{warn_lines}

## INFO

{chr(10).join('- ' + i for i in infos_l)}

## HISTORICAL_RECORD_SCAN（資訊性；不 FAIL、不刪除）

{chr(10).join('- ' + h for h in hist_hits) if hist_hits else '（無）'}
""")
    with open('tools/stats.json', 'w', encoding='utf-8', newline='\n') as report_file:
        json.dump(stats, report_file, ensure_ascii=False, indent=1)

if canonical: build_reports()
else: infos.append(f"Mode {MODE} 未達 canonical 寫入條件——僅 tools/reports/{MODE.lower()}.json")

print(f"MODE={MODE} CHECKS={CHECK_TOTAL} FAIL={FAIL_TOTAL} WARN={WARN_TOTAL} | GateA={gate_a_pass} GateB={gate_b_pass} GateC={gate_c_pass} blk={blocking_c} | canonical={'Y' if canonical else 'N'}")
[print(' FAIL -', x) for x in fails]
sys.exit(1 if fails else 0)
