/**
 * Cloud → Agent 명령 페이로드 타입
 */

// === 환경 프로비저닝 ===

export interface SetupEnvPayload {
  project_id: string;
  project_name: string;
  environment: {
    template: string;
    agents: AgentConfig[];
    skills: SkillConfig[];
    mcps: McpConfig[];
    claude?: {
      version: string;
      api_key_env: string;
    };
  };
  git?: {
    init: boolean;
    remote_url?: string;
    branch?: string;
  };
}

export interface AgentConfig {
  id: string;
  name: string;
  image: string;
  config: Record<string, unknown>;
}

export interface SkillConfig {
  id: string;
  name: string;
  image: string;
  config: Record<string, unknown>;
}

export interface McpConfig {
  id: string;
  name: string;
  image: string;
  config: Record<string, unknown>;
}

// === 티켓 전달 ===

export interface DeployTicketPayload {
  ticket_id: string;
  project_id: string;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  acceptance_criteria?: string[];
  context?: {
    related_files?: string[];
    branch?: string;
  };
}

// === 빌드/실행 ===

export interface BuildPayload {
  project_id: string;
  build_type: 'full' | 'incremental';
  command: string;
  env_vars?: Record<string, string>;
  stream_logs?: boolean;
}

export interface RunPayload {
  project_id: string;
  command: string;
  port?: number;
  env_vars?: Record<string, string>;
}

export interface StopPayload {
  project_id: string;
  target: 'all' | 'build' | 'service';
  force?: boolean;
}

export interface DestroyEnvPayload {
  project_id: string;
  keep_git?: boolean;
  keep_data?: boolean;
}

// === 설정 변경 ===

export interface ConfigUpdatePayload {
  project_id: string;
  changes: ConfigChange[];
}

export interface ConfigChange {
  action: 'add' | 'remove' | 'update';
  target: 'agent' | 'skill' | 'mcp';
  id: string;
  config?: Record<string, unknown>;
}
