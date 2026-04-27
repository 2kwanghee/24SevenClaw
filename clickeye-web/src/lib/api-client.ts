const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ApiError {
  detail: string | Array<{ msg: string; loc: unknown[] }>;
}

function extractDetail(detail: ApiError["detail"]): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((e) => e.msg).join(", ");
  }
  return "요청 처리 중 오류가 발생했습니다";
}

class ApiClientError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiClientError";
  }
}

/** fetch 자체가 실패할 때(네트워크 연결 없음, DNS 실패 등) 던지는 에러 */
class NetworkError extends Error {
  constructor(message = "네트워크 연결을 확인해 주세요") {
    super(message);
    this.name = "NetworkError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch (fetchErr) {
    const detail = fetchErr instanceof Error ? fetchErr.message : String(fetchErr);
    console.error(`[api-client] fetch 실패 → ${url}\n`, fetchErr);
    throw new NetworkError(`네트워크 연결을 확인해 주세요 (${detail})`);
  }

  if (!res.ok) {
    const body = (await res.json().catch(() => ({
      detail: "요청 처리 중 오류가 발생했습니다",
    }))) as ApiError;
    throw new ApiClientError(res.status, extractDetail(body.detail));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface RegisterResponse {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  plan: string;
  created_at: string;
}

// --- Preview / Generate ---

export interface FileTreeNode {
  path: string;
  type: "file" | "directory";
  children: FileTreeNode[];
}

export interface PreviewRequest {
  organization: Record<string, unknown>;
  solution: Record<string, unknown>;
  agents: string[];
  skills: string[];
  pipelines: string[];
  platform: Record<string, unknown>;
  pm_slug?: string | null;
}

export interface PreviewResponse {
  file_tree: FileTreeNode[];
  files: Record<string, string>;
}

export interface GenerateRequest extends PreviewRequest {
  env_vars: Record<string, string>;
  hook_ids?: string[];
  os_id?: "wsl2";
}

// --- Projects ---

export interface WizardConfigData {
  organization: Record<string, unknown>;
  solution: Record<string, unknown>;
  agents: Array<{ id: string }>;
  skills: Array<{ id: string }>;
  pipelines: Array<{ id: string }>;
  platform: Record<string, unknown>;
}

export interface ProjectResponse {
  id: string;
  owner_id: string;
  name: string;
  slug: string;
  description: string | null;
  status: "active" | "archived";
  settings: Record<string, unknown>;
  wizard_data: WizardConfigData | null;
  project_type: string | null;
  pm_profile_id: string | null;
  prototype_session_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface RedownloadRequest {
  env_vars: Record<string, string>;
}

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
}

export interface ProjectCreateRequest {
  name: string;
  description?: string;
}

export interface ProjectUpdateRequest {
  name?: string;
  description?: string;
  status?: "active" | "archived";
}

export interface ProjectListParams {
  offset?: number;
  limit?: number;
  search?: string;
  status?: string;
}

export interface ProjectKPIResponse {
  project_name: string;
  generated_at: string;
  automation_rate: number;
  review_acceptance_rate: number;
  avg_phase_duration: PhaseDuration[];
  throughput_per_week: WeeklyThroughput[];
}

export interface PhaseDuration {
  phase: string;
  avg_duration_seconds: number;
  sample_count: number;
}

export interface WeeklyThroughput {
  week_start: string;
  completed_count: number;
}

/**
 * 브라우저에서 Auth.js 세션을 조회하여 최신 Access Token을 가져온다.
 * JWT 콜백이 자동 갱신을 처리하므로 반환되는 토큰은 유효하다.
 */
async function getRefreshedToken(): Promise<string | null> {
  try {
    const res = await fetch("/api/auth/session");
    if (!res.ok) return null;
    const session = await res.json();
    return (session?.accessToken as string) ?? null;
  } catch {
    return null;
  }
}

async function authRequest<T>(
  path: string,
  token: string,
  options: RequestInit = {},
): Promise<T> {
  try {
    return await request<T>(path, {
      ...options,
      headers: {
        Authorization: `Bearer ${token}`,
        ...options.headers,
      },
    });
  } catch (error) {
    // 401 응답 시 세션에서 갱신된 토큰으로 1회 재시도
    if (error instanceof ApiClientError && error.status === 401) {
      const freshToken = await getRefreshedToken();
      if (freshToken && freshToken !== token) {
        return request<T>(path, {
          ...options,
          headers: {
            Authorization: `Bearer ${freshToken}`,
            ...options.headers,
          },
        });
      }
    }
    throw error;
  }
}

export const apiClient = {
  auth: {
    register: (data: RegisterRequest) =>
      request<RegisterResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  projects: {
    list: (token: string, params?: ProjectListParams) => {
      const query = new URLSearchParams();
      if (params?.offset !== undefined) query.set("offset", String(params.offset));
      if (params?.limit !== undefined) query.set("limit", String(params.limit));
      if (params?.search) query.set("search", params.search);
      if (params?.status) query.set("status", params.status);
      const qs = query.toString();
      return authRequest<ProjectListResponse>(
        `/api/v1/projects${qs ? `?${qs}` : ""}`,
        token,
      );
    },

    get: (token: string, projectId: string) =>
      authRequest<ProjectResponse>(`/api/v1/projects/${projectId}`, token),

    create: (token: string, data: ProjectCreateRequest) =>
      authRequest<ProjectResponse>("/api/v1/projects/", token, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (token: string, projectId: string, data: ProjectUpdateRequest) =>
      authRequest<ProjectResponse>(`/api/v1/projects/${projectId}`, token, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    delete: (token: string, projectId: string) =>
      authRequest<void>(`/api/v1/projects/${projectId}`, token, {
        method: "DELETE",
      }),

    preview: (token: string, projectId: string, data: PreviewRequest) =>
      authRequest<PreviewResponse>(
        `/api/v1/projects/${projectId}/preview`,
        token,
        { method: "POST", body: JSON.stringify(data) },
      ),

    /** 프로젝트 생성 전 드래프트 프리뷰 (project ID 불필요) */
    previewDraft: (token: string, data: PreviewRequest) =>
      authRequest<PreviewResponse>(
        "/api/v1/projects/draft/preview",
        token,
        { method: "POST", body: JSON.stringify(data) },
      ),

    /** 프로젝트 생성 전 드래프트 ZIP 다운로드 */
    generateZipDraft: async (
      token: string,
      data: GenerateRequest,
    ): Promise<Blob> => {
      const url = `${API_URL}/api/v1/projects/draft/generate`;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({
          detail: "ZIP 생성 중 오류가 발생했습니다",
        }));
        throw new ApiClientError(res.status, extractDetail(body.detail));
      }
      return res.blob();
    },

    generateZip: async (
      token: string,
      projectId: string,
      data: GenerateRequest,
    ): Promise<Blob> => {
      const url = `${API_URL}/api/v1/projects/${projectId}/generate`;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({
          detail: "ZIP 생성 중 오류가 발생했습니다",
        }));
        throw new ApiClientError(res.status, extractDetail(body.detail));
      }
      return res.blob();
    },

    saveConfig: (
      token: string,
      projectId: string,
      wizardData: WizardConfigData,
    ) =>
      authRequest<{ project_id: string; wizard_data: WizardConfigData; updated_at: string }>(
        `/api/v1/projects/${projectId}/config`,
        token,
        {
          method: "POST",
          body: JSON.stringify({ wizard_data: wizardData }),
        },
      ),

    /** 프로젝트 KPI 조회 */
    kpi: (token: string, projectId: string) =>
      authRequest<ProjectKPIResponse>(
        `/api/v1/projects/${projectId}/kpi`,
        token,
      ),

    /** 프로젝트 리포트 조회 */
    report: (token: string, projectId: string) =>
      authRequest<ProjectReportResponse>(
        `/api/v1/reports/project/${projectId}`,
        token,
      ),

    redownload: async (
      token: string,
      projectId: string,
      data: RedownloadRequest,
    ): Promise<Blob> => {
      const url = `${API_URL}/api/v1/projects/${projectId}/redownload`;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({
          detail: "재다운로드 중 오류가 발생했습니다",
        }));
        throw new ApiClientError(res.status, extractDetail(body.detail));
      }
      return res.blob();
    },
  },
};

// --- Presets ---

export type MaturityLevel = "starter" | "intermediate" | "advanced";

export interface PresetResponse {
  id: string;
  name: string;
  slug: string;
  maturity_level: MaturityLevel;
  solution_types: string[];
  default_agents: string[];
  default_skills: string[];
  default_pipelines: string[];
  description: string | null;
  is_system: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PresetListResponse {
  items: PresetResponse[];
  total: number;
}

export interface PresetListParams {
  offset?: number;
  limit?: number;
  maturity_level?: MaturityLevel;
  solution_type?: string;
}

export interface MaturityOption {
  label: string;
  score: number;
}

export interface MaturityQuestion {
  id: string;
  text: string;
  category: "team" | "process" | "tooling" | "ci" | "ai";
  weight: number;
  options: MaturityOption[];
}

export interface MaturityAssessmentResponse {
  level: MaturityLevel;
  score: number;
  recommended_preset_id: string | null;
  reasoning: string;
}

export interface NaturalLanguageConfigResponse {
  suggested_agents: string[];
  suggested_skills: string[];
  suggested_pipelines: string[];
  confidence: number;
  reasoning: string;
}

// --- Reports ---

export interface ArtifactStatusCount {
  status: string;
  count: number;
}

export interface PhaseTimelineEntry {
  phase: string;
  entered_at: string;
  exited_at: string | null;
  duration_seconds: number | null;
  actor_type: string | null;
  message: string | null;
}

export interface QualityMetrics {
  total_artifacts: number;
  released_artifacts: number;
  avg_review_score: number | null;
  avg_revision_count: number;
  review_rounds_total: number;
  review_completion_rate: number;
}

export interface AITeamActivity {
  role: string;
  title: string;
  status: string;
  event_type: string;
  timestamp: string;
  message: string | null;
}

export interface ProjectReportResponse {
  project_id: string;
  project_name: string;
  project_status: string;
  artifact_status_counts: ArtifactStatusCount[];
  phase_timeline: PhaseTimelineEntry[];
  quality_metrics: QualityMetrics;
  ai_team_activities: AITeamActivity[];
  sessions_total: number;
  subtasks_total: number;
  generated_at: string;
}

// --- Recommend ---

export interface RecommendRequest {
  solution_type: string;
}

export interface RecommendResponse {
  solution_type: string;
  agents: Array<{ id: string; reasoning?: string; [key: string]: unknown }>;
  skills: Array<{ id: string; reasoning?: string; [key: string]: unknown }>;
  pipelines: Array<{ id: string; reasoning?: string; [key: string]: unknown }>;
  summary: string;
}

export const presets = {
  list: (token: string, params?: PresetListParams) => {
    const query = new URLSearchParams();
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.maturity_level) query.set("maturity_level", params.maturity_level);
    if (params?.solution_type) query.set("solution_type", params.solution_type);
    const qs = query.toString();
    return authRequest<PresetListResponse>(
      `/api/v1/presets${qs ? `?${qs}` : ""}`,
      token,
    );
  },

  get: (token: string, presetId: string) =>
    authRequest<PresetResponse>(`/api/v1/presets/${presetId}`, token),

  getQuestions: (token: string) =>
    authRequest<MaturityQuestion[]>("/api/v1/presets/questions", token),

  assess: (token: string, answers: Record<string, number>) =>
    authRequest<MaturityAssessmentResponse>("/api/v1/presets/assess", token, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
};

export const recommend = {
  get: (data: RecommendRequest) =>
    request<RecommendResponse>("/api/v1/recommend", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// --- RBAC ---

export type SystemRole = "superadmin" | "admin" | "member" | "viewer";
export type OrgRole = "org_admin" | "org_member" | "org_viewer";

export interface PermissionsResponse {
  permissions: string[];
  system_role: SystemRole;
}

export interface UserAdminResponse {
  id: string;
  email: string;
  display_name: string;
  system_role: SystemRole;
  is_active: boolean;
  created_at: string;
}

export interface RoleUpdateRequest {
  system_role: SystemRole;
}

export interface OrgMemberResponse {
  id: string;
  user_id: string;
  organization_id: string;
  org_role: OrgRole;
  invited_by: string | null;
  joined_at: string;
  is_active: boolean;
}

export interface OrgMemberAddRequest {
  user_id: string;
  org_role: OrgRole;
}

export interface AuditLogResponse {
  id: string;
  actor_id: string;
  target_user_id: string | null;
  action: string;
  old_value: string | null;
  new_value: string;
  resource: string | null;
  created_at: string;
}

export interface AuditLogParams {
  actor_id?: string;
  target_user_id?: string;
  action?: string;
  limit?: number;
  offset?: number;
}

export const rbac = {
  getPermissions: (token: string) =>
    authRequest<PermissionsResponse>("/api/v1/rbac/permissions", token),

  listUsers: (token: string) =>
    authRequest<UserAdminResponse[]>("/api/v1/admin/users", token),

  updateUserRole: (token: string, userId: string, data: RoleUpdateRequest) =>
    authRequest<UserAdminResponse>(`/api/v1/admin/users/${userId}/role`, token, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  getOrgMembers: (token: string, orgId: string) =>
    authRequest<OrgMemberResponse[]>(
      `/api/v1/organizations/${orgId}/members`,
      token,
    ),

  addOrgMember: (token: string, orgId: string, data: OrgMemberAddRequest) =>
    authRequest<OrgMemberResponse>(
      `/api/v1/organizations/${orgId}/members`,
      token,
      { method: "POST", body: JSON.stringify(data) },
    ),

  removeOrgMember: (token: string, orgId: string, userId: string) =>
    authRequest<void>(
      `/api/v1/organizations/${orgId}/members/${userId}`,
      token,
      { method: "DELETE" },
    ),

  getAuditLog: (token: string, params?: AuditLogParams) => {
    const query = new URLSearchParams();
    if (params?.actor_id) query.set("actor_id", params.actor_id);
    if (params?.target_user_id) query.set("target_user_id", params.target_user_id);
    if (params?.action) query.set("action", params.action);
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    const qs = query.toString();
    return authRequest<AuditLogResponse[]>(
      `/api/v1/admin/audit-log${qs ? `?${qs}` : ""}`,
      token,
    );
  },
};

// --- Organizations ---

export interface OrganizationCreateRequest {
  company_name: string;
  size?: string;
  industry?: string;
  tech_stack?: string[];
  main_product?: string;
  business_type?: string;
  company_description?: string;
}

export interface OrganizationResponse {
  id: string;
  company_name: string;
  size: string | null;
  industry: string | null;
  tech_stack: string[] | null;
  main_product: string | null;
  business_type: string | null;
  company_description: string | null;
  created_at: string;
  updated_at: string;
}

export const organizations = {
  upsert: (token: string, data: OrganizationCreateRequest) =>
    authRequest<OrganizationResponse>("/api/v1/organizations/", token, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  me: (token: string) =>
    authRequest<OrganizationResponse>("/api/v1/organizations/me", token),
};

// --- Solution Wizard v2: Prototype Sessions ---

export interface PrototypeSessionCreateRequest {
  organization_id: string;
  solution_prompt: string;
  tech_stack?: string[];
  industry?: string | null;
}

export interface PrototypeSessionResponse {
  id: string;
  organization_id: string;
  user_id: string;
  solution_prompt: string | null;
  parsed_requirements: Record<string, unknown> | null;
  status: "pending" | "generating" | "completed" | "failed";
  selected_prototype_id: string | null;
  selected_pm_id: string | null;
  current_step: number;
  created_at: string;
  updated_at: string;
}

export interface PrototypeSessionStatusResponse {
  id: string;
  status: string;
  created_at: string;
}

export interface PrototypeSessionUpdateRequest {
  selected_prototype_id?: string | null;
  selected_pm_id?: string | null;
  current_step?: number | null;
}

export interface PrototypeResponse {
  id: string;
  session_id: string;
  variant_index: number;
  title: string;
  description: string | null;
  design_pattern: string | null;
  menu_structure: Record<string, unknown> | null;
  ui_structure: Record<string, unknown> | null;
  color_palette: Record<string, unknown> | null;
  thumbnail_url: string | null;
  figma_file_key: string | null;
  figma_embed_url: string | null;
  status: string;
  tech_stack_tags: string[];
  architecture_pattern: string | null;
  variant_rationale: string | null;
  is_recommended: boolean;
  pros: string[];
  cons: string[];
  created_at: string;
  updated_at: string;
}

export interface PrototypeListResponse {
  items: PrototypeResponse[];
  total: number;
}

/** 세션 기반 PM 추천 응답 단일 항목 */
export interface PMRecommendItemResponse {
  pm_id: string;
  name: string;
  slug: string;
  avatar_url: string | null;
  title: string | null;
  domain: string | null;
  match_score: number;
  reasoning: string;
}

/** POST /prototype-sessions/{id}/recommend-pms 응답 */
export interface SessionRecommendPMsResponse {
  items: PMRecommendItemResponse[];
}

export interface FinalizeRequest {
  project_name: string;
  description?: string | null;
}

export interface FinalizeResponse {
  project_id: string;
  project_name: string;
  session_id: string;
  message: string;
}

export interface GenerateStartResponse {
  message: string;
  session_id: string;
}

export const prototypeSessions = {
  create: (token: string, data: PrototypeSessionCreateRequest) =>
    authRequest<PrototypeSessionResponse>("/api/v1/prototype-sessions/", token, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  list: (token: string, params?: { offset?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    const qs = query.toString();
    return authRequest<PrototypeSessionResponse[]>(
      `/api/v1/prototype-sessions${qs ? `?${qs}` : ""}`,
      token,
    );
  },

  get: (token: string, sessionId: string) =>
    authRequest<PrototypeSessionResponse>(
      `/api/v1/prototype-sessions/${sessionId}`,
      token,
    ),

  update: (token: string, sessionId: string, data: PrototypeSessionUpdateRequest) =>
    authRequest<PrototypeSessionResponse>(
      `/api/v1/prototype-sessions/${sessionId}`,
      token,
      { method: "PATCH", body: JSON.stringify(data) },
    ),

  getStatus: (token: string, sessionId: string) =>
    authRequest<PrototypeSessionStatusResponse>(
      `/api/v1/prototype-sessions/${sessionId}/status`,
      token,
    ),

  getPrototypes: (token: string, sessionId: string) =>
    authRequest<PrototypeListResponse>(
      `/api/v1/prototype-sessions/${sessionId}/prototypes`,
      token,
    ),

  generatePrototypes: (token: string, sessionId: string) =>
    authRequest<GenerateStartResponse>(
      `/api/v1/prototype-sessions/${sessionId}/prototypes/generate`,
      token,
      { method: "POST" },
    ),

  recommendPMs: (token: string, sessionId: string) =>
    authRequest<SessionRecommendPMsResponse>(
      `/api/v1/prototype-sessions/${sessionId}/recommend-pms`,
      token,
      { method: "POST" },
    ),

  finalize: (token: string, sessionId: string, data: FinalizeRequest) =>
    authRequest<FinalizeResponse>(
      `/api/v1/prototype-sessions/${sessionId}/finalize`,
      token,
      { method: "POST", body: JSON.stringify(data) },
    ),

  delete: (token: string, sessionId: string) =>
    authRequest<void>(`/api/v1/prototype-sessions/${sessionId}`, token, {
      method: "DELETE",
    }),

  recommendComponents: (token: string, sessionId: string) =>
    authRequest<RecommendComponentsResponse>(
      `/api/v1/prototype-sessions/${sessionId}/recommend-components`,
      token,
    ),
};

/** GET /prototype-sessions/{id}/recommend-components 응답 */
export interface RecommendComponentsResponse {
  agents: string[];
  skills: string[];
  excluded_agents: string[];
  catalog_entry_slug: string | null;
  reasoning: string | null;
}

// --- Solution Wizard v2: PM Profiles ---

export interface PMProfileResponse {
  id: string;
  name: string;
  slug: string;
  avatar_url: string | null;
  title: string | null;
  description: string | null;
  domain: string | null;
  specialties: string[];
  personality: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  bio_long: string | null;
  years_experience: number | null;
  preferred_solution_types: string[];
  tech_stack_tags: string[];
  industry_tags: string[];
  language: string;
  updated_at: string | null;
}

export interface PMProfileCreateRequest {
  name: string;
  slug: string;
  avatar_url?: string | null;
  title?: string | null;
  description?: string | null;
  domain?: string | null;
  specialties?: string[];
  personality?: Record<string, unknown>;
  is_active?: boolean;
  bio_long?: string | null;
  years_experience?: number | null;
  preferred_solution_types?: string[];
  tech_stack_tags?: string[];
  industry_tags?: string[];
  language?: string;
}

export type PMProfileUpdateRequest = Partial<PMProfileCreateRequest>;

export interface PMCompositionCreateRequest {
  component_type: string;
  component_slug: string;
  component_name: string;
  config?: Record<string, unknown>;
  display_order?: number;
  is_required?: boolean;
}

export interface PMCompositionUpdateRequest {
  component_name?: string;
  config?: Record<string, unknown>;
  display_order?: number;
  is_required?: boolean;
}

export interface PMRecommendationLogResponse {
  id: string;
  session_id: string;
  created_at: string | null;
  input_snapshot: Record<string, unknown>;
  claude_raw: Record<string, unknown> | null;
  final_ranking: Array<Record<string, unknown>>;
  selected_pm_id: string | null;
  latency_ms: number | null;
  is_fallback: boolean;
}

export interface PMRecommendationLogListResponse {
  items: PMRecommendationLogResponse[];
  total: number;
}

export interface PMProfileWithMetrics extends PMProfileResponse {
  usage_count: number;
  completed_projects: number;
  avg_rating: number;
  total_ratings: number;
  like_count: number;
  dislike_count: number;
  success_rate: number;
  avg_completion_days: number;
}

export interface PMProfileListResponse {
  items: PMProfileResponse[];
  total: number;
}

export interface PMRecommendRequest {
  prototype_id: string;
  session_id?: string | null;
}

export interface PMRecommendResponse {
  pm_profile: PMProfileResponse;
  match_score: number;
  reasoning: string | null;
}

export interface PMRecommendListResponse {
  items: PMRecommendResponse[];
}

export interface PMMetricResponse {
  id: string;
  pm_id: string;
  usage_count: number;
  completed_projects: number;
  avg_rating: number;
  total_ratings: number;
  like_count: number;
  dislike_count: number;
  success_rate: number;
  avg_completion_days: number;
}

export interface PMCompositionResponse {
  id: string;
  pm_id: string;
  component_type: string;
  component_slug: string;
  component_name: string;
  config: Record<string, unknown>;
  display_order: number;
  is_required: boolean;
}

export interface PMCompositionGroupedResponse {
  agents: PMCompositionResponse[];
  skills: PMCompositionResponse[];
  hooks: PMCompositionResponse[];
  mcp_servers: PMCompositionResponse[];
  plugins: PMCompositionResponse[];
}

export interface PMRatingCreateRequest {
  session_id: string;
  reaction?: "like" | "dislike";
  rating?: number;
  comment?: string;
}

export interface PMRatingResponse {
  id: string;
  pm_id: string;
  user_id: string;
  session_id: string;
  rating: number;
  reaction: string | null;
  comment: string | null;
  created_at: string;
}

export interface PMRatingListResponse {
  items: PMRatingResponse[];
  total: number;
}

export const pmProfiles = {
  list: (
    token: string,
    params?: { specialty?: string; domain?: string; is_active?: boolean; offset?: number; limit?: number },
  ) => {
    const query = new URLSearchParams();
    if (params?.specialty) query.set("specialty", params.specialty);
    if (params?.domain) query.set("domain", params.domain);
    if (params?.is_active !== undefined)
      query.set("is_active", String(params.is_active));
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    const qs = query.toString();
    return authRequest<PMProfileListResponse>(
      `/api/v1/pm-profiles/${qs ? `?${qs}` : ""}`,
      token,
    );
  },

  get: (token: string, profileId: string) =>
    authRequest<PMProfileWithMetrics>(`/api/v1/pm-profiles/${profileId}`, token),

  recommend: (token: string, data: PMRecommendRequest) =>
    authRequest<PMRecommendListResponse>("/api/v1/pm-profiles/recommend", token, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getComposition: (token: string, profileId: string) =>
    authRequest<PMCompositionGroupedResponse>(
      `/api/v1/pm-profiles/${profileId}/composition`,
      token,
    ),

  createRating: (token: string, profileId: string, data: PMRatingCreateRequest) =>
    authRequest<PMRatingResponse>(`/api/v1/pm-profiles/${profileId}/ratings`, token, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listRatings: (
    token: string,
    profileId: string,
    params?: { offset?: number; limit?: number },
  ) => {
    const query = new URLSearchParams();
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    const qs = query.toString();
    return authRequest<PMRatingListResponse>(
      `/api/v1/pm-profiles/${profileId}/ratings${qs ? `?${qs}` : ""}`,
      token,
    );
  },

  getMetrics: (token: string, profileId: string) =>
    authRequest<PMMetricResponse>(`/api/v1/pm-profiles/${profileId}/metrics`, token),

  // Admin CRUD (pm:manage 권한 필요)
  create: (token: string, data: PMProfileCreateRequest) =>
    authRequest<PMProfileResponse>("/api/v1/pm-profiles/", token, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (token: string, profileId: string, data: PMProfileUpdateRequest) =>
    authRequest<PMProfileResponse>(`/api/v1/pm-profiles/${profileId}`, token, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (token: string, profileId: string) =>
    authRequest<void>(`/api/v1/pm-profiles/${profileId}`, token, {
      method: "DELETE",
    }),

  createComposition: (
    token: string,
    profileId: string,
    data: PMCompositionCreateRequest,
  ) =>
    authRequest<PMCompositionResponse>(
      `/api/v1/pm-profiles/${profileId}/composition`,
      token,
      { method: "POST", body: JSON.stringify(data) },
    ),

  updateComposition: (
    token: string,
    profileId: string,
    compositionId: string,
    data: PMCompositionUpdateRequest,
  ) =>
    authRequest<PMCompositionResponse>(
      `/api/v1/pm-profiles/${profileId}/composition/${compositionId}`,
      token,
      { method: "PUT", body: JSON.stringify(data) },
    ),

  deleteComposition: (
    token: string,
    profileId: string,
    compositionId: string,
  ) =>
    authRequest<void>(
      `/api/v1/pm-profiles/${profileId}/composition/${compositionId}`,
      token,
      { method: "DELETE" },
    ),
};

export const pmMarkdown = {
  get: (token: string, profileId: string): Promise<string> => {
    const url = `${API_URL}/api/v1/pm-profiles/${profileId}/markdown`;
    return fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(async (res) => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Markdown 조회 실패" }));
        throw new ApiClientError(res.status, extractDetail(body.detail));
      }
      return res.text();
    });
  },

  update: (token: string, profileId: string, markdown: string): Promise<PMProfileResponse> => {
    const url = `${API_URL}/api/v1/pm-profiles/${profileId}/from-markdown`;
    return fetch(url, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "text/plain",
      },
      body: markdown,
    }).then(async (res) => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Markdown 업데이트 실패" }));
        throw new ApiClientError(res.status, extractDetail(body.detail));
      }
      return res.json() as Promise<PMProfileResponse>;
    });
  },
};

// --- Registry Admin ---

export interface RegistryItemResponse {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  body_md: string | null;
  version: string;
  image_url: string | null;
  category: string | null;
  is_public: boolean;
  config_schema: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface RegistryItemListResponse {
  items: RegistryItemResponse[];
  total: number;
}

export interface RegistryItemCreateRequest {
  name: string;
  slug: string;
  description?: string | null;
  body_md?: string | null;
  version?: string;
  image_url?: string | null;
  category?: string | null;
  is_public?: boolean;
  config_schema?: Record<string, unknown>;
}

export interface RegistryItemUpdateRequest {
  name?: string;
  description?: string | null;
  body_md?: string | null;
  version?: string;
  image_url?: string | null;
  category?: string | null;
  is_public?: boolean;
  config_schema?: Record<string, unknown>;
}

export interface RegistryListParams {
  category?: string;
  is_public?: boolean;
  offset?: number;
  limit?: number;
}

function makeRegistryClient(resourcePath: string) {
  return {
    list: (token: string, params?: RegistryListParams) => {
      const query = new URLSearchParams();
      if (params?.category) query.set("category", params.category);
      if (params?.is_public !== undefined) query.set("is_public", String(params.is_public));
      if (params?.offset !== undefined) query.set("offset", String(params.offset));
      if (params?.limit !== undefined) query.set("limit", String(params.limit));
      const qs = query.toString();
      return authRequest<RegistryItemListResponse>(
        `/api/v1/admin/registry/${resourcePath}${qs ? `?${qs}` : ""}`,
        token,
      );
    },
    get: (token: string, id: string) =>
      authRequest<RegistryItemResponse>(`/api/v1/admin/registry/${resourcePath}/${id}`, token),
    create: (token: string, data: RegistryItemCreateRequest) =>
      authRequest<RegistryItemResponse>(`/api/v1/admin/registry/${resourcePath}`, token, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (token: string, id: string, data: RegistryItemUpdateRequest) =>
      authRequest<RegistryItemResponse>(`/api/v1/admin/registry/${resourcePath}/${id}`, token, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (token: string, id: string) =>
      authRequest<void>(`/api/v1/admin/registry/${resourcePath}/${id}`, token, {
        method: "DELETE",
      }),
  };
}

export const registryAgents = makeRegistryClient("agents");
export const registrySkills = makeRegistryClient("skills");
export const registryMcpServers = makeRegistryClient("mcp-servers");
export const registryHooks = makeRegistryClient("hooks");

export const adminPMRecommendations = {
  list: (
    token: string,
    params?: {
      session_id?: string;
      is_fallback?: boolean;
      offset?: number;
      limit?: number;
    },
  ) => {
    const query = new URLSearchParams();
    if (params?.session_id) query.set("session_id", params.session_id);
    if (params?.is_fallback !== undefined)
      query.set("is_fallback", String(params.is_fallback));
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    const qs = query.toString();
    return authRequest<PMRecommendationLogListResponse>(
      `/api/v1/admin/pm-recommendations/${qs ? `?${qs}` : ""}`,
      token,
    );
  },
};

// --- Contracts ---

export interface CentralContractResponse {
  id: string;
  slug: string;
  contract_type: string;
  source: string;
  version: string;
  content: Record<string, unknown>;
  description: string | null;
  is_locked: boolean;
  allowed_overrides: string[];
  created_at: string;
  updated_at: string;
}

export interface CentralContractListResponse {
  items: CentralContractResponse[];
  total: number;
}

export interface CentralContractCreateRequest {
  slug: string;
  contract_type: string;
  source: string;
  version?: string;
  content?: Record<string, unknown>;
  description?: string;
  is_locked?: boolean;
  allowed_overrides?: string[];
}

export interface CentralContractUpdateRequest {
  contract_type?: string;
  source?: string;
  version?: string;
  content?: Record<string, unknown>;
  description?: string;
  is_locked?: boolean;
  allowed_overrides?: string[];
}

export interface ContractListParams {
  contract_type?: string;
  offset?: number;
  limit?: number;
}

export interface CustomerContractOverrideResponse {
  id: string;
  project_id: string;
  central_contract_id: string;
  override_content: Record<string, unknown>;
  approved_by: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomerContractOverrideListResponse {
  items: CustomerContractOverrideResponse[];
  total: number;
}

export interface CustomerContractOverrideCreateRequest {
  central_contract_id: string;
  override_content?: Record<string, unknown>;
}

export interface CustomerContractOverrideUpdateRequest {
  override_content: Record<string, unknown>;
}

export interface ContractAuditLogResponse {
  id: string;
  contract_id: string | null;
  override_id: string | null;
  actor_id: string;
  change_type: string;
  diff_snapshot: Record<string, unknown>;
  created_at: string;
}

export interface ContractAuditLogListResponse {
  items: ContractAuditLogResponse[];
  total: number;
}

export interface ContractAuditLogParams {
  contract_id?: string;
  change_type?: string;
  offset?: number;
  limit?: number;
}

export interface ContractSyncResponse {
  synced_count: number;
  agent_ids: string[];
}

export const contracts = {
  list: (token: string, params?: ContractListParams) => {
    const query = new URLSearchParams();
    if (params?.contract_type) query.set("contract_type", params.contract_type);
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    const qs = query.toString();
    return authRequest<CentralContractListResponse>(
      `/api/v1/contracts/${qs ? `?${qs}` : ""}`,  // trailing slash prevents 307 redirect
      token,
    );
  },

  get: (token: string, contractId: string) =>
    authRequest<CentralContractResponse>(`/api/v1/contracts/${contractId}`, token),

  create: (token: string, data: CentralContractCreateRequest) =>
    authRequest<CentralContractResponse>("/api/v1/contracts/", token, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (token: string, contractId: string, data: CentralContractUpdateRequest) =>
    authRequest<CentralContractResponse>(`/api/v1/contracts/${contractId}`, token, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (token: string, contractId: string) =>
    authRequest<void>(`/api/v1/contracts/${contractId}`, token, {
      method: "DELETE",
    }),

  getAuditLog: (token: string, params?: ContractAuditLogParams) => {
    const query = new URLSearchParams();
    if (params?.contract_id) query.set("contract_id", params.contract_id);
    if (params?.change_type) query.set("change_type", params.change_type);
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    const qs = query.toString();
    return authRequest<ContractAuditLogListResponse>(
      `/api/v1/contracts/audit${qs ? `?${qs}` : ""}`,
      token,
    );
  },

  getProjectOverrides: (
    token: string,
    projectId: string,
    params?: { offset?: number; limit?: number },
  ) => {
    const query = new URLSearchParams();
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    const qs = query.toString();
    return authRequest<CustomerContractOverrideListResponse>(
      `/api/v1/projects/${projectId}/contract-overrides/${qs ? `?${qs}` : ""}`,
      token,
    );
  },

  applyToProject: (
    token: string,
    projectId: string,
    data: CustomerContractOverrideCreateRequest,
  ) =>
    authRequest<CustomerContractOverrideResponse>(
      `/api/v1/projects/${projectId}/contract-overrides/`,
      token,
      { method: "POST", body: JSON.stringify(data) },
    ),

  updateOverride: (
    token: string,
    projectId: string,
    overrideId: string,
    data: CustomerContractOverrideUpdateRequest,
  ) =>
    authRequest<CustomerContractOverrideResponse>(
      `/api/v1/projects/${projectId}/contract-overrides/${overrideId}`,
      token,
      { method: "PUT", body: JSON.stringify(data) },
    ),

  syncToAgent: (token: string, projectId: string) =>
    authRequest<ContractSyncResponse>(
      `/api/v1/projects/${projectId}/contracts/sync`,
      token,
      { method: "POST" },
    ),
};

// --- Orchestrator ---

export type OrchestratorPhase =
  | "requested"
  | "decomposed"
  | "assigned"
  | "drafting"
  | "reviewing"
  | "integrating"
  | "validating"
  | "approved"
  | "transitioning"
  | "completed";

export type SubTaskRole =
  | "architect"
  | "frontend"
  | "backend"
  | "qa"
  | "security"
  | "devops"
  | "reviewer";

export type MergeStrategy = "accept_draft" | "accept_review" | "manual_merge";

export interface OrchestratorSessionResponse {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  phase: OrchestratorPhase;
  created_by: string | null;
  prompt_template: string | null;
  risk_flags: string[];
  created_at: string;
  updated_at: string;
}

export interface OrchestratorSessionListResponse {
  items: OrchestratorSessionResponse[];
  total: number;
}

export interface SubTaskResponse {
  id: string;
  session_id: string;
  title: string;
  description: string | null;
  assigned_role: SubTaskRole;
  status: string;
  order_index: number;
  depends_on: string[];
  artifact_id: string | null;
  result_summary: string | null;
  linear_identifier: string | null;
  linear_issue_id: string | null;
  linear_state: string | null;
  created_at: string;
  updated_at: string;
}

export interface PhaseEventResponse {
  id: string;
  session_id: string;
  old_phase: string | null;
  new_phase: string;
  actor_type: string;
  actor_id: string | null;
  message: string | null;
  created_at: string;
}

export interface SessionSummaryResponse {
  session: OrchestratorSessionResponse;
  subtasks: SubTaskResponse[];
  phase_history: PhaseEventResponse[];
}

export interface ReviewRoundResponse {
  id: string;
  session_id: string;
  subtask_id: string | null;
  round_number: number;
  status: string;
  main_ai_role: string;
  draft_content: string;
  sub_ai_role: string | null;
  review_type: string | null;
  review_content: string | null;
  review_score: number | null;
  diff_summary: string | null;
  merged_content: string | null;
  merge_strategy: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewRoundListResponse {
  items: ReviewRoundResponse[];
  total: number;
}

export interface ReviewDiffResponse {
  round_id: string;
  draft_content: string;
  review_content: string;
  diff_summary: string;
  review_type: string | null;
}

export interface MergeReviewRequest {
  merge_strategy: MergeStrategy;
  merged_content?: string;
  message?: string;
}

export interface LinearSyncHintSubtask {
  title: string;
  role: string;
  draft_summary: string;
}

export interface LinearSyncHint {
  action: string;
  session_title: string;
  session_description?: string | null;
  subtasks: LinearSyncHintSubtask[];
  suggested_labels: string[];
  instructions: string;
}

export interface GenerateDraftsResponse {
  rounds: ReviewRoundResponse[];
  linear_sync_hint: LinearSyncHint;
}

export const orchestrator = {
  listSessions: (
    token: string,
    projectId: string,
    params?: { limit?: number; offset?: number; phase?: string },
  ) => {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.phase) query.set("phase", params.phase);
    const qs = query.toString();
    return authRequest<OrchestratorSessionListResponse>(
      `/api/v1/orchestrator/projects/${projectId}/sessions${qs ? `?${qs}` : ""}`,
      token,
    );
  },

  createSession: (
    token: string,
    projectId: string,
    data: { title: string; description?: string },
  ) =>
    authRequest<OrchestratorSessionResponse>(
      `/api/v1/orchestrator/projects/${projectId}/sessions`,
      token,
      { method: "POST", body: JSON.stringify(data) },
    ),

  getSessionSummary: (token: string, sessionId: string) =>
    authRequest<SessionSummaryResponse>(
      `/api/v1/orchestrator/sessions/${sessionId}/summary`,
      token,
    ),

  deleteSession: (token: string, sessionId: string) =>
    authRequest<void>(
      `/api/v1/orchestrator/sessions/${sessionId}`,
      token,
      { method: "DELETE" },
    ),

  decompose: (token: string, sessionId: string, hints?: string[]) =>
    authRequest<{ session: OrchestratorSessionResponse; subtasks: SubTaskResponse[] }>(
      `/api/v1/orchestrator/sessions/${sessionId}/decompose`,
      token,
      { method: "POST", body: JSON.stringify({ hints: hints ?? null }) },
    ),

  assign: (
    token: string,
    sessionId: string,
    overrides?: Record<string, SubTaskRole>,
  ) =>
    authRequest<{ session: OrchestratorSessionResponse; subtasks: SubTaskResponse[] }>(
      `/api/v1/orchestrator/sessions/${sessionId}/assign`,
      token,
      { method: "POST", body: JSON.stringify({ overrides: overrides ?? null }) },
    ),

  transition: (
    token: string,
    sessionId: string,
    targetPhase: OrchestratorPhase,
    message?: string,
  ) =>
    authRequest<OrchestratorSessionResponse>(
      `/api/v1/orchestrator/sessions/${sessionId}/transition`,
      token,
      {
        method: "PUT",
        body: JSON.stringify({ target_phase: targetPhase, message: message ?? null }),
      },
    ),
};

// --- Linear Credentials ---

export interface LinearCredentialsSave {
  api_key?: string | null;
  team_id: string;
  webhook_secret?: string | null;
  tunnel_url?: string | null;
}

export interface LinearCredentialsResponse {
  api_key_masked: string;
  team_id: string;
  webhook_secret_set: boolean;
  tunnel_url: string | null;
  linear_webhook_id: string | null;
  updated_at: string;
}

export interface PushToLinearResponse {
  created_identifiers: string[];
  created_urls: string[];
  count: number;
  initial_state_applied: boolean;
}

export interface ApproveSubtaskResponse {
  subtask_id: string;
  linear_identifier: string;
  transitioned_to: string;
}

export interface ResetToWaitResponse {
  subtask_id: string;
  linear_identifier: string;
  previous_state: string;
  transitioned_to: string;
}

export interface SyncedSubtask {
  subtask_id: string;
  linear_identifier: string;
  previous_state: string | null;
  current_state: string;
}

export interface SyncLinearStatesResponse {
  synced_count: number;
  changed: SyncedSubtask[];
}

export interface LinearTeamState {
  name: string;
  type: string;
  color: string;
}

export interface LinearTeamStatesResponse {
  states: LinearTeamState[];
}

export interface LinearConnectionStatus {
  credentials_saved: boolean;
  webhook_registered: boolean;
  tunnel_url: string | null;
  tunnel_reachable: boolean | null;
  team_name: string | null;
}

export const linearCredentials = {
  save: (token: string, data: LinearCredentialsSave) =>
    authRequest<LinearCredentialsResponse>("/api/v1/me/linear-credentials/", token, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  get: (token: string) =>
    authRequest<LinearCredentialsResponse>("/api/v1/me/linear-credentials/", token),

  status: (token: string) =>
    authRequest<LinearConnectionStatus>("/api/v1/me/linear-credentials/status", token),

  delete: (token: string) =>
    authRequest<void>("/api/v1/me/linear-credentials/", token, { method: "DELETE" }),
};

export interface ProjectLinearStatus {
  credentials_saved: boolean;
  team_id: string | null;
  api_key_masked: string | null;
}

export const projectLinearCredentials = {
  status: (token: string, projectId: string) =>
    authRequest<ProjectLinearStatus>(
      `/api/v1/integrations/projects/${projectId}/linear-credentials/status`,
      token,
    ),
};

export const reviews = {
  generateDrafts: (token: string, sessionId: string) =>
    authRequest<GenerateDraftsResponse>(
      `/api/v1/orchestrator/sessions/${sessionId}/generate-drafts`,
      token,
      { method: "POST" },
    ),

  resumePipeline: (token: string, sessionId: string) =>
    authRequest<{ message: string; session_id: string }>(
      `/api/v1/orchestrator/sessions/${sessionId}/resume-pipeline`,
      token,
      { method: "POST" },
    ),

  pushToLinear: (token: string, sessionId: string) =>
    authRequest<PushToLinearResponse>(
      `/api/v1/orchestrator/sessions/${sessionId}/push-to-linear`,
      token,
      { method: "POST" },
    ),

  approveSubtask: (token: string, sessionId: string, subtaskId: string) =>
    authRequest<ApproveSubtaskResponse>(
      `/api/v1/orchestrator/sessions/${sessionId}/subtasks/${subtaskId}/approve`,
      token,
      { method: "POST" },
    ),

  resetSubtaskToWait: (token: string, sessionId: string, subtaskId: string) =>
    authRequest<ResetToWaitResponse>(
      `/api/v1/orchestrator/sessions/${sessionId}/subtasks/${subtaskId}/reset-to-wait`,
      token,
      { method: "POST" },
    ),

  syncLinearStates: (token: string, sessionId: string) =>
    authRequest<SyncLinearStatesResponse>(
      `/api/v1/orchestrator/sessions/${sessionId}/sync-linear-states`,
      token,
      { method: "POST" },
    ),

  getLinearTeamStates: (token: string, sessionId: string) =>
    authRequest<LinearTeamStatesResponse>(
      `/api/v1/orchestrator/sessions/${sessionId}/linear-team-states`,
      token,
    ),

  list: (
    token: string,
    sessionId: string,
    params?: { limit?: number; offset?: number },
  ) => {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    const qs = query.toString();
    return authRequest<ReviewRoundListResponse>(
      `/api/v1/orchestrator/sessions/${sessionId}/reviews${qs ? `?${qs}` : ""}`,
      token,
    );
  },

  getDiff: (token: string, roundId: string) =>
    authRequest<ReviewDiffResponse>(
      `/api/v1/orchestrator/reviews/${roundId}/diff`,
      token,
    ),

  merge: (token: string, roundId: string, data: MergeReviewRequest) =>
    authRequest<ReviewRoundResponse>(
      `/api/v1/orchestrator/reviews/${roundId}/merge`,
      token,
      { method: "POST", body: JSON.stringify(data) },
    ),

  reject: (token: string, roundId: string, reason: string) =>
    authRequest<ReviewRoundResponse>(
      `/api/v1/orchestrator/reviews/${roundId}/reject`,
      token,
      { method: "POST", body: JSON.stringify({ reason }) },
    ),
};

// --- Catalog ---

export interface CatalogAgent {
  id: string;
  label: string;
  description: string | null;
}

export interface CatalogSkill {
  id: string;
  label: string;
  description: string | null;
  category: string | null;
  required: boolean;
  env_vars: { name: string; required: boolean; description?: string }[];
  hook_events: string[];
  body_md: string | null;
}

export interface CatalogHook {
  id: string;
  label: string;
  description: string | null;
  category: string | null;
  event: string | null;
  required: boolean;
}

export interface CatalogListResponse<T> {
  items: T[];
  total: number;
}

export const catalog = {
  agents: {
    list: () =>
      request<CatalogListResponse<CatalogAgent>>("/api/v1/catalog/agents"),
  },
  skills: {
    list: () =>
      request<CatalogListResponse<CatalogSkill>>("/api/v1/catalog/skills"),
  },
  hooks: {
    list: () =>
      request<CatalogListResponse<CatalogHook>>("/api/v1/catalog/hooks"),
  },
};

// ─── Prototype Catalog Admin ──────────────────────────────────────────────────

export interface PrototypeCatalogEntry {
  id: string;
  slug: string;
  title: string;
  description: string | null;
  tags: string[];
  primary_tag: string | null;
  design_pattern: string | null;
  architecture_pattern: string | null;
  tech_stack_tags: string[];
  pros: string[];
  cons: string[];
  ui_structure: Record<string, unknown>;
  menu_structure: Record<string, unknown>;
  color_palette: Record<string, unknown>;
  design_philosophy: string | null;
  implementation_constraints: string[];
  recommended_agents: string[];
  optional_agents: string[];
  excluded_agents: string[];
  recommended_skills: string[];
  agent_strategy: string | null;
  task_distribution_guide: string | null;
  is_active: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export type PrototypeCatalogEntryCreate = Omit<PrototypeCatalogEntry, "id" | "created_at" | "updated_at">;
export type PrototypeCatalogEntryUpdate = Partial<Omit<PrototypeCatalogEntry, "id" | "slug" | "created_at" | "updated_at">>;

export interface PrototypeCatalogListResponse {
  items: PrototypeCatalogEntry[];
  total: number;
}

export const prototypeCatalogAdmin = {
  list: (token: string, params?: { tags?: string; primary_tag?: string; is_active?: boolean; offset?: number; limit?: number }) => {
    const qs = params ? new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString() : "";
    return authRequest<PrototypeCatalogListResponse>(
      `/api/v1/admin/registry/prototype-catalog${qs ? `?${qs}` : ""}`,
      token,
    );
  },
  get: (token: string, id: string) =>
    authRequest<PrototypeCatalogEntry>(`/api/v1/admin/registry/prototype-catalog/${id}`, token),
  create: (token: string, data: PrototypeCatalogEntryCreate) =>
    authRequest<PrototypeCatalogEntry>("/api/v1/admin/registry/prototype-catalog", token, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (token: string, id: string, data: PrototypeCatalogEntryUpdate) =>
    authRequest<PrototypeCatalogEntry>(`/api/v1/admin/registry/prototype-catalog/${id}`, token, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (token: string, id: string) =>
    authRequest<void>(`/api/v1/admin/registry/prototype-catalog/${id}`, token, { method: "DELETE" }),
};

// ─── Prototype Tags Admin ─────────────────────────────────────────────────────

export interface PrototypeTag {
  id: string;
  slug: string;
  label: string;
  label_ko: string | null;
  description: string | null;
  color: string | null;
  is_active: boolean;
  sort_order: number;
}

export type PrototypeTagCreate = Omit<PrototypeTag, "id">;
export type PrototypeTagUpdate = Partial<Omit<PrototypeTag, "id" | "slug">>;

export interface PrototypeTagListResponse {
  items: PrototypeTag[];
  total: number;
}

export const prototypeTagsAdmin = {
  list: (token: string, params?: { is_active?: boolean }) => {
    const qs = params ? new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString() : "";
    return authRequest<PrototypeTagListResponse>(
      `/api/v1/admin/registry/prototype-tags${qs ? `?${qs}` : ""}`,
      token,
    );
  },
  create: (token: string, data: PrototypeTagCreate) =>
    authRequest<PrototypeTag>("/api/v1/admin/registry/prototype-tags", token, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (token: string, id: string, data: PrototypeTagUpdate) =>
    authRequest<PrototypeTag>(`/api/v1/admin/registry/prototype-tags/${id}`, token, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (token: string, id: string) =>
    authRequest<void>(`/api/v1/admin/registry/prototype-tags/${id}`, token, { method: "DELETE" }),
};

// ─── App Settings Admin ───────────────────────────────────────────────────────

export interface AppSettingResponse {
  key: string;
  value: unknown;
  description: string | null;
}

export const appSettingsAdmin = {
  getAll: (token: string) =>
    authRequest<AppSettingResponse[]>("/api/v1/admin/settings", token),
  setVariantCount: (token: string, value: number) =>
    authRequest<AppSettingResponse>("/api/v1/admin/settings/prototype-variant-count", token, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),
  setRagTopK: (token: string, value: number) =>
    authRequest<AppSettingResponse>("/api/v1/admin/settings/prototype-rag-top-k", token, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),
};

// ─── Integrations ─────────────────────────────────────────────────────────────

export interface IntegrationValidateResponse {
  valid: boolean;
  message: string;
}

export interface RegisterInitialTasksRequest {
  linear_api_key?: string | null;
  linear_team_id?: string | null;
  notion_api_key?: string | null;
  notion_database_id?: string | null;
  project_name: string;
}

export interface RegisterInitialTasksResponse {
  linear_created: boolean;
  linear_issue_url: string | null;
  notion_created: boolean;
  notion_page_url: string | null;
  errors: string[];
}

export const integrations = {
  validateLinear: (
    token: string,
    data: { api_key: string; team_id: string },
  ) =>
    authRequest<IntegrationValidateResponse>(
      "/api/v1/integrations/validate/linear",
      token,
      { method: "POST", body: JSON.stringify(data) },
    ),

  validateNotion: (
    token: string,
    data: { api_key: string; database_id: string },
  ) =>
    authRequest<IntegrationValidateResponse>(
      "/api/v1/integrations/validate/notion",
      token,
      { method: "POST", body: JSON.stringify(data) },
    ),

  registerInitialTasks: (
    token: string,
    projectId: string,
    data: RegisterInitialTasksRequest,
  ) =>
    authRequest<RegisterInitialTasksResponse>(
      `/api/v1/integrations/projects/${projectId}/initial-tasks`,
      token,
      { method: "POST", body: JSON.stringify(data) },
    ),
};

// --- Control Tower ---

export interface CustomerSummary {
  id: string;
  company_name: string;
  org_type: string;
  customer_status: string;
  account_manager_id: string | null;
  account_manager_name: string | null;
  project_count: number;
  active_session_count: number;
  created_at: string | null;
}

export interface CustomerDetail extends CustomerSummary {
  size: string | null;
  industry: string | null;
  main_product: string | null;
  business_type: string | null;
  company_description: string | null;
  updated_at: string | null;
}

export interface CustomerListResponse {
  items: CustomerSummary[];
  total: number;
}

export interface CtProjectOverview {
  id: string;
  name: string;
  slug: string;
  status: string;
  project_type: string | null;
  owner_id: string;
  owner_name: string | null;
  organization_id: string | null;
  session_count: number;
  active_session_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface CtProjectListResponse {
  items: CtProjectOverview[];
  total: number;
}

export const controlTower = {
  listCustomers: (
    token: string,
    params?: { offset?: number; limit?: number; search?: string; status?: string },
  ) => {
    const query = new URLSearchParams();
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    if (params?.search) query.set("search", params.search);
    if (params?.status) query.set("status", params.status);
    const qs = query.toString();
    return authRequest<CustomerListResponse>(
      `/api/v1/control-tower/customers${qs ? `?${qs}` : ""}`,
      token,
    );
  },

  getCustomer: (token: string, orgId: string) =>
    authRequest<CustomerDetail>(`/api/v1/control-tower/customers/${orgId}`, token),

  listCustomerProjects: (
    token: string,
    orgId: string,
    params?: { offset?: number; limit?: number },
  ) => {
    const query = new URLSearchParams();
    if (params?.offset !== undefined) query.set("offset", String(params.offset));
    if (params?.limit !== undefined) query.set("limit", String(params.limit));
    const qs = query.toString();
    return authRequest<CtProjectListResponse>(
      `/api/v1/control-tower/customers/${orgId}/projects${qs ? `?${qs}` : ""}`,
      token,
    );
  },

  getProjectOverview: (token: string, projectId: string) =>
    authRequest<CtProjectOverview>(
      `/api/v1/control-tower/projects/${projectId}/overview`,
      token,
    ),

  setCustomerStatus: (token: string, orgId: string, status: string) =>
    authRequest<CustomerDetail>(
      `/api/v1/control-tower/customers/${orgId}/status`,
      token,
      { method: "POST", body: JSON.stringify({ status }) },
    ),

  transferProject: (token: string, projectId: string, toOrganizationId: string) =>
    authRequest<CtProjectOverview>(
      `/api/v1/control-tower/projects/${projectId}/transfer`,
      token,
      { method: "POST", body: JSON.stringify({ to_organization_id: toOrganizationId }) },
    ),
};

// ─── ROI 타입 ───

export interface RoiStandardResponse {
  id: string;
  category: "role_rate" | "solution_effort" | "complexity_multiplier";
  key: string;
  label: string;
  description: string | null;
  value_numeric: number | null;
  value_json: Record<string, number> | null;
  unit: string;
  display_order: number;
  is_active: boolean;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface RoiStandardListResponse {
  items: RoiStandardResponse[];
  total: number;
}

export interface RoiStandardCreateRequest {
  category: "role_rate" | "solution_effort" | "complexity_multiplier";
  key: string;
  label: string;
  description?: string;
  value_numeric?: number;
  value_json?: Record<string, number>;
  unit: string;
  display_order?: number;
  is_active?: boolean;
}

export interface RoiStandardUpdateRequest {
  label?: string;
  description?: string;
  value_numeric?: number;
  value_json?: Record<string, number>;
  unit?: string;
  display_order?: number;
  is_active?: boolean;
}

export interface RoiBreakdownItem {
  role_key: string;
  label: string;
  days: number;
  rate: number;
  subtotal: number;
}

export interface RoiCalculateRequest {
  solution_type: string;
  complexity: "low" | "medium" | "high";
  selected_agents_count: number;
  selected_skills_count: number;
  selected_hooks_count: number;
  platform_id?: string;
  overrides?: Record<string, number>;
}

export interface RoiCalculateResponse {
  baseline_cost: number;
  clickeye_cost: number;
  savings: number;
  savings_ratio: number;
  baseline_days: number;
  clickeye_days: number;
  breakdown: RoiBreakdownItem[];
  rates_snapshot: Record<string, Record<string, number>>;
  formula_version: string;
}

export const roiAdmin = {
  list: (token: string, category?: string, includeInactive?: boolean) => {
    const q = new URLSearchParams();
    if (category) q.set("category", category);
    if (includeInactive) q.set("include_inactive", "true");
    const qs = q.toString();
    return authRequest<RoiStandardListResponse>(
      `/api/v1/admin/roi-standards${qs ? `?${qs}` : ""}`,
      token,
    );
  },
  create: (token: string, data: RoiStandardCreateRequest) =>
    authRequest<RoiStandardResponse>("/api/v1/admin/roi-standards", token, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (token: string, id: string, data: RoiStandardUpdateRequest) =>
    authRequest<RoiStandardResponse>(`/api/v1/admin/roi-standards/${id}`, token, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (token: string, id: string) =>
    authRequest<void>(`/api/v1/admin/roi-standards/${id}`, token, {
      method: "DELETE",
    }),
};

export const roi = {
  calculate: (token: string, data: RoiCalculateRequest) =>
    authRequest<RoiCalculateResponse>("/api/v1/roi/calculate", token, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

export { ApiClientError, NetworkError };
