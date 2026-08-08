import { EmptyState, Panel } from "@pcr-tw/ui";
import Link from "next/link";

export default function NotFound() {
  return (
    <Panel>
      <EmptyState eyebrow="NOT FOUND" title="找不到這筆攻略資料">
        <p>此 ID 未由 API 提供；平台不會自動建立不存在的隊伍或 Evidence。</p>
        <Link className="primary-action" href="/">返回深域攻略</Link>
      </EmptyState>
    </Panel>
  );
}
