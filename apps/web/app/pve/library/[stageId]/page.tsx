import { ApiError } from "@pcr-tw/api-client";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  PveModeNav,
  type PveMode,
  pveElementLabels,
  pveModeLabels,
} from "../../../../components/pve-library-ui";
import { PveTeamCard } from "../../../../components/pve-team-card";
import { serverApi } from "../../../../lib/api";

export const dynamic = "force-dynamic";

async function getStage(stageId: string) {
  try {
    return await serverApi().getPveLibraryStage(stageId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}

function decodeStageId(stageId: string): string {
  try {
    return decodeURIComponent(stageId);
  } catch {
    return stageId;
  }
}

function stageIndexHref(stage: { mode: string; element: string; stage_refs: Array<{ area: number; stage: number }> }) {
  if (stage.mode === "REMEMBRANCE") {
    return `/pve/remembrance?element=${encodeURIComponent(stage.element)}`;
  }
  if (stage.mode === "LUNA_TOWER") return "/pve/luna-tower";

  const ref = stage.stage_refs[0];
  if (!ref) return "/pve/deep";
  const query = new URLSearchParams({
    element: stage.element,
    area: String(ref.area),
    stage: String(ref.stage),
  });
  return `/pve/deep?${query}`;
}

export async function generateMetadata(
  { params }: { params: Promise<{ stageId: string }> },
): Promise<Metadata> {
  const { stageId: encodedStageId } = await params;
  const stageId = decodeStageId(encodedStageId);
  try {
    const response = await serverApi().getPveLibraryStage(stageId);
    return {
      title: `${response.data.label_raw ?? "PVE Excel 區段"}｜Excel PVE 隊伍庫`,
      description: "依 Excel 原文整理的本機 PVE 隊伍；未獨立驗證通關。",
    };
  } catch {
    return { title: "找不到 PVE Excel 區段｜台服 AI 攻略研究所" };
  }
}

export default async function PveLibraryStagePage(
  { params }: { params: Promise<{ stageId: string }> },
) {
  const { stageId: encodedStageId } = await params;
  const stageId = decodeStageId(encodedStageId);
  const response = await getStage(stageId);
  const stage = response.data;
  const label = stage.label_raw ?? `${pveModeLabels[stage.mode] ?? stage.mode} ${stage.stage_id}`;
  const refs = stage.stage_refs
    .map((ref) => stage.mode === "DEEP" ? `${ref.area}-${ref.stage}` : String(ref.stage))
    .join("、");

  return (
    <>
      <PveModeNav activeMode={(stage.mode in pveModeLabels ? stage.mode : "DEEP") as PveMode} />

      <nav className="breadcrumb" aria-label="麵包屑">
        <Link href={stageIndexHref(stage)}>{pveModeLabels[stage.mode] ?? "PVE"}攻略</Link>
        <span aria-hidden="true">/</span>
        <span>{label}</span>
      </nav>

      <header className="pve-library-detail">
        <div className="pve-library-detail__summary">
          <div>
            <div className="pve-library-detail__meta">
              <span className="badge badge--info">{pveModeLabels[stage.mode] ?? stage.mode}</span>
              <span className="badge">
                {pveElementLabels[stage.element] ?? stage.element}
                {stage.mode === "DEEP" ? "屬性" : ""}
              </span>
              <span className="badge">Excel 區段 {refs || "未標記"}</span>
            </div>
            <p className="eyebrow">LOCAL WORKBOOK SECTION</p>
            <h1>{label}</h1>
            <p className="pve-library-detail__lead">
              頭像、操作文字、備註與影片連結均按工作簿區段整理；追憶戰域的合併樓層標題保留為同一區段，
              不拆成逐層驗證結論。
            </p>
          </div>
          <div className="pve-library-detail__count panel">
            <strong>{stage.team_count}</strong>
            <span>Excel 收錄隊伍</span>
          </div>
        </div>
      </header>

      <div className="pve-library-disclosure" aria-label="資料驗證狀態">
        <strong>Excel來源整理</strong>
        <span>未獨立驗證通關</span>
      </div>

      <section className="section-block" aria-labelledby="pve-library-teams-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">PORTRAIT-FIRST TEAMS</p>
            <h2 id="pve-library-teams-heading">隊伍與來源操作軸</h2>
          </div>
          <p>每隊固定五張頭像；同一隊可保留多條 Excel 操作軸。</p>
        </div>
        {stage.teams.length > 0 ? (
          <div className="pve-library-team-list">
            {stage.teams.map((team) => <PveTeamCard key={team.team_id} team={team} />)}
          </div>
        ) : (
          <div className="empty-state panel">
            <h2>這個 Excel 區段沒有隊伍列</h2>
            <p className="empty-state__body">系統不會補寫工作簿沒有提供的隊伍或操作軸。</p>
          </div>
        )}
      </section>

      <section className="pve-library-provenance panel" aria-labelledby="pve-library-provenance-heading">
        <h2 id="pve-library-provenance-heading">Excel 來源定位</h2>
        <dl>
          <div className="definition">
            <dt>工作簿</dt>
            <dd>{stage.provenance.source_workbook_filename}</dd>
          </div>
          <div className="definition">
            <dt>工作表</dt>
            <dd>{stage.provenance.sheet_name}</dd>
          </div>
          <div className="definition">
            <dt>儲存格範圍</dt>
            <dd>{stage.provenance.source_range}</dd>
          </div>
          <div className="definition">
            <dt>資料集 SHA-256</dt>
            <dd><code title={response.meta.dataset_sha256}>{response.meta.dataset_sha256.slice(0, 12)}…</code></dd>
          </div>
          <div className="definition">
            <dt>來源狀態</dt>
            <dd>{response.meta.source_status}</dd>
          </div>
          <div className="definition">
            <dt>獨立通關驗證</dt>
            <dd>{response.meta.independent_clear_verification}</dd>
          </div>
        </dl>
      </section>
    </>
  );
}
