import inquirer from "inquirer";
import chalk from "chalk";
import { apiClient } from "../../api/client.js";
import type { WizardState } from "../state.js";

const INDUSTRY_CHOICES = [
  "SaaS / 소프트웨어",
  "이커머스 / 리테일",
  "금융 / 핀테크",
  "헬스케어",
  "교육 / 에듀테크",
  "미디어 / 콘텐츠",
  "제조 / 물류",
  "기타",
];

const BUSINESS_TYPE_CHOICES = ["B2B", "B2C", "B2B2C", "내부 도구"];

interface OrgResponse {
  id: string;
}

interface SessionResponse {
  id: string;
}

export async function step00Company(state: WizardState): Promise<WizardState> {
  console.log(chalk.bold("\n🏢 Step 0 — 회사 & 솔루션 정보\n"));

  const answers = await inquirer.prompt<{
    companyName: string;
    industry: string;
    techStack: string;
    mainProduct: string;
    businessType: string;
    solutionPrompt: string;
    enableAutoDecompose: boolean;
  }>([
    {
      type: "input",
      name: "companyName",
      message: "회사명:",
      default: state.company.companyName || undefined,
      validate: (v: string) => v.trim().length > 0 || "회사명을 입력해 주세요",
    },
    {
      type: "list",
      name: "industry",
      message: "업종:",
      choices: INDUSTRY_CHOICES,
      default: state.company.industry || INDUSTRY_CHOICES[0],
    },
    {
      type: "input",
      name: "techStack",
      message: "기술 스택 (쉼표 구분, 예: React, FastAPI, PostgreSQL):",
      default: state.company.techStack.join(", ") || undefined,
    },
    {
      type: "input",
      name: "mainProduct",
      message: "주요 제품/서비스 설명:",
      default: state.company.mainProduct || undefined,
    },
    {
      type: "list",
      name: "businessType",
      message: "비즈니스 유형:",
      choices: BUSINESS_TYPE_CHOICES,
      default: state.company.businessType || BUSINESS_TYPE_CHOICES[0],
    },
    {
      type: "input",
      name: "solutionPrompt",
      message: "만들고 싶은 AI 솔루션을 설명해 주세요:",
      default: state.company.solutionPrompt || undefined,
      validate: (v: string) =>
        v.trim().length > 10 || "솔루션 설명을 10자 이상 입력해 주세요",
    },
    {
      type: "confirm",
      name: "enableAutoDecompose",
      message: "솔루션 자동 분해(Auto Decompose) 활성화:",
      default: state.company.enableAutoDecompose,
    },
  ]);

  const techStack = answers.techStack
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const org = await apiClient.post<OrgResponse>("/api/v1/organizations/", {
    company_name: answers.companyName,
    industry: answers.industry,
    tech_stack: techStack,
    main_product: answers.mainProduct,
    business_type: answers.businessType,
  });

  const session = await apiClient.post<SessionResponse>(
    "/api/v1/prototype-sessions/",
    {
      organization_id: org.id,
      solution_prompt: answers.solutionPrompt,
      tech_stack: techStack,
      industry: answers.industry,
    },
  );

  return {
    ...state,
    organizationId: org.id,
    sessionId: session.id,
    currentStep: 1,
    company: {
      companyName: answers.companyName,
      industry: answers.industry,
      techStack,
      mainProduct: answers.mainProduct,
      businessType: answers.businessType,
      solutionPrompt: answers.solutionPrompt,
      enableAutoDecompose: answers.enableAutoDecompose,
    },
  };
}
