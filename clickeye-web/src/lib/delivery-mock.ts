/**
 * 딜리버리 콘솔 목업(샘플) 픽스처.
 * 실데이터가 비어 있어도 화면(A~F)을 채워 시각 확인하기 위한 클라이언트 전용 데이터.
 * api-client 실제 타입을 그대로 사용하며 타입 캐스팅(as) 없이 통과해야 한다.
 */
import type {
  GovernancePolicyResponse,
  LinearTeamState,
  LlmProjectUsageSummary,
  OrchestratorSessionListResponse,
  OrchestratorSessionResponse,
  ProjectResponse,
  ReviewRoundResponse,
  SessionSummaryResponse,
  SubTaskResponse,
} from "@/lib/api-client";

// --- 수주건 ---

export const mockProject: ProjectResponse = {
  id: "mock-engagement-0001",
  owner_id: "mock-owner-0001",
  name: "여신심사 시스템 현대화",
  slug: "yeoshin-simsa-modernization",
  description:
    "레거시 여신심사 코어를 스트랭글러 패턴으로 단계적 현대화하는 SI 딜리버리 수주 건.",
  status: "active",
  settings: {},
  wizard_data: null,
  project_type: "modernization",
  bootstrap_status: "completed",
  pm_profile_id: null,
  prototype_session_id: null,
  last_zip_downloaded_at: "2026-07-18T09:00:00Z",
  last_env_downloaded_at: "2026-07-18T09:05:00Z",
  anthropic_key_status: "fresh",
  linear_key_status: "fresh",
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-19T12:00:00Z",
};

// --- 세션 ---

const session1: OrchestratorSessionResponse = {
  id: "mock-session-a",
  project_id: mockProject.id,
  title: "여신 한도 재계산 모듈",
  description: "레거시 한도 재계산 로직을 신규 서비스로 분리한다.",
  phase: "reviewing",
  created_by: "mock-pm",
  prompt_template: null,
  risk_flags: ["security"],
  analysis_result: null,
  created_at: "2026-07-15T00:00:00Z",
  updated_at: "2026-07-19T10:00:00Z",
};

const session2: OrchestratorSessionResponse = {
  id: "mock-session-b",
  project_id: mockProject.id,
  title: "심사 이력 조회 API",
  description: "심사 이력 조회 엔드포인트를 신규 API로 구현한다.",
  phase: "drafting",
  created_by: "mock-pm",
  prompt_template: null,
  risk_flags: [],
  analysis_result: null,
  created_at: "2026-07-17T00:00:00Z",
  updated_at: "2026-07-19T09:00:00Z",
};

export const mockSessions: OrchestratorSessionListResponse = {
  items: [session1, session2],
  total: 2,
};

// --- 서브태스크 (session1 기준) ---
// depends_on 은 다른 서브태스크의 title 을 참조한다(대시보드 의존성 계산 규약).

const T_ARCH = "여신 도메인 아키텍처 설계";
const T_BACKEND = "한도 재계산 백엔드 서비스";
const T_FRONTEND = "심사 대시보드 프론트엔드";
const T_QA = "통합 회귀 테스트";

const st1: SubTaskResponse = {
  id: "mock-subtask-1",
  session_id: session1.id,
  title: T_ARCH,
  description:
    "## 목표\n스트랭글러 파사드를 정의하고 신규 서비스 경계를 설계한다.\n\n- 도메인 이벤트 모델링\n- 레거시 어댑터 인터페이스 정의",
  assigned_role: "architect",
  status: "approved",
  order_index: 0,
  depends_on: [],
  artifact_id: "mock-artifact-arch",
  result_summary: "파사드 경계와 어댑터 인터페이스 확정",
  linear_identifier: "24S-138",
  linear_issue_id: "mock-linear-138",
  linear_state: "Done",
  created_at: "2026-07-15T01:00:00Z",
  updated_at: "2026-07-18T02:00:00Z",
};

const st2: SubTaskResponse = {
  id: "mock-subtask-2",
  session_id: session1.id,
  title: T_BACKEND,
  description:
    "## 목표\n한도 재계산 서비스를 신규 FastAPI 서비스로 구현한다.\n\n- 재계산 규칙 엔진\n- 레거시 데이터 마이그레이션 어댑터",
  assigned_role: "backend",
  status: "in_progress",
  order_index: 1,
  depends_on: [T_ARCH],
  artifact_id: "mock-artifact-backend",
  result_summary: null,
  linear_identifier: "24S-142",
  linear_issue_id: "mock-linear-142",
  linear_state: "In Progress",
  created_at: "2026-07-15T01:10:00Z",
  updated_at: "2026-07-19T08:30:00Z",
};

const st3: SubTaskResponse = {
  id: "mock-subtask-3",
  session_id: session1.id,
  title: T_FRONTEND,
  description:
    "## 목표\n심사 대시보드에서 재계산 결과를 조회/시각화한다.\n\n- 결과 요약 카드\n- 히스토리 타임라인",
  assigned_role: "frontend",
  status: "in_review",
  order_index: 2,
  depends_on: [T_BACKEND],
  artifact_id: null,
  result_summary: null,
  linear_identifier: "24S-143",
  linear_issue_id: "mock-linear-143",
  linear_state: "In Review",
  created_at: "2026-07-15T01:20:00Z",
  updated_at: "2026-07-19T09:40:00Z",
};

const st4: SubTaskResponse = {
  id: "mock-subtask-4",
  session_id: session1.id,
  title: T_QA,
  description:
    "## 목표\n레거시 대비 회귀 동등성을 검증하는 통합 테스트를 작성한다.",
  assigned_role: "qa",
  status: "pending",
  order_index: 3,
  depends_on: [T_BACKEND],
  artifact_id: null,
  result_summary: null,
  linear_identifier: "24S-145",
  linear_issue_id: "mock-linear-145",
  linear_state: "Todo",
  created_at: "2026-07-15T01:30:00Z",
  updated_at: "2026-07-18T05:00:00Z",
};

// 미연동(linear_issue_id=null) — "미연동" 컬럼 + "Linear에 이슈 등록" 버튼 시연
const st5: SubTaskResponse = {
  id: "mock-subtask-5",
  session_id: session1.id,
  title: "보안 취약점 점검",
  description:
    "## 목표\n한도 재계산 경로의 권한/입력 검증 취약점을 점검한다.",
  assigned_role: "security",
  status: "pending",
  order_index: 4,
  depends_on: [T_BACKEND],
  artifact_id: null,
  result_summary: null,
  linear_identifier: null,
  linear_issue_id: null,
  linear_state: null,
  created_at: "2026-07-15T01:40:00Z",
  updated_at: "2026-07-15T01:40:00Z",
};

const st6: SubTaskResponse = {
  id: "mock-subtask-6",
  session_id: session1.id,
  title: "배포 파이프라인 구성",
  description:
    "## 목표\n신규 서비스의 무중단 배포 파이프라인을 구성한다.",
  assigned_role: "devops",
  status: "pending",
  order_index: 5,
  depends_on: [T_ARCH],
  artifact_id: null,
  result_summary: null,
  linear_identifier: null,
  linear_issue_id: null,
  linear_state: null,
  created_at: "2026-07-15T01:50:00Z",
  updated_at: "2026-07-15T01:50:00Z",
};

export const mockSummary: SessionSummaryResponse = {
  session: session1,
  subtasks: [st1, st2, st3, st4, st5, st6],
  phase_history: [],
};

// --- Linear 팀 상태(컬럼) ---

export const mockTeamStates: LinearTeamState[] = [
  { name: "Backlog", type: "backlog", color: "#95a2b3" },
  { name: "Todo", type: "unstarted", color: "#e2c08d" },
  { name: "In Progress", type: "started", color: "#f2c94c" },
  { name: "In Review", type: "started", color: "#5e6ad2" },
  { name: "Done", type: "completed", color: "#4cb782" },
];

// --- LLM 사용량 원장 집계 (비용 카드 D) ---
// 정직성: 구독 시트는 정액이라 cost=null(미산정), 조직 API 키만 종량 과금.

export const mockLedgerSummary: LlmProjectUsageSummary = {
  project_id: mockProject.id,
  total_input_tokens: 2_640_000,
  total_output_tokens: 1_640_000,
  total_cost: "11.94",
  by_key_source: [
    {
      key_source: "subscription_seat",
      input_tokens: 2_420_000,
      output_tokens: 1_480_000,
      cost: null,
    },
    {
      key_source: "org_api_key",
      input_tokens: 220_000,
      output_tokens: 160_000,
      cost: "11.94",
    },
  ],
};

// --- 리뷰 라운드 ---

export const mockReviewRounds: ReviewRoundResponse[] = [
  {
    id: "mock-round-1",
    session_id: session1.id,
    subtask_id: st2.id,
    round_number: 1,
    status: "review_completed",
    main_ai_role: "Claude Code · 구현",
    draft_content:
      "def recalc_limit(applicant):\n    # 신규 규칙 엔진 기반 한도 재계산\n    return engine.evaluate(applicant)",
    sub_ai_role: "Gemini · 리뷰",
    review_type: "code_review",
    review_content:
      "규칙 엔진 분리가 명확합니다. 경계 케이스(소득 0) 처리와 감사 로그만 보완하면 병합 가능합니다.",
    review_score: 8.7,
    diff_summary: "한도 재계산 서비스 신규 3파일 · +214 / -0",
    merged_content: null,
    merge_strategy: null,
    created_at: "2026-07-19T08:00:00Z",
    updated_at: "2026-07-19T08:20:00Z",
  },
  {
    id: "mock-round-2",
    session_id: session1.id,
    subtask_id: st3.id,
    round_number: 2,
    status: "review_completed",
    main_ai_role: "Claude Code · 구현",
    draft_content:
      "export function ResultSummary({ data }: ResultSummaryProps) {\n  return <section>{/* ... */}</section>;\n}",
    sub_ai_role: "Gemini · 리뷰",
    review_type: "code_review",
    review_content:
      "접근성 라벨 누락과 로딩 상태 미처리가 있습니다. 재작업 후 재검토가 필요합니다.",
    review_score: 6.2,
    diff_summary: "대시보드 요약 카드 2파일 · +96 / -12",
    merged_content: null,
    merge_strategy: null,
    created_at: "2026-07-19T09:10:00Z",
    updated_at: "2026-07-19T09:35:00Z",
  },
];

// --- 거버넌스 정책 (머지 게이트) ---

export const mockGovernancePolicy: GovernancePolicyResponse = {
  governance_enabled: true,
  gate_rules: [
    { key: "contract-drift", label: "차단", mode: "block", enabled: true },
    { key: "ticket-ref", label: "차단", mode: "block", enabled: true },
    { key: "plan-trace", label: "권고", mode: "warn", enabled: true },
  ],
  high_risk: {
    prefixes: ["clickeye-contracts/", "clickeye-infra/"],
    patterns: ["*auth*", "*security*"],
  },
  toggles: {
    FLOWOPS_GOVERNANCE: true,
    FLOWOPS_GOVERNANCE_CONTRACT: true,
    FLOWOPS_GOVERNANCE_TICKET: true,
    FLOWOPS_GOVERNANCE_TRACE: true,
  },
  risk_demote_to_pr: true,
  source_note: "목업 데이터 — 실제 API 응답이 아닙니다",
};
