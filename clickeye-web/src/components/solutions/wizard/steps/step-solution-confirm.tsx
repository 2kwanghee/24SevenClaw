"use client";

import { ClipboardCheck, Building2, Bot, Terminal, KeyRound, UserCircle2, Cpu } from "lucide-react";
import { useTranslations } from "next-intl";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";

interface SummaryRowProps {
  label: string;
  value: string;
}

function SummaryRow({ label, value }: SummaryRowProps) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="shrink-0 text-xs text-zinc-500">{label}</span>
      <span className="text-right text-xs text-zinc-700">{value}</span>
    </div>
  );
}

export function StepSolutionConfirm() {
  const t = useTranslations("wizard.step7.simpleConfirm");
  const data = useSolutionWizardStore((s) => s.data);

  const businessTypeLabels: Record<string, string> = {
    b2b: "B2B",
    b2c: "B2C",
    b2b2c: "B2B2C",
    internal: t("businessTypeInternal"),
  };
  const platformLabels: Record<string, string> = {
    "claude-code": "Claude Code",
    "gemini-cli": "Gemini CLI",
    cursor: "Cursor",
    codex: "Codex",
  };
  const solutionTypeLabels: Record<string, string> = {
    saas: "SaaS",
    "rest-api": "REST API",
    fullstack: t("solutionTypeFullstack"),
    "internal-tool": t("solutionTypeInternalTool"),
    mvp: "MVP",
    custom: t("solutionTypeCustom"),
  };

  const { company, prototypes, pm, agents, platform, env } = data;

  const selectedProto = prototypes.generatedPrototypes.find(
    (p) => p.id === prototypes.selectedPrototypeId,
  );

  const envKeyCount = Object.keys(env.envVars).length;

  return (
    <div className="space-y-4">
      {/* 회사 정보 */}
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-700">
          <Building2 className="h-4 w-4 text-emerald-600" />
          {t("sectionCompany")}
        </h3>
        <div className="space-y-2">
          <SummaryRow label={t("companyName")} value={company.companyName || t("noAgents")} />
          <SummaryRow
            label={t("businessType")}
            value={businessTypeLabels[company.businessType ?? ""] ?? t("noAgents")}
          />
          <SummaryRow
            label={t("mainProduct")}
            value={company.mainProduct || t("noAgents")}
          />
          {company.solutionRequest && (
            <div className="mt-2 rounded-lg bg-zinc-50 p-3">
              <p className="text-xs leading-relaxed text-zinc-500">
                {company.solutionRequest.length > 200
                  ? company.solutionRequest.slice(0, 200) + "..."
                  : company.solutionRequest}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 선택된 프로토타입 */}
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-700">
          <Cpu className="h-4 w-4 text-emerald-600" />
          {t("sectionPrototype")}
        </h3>
        {selectedProto ? (
          <div className="space-y-2">
            <SummaryRow label={t("protoName")} value={selectedProto.name} />
            <SummaryRow
              label={t("protoType")}
              value={solutionTypeLabels[selectedProto.solutionType] ?? selectedProto.solutionType}
            />
          </div>
        ) : (
          <p className="text-xs text-zinc-500">{t("noPrototype")}</p>
        )}
      </div>

      {/* PM */}
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-700">
          <UserCircle2 className="h-4 w-4 text-emerald-600" />
          {t("sectionPm")}
        </h3>
        <p className="text-xs text-zinc-500">
          {pm.selectedPmProfileId
            ? t("pmSelected", { id: pm.selectedPmProfileId.slice(0, 8) })
            : t("noPm")}
        </p>
      </div>

      {/* 에이전트 & 스킬 */}
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-700">
          <Bot className="h-4 w-4 text-emerald-600" />
          {t("sectionAgents")}
        </h3>
        <div className="space-y-2">
          <SummaryRow
            label={t("agentsLabel")}
            value={
              agents.selectedAgents.length > 0
                ? `${agents.selectedAgents.join(", ")}`
                : t("noAgents")
            }
          />
          <SummaryRow
            label={t("skillsLabel")}
            value={
              agents.selectedSkills.length > 0
                ? agents.selectedSkills.join(", ")
                : t("noSkills")
            }
          />
        </div>
      </div>

      {/* 플랫폼 */}
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-700">
          <Terminal className="h-4 w-4 text-emerald-600" />
          {t("sectionPlatform")}
        </h3>
        <p className="text-xs text-zinc-500">
          {platform.platformId
            ? platformLabels[platform.platformId] ?? platform.platformId
            : t("noPlatform")}
        </p>
      </div>

      {/* 환경변수 */}
      {envKeyCount > 0 && (
        <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-700">
            <KeyRound className="h-4 w-4 text-emerald-600" />
            {t("sectionEnv")}
          </h3>
          <p className="text-xs text-zinc-500">{t("envCount", { count: envKeyCount })}</p>
        </div>
      )}

      {/* 최종 안내 */}
      <div className="flex flex-col items-center justify-center pt-4 text-center">
        <ClipboardCheck className="mb-3 h-8 w-8 text-emerald-600" />
        <p className="text-sm font-medium text-zinc-950">
          {t("allConfirmed")}
        </p>
        <p className="mt-1 text-xs text-zinc-500">
          {t("submitHint")}
        </p>
      </div>
    </div>
  );
}
