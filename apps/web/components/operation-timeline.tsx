import type {
  StructuredTimelineSource,
  TeamMember,
  TeamTimeline,
  TimelineActionType,
  TimelineGapReason,
  TimelineOperationMode,
  TimelineSource,
  TimelineStep,
  TimelineTriggerType,
} from "@pcr-tw/api-client";
import { Badge, Panel } from "@pcr-tw/ui";
import { EvidenceDrawer } from "./evidence-drawer";

const operationLabels: Record<TimelineOperationMode, string> = {
  AUTO: "全自動聲明",
  SEMI_AUTO: "半自動",
  MANUAL_TIMELINE: "手動操作軸",
};

const triggerLabels: Record<TimelineTriggerType, string> = {
  CLOCK: "指定時間",
  UB_READY: "UB 就緒",
  ANIMATION_CUE: "動畫提示",
  HP_THRESHOLD: "HP 門檻",
  WAVE_START: "戰鬥開始",
  BOSS_ACTION: "Boss 動作",
  SOURCE_TEXT_ONLY: "來源文字提示",
};

const actionLabels: Record<TimelineActionType, string> = {
  USE_UB: "施放 UB",
  WAIT: "等待",
  AUTO_ON: "開啟 AUTO",
  AUTO_OFF: "關閉 AUTO",
  SET_ON: "開啟 SET",
  SET_OFF: "關閉 SET",
  PAUSE: "暫停",
  RESUME: "繼續",
  TARGET: "指定目標",
  NO_ACTION: "不操作",
};

const gapReasonLabels: Record<TimelineGapReason, string> = {
  INSUFFICIENT_SOURCE_DETAIL: "來源細節不足，無法安全拆成逐步操作。",
  PENDING_EXTRACTION: "正文已取得，但逐步操作仍待結構化整理。",
};

export function OperationTimeline({
  timeline,
  members,
}: {
  timeline: TeamTimeline;
  members: TeamMember[];
}) {
  const memberNames = new Map(members.map((member) => [member.unit_key, member.tw_name]));
  const presentation = timelinePresentation(timeline.status);

  return (
    <section className="operation-timeline section-block" aria-labelledby="operation-timeline-heading">
      <div className="section-heading timeline-heading">
        <div>
          <p className="eyebrow">OPERATION TIMELINE · SOURCE SEPARATED</p>
          <h2 id="operation-timeline-heading">{presentation.title}</h2>
        </div>
        <div className="timeline-coverage" aria-label="操作軸來源涵蓋率">
          <strong>{timeline.structured_sources}</strong>
          <span> / {timeline.registered_sources} 個來源已結構化</span>
        </div>
      </div>

      <Panel className={`timeline-disclosure timeline-disclosure--${timeline.status.toLowerCase()}`}>
        <div>
          <Badge tone={presentation.tone}>{presentation.badge}</Badge>
          <p>{presentation.description}</p>
        </div>
        <p>
          每個來源各自保留一條操作軸；平台不會跨來源合併、平均時間，或生成未經來源支持的「綜合操作軸」。
        </p>
      </Panel>

      {timeline.sources.length > 0 ? (
        <div className="timeline-source-list">
          {timeline.sources.map((source) => (
            <TimelineSourceCard key={source.source_axis_id} source={source} memberNames={memberNames} />
          ))}
        </div>
      ) : (
        <Panel className="timeline-missing">
          <div role="status">
            <p className="eyebrow">NO REGISTERED SOURCE AXIS</p>
            <h3>尚未登錄可追溯的操作軸來源</h3>
            <p>這不是「無需操作」；只是目前沒有足以呈現的來源資料。</p>
            {timeline.references.length > 0 ? (
              <LegacyReferences references={timeline.references} />
            ) : null}
          </div>
        </Panel>
      )}
    </section>
  );
}

function TimelineSourceCard({
  source,
  memberNames,
}: {
  source: TimelineSource;
  memberNames: Map<string, string>;
}) {
  if (source.status === "SOURCE_GAP") {
    return <GapSourceCard source={source} />;
  }

  return <StructuredSourceCard source={source} memberNames={memberNames} />;
}

function StructuredSourceCard({
  source,
  memberNames,
}: {
  source: StructuredTimelineSource;
  memberNames: Map<string, string>;
}) {
  return (
    <div data-source-id={source.source_id}>
      <Panel className="timeline-source timeline-source--structured">
      <div className="timeline-source__header">
        <div>
          <p className="eyebrow">STRUCTURED SOURCE AXIS</p>
          <h3 id={`timeline-source-${source.source_axis_id}`}>{source.timeline_variant_name}</h3>
          <code>{source.source_id}</code>
        </div>
        <div className="badge-row">
          <Badge tone="success">已結構化</Badge>
          <Badge tone="info">{operationLabels[source.operation_mode]}</Badge>
          <Badge>{source.steps.length} 步</Badge>
        </div>
      </div>

      <dl className="timeline-source__facts">
        <div><dt>來源軸 ID</dt><dd><code>{source.source_axis_id}</code></dd></div>
        <div><dt>計時方式</dt><dd>{clockModeLabel(source.clock_mode)}</dd></div>
        <div><dt>戰鬥長度</dt><dd>{durationLabel(source.battle_duration_ms)}</dd></div>
        <div><dt>初始 AUTO</dt><dd>{autoStateLabel(source.initial_auto_state)}</dd></div>
        <div><dt>最後核對</dt><dd>{source.last_verified_at}</dd></div>
      </dl>

      {source.reproducibility === "UNVERIFIED_ON_TW" ? (
        <div className="timeline-repro-warning" role="note">
          <strong>尚未在台服逐步重現</strong>
          <p>這條來源操作軸尚未逐步於台服重現；同隊已有台服通關證據，不代表此操作序列已完成台服驗證。</p>
        </div>
      ) : null}

      <p className="timeline-source__notes">{source.notes}</p>
      <EvidenceDrawer
        evidenceIds={[source.source_evidence_id]}
        buttonLabel="查看此來源 Evidence"
        compact
        contextLocator={source.source_locator}
      />

      <ol className="timeline-steps" aria-label={`${source.timeline_variant_name} 操作步驟`}>
        {source.steps.map((step) => (
          <TimelineStepCard
            evidenceId={source.source_evidence_id}
            key={step.timeline_step_id}
            memberNames={memberNames}
            source={source}
            step={step}
          />
        ))}
      </ol>
      </Panel>
    </div>
  );
}

function GapSourceCard({ source }: { source: Extract<TimelineSource, { status: "SOURCE_GAP" }> }) {
  return (
    <div data-source-id={source.source_id}>
      <Panel className="timeline-source timeline-source--gap">
      <div className="timeline-source__header">
        <div>
          <p className="eyebrow">SOURCE GAP</p>
          <h3 id={`timeline-source-${source.source_axis_id}`}>{source.timeline_variant_name}</h3>
          <code>{source.source_id}</code>
        </div>
        <div className="badge-row">
          <Badge tone="warning">僅有來源定位</Badge>
          <Badge tone="info">{operationLabels[source.operation_mode]}</Badge>
        </div>
      </div>

      <div className="timeline-gap-detail" role="note">
        <div className="timeline-gap__icon" aria-hidden="true">!</div>
        <div>
          <h4>尚未建立可驗證步驟</h4>
          <p>{gapReasonLabels[source.gap_reason]}</p>
          <p>定位資訊只用來回到來源，不會被冒充為操作步驟。</p>
        </div>
      </div>

      <dl className="timeline-source__facts">
        <div><dt>來源定位</dt><dd><code>{source.source_locator}</code></dd></div>
        <div><dt>最後核對</dt><dd>{source.last_verified_at}</dd></div>
        <div><dt>重現狀態</dt><dd>來源未載</dd></div>
      </dl>
      <p className="timeline-source__notes">{source.notes}</p>
      <EvidenceDrawer
        evidenceIds={[source.source_evidence_id]}
        buttonLabel="查看缺口來源 Evidence"
        compact
        contextLocator={source.source_locator}
      />
      </Panel>
    </div>
  );
}

function TimelineStepCard({
  step,
  source,
  evidenceId,
  memberNames,
}: {
  step: TimelineStep;
  source: StructuredTimelineSource;
  evidenceId: string;
  memberNames: Map<string, string>;
}) {
  const time = timelineTime(step, source.clock_mode);
  const triggerActor = unitLabel(step.trigger_actor_unit_key, memberNames);
  const actor = unitLabel(step.actor_unit_key, memberNames);
  const target = unitLabel(step.target_unit_key, memberNames);

  return (
    <li className="timeline-step" data-step-id={step.timeline_step_id}>
      <div className="timeline-step__rail" aria-hidden="true">
        <span>{step.sequence_no}</span>
      </div>
      <article className="timeline-step__card">
        <header className="timeline-step__header">
          <div>
            <span className="timeline-step__source-order">來源手順 {step.source_step_no}</span>
            <strong className={time.known ? "" : "unknown-value"}>{time.label}</strong>
          </div>
          <div className="badge-row">
            {step.criticality === "CRITICAL" ? <Badge tone="danger">關鍵步驟</Badge> : null}
            <Badge>{triggerLabels[step.trigger_type]}</Badge>
          </div>
        </header>

        <p className="timeline-step__instruction">{step.instruction_zh_tw}</p>

        <dl className="timeline-step__fields">
          <div>
            <dt>觸發</dt>
            <dd>
              <strong>{triggerLabels[step.trigger_type]}</strong>
              <span>{knownText(step.animation_cue)}</span>
              {step.trigger_actor_unit_key !== "NONE" ? <small>觸發角色：{triggerActor}</small> : null}
            </dd>
          </div>
          <div>
            <dt>動作</dt>
            <dd>
              <strong>{actionLabels[step.action_type]}</strong>
              <span>{step.actor_unit_key === "NONE" ? "不指定角色" : actor}</span>
              {step.target_unit_key !== "NONE" ? <small>目標：{target}</small> : null}
            </dd>
          </div>
          <div>
            <dt>操作後狀態</dt>
            <dd>AUTO {autoStateLabel(step.auto_state_after)}</dd>
          </div>
          <div>
            <dt>備註</dt>
            <dd>
              <span>HP：{knownText(step.hp_threshold)}</span>
              <small>容錯：{toleranceLabel(step.tolerance_ms)}</small>
              <small>關鍵度：{knownText(step.criticality)}</small>
              <small>定位：{step.source_locator}</small>
            </dd>
          </div>
        </dl>

        <div className={`timeline-step__failure${step.failure_if_missed === "UNKNOWN" ? " timeline-step__failure--unknown" : ""}`}>
          <strong>漏按／錯位後果</strong>
          <p>{knownText(step.failure_if_missed)}</p>
        </div>

        <EvidenceDrawer
          evidenceIds={[evidenceId]}
          buttonLabel="核對本步 Evidence"
          compact
          contextLocator={step.source_locator}
        />
      </article>
    </li>
  );
}

function LegacyReferences({ references }: { references: TeamTimeline["references"] }) {
  return (
    <div className="timeline-legacy-references">
      <p>僅保留舊版來源定位：</p>
      <ul>
        {references.map((reference) => <li key={reference.raw}><code>{reference.raw}</code></li>)}
      </ul>
    </div>
  );
}

function timelinePresentation(status: TeamTimeline["status"]): {
  title: string;
  badge: string;
  description: string;
  tone: "neutral" | "success" | "warning" | "info";
} {
  switch (status) {
    case "STRUCTURED":
      return {
        title: "已取得逐來源結構化操作軸",
        badge: "STRUCTURED",
        description: "已登錄來源均有各自的原子操作步驟；來源之間仍不互相替代。",
        tone: "success",
      };
    case "PARTIAL":
      return {
        title: "部分來源已有結構化操作軸",
        badge: "PARTIAL",
        description: "至少一個來源已有步驟，但其餘來源仍存在缺口；不可把局部資料視為完整共識。",
        tone: "warning",
      };
    case "SOURCE_GAP":
      return {
        title: "尚未建立可驗證的結構化操作軸",
        badge: "SOURCE_GAP",
        description: "目前只有來源與定位資訊，沒有可安全照做的逐步操作。",
        tone: "warning",
      };
    case "MISSING":
      return {
        title: "尚未登錄操作軸來源",
        badge: "MISSING",
        description: "目前沒有來源軸資料；這不代表此隊伍可以全自動或不需操作。",
        tone: "neutral",
      };
  }
}

function timelineTime(step: TimelineStep, clockMode: StructuredTimelineSource["clock_mode"]): {
  known: boolean;
  label: string;
} {
  if (step.time_state === "NOT_STATED" || step.clock_from_ms === null || step.clock_to_ms === null) {
    return { known: false, label: "時間未確認" };
  }
  const prefix = clockMode === "COUNTDOWN" ? "倒數" : "經過";
  const from = formatMilliseconds(step.clock_from_ms);
  const to = formatMilliseconds(step.clock_to_ms);
  return { known: true, label: `${prefix} ${from === to ? from : `${from}–${to}`}` };
}

function formatMilliseconds(milliseconds: number): string {
  const minutes = Math.floor(milliseconds / 60_000);
  const seconds = Math.floor((milliseconds % 60_000) / 1_000);
  const remainder = milliseconds % 1_000;
  return `${minutes}:${String(seconds).padStart(2, "0")}${remainder ? `.${String(remainder).padStart(3, "0")}` : ""}`;
}

function clockModeLabel(mode: StructuredTimelineSource["clock_mode"]): string {
  return mode === "COUNTDOWN" ? "戰鬥倒數" : "經過時間";
}

function durationLabel(milliseconds: number | null): string {
  return milliseconds === null ? "來源未載" : formatMilliseconds(milliseconds);
}

function toleranceLabel(milliseconds: number | null): string {
  return milliseconds === null ? "來源未載" : `±${milliseconds} ms`;
}

function autoStateLabel(state: "ON" | "OFF" | "UNKNOWN"): string {
  if (state === "UNKNOWN") return "來源未載";
  return state === "ON" ? "開啟" : "關閉";
}

function knownText(value: string): string {
  return value === "UNKNOWN" ? "來源未載" : value;
}

function unitLabel(unitKey: string, memberNames: Map<string, string>): string {
  if (unitKey === "NONE") return "不指定";
  if (unitKey === "UNKNOWN") return "來源未載";
  return memberNames.get(unitKey) ?? unitKey;
}
