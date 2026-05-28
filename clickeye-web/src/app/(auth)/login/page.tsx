"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { signIn } from "next-auth/react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Github,
  Chrome,
} from "lucide-react";

type LoginFormData = {
  email: string;
  password: string;
};

function LoginPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tV = useTranslations("validation");
  const callbackUrl = searchParams.get("callbackUrl") ?? "/projects";
  const registered = searchParams.get("registered");
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const loginSchema = useMemo(
    () =>
      z.object({
        email: z.string().email(tV("email")),
        password: z.string().min(1, tV("password")),
      }),
    [tV],
  );

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  async function onSubmit(data: LoginFormData) {
    setError("");

    const result = await signIn("credentials", {
      email: data.email,
      password: data.password,
      redirect: false,
    });

    if (result?.error) {
      setError("이메일 또는 비밀번호가 올바르지 않습니다");
      return;
    }

    router.push(callbackUrl);
    router.refresh();
  }

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-zinc-950">다시 오신 것을 환영해요</h1>
        <p className="mt-2 text-sm text-zinc-500">
          계정에 로그인하여 AI 에이전트를 관리하세요
        </p>
      </div>

      {/* 성공 알림 */}
      {registered && (
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          <p className="text-sm text-emerald-700">
            회원가입이 완료되었습니다. 로그인해주세요.
          </p>
        </div>
      )}

      {/* 에러 알림 */}
      {error && (
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* 소셜 로그인 */}
      <div className="mb-6 grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => signIn("github", { callbackUrl })}
          className="flex items-center justify-center gap-2 rounded-xl border border-zinc-300 bg-white px-4 py-2.5 text-sm font-medium text-zinc-700 transition-all hover:bg-zinc-50 hover:border-zinc-400"
        >
          <Github className="h-4 w-4" />
          GitHub
        </button>
        <button
          type="button"
          onClick={() => signIn("google", { callbackUrl })}
          className="flex items-center justify-center gap-2 rounded-xl border border-zinc-300 bg-white px-4 py-2.5 text-sm font-medium text-zinc-700 transition-all hover:bg-zinc-50 hover:border-zinc-400"
        >
          <Chrome className="h-4 w-4" />
          Google
        </button>
      </div>

      {/* 구분선 */}
      <div className="mb-6 flex items-center gap-4">
        <div className="h-px flex-1 bg-zinc-200" />
        <span className="text-xs text-zinc-400">또는 이메일로 계속</span>
        <div className="h-px flex-1 bg-zinc-200" />
      </div>

      {/* 폼 */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* 이메일 */}
        <div className="space-y-2">
          <label htmlFor="email" className="block text-sm font-medium text-zinc-700">
            이메일
          </label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="w-full rounded-xl border border-zinc-300 bg-white py-3 pl-11 pr-4 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200"
              placeholder="name@example.com"
              {...register("email")}
            />
          </div>
          {errors.email && (
            <p className="flex items-center gap-1.5 text-xs text-red-600">
              <AlertCircle className="h-3 w-3" />
              {errors.email.message}
            </p>
          )}
        </div>

        {/* 비밀번호 */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label htmlFor="password" className="block text-sm font-medium text-zinc-700">
              비밀번호
            </label>
            <button type="button" className="text-xs text-zinc-500 hover:text-zinc-900 transition-colors">
              비밀번호 찾기
            </button>
          </div>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              className="w-full rounded-xl border border-zinc-300 bg-white py-3 pl-11 pr-11 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all focus:border-zinc-500 focus:ring-2 focus:ring-zinc-200"
              placeholder="비밀번호를 입력하세요"
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700 transition-colors"
              tabIndex={-1}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.password && (
            <p className="flex items-center gap-1.5 text-xs text-red-600">
              <AlertCircle className="h-3 w-3" />
              {errors.password.message}
            </p>
          )}
        </div>

        {/* 로그인 버튼 */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-zinc-900 px-4 py-3 text-sm font-semibold text-white transition-all hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "로그인 중..." : "로그인"}
          {!isSubmitting && (
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          )}
        </button>
      </form>

      {/* 하단 링크 (모바일) */}
      <p className="mt-8 text-center text-sm text-zinc-500 lg:hidden">
        계정이 없으신가요?{" "}
        <Link href="/register" className="font-medium text-zinc-900 hover:underline transition-colors">
          회원가입
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900" />
        </div>
      }
    >
      <LoginPageInner />
    </Suspense>
  );
}
