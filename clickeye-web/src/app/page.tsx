import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  Sparkles,
  Layers,
  Shield,
  Monitor,
  ArrowRight,
  Check,
  Terminal,
  Globe,
  Download,
  Zap,
  Bot,
  MousePointerClick,
  Cpu,
  ThumbsUp,
  TrendingUp,
} from "lucide-react";

/* -- 페이지 -- */

export default function Home() {
  const t = useTranslations("home");

  const features = [
    {
      key: "wizard",
      icon: Layers,
      title: t("features.wizard.title"),
      desc: t("features.wizard.desc"),
    },
    {
      key: "catalog",
      icon: Sparkles,
      title: t("features.catalog.title"),
      desc: t("features.catalog.desc"),
    },
    {
      key: "security",
      icon: Shield,
      title: t("features.security.title"),
      desc: t("features.security.desc"),
    },
    {
      key: "platform",
      icon: Monitor,
      title: t("features.platform.title"),
      desc: t("features.platform.desc"),
    },
  ];

  const howItWorks = [
    {
      key: "design",
      step: "01",
      icon: Globe,
      title: t("howItWorks.design.title"),
      desc: t("howItWorks.design.desc"),
    },
    {
      key: "download",
      step: "02",
      icon: Download,
      title: t("howItWorks.download.title"),
      desc: t("howItWorks.download.desc"),
    },
    {
      key: "run",
      step: "03",
      icon: Zap,
      title: t("howItWorks.run.title"),
      desc: t("howItWorks.run.desc"),
    },
  ];

  const platforms = [
    {
      id: "claude-code",
      name: t("platforms.claudeCode.name"),
      desc: t("platforms.claudeCode.desc"),
      icon: Terminal,
      files: [".claude/", "CLAUDE.md", ".claude/settings.json"],
    },
    {
      id: "gemini-cli",
      name: t("platforms.geminiCli.name"),
      desc: t("platforms.geminiCli.desc"),
      icon: Bot,
      files: [".gemini/", "GEMINI.md", ".gemini/settings.json"],
    },
    {
      id: "cursor",
      name: t("platforms.cursor.name"),
      desc: t("platforms.cursor.desc"),
      icon: MousePointerClick,
      files: [".cursor/", ".cursorrules", ".cursor/settings.json"],
    },
    {
      id: "codex",
      name: t("platforms.codex.name"),
      desc: t("platforms.codex.desc"),
      icon: Terminal,
      files: [".codex/", "CODEX.md", ".codex/settings.json"],
    },
  ];

  const customerMetrics = [
    {
      key: "automation",
      icon: Cpu,
      value: "87%",
      label: t("metrics.automation.label"),
      desc: t("metrics.automation.desc"),
    },
    {
      key: "review",
      icon: ThumbsUp,
      value: "92%",
      label: t("metrics.review.label"),
      desc: t("metrics.review.desc"),
    },
    {
      key: "speed",
      icon: TrendingUp,
      value: "3.5x",
      label: t("metrics.speed.label"),
      desc: t("metrics.speed.desc"),
    },
  ];

  const earlyAccessFeatures = [
    t("earlyAccess.features.unlimitedWizard"),
    t("earlyAccess.features.catalog"),
    t("earlyAccess.features.platforms"),
    t("earlyAccess.features.downloads"),
  ];

  const wizardSteps = [
    t("hero.wizardSteps.company"),
    t("hero.wizardSteps.solution"),
    t("hero.wizardSteps.agent"),
    t("hero.wizardSteps.skill"),
    t("hero.wizardSteps.pipeline"),
    t("hero.wizardSteps.platform"),
    t("hero.wizardSteps.preview"),
  ];

  const demoAgents = [
    { name: t("hero.demoAgents.harness"), selected: true, required: true },
    { name: t("hero.demoAgents.backend"), selected: true, required: false },
    { name: t("hero.demoAgents.frontend"), selected: true, required: false },
    { name: t("hero.demoAgents.uiux"), selected: false, required: false },
    { name: t("hero.demoAgents.devops"), selected: false, required: false },
    { name: t("hero.demoAgents.fullstack"), selected: false, required: false },
  ];

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      {/* 네비게이션 */}
      <nav className="fixed top-0 z-50 w-full border-b border-zinc-200/80 bg-white/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="text-[15px] font-bold tracking-tight text-zinc-950">ClickEye</span>
          </Link>
          <div className="hidden items-center gap-8 md:flex">
            <a href="#features" className="text-sm text-zinc-500 transition-colors hover:text-zinc-900">
              {t("nav.features")}
            </a>
            <a href="#how-it-works" className="text-sm text-zinc-500 transition-colors hover:text-zinc-900">
              {t("nav.howItWorks")}
            </a>
            <a href="#platforms" className="text-sm text-zinc-500 transition-colors hover:text-zinc-900">
              {t("nav.platforms")}
            </a>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-900"
            >
              {t("nav.login")}
            </Link>
            <Link
              href="/solutions/new"
              className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-zinc-800"
            >
              {t("nav.ctaStart")}
            </Link>
          </div>
        </div>
      </nav>

      {/* 히어로 섹션 */}
      <section className="bg-white pt-32 pb-24 sm:pb-32">
        <div className="mx-auto max-w-6xl px-6 lg:px-8 text-center">
          {/* 배지 */}
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-zinc-50 px-4 py-1.5">
            <Sparkles className="h-3.5 w-3.5 text-zinc-500" />
            <span className="text-xs font-medium text-zinc-600">{t("hero.badge")}</span>
          </div>

          <h1 className="mx-auto max-w-4xl text-5xl font-bold leading-[1.08] tracking-tight text-zinc-950 md:text-6xl lg:text-7xl">
            {t("hero.titleLine1")}
            <br />
            {t("hero.titleLine2")}
            <br />
            {t("hero.titleLine3")}
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-zinc-500 md:text-xl">
            {t("hero.descLine1")}
            <br className="hidden sm:block" />
            {t("hero.descLine2")}
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/solutions/new"
              className="group flex items-center gap-2 rounded-xl bg-zinc-900 px-8 py-3.5 text-sm font-semibold text-white transition-all hover:bg-zinc-800"
            >
              {t("hero.primaryCta")}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <a
              href="#how-it-works"
              className="flex items-center gap-2 rounded-xl border border-zinc-300 px-8 py-3.5 text-sm font-medium text-zinc-700 transition-all hover:border-zinc-400 hover:bg-zinc-50"
            >
              <Layers className="h-4 w-4" />
              {t("hero.secondaryCta")}
            </a>
          </div>

          {/* 위저드 프리뷰 — 다크 디바이스 프레임 */}
          <div className="mx-auto mt-20 max-w-3xl overflow-hidden rounded-2xl border border-zinc-200 bg-zinc-950 shadow-2xl shadow-zinc-300/40">
            {/* 스텝 바 */}
            <div className="flex items-center gap-1 overflow-x-auto border-b border-white/5 px-4 py-3">
              {wizardSteps.map((step, i) => (
                <div
                  key={step}
                  className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 py-1 text-[11px] font-medium ${
                    i === 2
                      ? "bg-white/10 text-white"
                      : i < 2
                        ? "text-zinc-400"
                        : "text-zinc-600"
                  }`}
                >
                  <span
                    className={`flex h-4 w-4 items-center justify-center rounded-full text-[9px] ${
                      i === 2
                        ? "bg-white text-zinc-900"
                        : i < 2
                          ? "bg-zinc-700 text-zinc-300"
                          : "bg-zinc-800 text-zinc-600"
                    }`}
                  >
                    {i < 2 ? <Check className="h-2.5 w-2.5" /> : i + 1}
                  </span>
                  {step}
                </div>
              ))}
            </div>

            {/* 에이전트 선택 데모 */}
            <div className="p-6 text-left">
              <p className="mb-4 text-sm font-medium text-zinc-300">
                {t("hero.agentSelectPrompt")}
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {demoAgents.map((agent) => (
                  <div
                    key={agent.name}
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs ${
                      agent.selected
                        ? "border-white/20 bg-white/10 text-white"
                        : "border-white/5 bg-white/[0.03] text-zinc-600"
                    }`}
                  >
                    <div
                      className={`flex h-4 w-4 shrink-0 items-center justify-center rounded ${
                        agent.selected ? "bg-white" : "border border-white/10"
                      }`}
                    >
                      {agent.selected && <Check className="h-2.5 w-2.5 text-zinc-900" />}
                    </div>
                    {agent.name}
                    {agent.required && (
                      <span className="ml-auto rounded bg-zinc-700 px-1 py-0.5 text-[9px] text-zinc-400">
                        {t("hero.agentRequired")}
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <p className="mt-3 flex items-center gap-1.5 text-xs text-zinc-400">
                <Sparkles className="h-3 w-3" />
                {t("hero.recommendationNote")}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 기능 섹션 */}
      <section id="features" className="bg-zinc-50 py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight text-zinc-950 md:text-4xl">
              {t("features.sectionTitle")}
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-zinc-500">
              {t("features.sectionDescription")}
            </p>
          </div>

          <div className="mt-16 grid gap-6 md:grid-cols-2">
            {features.map((f) => (
              <div
                key={f.key}
                className="group rounded-2xl border border-zinc-200 bg-white p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all hover:shadow-md"
              >
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-zinc-100">
                  <f.icon className="h-6 w-6 text-zinc-700" />
                </div>
                <h3 className="mt-5 text-xl font-semibold text-zinc-950">{f.title}</h3>
                <p className="mt-3 leading-relaxed text-zinc-500">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 실제 고객 지표 */}
      <section className="bg-white py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-6 lg:px-8">
          <div className="text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-zinc-50 px-4 py-1.5">
              <TrendingUp className="h-3.5 w-3.5 text-zinc-500" />
              <span className="text-xs font-medium text-zinc-600">{t("metrics.badge")}</span>
            </div>
            <h2 className="text-3xl font-bold tracking-tight text-zinc-950 md:text-4xl">
              {t("metrics.sectionTitle")}
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-zinc-500">
              {t("metrics.sectionDescription")}
            </p>
          </div>

          <div className="mt-16 grid gap-6 md:grid-cols-3">
            {customerMetrics.map((m) => (
              <div
                key={m.key}
                className="group rounded-2xl border border-zinc-200 bg-white p-8 text-center shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all hover:shadow-md"
              >
                <div className="mx-auto mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-zinc-100">
                  <m.icon className="h-7 w-7 text-zinc-700" />
                </div>
                <p className="text-4xl font-bold text-zinc-950">{m.value}</p>
                <p className="mt-2 text-sm font-semibold text-zinc-700">{m.label}</p>
                <p className="mt-1 text-sm text-zinc-400">{m.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 작동 방식 */}
      <section id="how-it-works" className="bg-zinc-50 py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight text-zinc-950 md:text-4xl">
              {t("howItWorks.sectionTitle")}
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-zinc-500">
              {t("howItWorks.sectionDescription")}
            </p>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {howItWorks.map((item) => (
              <div
                key={item.key}
                className="relative rounded-2xl border border-zinc-200 bg-white p-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
              >
                <span className="text-7xl font-bold leading-none text-zinc-100">{item.step}</span>
                <div className="mt-4 flex h-10 w-10 items-center justify-center rounded-xl bg-zinc-900">
                  <item.icon className="h-5 w-5 text-white" />
                </div>
                <h3 className="mt-4 text-lg font-semibold text-zinc-950">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-zinc-500">{item.desc}</p>
              </div>
            ))}
          </div>

          {/* 터미널 프리뷰 */}
          <div className="mx-auto mt-12 max-w-2xl overflow-hidden rounded-xl border border-zinc-200 bg-zinc-950 shadow-lg">
            <div className="flex items-center gap-2 border-b border-white/5 px-4 py-2.5">
              <div className="h-2.5 w-2.5 rounded-full bg-red-500/60" />
              <div className="h-2.5 w-2.5 rounded-full bg-yellow-500/60" />
              <div className="h-2.5 w-2.5 rounded-full bg-green-500/60" />
              <span className="ml-3 text-[10px] text-zinc-500">Terminal</span>
            </div>
            <div className="p-5 font-mono text-sm leading-relaxed">
              <p className="text-zinc-500">$ unzip my-saas.zip && cd my-saas</p>
              <p className="mt-1 text-zinc-500">$ claude</p>
              <p className="mt-2 text-emerald-400">{">"} {t("howItWorks.terminal.loadingClaudeMd")}</p>
              <p className="text-zinc-400">{">"} {t("howItWorks.terminal.harnessActivated")}</p>
              <p className="text-cyan-400">{">"} {t("howItWorks.terminal.starting")}</p>
              <span className="mt-1 inline-block h-4 w-2 animate-pulse bg-white/60" />
            </div>
          </div>
        </div>
      </section>

      {/* 지원 플랫폼 */}
      <section id="platforms" className="bg-white py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight text-zinc-950 md:text-4xl">
              {t("platforms.sectionTitle")}
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-zinc-500">
              {t("platforms.sectionDescription")}
            </p>
          </div>

          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {platforms.map((p) => (
              <div
                key={p.id}
                className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all hover:shadow-md"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-zinc-100">
                  <p.icon className="h-5 w-5 text-zinc-700" />
                </div>
                <h3 className="mt-4 text-lg font-semibold text-zinc-950">{p.name}</h3>
                <p className="mt-1 text-sm text-zinc-500">{p.desc}</p>
                <div className="mt-4 space-y-1.5">
                  {p.files.map((file) => (
                    <div key={file} className="flex items-center gap-2">
                      <div className="h-1 w-1 rounded-full bg-zinc-400" />
                      <code className="text-xs text-zinc-500">{file}</code>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 얼리 액세스 */}
      <section id="pricing" className="bg-zinc-50 py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-6 lg:px-8">
          <div className="mx-auto max-w-lg text-center">
            <h2 className="text-3xl font-bold tracking-tight text-zinc-950 md:text-4xl">
              {t("earlyAccess.sectionTitle")}
            </h2>
            <p className="mx-auto mt-4 max-w-md text-zinc-500">
              {t("earlyAccess.sectionDescLine1")}
              <br />
              {t("earlyAccess.sectionDescLine2")}
            </p>

            <div className="mt-10 rounded-2xl border border-zinc-200 bg-white p-8 text-left shadow-lg shadow-zinc-100">
              <div className="mb-6 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-zinc-950">{t("earlyAccess.planName")}</span>
                <span className="rounded-full border border-zinc-200 bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-600">
                  {t("earlyAccess.freeBadge")}
                </span>
              </div>
              <ul className="space-y-3">
                {earlyAccessFeatures.map((f) => (
                  <li key={f} className="flex items-center gap-2.5 text-sm text-zinc-600">
                    <Check className="h-4 w-4 shrink-0 text-zinc-900" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/register"
                className="mt-8 block w-full rounded-xl bg-zinc-900 py-3 text-center text-sm font-semibold text-white transition-all hover:bg-zinc-800"
              >
                {t("earlyAccess.cta")}
              </Link>
              <p className="mt-3 text-center text-xs text-zinc-400">
                {t("earlyAccess.byokNote")}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA — 다크 섹션 */}
      <section className="bg-zinc-950 py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-white md:text-4xl lg:text-5xl">
            {t("finalCta.title")}
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-zinc-400">
            {t("finalCta.description")}
          </p>
          <Link
            href="/solutions/new"
            className="group mt-10 inline-flex items-center gap-2 rounded-full bg-white px-8 py-3.5 text-sm font-semibold text-zinc-900 shadow-lg transition-all hover:bg-zinc-100"
          >
            {t("finalCta.button")}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>
      </section>

      {/* 푸터 */}
      <footer className="border-t border-zinc-200 bg-white py-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 lg:px-8 md:flex-row">
          <div className="flex items-center gap-2.5">
            <Sparkles className="h-4 w-4 text-zinc-500" />
            <span className="text-sm font-semibold text-zinc-950">ClickEye</span>
          </div>
          <p className="text-sm text-zinc-400">{t("footer.copyright")}</p>
        </div>
      </footer>
    </div>
  );
}
