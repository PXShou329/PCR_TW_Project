"use client";

import { useState } from "react";

const localAssetPattern = /^\/api\/v1\/pve-library\/assets\/[0-9a-f]{64}$/;
const estertionIconPattern =
  /^https:\/\/redive\.estertion\.win\/icon\/unit\/[0-9]{6}\.webp$/;

type PortraitImageSource = "external" | "workbook" | "failed";

interface PvePortraitProps {
  assetUrl: string;
  displayPosition: number;
  iconUrl: string | null;
  mappingStatus: string;
  twName: string | null;
  unitKey: string | null;
}

export function PvePortrait({
  assetUrl,
  displayPosition,
  iconUrl,
  mappingStatus,
  twName,
  unitKey,
}: PvePortraitProps) {
  const workbookAssetUrl = localAssetPattern.test(assetUrl) ? assetUrl : null;
  const externalIconUrl = iconUrl && estertionIconPattern.test(iconUrl) ? iconUrl : null;
  const [imageSource, setImageSource] = useState<PortraitImageSource>(() => {
    if (externalIconUrl) return "external";
    if (workbookAssetUrl) return "workbook";
    return "failed";
  });
  const currentUrl = imageSource === "external"
    ? externalIconUrl
    : imageSource === "workbook"
      ? workbookAssetUrl
      : null;
  const alt = twName ? `位置 ${displayPosition}：${twName}` : `位置 ${displayPosition}`;

  return (
    <li
      className="pve-portrait"
      data-image-source={imageSource}
      data-mapping-status={mappingStatus}
    >
      {currentUrl === null ? (
        <span className="pve-portrait__fallback" role="img" aria-label={`${alt}（頭像無法載入）`}>
          <span aria-hidden="true">?</span>
        </span>
      ) : (
        <img
          alt={alt}
          decoding="async"
          height={112}
          loading="lazy"
          onError={() => {
            if (imageSource === "external" && workbookAssetUrl) {
              setImageSource("workbook");
            } else {
              setImageSource("failed");
            }
          }}
          referrerPolicy="no-referrer"
          src={currentUrl}
          title={twName ?? unitKey ?? undefined}
          width={112}
        />
      )}
      <span className="pve-portrait__position" aria-hidden="true">{displayPosition}</span>
    </li>
  );
}
