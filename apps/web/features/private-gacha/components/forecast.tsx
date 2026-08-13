"use client";

import {
  ApiError,
  createApiClient,
  type GachaLibraryForecast,
  type GachaLibraryForecastData,
} from "@pcr-tw/api-client";
import { Badge, Definition, EmptyState, Panel } from "@pcr-tw/ui";
import { useEffect, useState } from "react";

type LoadState =
  | { status: "loading" }
  | {
      status: "ready";
      data: GachaLibraryForecastData;
      datasetSha256: string;
      sourceDocument: string;
    }
  | { status: "error"; message: string };

const privateAssetPattern = /^\/api\/v1\/gacha-library\/assets\/[0-9a-f]{64}$/;

export function PrivateGachaForecastSection() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    const api = createApiClient({ baseUrl: "" });
    api.getGachaLibraryForecasts().then(
      (response) => {
        if (active) {
          setState({
            status: "ready",
            data: response.data,
            datasetSha256: response.meta.dataset_sha256,
            sourceDocument: response.meta.source_document.content_addressed_filename,
          });
        }
      },
      (error: unknown) => {
        if (!active) return;
        const message = error instanceof ApiError
          ? `${error.message} (${error.status})`
          : "UNKNOWN_ERROR";
        setState({ status: "error", message });
      },
    );
    return () => {
      active = false;
    };
  }, []);

  return (
    <section
      className="section-block private-gacha-section"
      aria-labelledby="private-gacha-heading"
      data-load-state={state.status}
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">PRIVATE DOCX FORECAST · NOT OFFICIAL</p>
          <h2 id="private-gacha-heading">私人文件預測／非官方</h2>
        </div>
        <p>這 17 池只呈現使用者提供文件的原始預測；不改寫下方 canonical timeline。</p>
      </div>

      {state.status === "loading" ? (
        <Panel className="private-gacha-status" aria-live="polite">
          <p>正在讀取本機私人卡池文件…</p>
        </Panel>
      ) : state.status === "error" ? (
        <Panel className="private-gacha-status" aria-live="polite">
          <EmptyState eyebrow="PRIVATE SOURCE UNAVAILABLE" title="私人文件預測暫時無法取得">
            <p>公共 canonical timeline 仍可使用；私人資料不會以猜測內容補齊。</p>
            <code>{state.message}</code>
          </EmptyState>
        </Panel>
      ) : (
        <PrivateForecastContent
          data={state.data}
          datasetSha256={state.datasetSha256}
          sourceDocument={state.sourceDocument}
        />
      )}
    </section>
  );
}

function PrivateForecastContent({
  data,
  datasetSha256,
  sourceDocument,
}: {
  data: GachaLibraryForecastData;
  datasetSha256: string;
  sourceDocument: string;
}) {
  const forecasts = [...data.items].sort(
    (left, right) => left.review_order - right.review_order,
  );
  const namesCount = forecasts.reduce(
    (total, forecast) => total + forecast.raw_character_names.length,
    0,
  );
  const coverageStart = forecasts.reduce(
    (minimum, forecast) => minimum < forecast.forecast_start ? minimum : forecast.forecast_start,
    forecasts[0]?.forecast_start ?? "UNKNOWN",
  );
  const coverageEnd = forecasts.reduce(
    (maximum, forecast) => maximum > forecast.forecast_end ? maximum : forecast.forecast_end,
    forecasts[0]?.forecast_end ?? "UNKNOWN",
  );
  const uniqueWindows = new Set(
    forecasts.map((forecast) => `${forecast.forecast_start}/${forecast.forecast_end}`),
  ).size;
  return (
    <>
      <Panel className="private-gacha-scope">
        <div className="private-gacha-scope__heading">
          <div>
            <div className="badge-row">
              <Badge tone="warning">私人文件預測</Badge>
              <Badge tone="neutral">非官方</Badge>
              <Badge tone="info">{forecasts.length} 池</Badge>
            </div>
            <h3>文件日期與名稱均維持來源原文</h3>
          </div>
          <code title={datasetSha256}>{shortHash(datasetSha256)}</code>
        </div>
        <dl className="private-gacha-summary" aria-label="私人文件預測資料範圍">
          <Definition term="來源文件">使用者提供 DOCX（{sourceDocument}）</Definition>
          <Definition term="預測期間">
            {formatInterval(coverageStart, coverageEnd)}
          </Definition>
          <Definition term="角色標籤">{namesCount}</Definition>
          <Definition term="不同日期區間">{uniqueWindows}</Definition>
        </dl>
        <p className="private-gacha-disclosure">
          文件中的中文名稱尚未等同台服官方角色名稱；圖片只作日版卡池來源定位，圖片上的日版日期不會當成台服日期。
        </p>
      </Panel>

      {forecasts.length > 0 ? (
        <div className="private-gacha-grid">
          {forecasts.map((forecast) => (
            <PrivateForecastCard forecast={forecast} key={forecast.candidate_id} />
          ))}
        </div>
      ) : (
        <Panel>
          <EmptyState eyebrow="NO PRIVATE FORECASTS" title="文件中沒有可呈現的卡池">
            <p>不會由圖片或其他公開時間線補造私人文件內容。</p>
          </EmptyState>
        </Panel>
      )}
    </>
  );
}

function PrivateForecastCard({ forecast }: { forecast: GachaLibraryForecast }) {
  return (
    <article
      className="panel private-gacha-card"
      data-forecast-id={forecast.candidate_id}
      data-pool-kind={forecast.source_declared_pool_kind}
    >
      <PrivateForecastImage forecast={forecast} />
      <div className="private-gacha-card__body">
        <div className="private-gacha-card__heading">
          <div className="badge-row">
            <Badge tone={poolKindTone(forecast.source_declared_pool_kind)}>
              {poolKindLabel(forecast.source_declared_pool_kind)}
            </Badge>
            <Badge tone="warning">非官方</Badge>
          </div>
          <span>{forecast.raw_sequence_label ?? `文件順序 ${forecast.review_order}`}</span>
        </div>

        <ul className="private-gacha-names" aria-label={`第 ${forecast.review_order} 池原始角色名稱`}>
          {forecast.raw_character_names.map((name, index) => (
            <li key={`${forecast.candidate_id}-${index}`}>{name}</li>
          ))}
        </ul>
        <p className="private-gacha-raw-note">文件原始名稱 · 尚未確認為台服官方名稱</p>

        <div className="gacha-window private-gacha-window" aria-label="文件預測日期">
          <span>文件台服預測</span>
          <strong>{formatInterval(forecast.forecast_start, forecast.forecast_end)}</strong>
          <small>日精度 · 起訖邊界語意未記載</small>
        </div>

        {forecast.parser_warnings.length > 0 ? (
          <div className="private-gacha-warnings">
            <strong>需人工覆核</strong>
            <ul>
              {forecast.parser_warnings.map((warning) => (
                <li key={warning}><code>{warning}</code> · {warningLabel(warning)}</li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="private-gacha-no-warning">結構解析無警告；角色身分仍未人工確認。</p>
        )}
      </div>
    </article>
  );
}

function PrivateForecastImage({ forecast }: { forecast: GachaLibraryForecast }) {
  const validUrl = privateAssetPattern.test(forecast.image.asset_url)
    && forecast.image.asset_url.endsWith(forecast.image.sha256);
  const [failed, setFailed] = useState(false);

  return (
    <div className="private-gacha-card__media" data-image-state={!validUrl ? "rejected" : failed ? "failed" : "ready"}>
      {validUrl && !failed ? (
        // The proxy accepts only the catalog's same-origin SHA-256 asset path.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          alt={`第 ${forecast.review_order} 池文件內嵌卡池圖片`}
          loading="lazy"
          onError={() => setFailed(true)}
          src={forecast.image.asset_url}
        />
      ) : (
        <div className="private-gacha-image-fallback" role="img" aria-label="來源圖片不可用">
          <span>來源圖片不可用</span>
          <small>{validUrl ? "本機圖片載入失敗" : "已拒絕非 same-origin 圖片路徑"}</small>
        </div>
      )}
    </div>
  );
}

function poolKindLabel(kind: GachaLibraryForecast["source_declared_pool_kind"]): string {
  if (kind === "RERUN") return "復刻池";
  if (kind === "PERMANENT_PICKUP") return "常駐角色";
  return "限定 UP";
}

function poolKindTone(
  kind: GachaLibraryForecast["source_declared_pool_kind"],
): "info" | "neutral" | "warning" {
  if (kind === "RERUN") return "neutral";
  if (kind === "PERMANENT_PICKUP") return "info";
  return "warning";
}

function warningLabel(warning: string): string {
  if (warning === "UNQUOTED_CHARACTER_SEQUENCE") {
    return "原文含未加引號的角色序列";
  }
  return "解析器回報未分類警告";
}

function formatInterval(start: string, end: string): string {
  return start === end ? start : `${start} – ${end}`;
}

function shortHash(hash: string): string {
  return hash.length > 12 ? `${hash.slice(0, 12)}…` : hash;
}
