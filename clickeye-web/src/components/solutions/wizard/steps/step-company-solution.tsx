"use client";

import {
  Building2,
  Store,
  Network,
  Laptop,
  AlertCircle,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { useEffect } from "react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import type { BusinessType, CompanySize, IndustryType } from "@/types/solution-wizard";

/* -- 상수 -- */

const BUSINESS_TYPE_OPTIONS: {
  value: BusinessType;
  label: string;
  description: string;
  icon: typeof Building2;
}[] = [
  { value: "b2b", label: "B2B", description: "기업 대상", icon: Building2 },
  { value: "b2c", label: "B2C", description: "소비자 대상", icon: Store },
  { value: "b2b2c", label: "B2B2C", description: "복합 모델", icon: Network },
  { value: "internal", label: "내부 도구", description: "사내 시스템", icon: Laptop },
];

const COMPANY_SIZE_OPTIONS: { value: CompanySize; label: string; sub: string }[] = [
  { value: "startup", label: "스타트업", sub: "1–10명" },
  { value: "small", label: "소기업", sub: "11–50명" },
  { value: "medium", label: "중소기업", sub: "51–200명" },
  { value: "mid-large", label: "중견기업", sub: "201–1,000명" },
  { value: "enterprise", label: "대기업", sub: "1,000명+" },
];

const INDUSTRY_OPTIONS: { value: IndustryType; label: string }[] = [
  { value: "it", label: "IT/소프트웨어" },
  { value: "fintech", label: "금융/핀테크" },
  { value: "ecommerce", label: "이커머스/리테일" },
  { value: "healthcare", label: "헬스케어/의료" },
  { value: "education", label: "교육/에듀테크" },
  { value: "manufacturing", label: "제조업" },
  { value: "logistics", label: "물류/배송" },
  { value: "marketing", label: "마케팅/광고" },
  { value: "game", label: "게임/엔터테인먼트" },
  { value: "other", label: "기타" },
];

const TECH_STACK_CATEGORIES: {
  label: string;
  key: string;
  options: string[];
}[] = [
  {
    key: "language",
    label: "언어",
    options: ["Python", "TypeScript", "JavaScript", "Java", "Kotlin", "Go", "Rust", "C#"],
  },
  {
    key: "framework",
    label: "프레임워크 / 라이브러리",
    options: [
      "React", "Next.js", "Vue", "Angular",
      "FastAPI", "Django", "Spring Boot",
      "Node.js", "NestJS", "Express",
      "Flutter",
    ],
  },
  {
    key: "database",
    label: "데이터베이스",
    options: ["PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Elasticsearch", "DynamoDB"],
  },
  {
    key: "cloud",
    label: "클라우드 / 인프라",
    options: ["AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform"],
  },
];

/* -- Zod 스키마 -- */

const schema = z.object({
  companyName: z
    .string()
    .min(1, "회사 이름을 입력하세요")
    .max(200, "200자 이내로 입력하세요"),
  companySize: z.enum(
    ["startup", "small", "medium", "mid-large", "enterprise"],
    { message: "회사 규모를 선택하세요" },
  ),
  industry: z.enum(
    [
      "it",
      "fintech",
      "ecommerce",
      "healthcare",
      "education",
      "manufacturing",
      "logistics",
      "marketing",
      "game",
      "other",
    ],
    { message: "업종을 선택하세요" },
  ),
  techStack: z.array(z.string()),
  mainProduct: z
    .string()
    .min(1, "주력 제품/서비스를 입력하세요")
    .max(500, "500자 이내로 입력하세요"),
  businessType: z.enum(["b2b", "b2c", "b2b2c", "internal"], {
    message: "비즈니스 유형을 선택하세요",
  }),
  companyDescription: z
    .string()
    .max(1000, "1000자 이내로 입력하세요")
    .optional(),
  solutionRequest: z
    .string()
    .min(50, "솔루션 요구사항을 50자 이상 입력하세요")
    .max(2000, "2000자 이내로 입력하세요"),
});

type FormData = z.infer<typeof schema>;

/* -- 컴포넌트 -- */

export function StepCompanySolution() {
  // defaultValues 초기화에만 필요 — reactive 구독 없이 1회 읽기
  const initialCompany = useSolutionWizardStore.getState().data.company;
  const setCompany = useSolutionWizardStore((s) => s.setCompany);
  const setStep0Valid = useSolutionWizardStore((s) => s.setStep0Valid);

  const {
    register,
    control,
    watch,
    formState: { errors, isValid },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    mode: "onChange",
    defaultValues: {
      companyName: initialCompany.companyName,
      companySize: initialCompany.companySize ?? undefined,
      industry: initialCompany.industry ?? undefined,
      techStack: initialCompany.techStack,
      mainProduct: initialCompany.mainProduct,
      businessType: initialCompany.businessType ?? undefined,
      companyDescription: initialCompany.companyDescription,
      solutionRequest: initialCompany.solutionRequest,
    },
  });

  // ① 폼 유효성(boolean) → 스토어 동기화 — 다음 버튼 활성화에 사용
  useEffect(() => {
    setStep0Valid(isValid);
  }, [isValid, setStep0Valid]);

  // ② 필드값 → 스토어 동기화 — handleStep1Next의 data.company 읽기에 사용
  //    JSON.stringify로 직렬화하여 배열 참조 변경 문제 회피
  const values = watch();
  const valuesJson = JSON.stringify(values);

  useEffect(() => {
    const v = JSON.parse(valuesJson) as FormData;
    setCompany({
      companyName: v.companyName ?? "",
      companySize: v.companySize ?? null,
      industry: v.industry ?? null,
      techStack: v.techStack ?? [],
      mainProduct: v.mainProduct ?? "",
      businessType: v.businessType ?? null,
      companyDescription: v.companyDescription ?? "",
      solutionRequest: v.solutionRequest ?? "",
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valuesJson, setCompany]);

  const solutionRequest = watch("solutionRequest");

  return (
    <div className="space-y-6">
      {/* 회사 이름 */}
      <div className="space-y-2">
        <label
          htmlFor="company-name"
          className="block text-sm font-medium text-slate-300"
        >
          회사 이름 <span className="text-red-400">*</span>
        </label>
        <input
          id="company-name"
          type="text"
          {...register("companyName")}
          className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-emerald-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-emerald-500/20"
          placeholder="예: 우리 회사"
        />
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
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 lg:grid-cols-5">
              {COMPANY_SIZE_OPTIONS.map((opt) => {
                const selected = field.value === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => field.onChange(opt.value)}
                    aria-pressed={selected}
                    className={`flex flex-col items-center gap-1 rounded-xl border px-3 py-3 text-center transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${
                      selected
                        ? "border-emerald-500/50 bg-emerald-500/10 shadow-lg shadow-emerald-500/10 ring-2 ring-emerald-500/20"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]"
                    }`}
                  >
                    <span
                      className={`text-sm font-medium ${selected ? "text-white" : "text-slate-300"}`}
                    >
                      {opt.label}
                    </span>
                    <span className="text-xs text-slate-500">{opt.sub}</span>
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
            <div className="flex flex-wrap gap-2">
              {INDUSTRY_OPTIONS.map((opt) => {
                const selected = field.value === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => field.onChange(opt.value)}
                    aria-pressed={selected}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
                      selected
                        ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30"
                        : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20 hover:text-slate-300"
                    }`}
                  >
                    {opt.label}
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

      {/* 기술 스택 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="block text-sm font-medium text-slate-300">
            기술 스택{" "}
            <span className="text-xs font-normal text-slate-500">(선택, 복수 가능)</span>
          </label>
          <Controller
            name="techStack"
            control={control}
            render={({ field }) => (
              <span className="text-xs text-emerald-400">
                {field.value.length > 0 ? `${field.value.length}개 선택됨` : ""}
              </span>
            )}
          />
        </div>
        <Controller
          name="techStack"
          control={control}
          render={({ field }) => (
            <div className="space-y-4 rounded-xl border border-white/5 bg-white/[0.02] p-4">
              {TECH_STACK_CATEGORIES.map((category) => (
                <div key={category.key}>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {category.label}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {category.options.map((tech) => {
                      const selected = field.value.includes(tech);
                      return (
                        <button
                          key={tech}
                          type="button"
                          aria-pressed={selected}
                          onClick={() => {
                            if (selected) {
                              field.onChange(field.value.filter((t) => t !== tech));
                            } else {
                              field.onChange([...field.value, tech]);
                            }
                          }}
                          className={`flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-200 ${
                            selected
                              ? "border-emerald-500/50 bg-emerald-500/15 text-emerald-300"
                              : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20 hover:text-slate-300"
                          }`}
                        >
                          {selected && (
                            <CheckCircle2 className="h-3 w-3 text-emerald-400" aria-hidden="true" />
                          )}
                          {tech}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        />
      </div>

      {/* 주력 제품/서비스 */}
      <div className="space-y-2">
        <label
          htmlFor="main-product"
          className="block text-sm font-medium text-slate-300"
        >
          주력 제품/서비스 <span className="text-red-400">*</span>
        </label>
        <input
          id="main-product"
          type="text"
          {...register("mainProduct")}
          className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-emerald-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-emerald-500/20"
          placeholder="예: 기업용 HR 관리 플랫폼"
        />
        {errors.mainProduct && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {errors.mainProduct.message}
          </p>
        )}
      </div>

      {/* 비즈니스 유형 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-300">
          비즈니스 유형 <span className="text-red-400">*</span>
        </label>
        <Controller
          name="businessType"
          control={control}
          render={({ field }) => (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {BUSINESS_TYPE_OPTIONS.map((opt) => {
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
                        ? "border-emerald-500/50 bg-emerald-500/10 shadow-lg shadow-emerald-500/10 ring-2 ring-emerald-500/20"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]"
                    }`}
                  >
                    <Icon
                      className={`h-5 w-5 ${selected ? "text-emerald-400" : "text-slate-400"}`}
                      aria-hidden="true"
                    />
                    <span
                      className={`text-sm font-medium ${selected ? "text-white" : "text-slate-300"}`}
                    >
                      {opt.label}
                    </span>
                    <span className="text-xs text-slate-500">{opt.description}</span>
                  </button>
                );
              })}
            </div>
          )}
        />
        {errors.businessType && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {errors.businessType.message}
          </p>
        )}
      </div>

      {/* 회사 설명 (선택) */}
      <div className="space-y-2">
        <label
          htmlFor="company-description"
          className="block text-sm font-medium text-slate-300"
        >
          회사 설명{" "}
          <span className="text-xs font-normal text-slate-500">(선택)</span>
        </label>
        <textarea
          id="company-description"
          {...register("companyDescription")}
          rows={3}
          className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-emerald-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-emerald-500/20"
          placeholder="회사 배경, 팀 구성, 현재 기술 수준 등을 자유롭게 설명해 주세요"
        />
        {errors.companyDescription && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {errors.companyDescription.message}
          </p>
        )}
      </div>

      {/* 솔루션 요구사항 (자연어) */}
      <div className="space-y-2">
        <label
          htmlFor="solution-request"
          className="flex items-center gap-2 text-sm font-medium text-slate-300"
        >
          <Sparkles className="h-4 w-4 text-emerald-400" aria-hidden="true" />
          필요한 솔루션 설명 <span className="text-red-400">*</span>
        </label>
        <p className="text-xs text-slate-500">
          자연어로 자유롭게 작성하세요. AI가 분석하여 최적의 솔루션을 설계합니다.
        </p>
        <textarea
          id="solution-request"
          {...register("solutionRequest")}
          rows={5}
          className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-emerald-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-emerald-500/20"
          placeholder="예: 현재 엑셀로 관리하는 고객 데이터를 자동화하고 싶습니다. 영업팀 10명이 사용할 CRM 시스템이 필요하고, Slack 알림과 연동되면 좋겠습니다..."
        />
        <div className="flex items-center justify-between">
          {errors.solutionRequest ? (
            <p className="flex items-center gap-1.5 text-xs text-red-400">
              <AlertCircle className="h-3 w-3" />
              {errors.solutionRequest.message}
            </p>
          ) : (
            <span />
          )}
          <span
            className={`text-xs ${
              (solutionRequest?.length ?? 0) < 50
                ? "text-slate-500"
                : "text-emerald-500"
            }`}
          >
            {solutionRequest?.length ?? 0} / 2000
            {(solutionRequest?.length ?? 0) < 50 && (
              <span className="ml-1 text-slate-600">
                (최소 {50 - (solutionRequest?.length ?? 0)}자 더)
              </span>
            )}
          </span>
        </div>
      </div>
    </div>
  );
}
