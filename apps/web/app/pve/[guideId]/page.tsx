import { ApiError, type TeamSummary } from "@pcr-tw/api-client";
import { Badge, Definition, Panel } from "@pcr-tw/ui";
import Link from "next/link";
import { notFound } from "next/navigation";
import { TeamRoster } from "../../../components/team-roster";
import { serverApi } from "../../../lib/api";
import { operationLabel, statusLabel, statusTone } from "../../../lib/presentation";

export const dynamic = "force-dynamic";

export default async function StagePage({ params }: { params: Promise<{ guideId: string }> }) {
  const { guideId } = await params;
  let response;
  try {
    response = await serverApi().getStage(guideId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  const stage = response.data;
  const coverage = stage.coverage;
  const percent = Math.min(100, Math.round((coverage.verified_distinct_teams / coverage.maturity_target) * 100));

  return (
    <>
      <nav className="breadcrumb" aria-label="麵包屑">
        <Link href="/">深域攻略</Link><span aria-hidden="true">/</span><span>{stage.area} {stage.stage}</span>
      </nav>

      <header className="stage-hero">
        <div>
          <div className="badge-row">
            <Badge tone="info">{stage.server}</Badge>
            <Badge tone={statusTone(stage.status)}>{statusLabel(stage.status)}</Badge>
            <Badge tone={statusTone(stage.reproducibility)}>
              重現性：{statusLabel(stage.reproducibility)}
            </Badge>
          </div>
          <p className="eyebrow">{stage.area.toUpperCase()} DEEP ZONE</p>
          <h1>{stage.area}深域 {stage.stage}</h1>
          <p>適用版本：{stage.applicable_version} · 最後核對：{stage.verified_date}</p>
        </div>
        <Panel className="coverage-panel">
          <span>不同五人實證隊</span>
          <strong>{coverage.verified_distinct_teams}<small> / {coverage.maturity_target}</small></strong>
          <div className="progress-track" aria-hidden="true"><span style={{ width: `${percent}%` }} /></div>
          <p>距成熟門檻仍差 {coverage.remaining} 隊，因此本關維持 PROVISIONAL。</p>
        </Panel>
      </header>

      <Panel className="truth-notice">
        <div>
          <p className="eyebrow">MATURITY DISCLOSURE</p>
          <h2>已確認 {coverage.verified_distinct_teams} 隊，不等於成熟攻略</h2>
        </div>
        <p>{stage.notes}</p>
      </Panel>

      <section className="section-block" aria-labelledby="teams-heading">
        <div className="section-heading">
          <div><p className="eyebrow">VERIFIED EFFECTIVE TEAMS</p><h2 id="teams-heading">實際通關隊伍</h2></div>
          <p>相同五人多來源已合併，只計一隊。</p>
        </div>
        <div className="team-grid">
          {stage.teams.map((team) => <TeamCard guideId={stage.guide_id} key={team.team_id} team={team} />)}
        </div>
      </section>

      <Panel className="metadata-panel">
        <h2>資料狀態</h2>
        <dl>
          <Definition term="來源層級">{stage.source_tier}</Definition>
          <Definition term="Claim 信心">{stage.claim_confidence}</Definition>
          <Definition term="Evidence 數">{stage.evidence_ids.length}</Definition>
          <Definition term="下次複核">{stage.last_review_due ?? "未排定"}</Definition>
        </dl>
      </Panel>
    </>
  );
}

function TeamCard({ guideId, team }: { guideId: string; team: TeamSummary }) {
  return (
    <article className="team-card panel">
      <div className="team-card__heading">
        <div><p className="eyebrow">{team.team_id}</p><h3>{operationLabel(team.operation_mode)}</h3></div>
        <Badge tone={statusTone(team.clear_status)}>{statusLabel(team.clear_status)}</Badge>
      </div>
      {team.operation_mode === "SOURCE_CONFLICT" ? (
        <p className="inline-warning">各來源對 AUTO／SEMI_AUTO 的聲明不同；詳情頁會分來源列出，不替來源裁決。</p>
      ) : null}
      <TeamRoster members={team.members} />
      <div className="team-card__footer">
        <span>{team.stability}</span>
        <Link className="card-link" href={`/pve/${guideId}/teams/${team.team_id}`}>
          查看條件與 Evidence <span aria-hidden="true">→</span>
        </Link>
      </div>
    </article>
  );
}
