"use client";

import { EmptyState, Panel } from "@pcr-tw/ui";
import { useEffect } from "react";

export default function ErrorPage({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Panel>
      <EmptyState eyebrow="API UNAVAILABLE" title="目前無法取得攻略資料">
        <p>平台不會在 API 失聯時用舊印象補寫攻略。請稍後再試。</p>
        <button className="primary-action" onClick={retry} type="button">重新取得</button>
      </EmptyState>
    </Panel>
  );
}
