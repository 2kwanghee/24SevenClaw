"use client";

import { useEffect, useRef, useState } from "react";

import { recommend } from "@/lib/api-client";
import { useWizardStore } from "@/stores/wizard-store";
import type { SolutionType, Recommendations } from "@/types/wizard";

/**
 * API 추천 ID → 프론트엔드 카탈로그 ID 매핑.
 * API 카탈로그와 프론트엔드 카탈로그의 ID가 다른 경우 변환한다.
 */
const SKILL_ID_MAP: Record<string, string> = {
  "github-mcp": "github",
};

const PIPELINE_ID_MAP: Record<string, string> = {
  "ai-critique": "ai-review",
};

function mapIds(ids: string[], mapping: Record<string, string>): string[] {
  return ids.map((id) => mapping[id] ?? id);
}

/** reasoning 맵의 키도 ID 매핑에 따라 변환한다. */
function mapReasonings(
  items: Array<{ id: string; reasoning?: string }>,
  idMap: Record<string, string>,
): Record<string, string> {
  const result: Record<string, string> = {};
  for (const item of items) {
    if (item.reasoning) {
      const mappedId = idMap[item.id] ?? item.id;
      result[mappedId] = item.reasoning;
    }
  }
  return result;
}

const DEBOUNCE_MS = 300;

/** AI 분석 진행 단계 */
export type AnalysisPhase = "idle" | "agents" | "skills" | "pipelines" | "done";

/**
 * Step 2 솔루션 유형 변경 시 /api/v1/recommend 호출 (debounce).
 * 결과를 wizard store의 recommendations에 저장한다.
 * 분석 진행 단계(phase)를 노출하여 UI에서 단계별 피드백을 표시할 수 있다.
 */
export function useRecommend() {
  const solutionType = useWizardStore((s) => s.data.solution.solutionType);
  const setRecommendations = useWizardStore((s) => s.setRecommendations);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const phaseTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [phase, setPhase] = useState<AnalysisPhase>("idle");

  useEffect(() => {
    if (!solutionType) return;

    clearTimeout(timerRef.current);
    phaseTimersRef.current.forEach(clearTimeout);
    phaseTimersRef.current = [];

    setIsLoading(true);
    setPhase("agents");

    phaseTimersRef.current.push(
      setTimeout(() => setPhase("skills"), 500),
      setTimeout(() => setPhase("pipelines"), 1000),
    );

    timerRef.current = setTimeout(async () => {
      try {
        const res = await recommend.get({ solution_type: solutionType });
        const rec: Recommendations = {
          agents: res.agents.map((a) => a.id),
          skills: mapIds(
            res.skills.map((s) => s.id),
            SKILL_ID_MAP,
          ),
          pipelines: mapIds(
            res.pipelines.map((p) => p.id),
            PIPELINE_ID_MAP,
          ),
          skillReasonings: mapReasonings(res.skills, SKILL_ID_MAP),
          pipelineReasonings: mapReasonings(res.pipelines, PIPELINE_ID_MAP),
          summary: res.summary,
        };
        setRecommendations(rec);
      } catch {
        // API 실패 시 조용히 무시 — 추천은 선택 사항
      } finally {
        setIsLoading(false);
        phaseTimersRef.current.forEach(clearTimeout);
        phaseTimersRef.current = [];
        setPhase("done");
        phaseTimersRef.current.push(
          setTimeout(() => setPhase("idle"), 2000),
        );
      }
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timerRef.current);
      phaseTimersRef.current.forEach(clearTimeout);
      phaseTimersRef.current = [];
    };
  }, [solutionType, setRecommendations]);

  return { isLoading, phase };
}

/**
 * 솔루션 유형 → 추천 역할 에이전트 매핑 (클라이언트 측).
 * API의 agents는 플랫폼(claude-code 등)이므로 Step 3 역할 에이전트는 별도 매핑 사용.
 */
export const AGENT_RECOMMENDATION_MAP: Record<SolutionType, string[]> = {
  saas: ["backend", "frontend", "uiux"],
  "rest-api": ["backend"],
  fullstack: ["fullstack", "uiux"],
  "internal-tool": ["backend", "frontend"],
  mvp: ["fullstack"],
  custom: [],
};

/**
 * 솔루션 유형 → 역할 에이전트별 추천 사유 (클라이언트 측).
 * API의 에이전트 reasoning은 플랫폼(claude-code 등) 기준이므로, 역할 에이전트는 별도 정의.
 */
export const AGENT_REASONING_MAP: Record<SolutionType, Record<string, string>> =
  {
    saas: {
      backend:
        "SaaS는 복잡한 API와 인증 시스템이 핵심이므로 백엔드 전문가가 필수입니다",
      frontend:
        "사용자 대시보드와 결제 UI에 프론트엔드 전문가가 필요합니다",
      uiux: "SaaS 제품의 사용성과 전환율을 위해 UI/UX 디자이너가 추천됩니다",
    },
    "rest-api": {
      backend:
        "REST API 설계와 서비스 로직 구현에 백엔드 전문가가 최적입니다",
    },
    fullstack: {
      fullstack:
        "프론트+백엔드를 아우르는 풀스택 개발에 최적화된 에이전트입니다",
      uiux: "사용자 경험을 고려한 인터페이스 설계에 UI/UX 전문가가 도움됩니다",
    },
    "internal-tool": {
      backend:
        "내부 도구의 핵심인 API와 데이터 처리에 백엔드 전문가가 적합합니다",
      frontend: "사용자 인터페이스 구현에 프론트엔드 전문가가 필요합니다",
    },
    mvp: {
      fullstack:
        "MVP의 빠른 개발을 위해 풀스택 시니어가 가장 효율적입니다",
    },
    custom: {},
  };
