import type { PvpCounter } from "@pcr-tw/api-client";
import { Badge, Definition, EmptyState, Panel } from "@pcr-tw/ui";
import { ArenaRoster } from "../../components/arena-roster";
import { EvidenceDrawer } from "../../components/evidence-drawer";
import { serverApi } from "../../lib/api";

export const dynamic = "force-dynamic";

const SOURCE_PLATFORM_LABELS: Readonly<Record<string, string>> = {
  Bahamut: "巴哈姆特",
};

export default async function PvpPage() {
  const response = await serverApi().getPvpCounters();
  const defenses = groupByDefense(response.data);
  const legacyMaterialization = response.meta.warnings.includes("NO_ARENA_MATERIALIZATION");

  return (
    <>
      <header className="page-heading">
        <p className="eyebrow">BATTLE ARENA · TW</p>
        <h1>競技場精確解陣</h1>
        <p>只呈現 Registry 中的 exact composition；單筆戰果會明確標示限制，不推論可重現性。</p>
      </header>

      {response.meta.warnings.length > 0 ? (
        <aside className="arena-warning" aria-label="Arena 資料限制">
          <div>
            <p className="eyebrow">DATA LIMITS</p>
            <div className="arena-warning__messages">
              {response.meta.warnings.map((warning) => (
                <p key={warning}>{warningMessage(warning)}</p>
              ))}
            </div>
          </div>
          <div className="badge-row">
            {response.meta.warnings.map((warning) => (
              <Badge key={warning} tone="warning">{warning}</Badge>
            ))}
          </div>
        </aside>
      ) : null}

      {response.data.length === 0 ? (
        <Panel>
          <EmptyState eyebrow="NO EXACT RESULT" title="目前沒有可顯示的精確案例">
            <p>
              {legacyMaterialization
                ? "此快照只包含舊版 serving tables；平台不會拿缺少的 Arena 資料推造反制。"
                : "Registry 沒有符合條件的 exact composition；平台不建立示意隊或理論隊。"}
            </p>
            <div className="badge-row">
              {response.meta.warnings.length === 0 ? (
                <Badge tone="warning">NO_VERIFIED_COUNTER</Badge>
              ) : null}
              <Badge>0 筆 exact 案例</Badge>
            </div>
          </EmptyState>
        </Panel>
      ) : (
        <div className="arena-defense-list">
          {defenses.map(({ defense, counters }) => (
            <DefenseCase counters={counters} defense={defense} key={defense.defense_id} />
          ))}
        </div>
      )}

      <Panel className="arena-similar-panel">
        <div>
          <p className="eyebrow">SIMILAR MATCH</p>
          <h2>Similar 未啟用</h2>
        </div>
        <p>相似防守不會冒充 exact counter；目前 API 與畫面只提供完整五人精確比對。</p>
      </Panel>
    </>
  );
}

function groupByDefense(counters: PvpCounter[]) {
  const groups = new Map<string, { defense: PvpCounter; counters: PvpCounter[] }>();
  for (const counter of counters) {
    const existing = groups.get(counter.defense_id);
    if (existing) existing.counters.push(counter);
    else groups.set(counter.defense_id, { defense: counter, counters: [counter] });
  }
  return [...groups.values()];
}

function DefenseCase({
  counters,
  defense,
}: {
  counters: PvpCounter[];
  defense: PvpCounter;
}) {
  return (
    <Panel className="arena-defense">
      <div className="arena-defense__heading">
        <div>
          <p className="eyebrow">DEFENSE · {defense.defense_id}</p>
          <h2>精確防守五人</h2>
        </div>
        <div className="badge-row">
          <Badge tone="info">{defense.server}</Badge>
          <Badge>{defense.environment_version}</Badge>
          <Badge>EXACT</Badge>
        </div>
      </div>

      <ArenaRoster label="精確防守五人" members={defense.defense_members} />

      <div className="arena-counter-list">
        {counters.map((counter) => (
          <CounterCase counter={counter} key={counter.counter_id} />
        ))}
      </div>
    </Panel>
  );
}

function CounterCase({ counter }: { counter: PvpCounter }) {
  const referenceOnly = counter.status === "SINGLE_REPORT";
  return (
    <article className="arena-counter-card">
      <div className="arena-counter-card__heading">
        <div>
          <p className="eyebrow">COUNTER · {counter.counter_id}</p>
          <h3>反制五人</h3>
        </div>
        <div className="badge-row">
          {referenceOnly ? <Badge tone="warning">【僅供參考】</Badge> : null}
          <Badge tone={referenceOnly ? "warning" : "neutral"}>{counter.status}</Badge>
          <Badge>Confidence {counter.claim_confidence}</Badge>
          <Badge tone="success">TW Availability {counter.tw_availability_check}</Badge>
        </div>
      </div>

      <ArenaRoster label={`${counter.counter_id} 反制五人`} members={counter.counter_members} />

      <div className="arena-facts">
        <Definition term="台服可用性">{counter.tw_availability_check}</Definition>
        <Definition term="不可用角色">
          {counter.unavailable_unit_ids.length === 0
            ? "無"
            : counter.unavailable_unit_ids.join("、")}
        </Definition>
        <Definition term="來源等級">{counter.source_tier}</Definition>
        <Definition term="來源平台">
          {counter.source_platforms.length === 0
            ? "未登錄"
            : counter.source_platforms.map(sourcePlatformLabel).join("、")}
        </Definition>
        <Definition term="結果證據">{counter.verification}</Definition>
        <Definition term="來源紀錄">{counter.source_record_count} 筆</Definition>
        <Definition term="戰果樣本">
          {counter.sample_size === null
            ? "未提供"
            : `${counter.wins ?? 0} 勝 / ${counter.losses ?? 0} 敗（n=${counter.sample_size}）`}
        </Definition>
        <Definition term="實測勝率">
          {counter.empirical_win_rate === null
            ? "樣本不足，未計算"
            : `${counter.empirical_win_rate}%`}
        </Definition>
        <Definition term="RNG 風險">{counter.rng_risk}</Definition>
        <Definition term="隨機性聲明">{counter.randomness}</Definition>
        <Definition term="可重現性">{counter.reproducibility}</Definition>
        <Definition term="操作模式">{counter.operation_mode}</Definition>
        <Definition term="速度條件">{counter.speed_conditions}</Definition>
        <Definition term="初動備註">{counter.initial_action_notes}</Definition>
        <Definition term="環境相符">{counter.environment_match}</Definition>
        <Definition term="強化條件檢查">{counter.required_upgrade_check}</Definition>
        <Definition term="資料核對日">{counter.verified_date}</Definition>
        <Definition term="下次複核">{counter.last_review_due ?? "未排定"}</Definition>
        <Definition term="紀錄日期範圍">
          {counter.record_date_min && counter.record_date_max
            ? `${counter.record_date_min} ～ ${counter.record_date_max}`
            : "未提供"}
        </Definition>
      </div>

      <div className="arena-counter-card__footer">
        <div>
          <p className="eyebrow">TRACEABILITY</p>
          <p>{referenceOnly ? "單一來源戰果；只保留可追溯原文，不延伸為穩定結論。" : counter.notes}</p>
        </div>
        <EvidenceDrawer
          buttonLabel="開啟 Evidence"
          compact
          contextLocator={`39_ARENA_COUNTER_REGISTRY.csv#${counter.counter_id}`}
          evidenceIds={counter.evidence_ids}
        />
      </div>
    </article>
  );
}

function sourcePlatformLabel(platform: string) {
  return SOURCE_PLATFORM_LABELS[platform] ?? platform;
}

function warningMessage(warning: string): string {
  switch (warning) {
    case "NO_ARENA_MATERIALIZATION":
      return "目前資料快照尚未包含 Arena materialization。";
    case "NO_EXACT_COUNTER":
      return "目前沒有符合完整五人簽章的 exact counter；不會回退為相似隊伍。";
    case "NO_VERIFIED_COUNTER":
      return "目前沒有 VERIFIED counter；現有資料不會被提升為成熟結論。";
    case "SINGLE_REPORT_REFERENCE_ONLY":
      return "目前顯示的案例只有單筆來源戰果，僅供參考且不代表可重現性。";
    default:
      return `資料快照帶有 ${warning} 限制，請依警示代碼判讀。`;
  }
}
