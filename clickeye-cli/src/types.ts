/** 프로젝트 유형 */
export type ProjectType = "webapp" | "rest-api" | "fullstack" | "custom";

/** 기술 스택 프리셋 ID */
export type StackPreset =
  | "fastapi-nextjs"
  | "django-react"
  | "express-vue"
  | "nestjs-nextjs"
  | "flask-react"
  | "custom";

/** 에이전트 ID */
export type AgentId =
  | "backend"
  | "frontend"
  | "uiux"
  | "devops"
  | "fullstack"
  | "harness";

/** 워크플로우 옵션 ID */
export type WorkflowId =
  | "tdd"
  | "ai-critique"
  | "linear"
  | "ralph-loop"
  | "harness-gate";

/** Step 1: 프로젝트 기본 정보 */
export interface ProjectInfo {
  name: string;
  type: ProjectType;
  stack: StackPreset;
}

/** Step 2: 에이전트 선택 */
export interface AgentSelection {
  agents: AgentId[];
}

/** Step 3: 워크플로우 옵션 (Week 2에서 구현) */
export interface WorkflowSelection {
  workflows: WorkflowId[];
}

/** 전체 init 옵션 */
export interface InitOptions {
  project: ProjectInfo;
  agents: AgentSelection;
  workflows?: WorkflowSelection;
}

/** 카탈로그 에이전트 항목 */
export interface CatalogAgent {
  id: AgentId;
  name: string;
  description: string;
  outputFile: string;
  template: string;
  required?: boolean;
}

/** 카탈로그 스택 항목 */
export interface CatalogStack {
  id: StackPreset;
  name: string;
  backend: string;
  frontend: string;
  test: { backend: string; frontend: string };
  lint: { backend: string; frontend: string };
  typecheck: { backend: string; frontend: string };
}
