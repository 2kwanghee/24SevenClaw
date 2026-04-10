/**
 * 마스터 PM AI 오케스트레이터 프로토콜 타입 정의
 * 10단계 업무 프로세스: 요청→분해→배정→초안→리뷰→통합→검증→승인→전이→완료
 */

// === 오케스트레이션 단계 (10단계) ===

export type OrchestratorPhase =
  | 'requested'      // 1. 요청 접수
  | 'decomposed'     // 2. 작업 분해
  | 'assigned'       // 3. AI 팀 배정
  | 'drafting'       // 4. 초안 작성
  | 'reviewing'      // 5. 리뷰
  | 'integrating'    // 6. 통합
  | 'validating'     // 7. 검증
  | 'approved'       // 8. 승인
  | 'transitioning'  // 9. 전이 (산출물 상태 변경)
  | 'completed';     // 10. 완료

// === 단계 전이 맵 ===

export const ORCHESTRATOR_TRANSITIONS: Record<OrchestratorPhase, OrchestratorPhase[]> = {
  requested: ['decomposed'],
  decomposed: ['assigned'],
  assigned: ['drafting'],
  drafting: ['reviewing'],
  reviewing: ['integrating', 'drafting'],   // 리뷰 실패 시 초안 재작성
  integrating: ['validating'],
  validating: ['approved', 'integrating'],  // 검증 실패 시 재통합
  approved: ['transitioning'],
  transitioning: ['completed'],
  completed: [],
};

// === AI 에이전트 역할 ===

export type AgentRole =
  | 'architect'   // 아키텍처 설계
  | 'frontend'    // 프론트엔드 개발
  | 'backend'     // 백엔드 개발
  | 'qa'          // 품질 보증
  | 'security'    // 보안 검토
  | 'devops'      // 인프라/배포
  | 'reviewer';   // 코드 리뷰

// === 서브태스크 상태 ===

export type SubTaskStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'blocked';

// === 서브태스크 ===

export interface SubTask {
  id: string;
  session_id: string;
  title: string;
  description?: string;
  assigned_role: AgentRole;
  status: SubTaskStatus;
  order_index: number;
  depends_on?: string[];   // 선행 서브태스크 ID 목록
  artifact_id?: string;    // 연결된 산출물 ID
  result_summary?: string;
  created_at: string;
  updated_at: string;
}

// === 오케스트레이션 세션 ===

export interface OrchestratorSession {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  phase: OrchestratorPhase;
  created_by: string;       // user ID
  prompt_template?: string; // 표준화된 프롬프트 템플릿
  risk_flags: string[];     // 탐지된 리스크
  created_at: string;
  updated_at: string;
}

// === 요청/응답 ===

export interface CreateSessionRequest {
  title: string;
  description?: string;
}

export interface DecomposeRequest {
  hints?: string[];  // 분해 힌트 (선택)
}

export interface AssignRequest {
  overrides?: Record<string, AgentRole>;  // subtask_id → role 수동 지정
}

export interface PhaseTransitionRequest {
  target_phase: OrchestratorPhase;
  message?: string;
}

export interface SessionSummary {
  session: OrchestratorSession;
  subtasks: SubTask[];
  phase_history: PhaseEvent[];
}

// === 단계 변경 이벤트 ===

export interface PhaseEvent {
  id: string;
  session_id: string;
  old_phase: OrchestratorPhase;
  new_phase: OrchestratorPhase;
  actor_type: 'user' | 'agent' | 'system';
  actor_id?: string;
  message?: string;
  created_at: string;
}
