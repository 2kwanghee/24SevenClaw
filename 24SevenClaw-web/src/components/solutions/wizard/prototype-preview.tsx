"use client";

import { ArrowRight, Database, Globe, Lock, Package, Server } from "lucide-react";

import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Tech Stack Preview (기존 방식)
// ---------------------------------------------------------------------------

/** 기술 스택 레이어 색상 */
const LAYER_COLORS: Record<
  string,
  { bg: string; border: string; text: string; icon: string }
> = {
  frontend: {
    bg: "bg-sky-500/10",
    border: "border-sky-500/30",
    text: "text-sky-300",
    icon: "text-sky-400",
  },
  backend: {
    bg: "bg-violet-500/10",
    border: "border-violet-500/30",
    text: "text-violet-300",
    icon: "text-violet-400",
  },
  database: {
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    text: "text-emerald-300",
    icon: "text-emerald-400",
  },
  auth: {
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    text: "text-amber-300",
    icon: "text-amber-400",
  },
  deployment: {
    bg: "bg-slate-500/10",
    border: "border-slate-500/30",
    text: "text-slate-300",
    icon: "text-slate-400",
  },
};

/** 기술명 → 표시 레이블 정규화 */
const TECH_LABELS: Record<string, string> = {
  "next.js": "Next.js",
  "next.js-api-routes": "Next.js API",
  react: "React",
  "react-admin": "React Admin",
  vue: "Vue.js",
  angular: "Angular",
  htmx: "HTMX",
  fastapi: "FastAPI",
  express: "Express",
  flask: "Flask",
  django: "Django",
  "nest.js": "NestJS",
  postgresql: "PostgreSQL",
  mysql: "MySQL",
  mongodb: "MongoDB",
  sqlite: "SQLite",
  redis: "Redis",
  jwt: "JWT",
  "next-auth": "NextAuth",
  session: "Session",
  oauth: "OAuth",
  ldap: "LDAP",
  docker: "Docker",
  "docker-compose": "Docker Compose",
  kubernetes: "Kubernetes",
  vercel: "Vercel",
  railway: "Railway",
  aws: "AWS",
  gcp: "GCP",
  openapi: "OpenAPI",
  swagger: "Swagger",
  prisma: "Prisma",
};

function normalizeLabel(value: string): string {
  return TECH_LABELS[value.toLowerCase()] ?? value;
}

interface TechLayerProps {
  layer: "frontend" | "backend" | "database" | "auth" | "deployment";
  label: string;
  value: string;
  className?: string;
}

function TechLayer({ layer, label, value, className }: TechLayerProps) {
  const colors = LAYER_COLORS[layer];

  const Icon = {
    frontend: Globe,
    backend: Server,
    database: Database,
    auth: Lock,
    deployment: Package,
  }[layer];

  return (
    <div
      className={cn(
        "flex flex-col items-center gap-1 rounded-lg border px-3 py-2",
        colors.bg,
        colors.border,
        className,
      )}
    >
      <Icon className={cn("h-3.5 w-3.5", colors.icon)} />
      <span className="text-[10px] font-medium text-slate-500 leading-none">
        {label}
      </span>
      <span className={cn("text-xs font-semibold leading-none", colors.text)}>
        {normalizeLabel(value)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// UI Structure Preview (메뉴/페이지/컬러 방식)
// ---------------------------------------------------------------------------

interface UIMenuItem {
  label: string;
  icon?: string;
  path?: string;
}

interface UIPage {
  name: string;
  description?: string;
  components?: string[];
}

interface UIColors {
  primary?: string;
  secondary?: string;
  accent?: string;
  background?: string;
}

function isUIStructure(config: Record<string, unknown>): boolean {
  return (
    Array.isArray(config.menus) ||
    Array.isArray(config.pages) ||
    (typeof config.colors === "object" && config.colors !== null)
  );
}

interface UIStructurePreviewProps {
  menus?: UIMenuItem[];
  pages?: UIPage[];
  colors?: UIColors;
  isExpanded: boolean;
}

function UIStructurePreview({ menus, pages, colors, isExpanded }: UIStructurePreviewProps) {
  const hasMenus = Array.isArray(menus) && menus.length > 0;
  const hasPages = Array.isArray(pages) && pages.length > 0;
  const hasColors = colors && Object.values(colors).some(Boolean);

  if (!hasMenus && !hasPages && !hasColors) return null;

  /* 컴팩트 모드: 컬러 스와치 + 메뉴 수 요약 */
  if (!isExpanded) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        {/* 컬러 팔레트 미니 */}
        {hasColors && (
          <div className="flex items-center gap-1">
            {([colors.primary, colors.secondary, colors.accent].filter(Boolean) as string[]).map(
              (hex, i) => (
                <span
                  key={i}
                  title={hex}
                  className="h-3.5 w-3.5 rounded-full border border-white/10"
                  style={{ backgroundColor: hex }}
                />
              ),
            )}
          </div>
        )}
        {/* 메뉴 수 */}
        {hasMenus && (
          <span className="rounded-md border border-white/[0.08] bg-white/[0.04] px-2 py-0.5 text-[10px] font-medium text-slate-500">
            메뉴 {menus!.length}개
          </span>
        )}
        {/* 페이지 수 */}
        {hasPages && (
          <span className="rounded-md border border-white/[0.08] bg-white/[0.04] px-2 py-0.5 text-[10px] font-medium text-slate-500">
            페이지 {pages!.length}개
          </span>
        )}
      </div>
    );
  }

  /* 확장 모드: 메뉴 트리 + 페이지 레이아웃 + 컬러 팔레트 */
  return (
    <div className="space-y-3">
      {/* 컬러 팔레트 */}
      {hasColors && (
        <div>
          <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-600">
            컬러 팔레트
          </p>
          <div className="flex flex-wrap gap-2">
            {(
              [
                { label: "Primary", value: colors.primary },
                { label: "Secondary", value: colors.secondary },
                { label: "Accent", value: colors.accent },
              ] as { label: string; value: string | undefined }[]
            )
              .filter((c) => c.value)
              .map((c) => (
                <div key={c.label} className="flex items-center gap-1.5">
                  <span
                    className="h-4 w-4 rounded-full border border-white/10"
                    style={{ backgroundColor: c.value }}
                  />
                  <span className="text-[10px] text-slate-400">{c.label}</span>
                  <span className="font-mono text-[10px] text-slate-600">
                    {c.value}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* 메뉴 트리 */}
      {hasMenus && (
        <div>
          <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-600">
            메뉴 구조
          </p>
          <div className="flex flex-wrap gap-1.5">
            {menus!.slice(0, 8).map((menu, i) => (
              <span
                key={i}
                className="rounded-md border border-white/[0.08] bg-white/[0.03] px-2 py-0.5 text-[11px] text-slate-400"
              >
                {menu.label}
              </span>
            ))}
            {menus!.length > 8 && (
              <span className="rounded-md border border-white/[0.06] px-2 py-0.5 text-[11px] text-slate-600">
                +{menus!.length - 8}
              </span>
            )}
          </div>
        </div>
      )}

      {/* 페이지 레이아웃 */}
      {hasPages && (
        <div>
          <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-600">
            페이지 레이아웃
          </p>
          <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 lg:grid-cols-3">
            {pages!.slice(0, 6).map((page, i) => (
              <div
                key={i}
                className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-2.5 py-1.5"
              >
                <p className="text-[11px] font-medium text-slate-300 truncate">
                  {page.name}
                </p>
                {page.description && (
                  <p className="mt-0.5 line-clamp-1 text-[10px] text-slate-600">
                    {page.description}
                  </p>
                )}
              </div>
            ))}
            {pages!.length > 6 && (
              <div className="flex items-center justify-center rounded-lg border border-white/[0.04] px-2.5 py-1.5">
                <span className="text-[10px] text-slate-600">
                  +{pages!.length - 6}개
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PrototypePreview (공개 컴포넌트)
// ---------------------------------------------------------------------------

interface PrototypePreviewProps {
  /** Prototype.config JSON */
  config: Record<string, unknown>;
  solutionType: string;
  /** 확장 모드 여부 (선택된 카드에서 true) */
  isExpanded?: boolean;
}

/**
 * PrototypePreview — config JSON을 아키텍처 또는 UI 구조 다이어그램으로 자체 렌더링.
 *
 * config 필드 지원:
 *   기술 스택: frontend / backend / framework / database / auth / deployment / orm / docs
 *   UI 구조:   menus / pages / colors
 */
export function PrototypePreview({
  config,
  isExpanded = false,
}: PrototypePreviewProps) {
  /* UI 구조 방식 */
  if (isUIStructure(config)) {
    return (
      <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
        <UIStructurePreview
          menus={config.menus as UIMenuItem[] | undefined}
          pages={config.pages as UIPage[] | undefined}
          colors={config.colors as UIColors | undefined}
          isExpanded={isExpanded}
        />
      </div>
    );
  }

  /* 기술 스택 방식 (기존) */
  const frontend = config.frontend as string | undefined;
  const backend = (config.backend ?? config.framework) as string | undefined;
  const database = config.database as string | undefined;
  const auth = config.auth as string | undefined;
  const deployment = config.deployment as string | undefined;
  const orm = config.orm as string | undefined;
  const docs = config.docs as string | undefined;

  const layers: Array<{ layer: TechLayerProps["layer"]; label: string; value: string }> = [];

  if (frontend) layers.push({ layer: "frontend", label: "Frontend", value: frontend });
  if (backend) layers.push({ layer: "backend", label: "Backend", value: backend });
  if (orm) layers.push({ layer: "backend", label: "ORM", value: orm });
  if (docs) layers.push({ layer: "backend", label: "API Docs", value: docs });
  if (database) layers.push({ layer: "database", label: "Database", value: database });
  if (auth) layers.push({ layer: "auth", label: "Auth", value: auth });
  if (deployment) layers.push({ layer: "deployment", label: "Deploy", value: deployment });

  if (layers.length === 0) return null;

  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
      <div className="flex flex-wrap items-center gap-1.5">
        {layers.map((item, idx) => (
          <div key={`${item.layer}-${idx}`} className="flex items-center gap-1.5">
            {idx > 0 && (
              <ArrowRight className="h-3 w-3 shrink-0 text-slate-700" />
            )}
            <TechLayer
              layer={item.layer}
              label={item.label}
              value={item.value}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
