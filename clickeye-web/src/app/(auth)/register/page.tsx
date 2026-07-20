"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { signIn } from "next-auth/react";
import { useTranslations } from "next-intl";
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

type RegisterFormData = {
  email: string;
  displayName: string;
  password: string;
  confirmPassword: string;
};

export default function RegisterPage() {
  const router = useRouter();
  const t = useTranslations("auth.register");
  const tV = useTranslations("validation");
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const passwordRequirements = useMemo(
    () => [
      { test: (v: string) => v.length >= 8, label: t("requirements.minLength") },
      { test: (v: string) => /[A-Z]/.test(v), label: t("requirements.hasUpper") },
      { test: (v: string) => /[0-9]/.test(v), label: t("requirements.hasNumber") },
    ],
    [t],
  );

  const registerSchema = useMemo(
    () =>
      z
        .object({
          email: z.string().email(tV("email")),
          displayName: z.string().min(1, tV("name")).max(100, tV("max100")),
          password: z.string().min(8, tV("passwordMin")),
          confirmPassword: z.string().min(1, tV("confirmPassword")),
        })
        .refine((data) => data.password === data.confirmPassword, {
          message: tV("passwordMismatch"),
          path: ["confirmPassword"],
        }),
    [tV],
  );

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
        setError(t("genericError"));
      }
    }
  }

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">{t("title")}</h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">{t("subtitle")}</p>
      </div>

      {/* 에러 알림 */}
      {error && (
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 dark:border-red-800 dark:bg-red-950/40">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-600 dark:text-red-400" />
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* 소셜 가입 */}
      <div className="mb-6 grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => signIn("github", { callbackUrl: "/onboarding/maturity" })}
          className="flex items-center justify-center gap-2 rounded-xl border border-[var(--border-medium)] bg-[var(--bg-surface)] px-4 py-2.5 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
        >
          <Github className="h-4 w-4" />
          GitHub
        </button>
        <button
          type="button"
          onClick={() => signIn("google", { callbackUrl: "/onboarding/maturity" })}
          className="flex items-center justify-center gap-2 rounded-xl border border-[var(--border-medium)] bg-[var(--bg-surface)] px-4 py-2.5 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--bg-hover)]"
        >
          <Chrome className="h-4 w-4" />
          Google
        </button>
      </div>

      {/* 구분선 */}
      <div className="mb-6 flex items-center gap-4">
        <div className="h-px flex-1 bg-[var(--border-subtle)]" />
        <span className="text-xs text-[var(--text-muted)]">{t("orContinueWithEmail")}</span>
        <div className="h-px flex-1 bg-[var(--border-subtle)]" />
      </div>

      {/* 폼 */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* 이메일 */}
        <div className="space-y-2">
          <label htmlFor="email" className="block text-sm font-medium text-[var(--text-primary)]">
            {t("emailLabel")}
          </label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="w-full rounded-xl border border-[var(--border-medium)] bg-[var(--bg-surface)] py-3 pl-11 pr-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-all focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]"
              placeholder="name@example.com"
              {...register("email")}
            />
          </div>
          {errors.email && (
            <p className="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
              <AlertCircle className="h-3 w-3" />
              {errors.email.message}
            </p>
          )}
        </div>

        {/* 이름 */}
        <div className="space-y-2">
          <label htmlFor="displayName" className="block text-sm font-medium text-[var(--text-primary)]">
            {t("nameLabel")}
          </label>
          <div className="relative">
            <User className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              id="displayName"
              type="text"
              autoComplete="name"
              className="w-full rounded-xl border border-[var(--border-medium)] bg-[var(--bg-surface)] py-3 pl-11 pr-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-all focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]"
              placeholder={t("namePlaceholder")}
              {...register("displayName")}
            />
          </div>
          {errors.displayName && (
            <p className="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
              <AlertCircle className="h-3 w-3" />
              {errors.displayName.message}
            </p>
          )}
        </div>

        {/* 비밀번호 */}
        <div className="space-y-2">
          <label htmlFor="password" className="block text-sm font-medium text-[var(--text-primary)]">
            {t("passwordLabel")}
          </label>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              className="w-full rounded-xl border border-[var(--border-medium)] bg-[var(--bg-surface)] py-3 pl-11 pr-11 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-all focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]"
              placeholder={t("passwordPlaceholder")}
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)]"
              tabIndex={-1}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.password && (
            <p className="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
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
                    req.test(passwordValue)
                      ? "text-emerald-600 dark:text-emerald-400"
                      : "text-[var(--text-muted)]"
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
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-[var(--text-primary)]">
            {t("confirmPasswordLabel")}
          </label>
          <div className="relative">
            <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              id="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              autoComplete="new-password"
              className="w-full rounded-xl border border-[var(--border-medium)] bg-[var(--bg-surface)] py-3 pl-11 pr-11 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-all focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]"
              placeholder={t("confirmPasswordPlaceholder")}
              {...register("confirmPassword")}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)]"
              tabIndex={-1}
            >
              {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.confirmPassword && (
            <p className="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
              <AlertCircle className="h-3 w-3" />
              {errors.confirmPassword.message}
            </p>
          )}
        </div>

        {/* 약관 동의 */}
        <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
          {t("termsPrefix")}{" "}
          <button
            type="button"
            className="underline text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
          >
            {t("termsLink")}
          </button>
          {" "}
          {t("termsConjunction")}{" "}
          <button
            type="button"
            className="underline text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
          >
            {t("privacyLink")}
          </button>
          {t("termsSuffix")}
        </p>

        {/* 가입 버튼 */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="group flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-3 text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? t("submitting") : t("submit")}
          {!isSubmitting && (
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          )}
        </button>
      </form>

      {/* 하단 링크 (모바일) */}
      <p className="mt-8 text-center text-sm text-[var(--text-secondary)] lg:hidden">
        {t("hasAccountPrompt")}{" "}
        <Link
          href="/login"
          className="font-medium text-[var(--accent)] transition-colors hover:underline"
        >
          {t("loginLink")}
        </Link>
      </p>
    </div>
  );
}
