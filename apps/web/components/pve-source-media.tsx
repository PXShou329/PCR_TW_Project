"use client";

import { useState } from "react";

interface PveSourceMediaProps {
  embedUrl: string;
  externalUrl: string;
  label: string;
}

function safeHttpUrl(raw: string): string | null {
  try {
    const url = new URL(raw);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function safeYouTubeEmbed(raw: string): string | null {
  const safe = safeHttpUrl(raw);
  if (!safe) return null;
  const url = new URL(safe);
  if (url.protocol !== "https:" || url.hostname !== "www.youtube-nocookie.com") return null;
  return /^\/embed\/[A-Za-z0-9_-]{6,}$/.test(url.pathname) ? url.toString() : null;
}

export function PveYouTubeMedia({ embedUrl, externalUrl, label }: PveSourceMediaProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const safeEmbed = safeYouTubeEmbed(embedUrl);
  const safeExternal = safeHttpUrl(externalUrl);

  return (
    <div className="pve-video" data-player-state={isPlaying ? "loaded" : "idle"}>
      {isPlaying && safeEmbed ? (
        <div className="pve-video__frame">
          <iframe
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            src={safeEmbed}
            title={`${label}影片播放器`}
          />
        </div>
      ) : (
        <button
          className="pve-video__load"
          disabled={!safeEmbed}
          onClick={() => setIsPlaying(true)}
          type="button"
        >
          <span aria-hidden="true">▶</span>
          {safeEmbed ? "載入 YouTube 影片" : "影片嵌入網址無效"}
          <small>點擊後才連線至 YouTube</small>
        </button>
      )}
      {safeExternal ? (
        <a className="source-link" href={safeExternal} rel="noreferrer" target="_blank">
          在外部網站開啟 <span className="sr-only">（另開新分頁）</span>
        </a>
      ) : null}
    </div>
  );
}
