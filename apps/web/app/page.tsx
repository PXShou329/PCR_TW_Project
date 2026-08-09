import type { StageSummary } from "@pcr-tw/api-client";
import { Badge, Panel } from "@pcr-tw/ui";
import Link from "next/link";
import { serverApi } from "../lib/api";
import { statusLabel, statusTone } from "../lib/presentation";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const api = serverApi();
  const [baseline, stages] = await Promise.all([api.getBaseline(), api.getStages()]);
  const featured = baseline.data.featured_stage ?? stages.data[0];

  return (
    <>
      <section className="hero">
        <div className="hero__copy">
          <p className="eyebrow">TAIWAN SERVER · EVIDENCE FIRST</p>
          <h1>找得到證據的攻略，<br />才進得了隊伍庫。</h1>
          <p className="hero__lead">
            台服為主體，保留來源衝突與未知條件；沒有通關證據，就不以理論隊補洞。
          </p>
          {featured ? (
            <Link className="primary-action" href={`/pve/${featured.guide_id}`}>
              查看{featured.area}深域 {featured.stage} <span aria-hidden="true">→</span>
            </Link>
          ) : null}
        </div>
        <Panel className="baseline-card">
          <p className="eyebrow">CURRENT BASELINE</p>
          <p className="baseline-card__version">{baseline.data.application_version}</p>
          <dl>
            <div><dt>研究核心</dt><dd>{baseline.data.research_core_version}</dd></div>
            <div><dt>Canonical</dt><dd>{baseline.data.canonical_source}</dd></div>
            <div><dt>API</dt><dd>{baseline.meta.api_version}</dd></div>
            <div><dt>Evidence</dt><dd>{baseline.data.counts.evidence}</dd></div>
            <div><dt>Claims</dt><dd>{baseline.data.counts.claims}</dd></div>
            <div><dt>來源軸</dt><dd>{baseline.data.counts.operation_timelines}</dd></div>
            <div><dt>操作步驟</dt><dd>{baseline.data.counts.timeline_steps}</dd></div>
          </dl>
          <p className="baseline-card__note">資料由 read-only mirror 提供；file core 仍是唯一可寫 SSOT。</p>
        </Panel>
      </section>

      <section className="section-block" aria-labelledby="pve-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">PVE · DEEP ZONE</p>
            <h2 id="pve-heading">深域實證攻略</h2>
          </div>
          <p>成熟門檻為每關 5 支不同五人實證隊伍。</p>
        </div>
        <div className="stage-grid">
          {stages.data.map((stage) => <StageCard key={stage.guide_id} stage={stage} />)}
        </div>
      </section>

      <section className="principles" aria-label="資料原則">
        <div><strong>正文優先</strong><span>搜尋摘要不當 Evidence</span></div>
        <div><strong>不補理論隊</strong><span>不足就揭露實際 N 隊</span></div>
        <div><strong>未知即未知</strong><span>逐 slot 條件不臆測</span></div>
      </section>
    </>
  );
}

function StageCard({ stage }: { stage: StageSummary }) {
  const current = stage.team_count;
  const target = 5;
  const percent = Math.min(100, Math.round((current / target) * 100));
  return (
    <Link className="stage-card panel" href={`/pve/${stage.guide_id}`}>
      <div className="stage-card__topline">
        <span>{stage.area}深域</span>
        <Badge tone={statusTone(stage.status)}>{statusLabel(stage.status)}</Badge>
      </div>
      <h3>{stage.stage}</h3>
      <p>台服 · {stage.mode}</p>
      <div className="coverage" aria-label={`實證隊伍 ${current} / ${target}`}>
        <div><strong>{current}/{target}</strong><span>不同五人實證隊</span></div>
        <div className="progress-track" aria-hidden="true"><span style={{ width: `${percent}%` }} /></div>
      </div>
      <span className="card-link">查看隊伍與證據 <span aria-hidden="true">→</span></span>
    </Link>
  );
}
