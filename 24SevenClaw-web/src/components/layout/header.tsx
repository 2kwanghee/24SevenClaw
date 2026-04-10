"use client";

import { signOut, useSession } from "next-auth/react";
import { LogOut, Bell } from "lucide-react";

export function Header() {
  const { data: session } = useSession();

  if (!session) return null;

  const initials = session.user.displayName
    ? session.user.displayName.charAt(0).toUpperCase()
    : "U";

  return (
    <header className="flex h-16 items-center justify-between border-b border-white/5 bg-slate-950/50 px-8 backdrop-blur-sm">
      <div />
      <div className="flex items-center gap-4">
        {/* 알림 */}
        <button className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300">
          <Bell className="h-4 w-4" />
        </button>

        {/* 구분선 */}
        <div className="h-6 w-px bg-white/10" />

        {/* 유저 정보 */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/10 text-sm font-medium text-violet-300">
            {session.user.avatarUrl ? (
              <span>{initials}</span>
            ) : (
              initials
            )}
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-medium text-slate-200">
              {session.user.displayName}
            </p>
          </div>
          <span className="rounded-md bg-violet-500/10 px-2 py-0.5 text-xs font-medium text-violet-300">
            {session.user.plan}
          </span>
        </div>

        {/* 로그아웃 */}
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-slate-500 transition-colors hover:bg-red-500/10 hover:text-red-400"
          title="로그아웃"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
