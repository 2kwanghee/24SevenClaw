/**
 * 산출물(Artifact) 상태 관리 타입 정의
 * Draft → Reviewed → Revised → Approved → In Development → Validated → Released
 */

// === 산출물 상태 ===

export type ArtifactStatus =
  | 'draft'
  | 'reviewed'
  | 'revised'
  | 'approved'
  | 'in_development'
  | 'validated'
  | 'released';

// === 허용된 상태 전이 맵 ===

export const ARTIFACT_TRANSITIONS: Record<ArtifactStatus, ArtifactStatus[]> = {
  draft: ['reviewed'],
  reviewed: ['revised', 'approved'],
  revised: ['reviewed'],
  approved: ['in_development'],
  in_development: ['validated'],
  validated: ['released', 'in_development'],
  released: [],
};

// === 상태 전이 요청/응답 ===

export interface ArtifactTransitionRequest {
  target_status: ArtifactStatus;
  actor_type: 'user' | 'agent' | 'system';
  actor_id?: string;
  message?: string;
}

export interface ArtifactMeta {
  created_by_ai?: string;
  reviewed_by_ai?: string;
  last_transition_at?: string;
  revision_count: number;
}

export interface ArtifactEventPayload {
  artifact_id: string;
  event_type: 'status_transition';
  old_status: ArtifactStatus;
  new_status: ArtifactStatus;
  actor_type: 'user' | 'agent' | 'system';
  actor_id?: string;
  message?: string;
  timestamp: string;
}
