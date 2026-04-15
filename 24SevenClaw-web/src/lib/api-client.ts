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

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

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
}

export interface PreviewResponse {
  file_tree: FileTreeNode[];
  files: Record<string, string>;
}

export interface GenerateRequest extends PreviewRequest {
  env_vars: Record<string, string>;
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

export { ApiClientError };
