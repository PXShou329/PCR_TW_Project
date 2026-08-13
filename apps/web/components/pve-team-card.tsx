import { PvePortrait } from "./pve-portrait";
import { PveYouTubeMedia } from "./pve-source-media";

interface PveSourceLinkView {
  alias_label: string | null;
  applies_to_cell: string | null;
  kind: string;
  label_raw: string | null;
  media: {
    embed_url: string | null;
    external_url: string;
    kind: "YOUTUBE" | "EXTERNAL";
    video_id: string | null;
  } | null;
  origin_cell: string;
  resolution_status: string;
  url: string | null;
}

interface PveTeamView {
  axes: Array<{
    axis_id: string;
    notes_raw: string | null;
    operation: {
      execution_hints: string[];
      kind: string;
      member_alignment: string;
      order_basis: string;
      variants: Array<{
        kind: string;
        origin_cell: string;
        origin_field: string;
        raw: string;
        source_order_states: Array<"SET" | "NOT_SET">;
      }>;
    };
    operation_raw: string | null;
    source_cell: string;
    source_links: PveSourceLinkView[];
  }>;
  display_order: number;
  flags: string[];
  notes_raw: string | null;
  portraits: Array<{
    asset_url: string;
    display_position: number;
    icon_url: string | null;
    mapping_status: string;
    tw_name: string | null;
    unit_key: string | null;
  }>;
  source_links: PveSourceLinkView[];
  source_range: string;
  team_id: string;
}

function safeHttpUrl(raw: string | null): string | null {
  if (!raw) return null;
  try {
    const url = new URL(raw);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function sourceKey(source: PveSourceLinkView): string {
  return `${source.origin_cell}\u0000${source.url ?? ""}\u0000${source.label_raw ?? ""}`;
}

export function PveTeamCard({ team }: { team: PveTeamView }) {
  const axisSourceKeys = new Set(team.axes.flatMap((axis) => axis.source_links.map(sourceKey)));
  const teamOnlySources = team.source_links.filter((source) => !axisSourceKeys.has(sourceKey(source)));

  return (
    <article className="pve-library-team panel" data-team-id={team.team_id}>
      <div className="pve-library-team__heading">
        <div>
          <p className="eyebrow">TEAM {team.display_order}</p>
          <h3>隊伍 {team.display_order}</h3>
        </div>
        <div className="badge-row">
          <span className="badge">Excel 收錄</span>
          {team.flags.map((flag) => <span className="badge badge--info" key={flag}>{flag}</span>)}
        </div>
      </div>

      {team.notes_raw ? <p className="pve-library-team__notes">{team.notes_raw}</p> : null}

      <ul className="pve-portraits" aria-label={`隊伍 ${team.display_order} 的五位角色`}>
        {team.portraits.map((portrait) => (
          <PvePortrait
            assetUrl={portrait.asset_url}
            displayPosition={portrait.display_position}
            iconUrl={portrait.icon_url}
            key={`${portrait.display_position}-${portrait.icon_url ?? portrait.asset_url}`}
            mappingStatus={portrait.mapping_status}
            twName={portrait.tw_name}
            unitKey={portrait.unit_key}
          />
        ))}
      </ul>

      {team.axes.length > 0 ? (
        <div className="pve-axis-list" aria-label={`隊伍 ${team.display_order} 的操作軸`}>
          {team.axes.map((axis, index) => (
            <section className="pve-axis" data-axis-id={axis.axis_id} key={axis.axis_id}>
              <div className="pve-axis__heading">
                <h4>操作軸 {index + 1}</h4>
                <code>{axis.source_cell}</code>
              </div>
              <p className="pve-axis__raw">{axis.operation_raw ?? "Excel 未填操作文字"}</p>
              {axis.notes_raw ? <p className="pve-axis__notes">{axis.notes_raw}</p> : null}
              {axis.operation.member_alignment === "UNRESOLVED" ? (
                <p className="pve-axis__alignment">
                  O／X 只按 Excel 來源文字由左到右呈現，尚未對齊角色位置；不會疊到頭像上。
                </p>
              ) : null}

              <div className="pve-operation-variants">
                {axis.operation.variants.map((variant, variantIndex) => (
                  <div className="pve-operation-variant" key={`${variant.origin_cell}-${variantIndex}`}>
                    <div className="pve-operation-variant__meta">
                      <span>{variant.raw}</span>
                      <span>{variant.origin_field} · {variant.origin_cell}</span>
                    </div>
                    {variant.source_order_states.length > 0 ? (
                      <ol
                        className="pve-set-pattern"
                        aria-label="Excel 來源文字順序的 SET 狀態"
                        data-member-alignment={axis.operation.member_alignment}
                        data-order-basis={axis.operation.order_basis}
                      >
                        {variant.source_order_states.map((state, stateIndex) => (
                          <li data-state={state} key={`${state}-${stateIndex}`}>
                            {state === "SET" ? "O · SET" : "X · 不SET"}
                          </li>
                        ))}
                      </ol>
                    ) : null}
                  </div>
                ))}
              </div>

              <PveSourceList sources={axis.source_links} title="此操作軸來源" />
            </section>
          ))}
        </div>
      ) : (
        <p className="pve-axis__alignment">Excel 未提供操作軸；不補寫 SET 狀態。</p>
      )}

      {teamOnlySources.length > 0 ? <PveSourceList sources={teamOnlySources} title="隊伍來源" /> : null}
      <p className="pve-library-team__notes">Excel 來源範圍：<code>{team.source_range}</code></p>
    </article>
  );
}

function PveSourceList({ sources, title }: { sources: PveSourceLinkView[]; title: string }) {
  if (sources.length === 0) return null;
  return (
    <div className="pve-source-list" aria-label={title}>
      {sources.map((source, index) => {
        const label = source.label_raw ?? source.alias_label ?? `來源 ${index + 1}`;
        const safeUrl = safeHttpUrl(source.media?.external_url ?? source.url);
        return (
          <div className="pve-source" key={`${sourceKey(source)}-${index}`}>
            <div className="pve-source__heading">
              <h5>{label}</h5>
              <code>{source.origin_cell}</code>
            </div>
            <span className="badge">{source.resolution_status}</span>
            {source.media?.kind === "YOUTUBE" && source.media.embed_url ? (
              <PveYouTubeMedia
                embedUrl={source.media.embed_url}
                externalUrl={source.media.external_url}
                label={label}
              />
            ) : safeUrl ? (
              <a className="source-link" href={safeUrl} rel="noreferrer" target="_blank">
                開啟外部來源 <span className="sr-only">（另開新分頁）</span>
              </a>
            ) : (
              <p className="pve-axis__notes">此來源在 Excel 中沒有可開啟的網址。</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
