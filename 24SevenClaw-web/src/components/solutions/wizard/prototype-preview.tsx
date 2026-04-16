"use client";

import { ArrowRight, Database, Globe, Lock, Package, Server } from "lucide-react";

import { cn } from "@/lib/utils";

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

interface PrototypePreviewProps {
  /** Prototype.config JSON */
  config: Record<string, unknown>;
  solutionType: string;
}

/**
 * PrototypePreview — config JSON을 아키텍처 다이어그램으로 자체 렌더링.
 *
 * config 필드 지원:
 *   - frontend / backend / framework / database / auth / deployment / orm / docs
 */
export function PrototypePreview({
  config,
}: PrototypePreviewProps) {
  const frontend = config.frontend as string | undefined;
  const backend = (config.backend ?? config.framework) as string | undefined;
  const database = config.database as string | undefined;
  const auth = config.auth as string | undefined;
  const deployment = config.deployment as string | undefined;
  const orm = config.orm as string | undefined;
  const docs = config.docs as string | undefined;

  // 보여줄 레이어 목록 구성
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
