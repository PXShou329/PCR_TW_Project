"use client";

import { createApiClient, type Evidence } from "@pcr-tw/api-client";
import { Badge } from "@pcr-tw/ui";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

type DrawerState =
  | { kind: "closed" }
  | { kind: "loading"; evidenceId: string }
  | { kind: "loaded"; evidence: Evidence }
  | { kind: "error"; evidenceId: string };

export function EvidenceDrawer({
  evidenceIds,
  buttonLabel,
  compact = false,
  contextLocator,
}: {
  evidenceIds: string[];
  buttonLabel?: string;
  compact?: boolean;
  contextLocator?: string;
}) {
  const [state, setState] = useState<DrawerState>({ kind: "closed" });
  const [mounted, setMounted] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const requestTokenRef = useRef(0);

  const isOpen = state.kind !== "closed";

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!isOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
        return;
      }
      if (event.key !== "Tab") return;

      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((element) => !element.hasAttribute("hidden"));
      if (focusable.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable.at(-1)!;
      const active = document.activeElement;
      if (event.shiftKey && (active === first || !dialog.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [isOpen]);

  function close() {
    requestTokenRef.current += 1;
    setState({ kind: "closed" });
    queueMicrotask(() => triggerRef.current?.focus());
  }

  async function open(evidenceId: string, trigger: HTMLButtonElement) {
    const requestToken = requestTokenRef.current + 1;
    requestTokenRef.current = requestToken;
    triggerRef.current = trigger;
    setState({ kind: "loading", evidenceId });
    try {
      const result = await createApiClient({ baseUrl: "" }).getEvidence(evidenceId);
      if (requestTokenRef.current === requestToken) {
        setState({ kind: "loaded", evidence: result.data });
      }
    } catch {
      if (requestTokenRef.current === requestToken) {
        setState({ kind: "error", evidenceId });
      }
    }
  }

  if (evidenceIds.length === 0) {
    return <p className="muted">此隊伍沒有可開啟的 Evidence；不得據此推論來源。</p>;
  }

  return (
    <>
      <div
        className={`evidence-list${compact ? " evidence-list--compact" : ""}`}
        aria-label="Evidence 清單"
      >
        {evidenceIds.map((evidenceId) => (
          <button
            className="evidence-button"
            key={evidenceId}
            onClick={(event) => void open(evidenceId, event.currentTarget)}
            type="button"
          >
            <span>{buttonLabel ?? evidenceId}</span>
            {buttonLabel ? <code>{evidenceId}</code> : null}
            <span aria-hidden="true">→</span>
          </button>
        ))}
      </div>

      {mounted && isOpen ? createPortal(
        <div className="drawer-layer">
          <div className="drawer-backdrop" aria-hidden="true" onClick={close} />
          <aside
            className="drawer"
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="evidence-title"
            tabIndex={-1}
          >
            <div className="drawer__header">
              <div>
                <p className="eyebrow">Evidence Drawer</p>
                <h2 id="evidence-title">
                  {state.kind === "loaded" ? state.evidence.evidence_id : "證據資料"}
                </h2>
              </div>
              <button ref={closeButtonRef} className="icon-button" onClick={close} type="button">
                <span aria-hidden="true">×</span>
                <span className="sr-only">關閉</span>
              </button>
            </div>

            {state.kind === "loading" ? <p className="drawer__message">正在向 API 取得正文核對紀錄…</p> : null}
            {state.kind === "error" ? (
              <div className="drawer__message" role="alert">
                <h3>Evidence 暫時無法取得</h3>
                <p>API 未回傳 {state.evidenceId}。平台不會以快取印象或搜尋摘要補寫內容。</p>
              </div>
            ) : null}
            {state.kind === "loaded" ? (
              <EvidenceBody evidence={state.evidence} contextLocator={contextLocator} />
            ) : null}
          </aside>
        </div>,
        document.body,
      ) : null}
    </>
  );
}

function EvidenceBody({
  evidence,
  contextLocator,
}: {
  evidence: Evidence;
  contextLocator?: string;
}) {
  return (
    <div className="drawer__body">
      <div className="badge-row">
        <Badge tone={evidence.source_tier === "OFFICIAL" ? "success" : "warning"}>
          {evidence.source_tier}
        </Badge>
        <Badge tone="info">信心 {evidence.evidence_confidence}</Badge>
        <Badge>{evidence.server}</Badge>
      </div>

      <section>
        <p className="eyebrow">來源標題</p>
        <h3>{evidence.source_title}</h3>
        <p className="locator">Evidence 登錄定位：{evidence.source_locator}</p>
        {contextLocator ? <p className="locator">本次核對定位：{contextLocator}</p> : null}
        <a className="text-link" href={evidence.source_url} rel="noreferrer" target="_blank">
          開啟已登錄來源 <span aria-hidden="true">↗</span>
        </a>
      </section>

      <section>
        <p className="eyebrow">正文支持內容</p>
        <p>{evidence.claim_summary}</p>
      </section>

      <section className="caution-box">
        <p className="eyebrow">限制</p>
        <p>{evidence.limitations}</p>
      </section>

      <dl className="compact-facts">
        <div><dt>登錄 Claim</dt><dd>{evidence.declared_claim_id ?? "未登錄"}</dd></div>
        <div><dt>已連結 Claim</dt><dd>{evidence.linked_claim_id ?? "待裁決"}</dd></div>
        <div><dt>發布日</dt><dd>{evidence.published_date ?? "未確認"}</dd></div>
        <div><dt>最後核對</dt><dd>{evidence.verified_date}</dd></div>
        <div><dt>狀態</dt><dd>{evidence.status}</dd></div>
      </dl>
    </div>
  );
}
