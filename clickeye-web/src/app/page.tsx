import Link from "next/link";
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

/* -- 데이터 -- */

const features = [
  {
    icon: Layers,
    title: "7-Step 위저드",
    desc: "회사 정보부터 플랫폼 선택까지, 브라우저에서 7단계로 AI 솔루션을 설계합니다. 코드 한 줄 없이 시작하세요.",
  },
  {
    icon: Sparkles,
    title: "카탈로그 자동 추천",
    desc: "솔루션 유형을 선택하면 에이전트, 스킬, 파이프라인을 자동 추천합니다. 하네스, TDD, AI 리뷰 등 검증된 파이프라인 내장.",
  },
  {
    icon: Shield,
    title: "BYOK 보안 모델",
    desc: "API 키는 ZIP의 .env에만 포함됩니다. 서버에 키를 저장하지 않는 Zero-Trust 설계로 안심하고 사용하세요.",
  },
  {
    icon: Monitor,
    title: "멀티 플랫폼 지원",
    desc: "Claude Code, Gemini CLI, Cursor, Codex. 어떤 AI 코딩 도구를 쓰든 같은 위저드, 같은 품질의 프로젝트를 생성합니다.",
  },
];

const howItWorks = [
  {
    step: "01",
    icon: Globe,
    title: "웹에서 설계",
    desc: "로그인 후 7-Step 위저드로 회사 정보, 솔루션 유형, 에이전트, 스킬, 파이프라인, 플랫폼을 선택합니다. 솔루션 유형에 따라 자동 추천이 적용됩니다.",
  },
  {
    step: "02",
    icon: Download,
    title: "ZIP 다운로드",
    desc: "설정이 완료되면 파일 프리뷰를 확인하고 프로젝트 ZIP을 다운로드합니다. CLAUDE.md, 에이전트 가이드, .env 등 모든 설정이 포함됩니다.",
  },
  {
    step: "03",
    icon: Zap,
    title: "로컬에서 실행",
    desc: "ZIP을 풀고 AI 코딩 도구를 실행하면 끝. claude, gemini, cursor — 어떤 도구든 프로젝트 가이드를 읽고 바로 개발을 시작합니다.",
  },
];

const platforms = [
  {
    id: "claude-code",
    name: "Claude Code",
    desc: "Anthropic 터미널 AI 에이전트",
    icon: Terminal,
    files: [".claude/", "CLAUDE.md", ".claude/settings.json"],
  },
  {
    id: "gemini-cli",
    name: "Gemini CLI",
    desc: "Google 터미널 AI 에이전트",
    icon: Bot,
    files: [".gemini/", "GEMINI.md", ".gemini/settings.json"],
  },
  {
    id: "cursor",
    name: "Cursor",
    desc: "AI 네이티브 IDE",
    icon: MousePointerClick,
    files: [".cursor/", ".cursorrules", ".cursor/settings.json"],
  },
  {
    id: "codex",
    name: "Codex",
    desc: "OpenAI 터미널 AI 에이전트",
    icon: Terminal,
    files: [".codex/", "CODEX.md", ".codex/settings.json"],
  },
];

const customerMetrics = [
  {
    icon: Cpu,
    value: "87%",
    label: "평균 자동화율",
    desc: "서브태스크의 87%가 AI로 자동 처리",
  },
  {
    icon: ThumbsUp,
    value: "92%",
    label: "리뷰 수락율",
    desc: "첫 리뷰에서 수정 없이 통과",
  },
  {
    icon: TrendingUp,
    value: "3.5x",
    label: "개발 속도 향상",
    desc: "수동 대비 평균 3.5배 빠른 처리",
  },
];

const earlyAccessFeatures = [
  "7-Step 위저드 무제한",
  "모든 에이전트 & 스킬 카탈로그",
  "4개 AI 플랫폼 지원",
  "ZIP 다운로드 무제한",
];

/* -- 페이지 -- */

export default function Home() {
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
              기능
            </a>
            <a href="#how-it-works" className="text-sm text-zinc-500 transition-colors hover:text-zinc-900">
              작동 방식
            </a>
            <a href="#platforms" className="text-sm text-zinc-500 transition-colors hover:text-zinc-900">
              지원 플랫폼
            </a>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-900"
            >
              로그인
            </Link>
            <Link
              href="/solutions/new"
              className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-zinc-800"
            >
              솔루션 설계 시작
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
            <span className="text-xs font-medium text-zinc-600">Web-First AI 솔루션 빌더</span>
          </div>

          <h1 className="mx-auto max-w-4xl text-5xl font-bold leading-[1.08] tracking-tight text-zinc-950 md:text-6xl lg:text-7xl">
            직접 설계하고
            <br />
            ZIP 하나로 시작하는
            <br />
            AI 개발
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-zinc-500 md:text-xl">
            브라우저에서 에이전트, 스킬, 파이프라인을 선택하면
            <br className="hidden sm:block" />
            Claude Code / Gemini CLI / Cursor / Codex용 프로젝트가 자동 생성됩니다.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/solutions/new"
              className="group flex items-center gap-2 rounded-xl bg-zinc-900 px-8 py-3.5 text-sm font-semibold text-white transition-all hover:bg-zinc-800"
            >
              솔루션 설계 시작
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <a
              href="#how-it-works"
              className="flex items-center gap-2 rounded-xl border border-zinc-300 px-8 py-3.5 text-sm font-medium text-zinc-700 transition-all hover:border-zinc-400 hover:bg-zinc-50"
            >
              <Layers className="h-4 w-4" />
              작동 방식 보기
            </a>
          </div>

          {/* 위저드 프리뷰 — 다크 디바이스 프레임 */}
          <div className="mx-auto mt-20 max-w-3xl overflow-hidden rounded-2xl border border-zinc-200 bg-zinc-950 shadow-2xl shadow-zinc-300/40">
            {/* 스텝 바 */}
            <div className="flex items-center gap-1 overflow-x-auto border-b border-white/5 px-4 py-3">
              {["회사 정보", "솔루션", "에이전트", "스킬", "파이프라인", "플랫폼", "프리뷰"].map(
                (step, i) => (
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
                ),
              )}
            </div>

            {/* 에이전트 선택 데모 */}
            <div className="p-6 text-left">
              <p className="mb-4 text-sm font-medium text-zinc-300">
                프로젝트에 투입할 AI 에이전트를 선택하세요
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {[
                  { name: "하네스 엔지니어", selected: true, required: true },
                  { name: "시니어 백엔드", selected: true, required: false },
                  { name: "프론트엔드 전문가", selected: true, required: false },
                  { name: "UI/UX 디자이너", selected: false, required: false },
                  { name: "DevOps", selected: false, required: false },
                  { name: "풀스택", selected: false, required: false },
                ].map((agent) => (
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
                        필수
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <p className="mt-3 flex items-center gap-1.5 text-xs text-zinc-400">
                <Sparkles className="h-3 w-3" />
                솔루션 유형 기반 추천이 적용되었습니다
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
              왜 ClickEye인가요?
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-zinc-500">
              웹에서 설계하고, ZIP으로 시작하는 AI 개발 자동화 플랫폼
            </p>
          </div>

          <div className="mt-16 grid gap-6 md:grid-cols-2">
            {features.map((f) => (
              <div
                key={f.title}
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
              <span className="text-xs font-medium text-zinc-600">실제 고객 지표</span>
            </div>
            <h2 className="text-3xl font-bold tracking-tight text-zinc-950 md:text-4xl">
              숫자로 증명합니다
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-zinc-500">
              ClickEye를 사용하는 팀의 실제 개발 성과 지표입니다
            </p>
          </div>

          <div className="mt-16 grid gap-6 md:grid-cols-3">
            {customerMetrics.map((m) => (
              <div
                key={m.label}
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
              어떻게 작동하나요?
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-zinc-500">3단계로 AI 개발 환경을 완성하세요</p>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {howItWorks.map((item) => (
              <div
                key={item.step}
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
              <p className="mt-2 text-emerald-400">{">"} CLAUDE.md를 읽고 있습니다...</p>
              <p className="text-zinc-400">{">"} 하네스 엔지니어링 4단계 파이프라인 활성화</p>
              <p className="text-cyan-400">{">"} 프로젝트 개발을 시작합니다</p>
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
              지원 플랫폼
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-zinc-500">
              어떤 AI 코딩 도구를 사용하시든, ClickEye가 맞춤 설정을 생성합니다
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
              지금은 무료입니다
            </h2>
            <p className="mx-auto mt-4 max-w-md text-zinc-500">
              얼리 액세스 기간 동안 모든 기능을 무료로 사용하세요.
              <br />
              AI 플랫폼 API 키만 준비하면 됩니다.
            </p>

            <div className="mt-10 rounded-2xl border border-zinc-200 bg-white p-8 text-left shadow-lg shadow-zinc-100">
              <div className="mb-6 flex items-baseline gap-2">
                <span className="text-3xl font-bold text-zinc-950">Early Access</span>
                <span className="rounded-full border border-zinc-200 bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-600">
                  무료
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
                무료로 시작하기
              </Link>
              <p className="mt-3 text-center text-xs text-zinc-400">
                BYOK — Bring Your Own Key. 서버에 API 키를 저장하지 않습니다.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA — 다크 섹션 */}
      <section className="bg-zinc-950 py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-white md:text-4xl lg:text-5xl">
            AI 개발, 7단계면 충분합니다
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-zinc-400">
            브라우저에서 설계하고, ZIP으로 시작하세요. API 키는 당신의 로컬에만 있습니다.
          </p>
          <Link
            href="/solutions/new"
            className="group mt-10 inline-flex items-center gap-2 rounded-full bg-white px-8 py-3.5 text-sm font-semibold text-zinc-900 shadow-lg transition-all hover:bg-zinc-100"
          >
            솔루션 설계 시작
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
          <p className="text-sm text-zinc-400">&copy; 2026 ClickEye. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
