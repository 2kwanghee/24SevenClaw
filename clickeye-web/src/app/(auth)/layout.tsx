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
      <div className="relative hidden w-1/2 overflow-hidden border-r border-zinc-200 bg-zinc-50 lg:flex lg:flex-col lg:justify-between lg:p-12">
          {/* 로고 */}
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-zinc-900">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight text-zinc-950">
              ClickEye
            </span>
          </Link>

          {/* 중앙 히어로 */}
          <div className="space-y-8">
            <div className="space-y-4">
              <h2 className="text-4xl font-bold leading-tight tracking-tight text-zinc-950">
                AI가 코드를 작성하는
                <br />
                새로운 개발 경험
              </h2>
              <p className="max-w-md text-lg leading-relaxed text-zinc-500">
                티켓 할당부터 코드 리뷰, PR 생성까지.
                <br />
                24시간 쉬지 않는 AI 개발 에이전트를 만나보세요.
              </p>
            </div>

            {/* 피쳐 카드 */}
            <div className="space-y-3">
              {features.map((f) => (
                <div
                  key={f.title}
                  className="flex items-start gap-4 rounded-2xl border border-zinc-200 bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-colors hover:bg-zinc-50"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-zinc-100">
                    <f.icon className="h-5 w-5 text-zinc-700" />
                  </div>
                  <div>
                    <p className="font-semibold text-zinc-950">{f.title}</p>
                    <p className="text-sm text-zinc-500">{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 하단 */}
          <p className="text-sm text-zinc-400">
            &copy; 2026 ClickEye. All rights reserved.
          </p>
      </div>

      {/* 우측 폼 패널 */}
      <div className="relative flex w-full flex-col items-center justify-center bg-white px-6 py-12 lg:w-1/2">
        {/* 모바일 로고 */}
        <div className="mb-8 flex items-center gap-3 lg:hidden">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-zinc-900">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight text-zinc-950">
            ClickEye
          </span>
        </div>

        {/* 폼 컨테이너 */}
        <div className="w-full max-w-[420px]">
          {/* 탭 네비게이션 */}
          <div className="mb-8 flex rounded-2xl border border-zinc-200 bg-zinc-50 p-1">
            <Link
              href="/login"
              className={`flex-1 rounded-xl py-2.5 text-center text-sm font-medium transition-all ${
                isLogin
                  ? "bg-zinc-900 text-white shadow-sm"
                  : "text-zinc-500 hover:text-zinc-900"
              }`}
            >
              로그인
            </Link>
            <Link
              href="/register"
              className={`flex-1 rounded-xl py-2.5 text-center text-sm font-medium transition-all ${
                !isLogin
                  ? "bg-zinc-900 text-white shadow-sm"
                  : "text-zinc-500 hover:text-zinc-900"
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
