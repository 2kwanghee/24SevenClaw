"use client";

import { Lock, Unlock, Tag, FileCode2, Clock, Hash } from "lucide-react";
import type { CentralContractResponse } from "@/lib/api-client";

const TYPE_COLORS: Record<string, string> = {
  settings: "bg-blue-50 text-blue-700 border-blue-200",
  skill: "bg-emerald-50 text-emerald-700 border-emerald-200",
  agent: "bg-violet-50 text-violet-700 border-violet-200",
  pipeline: "bg-amber-50 text-amber-700 border-amber-200",
};

const TYPE_LABELS: Record<string, string> = {
  settings: "설정",
  skill: "스킬",
  agent: "에이전트",
  pipeline: "파이프라인",
};

interface ContractViewerProps {
  contract: CentralContractResponse;
}

export function ContractViewer({ contract }: ContractViewerProps) {
  const typeColor = TYPE_COLORS[contract.contract_type] ?? "bg-zinc-100 text-zinc-600 border-zinc-200";
  const typeLabel = TYPE_LABELS[contract.contract_type] ?? contract.contract_type;

  return (
    <div className="space-y-6">
      {/* 메타 정보 */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <MetaItem icon={Tag} label="슬러그" value={contract.slug} />
        <MetaItem
          icon={FileCode2}
          label="타입"
          value={typeLabel}
          badge={typeColor}
        />
        <MetaItem icon={Hash} label="버전" value={contract.version} />
        <MetaItem
          icon={contract.is_locked ? Lock : Unlock}
          label="잠금"
          value={contract.is_locked ? "잠금" : "편집 가능"}
          badge={
            contract.is_locked
              ? "bg-red-50 text-red-700 border-red-200"
              : "bg-emerald-50 text-emerald-700 border-emerald-200"
          }
        />
      </div>

      {/* 설명 */}
      {contract.description && (
        <div>
          <p className="mb-1 text-xs font-medium text-[var(--text-muted)]">설명</p>
          <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
            {contract.description}
          </p>
        </div>
      )}

      {/* 소스 + 날짜 */}
      <div className="flex flex-wrap gap-4 text-xs text-[var(--text-muted)]">
        <span className="flex items-center gap-1">
          소스: <code className="rounded bg-zinc-100 px-1.5 py-0.5">{contract.source}</code>
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          생성: {new Date(contract.created_at).toLocaleString("ko-KR")}
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          수정: {new Date(contract.updated_at).toLocaleString("ko-KR")}
        </span>
      </div>

      {/* 허용 오버라이드 */}
      {contract.allowed_overrides.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium text-[var(--text-muted)]">
            허용된 오버라이드 필드
          </p>
          <div className="flex flex-wrap gap-1.5">
            {contract.allowed_overrides.map((field) => (
              <span
                key={field}
                className="rounded-lg border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs font-medium text-violet-700"
              >
                {field}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* JSON 콘텐츠 */}
      <div>
        <p className="mb-2 text-xs font-medium text-[var(--text-muted)]">콘텐츠 (JSON)</p>
        <pre className="max-h-96 overflow-auto rounded-xl border border-[var(--border-subtle)] bg-zinc-50 p-4 text-xs leading-relaxed text-[var(--text-secondary)]">
          {JSON.stringify(contract.content, null, 2)}
        </pre>
      </div>
    </div>
  );
}

/* 메타 아이템 */

interface MetaItemProps {
  icon: typeof Tag;
  label: string;
  value: string;
  badge?: string;
}

function MetaItem({ icon: Icon, label, value, badge }: MetaItemProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-3 py-2.5">
      <Icon className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
      <div className="min-w-0">
        <p className="text-[10px] text-[var(--text-muted)]">{label}</p>
        {badge ? (
          <span
            className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-xs font-medium ${badge}`}
          >
            {value}
          </span>
        ) : (
          <p className="truncate text-xs font-medium text-[var(--text-primary)]">
            {value}
          </p>
        )}
      </div>
    </div>
  );
}

export { TYPE_COLORS, TYPE_LABELS };
