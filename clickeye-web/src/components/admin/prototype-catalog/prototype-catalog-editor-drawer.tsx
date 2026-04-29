"use client";

import { useState } from "react";
import { X, Loader2 } from "lucide-react";
import { toast } from "sonner";

import type { PrototypeCatalogEntry } from "@/lib/api-client";
import {
  useCreateCatalogEntry,
  useUpdateCatalogEntry,
} from "@/hooks/use-prototype-catalog-admin";

type Tab = "basic" | "tech" | "proscons" | "agent";

const TABS: { id: Tab; label: string }[] = [
  { id: "basic", label: "기본 정보" },
  { id: "tech", label: "기술 구성" },
  { id: "proscons", label: "장단점" },
  { id: "agent", label: "Agent 컨텍스트" },
];

type FormState = {
  slug: string;
  title: string;
  description: string;
  tags: string;
  primary_tag: string;
  design_pattern: string;
  architecture_pattern: string;
  tech_stack_tags: string;
  ui_structure: string;
  menu_structure: string;
  color_palette: string;
  pros: string;
  cons: string;
  design_philosophy: string;
  implementation_constraints: string;
  recommended_agents: string;
  optional_agents: string;
  excluded_agents: string;
  recommended_skills: string;
  agent_strategy: string;
  task_distribution_guide: string;
  is_active: boolean;
  priority: string;
};

function entryToForm(entry: PrototypeCatalogEntry | null): FormState {
  if (!entry) {
    return {
      slug: "", title: "", description: "", tags: "", primary_tag: "",
      design_pattern: "", architecture_pattern: "", tech_stack_tags: "",
      ui_structure: "{}", menu_structure: "{}", color_palette: "{}",
      pros: "", cons: "", design_philosophy: "",
      implementation_constraints: "", recommended_agents: "", optional_agents: "",
      excluded_agents: "", recommended_skills: "", agent_strategy: "",
      task_distribution_guide: "", is_active: true, priority: "0",
    };
  }
  return {
    slug: entry.slug,
    title: entry.title,
    description: entry.description ?? "",
    tags: (entry.tags ?? []).join(", "),
    primary_tag: entry.primary_tag ?? "",
    design_pattern: entry.design_pattern ?? "",
    architecture_pattern: entry.architecture_pattern ?? "",
    tech_stack_tags: (entry.tech_stack_tags ?? []).join(", "),
    ui_structure: JSON.stringify(entry.ui_structure ?? {}, null, 2),
    menu_structure: JSON.stringify(entry.menu_structure ?? {}, null, 2),
    color_palette: JSON.stringify(entry.color_palette ?? {}, null, 2),
    pros: (entry.pros ?? []).join("\n"),
    cons: (entry.cons ?? []).join("\n"),
    design_philosophy: entry.design_philosophy ?? "",
    implementation_constraints: (entry.implementation_constraints ?? []).join("\n"),
    recommended_agents: (entry.recommended_agents ?? []).join(", "),
    optional_agents: (entry.optional_agents ?? []).join(", "),
    excluded_agents: (entry.excluded_agents ?? []).join(", "),
    recommended_skills: (entry.recommended_skills ?? []).join(", "),
    agent_strategy: entry.agent_strategy ?? "",
    task_distribution_guide: entry.task_distribution_guide ?? "",
    is_active: entry.is_active,
    priority: String(entry.priority ?? 0),
  };
}

function parseList(val: string): string[] {
  return val.split("\n").map(s => s.trim()).filter(Boolean);
}

function parseTags(val: string): string[] {
  return val.split(",").map(s => s.trim()).filter(Boolean);
}

function parseJson(val: string): Record<string, unknown> {
  try { return JSON.parse(val) as Record<string, unknown>; } catch { return {}; }
}

interface PrototypeCatalogEditorDrawerProps {
  entry: PrototypeCatalogEntry | null;
  open: boolean;
  onClose: () => void;
}

export function PrototypeCatalogEditorDrawer({
  entry, open, onClose,
}: PrototypeCatalogEditorDrawerProps) {
  const [tab, setTab] = useState<Tab>("basic");
  const [form, setForm] = useState<FormState>(() => entryToForm(entry));

  const createMutation = useCreateCatalogEntry();
  const updateMutation = useUpdateCatalogEntry();
  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  const set = (key: keyof FormState) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => setForm(prev => ({ ...prev, [key]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      slug: form.slug,
      title: form.title,
      description: form.description || null,
      tags: parseTags(form.tags),
      primary_tag: form.primary_tag || null,
      design_pattern: form.design_pattern || null,
      architecture_pattern: form.architecture_pattern || null,
      tech_stack_tags: parseTags(form.tech_stack_tags),
      ui_structure: parseJson(form.ui_structure),
      menu_structure: parseJson(form.menu_structure),
      color_palette: parseJson(form.color_palette),
      pros: parseList(form.pros),
      cons: parseList(form.cons),
      design_philosophy: form.design_philosophy || null,
      implementation_constraints: parseList(form.implementation_constraints),
      recommended_agents: parseTags(form.recommended_agents),
      optional_agents: parseTags(form.optional_agents),
      excluded_agents: parseTags(form.excluded_agents),
      recommended_skills: parseTags(form.recommended_skills),
      agent_strategy: form.agent_strategy || null,
      task_distribution_guide: form.task_distribution_guide || null,
      is_active: form.is_active,
      priority: parseInt(form.priority, 10) || 0,
    };

    try {
      if (entry) {
        await updateMutation.mutateAsync({ id: entry.id, data: payload });
        toast.success("카탈로그 항목이 수정되었습니다");
      } else {
        await createMutation.mutateAsync(payload);
        toast.success("카탈로그 항목이 생성되었습니다");
      }
      onClose();
    } catch {
      toast.error("저장에 실패했습니다");
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
        role="button"
        tabIndex={0}
        aria-label="닫기"
      />
      <div className="relative w-full max-w-2xl h-full overflow-y-auto border-l border-[var(--border-subtle)] bg-[var(--bg-surface)] flex flex-col">
        {/* 헤더 */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-6 py-4">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            {entry ? "카탈로그 항목 편집" : "새 카탈로그 항목"}
          </h2>
          <button type="button" onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">
            <X size={16} />
          </button>
        </div>

        {/* 탭 */}
        <div className="flex border-b border-[var(--border-subtle)] px-6">
          {TABS.map(t => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`mr-4 py-3 text-xs font-medium border-b-2 transition-colors ${
                tab === t.id
                  ? "border-zinc-900 text-[var(--text-primary)]"
                  : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* 폼 */}
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 p-6 gap-4">
          {tab === "basic" && (
            <BasicTab form={form} set={set} isEdit={!!entry} />
          )}
          {tab === "tech" && (
            <TechTab form={form} set={set} />
          )}
          {tab === "proscons" && (
            <ProsConsTab form={form} set={set} />
          )}
          {tab === "agent" && (
            <AgentTab form={form} set={set} />
          )}

          <div className="sticky bottom-0 bg-[var(--bg-surface)] pt-4 flex justify-end gap-3 border-t border-[var(--border-subtle)] mt-auto">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-[var(--border-subtle)] px-4 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 size={12} className="animate-spin" />}
              저장
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({
  label, hint, children,
}: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-[var(--text-secondary)]">{label}</label>
      {hint && <p className="text-xs text-[var(--text-muted)]">{hint}</p>}
      {children}
    </div>
  );
}

const INPUT = "w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-zinc-400 focus:outline-none";
const TEXTAREA = `${INPUT} resize-y min-h-[80px]`;

type SetFn = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;

function BasicTab({ form, set, isEdit }: { form: FormState; set: SetFn; isEdit: boolean }) {
  return (
    <>
      <Field label="Slug *" hint="소문자·숫자·하이픈만 허용 (예: saas-fullstack-standard)">
        <input className={INPUT} value={form.slug} onChange={set("slug")} required disabled={isEdit} />
      </Field>
      <Field label="제목 *">
        <input className={INPUT} value={form.title} onChange={set("title")} required />
      </Field>
      <Field label="설명">
        <textarea data-gramm="false" data-gramm_editor="false" className={TEXTAREA} value={form.description} onChange={set("description")} />
      </Field>
      <Field label="태그" hint="쉼표로 구분 (예: saas, fullstack, multi-tenant)">
        <input className={INPUT} value={form.tags} onChange={set("tags")} />
      </Field>
      <Field label="대표 태그 (primary_tag)" hint="예: saas, rest-api, mvp">
        <input className={INPUT} value={form.primary_tag} onChange={set("primary_tag")} />
      </Field>
      <Field label="Design Pattern" hint="예: saas-fullstack">
        <input className={INPUT} value={form.design_pattern} onChange={set("design_pattern")} />
      </Field>
      <Field label="Architecture Pattern" hint="예: 모놀리식 3-tier">
        <input className={INPUT} value={form.architecture_pattern} onChange={set("architecture_pattern")} />
      </Field>
      <div className="flex gap-4">
        <Field label="우선순위 (높을수록 먼저)">
          <input type="number" className={INPUT} value={form.priority} onChange={set("priority")} />
        </Field>
        <Field label="활성">
          <label className="flex items-center gap-2 mt-2">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={e => {
                const val = e.target.checked;
                set("is_active")({ target: { value: String(val) } } as React.ChangeEvent<HTMLInputElement>);
              }}
              className="rounded"
            />
            <span className="text-xs text-[var(--text-secondary)]">활성화</span>
          </label>
        </Field>
      </div>
    </>
  );
}

function TechTab({ form, set }: { form: FormState; set: SetFn }) {
  return (
    <>
      <Field label="기술 스택 태그" hint="쉼표로 구분 (예: Next.js, FastAPI, PostgreSQL)">
        <input className={INPUT} value={form.tech_stack_tags} onChange={set("tech_stack_tags")} />
      </Field>
      <Field label="UI Structure (JSON)">
        <textarea data-gramm="false" data-gramm_editor="false" className={`${TEXTAREA} min-h-[120px] font-mono text-xs`} value={form.ui_structure} onChange={set("ui_structure")} />
      </Field>
      <Field label="Menu Structure (JSON)">
        <textarea data-gramm="false" data-gramm_editor="false" className={`${TEXTAREA} min-h-[80px] font-mono text-xs`} value={form.menu_structure} onChange={set("menu_structure")} />
      </Field>
      <Field label="Color Palette (JSON)">
        <textarea data-gramm="false" data-gramm_editor="false" className={`${TEXTAREA} min-h-[80px] font-mono text-xs`} value={form.color_palette} onChange={set("color_palette")} />
      </Field>
    </>
  );
}

function ProsConsTab({ form, set }: { form: FormState; set: SetFn }) {
  return (
    <>
      <Field label="장점 (줄바꿈으로 구분)">
        <textarea data-gramm="false" data-gramm_editor="false" className={`${TEXTAREA} min-h-[120px]`} value={form.pros} onChange={set("pros")} placeholder="예:\nAPI-first 설계로 확장 용이&#10;멀티테넌트 지원" />
      </Field>
      <Field label="단점 (줄바꿈으로 구분)">
        <textarea data-gramm="false" data-gramm_editor="false" className={`${TEXTAREA} min-h-[120px]`} value={form.cons} onChange={set("cons")} placeholder="예:\n초기 설정 복잡&#10;러닝커브 높음" />
      </Field>
    </>
  );
}

function AgentTab({ form, set }: { form: FormState; set: SetFn }) {
  return (
    <>
      <Field label="설계 철학">
        <textarea data-gramm="false" data-gramm_editor="false" className={`${TEXTAREA} min-h-[100px]`} value={form.design_philosophy} onChange={set("design_philosophy")} />
      </Field>
      <Field label="구현 제약사항 (줄바꿈으로 구분)">
        <textarea data-gramm="false" data-gramm_editor="false" className={TEXTAREA} value={form.implementation_constraints} onChange={set("implementation_constraints")} />
      </Field>
      <Field label="권장 에이전트" hint="쉼표로 구분 (예: backend, fullstack, frontend)">
        <input className={INPUT} value={form.recommended_agents} onChange={set("recommended_agents")} />
      </Field>
      <Field label="선택적 에이전트">
        <input className={INPUT} value={form.optional_agents} onChange={set("optional_agents")} />
      </Field>
      <Field label="제외 에이전트 (이 프로젝트에 불필요)">
        <input className={INPUT} value={form.excluded_agents} onChange={set("excluded_agents")} />
      </Field>
      <Field label="권장 스킬" hint="쉼표로 구분 (예: tdd, ralph-loop)">
        <input className={INPUT} value={form.recommended_skills} onChange={set("recommended_skills")} />
      </Field>
      <Field label="에이전트 전략">
        <textarea data-gramm="false" data-gramm_editor="false" className={`${TEXTAREA} min-h-[100px]`} value={form.agent_strategy} onChange={set("agent_strategy")} />
      </Field>
      <Field label="작업 분배 가이드">
        <textarea data-gramm="false" data-gramm_editor="false" className={`${TEXTAREA} min-h-[100px]`} value={form.task_distribution_guide} onChange={set("task_distribution_guide")} />
      </Field>
    </>
  );
}
