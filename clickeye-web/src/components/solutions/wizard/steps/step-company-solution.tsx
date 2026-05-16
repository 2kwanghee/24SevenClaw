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
import { useWizardPreview } from "@/hooks/use-wizard-preview";
import type { NaturalLanguageConfigResponse } from "@/lib/api-client";
import { NL_ANALYSIS_STORAGE_KEY } from "@/lib/storage-keys";

/** 분석 결과 industry 문자열을 IndustryType으로 매핑 */
const INDUSTRY_KEYWORD_MAP: Record<string, IndustryType> = {
  fintech: "fintech",
  finance: "fintech",
  핀테크: "fintech",
  금융: "fintech",
  ecommerce: "ecommerce",
  retail: "ecommerce",
  이커머스: "ecommerce",
  리테일: "ecommerce",
  healthcare: "healthcare",
  health: "healthcare",
  헬스케어: "healthcare",
  의료: "healthcare",
  education: "education",
  교육: "education",
  edutech: "education",
  manufacturing: "manufacturing",
  제조: "manufacturing",
  logistics: "logistics",
  물류: "logistics",
  배송: "logistics",
  marketing: "marketing",
  마케팅: "marketing",
  광고: "marketing",
  game: "game",
  gaming: "game",
  게임: "game",
  it: "it",
  saas: "it",
  software: "it",
};

/** 분석 결과에서 IndustryType 추론 */
function inferIndustry(analysis: NaturalLanguageConfigResponse): IndustryType | null {
  const candidates: string[] = [];
  if (analysis.primary_tag) candidates.push(analysis.primary_tag);
  if (analysis.tags) candidates.push(...analysis.tags);
  if (analysis.target_users) candidates.push(analysis.target_users);
  for (const cand of candidates) {
    const lower = cand.toLowerCase();
    for (const [keyword, industry] of Object.entries(INDUSTRY_KEYWORD_MAP)) {
      if (lower.includes(keyword)) return industry;
    }
  }
  return null;
}

/** 분석 결과의 tech_stack/tags 중 카탈로그 옵션과 일치하는 항목만 추출 */
function inferTechStack(analysis: NaturalLanguageConfigResponse): string[] {
  const all = new Set<string>();
  if (analysis.tech_stack) {
    for (const v of Object.values(analysis.tech_stack)) {
      if (v) all.add(v);
    }
  }
  if (analysis.tags) {
    for (const t of analysis.tags) all.add(t);
  }
  const result: string[] = [];
  // 원래 케이스를 보존하기 위해 카탈로그를 다시 순회
  for (const cat of TECH_STACK_CATEGORIES) {
    for (const opt of cat.options) {
      for (const item of all) {
        if (item.toLowerCase() === opt.toLowerCase() && !result.includes(opt)) {
          result.push(opt);
        }
      }
    }
  }
  return result;
}

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
  enableAutoDecompose: z.boolean(),
});

type FormData = z.infer<typeof schema>;

/* -- 컴포넌트 -- */

/** sessionStorage에서 자연어 분석 결과를 읽어 form 기본값에 병합한다 (일회성). */
function consumeNlAnalysisPrefill(): {
  industry?: IndustryType;
  techStack?: string[];
  solutionRequest?: string;
  companyDescription?: string;
} {
  if (typeof window === "undefined") return {};
  try {
    const raw = sessionStorage.getItem(NL_ANALYSIS_STORAGE_KEY);
    if (!raw) return {};
    sessionStorage.removeItem(NL_ANALYSIS_STORAGE_KEY);
    const parsed = JSON.parse(raw) as NaturalLanguageConfigResponse & { sourceText?: string };
    const industry = inferIndustry(parsed) ?? undefined;
    const techStack = inferTechStack(parsed);
    const reasoning = parsed.reasoning ?? "";
    const features = (parsed.features ?? []).join(", ");
    const description = parsed.target_users
      ? `대상 사용자: ${parsed.target_users}${features ? `. 주요 기능: ${features}` : ""}`
      : features
        ? `주요 기능: ${features}`
        : reasoning;
    return {
      industry,
      techStack: techStack.length > 0 ? techStack : undefined,
      solutionRequest: parsed.sourceText || undefined,
      companyDescription: description || undefined,
    };
  } catch {
    return {};
  }
}

export function StepCompanySolution() {
  // defaultValues 초기화에만 필요 — reactive 구독 없이 1회 읽기
  const initialCompany = useSolutionWizardStore.getState().data.company;
  const setCompany = useSolutionWizardStore((s) => s.setCompany);
  const setStep0Valid = useSolutionWizardStore((s) => s.setStep0Valid);

  // 빠른 시작에서 넘어온 자연어 분석 결과가 있으면 초기값에 병합 (mount 시 1회만)
  const nlPrefill = consumeNlAnalysisPrefill();

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
      industry: nlPrefill.industry ?? initialCompany.industry ?? undefined,
      techStack: nlPrefill.techStack ?? initialCompany.techStack,
      mainProduct: initialCompany.mainProduct,
      businessType: initialCompany.businessType ?? undefined,
      companyDescription: nlPrefill.companyDescription ?? initialCompany.companyDescription,
      solutionRequest: nlPrefill.solutionRequest ?? initialCompany.solutionRequest,
      enableAutoDecompose: initialCompany.enableAutoDecompose ?? false,
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
      enableAutoDecompose: v.enableAutoDecompose ?? false,
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valuesJson, setCompany]);

  const solutionRequest = watch("solutionRequest");

  // ③ 라이브 프리뷰 — 입력 안정 후 700ms 디바운스로 Claude 분석 호출
  useWizardPreview(
    "company",
    JSON.parse(valuesJson) as Record<string, unknown>,
    (d) => typeof d.solutionRequest === "string" && (d.solutionRequest as string).length >= 50,
  );

  return (
    <div className="space-y-6">
      {/* 회사 이름 */}
      <div className="space-y-2">
        <label
          htmlFor="company-name"
          className="block text-sm font-medium text-zinc-700"
        >
          회사 이름 <span className="text-red-600">*</span>
        </label>
        <input
          id="company-name"
          type="text"
          {...register("companyName")}
          className="w-full rounded-xl border border-zinc-300 bg-white px-4 py-3 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all focus:border-zinc-400 focus:ring-2 focus:ring-zinc-400/20"
          placeholder="예: 우리 회사"
        />
        {errors.companyName && (
          <p className="flex items-center gap-1.5 text-xs text-red-600">
            <AlertCircle className="h-3 w-3" />
            {errors.companyName.message}
          </p>
        )}
      </div>

      {/* 회사 규모 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-zinc-700">
          회사 규모 <span className="text-red-600">*</span>
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
                        ? "border-zinc-900 bg-zinc-50 shadow-sm ring-2 ring-zinc-900/10"
                        : "border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50"
                    }`}
                  >
                    <span
                      className={`text-sm font-medium ${selected ? "text-zinc-950" : "text-zinc-700"}`}
                    >
                      {opt.label}
                    </span>
                    <span className="text-xs text-zinc-500">{opt.sub}</span>
                  </button>
                );
              })}
            </div>
          )}
        />
        {errors.companySize && (
          <p className="flex items-center gap-1.5 text-xs text-red-600">
            <AlertCircle className="h-3 w-3" />
            {errors.companySize.message}
          </p>
        )}
      </div>

      {/* 업종 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-zinc-700">
          업종 <span className="text-red-600">*</span>
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
                        ? "border-zinc-900 bg-zinc-900 text-white"
                        : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300 hover:text-zinc-900"
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
          <p className="flex items-center gap-1.5 text-xs text-red-600">
            <AlertCircle className="h-3 w-3" />
            {errors.industry.message}
          </p>
        )}
      </div>

      {/* 기술 스택 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="block text-sm font-medium text-zinc-700">
            기술 스택{" "}
            <span className="text-xs font-normal text-zinc-500">(선택, 복수 가능)</span>
          </label>
          <Controller
            name="techStack"
            control={control}
            render={({ field }) => (
              <span className="text-xs text-emerald-600">
                {field.value.length > 0 ? `${field.value.length}개 선택됨` : ""}
              </span>
            )}
          />
        </div>
        <Controller
          name="techStack"
          control={control}
          render={({ field }) => (
            <div className="space-y-4 rounded-xl border border-zinc-200 bg-zinc-50 p-4">
              {TECH_STACK_CATEGORIES.map((category) => (
                <div key={category.key}>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
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
                              ? "border-emerald-500/50 bg-emerald-50 text-emerald-600"
                              : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300 hover:text-zinc-900"
                          }`}
                        >
                          {selected && (
                            <CheckCircle2 className="h-3 w-3 text-emerald-600" aria-hidden="true" />
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
          className="block text-sm font-medium text-zinc-700"
        >
          주력 제품/서비스 <span className="text-red-600">*</span>
        </label>
        <input
          id="main-product"
          type="text"
          {...register("mainProduct")}
          className="w-full rounded-xl border border-zinc-300 bg-white px-4 py-3 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all focus:border-zinc-400 focus:ring-2 focus:ring-zinc-400/20"
          placeholder="예: 기업용 HR 관리 플랫폼"
        />
        {errors.mainProduct && (
          <p className="flex items-center gap-1.5 text-xs text-red-600">
            <AlertCircle className="h-3 w-3" />
            {errors.mainProduct.message}
          </p>
        )}
      </div>

      {/* 비즈니스 유형 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-zinc-700">
          비즈니스 유형 <span className="text-red-600">*</span>
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
                        ? "border-zinc-900 bg-zinc-50 shadow-sm ring-2 ring-zinc-900/10"
                        : "border-zinc-200 bg-white hover:border-zinc-300 hover:bg-zinc-50"
                    }`}
                  >
                    <Icon
                      className={`h-5 w-5 ${selected ? "text-emerald-600" : "text-zinc-500"}`}
                      aria-hidden="true"
                    />
                    <span
                      className={`text-sm font-medium ${selected ? "text-zinc-950" : "text-zinc-700"}`}
                    >
                      {opt.label}
                    </span>
                    <span className="text-xs text-zinc-500">{opt.description}</span>
                  </button>
                );
              })}
            </div>
          )}
        />
        {errors.businessType && (
          <p className="flex items-center gap-1.5 text-xs text-red-600">
            <AlertCircle className="h-3 w-3" />
            {errors.businessType.message}
          </p>
        )}
      </div>

      {/* 회사 설명 (선택) */}
      <div className="space-y-2">
        <label
          htmlFor="company-description"
          className="block text-sm font-medium text-zinc-700"
        >
          회사 설명{" "}
          <span className="text-xs font-normal text-zinc-500">(선택)</span>
        </label>
        <textarea data-gramm="false" data-gramm_editor="false"
          id="company-description"
          {...register("companyDescription")}
          rows={3}
          className="w-full resize-none rounded-xl border border-zinc-300 bg-white px-4 py-3 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all focus:border-zinc-400 focus:ring-2 focus:ring-zinc-400/20"
          placeholder="회사 배경, 팀 구성, 현재 기술 수준 등을 자유롭게 설명해 주세요"
        />
        {errors.companyDescription && (
          <p className="flex items-center gap-1.5 text-xs text-red-600">
            <AlertCircle className="h-3 w-3" />
            {errors.companyDescription.message}
          </p>
        )}
      </div>

      {/* 솔루션 요구사항 (자연어) */}
      <div className="space-y-2">
        <label
          htmlFor="solution-request"
          className="flex items-center gap-2 text-sm font-medium text-zinc-700"
        >
          <Sparkles className="h-4 w-4 text-emerald-600" aria-hidden="true" />
          필요한 솔루션 설명 <span className="text-red-600">*</span>
        </label>
        <p className="text-xs text-zinc-500">
          자연어로 자유롭게 작성하세요. AI가 분석하여 최적의 솔루션을 설계합니다.
        </p>
        <textarea data-gramm="false" data-gramm_editor="false"
          id="solution-request"
          {...register("solutionRequest")}
          rows={5}
          className="w-full resize-none rounded-xl border border-zinc-300 bg-white px-4 py-3 text-sm text-zinc-900 placeholder-zinc-400 outline-none transition-all focus:border-zinc-400 focus:ring-2 focus:ring-zinc-400/20"
          placeholder="예: 현재 엑셀로 관리하는 고객 데이터를 자동화하고 싶습니다. 영업팀 10명이 사용할 CRM 시스템이 필요하고, Slack 알림과 연동되면 좋겠습니다..."
        />
        <div className="flex items-center justify-between">
          {errors.solutionRequest ? (
            <p className="flex items-center gap-1.5 text-xs text-red-600">
              <AlertCircle className="h-3 w-3" />
              {errors.solutionRequest.message}
            </p>
          ) : (
            <span />
          )}
          <span
            className={`text-xs ${
              (solutionRequest?.length ?? 0) < 50
                ? "text-zinc-500"
                : "text-emerald-600"
            }`}
          >
            {solutionRequest?.length ?? 0} / 2000
            {(solutionRequest?.length ?? 0) < 50 && (
              <span className="ml-1 text-zinc-500">
                (최소 {50 - (solutionRequest?.length ?? 0)}자 더)
              </span>
            )}
          </span>
        </div>
      </div>

      {/* 자동 분석/분해 토글 */}
      <Controller
        name="enableAutoDecompose"
        control={control}
        render={({ field }) => (
          <div className="flex items-start justify-between rounded-xl border border-zinc-200 bg-zinc-50 p-4">
            <div className="space-y-1 pr-4">
              <div className="flex items-center gap-2 text-sm font-medium text-zinc-900">
                <Sparkles className="h-4 w-4 text-amber-500" aria-hidden="true" />
                ClickEye 자동 분석/분해
              </div>
              <p className="text-xs text-zinc-500">
                ON 시 다운로드 후 <code className="rounded bg-zinc-200 px-1 py-0.5 font-mono">bash start.sh</code> 실행하면 솔루션 요구사항을 자동 분석·분해해 AI Team 검수 카드를 생성합니다.
                직접 설계하려면 OFF로 두세요.
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={field.value}
              aria-label="ClickEye 자동 분석/분해"
              onClick={() => field.onChange(!field.value)}
              className={`mt-0.5 inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full p-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-400/20 ${
                field.value ? "bg-emerald-500" : "bg-zinc-300"
              }`}
            >
              <span
                className={`h-5 w-5 rounded-full bg-white shadow transition-transform ${
                  field.value ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>
          </div>
        )}
      />
    </div>
  );
}
