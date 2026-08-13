import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "公主連結台服 AI 攻略研究所",
  description: "以證據為核心的台服 Guide-Only 攻略平台",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-Hant-TW" data-scroll-behavior="smooth">
      <body>
        <a className="skip-link" href="#main-content">
          跳至主要內容
        </a>
        <header className="site-header">
          <div className="site-header__inner">
            <Link className="brand" href="/" aria-label="公主連結台服 AI 攻略研究所首頁">
              <span className="brand__mark" aria-hidden="true">PCR</span>
              <span>
                <strong>台服 AI 攻略研究所</strong>
                <small>Guide-Only Strategy Platform</small>
              </span>
            </Link>
            <nav aria-label="主要導覽">
              <Link href="/">深域攻略</Link>
              <Link href="/pve/deep">PVE 攻略</Link>
              <Link href="/pvp">競技場解陣</Link>
              <Link href="/parena">公主競技場</Link>
              <Link href="/gacha">抽卡未來視</Link>
            </nav>
          </div>
        </header>
        <main id="main-content" className="page-shell">{children}</main>
        <footer className="site-footer">
          <p>攻略狀態與限制會如實揭露；本平台不登入或操作遊戲。</p>
        </footer>
      </body>
    </html>
  );
}
