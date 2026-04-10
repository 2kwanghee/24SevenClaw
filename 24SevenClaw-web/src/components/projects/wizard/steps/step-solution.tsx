"use client";

import {
  Layers,
  AlertCircle,
  Globe,
  Server,
  Layout,
  Wrench,
  Rocket,
  Settings,
  FileText,
  Loader2,
  Check,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { useEffect } from "react";

import { useWizardStore } from "@/stores/wizard-store";
import { useRecommend } from "@/hooks/use-recommend";
import type { SolutionType } from "@/types/wizard";

/* ── 상수 ── */

const SOLUTION_TYPE_OPTIONS: {
  value: SolutionType;
  label: string;
  description: string;
  icon: typeof Globe;
}[] = [
  {
    value: "saas",
    label: "SaaS",
    description: "구독형 웹 서비스",
    icon: Globe,
  },
  {
    value: "rest-api",
    label: "REST API",
    description: "백엔드 API 서버",
    icon: Server,
  },
  {
    value: "fullstack",
    label: "풀스택",
    description: "프론트 + 백엔드",
    icon: Layout,
  },
  {
    value: "internal-tool",
    label: "내부 도구",
    description: "사내 관리 도구",
    icon: Wrench,
  },
  {
    value: "mvp",
    label: "MVP",
    description: "빠른 프로토타입",
    icon: Rocket,
  },
  {
    value: "custom",
    label: "커스텀",
    description: "직접 구성",
    icon: Settings,
  },
];

interface StackPreset {
  id: string;
  label: string;
  techs: string[];
}

const STACK_PRESETS: StackPreset[] = [
  {
    id: "nextjs-fastapi",
    label: "Next.js + FastAPI",
    techs: ["Next.js", "React", "FastAPI", "PostgreSQL"],
  },
  {
    id: "react-express",
    label: "React + Express",
    techs: ["React", "Express", "Node.js", "MongoDB"],
  },
  {
    id: "vue-django",
    label: "Vue + Django",
    techs: ["Vue", "Django", "Python", "PostgreSQL"],
  },
  {
    id: "fastapi-only",
    label: "FastAPI Only",
    techs: ["FastAPI", "Python", "PostgreSQL", "Redis"],
  },
  {
    id: "nextjs-fullstack",
    label: "Next.js Fullstack",
    techs: ["Next.js", "React", "Prisma", "PostgreSQL"],
  },
  {
    id: "spring-react",
    label: "Spring + React",
    techs: ["Spring Boot", "Java", "React", "MySQL"],
  },
];

/* ── Zod 스키마 ── */

const schema = z.object({
  projectName: z
    .string()
    .min(1, "프로젝트 이름을 입력하세요")
    .max(100, "100자 이내로 입력하세요")
    .regex(
      /^[a-zA-Z0-9][a-zA-Z0-9-]*$/,
      "영문, 숫자, 하이픈만 사용 가능합니다 (첫 글자는 영문 또는 숫자)",
    ),
  solutionType: z.enum(
    ["saas", "rest-api", "fullstack", "internal-tool", "mvp", "custom"],
    { message: "솔루션 유형을 선택하세요" },
  ),
  stackPreset: z.string().nullable(),
  description: z.string().max(1000, "1000자 이내로 입력하세요"),
});

type FormData = z.infer<typeof schema>;

/* ── 컴포넌트 ── */

export function StepSolution() {
  const solution = useWizardStore((s) => s.data.solution);
  const setSolution = useWizardStore((s) => s.setSolution);

  // 솔루션 유형 변경 시 추천 API 호출 (debounce)
  const { isLoading: isRecommending, phase } = useRecommend();

  const {
    register,
    control,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      projectName: solution.projectName,
      solutionType: solution.solutionType ?? undefined,
      stackPreset: solution.stackPreset,
      description: solution.description,
    },
  });

  // 입력 값이 변경될 때 스토어에 자동 저장
  const watchedValues = watch();
  useEffect(() => {
    setSolution({
      projectName: watchedValues.projectName,
      solutionType: watchedValues.solutionType ?? null,
      stackPreset: watchedValues.stackPreset ?? null,
      description: watchedValues.description,
    });
  }, [
    watchedValues.projectName,
    watchedValues.solutionType,
    watchedValues.stackPreset,
    watchedValues.description,
    setSolution,
  ]);

  return (
    <div className="space-y-6">
      {/* 프로젝트 이름 */}
      <div className="space-y-2">
        <label
          htmlFor="project-name"
          className="block text-sm font-medium text-slate-300"
        >
          프로젝트 이름 <span className="text-red-400">*</span>
        </label>
        <div className="relative">
          <Layers className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            id="project-name"
            type="text"
            {...register("projectName")}
            className="w-full rounded-xl border border-white/10 bg-white/5 py-3 pl-11 pr-4 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-violet-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-violet-500/20"
            placeholder="예: my-awesome-project"
          />
        </div>
        {errors.projectName && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {errors.projectName.message}
          </p>
        )}
        <p className="text-xs text-slate-500">
          영문, 숫자, 하이픈만 사용 가능
        </p>
      </div>

      {/* 솔루션 유형 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-300">
          솔루션 유형 <span className="text-red-400">*</span>
        </label>
        <Controller
          name="solutionType"
          control={control}
          render={({ field }) => (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {SOLUTION_TYPE_OPTIONS.map((opt) => {
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
        {errors.solutionType && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {errors.solutionType.message}
          </p>
        )}
        {/* AI 분석 상태 카드 */}
        {(isRecommending || phase === "done") && (
          <div
            className={`rounded-xl border px-4 py-3 transition-all duration-500 ${
              phase === "done"
                ? "border-emerald-500/30 bg-emerald-500/5"
                : "border-violet-500/30 bg-violet-500/5"
            }`}
          >
            <div className="mb-2.5 flex items-center gap-2">
              {phase === "done" ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <Sparkles className="h-4 w-4 animate-pulse text-violet-400" />
              )}
              <span
                className={`text-sm font-medium ${
                  phase === "done" ? "text-emerald-300" : "text-violet-300"
                }`}
              >
                {phase === "done"
                  ? "AI 분석 완료"
                  : "AI가 최적 구성을 분석하고 있습니다"}
              </span>
            </div>
            <div className="space-y-1.5 pl-6">
              <AnalysisStepRow
                label="에이전트 분석"
                active={phase === "agents"}
                done={phase !== "agents" && phase !== "idle"}
              />
              <AnalysisStepRow
                label="스킬 선정"
                active={phase === "skills"}
                done={phase === "pipelines" || phase === "done"}
              />
              <AnalysisStepRow
                label="파이프라인 구성"
                active={phase === "pipelines"}
                done={phase === "done"}
              />
            </div>
          </div>
        )}
      </div>

      {/* 기술 스택 프리셋 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-300">
          기술 스택 프리셋{" "}
          <span className="text-xs font-normal text-slate-500">(선택)</span>
        </label>
        <Controller
          name="stackPreset"
          control={control}
          render={({ field }) => (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {STACK_PRESETS.map((preset) => {
                const selected = field.value === preset.id;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() =>
                      field.onChange(selected ? null : preset.id)
                    }
                    aria-pressed={selected}
                    className={`flex flex-col gap-2 rounded-xl border px-4 py-3 text-left transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${
                      selected
                        ? "border-violet-500/50 bg-violet-500/10 shadow-lg shadow-violet-500/10 ring-2 ring-violet-500/20"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]"
                    }`}
                  >
                    <span
                      className={`text-sm font-medium ${selected ? "text-white" : "text-slate-300"}`}
                    >
                      {preset.label}
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {preset.techs.map((tech) => (
                        <span
                          key={tech}
                          className={`rounded-md px-2 py-0.5 text-xs ${
                            selected
                              ? "bg-violet-500/20 text-violet-300"
                              : "bg-white/5 text-slate-500"
                          }`}
                        >
                          {tech}
                        </span>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        />
      </div>

      {/* 목표 설명 */}
      <div className="space-y-2">
        <label
          htmlFor="solution-desc"
          className="block text-sm font-medium text-slate-300"
        >
          목표 설명{" "}
          <span className="text-xs font-normal text-slate-500">(선택)</span>
        </label>
        <div className="relative">
          <FileText className="pointer-events-none absolute left-3.5 top-3.5 h-4 w-4 text-slate-500" />
          <textarea
            id="solution-desc"
            {...register("description")}
            rows={4}
            className="w-full resize-none rounded-xl border border-white/10 bg-white/5 py-3 pl-11 pr-4 text-sm text-white placeholder-slate-500 outline-none transition-all focus:border-violet-500/50 focus:bg-white/[0.07] focus:ring-2 focus:ring-violet-500/20"
            placeholder="프로젝트의 목표와 주요 기능을 간략히 설명하세요"
          />
        </div>
        {errors.description && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {errors.description.message}
          </p>
        )}
      </div>
    </div>
  );
}

/* ── 분석 단계 행 ── */

interface AnalysisStepRowProps {
  label: string;
  active: boolean;
  done: boolean;
}

function AnalysisStepRow({ label, active, done }: AnalysisStepRowProps) {
  return (
    <div className="flex items-center gap-2 text-xs">
      {done ? (
        <Check className="h-3 w-3 text-emerald-400" />
      ) : active ? (
        <Loader2 className="h-3 w-3 animate-spin text-violet-400" />
      ) : (
        <div className="h-3 w-3 rounded-full border border-white/10" />
      )}
      <span
        className={
          done
            ? "text-emerald-300"
            : active
              ? "text-violet-300"
              : "text-slate-600"
        }
      >
        {label}
        {active && "..."}
      </span>
    </div>
  );
}
