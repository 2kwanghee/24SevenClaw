"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { Header } from "@/components/layout/header";
import {
  Sparkles,
  FolderKanban,
  Bot,
  Puzzle,
  Blocks,
  Building2,
  ChevronLeft,
  ChevronRight,
  Shield,
  ScrollText,
  Users2,
  FileText,
  Users,
  BarChart3,
  BookOpen,
  Calculator,
  Key,
} from "lucide-react";
import { useState, useEffect } from "react";

import { useRBACStore } from "@/stores/rbac-store";
import { usePermissions } from "@/hooks/use-rbac";

const TourWrapper = dynamic(
  () =>
    import("@/components/onboarding/tour").then((m) => ({ default: m.TourWrapper })),
  { ssr: false },
);

const navItems = [
  // activePrefix: 하이라이트 기준 경로 (href와 다른 경우에 지정)
  { href: "/solutions/new", label: "새 솔루션", icon: Sparkles, activePrefix: "/solutions", dataTour: "new-solution-link" },
  { href: "/projects", label: "프로젝트", icon: FolderKanban, dataTour: "projects-link" },
  { href: "/guide", label: "가이드", icon: BookOpen },
];

const adminItems = [
  { href: "/admin/control-tower", label: "컨트롤 타워", icon: Building2 },
  { href: "/admin/users", label: "사용자 관리", icon: Shield },
  { href: "/admin/contracts", label: "계약 관리", icon: FileText },
  { href: "/admin/pm", label: "PM 관리", icon: Users },
  { href: "/admin/registry/agents", label: "Agent 레지스트리", icon: Bot },
  { href: "/admin/registry/skills", label: "Skill 레지스트리", icon: Puzzle },
  { href: "/admin/registry/mcps", label: "MCP 레지스트리", icon: Blocks },
  { href: "/admin/registry/prototype-catalog", label: "프로토타입 카탈로그", icon: Sparkles },
  { href: "/admin/registry/prototype-tags", label: "프로토타입 태그", icon: Puzzle },
  { href: "/admin/roi-standards", label: "ROI 단가/공수", icon: Calculator },
  { href: "/admin/settings", label: "전역 설정", icon: Blocks },
  { href: "/admin/recommendations", label: "추천 로그", icon: BarChart3 },
  { href: "/admin/audit", label: "감사 로그", icon: ScrollText },
];

const settingsItems = [
  { href: "/settings/members", label: "조직 멤버", icon: Users2 },
  { href: "/settings/anthropic", label: "Anthropic 자격증명", icon: Key },
];

function NavLink({
  href,
  label,
  icon: Icon,
  collapsed,
  isActive,
  dataTour,
}: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  collapsed: boolean;
  isActive: boolean;
  activePrefix?: string;
  dataTour?: string;
}) {
  return (
    <Link
      href={href}
      data-tour={dataTour}
      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
        isActive
          ? "bg-[var(--nav-active-bg)] text-[var(--nav-active-text)] shadow-sm"
          : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
      }`}
      title={collapsed ? label : undefined}
    >
      <Icon
        className={`h-4.5 w-4.5 shrink-0 ${
          isActive ? "text-[var(--nav-active-icon)]" : ""
        }`}
      />
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
  const loaded = useRBACStore((s) => s.loaded);
  const setPermissions = useRBACStore((s) => s.setPermissions);
  const showAdmin = useRBACStore((s) => s.isAdmin());
  const showOrgManage = useRBACStore((s) => s.hasPermission("org:manage"));

  // 스토어에 권한 동기화 (이미 RoleGuard에서도 하지만, 사이드바 렌더링용)
  useEffect(() => {
    if (permsData && !loaded) {
      setPermissions(permsData.permissions, permsData.system_role);
    }
  }, [permsData, loaded, setPermissions]);

  return (
    <div className="flex min-h-screen bg-[var(--bg-base)]">
      {/* 온보딩 투어 (SSR 비활성화, 클라이언트 전용) */}
      <TourWrapper />

      {/* 사이드바 */}
      <aside
        aria-label="메인 네비게이션"
        className={`relative flex flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-surface)] backdrop-blur-sm transition-all duration-300 ${
          collapsed ? "w-[68px]" : "w-64"
        }`}
      >
        {/* 로고 */}
        <div className="flex h-16 items-center gap-2.5 border-b border-[var(--border-subtle)] px-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--logo-bg)]">
            <Sparkles className="h-4 w-4 text-[var(--logo-text)]" />
          </div>
          {!collapsed && (
            <span className="text-sm font-bold tracking-tight text-[var(--text-primary)]">
              ClickEye
            </span>
          )}
        </div>

        {/* 네비게이션 */}
        <nav className="flex-1 overflow-y-auto p-3" data-tour="sidebar-nav">
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
            <div className="mt-6" data-tour="settings-section">
              {!collapsed && (
                <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">
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
                <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">
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
          className="m-3 flex items-center justify-center rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] py-2 text-[var(--text-muted)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-secondary)]"
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
