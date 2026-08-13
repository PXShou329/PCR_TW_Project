import { ApiError } from "@pcr-tw/api-client";
import type { GachaCommunitySource, GachaTimelineEvent } from "@pcr-tw/api-client";
import { Badge, Definition, EmptyState, Panel } from "@pcr-tw/ui";
import { EvidenceDrawer } from "../../components/evidence-drawer";
import { PrivateGachaForecastSection } from "../../features/private-gacha/components/forecast";
import { serverApi } from "../../lib/api";

export const dynamic = "force-dynamic";

async function loadCanonicalGacha() {
  const api = serverApi();
  const [timelineResult, communityResult] = await Promise.allSettled([
    api.getGachaTimeline(),
    api.getGachaCommunitySources(),
  ]);
  if (timelineResult.status === "fulfilled" && communityResult.status === "fulfilled") {
    return {
      communityResponse: communityResult.value,
      status: "ready" as const,
      timelineResponse: timelineResult.value,
    };
  }

  const failures = [timelineResult, communityResult].filter(
    (result): result is PromiseRejectedResult => result.status === "rejected",
  );
  const unexpectedFailure = failures.find(({ reason }) => !isDatabaseUnavailable(reason));
  if (unexpectedFailure) {
    throw unexpectedFailure.reason;
  }
  console.error(
    "Canonical Gacha data is unavailable; private DOCX forecasts remain enabled.",
    failures.map(({ reason }) => (reason as ApiError).message).join(", "),
  );
  return { status: "unavailable" as const };
}

function isDatabaseUnavailable(error: unknown): error is ApiError {
  return (
    error instanceof ApiError &&
    error.status === 503 &&
    error.problem?.detail?.code === "DATABASE_UNAVAILABLE"
  );
}

export default async function GachaPage() {
  const canonical = await loadCanonicalGacha();
  const timeline =
    canonical.status === "ready"
      ? [...canonical.timelineResponse.data].sort((left, right) =>
          left.jp_date.localeCompare(right.jp_date),
        )
      : [];
  const matureCount = timeline.filter((event) => event.maturity === "MATURE").length;
  const researchCount = timeline.length - matureCount;
  const checkedSources =
    canonical.status === "ready"
      ? canonical.communityResponse.data.filter((source) => source.update_status === "CHECKED")
          .length
      : 0;

  return (
    <>
      <header className="page-heading gacha-heading">
        <p className="eyebrow">GACHA FUTURE SIGHT · JP → TW</p>
        <h1>抽卡未來視</h1>
        <p>
          以日服官方事件與台日差距錨點建立公共時間線；未知限定身分、台服名稱與未完成價值研究都原樣揭露。
        </p>
      </header>

      {canonical.status === "ready" ? (
        <Panel className="gacha-scope">
          <div className="gacha-scope__heading">
            <div>
              <p className="eyebrow">PUBLIC RESEARCH SCOPE</p>
              <h2>模型是日期參考，不是個人抽卡指令</h2>
            </div>
            <div className="badge-row">
              <Badge tone="success">MATURE {matureCount}</Badge>
              <Badge tone="info">RESEARCH {researchCount}</Badge>
              <Badge tone="neutral">現行社群來源 {checkedSources}</Badge>
            </div>
          </div>
          <dl className="gacha-summary" aria-label="Gacha 資料範圍">
            <Definition term="研究方向">JP 官方事件 → TW 公共未來視</Definition>
            <Definition term="最後核對">
              {canonical.timelineResponse.meta.verified_at ?? "UNKNOWN"}
            </Definition>
            <Definition term="資料修訂">
              <code title={canonical.timelineResponse.meta.data_revision}>
                {shortRevision(canonical.timelineResponse.meta.data_revision)}
              </code>
            </Definition>
            <Definition term="鮮度">{canonical.timelineResponse.meta.stale_status}</Definition>
          </dl>
          <p className="gacha-scope__disclosure">
            本頁不讀取帳號、持有角色或個人寶石，也不產生帳號專屬推薦。日期區間可能因台服排程調整而變動；社群來源不會升格為官方證據。
          </p>
        </Panel>
      ) : null}

      <PrivateGachaForecastSection />

      {canonical.status === "unavailable" ? (
        <section
          aria-label="公共時間線狀態"
          className="section-block gacha-canonical-status"
          data-load-state="error"
        >
          <Panel className="private-gacha-status">
            <EmptyState eyebrow="PUBLIC RESEARCH UNAVAILABLE" title="公共時間線目前無法取得">
              <p>
                上方私人 DOCX 未來視仍可使用；公共時間線需要資料庫，恢復後重新載入頁面即可顯示。
              </p>
            </EmptyState>
          </Panel>
        </section>
      ) : (
        <>
          <section className="section-block" aria-labelledby="gacha-timeline-heading">
            <div className="section-heading">
              <div>
                <p className="eyebrow">CANONICAL TIMELINE</p>
                <h2 id="gacha-timeline-heading">日服事件與台服模型區間</h2>
              </div>
              <p>MATURE 才提供已完成的公共價值研究；RESEARCH 僅保留可證日期與明示缺口。</p>
            </div>
            {timeline.length > 0 ? (
              <div className="gacha-timeline-grid">
                {timeline.map((event) => (
                  <TimelineCard event={event} key={event.event_id} />
                ))}
              </div>
            ) : (
              <Panel>
                <EmptyState
                  eyebrow="NO TIMELINE MATERIALIZATION"
                  title="目前沒有可供應的 Gacha 時間線"
                >
                  <p>平台不會用搜尋摘要或理論角色補出未來卡池；資料閉合後才會顯示。</p>
                </EmptyState>
              </Panel>
            )}
          </section>

          <section className="section-block" aria-labelledby="gacha-community-heading">
            <div className="section-heading">
              <div>
                <p className="eyebrow">COMMUNITY SOURCE INDEX</p>
                <h2 id="gacha-community-heading">社群未來視來源狀態</h2>
              </div>
              <p>CHECKED 代表正文已實開且仍在維護，不代表其日期或主觀評價為官方事實。</p>
            </div>
            <div className="community-grid">
              {canonical.communityResponse.data.map((source) => (
                <CommunitySourceCard key={source.source_id} source={source} />
              ))}
            </div>
          </section>
        </>
      )}
    </>
  );
}

function TimelineCard({ event }: { event: GachaTimelineEvent }) {
  const isResearch = event.maturity === "RESEARCH";
  const twLabel = event.tw_name ?? "台服官方名稱待公告";
  return (
    <article
      className={`panel gacha-card${isResearch ? " gacha-card--research" : ""}`}
      data-maturity={event.maturity}
    >
      <div className="gacha-card__heading">
        <div className="badge-row">
          <Badge tone={isResearch ? "info" : "success"}>{event.maturity}</Badge>
          <Badge tone={event.limited_status === "UNKNOWN" ? "warning" : "neutral"}>
            {limitedLabel(event.limited_status)}
          </Badge>
        </div>
        <code>{event.event_id}</code>
      </div>

      <div className="gacha-card__identity">
        <p className="eyebrow">{event.source_server} {event.jp_date}</p>
        <h3>{event.character_name_jp}</h3>
        <p>{twLabel}</p>
      </div>

      <div className="gacha-window" aria-label={`${event.character_name_jp} 台服日期模型`}>
        <span>台服模型區間</span>
        <strong>{formatInterval(event.tw_estimate_start, event.tw_estimate_end)}</strong>
        <small>{forecastMethodLabel(event.forecast_method)} · {event.anchor_track} n={event.anchor_count}</small>
      </div>

      <dl className="gacha-facts">
        <Definition term="日服池型">{event.pool_type}</Definition>
        <Definition term="限定依據">
          {event.limited_claim_id ? <code>{event.limited_claim_id}</code> : "UNKNOWN"}
        </Definition>
        <Definition term="預測信心">{event.confidence}</Definition>
        <Definition term="最後核對">{event.last_verified}</Definition>
        <Definition term="下次審查">{event.last_review_due ?? "UNKNOWN"}</Definition>
      </dl>

      <div className="gacha-values" aria-label="公共價值研究">
        <ValueItem label="競技場" value={event.arena_value} />
        <ValueItem label="公主競技場" value={event.p_arena_value} />
        <ValueItem label="PVE" value={event.pve_value} />
        <ValueItem label="戰隊戰" value={event.clan_value} />
      </div>

      <div className="gacha-card__analysis">
        <p><strong>公共相對評估：</strong>{displayValue(event.relative_priority)}</p>
        <p><strong>強化資訊：</strong>{displayValue(event.future_upgrade)}</p>
        {event.community_source_count > 0 ? (
          <p><strong>社群整合：</strong>{event.community_order_consensus || "有登錄來源，但無可安全正規化的共識"}</p>
        ) : (
          <p><strong>社群整合：</strong>未納入最終日期區間；不以月份位置臆造日精度。</p>
        )}
      </div>

      {isResearch ? (
        <p className="gacha-disclosure">
          研究列：價值或身分尚未閉合，不應據此產生抽取優先級；UNKNOWN 不會由池名或社群譯名補全。
        </p>
      ) : null}

      <EvidenceDrawer evidenceIds={event.evidence_ids} buttonLabel="開啟 Gacha Evidence" compact />
    </article>
  );
}

function ValueItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{displayValue(value)}</strong>
    </div>
  );
}

function CommunitySourceCard({ source }: { source: GachaCommunitySource }) {
  const stale = source.update_status === "STALE";
  return (
    <article className="panel community-card" data-status={source.update_status}>
      <div className="community-card__heading">
        <Badge tone={stale ? "warning" : "success"}>{source.update_status}</Badge>
        <code>{source.source_id}</code>
      </div>
      <h3>{source.title}</h3>
      <p>{source.platform} · {source.author}</p>
      <dl>
        <Definition term="最後更新">{source.last_seen_update ?? "UNKNOWN"}</Definition>
        <Definition term="涵蓋區間">{formatInterval(source.coverage_start, source.coverage_end)}</Definition>
        <Definition term="信心上限">{source.confidence_cap}</Definition>
        <Definition term="最後實開">{source.last_checked}</Definition>
      </dl>
      <p className="community-card__usage">{source.usage}</p>
      <p className="community-card__notes">{source.notes}</p>
      <a className="source-link" href={source.url} rel="noreferrer" target="_blank">
        開啟已登錄正文 <span aria-hidden="true">↗</span>
      </a>
    </article>
  );
}

function limitedLabel(status: GachaTimelineEvent["limited_status"]): string {
  if (status === "YES") return "限定身分已明示";
  if (status === "NO") return "非限定";
  return "限定身分 UNKNOWN";
}

function forecastMethodLabel(method: GachaTimelineEvent["forecast_method"]): string {
  if (method === "MODEL_PLUS_COMMUNITY") return "模型＋社群共識";
  if (method === "OFFICIAL_OVERRIDE") return "台服官方落地";
  return "僅模型";
}

function formatInterval(start: string | null, end: string | null): string {
  if (!start || !end) return "UNKNOWN";
  return start === end ? start : `${start} – ${end}`;
}

function displayValue(value: string): string {
  if (value === "NOT_EVALUATED") return "尚未評估";
  if (value === "UNKNOWN" || value === "待查證") return "UNKNOWN／待查證";
  return value;
}

function shortRevision(revision: string): string {
  return revision.length > 12 ? `${revision.slice(0, 12)}…` : revision;
}
