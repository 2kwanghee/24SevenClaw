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

export const recommend = {
  get: (data: RecommendRequest) =>
    request<RecommendResponse>("/api/v1/recommend", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

export { ApiClientError };
