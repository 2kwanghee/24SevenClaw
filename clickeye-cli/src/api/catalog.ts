import { apiClient } from "./client.js";

// ── 공통 타입 ──────────────────────────────────────────────────────────────────

export interface CatalogAgent {
  id: string;
  slug: string;
  label: string;
  description: string;
  category?: string;
  output_file?: string;
}

export interface CatalogSkill {
  id: string;
  slug: string;
  label: string;
  description: string;
  category?: string;
  output_file?: string;
  env_vars?: { name: string; required: boolean; description?: string }[];
}

export interface CatalogHook {
  id: string;
  slug: string;
  label: string;
  description: string;
  hook_events?: string[];
}

export interface CatalogPlatform {
  id: string;
  label: string;
  description?: string;
}

export interface CatalogPipeline {
  id: string;
  label: string;
  description?: string;
}

interface ListResponse<T> {
  items: T[];
  total: number;
}

// ── 인메모리 캐시 (세션 단위, TTL 5분) ─────────────────────────────────────────

interface CacheEntry<T> {
  data: T;
  expiresAt: number;
}

const CACHE_TTL_MS = 5 * 60 * 1000;
const cache = new Map<string, CacheEntry<unknown>>();

function getCache<T>(key: string): T | null {
  const entry = cache.get(key) as CacheEntry<T> | undefined;
  if (!entry) return null;
  if (Date.now() > entry.expiresAt) {
    cache.delete(key);
    return null;
  }
  return entry.data;
}

function setCache<T>(key: string, data: T): void {
  cache.set(key, { data, expiresAt: Date.now() + CACHE_TTL_MS });
}

// ── 카탈로그 조회 함수 ──────────────────────────────────────────────────────────

export async function fetchAgents(): Promise<CatalogAgent[]> {
  const cached = getCache<CatalogAgent[]>("agents");
  if (cached) return cached;

  const res = await apiClient.get<ListResponse<CatalogAgent>>(
    "/api/v1/catalog/agents",
  );
  setCache("agents", res.items);
  return res.items;
}

export async function fetchSkills(): Promise<CatalogSkill[]> {
  const cached = getCache<CatalogSkill[]>("skills");
  if (cached) return cached;

  const res = await apiClient.get<ListResponse<CatalogSkill>>(
    "/api/v1/catalog/skills",
  );
  setCache("skills", res.items);
  return res.items;
}

export async function fetchHooks(): Promise<CatalogHook[]> {
  const cached = getCache<CatalogHook[]>("hooks");
  if (cached) return cached;

  const res = await apiClient.get<ListResponse<CatalogHook>>(
    "/api/v1/catalog/hooks",
  );
  setCache("hooks", res.items);
  return res.items;
}

export async function fetchPlatforms(): Promise<CatalogPlatform[]> {
  const cached = getCache<CatalogPlatform[]>("platforms");
  if (cached) return cached;

  const res = await apiClient.get<ListResponse<CatalogPlatform>>(
    "/api/v1/catalog/platforms",
  );
  setCache("platforms", res.items);
  return res.items;
}

export async function fetchPipelines(): Promise<CatalogPipeline[]> {
  const cached = getCache<CatalogPipeline[]>("pipelines");
  if (cached) return cached;

  const res = await apiClient.get<ListResponse<CatalogPipeline>>(
    "/api/v1/catalog/pipelines",
  );
  setCache("pipelines", res.items);
  return res.items;
}

export type CatalogCategory =
  | "agents"
  | "skills"
  | "hooks"
  | "platforms"
  | "pipelines";

export type CatalogItem =
  | CatalogAgent
  | CatalogSkill
  | CatalogHook
  | CatalogPlatform
  | CatalogPipeline;

export async function fetchCatalog(
  category: CatalogCategory,
): Promise<CatalogItem[]> {
  switch (category) {
    case "agents":    return fetchAgents();
    case "skills":    return fetchSkills();
    case "hooks":     return fetchHooks();
    case "platforms": return fetchPlatforms();
    case "pipelines": return fetchPipelines();
    default: {
      const _exhaustive: never = category;
      throw new Error(`알 수 없는 카탈로그 카테고리: ${_exhaustive}`);
    }
  }
}

/** 테스트에서 캐시를 비울 때 사용 */
export function clearCatalogCache(): void {
  cache.clear();
}
