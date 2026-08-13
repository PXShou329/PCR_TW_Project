import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import {
  PveModeNav,
  PveStageGrid,
  PveWorkbookDisclosure,
  pveElementLabels,
} from "../../../features/private-pve/components/library-ui";
import { serverApi } from "../../../lib/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "深域攻略｜Excel PVE 隊伍庫",
  description: "依屬性、區域與關卡查詢使用者 Excel 收錄的深域隊伍與操作軸。",
};

type Query = Record<string, string | string[] | undefined>;

function firstValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function normalizedText(value: string | string[] | undefined): string | undefined {
  const normalized = firstValue(value)?.trim().toUpperCase();
  return normalized && normalized.length <= 64 ? normalized : undefined;
}

function positiveInteger(value: string | string[] | undefined): number | undefined {
  const normalized = firstValue(value)?.trim();
  if (!normalized || !/^\d+$/.test(normalized)) return undefined;
  const parsed = Number(normalized);
  return Number.isSafeInteger(parsed) && parsed >= 1 ? parsed : undefined;
}

function hasQueryKey(query: Query, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(query, key);
}

function selectionUrl(element: string, area: number, stage: number): string {
  const query = new URLSearchParams({ element, area: String(area), stage: String(stage) });
  return `/pve/deep?${query}`;
}

export default async function DeepPvePage({ searchParams }: { searchParams: Promise<Query> }) {
  const query = await searchParams;
  const element = normalizedText(query.element);
  const area = positiveInteger(query.area);
  const stage = positiveInteger(query.stage);
  const elementSupplied = hasQueryKey(query, "element");
  const areaSupplied = hasQueryKey(query, "area");
  const stageSupplied = hasQueryKey(query, "stage");
  const hasMalformedQuery = (elementSupplied && !element)
    || (areaSupplied && area === undefined)
    || (stageSupplied && stage === undefined);

  let response = await serverApi().getPveLibraryStages({
    mode: "DEEP",
    ...(element ? { element } : {}),
    ...(area !== undefined ? { area } : {}),
    ...(stage !== undefined ? { stage } : {}),
  });

  if (!elementSupplied) {
    const firstElement = response.data.available_filters.elements[0];
    if (firstElement) {
      const scoped = await serverApi().getPveLibraryStages({ mode: "DEEP", element: firstElement });
      const firstArea = scoped.data.available_filters.areas[0];
      const firstStage = scoped.data.available_filters.stages[0];
      if (firstArea !== undefined && firstStage !== undefined) {
        redirect(selectionUrl(firstElement, firstArea, firstStage));
      }
      response = scoped;
    }
  }

  const choices = response.data.available_filters;
  const validElement = element !== undefined && choices.elements.includes(element);
  const validArea = area !== undefined && choices.areas.includes(area);
  const validStage = stage !== undefined && choices.stages.includes(stage);

  if (!hasMalformedQuery && validElement && element !== undefined && (!areaSupplied || !stageSupplied)) {
    const nextArea = areaSupplied ? area : choices.areas[0];
    const nextStage = stageSupplied ? stage : choices.stages[0];
    if (nextArea !== undefined && nextStage !== undefined) {
      redirect(selectionUrl(element, nextArea, nextStage));
    }
  }

  const validSelection = !hasMalformedQuery && validElement && validArea && validStage;
  const items = validSelection ? response.data.items : [];
  const selectedElementLabel = element ? pveElementLabels[element] ?? element : "";

  return (
    <>
      <PveModeNav activeMode="DEEP" />

      <header className="pve-library-hero pve-library-hero--deep">
        <div>
          <p className="eyebrow">DEEP ZONE · LOCAL WORKBOOK</p>
          <h1>深域關卡攻略</h1>
          <p className="pve-library-hero__lead">
            先選屬性，再從目前 Excel 確實收錄的區域與關卡中查找隊伍。
            新區域匯入後會自動出現在選單，不需要改動頁面上限。
          </p>
        </div>
        <PveWorkbookDisclosure />
      </header>

      <form action="/pve/deep" className="pve-library-filters pve-library-filters--deep panel" method="get">
        <label>
          <span>屬性</span>
          <select aria-label="屬性" defaultValue={validElement ? element : ""} name="element">
            <option disabled value="">選擇屬性</option>
            {choices.elements.map((choice) => (
              <option key={choice} value={choice}>{pveElementLabels[choice] ?? choice}</option>
            ))}
          </select>
        </label>
        <label>
          <span>深域區域</span>
          <select aria-label="深域區域" defaultValue={validArea ? String(area) : ""} disabled={!validElement} name="area">
            <option disabled value="">選擇區域</option>
            {choices.areas.map((choice) => (
              <option key={choice} value={choice}>區域 {choice}</option>
            ))}
          </select>
        </label>
        <label>
          <span>關卡</span>
          <select aria-label="關卡" defaultValue={validStage ? String(stage) : ""} disabled={!validElement} name="stage">
            <option disabled value="">選擇關卡</option>
            {choices.stages.map((choice) => (
              <option key={choice} value={choice}>第 {choice} 關</option>
            ))}
          </select>
        </label>
        <div className="pve-library-filter-actions">
          <button className="primary-action" type="submit">查看這一關</button>
          <Link className="text-link" href="/pve/deep">回到目前首關</Link>
        </div>
      </form>

      {!validSelection && (elementSupplied || areaSupplied || stageSupplied) ? (
        <p className="pve-filter-notice" role="status">
          網址中的篩選不在目前資料清單內，系統不會推測或建立不存在的關卡；請從選單重新選擇。
        </p>
      ) : null}

      <section className="pve-library-results-block" aria-labelledby="deep-results-heading">
        <div className="pve-library-results">
          <div>
            <p className="eyebrow">CURRENT SELECTION</p>
            <h2 id="deep-results-heading">
              {validSelection
                ? `${selectedElementLabel}屬性 · 區域 ${area} · 第 ${stage} 關`
                : "請選擇有效的深域關卡"}
            </h2>
          </div>
          <p>{items.length} 個區段 · <code title={response.meta.dataset_sha256}>{response.meta.dataset_sha256.slice(0, 10)}…</code></p>
        </div>
        <PveStageGrid
          emptyDescription="請從上方目前可用的選項重新選擇；系統不會補出 Excel 沒有的關卡或隊伍。"
          items={items}
        />
      </section>
    </>
  );
}
