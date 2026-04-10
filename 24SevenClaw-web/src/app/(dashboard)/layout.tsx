"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Header } from "@/components/layout/header";
import {
  Sparkles,
  FolderKanban,
  Bot,
  Puzzle,
  Blocks,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { useState } from "react";

const navItems = [
  { href: "/projects", label: "프로젝트", icon: FolderKanban },
  { href: "/registry/agents", label: "에이전트", icon: Bot },
  { href: "/registry/skills", label: "스킬", icon: Puzzle },
  { href: "/registry/mcps", label: "MCP", icon: Blocks },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-950">
      {/* 사이드바 */}
      <aside
        className={`relative flex flex-col border-r border-white/5 bg-slate-900/50 transition-all duration-300 ${
          collapsed ? "w-[68px]" : "w-64"
        }`}
      >
        {/* 로고 */}
        <div className="flex h-16 items-center gap-2.5 border-b border-white/5 px-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/10">
            <Sparkles className="h-4 w-4 text-violet-400" />
          </div>
          {!collapsed && (
            <span className="text-sm font-bold tracking-tight text-white">
              24SevenClaw
            </span>
          )}
        </div>

        {/* 네비게이션 */}
        <nav className="flex-1 space-y-1 p-3">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                  isActive
                    ? "bg-violet-500/10 text-violet-300 shadow-sm shadow-violet-500/5"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
                }`}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className={`h-4.5 w-4.5 shrink-0 ${isActive ? "text-violet-400" : ""}`} />
                {!collapsed && item.label}
              </Link>
            );
          })}
        </nav>

        {/* 접기 토글 */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="m-3 flex items-center justify-center rounded-xl border border-white/5 bg-white/[0.02] py-2 text-slate-500 transition-all hover:bg-white/5 hover:text-slate-300"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </aside>

      {/* 메인 영역 */}
      <div className="flex flex-1 flex-col">
        <Header />
        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}
