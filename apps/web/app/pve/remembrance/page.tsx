import type { Metadata } from "next";
import Link from "next/link";
import {
  PveModeNav,
  PveStageGrid,
  PveWorkbookDisclosure,
  pveElementLabels,
} from "../../../components/pve-library-ui";
import { serverApi } from "../../../lib/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "追憶戰域攻略｜Excel PVE 隊伍庫",
  description: "獨立瀏覽 Excel 收錄的追憶戰域首領區段、隊伍與操作軸。",
};

type Query = Record<string, string | string[] | undefined>;

function firstValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function RemembrancePvePage(
  { searchParams }: { searchParams: Promise<Query> },
) {
  const query = await searchParams;
  const rawElement = firstValue(query.element)?.trim().toUpperCase();
  const element = rawElement && rawElement.length <= 64 ? rawElement : undefined;
  const malformedElement = Boolean(rawElement && rawElement.length > 64);
  const response = await serverApi().getPveLibraryStages({
    mode: "REMEMBRANCE",
    ...(element ? { element } : {}),
  });
  const choices = response.data.available_filters;
  const validElement = !malformedElement && (element === undefined || choices.elements.includes(element));
  const items = validElement ? response.data.items : [];

  return (
    <>
      <PveModeNav activeMode="REMEMBRANCE" />

      <header className="pve-library-hero pve-library-hero--remembrance">
        <div>
          <p className="eyebrow">REMEMBRANCE · LOCAL WORKBOOK</p>
          <h1>追憶戰域攻略</h1>
          <p className="pve-library-hero__lead">
            追憶戰域依 Excel 的首領與合併樓層區段呈現，保留來源原本的分組方式，
            不套用深域的「區域／第幾關」語意。
          </p>
        </div>
        <PveWorkbookDisclosure />
      </header>

      <form action="/pve/remembrance" className="pve-library-filters pve-library-filters--compact panel" method="get">
        <label>
          <span>戰域首領</span>
          <select aria-label="戰域首領" defaultValue={validElement ? element ?? "" : ""} name="element">
            <option value="">全部首領</option>
            {choices.elements.map((choice) => (
              <option key={choice} value={choice}>{pveElementLabels[choice] ?? choice}</option>
            ))}
          </select>
        </label>
        <div className="pve-library-filter-actions">
          <button className="primary-action" type="submit">套用篩選</button>
          <Link className="text-link" href="/pve/remembrance">顯示全部</Link>
        </div>
      </form>

      {!validElement ? (
        <p className="pve-filter-notice" role="status">
          網址中的首領不在目前 Excel 清單內；請從選單重新選擇。
        </p>
      ) : null}

      <section className="pve-library-results-block" aria-labelledby="remembrance-results-heading">
        <div className="pve-library-results">
          <div>
            <p className="eyebrow">REMEMBRANCE SECTIONS</p>
            <h2 id="remembrance-results-heading">
              {element && validElement ? `${pveElementLabels[element] ?? element}收錄區段` : "全部追憶戰域區段"}
            </h2>
          </div>
          <p>{items.length} 個區段 · <code title={response.meta.dataset_sha256}>{response.meta.dataset_sha256.slice(0, 10)}…</code></p>
        </div>
        <PveStageGrid
          emptyDescription="目前 Excel 沒有符合這個首領條件的區段；系統不會推測缺少的樓層。"
          items={items}
        />
      </section>
    </>
  );
}
