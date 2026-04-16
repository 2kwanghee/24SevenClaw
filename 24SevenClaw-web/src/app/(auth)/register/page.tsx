"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { signIn } from "next-auth/react";
import { apiClient, ApiClientError } from "@/lib/api-client";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  User,
  ArrowRight,
  AlertCircle,
  Github,
  Chrome,
  Check,
} from "lucide-react";

const registerSchema = z
  .object({
    email: z.string().email("올바른 이메일을 입력하세요"),
    displayName: z
      .string()
      .min(1, "이름을 입력하세요")
      .max(100, "이름은 100자 이하로 입력하세요"),
    password: z.string().min(8, "비밀번호는 8자 이상이어야 합니다"),
    confirmPassword: z.string().min(1, "비밀번호 확인을 입력하세요"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "비밀번호가 일치하지 않습니다",
    path: ["confirmPassword"],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

const passwordRequirements = [
  { test: (v: string) => v.length >= 8, label: "8자 이상" },
  { test: (v: string) => /[A-Z]/.test(v), label: "대문자 포함" },
  { test: (v: string) => /[0-9]/.test(v), label: "숫자 포함" },
];

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const passwordValue = watch("password", "");

  async function onSubmit(data: RegisterFormData) {
    setError("");

    try {
      await apiClient.auth.register({
        email: data.email,
        password: data.password,
        display_name: data.displayName,
      });

      router.push("/login?registered=1&callbackUrl=/onboarding/maturity");
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("회원가입 중 오류가 발생했습니다");
      }
    }
  }

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">시작하기</h1>
        <p className="mt-2 text-sm text-slate-400">
          무료 계정을 만들고 AI 에이전트의 힘을 경험하세요
        </p>
      </div>

      {/* 에러 알림 */}
      {error && (
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* 소셜 가입 */}
      <div className="mb-6 grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => signIn("github", { callbackUrl: "/onboarding/maturity" })}
          className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-300 transition-all hover:bg-white/10 hover:text-white"
        >
          <Github className="h-4 w-4" />
          GitHub
        </button>
        <button
          type="button"
          onClick={() => signIn("google", { callbackUrl: "/onboarding/maturity" })}
          className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-300 transition-all hover:bg-white/10 hover:text-white"
        >
          <Chrome className="h-4 w-4" />
          Google
        </button>
      </div>

      {/* 구분선 */}
      <div className="mb-6 flex items-center gap-4">
        <div className="h-px flex-1 bg-white/10" />
        <span className="text-xs text-slate-500">또는 이메일로 가입</span>
        <div className="h-px flex-1 bg-white/10" />
      </div>

      {/* 폼 */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* 이메일 */}
        <div className="space-y-2">
          <label htmlFor="email" className="block text-sm font-medium text-slate-300">
            이메일
          </label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pl-11 pr-4 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-violet-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-violet-500/20"
              placeholder="name@example.com"
              {...register("email")}
            />
          </div>
          {errors.email && (
            <p className="flex items-center gap-1.5 text-xs text-red-400">
              <AlertCircle className="h-3 w-3" />
              {errors.email.message}
            </p>
          )}
        </div>

        {/* 이름 */}
        <div className="space-y-2">
          <label htmlFor="displayName" className="block text-sm font-medium text-slate-300">
            이름
          </label>
          <div className="relative">
            <User className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              id="displayName"
              type="text"
              autoComplete="name"
              className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pl-11 pr-4 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-violet-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-violet-500/20"
              placeholder="표시할 이름"
              {...register("displayName")}
            />
          </div>
          {errors.displayName && (
            <p className="flex items-center gap-1.5 text-xs text-red-400">
              <AlertCircle className="h-3 w-3" />
              {errors.displayName.message}
            </p>
          )}
        </div>

        {/* 비밀번호 */}
        <div className="space-y-2">
          <label htmlFor="password" className="block text-sm font-medium text-slate-300">
            비밀번호
          </label>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pl-11 pr-11 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-violet-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-violet-500/20"
              placeholder="8자 이상의 비밀번호"
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
              tabIndex={-1}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.password && (
            <p className="flex items-center gap-1.5 text-xs text-red-400">
              <AlertCircle className="h-3 w-3" />
              {errors.password.message}
            </p>
          )}

          {/* 비밀번호 강도 표시 */}
          {passwordValue && (
            <div className="flex gap-3 pt-1">
              {passwordRequirements.map((req) => (
                <span
                  key={req.label}
                  className={`flex items-center gap-1 text-xs transition-colors ${
                    req.test(passwordValue) ? "text-emerald-400" : "text-slate-600"
                  }`}
                >
                  <Check className="h-3 w-3" />
                  {req.label}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 비밀번호 확인 */}
        <div className="space-y-2">
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300">
            비밀번호 확인
          </label>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              id="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              autoComplete="new-password"
              className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pl-11 pr-11 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-violet-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-violet-500/20"
              placeholder="비밀번호를 다시 입력하세요"
              {...register("confirmPassword")}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
              tabIndex={-1}
            >
              {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.confirmPassword && (
            <p className="flex items-center gap-1.5 text-xs text-red-400">
              <AlertCircle className="h-3 w-3" />
              {errors.confirmPassword.message}
            </p>
          )}
        </div>

        {/* 약관 동의 */}
        <p className="text-xs leading-relaxed text-slate-500">
          회원가입 시{" "}
          <button type="button" className="text-violet-400 hover:text-violet-300 transition-colors">
            서비스 이용약관
          </button>
          {" "}및{" "}
          <button type="button" className="text-violet-400 hover:text-violet-300 transition-colors">
            개인정보 처리방침
          </button>
          에 동의하는 것으로 간주됩니다.
        </p>

        {/* 가입 버튼 */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-violet-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-600/25 transition-all hover:bg-violet-500 hover:shadow-violet-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="absolute inset-0 bg-gradient-to-r from-violet-600 to-indigo-600 opacity-0 transition-opacity group-hover:opacity-100" />
          <span className="relative">
            {isSubmitting ? "가입 중..." : "계정 만들기"}
          </span>
          {!isSubmitting && (
            <ArrowRight className="relative h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          )}
        </button>
      </form>

      {/* 하단 링크 (모바일) */}
      <p className="mt-8 text-center text-sm text-slate-500 lg:hidden">
        이미 계정이 있으신가요?{" "}
        <Link href="/login" className="font-medium text-violet-400 hover:text-violet-300 transition-colors">
          로그인
        </Link>
      </p>
    </div>
  );
}
