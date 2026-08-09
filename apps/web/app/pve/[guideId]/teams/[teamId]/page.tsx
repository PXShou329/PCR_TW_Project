import { ApiError } from "@pcr-tw/api-client";
import { Badge, Definition, Panel } from "@pcr-tw/ui";
import Link from "next/link";
import { notFound } from "next/navigation";
import { EvidenceDrawer } from "../../../../../components/evidence-drawer";
import { OperationTimeline } from "../../../../../components/operation-timeline";
import { RequirementsMatrix } from "../../../../../components/requirements-matrix";
import { TeamRoster } from "../../../../../components/team-roster";
import { serverApi } from "../../../../../lib/api";
import { operationLabel, statusLabel, statusTone } from "../../../../../lib/presentation";

export const dynamic = "force-dynamic";

export default async function TeamPage({
  params,
}: {
  params: Promise<{ guideId: string; teamId: string }>;
}) {
  const { guideId, teamId } = await params;
  let response;
  try {
    response = await serverApi().getTeam(teamId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
  const team = response.data;
  if (team.guide_id !== guideId) notFound();

  return (
    <>
      <nav className="breadcrumb" aria-label="麵包屑">
        <Link href="/">深域攻略</Link><span aria-hidden="true">/</span>
        <Link href={`/pve/${guideId}`}>{team.stage}</Link><span aria-hidden="true">/</span>
        <span>{team.team_id}</span>
      </nav>

      <header className="page-heading team-heading">
        <div className="badge-row">
          <Badge tone={statusTone(team.clear_status)}>{statusLabel(team.clear_status)}</Badge>
          <Badge tone={statusTone(team.operation_mode)}>{operationLabel(team.operation_mode)}</Badge>
          <Badge tone={team.tw_availability_check === "PASS" ? "success" : "warning"}>
            {team.tw_availability_check === "PASS" ? "全員台服可用" : "台服可用性未確認"}
          </Badge>
        </div>
        <p className="eyebrow">{team.team_id}</p>
        <h1>{team.stage} · {operationLabel(team.operation_mode)}</h1>
        <p>{team.notes}</p>
      </header>

      <div className="detail-layout">
        <div className="detail-main">
          <Panel>
            <div className="section-heading compact"><div><p className="eyebrow">TEAM</p><h2>五人隊伍</h2></div></div>
            <TeamRoster members={team.members} />
          </Panel>

          {team.operation_mode === "SOURCE_CONFLICT" ? (
            <Panel className="source-conflict">
              <p className="eyebrow">SOURCE CONFLICT</p>
              <h2>AUTO／SEMI_AUTO 聲明互相衝突</h2>
              <p>平台分來源保存原始聲明，不合併成單一操作模式，也不替缺少的資訊作推測。</p>
              <ul>
                {team.requirements.operation_mode_claims.map((claim) => (
                  <li key={`${claim.source_id}-${claim.mode}`}>
                    <code>{claim.source_id}</code><Badge tone="warning">{operationLabel(claim.mode)}</Badge>
                  </li>
                ))}
              </ul>
            </Panel>
          ) : null}

          <section className="section-block" aria-labelledby="requirements-heading">
            <div className="section-heading">
              <div><p className="eyebrow">SLOT REQUIREMENTS</p><h2 id="requirements-heading">逐 Slot 條件</h2></div>
              <p>「未確認」就是來源沒有足夠資訊，不代表無需求。</p>
            </div>
            <RequirementsMatrix members={team.members} requirements={team.requirements} />
          </section>

          <OperationTimeline timeline={team.timeline} members={team.members} />
        </div>

        <aside className="detail-aside" aria-label="隊伍證據與中繼資料">
          <Panel>
            <p className="eyebrow">EVIDENCE</p>
            <h2>證據抽屜</h2>
            <p>點選 Evidence 查看來源標題、正文支持內容、定位與限制。</p>
            <EvidenceDrawer evidenceIds={team.evidence_ids} />
          </Panel>
          <Panel className="metadata-panel">
            <h2>隊伍資料</h2>
            <dl>
              <Definition term="穩定性">{team.stability}</Definition>
              <Definition term="驗證日">{team.verified_date}</Definition>
              <Definition term="下次複核">{team.last_review_due ?? "未排定"}</Definition>
              <Definition term="Schema">{team.requirements.schema_version}</Definition>
              <Definition term="借角">
                {team.requirements.support.unit === "UNKNOWN" ? "未確認" : team.requirements.support.unit}
              </Definition>
            </dl>
          </Panel>
        </aside>
      </div>
    </>
  );
}
