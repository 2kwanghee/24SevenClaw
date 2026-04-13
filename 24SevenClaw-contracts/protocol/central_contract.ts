/**
 * 24SevenClaw 중앙 실행 계약 관리 타입 정의
 * 중앙 레포(private)에서 settings, skills, agents, pipelines 계약을 관리하고
 * 고객 프로젝트에 배포. 허용된 필드만 오버라이드 가능.
 */

// === 계약 소스 & 타입 ===

export type ContractSource = 'central' | 'custom';

export type ContractType = 'settings' | 'skill' | 'agent' | 'pipeline';

// === 중앙 계약 ===

export interface CentralContract {
  id: string;
  slug: string;
  contract_type: ContractType;
  source: ContractSource;
  version: string;
  content: Record<string, unknown>;
  is_locked: boolean;
  allowed_overrides: string[];
  created_at?: string;
  updated_at?: string;
}

// === 고객 오버라이드 ===

export interface CustomerContractOverride {
  id: string;
  project_id: string;
  central_contract_id: string;
  override_content: Record<string, unknown>;
  approved_by: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

// === 계약 감사 로그 ===

export type ContractChangeType = 'create' | 'update' | 'delete' | 'apply' | 'override' | 'sync';

export interface ContractAuditEntry {
  id: string;
  contract_id: string | null;
  override_id: string | null;
  actor_id: string;
  change_type: ContractChangeType;
  diff_snapshot: Record<string, unknown> | null;
  created_at: string;
}

// === 에이전트 동기화 페이로드 ===

export interface ContractSyncPayload {
  project_id: string;
  contracts: ContractSyncItem[];
}

export interface ContractSyncItem {
  slug: string;
  contract_type: ContractType;
  version: string;
  content: Record<string, unknown>;
  overrides: Record<string, unknown>;
}
