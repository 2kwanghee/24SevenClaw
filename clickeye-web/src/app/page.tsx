import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  ScanEye,
  ArrowRight,
  Inbox,
  Boxes,
  ShieldCheck,
  Gauge,
  LayoutDashboard,
  CircleDollarSign,
  Workflow,
  Server,
  GitBranch,
} from "lucide-react";

/* -- 딜리버리 보드 시그니처 데이터 (예시) -- */

type StageKey = "intake" | "plan" | "build" | "review" | "merge";
type RoleKey = "architect" | "backend" | "frontend" | "reviewer" | "intake";

const STAGE_ORDER: StageKey[] = ["intake", "plan", "build", "review", "merge"];

interface Chip {
  id: string;
  role: RoleKey;
  gate?: "direct" | "pr";
  token?: string;
}

interface Lane {
  code: string;
  nameKey: "eng1" | "eng2" | "eng3";
  cells: Partial<Record<StageKey, Chip>>;
}

const LANES: Lane[] = [
  {
    code: "ENG-204",
    nameKey: "eng1",
    cells: {
      build: { id: "24S-142", role: "backend", token: "1.2k" },
      review: { id: "24S-139", role: "reviewer", gate: "pr" },
    },
  },
  {
    code: "ENG-198",
    nameKey: "eng2",
    cells: {
      plan: { id: "24S-151", role: "architect" },
      build: { id: "24S-148", role: "frontend", token: "0.9k" },
      merge: { id: "24S-133", role: "backend", gate: "direct" },
    },
  },
  {
    code: "ENG-211",
    nameKey: "eng3",
    cells: {
      intake: { id: "24S-160", role: "intake" },
      plan: { id: "24S-157", role: "backend" },
    },
  },
];

/* -- 페이지 -- */

export default function Home() {
  const t = useTranslations("home");

  const roleLabel = (role: RoleKey) => t(`hero.board.roles.${role}`);
  const roleClass = (role: RoleKey) =>
    role === "reviewer"
      ? "bg-[var(--accent-soft)] text-[var(--accent)]"
      : "bg-[var(--bg-hover)] text-[var(--text-secondary)]";

  const process = [
    { key: "intake", icon: Inbox },
    { key: "delivery", icon: Boxes },
    { key: "governance", icon: ShieldCheck },
    { key: "control", icon: Gauge },
  ] as const;

  const capabilities = [
    { key: "console", icon: LayoutDashboard },
    { key: "governance", icon: ShieldCheck },
    { key: "cost", icon: CircleDollarSign },
    { key: "temporal", icon: Workflow },
    { key: "hybrid", icon: Server },
    { key: "linear", icon: GitBranch },
  ] as const;

  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)]">
      {/* 네비게이션 */}
      <nav className="fixed top-0 z-50 w-full border-b border-[var(--border-subtle)] bg-[var(--bg-header)] backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent)]">
              <ScanEye className="h-4 w-4 text-[var(--accent-fg)]" aria-hidden="true" />
            </div>
            <span className="text-[15px] font-bold tracking-tight text-[var(--text-primary)]">
              ClickEye
            </span>
          </Link>
          <div className="hidden items-center gap-8 md:flex">
            <a
              href="#process"
              className="text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
            >
              {t("nav.process")}
            </a>
            <a
              href="#capabilities"
              className="text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
            >
              {t("nav.capabilities")}
            </a>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
            >
              {t("nav.login")}
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-fg)] transition-opacity hover:opacity-90"
            >
              {t("nav.ctaRegister")}
            </Link>
          </div>
        </div>
      </nav>

      {/* 히어로 */}
      <section className="pt-32 pb-20 sm:pt-36 sm:pb-28">
        <div className="mx-auto max-w-6xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3.5 py-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" aria-hidden="true" />
              <span className="font-mono text-[11px] font-medium tracking-wide text-[var(--text-secondary)]">
                {t("hero.badge")}
              </span>
            </div>

            <h1 className="text-4xl font-bold leading-[1.1] tracking-tight text-[var(--text-primary)] sm:text-5xl lg:text-6xl">
              {t("hero.titleLine1")}
              <br />
              {t("hero.titleLine2")}
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-[var(--text-secondary)] sm:text-lg">
              {t("hero.desc")}
            </p>

            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link
                href="/login"
                className="group flex items-center gap-2 rounded-xl bg-[var(--accent)] px-7 py-3.5 text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90"
              >
                {t("hero.primaryCta")}
                <ArrowRight
                  className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                  aria-hidden="true"
                />
              </Link>
              <Link
                href="/register"
                className="flex items-center gap-2 rounded-xl border border-[var(--border-medium)] px-7 py-3.5 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
              >
                {t("hero.secondaryCta")}
              </Link>
            </div>
          </div>

          {/* 시그니처 — 병렬 딜리버리 보드 */}
          <div className="animate-fade-in-up motion-reduce:animate-none mx-auto mt-16 max-w-5xl overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] shadow-xl shadow-black/[0.04]">
            {/* 콘솔 헤더 */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-3">
              <div className="flex items-center gap-1.5" aria-hidden="true">
                <span className="h-2.5 w-2.5 rounded-full bg-[var(--border-medium)]" />
                <span className="h-2.5 w-2.5 rounded-full bg-[var(--border-medium)]" />
                <span className="h-2.5 w-2.5 rounded-full bg-[var(--border-medium)]" />
              </div>
              <span className="font-mono text-[11px] font-semibold text-[var(--text-secondary)]">
                {t("hero.board.caption")}
              </span>
              <span className="ml-auto inline-flex items-center gap-1.5 font-mono text-[11px] text-[var(--text-muted)]">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
                {t("hero.board.live")}
              </span>
            </div>

            {/* 보드 (가로 스크롤 컨테이너) */}
            <div className="overflow-x-auto">
              <div className="min-w-[720px] p-4">
                {/* 스테이지 헤더 */}
                <div className="grid grid-cols-[132px_repeat(5,minmax(104px,1fr))] items-center gap-2 px-1 pb-3">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                    {t("hero.board.laneLabel")}
                  </span>
                  {STAGE_ORDER.map((stage, i) => (
                    <div key={stage} className="flex items-center gap-1.5">
                      <span className="font-mono text-[10px] text-[var(--text-muted)]">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="text-[11px] font-medium text-[var(--text-secondary)]">
                        {t(`hero.board.stages.${stage}`)}
                      </span>
                    </div>
                  ))}
                </div>

                {/* 스윔레인 */}
                <div className="space-y-2">
                  {LANES.map((lane) => (
                    <div
                      key={lane.code}
                      className="grid grid-cols-[132px_repeat(5,minmax(104px,1fr))] items-stretch gap-2 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2"
                    >
                      {/* 레인 라벨 */}
                      <div className="flex flex-col justify-center gap-0.5 pl-1">
                        <span className="font-mono text-[11px] font-bold text-[var(--accent)]">
                          {lane.code}
                        </span>
                        <span className="truncate text-[11px] text-[var(--text-secondary)]">
                          {t(`hero.board.engagements.${lane.nameKey}`)}
                        </span>
                      </div>

                      {/* 스테이지 셀 */}
                      {STAGE_ORDER.map((stage) => {
                        const chip = lane.cells[stage];
                        if (!chip) {
                          return (
                            <div
                              key={stage}
                              className="flex items-center justify-center"
                              aria-hidden="true"
                            >
                              <span className="h-1 w-1 rounded-full bg-[var(--border-medium)]" />
                            </div>
                          );
                        }
                        return (
                          <div
                            key={stage}
                            className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-1.5"
                          >
                            <div className="flex items-center gap-1">
                              <span
                                className="h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--accent)]"
                                aria-hidden="true"
                              />
                              <span className="font-mono text-[10px] font-semibold text-[var(--text-primary)]">
                                {chip.id}
                              </span>
                            </div>
                            <div className="mt-1 flex flex-wrap items-center gap-1">
                              <span
                                className={`rounded px-1 py-0.5 text-[9px] font-medium ${roleClass(chip.role)}`}
                              >
                                {roleLabel(chip.role)}
                              </span>
                              {chip.gate === "direct" && (
                                <span className="rounded bg-emerald-50 px-1 py-0.5 font-mono text-[9px] font-semibold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                                  direct
                                </span>
                              )}
                              {chip.gate === "pr" && (
                                <span className="rounded bg-amber-50 px-1 py-0.5 font-mono text-[9px] font-semibold text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
                                  PR
                                </span>
                              )}
                              {chip.token && (
                                <span className="font-mono text-[9px] text-[var(--text-muted)]">
                                  {chip.token}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* 보드 푸터 노트 */}
            <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2.5">
              <p className="font-mono text-[10.5px] text-[var(--text-muted)]">
                {t("hero.board.note")}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 딜리버리 흐름 (프로세스 — 실제 순서) */}
      <section id="process" className="border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] py-24 sm:py-28">
        <div className="mx-auto max-w-6xl px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="font-mono text-[11px] uppercase tracking-wider text-[var(--accent)]">
              {t("process.eyebrow")}
            </p>
            <h2 className="mt-3 text-2xl font-bold tracking-tight text-[var(--text-primary)] sm:text-3xl">
              {t("process.sectionTitle")}
            </h2>
            <p className="mt-3 text-[var(--text-secondary)]">{t("process.sectionDescription")}</p>
          </div>

          <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {process.map((item, i) => (
              <div
                key={item.key}
                className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-6"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm font-bold text-[var(--accent)]">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="h-px flex-1 bg-[var(--border-subtle)]" aria-hidden="true" />
                  <item.icon className="h-5 w-5 text-[var(--text-secondary)]" aria-hidden="true" />
                </div>
                <h3 className="mt-4 text-base font-semibold text-[var(--text-primary)]">
                  {t(`process.${item.key}.title`)}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                  {t(`process.${item.key}.desc`)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 플랫폼 역량 */}
      <section id="capabilities" className="border-t border-[var(--border-subtle)] py-24 sm:py-28">
        <div className="mx-auto max-w-6xl px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="font-mono text-[11px] uppercase tracking-wider text-[var(--accent)]">
              {t("capabilities.eyebrow")}
            </p>
            <h2 className="mt-3 text-2xl font-bold tracking-tight text-[var(--text-primary)] sm:text-3xl">
              {t("capabilities.sectionTitle")}
            </h2>
            <p className="mt-3 text-[var(--text-secondary)]">
              {t("capabilities.sectionDescription")}
            </p>
          </div>

          <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {capabilities.map((cap) => (
              <div
                key={cap.key}
                className="group rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 transition-colors hover:border-[var(--border-medium)]"
              >
                <div className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
                  <cap.icon className="h-5 w-5 text-[var(--accent)]" aria-hidden="true" />
                </div>
                <h3 className="mt-4 text-base font-semibold text-[var(--text-primary)]">
                  {t(`capabilities.${cap.key}.title`)}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                  {t(`capabilities.${cap.key}.desc`)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 최종 CTA */}
      <section className="border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] py-24 sm:py-28">
        <div className="mx-auto max-w-6xl px-6 lg:px-8">
          <div className="rounded-3xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-8 py-14 text-center sm:px-12">
            <h2 className="mx-auto max-w-2xl text-2xl font-bold tracking-tight text-[var(--text-primary)] sm:text-4xl">
              {t("finalCta.title")}
            </h2>
            <p className="mx-auto mt-5 max-w-xl text-[var(--text-secondary)]">
              {t("finalCta.description")}
            </p>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link
                href="/login"
                className="group flex items-center gap-2 rounded-xl bg-[var(--accent)] px-7 py-3.5 text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90"
              >
                {t("finalCta.primary")}
                <ArrowRight
                  className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                  aria-hidden="true"
                />
              </Link>
              <Link
                href="/register"
                className="flex items-center gap-2 rounded-xl border border-[var(--border-medium)] px-7 py-3.5 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
              >
                {t("finalCta.secondary")}
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 푸터 */}
      <footer className="border-t border-[var(--border-subtle)] py-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 lg:px-8 md:flex-row">
          <div className="flex items-center gap-2.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-[var(--accent)]">
              <ScanEye className="h-3.5 w-3.5 text-[var(--accent-fg)]" aria-hidden="true" />
            </div>
            <span className="text-sm font-semibold text-[var(--text-primary)]">ClickEye</span>
            <span className="hidden font-mono text-[11px] text-[var(--text-muted)] sm:inline">
              {t("footer.tagline")}
            </span>
          </div>
          <p className="text-sm text-[var(--text-muted)]">{t("footer.copyright")}</p>
        </div>
      </footer>
    </div>
  );
}
