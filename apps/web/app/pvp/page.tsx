import { Badge, EmptyState, Panel } from "@pcr-tw/ui";
import { serverApi } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function PvpPage() {
  const response = await serverApi().getPvpCounters();
  return (
    <>
      <header className="page-heading">
        <p className="eyebrow">BATTLE ARENA · TW</p>
        <h1>競技場解陣</h1>
        <p>只顯示可追溯的 exact verified counter；相似隊伍不會冒充已驗證反制。</p>
      </header>

      {response.data.length === 0 ? (
        <Panel>
          <EmptyState eyebrow="NO VERIFIED COUNTER" title="目前沒有可公開的實證反制">
            <p>Registry 尚無正式案例，因此本頁維持空結果，不建立示意隊或理論隊。</p>
            <div className="badge-row">
              <Badge tone="warning">NO_VERIFIED_COUNTER</Badge>
              <Badge>0 筆正式案例</Badge>
            </div>
          </EmptyState>
        </Panel>
      ) : null}
    </>
  );
}
