import type { PveStageSummary } from "@pcr-tw/api-client";
import Link from "next/link";

export type PveMode = "DEEP" | "REMEMBRANCE" | "LUNA_TOWER";

export const pveModeLabels: Record<string, string> = {
  DEEP: "深域",
  LUNA_TOWER: "露娜塔",
  REMEMBRANCE: "追憶戰域",
};

export const pveElementLabels: Record<string, string> = {
  DARK: "闇",
  FIRE: "火",
  HATOU: "霸瞳",
  LIGHT: "光",
  LUNA: "露娜塔",
  MAITREYA: "彌勒",
  NONE: "無屬性",
  ARACHNE: "阿剌克涅",
  WATER: "水",
  WIND: "風",
  ZANE: "贊恩",
};

const modeLinks: Array<{
  href: string;
  label: string;
  mode: PveMode;
  summary: string;
}> = [
  { href: "/pve/deep", label: "深域", mode: "DEEP", summary: "屬性 · 區域 · 關卡" },
  { href: "/pve/remembrance", label: "追憶戰域", mode: "REMEMBRANCE", summary: "首領區段攻略" },
  { href: "/pve/luna-tower", label: "露娜塔", mode: "LUNA_TOWER", summary: "塔頂與 EX 區段" },
];

export function PveModeNav({ activeMode }: { activeMode: PveMode }) {
  return (
    <nav className="pve-mode-nav" aria-label="PVE 攻略分類">
      {modeLinks.map((item) => (
        <Link
          aria-current={item.mode === activeMode ? "page" : undefined}
          className="pve-mode-nav__item"
          href={item.href}
          key={item.mode}
        >
          <strong>{item.label}</strong>
          <span>{item.summary}</span>
        </Link>
      ))}
    </nav>
  );
}

export function PveWorkbookDisclosure() {
  return (
    <div className="pve-library-disclosure" aria-label="資料驗證狀態">
      <span className="pve-library-disclosure__mark" aria-hidden="true">XLSX</span>
      <div>
        <strong>Excel 來源整理</strong>
        <span>保留原始隊伍與操作軸，未獨立驗證通關</span>
      </div>
    </div>
  );
}

export function PveStageGrid({
  emptyDescription,
  items,
}: {
  emptyDescription: string;
  items: PveStageSummary[];
}) {
  if (items.length === 0) {
    return (
      <div className="empty-state panel">
        <h2>目前沒有符合條件的 Excel 區段</h2>
        <p className="empty-state__body">{emptyDescription}</p>
      </div>
    );
  }

  return (
    <div className="pve-library-grid">
      {items.map((stage) => <PveStageCard key={stage.stage_id} stage={stage} />)}
    </div>
  );
}

function PveStageCard({ stage }: { stage: PveStageSummary }) {
  const label = stage.label_raw || `${pveModeLabels[stage.mode] ?? stage.mode} ${stage.stage_id}`;
  const refs = stage.stage_refs
    .map((ref) => stage.mode === "DEEP" ? `${ref.area}-${ref.stage}` : String(ref.stage))
    .join("、");

  return (
    <Link
      className="pve-library-card panel"
      href={`/pve/library/${encodeURIComponent(stage.stage_id)}`}
      prefetch={false}
    >
      <div className="pve-library-card__topline">
        <span className="badge badge--info">{pveModeLabels[stage.mode] ?? stage.mode}</span>
        <span className="badge">{pveElementLabels[stage.element] ?? stage.element}</span>
      </div>
      <h3>{label}</h3>
      <p className="pve-library-card__refs">Excel 區段標記：{refs || "未標記"}</p>
      <div className="pve-library-card__footer">
        <strong>收錄 {stage.team_count} 隊</strong>
        <span aria-hidden="true">查看攻略 →</span>
      </div>
    </Link>
  );
}
