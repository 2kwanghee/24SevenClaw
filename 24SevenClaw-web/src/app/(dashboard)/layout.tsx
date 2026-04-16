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
  Shield,
  ScrollText,
  Users2,
} from "lucide-react";
import { useState } from "react";

import { useRBACStore } from "@/stores/rbac-store";
import { usePermissions } from "@/hooks/use-rbac";

const navItems = [
  // activePrefix: 하이라이트 기준 경로 (href와 다른 경우에 지정)
  { href: "/solutions/new", label: "새 솔루션", icon: Sparkles, activePrefix: "/solutions" },
  { href: "/projects", label: "프로젝트", icon: FolderKanban },
  { href: "/registry/agents", label: "에이전트", icon: Bot },
  { href: "/registry/skills", label: "스킬", icon: Puzzle },
  { href: "/registry/mcps", label: "MCP", icon: Blocks },
];

const adminItems = [
  { href: "/admin/users", label: "사용자 관리", icon: Shield },
  { href: "/admin/audit", label: "감사 로그", icon: ScrollText },
];

const settingsItems = [
  { href: "/settings/members", label: "조직 멤버", icon: Users2 },
];

function NavLink({
  href,
  label,
  icon: Icon,
  collapsed,
  isActive,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  collapsed: boolean;
  isActive: boolean;
  activePrefix?: string;
}) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
        isActive
          ? "bg-violet-500/10 text-violet-300 shadow-sm shadow-violet-500/5"
          : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
      }`}
      title={collapsed ? label : undefined}
    >
      <Icon className={`h-4.5 w-4.5 shrink-0 ${isActive ? "text-violet-400" : ""}`} />
      {!collapsed && label}
    </Link>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  // 권한 데이터를 로드하여 스토어에 동기화
  const { data: permsData } = usePermissions();
  const store = useRBACStore();

  // 스토어에 권한 동기화 (이미 RoleGuard에서도 하지만, 사이드바 렌더링용)
  if (permsData && !store.loaded) {
    store.setPermissions(permsData.permissions, permsData.system_role);
  }

  const showAdmin = store.isAdmin();
  const showOrgManage = store.hasPermission("org:manage");

  return (
    <div className="flex min-h-screen bg-slate-950">
      {/* 사이드바 */}
      <aside
        aria-label="메인 네비게이션"
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
        <nav className="flex-1 overflow-y-auto p-3">
          <div className="space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.href}
                {...item}
                collapsed={collapsed}
                isActive={pathname.startsWith(item.activePrefix ?? item.href)}
              />
            ))}
          </div>

          {/* 설정 섹션 */}
          {showOrgManage && (
            <div className="mt-6">
              {!collapsed && (
                <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
                  설정
                </p>
              )}
              <div className="space-y-1">
                {settingsItems.map((item) => (
                  <NavLink
                    key={item.href}
                    {...item}
                    collapsed={collapsed}
                    isActive={pathname.startsWith(item.href)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* 관리 섹션 */}
          {showAdmin && (
            <div className="mt-6">
              {!collapsed && (
                <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
                  관리
                </p>
              )}
              <div className="space-y-1">
                {adminItems.map((item) => (
                  <NavLink
                    key={item.href}
                    {...item}
                    collapsed={collapsed}
                    isActive={pathname.startsWith(item.href)}
                  />
                ))}
              </div>
            </div>
          )}
        </nav>

        {/* 접기 토글 */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "사이드바 펼치기" : "사이드바 접기"}
          aria-expanded={!collapsed}
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
