"use client";

import {
  FolderKanban,
  AlertCircle,
  User,
  Users,
  Building2,
  Building,
  Monitor,
  Landmark,
  ShoppingCart,
  HeartPulse,
  GraduationCap,
  MoreHorizontal,
  X,
} from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { useEffect } from "react";

import { useWizardStore } from "@/stores/wizard-store";
import type { CompanySize, Industry } from "@/types/wizard";

/* ── 상수 ── */

const COMPANY_SIZE_OPTIONS: {
  value: CompanySize;
  label: string;
  description: string;
  icon: typeof User;
}[] = [
  { value: "solo", label: "1인", description: "개인 개발자", icon: User },
  {
    value: "small",
    label: "소규모",
    description: "2~10명",
    icon: Users,
  },
  {
    value: "medium",
    label: "중소기업",
    description: "11~100명",
    icon: Building2,
  },
  {
    value: "enterprise",
    label: "대기업",
    description: "100명 이상",
    icon: Building,
  },
];

const INDUSTRY_OPTIONS: {
  value: Industry;
  label: string;
  icon: typeof Monitor;
}[] = [
  { value: "it", label: "IT / 소프트웨어", icon: Monitor },
  { value: "finance", label: "금융", icon: Landmark },
  { value: "commerce", label: "커머스", icon: ShoppingCart },
  { value: "healthcare", label: "헬스케어", icon: HeartPulse },
  { value: "education", label: "교육", icon: GraduationCap },
  { value: "other", label: "기타", icon: MoreHorizontal },
];

const TECH_STACK_OPTIONS = [
  "React",
  "Next.js",
  "Vue",
  "Angular",
  "TypeScript",
  "Python",
  "FastAPI",
  "Django",
  "Java",
  "Spring",
  "Go",
  "Node.js",
  "PostgreSQL",
  "MySQL",
  "MongoDB",
  "Redis",
  "Docker",
  "Kubernetes",
  "AWS",
  "GCP",
  "Azure",
  "Terraform",
] as const;

/* ── Zod 스키마 ── */

const schema = z.object({
  companyName: z
    .string()
    .min(1, "회사 이름을 입력하세요")
    .max(200, "200자 이내로 입력하세요"),
  companySize: z.enum(["solo", "small", "medium", "enterprise"], {
    message: "회사 규모를 선택하세요",
  }),
  industry: z.enum(
    ["it", "finance", "commerce", "healthcare", "education", "other"],
    { message: "업종을 선택하세요" },
  ),
  techStack: z.array(z.string()),
});

type FormData = z.infer<typeof schema>;

/* ── 컴포넌트 ── */

export function StepOrganization() {
  const organization = useWizardStore((s) => s.data.organization);
  const setOrganization = useWizardStore((s) => s.setOrganization);

  const {
    register,
    control,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      companyName: organization.companyName,
      companySize: organization.companySize ?? undefined,
      industry: organization.industry ?? undefined,
      techStack: organization.techStack,
    },
  });

  // 입력 값이 변경될 때 스토어에 자동 저장
  const watchedValues = watch();
  useEffect(() => {
    setOrganization({
      companyName: watchedValues.companyName,
      companySize: watchedValues.companySize ?? null,
      industry: watchedValues.industry ?? null,
      techStack: watchedValues.techStack ?? [],
    });
  }, [
    watchedValues.companyName,
    watchedValues.companySize,
    watchedValues.industry,
    watchedValues.techStack,
    setOrganization,
  ]);

  return (
    <div className="space-y-6">
      {/* 회사 이름 */}
      <div className="space-y-2">
        <label
          htmlFor="org-name"
          className="block text-sm font-medium text-slate-300"
        >
          회사 이름 <span className="text-red-400">*</span>
        </label>
        <div className="relative">
          <FolderKanban className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            id="org-name"
            type="text"
            {...register("companyName")}
            className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pl-11 pr-4 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-violet-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-violet-500/20"
            placeholder="예: 우리 회사"
          />
        </div>
        {errors.companyName && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {errors.companyName.message}
          </p>
        )}
      </div>

      {/* 회사 규모 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-300">
          회사 규모 <span className="text-red-400">*</span>
        </label>
        <Controller
          name="companySize"
          control={control}
          render={({ field }) => (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {COMPANY_SIZE_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                const selected = field.value === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => field.onChange(opt.value)}
                    aria-pressed={selected}
                    className={`flex flex-col items-center gap-1.5 rounded-xl border px-3 py-4 text-center transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${
                      selected
                        ? "border-violet-500/50 bg-violet-500/10 shadow-lg shadow-violet-500/10 ring-2 ring-violet-500/20"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]"
                    }`}
                  >
                    <Icon
                      className={`h-5 w-5 ${selected ? "text-violet-400" : "text-slate-400"}`}
                    />
                    <span
                      className={`text-sm font-medium ${selected ? "text-white" : "text-slate-300"}`}
                    >
                      {opt.label}
                    </span>
                    <span className="text-xs text-slate-500">
                      {opt.description}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        />
        {errors.companySize && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {errors.companySize.message}
          </p>
        )}
      </div>

      {/* 업종 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-300">
          업종 <span className="text-red-400">*</span>
        </label>
        <Controller
          name="industry"
          control={control}
          render={({ field }) => (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {INDUSTRY_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                const selected = field.value === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => field.onChange(opt.value)}
                    aria-pressed={selected}
                    className={`flex items-center gap-2.5 rounded-xl border px-4 py-3 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${
                      selected
                        ? "border-violet-500/50 bg-violet-500/10 shadow-lg shadow-violet-500/10 ring-2 ring-violet-500/20"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]"
                    }`}
                  >
                    <Icon
                      className={`h-4 w-4 shrink-0 ${selected ? "text-violet-400" : "text-slate-400"}`}
                    />
                    <span
                      className={`text-sm font-medium ${selected ? "text-white" : "text-slate-300"}`}
                    >
                      {opt.label}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        />
        {errors.industry && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {errors.industry.message}
          </p>
        )}
      </div>

      {/* 기존 기술 스택 (선택사항) */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-300">
          기존 기술 스택{" "}
          <span className="text-xs font-normal text-slate-500">(선택)</span>
        </label>
        <Controller
          name="techStack"
          control={control}
          render={({ field }) => (
            <div className="space-y-3">
              {/* 선택된 태그 */}
              {field.value.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {field.value.map((tech) => (
                    <span
                      key={tech}
                      className="inline-flex items-center gap-1 rounded-lg border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-xs font-medium text-violet-300"
                    >
                      {tech}
                      <button
                        type="button"
                        onClick={() =>
                          field.onChange(field.value.filter((t) => t !== tech))
                        }
                        aria-label={`${tech} 제거`}
                        className="rounded-sm p-0.5 transition-colors hover:bg-violet-500/20"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {/* 선택 가능한 태그 */}
              <div className="flex flex-wrap gap-2">
                {TECH_STACK_OPTIONS.filter(
                  (tech) => !field.value.includes(tech),
                ).map((tech) => (
                  <button
                    key={tech}
                    type="button"
                    onClick={() => field.onChange([...field.value, tech])}
                    className="rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-400 transition-all hover:border-white/20 hover:bg-white/[0.07] hover:text-slate-300"
                  >
                    {tech}
                  </button>
                ))}
              </div>
            </div>
          )}
        />
      </div>
    </div>
  );
}
