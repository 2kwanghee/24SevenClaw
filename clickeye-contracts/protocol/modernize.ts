/**
 * ClickEye Modernize 6단계 워크플로 Phase 타입 정의
 * 기존 ModernizeSession.status(pending→cloning→analyzing→recommending→ready→finalized)
 * 파이프라인과 병행 도입되는 축 — 사용자에게 노출되는 위저드 단계를 표현한다.
 * Python protocol.py 와 반드시 동기화 유지.
 */

// === Phase ===

export type ModernizePhase =
  | 'asis'
  | 'requirements'
  | 'tobe'
  | 'plan'
  | 'preflight'
  | 'execute';

export const MODERNIZE_PHASE_ORDER: ModernizePhase[] = [
  'asis',
  'requirements',
  'tobe',
  'plan',
  'preflight',
  'execute',
];

// === 스택 서술자 (As-Is / To-Be 공용) ===

export interface StackDescriptor {
  db_type: string | null;
  db_version: string | null;
  runtime: string | null;
  runtime_version: string | null;
  framework: string | null;
  framework_version: string | null;
  infra: string | null;
  extra: Record<string, unknown>;
}

// === requirements phase 산출물 내용 ===

export interface RequirementsArtifactContent {
  as_is_stack: StackDescriptor;
  to_be_stack: StackDescriptor;
  notes_md: string | null;
}

// === 단계별 산출물 (영속 레코드) ===

export interface ModernizePhaseArtifact {
  id: string;
  session_id: string;
  phase: ModernizePhase;
  artifact_type: string;
  content_md: string | null;
  content_json: Record<string, unknown> | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

// === Pre-flight 게이트 (Phase 5) ===
// `preflight_review` artifact 의 content_json 구조. 실행(Phase 6) 직전 계획을
// 영향도·위험 관점에서 점검하고, block 항목이 남아 있으면 승인(approve)이 불가능하다.

export type PreflightVerdict = 'pass' | 'warn' | 'block';

export interface PreflightChecklistItem {
  key: string;
  title: string;
  verdict: PreflightVerdict;
  detail_md: string;
  requires_manual_ack: boolean;
}

export interface PreflightReviewContent {
  checklist: PreflightChecklistItem[];
  overall_verdict: PreflightVerdict;
  acknowledged_high_risk: boolean;
  generated_at: string;
}
