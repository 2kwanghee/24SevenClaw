"use client";

import { signOut, useSession } from "next-auth/react";
import { LogOut, Bell } from "lucide-react";
import { ThemeSwitcher } from "@/components/common/theme-switcher";

export function Header() {
  const { data: session } = useSession();

  if (!session) return null;

  const initials = session.user.displayName
    ? session.user.displayName.charAt(0).toUpperCase()
    : "U";

  return (
    <header className="flex h-16 items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-header)] px-8 backdrop-blur-sm">
      <div />
      <div className="flex items-center gap-4">
        {/* 테마 스위처 */}
        <ThemeSwitcher />

        {/* 구분선 */}
        <div className="h-6 w-px bg-[var(--border-medium)]" />

        {/* 알림 */}
        <button
          aria-label="알림"
          className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
        >
          <Bell className="h-4 w-4" />
        </button>

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
          title="로그아웃"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
