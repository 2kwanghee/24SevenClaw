import type { SolutionWizardStepId, SolutionWizardData } from "@/types/solution-wizard";
import { CompanyBlueprintView } from "./company-blueprint-view";

interface StepSummaryViewProps {
  stepId: SolutionWizardStepId;
  data: SolutionWizardData;
  previewByStep: Partial<Record<SolutionWizardStepId, Record<string, unknown>>>;
}

const INDUSTRY_LABEL: Record<string, string> = {
  it: "IT/소프트웨어", fintech: "금융/핀테크", ecommerce: "이커머스/리테일",
  healthcare: "헬스케어/의료", education: "교육/에듀테크", manufacturing: "제조업",
  logistics: "물류/배송", marketing: "마케팅/광고", game: "게임/엔터테인먼트", other: "기타",
};

const BUSINESS_TYPE_LABEL: Record<string, string> = {
  b2b: "B2B", b2c: "B2C", b2b2c: "B2B2C", internal: "내부 도구",
};

const COMPANY_SIZE_LABEL: Record<string, string> = {
  startup: "스타트업", small: "소기업", medium: "중소기업",
  "mid-large": "중견기업", enterprise: "대기업",
};

const PLATFORM_LABEL: Record<string, string> = {
  "claude-code": "Claude Code", "gemini-cli": "Gemini CLI", cursor: "Cursor", codex: "Codex",
};

const OS_LABEL: Record<string, string> = { wsl2: "WSL2" };

const AUTH_METHOD_LABEL: Record<string, string> = {
  api_key: "API 키", oauth_browser: "OAuth 브라우저", oauth_setup_token: "OAuth Setup Token",
};

const ERROR_STATUSES = new Set(["too_short", "api_credit_error", "api_auth_error", "api_error", "error"]);

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-zinc-500">{label}</span>
      <span className="font-medium text-zinc-800">{value}</span>
    </div>
  );
}

export function StepSummaryView({ stepId, data, previewByStep }: StepSummaryViewProps) {
  switch (stepId) {
    case "company": {
      const blueprint = previewByStep.company;
      const hasValidBlueprint = blueprint && !ERROR_STATUSES.has(blueprint.status as string);
      if (hasValidBlueprint) {
        return <CompanyBlueprintView result={blueprint} />;
      }
      const { companyName, industry, businessType, companySize, solutionRequest } = data.company;
      return (
        <div className="space-y-2 text-xs">
          {companyName && <Row label="회사명" value={companyName} />}
          {industry && <Row label="업종" value={INDUSTRY_LABEL[industry] ?? industry} />}
          {businessType && <Row label="비즈니스 유형" value={BUSINESS_TYPE_LABEL[businessType] ?? businessType} />}
          {companySize && <Row label="규모" value={COMPANY_SIZE_LABEL[companySize] ?? companySize} />}
          {solutionRequest && (
            <p className="mt-2 line-clamp-4 rounded-lg bg-zinc-50 p-2.5 leading-relaxed text-zinc-600">
              {solutionRequest}
            </p>
          )}
        </div>
      );
    }

    case "prototypes": {
      const { selectedPrototypeId, generatedPrototypes } = data.prototypes;
      const selected = generatedPrototypes.find((p) => p.id === selectedPrototypeId);
      if (!selected) return <p className="text-xs text-zinc-400">프로토타입이 선택되지 않았습니다.</p>;
      return (
        <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 text-xs">
          <p className="font-semibold text-zinc-800">{selected.name}</p>
          {selected.solutionType && <p className="mt-0.5 text-zinc-500">{selected.solutionType}</p>}
          {selected.reasoning && (
            <p className="mt-1.5 line-clamp-3 leading-relaxed text-zinc-600">{selected.reasoning}</p>
          )}
        </div>
      );
    }

    case "pm-selection": {
      const { selectedPmProfileId, recommendedItems } = data.pm;
      const selected = recommendedItems.find((item) => item.pmId === selectedPmProfileId);
      if (!selected) return <p className="text-xs text-zinc-400">PM이 선택되지 않았습니다.</p>;
      return (
        <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 text-xs">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-semibold text-zinc-800">{selected.name}</p>
              {selected.title && <p className="mt-0.5 text-zinc-500">{selected.title}</p>}
              {selected.domain && <p className="text-zinc-500">{selected.domain}</p>}
            </div>
            <span className="shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">
              {Math.round(selected.matchScore)}% 매칭
            </span>
          </div>
        </div>
      );
    }

    case "pm-composition":
      return (
        <p className="rounded-lg bg-zinc-50 p-3 text-xs text-zinc-500">
          PM 구성 요소가 확인되었습니다.
        </p>
      );

    case "agents": {
      const { selectedAgents, selectedSkills, selectedHooks } = data.agents;
      const total = selectedAgents.length + selectedSkills.length + selectedHooks.length;
      if (total === 0) return <p className="text-xs text-zinc-400">에이전트가 선택되지 않았습니다.</p>;
      return (
        <div className="space-y-1.5 text-xs">
          {selectedAgents.length > 0 && <Row label="에이전트" value={`${selectedAgents.length}개`} />}
          {selectedSkills.length > 0 && <Row label="스킬" value={`${selectedSkills.length}개`} />}
          {selectedHooks.length > 0 && <Row label="훅" value={`${selectedHooks.length}개`} />}
        </div>
      );
    }

    case "platform": {
      const { platformId } = data.platform;
      if (!platformId) return <p className="text-xs text-zinc-400">플랫폼이 선택되지 않았습니다.</p>;
      return (
        <div className="text-xs">
          <Row label="선택 플랫폼" value={PLATFORM_LABEL[platformId] ?? platformId} />
        </div>
      );
    }

    case "os": {
      const { osId } = data.os;
      if (!osId) return <p className="text-xs text-zinc-400">실행 환경이 선택되지 않았습니다.</p>;
      return (
        <div className="text-xs">
          <Row label="실행 환경" value={OS_LABEL[osId] ?? osId} />
        </div>
      );
    }

    case "env": {
      const { authMethod, envVars } = data.env;
      const envCount = Object.values(envVars).filter(Boolean).length;
      return (
        <div className="space-y-1.5 text-xs">
          <Row label="인증 방식" value={AUTH_METHOD_LABEL[authMethod] ?? authMethod} />
          {envCount > 0 && <Row label="환경변수" value={`${envCount}개 설정됨`} />}
        </div>
      );
    }

    case "roi": {
      const { result } = data.roi;
      if (!result) return <p className="text-xs text-zinc-400">ROI 분석이 완료되지 않았습니다.</p>;
      return (
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-zinc-500">절감 비용</span>
            <span className="font-semibold text-emerald-700">₩{result.savings.toLocaleString()}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-zinc-500">절감율</span>
            <span className="font-semibold text-emerald-700">{Math.round(result.savingsRatio * 100)}%</span>
          </div>
        </div>
      );
    }

    case "confirm":
      return (
        <p className="rounded-lg bg-zinc-50 p-3 text-xs text-zinc-500">
          모든 설정이 완료되었습니다.
        </p>
      );

    default:
      return null;
  }
}
