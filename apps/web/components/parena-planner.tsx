"use client";

import { ApiError, createApiClient, type ParenaEnvironment, type ParenaSolveData, type PvpCharacter } from "@pcr-tw/api-client";
import { Badge, Definition, EmptyState, Panel } from "@pcr-tw/ui";
import { type FormEvent, useMemo, useState } from "react";
import { ArenaRoster } from "./arena-roster";
import { EvidenceDrawer } from "./evidence-drawer";

const SLOT_COUNT = 15;

export function ParenaPlanner({ characters, environments, initialWarnings }: {
  characters: PvpCharacter[];
  environments: ParenaEnvironment[];
  initialWarnings: string[];
}) {
  const options = useMemo(() => [...characters].sort((a, b) => a.tw_name.localeCompare(b.tw_name, "zh-Hant")), [characters]);
  const [environment, setEnvironment] = useState(environments[0]?.environment_version ?? "");
  const [units, setUnits] = useState(() => Array<string>(SLOT_COUNT).fill(""));
  const [result, setResult] = useState<ParenaSolveData | null>(null);
  const [warnings, setWarnings] = useState(initialWarnings);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const selected = units.filter(Boolean);
  const valid = environment.length > 0 && selected.length === SLOT_COUNT && new Set(selected).size === SLOT_COUNT;

  function resetQueryState() {
    setResult(null);
    setWarnings(initialWarnings);
    setState("idle");
  }

  function updateEnvironment(value: string) {
    setEnvironment(value);
    resetQueryState();
  }

  function updateUnit(index: number, value: string) {
    setUnits((current) => current.map((unit, slot) => slot === index ? value : unit));
    resetQueryState();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!valid) return;
    setState("loading");
    try {
      const response = await createApiClient({ baseUrl: "" }).solveParena({
        server: "TW",
        environment_version: environment,
        defense_teams: [units.slice(0, 5), units.slice(5, 10), units.slice(10, 15)],
      });
      setResult(response.data);
      setWarnings(response.meta.warnings);
      setState("idle");
    } catch (error) {
      setWarnings([error instanceof ApiError ? error.problem?.detail?.code ?? error.message : "SOLVER_UNAVAILABLE"]);
      setState("error");
    }
  }

  return <>
    <header className="page-heading">
      <p className="eyebrow">PRINCESS ARENA · TW · EXACT ONLY</p>
      <h1>公主競技場三隊規劃</h1>
      <p>輸入三隊完整防守後，只查詢同環境、完整 3×5 的實證通關案例；不猜隱藏隊、不回退 Similar。</p>
    </header>

    <Panel className="parena-query-panel">
      <div className="parena-query-heading"><div><p className="eyebrow">FULL VISIBLE DEFENSE</p><h2>三隊十五人</h2></div><div className="badge-row"><Badge tone="info">TW AVAILABLE</Badge><Badge>15 人不得重複</Badge></div></div>
      <form onSubmit={submit}>
        <label className="parena-environment"><span>環境版本</span><select disabled={state === "loading"} value={environment} onChange={(event) => updateEnvironment(event.target.value)}><option value="">目前沒有 mature 環境</option>{environments.map((row) => <option key={row.environment_version} value={row.environment_version}>{row.environment_version} · {row.verified_case_count} case</option>)}</select></label>
        <div className="parena-team-grid">
          {[0, 1, 2].map((teamIndex) => <fieldset className="parena-team" key={teamIndex}>
            <legend>防守隊伍 {teamIndex + 1}</legend>
            {[0, 1, 2, 3, 4].map((slotIndex) => {
              const index = teamIndex * 5 + slotIndex;
              return <label key={index}><span>位置 {slotIndex + 1}</span><select aria-label={`防守隊伍 ${teamIndex + 1} 位置 ${slotIndex + 1}`} disabled={state === "loading"} value={units[index]} onChange={(event) => updateUnit(index, event.target.value)}><option value="">選擇角色</option>{options.map((character) => <option disabled={units.includes(character.unit_key) && units[index] !== character.unit_key} key={character.unit_key} value={character.unit_key}>{character.tw_name} · {character.unit_key}</option>)}</select></label>;
            })}
          </fieldset>)}
        </div>
        <div className="parena-query-actions"><button className="primary-action" disabled={!valid || state === "loading"} type="submit">{state === "loading" ? "查詢中…" : "查詢三隊 exact 解法"}</button><p>{selected.length}/15 已選擇；{new Set(selected).size}/15 不重複。</p></div>
      </form>
    </Panel>

    {warnings.length > 0 ? <aside className="arena-warning" aria-label="P-Arena 資料限制"><div><p className="eyebrow">DATA LIMITS</p>{warnings.map((warning) => <p key={warning}>{warningText(warning)}</p>)}</div><div className="badge-row">{warnings.map((warning) => <Badge key={warning} tone="warning">{warning}</Badge>)}</div></aside> : null}
    {state === "error" ? <Panel><EmptyState eyebrow="FAIL CLOSED" title="查詢服務目前不可用"><p>平台沒有改用快取印象或相似隊伍補結果。</p></EmptyState></Panel> : null}
    {result && result.cases.length === 0 ? <Panel data-testid="parena-no-exact-result"><EmptyState eyebrow="NO EXACT PLAN" title="目前沒有可呈現的三隊實證解法"><p>輸入已通過 3×5、15 人不重複與 TW AVAILABLE 檢查；資料庫仍沒有符合的成熟 exact case。</p></EmptyState></Panel> : null}

    {result?.cases.map((caseRow) => <Panel className="parena-case" key={caseRow.case_id}>
      <div className="parena-case-heading"><div><p className="eyebrow">CASE · {caseRow.case_id}</p><h2>三場完整實證組合</h2></div><div className="badge-row">{caseRow.case_win_confidence === "D" ? <><Badge tone="warning">SINGLE_REPORT</Badge><Badge tone="warning">BLOCKS GATE C</Badge></> : <Badge tone="success">VERIFIED</Badge>}<Badge>CONFIDENCE {caseRow.case_win_confidence}</Badge><Badge>EXACT</Badge><Badge>{caseRow.environment_version}</Badge></div></div>
      <dl className="arena-facts"><Definition term="隱藏隊處理">{caseRow.hidden_team_mode}</Definition><Definition term="可重現性">{caseRow.reproducibility}</Definition><Definition term="Case 信心">{caseRow.case_win_confidence}</Definition><Definition term="核對日">{caseRow.verified_date}</Definition><Definition term="Case Claim"><code>{caseRow.case_win_claim_id}</code></Definition></dl>
      <div className="parena-matchups">{caseRow.matchups.map((matchup) => <article className="arena-counter-card" key={matchup.matchup_no}>
        <div className="arena-counter-card__heading"><div><p className="eyebrow">MATCHUP {matchup.defense_input_index}</p><h3>對應輸入隊伍 {matchup.defense_input_index}</h3></div><Badge tone="success">EXACT WIN</Badge></div>
        <ArenaRoster label={`隊伍 ${matchup.defense_input_index} 防守`} members={matchup.counter.defense_members} />
        <h4>實證反制隊伍</h4><ArenaRoster label={`隊伍 ${matchup.defense_input_index} 反制`} members={matchup.counter.counter_members} />
        <p>{matchup.counter.notes}</p><EvidenceDrawer compact evidenceIds={matchup.counter.evidence_ids} buttonLabel="開啟本場 Evidence" contextLocator={`47_PRINCESS_ARENA_CASE_REGISTRY.csv#${caseRow.case_id}`} />
      </article>)}</div>
      <div className="parena-case-footer"><div><p className="eyebrow">SOURCES</p>{caseRow.sources.map((source) => <a className="source-link" href={source.url} key={source.source_id} rel="noreferrer" target="_blank">{source.title} ↗</a>)}</div><EvidenceDrawer evidenceIds={caseRow.evidence_ids} buttonLabel="開啟 Case Evidence" contextLocator={`47_PRINCESS_ARENA_CASE_REGISTRY.csv#${caseRow.case_id}`} /></div>
    </Panel>)}

    <Panel className="arena-similar-panel"><div><p className="eyebrow">SIMILAR / HIDDEN</p><h2>推測功能未啟用</h2></div><p>結果只來自完整可見的 exact case；任何未知隊伍都保持未知。</p></Panel>
  </>;
}

function warningText(warning: string) {
  if (warning === "NO_MATURE_PARENA_CASE") return "目前 typed materialization 中沒有成熟 P-Arena case。";
  if (warning === "NO_EXACT_PARENA_PLAN") return "有成熟資料，但沒有符合本環境與完整三隊簽章的案例。";
  if (warning === "NO_PARENA_MATERIALIZATION") return "目前快照沒有 P-Arena typed closure，服務已 fail closed。";
  if (warning === "CASE_WIN_SINGLE_SOURCE_REFERENCE") return "此 Case 的整體勝場僅有單一玩家回報，僅供參考。";
  if (warning === "CASE_WIN_CONFIDENCE_D_BLOCKS_GATE_C") return "此 Case 信心為 D；可列入 Gate B，但會阻擋 Gate C。";
  return `資料限制：${warning}`;
}
