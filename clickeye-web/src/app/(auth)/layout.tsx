"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { ScanEye, LayoutDashboard, ShieldCheck, Server } from "lucide-react";

import { LocaleToggle } from "@/components/common/locale-toggle";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const t = useTranslations("auth.layout");
  const isLogin = pathname === "/login";

  const features = [
    {
      key: "console",
      icon: LayoutDashboard,
      title: t("features.console.title"),
      desc: t("features.console.desc"),
    },
    {
      key: "governance",
      icon: ShieldCheck,
      title: t("features.governance.title"),
      desc: t("features.governance.desc"),
    },
    {
      key: "hybrid",
      icon: Server,
      title: t("features.hybrid.title"),
      desc: t("features.hybrid.desc"),
    },
  ];

  return (
    <div className="flex min-h-screen">
      {/* 좌측 브랜딩 패널 */}
      <div className="relative hidden w-1/2 overflow-hidden border-r border-[var(--border-subtle)] bg-[var(--bg-surface)] lg:flex lg:flex-col lg:justify-between lg:p-12">
        {/* 로고 */}
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent)]">
            <ScanEye className="h-5 w-5 text-[var(--accent-fg)]" aria-hidden="true" />
          </div>
          <span className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
            ClickEye
          </span>
        </Link>

        {/* 중앙 히어로 */}
        <div className="space-y-8">
          <div className="space-y-4">
            <p className="font-mono text-[11px] uppercase tracking-wider text-[var(--accent)]">
              {t("eyebrow")}
            </p>
            <h2 className="text-4xl font-bold leading-tight tracking-tight text-[var(--text-primary)]">
              {t("heroTitleLine1")}
              <br />
              {t("heroTitleLine2")}
            </h2>
            <p className="max-w-md text-lg leading-relaxed text-[var(--text-secondary)]">
              {t("heroDescLine1")}
              <br />
              {t("heroDescLine2")}
            </p>
          </div>

          {/* 피쳐 카드 */}
          <div className="space-y-3">
            {features.map((f) => (
              <div
                key={f.key}
                className="flex items-start gap-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-4 transition-colors hover:bg-[var(--bg-hover)]"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
                  <f.icon className="h-5 w-5 text-[var(--accent)]" aria-hidden="true" />
                </div>
                <div>
                  <p className="font-semibold text-[var(--text-primary)]">{f.title}</p>
                  <p className="text-sm text-[var(--text-secondary)]">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 하단 */}
        <p className="text-sm text-[var(--text-muted)]">{t("copyright")}</p>
      </div>

      {/* 우측 폼 패널 */}
      <div className="relative flex w-full flex-col items-center justify-center bg-[var(--bg-base)] px-6 py-12 lg:w-1/2">
        {/* 언어 선택기 (로그인 전 화면에서도 노출) */}
        <div className="absolute right-4 top-4 z-10">
          <LocaleToggle />
        </div>

        {/* 모바일 로고 */}
        <div className="mb-8 flex items-center gap-3 lg:hidden">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent)]">
            <ScanEye className="h-5 w-5 text-[var(--accent-fg)]" aria-hidden="true" />
          </div>
          <span className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
            ClickEye
          </span>
        </div>

        {/* 폼 컨테이너 */}
        <div className="w-full max-w-[420px]">
          {/* 탭 네비게이션 */}
          <div className="mb-8 flex rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1">
            <Link
              href="/login"
              className={`flex-1 rounded-xl py-2.5 text-center text-sm font-medium transition-all ${
                isLogin
                  ? "bg-[var(--accent)] text-[var(--accent-fg)] shadow-sm"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              {t("tabLogin")}
            </Link>
            <Link
              href="/register"
              className={`flex-1 rounded-xl py-2.5 text-center text-sm font-medium transition-all ${
                !isLogin
                  ? "bg-[var(--accent)] text-[var(--accent-fg)] shadow-sm"
                  : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              }`}
            >
              {t("tabRegister")}
            </Link>
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}
