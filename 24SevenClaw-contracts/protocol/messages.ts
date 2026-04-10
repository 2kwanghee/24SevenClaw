/**
 * 24SevenClaw Agent ↔ Cloud WebSocket 메시지 타입 정의
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
  | 'command.stop'
  | 'command.destroy_env'
  | 'config.update';

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
  task_id?: string;
  progress?: number;
  message?: string;
  detail?: Record<string, unknown>;
}

export interface LogPayload {
  project_id: string;
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
