import type { Metadata } from "next";
import {
  PveModeNav,
  PveStageGrid,
  PveWorkbookDisclosure,
} from "../../../components/pve-library-ui";
import { serverApi } from "../../../lib/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "露娜塔攻略｜Excel PVE 隊伍庫",
  description: "獨立瀏覽 Excel 收錄的露娜塔與塔頂 EX 隊伍及操作軸。",
};

export default async function LunaTowerPvePage() {
  const response = await serverApi().getPveLibraryStages({ mode: "LUNA_TOWER" });

  return (
    <>
      <PveModeNav activeMode="LUNA_TOWER" />

      <header className="pve-library-hero pve-library-hero--luna">
        <div>
          <p className="eyebrow">LUNA TOWER · LOCAL WORKBOOK</p>
          <h1>露娜塔攻略</h1>
          <p className="pve-library-hero__lead">
            露娜塔獨立呈現目前工作簿收錄的塔頂與 EX 區段。沒有多餘的深域區域輸入，
            直接選擇需要查看的攻略即可。
          </p>
        </div>
        <PveWorkbookDisclosure />
      </header>

      <section className="pve-library-results-block" aria-labelledby="luna-results-heading">
        <div className="pve-library-results">
          <div>
            <p className="eyebrow">LUNA TOWER SECTIONS</p>
            <h2 id="luna-results-heading">目前收錄的露娜塔區段</h2>
          </div>
          <p>{response.data.total} 個區段 · <code title={response.meta.dataset_sha256}>{response.meta.dataset_sha256.slice(0, 10)}…</code></p>
        </div>
        <PveStageGrid
          emptyDescription="目前 Excel 尚未收錄露娜塔區段；更新資料後會直接出現在這裡。"
          items={response.data.items}
        />
      </section>
    </>
  );
}
