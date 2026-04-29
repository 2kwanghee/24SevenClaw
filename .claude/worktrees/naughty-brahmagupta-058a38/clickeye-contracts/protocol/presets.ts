/**
 * ClickEye 프리셋 & 성숙도 평가 타입 정의
 * 기본 프리셋 기능 + 성숙도 기반 프리셋 추천
 */

// === 성숙도 레벨 ===

export type MaturityLevel = 'starter' | 'intermediate' | 'advanced';

// === 프리셋 프로필 ===

export interface PresetProfile {
  id: string;
  name: string;
  slug: string;
  maturity_level: MaturityLevel;
  solution_types: string[];
  default_agents: string[];
  default_skills: string[];
  default_pipelines: string[];
  description: string;
  is_system?: boolean;
}

// === 성숙도 평가 ===

export interface MaturityQuestion {
  id: string;
  text: string;
  category: 'team' | 'process' | 'tooling' | 'ci' | 'ai';
  weight: number;
  options: MaturityOption[];
}

export interface MaturityOption {
  label: string;
  score: number;
}

export interface MaturityAssessmentRequest {
  answers: Record<string, number>;
}

export interface MaturityAssessmentResponse {
  level: MaturityLevel;
  score: number;
  recommended_preset_id?: string;
  reasoning: string;
}

// === 자연어 설정 ===

export interface NaturalLanguageConfigRequest {
  text: string;
  project_id?: string;
}

export interface NaturalLanguageConfigResponse {
  suggested_agents: string[];
  suggested_skills: string[];
  suggested_pipelines: string[];
  /** 신뢰도 [0.0, 1.0] */
  confidence: number;
  reasoning: string;
}
