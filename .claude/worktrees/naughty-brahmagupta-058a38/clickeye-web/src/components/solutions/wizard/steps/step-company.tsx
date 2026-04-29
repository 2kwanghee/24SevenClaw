"use client";

import {
  Building2,
  Store,
  Network,
  Laptop,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { useEffect } from "react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import type { BusinessType } from "@/types/solution-wizard";

/* -- 상수 -- */

const BUSINESS_TYPE_OPTIONS: {
  value: BusinessType;
  label: string;
  description: string;
  icon: typeof Building2;
}[] = [
  {
    value: "b2b",
    label: "B2B",
    description: "기업 대상",
    icon: Building2,
  },
  {
    value: "b2c",
    label: "B2C",
    description: "소비자 대상",
    icon: Store,
  },
  {
    value: "b2b2c",
    label: "B2B2C",
    description: "복합 모델",
    icon: Network,
  },
  {
    value: "internal",
    label: "내부 도구",
    description: "사내 시스템",
    icon: Laptop,
  },
];

/* -- Zod 스키마 -- */

const schema = z.object({
  companyName: z
    .string()
    .min(1, "회사 이름을 입력하세요")
    .max(200, "200자 이내로 입력하세요"),
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
    .min(10, "솔루션 요구사항을 10자 이상 입력하세요")
    .max(2000, "2000자 이내로 입력하세요"),
});

type FormData = z.infer<typeof schema>;

/* -- 컴포넌트 -- */

export function StepCompany() {
  const company = useSolutionWizardStore((s) => s.data.company);
  const setCompany = useSolutionWizardStore((s) => s.setCompany);

  const {
    register,
    control,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      companyName: company.companyName,
      mainProduct: company.mainProduct,
      businessType: company.businessType ?? undefined,
      companyDescription: company.companyDescription,
      solutionRequest: company.solutionRequest,
    },
  });

  // 입력 변경 시 스토어 자동 저장
  const watchedValues = watch();
  useEffect(() => {
    setCompany({
      companyName: watchedValues.companyName ?? "",
      mainProduct: watchedValues.mainProduct ?? "",
      businessType: watchedValues.businessType ?? null,
      companyDescription: watchedValues.companyDescription ?? "",
      solutionRequest: watchedValues.solutionRequest ?? "",
    });
  }, [
    watchedValues.companyName,
    watchedValues.mainProduct,
    watchedValues.businessType,
    watchedValues.companyDescription,
    watchedValues.solutionRequest,
    setCompany,
  ]);

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
                    />
                    <span
                      className={`text-sm font-medium ${selected ? "text-zinc-950" : "text-zinc-700"}`}
                    >
                      {opt.label}
                    </span>
                    <span className="text-xs text-zinc-500">
                      {opt.description}
                    </span>
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
        <textarea
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
          <Sparkles className="h-4 w-4 text-emerald-600" />
          필요한 솔루션 설명 <span className="text-red-600">*</span>
        </label>
        <p className="text-xs text-zinc-500">
          자연어로 자유롭게 작성하세요. AI가 분석하여 최적의 솔루션을
          설계합니다.
        </p>
        <textarea
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
          <span className="text-xs text-zinc-500">
            {watchedValues.solutionRequest?.length ?? 0} / 2000
          </span>
        </div>
      </div>
    </div>
  );
}
