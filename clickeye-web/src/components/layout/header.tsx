"use client";

import { signOut, useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { LogOut, Bell, HelpCircle, BookOpen, RotateCcw } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { useOnboardingStore } from "@/stores/onboarding-store";
import { LocaleToggle } from "@/components/common/locale-toggle";
import { ThemeSwitcher } from "@/components/common/theme-switcher";

function HelpDropdown() {
  const router = useRouter();
  const { restartTour } = useOnboardingStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const tA = useTranslations("common.aria");
  const tH = useTranslations("common.header");

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        data-tour="help-button"
        aria-label={tA("help")}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
      >
        <HelpCircle className="h-4 w-4" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-11 z-50 min-w-[160px] rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-1 shadow-lg"
        >
          <button
            role="menuitem"
            onClick={() => {
              setOpen(false);
              router.push("/guide");
            }}
            className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            <BookOpen className="h-4 w-4 shrink-0" />
            {tH("viewGuide")}
          </button>
          <button
            role="menuitem"
            onClick={() => {
              setOpen(false);
              restartTour();
            }}
            className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            <RotateCcw className="h-4 w-4 shrink-0" />
            {tH("restartTour")}
          </button>
        </div>
      )}
    </div>
  );
}

export function Header() {
  const { data: session } = useSession();
  const tA = useTranslations("common.aria");
  const tH = useTranslations("common.header");

  if (!session) return null;

  const initials = session.user.displayName
    ? session.user.displayName.charAt(0).toUpperCase()
    : "U";

  return (
    <header className="flex h-16 items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-header)] px-8 backdrop-blur-sm">
      <div />
      <div className="flex items-center gap-4">
        {/* 언어 토글 (사용자 향 페이지 한정 — /admin/* 내부에서 자체 미노출) */}
        <LocaleToggle />

        {/* 테마 토글 (라이트/다크) */}
        <ThemeSwitcher />

        {/* 알림 */}
        <button
          aria-label={tA("notifications")}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
        >
          <Bell className="h-4 w-4" />
        </button>

        {/* 도움말 드롭다운 */}
        <HelpDropdown />

        {/* 구분선 */}
        <div className="h-6 w-px bg-[var(--border-medium)]" />

        {/* 유저 정보 */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-bg)] text-sm font-medium text-[var(--accent-text)]">
            {session.user.avatarUrl ? (
              <span>{initials}</span>
            ) : (
              initials
            )}
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-medium text-[var(--text-primary)]">
              {session.user.displayName}
            </p>
          </div>
          <span className="rounded-md bg-[var(--accent-bg)] px-2 py-0.5 text-xs font-medium text-[var(--accent-text)]">
            {session.user.plan}
          </span>
        </div>

        {/* 로그아웃 */}
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover-danger)] hover:text-red-400"
          title={tH("logout")}
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
