/**
 * ClickEye Agent ↔ Cloud WebSocket 메시지 타입 정의
 * 양쪽(api, agent, web) 모두 이 타입을 참조
 */

// === 메시지 타입 ===

export type AgentMessageType =
  | 'agent.register'
  | 'agent.heartbeat'
  | 'agent.status'
  | 'agent.log'
  | 'agent.result';

export type CommandMessageType =
  | 'command.setup_env'
  | 'command.deploy_ticket'
  | 'command.build'
  | 'command.run'
  | 'command.run_task' // CE-301: 위치 무관 Runner 태스크 실행 (payload=RunnerTaskPayload)
  | 'command.stop'
  | 'command.destroy_env'
  | 'config.update'
  // TODO(범위 밖): contract_service.py:305 는 'contract.sync' 문자열을 사용 — 계약면 불일치. 별도 티켓에서 통일.
  | 'command.contract_sync';

export type MessageType = AgentMessageType | CommandMessageType | 'error';

// === 공통 Envelope ===

export interface Message<T = unknown> {
  id: string;
  type: MessageType;
  timestamp: string;
  payload: T;
  signature: string;
}

// === Agent → Cloud 페이로드 ===

export interface RegisterPayload {
  registration_token: string;
  hostname: string;
  os: string;
  docker_version: string;
  agent_version: string;
  capabilities: string[];
}

export interface HeartbeatPayload {
  status: 'idle' | 'busy' | 'error';
  uptime_seconds?: number;
  hostname?: string;
  os?: string;
  agent_version?: string;
  system?: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent: number;
  };
  environments?: EnvironmentStatus[];
  active_tasks?: string[];
}

export interface EnvironmentStatus {
  project_id: string;
  status: 'running' | 'stopped' | 'error' | 'creating';
  containers: number;
  uptime_seconds: number;
}

export interface StatusPayload {
  event: string;
  project_id: string;
  // 상관관계 키 — Runner 태스크(command.run_task, CE-301)의 task_id 와 동일 값. 진행 상태를 태스크에 귀속.
  task_id?: string;
  progress?: number;
  message?: string;
  detail?: Record<string, unknown>;
}

export interface LogPayload {
  project_id: string;
  // 상관관계 키 — Runner 태스크(command.run_task)의 task_id. 로그 스트리밍을 태스크에 귀속.
  task_id?: string;
  level: 'info' | 'warn' | 'error';
  source: 'docker' | 'claude' | 'git' | 'build' | 'agent';
  message: string;
  truncated?: boolean;
}

export interface ResultPayload {
  task_id: string;
  ticket_id?: string;
  status: 'completed' | 'failed' | 'partial';
  summary: string;
  // CE-301: 러너 실행 팔·인증 모드 회계 — LLM 게이트웨이+원장(CE-299)이 구독 시트/조직 키 비용을 구분 집계.
  target?: 'cloud' | 'desktop';
  auth_mode?: 'subscription_seat' | 'org_api_key';
  changes?: {
    files_created: string[];
    files_modified: string[];
    files_deleted: string[];
    git_commit?: string;
    git_branch?: string;
  };
  metrics?: {
    duration_ms: number;
    tokens_used?: number;
  };
}
