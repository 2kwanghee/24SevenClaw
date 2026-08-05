"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { Header } from "@/components/layout/header";
import {
  ScanEye,
  Sparkles,
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
  LayoutDashboard,
  Coins,
  ListOrdered,
  Activity,
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

// 딜리버리가 단일 진입점이다(I-14). `프로젝트`를 1뎁스에서 제거했다 —
// `/delivery` 목록과 `/projects` 목록이 같은 엔티티를 같은 훅(useProjects)으로
// 중복 노출하고 있었다(engagementId === projectId). 라우트와 페이지는 유지하므로
// 기존 URL·북마크·딜리버리 콘솔의 하위 탭 링크는 그대로 동작한다.
const navItems: NavItem[] = [
  { href: "/dashboard", labelKey: "items.dashboard", icon: LayoutDashboard },
  { href: "/delivery", labelKey: "items.delivery", icon: Boxes, activePrefix: "/delivery", dataTour: "projects-link" },
  { href: "/guide", labelKey: "items.guide", icon: BookOpen },
];

// 관측(CE-388 관측 API 소비) — 백엔드 require_permission("settings:manage") 와 동일한
// 권한으로 게이팅한다(admin+superadmin 둘 다 보유, showOps 는 superadmin 전용이라 부적합).
const observabilityItems: NavItem[] = [
  { href: "/observability/seats", labelKey: "observability.seats", icon: Coins },
  { href: "/observability/usage", labelKey: "observability.usage", icon: ListOrdered },
  { href: "/observability/runs", labelKey: "observability.runs", icon: Activity },
];

// 딜리버리 체인이 실제로 쓰는 관리 화면만 남긴다.
//   · intake — 수신된 수주를 검토·승인한다(체인 1단계의 사람 개입 지점)
//   · users  — 계정·권한 관리(실운영 필수)
const adminItems: NavItem[] = [
  { href: "/admin/intake", labelKey: "admin.intake", icon: Inbox },
  { href: "/admin/users", labelKey: "admin.users", icon: Shield },
];

// ── 네비에서 숨긴 관리 메뉴 (2026-08-04) ─────────────────────────────────────
// **라우트·페이지·API·데이터는 모두 살아 있다.** 아래 URL 로 직접 접근하면 그대로 열린다.
// 되살리려면 해당 항목을 adminItems 로 옮기면 된다(labelKey·i18n 문구도 그대로 남겨 두었다).
//
// 왜 숨겼나 — 딜리버리 체인이 이 화면들의 데이터를 **전혀 참조하지 않는다**(실측으로 3지점 확인):
//   · 실행면(scripts/) — 레지스트리·PM·ROI API 호출 0건. 워크스페이스 조달은
//     templates/harness-core(Tier 0)만 복사하고 카탈로그를 승계하지 않으며, 스택·게이트는
//     stack_profiler.py 가 저장소에서 자동 도출한다(사람이 피커에서 고르지 않는다)
//   · 수주→수락(intake_service.py) — PM·ROI·레지스트리 참조 0건(Project 만 생성)
//   · 딜리버리 콘솔 페이지 — 해당 훅 참조 0건
// 즉 위저드/솔루션빌더 시절의 "프로젝트마다 콘솔에서 에이전트·스킬을 조합한다" 전제가
// 파생형 하네스로 대체된 뒤 남은 화면들이다. 데이터는 구성 자산(pm_compositions 173 ·
// skills 24 · agents 17 · prototype_catalog 15)이 실제 딜리버리 데이터(projects 5 ·
// intake_requests 3)의 수십 배로 쌓여 있어, 메뉴에 남겨 두면 운영자가 볼 곳을 흐린다.
//
// 삭제하지 않는 이유: 되돌리기가 비싸고 PM 구성 매칭(CE-273)처럼 마이그레이션까지 들어간
// 자산이 섞여 있다. 폐기 판단은 별도 티켓에서 데이터 이관·아카이브와 함께 다룬다.
// 2026-08-05 추가로 숨긴 5개 — 사용자가 화면에서 "쓰이는 기능인지 불명확하다" 고 지목했고
// 확인 결과 딜리버리 체인과 무관했다:
//   · /admin/settings  — 페이지 본문에 "**위저드 동작에** 영향을 주는 전역 설정" 이라고
//     적혀 있다. 위저드 잔재 확정
//   · /admin/roi-standards — 위 주석의 실측대로 체인 참조 0건(수주→수락·실행면·콘솔 전부)
//   · /admin/control-tower · /admin/contracts · /admin/audit — 체인 8단계
//     (수신→승인→분해→구현→검증→알림→모니터링)의 어느 지점도 이 화면들을 읽지 않는다
// 라우트·API·데이터는 그대로 살아 있다. URL 직접 접근 가능하고, 되살리려면 adminItems 로 옮긴다.
const hiddenAdminItems: NavItem[] = [
  { href: "/admin/control-tower", labelKey: "admin.controlTower", icon: Building2 },
  { href: "/admin/contracts", labelKey: "admin.contracts", icon: FileText },
  { href: "/admin/roi-standards", labelKey: "admin.roiStandards", icon: Calculator },
  { href: "/admin/settings", labelKey: "admin.globalSettings", icon: Blocks },
  { href: "/admin/audit", labelKey: "admin.audit", icon: ScrollText },
  { href: "/admin/pm", labelKey: "admin.pm", icon: Users },
  { href: "/admin/registry/agents", labelKey: "admin.agentsRegistry", icon: Bot },
  { href: "/admin/registry/skills", labelKey: "admin.skillsRegistry", icon: Puzzle },
  { href: "/admin/registry/mcps", labelKey: "admin.mcpsRegistry", icon: Blocks },
  { href: "/admin/registry/prototype-catalog", labelKey: "admin.prototypeCatalog", icon: Sparkles },
  { href: "/admin/registry/prototype-tags", labelKey: "admin.prototypeTags", icon: Puzzle },
  { href: "/admin/recommendations", labelKey: "admin.recommendations", icon: BarChart3 },
];
void hiddenAdminItems; // 렌더하지 않는다 — 위 주석의 복원 목록으로만 존재한다

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
  const showObservability = useRBACStore((s) => s.hasPermission("settings:manage"));

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
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[var(--accent)]">
            <ScanEye className="h-4 w-4 text-[var(--accent-fg)]" aria-hidden="true" />
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

          {/* 관측 섹션 — 대시보드 홈은 top-level navItems, 나머지 3화면은 여기 */}
          {showObservability && (
            <div className="mt-6">
              {!collapsed && (
                <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">
                  {t("sections.observability")}
                </p>
              )}
              <div className="space-y-1">
                {observabilityItems.map((item) => (
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
