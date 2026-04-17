"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { ArrowLeft, Save, Layers, AlertCircle, Code2, FormInput } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { RoleGuard } from "@/components/common/role-guard";
import {
  pmProfiles,
  pmMarkdown,
  type PMProfileUpdateRequest,
} from "@/lib/api-client";

type TagInputProps = {
  label: string;
  values: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
};

function TagInput({ label, values, onChange, placeholder }: TagInputProps) {
  const [input, setInput] = useState("");

  const add = () => {
    const v = input.trim();
    if (v && !values.includes(v)) onChange([...values, v]);
    setInput("");
  };

  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1">{label}</label>
      <div className="flex flex-wrap gap-1 mb-2 min-h-[28px]">
        {values.map((v) => (
          <span
            key={v}
            className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-slate-300"
          >
            {v}
            <button
              type="button"
              onClick={() => onChange(values.filter((x) => x !== v))}
              className="text-slate-500 hover:text-slate-300"
            >
              ×
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white placeholder-slate-600 focus:border-violet-500/50 focus:outline-none"
          placeholder={placeholder ?? "입력 후 Enter"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); add(); }
          }}
        />
        <button
          type="button"
          onClick={add}
          className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:bg-white/5"
        >
          추가
        </button>
      </div>
    </div>
  );
}

function PMEditForm({ profileId }: { profileId: string }) {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const router = useRouter();
  const qc = useQueryClient();

  const [activeTab, setActiveTab] = useState<"form" | "markdown">("form");
  const [markdownText, setMarkdownText] = useState("");
  const [mdLoaded, setMdLoaded] = useState(false);

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ["pm-profile-detail", profileId],
    queryFn: () => pmProfiles.get(token, profileId),
    enabled: !!token,
  });

  const [form, setForm] = useState<PMProfileUpdateRequest>({});
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (profile && !initialized) {
      setForm({
        name: profile.name,
        title: profile.title ?? "",
        avatar_url: profile.avatar_url ?? "",
        domain: profile.domain ?? "",
        description: profile.description ?? "",
        bio_long: profile.bio_long ?? "",
        years_experience: profile.years_experience ?? undefined,
        is_active: profile.is_active,
        specialties: profile.specialties,
        tech_stack_tags: profile.tech_stack_tags ?? [],
        industry_tags: profile.industry_tags ?? [],
        preferred_solution_types: profile.preferred_solution_types ?? [],
        language: profile.language ?? "ko",
      });
      setInitialized(true);
    }
  }, [profile, initialized]);

  // Markdown 탭 진입 시 서버에서 최신 markdown 로드
  useEffect(() => {
    if (activeTab === "markdown" && token && !mdLoaded) {
      pmMarkdown.get(token, profileId)
        .then((md) => { setMarkdownText(md); setMdLoaded(true); })
        .catch(() => toast.error("Markdown 로드에 실패했습니다."));
    }
  }, [activeTab, token, profileId, mdLoaded]);

  const updateMutation = useMutation({
    mutationFn: (data: PMProfileUpdateRequest) =>
      pmProfiles.update(token, profileId, data),
    onSuccess: () => {
      toast.success("PM 프로필이 업데이트되었습니다.");
      qc.invalidateQueries({ queryKey: ["admin-pm-profiles"] });
      qc.invalidateQueries({ queryKey: ["pm-profile-detail", profileId] });
      setMdLoaded(false); // force md reload on next tab switch
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const mdUpdateMutation = useMutation({
    mutationFn: (md: string) => pmMarkdown.update(token, profileId, md),
    onSuccess: (updatedProfile) => {
      toast.success("Markdown이 저장되었습니다.");
      qc.invalidateQueries({ queryKey: ["admin-pm-profiles"] });
      qc.invalidateQueries({ queryKey: ["pm-profile-detail", profileId] });
      setInitialized(false); // force form reload on next switch
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const setField = <K extends keyof PMProfileUpdateRequest>(
    key: K,
    value: PMProfileUpdateRequest[K],
  ) => setForm((prev) => ({ ...prev, [key]: value }));

  if (isLoading) return <div className="py-12 text-center text-sm text-slate-500">불러오는 중...</div>;
  if (error) return (
    <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
      <AlertCircle className="h-4 w-4 shrink-0" />
      {(error as Error).message}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/admin/pm"
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            목록으로
          </Link>
          <span className="text-slate-700">/</span>
          <h1 className="text-sm font-semibold text-white">{profile?.name}</h1>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={`/admin/pm/${profileId}/composition`}
            className="flex items-center gap-1.5 rounded-xl border border-white/10 px-3 py-1.5 text-xs text-slate-400 transition-colors hover:bg-white/5"
          >
            <Layers className="h-3.5 w-3.5" />
            구성 관리
          </Link>
          {activeTab === "form" ? (
            <button
              type="button"
              onClick={() => updateMutation.mutate(form)}
              disabled={updateMutation.isPending}
              className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              {updateMutation.isPending ? "저장 중..." : "저장"}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => mdUpdateMutation.mutate(markdownText)}
              disabled={mdUpdateMutation.isPending}
              className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              {mdUpdateMutation.isPending ? "저장 중..." : "MD 저장"}
            </button>
          )}
        </div>
      </div>

      {/* 탭 */}
      <div className="flex gap-1 rounded-xl border border-white/10 bg-white/[0.02] p-1 w-fit">
        <button
          type="button"
          onClick={() => setActiveTab("form")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            activeTab === "form"
              ? "bg-violet-600 text-white"
              : "text-slate-400 hover:text-slate-300"
          }`}
        >
          <FormInput className="h-3.5 w-3.5" />
          폼 편집
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("markdown")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            activeTab === "markdown"
              ? "bg-violet-600 text-white"
              : "text-slate-400 hover:text-slate-300"
          }`}
        >
          <Code2 className="h-3.5 w-3.5" />
          Markdown 편집
        </button>
      </div>

      {/* 폼 탭 */}
      {activeTab === "form" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* 기본 정보 */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">기본 정보</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">이름</label>
                <input
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                  value={form.name ?? ""}
                  onChange={(e) => setField("name", e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">직함</label>
                <input
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                  value={form.title ?? ""}
                  onChange={(e) => setField("title", e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">도메인</label>
                <input
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                  placeholder="예: saas, fintech"
                  value={form.domain ?? ""}
                  onChange={(e) => setField("domain", e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">연차</label>
                <input
                  type="number"
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                  min={0}
                  max={50}
                  value={form.years_experience ?? ""}
                  onChange={(e) =>
                    setField(
                      "years_experience",
                      e.target.value ? parseInt(e.target.value) : undefined,
                    )
                  }
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">언어</label>
                <select
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                  value={form.language ?? "ko"}
                  onChange={(e) => setField("language", e.target.value)}
                >
                  <option value="ko">한국어</option>
                  <option value="en">English</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="is_active"
                  type="checkbox"
                  checked={form.is_active ?? true}
                  onChange={(e) => setField("is_active", e.target.checked)}
                  className="h-4 w-4 rounded border-white/20"
                />
                <label htmlFor="is_active" className="text-sm text-slate-300">활성 상태</label>
              </div>
            </div>
          </div>

          {/* 태그 & 전문 분야 */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">전문 분야 & 태그</h2>
            <TagInput
              label="전문분야 (specialties)"
              values={form.specialties ?? []}
              onChange={(v) => setField("specialties", v)}
              placeholder="예: product, saas"
            />
            <TagInput
              label="기술 스택 태그"
              values={form.tech_stack_tags ?? []}
              onChange={(v) => setField("tech_stack_tags", v)}
              placeholder="예: nextjs, fastapi"
            />
            <TagInput
              label="산업 태그"
              values={form.industry_tags ?? []}
              onChange={(v) => setField("industry_tags", v)}
              placeholder="예: fintech, ecommerce"
            />
            <TagInput
              label="선호 솔루션 유형"
              values={form.preferred_solution_types ?? []}
              onChange={(v) => setField("preferred_solution_types", v)}
              placeholder="예: saas, rest-api"
            />
          </div>

          {/* 설명 */}
          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 space-y-4 lg:col-span-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">설명 (Claude 추천 컨텍스트)</h2>
            <div>
              <label className="block text-xs text-slate-400 mb-1">한 줄 설명</label>
              <input
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                value={form.description ?? ""}
                onChange={(e) => setField("description", e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                상세 소개 (bio_long) — Claude PM 추천 시 전달되는 내용
              </label>
              <textarea
                rows={6}
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                placeholder="PM의 전문성, 경험, 스타일을 상세히 기술해 주세요."
                value={form.bio_long ?? ""}
                onChange={(e) => setField("bio_long", e.target.value)}
              />
              <p className="mt-1 text-xs text-slate-600">
                구체적이고 상세할수록 Claude 추천 품질이 높아집니다.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Markdown 탭 */}
      {activeTab === "markdown" && (
        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Markdown 편집
            </h2>
            <p className="text-xs text-slate-600">
              YAML frontmatter 수정 시 폼 필드에 자동 반영됩니다.
              <code className="mx-1 rounded bg-white/5 px-1 text-slate-400">---bio---</code>
              아래는 상세 소개(bio_long).
            </p>
          </div>
          <textarea
            rows={28}
            spellCheck={false}
            className="w-full rounded-lg border border-white/10 bg-black/30 px-4 py-3 font-mono text-sm text-slate-300 focus:border-violet-500/50 focus:outline-none resize-y"
            value={markdownText}
            onChange={(e) => setMarkdownText(e.target.value)}
          />
        </div>
      )}
    </div>
  );
}

export default function AdminPMDetailPage() {
  const params = useParams<{ id: string }>();
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <PMEditForm profileId={params.id} />
    </RoleGuard>
  );
}
