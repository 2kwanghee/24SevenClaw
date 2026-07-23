"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { Header } from "@/components/layout/header";
import {
  Sparkles,
  FolderKanban,
  Boxes,
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
  Server,
  KeyRound,
  Database,
  Inbox,
} from "lucide-react";
import { useState, useEffect } from "react";

import { useRBACStore } from "@/stores/rbac-store";
import { usePermissions } from "@/hooks/use-rbac";

const TourWrapper = dynamic(
  () =>
    import("@/components/onboarding/tour").then((m) => ({ default: m.TourWrapper })),
  { ssr: false },
);

type NavItem = {
  href: string;
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
  activePrefix?: string;
  dataTour?: string;
};

const navItems: NavItem[] = [
  { href: "/delivery", labelKey: "items.delivery", icon: Boxes, activePrefix: "/delivery" },
  { href: "/projects", labelKey: "items.projects", icon: FolderKanban, dataTour: "projects-link" },
  { href: "/guide", labelKey: "items.guide", icon: BookOpen },
];

const adminItems: NavItem[] = [
  { href: "/admin/control-tower", labelKey: "admin.controlTower", icon: Building2 },
  { href: "/admin/intake", labelKey: "admin.intake", icon: Inbox },
  { href: "/admin/users", labelKey: "admin.users", icon: Shield },
  { href: "/admin/contracts", labelKey: "admin.contracts", icon: FileText },
  { href: "/admin/pm", labelKey: "admin.pm", icon: Users },
  { href: "/admin/registry/agents", labelKey: "admin.agentsRegistry", icon: Bot },
  { href: "/admin/registry/skills", labelKey: "admin.skillsRegistry", icon: Puzzle },
  { href: "/admin/registry/mcps", labelKey: "admin.mcpsRegistry", icon: Blocks },
  { href: "/admin/registry/prototype-catalog", labelKey: "admin.prototypeCatalog", icon: Sparkles },
  { href: "/admin/registry/prototype-tags", labelKey: "admin.prototypeTags", icon: Puzzle },
  { href: "/admin/roi-standards", labelKey: "admin.roiStandards", icon: Calculator },
  { href: "/admin/settings", labelKey: "admin.globalSettings", icon: Blocks },
  { href: "/admin/recommendations", labelKey: "admin.recommendations", icon: BarChart3 },
  { href: "/admin/audit", labelKey: "admin.audit", icon: ScrollText },
];

// 운영(Ops) 네비: superadmin 전용. 실경계는 백엔드(FEATURE_OPS_PANEL + superadmin)가 강제.
const opsItems: NavItem[] = [
  { href: "/admin/ops/containers", labelKey: "ops.containers", icon: Server },
  { href: "/admin/ops/env", labelKey: "ops.env", icon: KeyRound },
  { href: "/admin/ops/tables", labelKey: "ops.tables", icon: Database },
];

const settingsItems: NavItem[] = [
  { href: "/settings/members", labelKey: "settings.members", icon: Users2 },
  { href: "/settings/anthropic", labelKey: "settings.anthropic", icon: Key },
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
  const t = useTranslations("nav");
  const [collapsed, setCollapsed] = useState(false);

  // 권한 데이터를 로드하여 스토어에 동기화
  const { data: permsData } = usePermissions();
  const loaded = useRBACStore((s) => s.loaded);
  const setPermissions = useRBACStore((s) => s.setPermissions);
  const showAdmin = useRBACStore((s) => s.isAdmin());
  const showOps = useRBACStore((s) => s.isSuperadmin());
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
        aria-label={t("main")}
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
                href={item.href}
                label={t(item.labelKey)}
                icon={item.icon}
                dataTour={item.dataTour}
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
                  {t("sections.settings")}
                </p>
              )}
              <div className="space-y-1">
                {settingsItems.map((item) => (
                  <NavLink
                    key={item.href}
                    href={item.href}
                    label={t(item.labelKey)}
                    icon={item.icon}
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
                  {t("sections.admin")}
                </p>
              )}
              <div className="space-y-1">
                {adminItems.map((item) => (
                  <NavLink
                    key={item.href}
                    href={item.href}
                    label={t(item.labelKey)}
                    icon={item.icon}
                    collapsed={collapsed}
                    isActive={pathname.startsWith(item.href)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* 운영(Ops) 섹션 — superadmin 전용 */}
          {showOps && (
            <div className="mt-6">
              {!collapsed && (
                <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">
                  {t("sections.ops")}
                </p>
              )}
              <div className="space-y-1">
                {opsItems.map((item) => (
                  <NavLink
                    key={item.href}
                    href={item.href}
                    label={t(item.labelKey)}
                    icon={item.icon}
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
          aria-label={collapsed ? t("sidebar.expand") : t("sidebar.collapse")}
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
