"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Sparkles, Shield, Zap } from "lucide-react";

const features = [
  {
    icon: Bot,
    title: "AI 에이전트 오케스트레이션",
    desc: "Claude 기반 자율 개발 에이전트",
  },
  {
    icon: Shield,
    title: "엔터프라이즈 보안",
    desc: "격리된 실행 환경과 라이센스 관리",
  },
  {
    icon: Zap,
    title: "자동화된 워크플로",
    desc: "티켓에서 PR까지 완전 자동화",
  },
];

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isLogin = pathname === "/login";

  return (
    <div className="flex min-h-screen">
      {/* 좌측 브랜딩 패널 */}
      <div className="relative hidden w-1/2 overflow-hidden lg:block">
        {/* 그라데이션 배경 */}
        <div className="absolute inset-0 bg-gradient-to-br from-violet-950 via-indigo-900 to-slate-900" />

        {/* 메시 그라데이션 오버레이 */}
        <div className="absolute inset-0 opacity-30">
          <div className="absolute -left-20 -top-20 h-96 w-96 rounded-full bg-violet-500 blur-[120px]" />
          <div className="absolute bottom-20 right-10 h-80 w-80 rounded-full bg-indigo-400 blur-[100px]" />
          <div className="absolute left-1/3 top-1/2 h-64 w-64 rounded-full bg-cyan-400 blur-[80px]" />
        </div>

        {/* 그리드 패턴 */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

        {/* 컨텐츠 */}
        <div className="relative z-10 flex h-full flex-col justify-between p-12">
          {/* 로고 */}
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 backdrop-blur-sm">
              <Sparkles className="h-5 w-5 text-violet-300" />
            </div>
            <span className="text-xl font-bold tracking-tight text-white">
              ClickEye
            </span>
          </Link>

          {/* 중앙 히어로 */}
          <div className="space-y-8">
            <div className="space-y-4">
              <h2 className="text-4xl font-bold leading-tight text-white">
                AI가 코드를 작성하는
                <br />
                <span className="bg-gradient-to-r from-violet-300 to-cyan-300 bg-clip-text text-transparent">
                  새로운 개발 경험
                </span>
              </h2>
              <p className="max-w-md text-lg leading-relaxed text-indigo-200/70">
                티켓 할당부터 코드 리뷰, PR 생성까지.
                <br />
                24시간 쉬지 않는 AI 개발 에이전트를 만나보세요.
              </p>
            </div>

            {/* 피쳐 카드 */}
            <div className="space-y-4">
              {features.map((f) => (
                <div
                  key={f.title}
                  className="flex items-start gap-4 rounded-2xl border border-white/5 bg-white/5 p-4 backdrop-blur-sm transition-colors hover:bg-white/10"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10">
                    <f.icon className="h-5 w-5 text-violet-300" />
                  </div>
                  <div>
                    <p className="font-semibold text-white">{f.title}</p>
                    <p className="text-sm text-indigo-200/60">{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 하단 */}
          <p className="text-sm text-indigo-300/40">
            &copy; 2026 ClickEye. All rights reserved.
          </p>
        </div>
      </div>

      {/* 우측 폼 패널 */}
      <div className="relative flex w-full flex-col items-center justify-center bg-slate-950 px-6 py-12 lg:w-1/2">
        {/* 배경 글로우 */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -right-32 -top-32 h-64 w-64 rounded-full bg-violet-500/10 blur-[100px]" />
          <div className="absolute -bottom-32 -left-32 h-64 w-64 rounded-full bg-indigo-500/10 blur-[100px]" />
        </div>

        {/* 모바일 로고 */}
        <div className="relative z-10 mb-8 flex items-center gap-3 lg:hidden">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-500/10">
            <Sparkles className="h-5 w-5 text-violet-400" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">
            ClickEye
          </span>
        </div>

        {/* 폼 컨테이너 */}
        <div className="relative z-10 w-full max-w-[420px]">
          {/* 탭 네비게이션 */}
          <div className="mb-8 flex rounded-2xl bg-white/5 p-1">
            <Link
              href="/login"
              className={`flex-1 rounded-xl py-2.5 text-center text-sm font-medium transition-all ${
                isLogin
                  ? "bg-violet-600 text-white shadow-lg shadow-violet-600/25"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              로그인
            </Link>
            <Link
              href="/register"
              className={`flex-1 rounded-xl py-2.5 text-center text-sm font-medium transition-all ${
                !isLogin
                  ? "bg-violet-600 text-white shadow-lg shadow-violet-600/25"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              회원가입
            </Link>
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}
