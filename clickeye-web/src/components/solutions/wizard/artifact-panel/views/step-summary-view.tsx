import { useTranslations } from "next-intl";

import type { SolutionWizardStepId, SolutionWizardData } from "@/types/solution-wizard";
import { CompanyBlueprintView } from "./company-blueprint-view";

interface StepSummaryViewProps {
  stepId: SolutionWizardStepId;
  data: SolutionWizardData;
  previewByStep: Partial<Record<SolutionWizardStepId, Record<string, unknown>>>;
}

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
  const t = useTranslations("wizard.preview.summary");
  const mapLabel = (map: string, key: string) =>
    t.has(`${map}.${key}`) ? t(`${map}.${key}`) : key;

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
          {companyName && <Row label={t("companyName")} value={companyName} />}
          {industry && <Row label={t("industry")} value={mapLabel("industryMap", industry)} />}
          {businessType && <Row label={t("businessType")} value={mapLabel("businessTypeMap", businessType)} />}
          {companySize && <Row label={t("companySize")} value={mapLabel("companySizeMap", companySize)} />}
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
      if (!selected) return <p className="text-xs text-zinc-400">{t("noPrototype")}</p>;
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
      if (!selected) return <p className="text-xs text-zinc-400">{t("noPm")}</p>;
      return (
        <div className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 text-xs">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-semibold text-zinc-800">{selected.name}</p>
              {selected.title && <p className="mt-0.5 text-zinc-500">{selected.title}</p>}
              {selected.domain && <p className="text-zinc-500">{selected.domain}</p>}
            </div>
            <span className="shrink-0 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">
              {t("matching", { score: Math.round(selected.matchScore) })}
            </span>
          </div>
        </div>
      );
    }

    case "pm-composition":
      return (
        <p className="rounded-lg bg-zinc-50 p-3 text-xs text-zinc-500">
          {t("pmComposition")}
        </p>
      );

    case "agents": {
      const { selectedAgents, selectedSkills, selectedHooks } = data.agents;
      const total = selectedAgents.length + selectedSkills.length + selectedHooks.length;
      if (total === 0) return <p className="text-xs text-zinc-400">{t("noAgents")}</p>;
      return (
        <div className="space-y-1.5 text-xs">
          {selectedAgents.length > 0 && <Row label={t("agents")} value={t("countValue", { count: selectedAgents.length })} />}
          {selectedSkills.length > 0 && <Row label={t("skills")} value={t("countValue", { count: selectedSkills.length })} />}
          {selectedHooks.length > 0 && <Row label={t("hooks")} value={t("countValue", { count: selectedHooks.length })} />}
        </div>
      );
    }

    case "platform": {
      const { platformId } = data.platform;
      if (!platformId) return <p className="text-xs text-zinc-400">{t("noPlatform")}</p>;
      return (
        <div className="text-xs">
          <Row label={t("platform")} value={mapLabel("platformMap", platformId)} />
        </div>
      );
    }

    case "os": {
      const { osId } = data.os;
      if (!osId) return <p className="text-xs text-zinc-400">{t("noOs")}</p>;
      return (
        <div className="text-xs">
          <Row label={t("os")} value={mapLabel("osMap", osId)} />
        </div>
      );
    }

    case "env": {
      const { authMethod, envVars } = data.env;
      const envCount = Object.values(envVars).filter(Boolean).length;
      return (
        <div className="space-y-1.5 text-xs">
          <Row label={t("authMethod")} value={mapLabel("authMethodMap", authMethod)} />
          {envCount > 0 && <Row label={t("envVars")} value={t("envCountValue", { count: envCount })} />}
        </div>
      );
    }

    case "roi": {
      const { result } = data.roi;
      if (!result) return <p className="text-xs text-zinc-400">{t("noRoi")}</p>;
      return (
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-zinc-500">{t("savings")}</span>
            <span className="font-semibold text-emerald-700">₩{result.savings.toLocaleString()}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-zinc-500">{t("savingsRatio")}</span>
            <span className="font-semibold text-emerald-700">{Math.round(result.savingsRatio * 100)}%</span>
          </div>
        </div>
      );
    }

    case "confirm":
      return (
        <p className="rounded-lg bg-zinc-50 p-3 text-xs text-zinc-500">
          {t("confirm")}
        </p>
      );

    default:
      return null;
  }
}
