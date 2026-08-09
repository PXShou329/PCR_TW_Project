import type { PvpCounter } from "@pcr-tw/api-client";
import { Badge, Definition, EmptyState, Panel } from "@pcr-tw/ui";
import Form from "next/form";
import Link from "next/link";
import { ArenaRoster } from "../../components/arena-roster";
import { EvidenceDrawer } from "../../components/evidence-drawer";
import { serverApi } from "../../lib/api";

export const dynamic = "force-dynamic";

const SOURCE_PLATFORM_LABELS: Readonly<Record<string, string>> = {
  Bahamut: "巴哈姆特",
};

const SLOT_KEYS = ["slot1", "slot2", "slot3", "slot4", "slot5"] as const;

type PvpSearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function PvpPage({ searchParams }: { searchParams: PvpSearchParams }) {
  const params = await searchParams;
  const api = serverApi();
  const charactersResponse = await api.getPvpCharacters();
  const availableCharacters = [...charactersResponse.data]
    .filter((character) => character.tw_availability_status === "AVAILABLE")
    .sort((left, right) => characterLabel(left).localeCompare(characterLabel(right), "zh-Hant"));
  const availableKeys = new Set(availableCharacters.map((character) => character.unit_key));
  const hasSearch = SLOT_KEYS.some((key) => Object.hasOwn(params, key));
  const selectedUnits = SLOT_KEYS.map((key) => scalarParam(params[key]));
  const hasOnlyScalarParams = SLOT_KEYS.every((key) => !Array.isArray(params[key]));
  const hasFiveUnits = selectedUnits.every(Boolean);
  const hasFiveDistinctUnits = new Set(selectedUnits).size === SLOT_KEYS.length;
  const hasOnlyAvailableUnits = selectedUnits.every((unitKey) => availableKeys.has(unitKey));
  const validSelection = hasSearch
    && hasOnlyScalarParams
    && hasFiveUnits
    && hasFiveDistinctUnits
    && hasOnlyAvailableUnits;
  const response = validSelection
    ? await api.getPvpCounters(selectedUnits.join(";"))
    : null;
  const counters = response?.data ?? [];
  const defenses = groupByDefense(counters);
  const warnings = response?.meta.warnings ?? [];
  const legacyMaterialization = warnings.includes("NO_ARENA_MATERIALIZATION");

  return (
    <>
      <header className="page-heading">
        <p className="eyebrow">BATTLE ARENA · TW</p>
        <h1>競技場精確解陣</h1>
        <p>以完整五人簽章查詢 Registry 的 exact composition；單筆戰果會明確標示限制，不推論可重現性。</p>
      </header>

      <Panel className="arena-search-panel">
        <div className="arena-search-heading">
          <div>
            <p className="eyebrow">EXACT-FIRST SEARCH</p>
            <h2>選擇完整防守五人</h2>
          </div>
          <Badge tone="info">TW · AVAILABLE MIRROR</Badge>
        </div>

        <Form action="/pvp" className="arena-search-form">
          <fieldset>
            <legend className="sr-only">防守隊伍五個角色位置</legend>
            <div className="arena-search-grid">
              {SLOT_KEYS.map((key, index) => (
                <label key={key}>
                  <span>防守位置 {index + 1}</span>
                  <select defaultValue={selectedUnits[index]} name={key} required>
                    <option value="">請選擇角色</option>
                    {availableCharacters.map((character) => (
                      <option key={character.unit_key} value={character.unit_key}>
                        {characterLabel(character)}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <div className="arena-search-actions">
              <button className="primary-action" type="submit">搜尋精確反制</button>
              <Link className="text-link" href="/pvp">清除選擇</Link>
              <p>位置順序只供畫面與分享網址保留；API 會以五位不同角色的 canonical signature 精確比對。</p>
            </div>
          </fieldset>
        </Form>

        <dl className="arena-search-scope" aria-label="角色研究鏡像範圍">
          <Definition term="研究鏡像">{availableCharacters.length} 位 AVAILABLE 角色</Definition>
          <Definition term="資料伺服器">{charactersResponse.meta.server}</Definition>
          <Definition term="鏡像核對日">{charactersResponse.meta.verified_at ?? "UNKNOWN"}</Definition>
          <Definition term="鮮度狀態">{charactersResponse.meta.stale_status}</Definition>
          <Definition term="Research Core">{charactersResponse.meta.source.research_core_version}</Definition>
          <Definition term="API 版本">{charactersResponse.meta.api_version}</Definition>
          <Definition term="資料修訂">
            <code title={charactersResponse.meta.data_revision}>
              {shortRevision(charactersResponse.meta.data_revision)}
            </code>
          </Definition>
        </dl>
        <p className="arena-search-disclosure">
          選項只來自 API typed mirror 中標為 AVAILABLE 的台服研究資料；這是目前研究鏡像範圍，不是全角色百科。
        </p>
      </Panel>

      {hasSearch && !validSelection ? (
        <Panel className="arena-search-feedback" data-testid="pvp-search-invalid">
          <EmptyState eyebrow="INVALID EXACT SIGNATURE" title="需要剛好五個不同角色">
            <p>每個位置都必須選擇研究鏡像中的 AVAILABLE 角色，且五個 unit_key 不得重複；未符合時不會送出反制查詢。</p>
          </EmptyState>
        </Panel>
      ) : null}

      {!hasSearch ? (
        <Panel className="arena-search-feedback">
          <EmptyState eyebrow="READY TO SEARCH" title="選滿五位防守角色後執行精確搜尋">
            <p>平台不會預先列出全部案例，也不會用不完整隊伍猜測相似反制。</p>
          </EmptyState>
        </Panel>
      ) : null}

      {warnings.length > 0 ? (
        <aside className="arena-warning" aria-label="Arena 資料限制">
          <div>
            <p className="eyebrow">DATA LIMITS</p>
            <div className="arena-warning__messages">
              {warnings.map((warning) => (
                <p key={warning}>{warningMessage(warning)}</p>
              ))}
            </div>
          </div>
          <div className="badge-row">
            {warnings.map((warning) => (
              <Badge key={warning} tone="warning">{warning}</Badge>
            ))}
          </div>
        </aside>
      ) : null}

      {validSelection && counters.length === 0 ? (
        <Panel data-testid="pvp-no-exact-result">
          <EmptyState eyebrow="NO EXACT RESULT" title="目前沒有 VERIFIED 精確反制">
            <p>
              {legacyMaterialization
                ? "此快照只包含舊版 serving tables；平台不會拿缺少的 Arena 資料推造反制。"
                : "Registry 沒有符合完整五人簽章的 exact composition；平台不建立示意隊、理論隊或 Similar 替代結果。"}
            </p>
            <div className="badge-row">
              {!warnings.includes("NO_VERIFIED_COUNTER") ? (
                <Badge tone="warning">NO_VERIFIED_COUNTER</Badge>
              ) : null}
              <Badge>0 筆 exact 案例</Badge>
            </div>
          </EmptyState>
        </Panel>
      ) : validSelection ? (
        <div className="arena-defense-list">
          {defenses.map(({ defense, counters }) => (
            <DefenseCase counters={counters} defense={defense} key={defense.defense_id} />
          ))}
        </div>
      ) : null}

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

function scalarParam(value: string | string[] | undefined): string {
  return typeof value === "string" ? value.trim() : "";
}

function characterLabel(character: {
  jp_name: string | null;
  tw_name: string;
  unit_key: string;
}): string {
  const jpName = character.jp_name?.trim();
  const jpNameIsPlaceholder = !jpName
    || jpName.toUpperCase() === "UNKNOWN"
    || jpName.includes("待查證");
  const hasDisplayableJpName = !jpNameIsPlaceholder && jpName !== character.tw_name;
  const localizedNames = hasDisplayableJpName
    ? `${character.tw_name}／${jpName}`
    : character.tw_name;
  return `${localizedNames} · ${character.unit_key}`;
}

function shortRevision(revisionId: string): string {
  return revisionId.length > 18 ? `${revisionId.slice(0, 18)}…` : revisionId;
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
