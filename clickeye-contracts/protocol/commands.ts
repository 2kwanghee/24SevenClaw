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

// === 위치 무관 Runner 태스크 실행 (CE-301) ===
// docs/si-factory-transition.md §1.1(실행 계층 균일 추상화) / §2.4·§3.2(하이브리드 러너 패턴) 참조.
// 데스크탑 러너(구독 시트, 주력)와 클라우드 컨테이너(조직 API 키, 폴백)가 **동일하게 소비**하는
// 위치 무관 실행 계약. 발신 주체(컨트롤 플레인)가 task_id를 발급하며, 이후 상태(StatusPayload)·
// 로그(LogPayload)·결과(ResultPayload)가 모두 이 task_id로 상관관계(correlation)를 맺는다.
// TODO(P1/P3, 범위 밖): clickeye-agent 의 DockerHandler 실행 핸들러 스키마를 본 계약에 정합화.

export type RunnerTarget = 'cloud' | 'desktop';

export type RunnerAuthMode = 'subscription_seat' | 'org_api_key';

/**
 * 위치 무관 Runner 태스크 실행 요청.
 * 계약 제약(TS 타입으로 표현 불가 → 소비자 런타임 검증):
 *   - ticket_id / prompt / command 중 **최소 하나 필수**. Python 미러(RunnerTaskPayload)의
 *     `model_validator`가 이 제약을 강제한다(W1).
 */
export interface RunnerTaskPayload {
  // 상관관계 키 — 이 명령을 발급한 컨트롤 플레인이 부여. 이후 status/log/result가 동일 값을 사용.
  task_id: string;
  project_id: string;

  // 실행 위치(팔) — desktop=구독 시트 주력(§2.1), cloud=조직 API 키 폴백.
  target: RunnerTarget;

  // 하이브리드 인증 결정 — 미지정 시 러너가 target 기본값(desktop→구독 시트, cloud→조직 키)을 적용.
  auth_mode?: RunnerAuthMode;

  // 실행 명세 — 아래 셋 중 최소 하나 필수. 위치(cloud/desktop) 무관하게 동일하게 소비된다:
  //   - ticket_id : 작업 단위 = Linear 이슈(§1.1). 러너가 이슈를 조회해 컨텍스트로 실행.
  //   - prompt    : AI 코딩 지시(desktop=`claude -p` 구독 세션 / cloud=컨테이너 내 동일 세션).
  //   - command   : 순수 셸 명령(AI 없이 빌드/스크립트 실행).
  // 조합 근거: ticket_id(+prompt)=이슈 기반 AI 작업 / prompt 단독=ad-hoc AI 작업 /
  //   command 단독=비-AI 실행. TS 인터페이스로 "최소 하나" 제약은 표현 불가 →
  //   소비 핸들러가 런타임 검증한다(P1/P3 범위).
  ticket_id?: string;
  prompt?: string;
  command?: string;

  // 모델 라우팅 힌트(opus/sonnet/haiku). 미지정 시 러너 정책 기본값 적용.
  model?: string;

  // 로그·산출물 스트리밍 정책. 미지정 시 러너 기본값(로그 스트리밍 on, 산출물은 결과에 일괄).
  streaming?: {
    logs?: boolean;
    artifacts?: boolean;
  };

  // 실행 타임아웃(정수 초, seconds). 소수 금지(Python 미러는 int) — 초과 시 러너가 중단 후 result status=failed.
  timeout_seconds?: number;
}
