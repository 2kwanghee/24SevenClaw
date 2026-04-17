"use client";

import { useEffect, useState } from "react";
import { useForm, Controller, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { ArrowLeft, Save, Layers, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { RoleGuard } from "@/components/common/role-guard";
import { pmProfiles, pmMarkdown, type PMProfileUpdateRequest } from "@/lib/api-client";
import { pmProfileSchema, type PMProfileFormData } from "@/lib/validations/pm";
import { CollapsibleSection } from "@/components/admin/markdown/collapsible-section";
import { PMMarkdownPane } from "@/components/admin/pm/pm-markdown-pane";
import { TagInput } from "@/components/admin/pm/tag-input";

interface PMEditFormInnerProps {
  profileId: string;
}

function PMEditFormInner({ profileId }: PMEditFormInnerProps) {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const qc = useQueryClient();

  const [markdownText, setMarkdownText] = useState("");
  const [mdLoaded, setMdLoaded] = useState(false);
  const [mdDirty, setMdDirty] = useState(false);

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ["pm-profile-detail", profileId],
    queryFn: () => pmProfiles.get(token, profileId),
    enabled: !!token,
  });

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<PMProfileFormData>({
    resolver: zodResolver(pmProfileSchema) as Resolver<PMProfileFormData>,
    defaultValues: {
      name: "",
      slug: "",
      title: "",
      avatar_url: "",
      domain: "",
      description: "",
      bio_long: "",
      years_experience: "",
      is_active: true,
      language: "ko",
      specialties: [],
      tech_stack_tags: [],
      industry_tags: [],
      preferred_solution_types: [],
    },
  });

  useEffect(() => {
    if (profile) {
      reset({
        name: profile.name,
        slug: profile.slug,
        title: profile.title ?? "",
        avatar_url: profile.avatar_url ?? "",
        domain: profile.domain ?? "",
        description: profile.description ?? "",
        bio_long: profile.bio_long ?? "",
        years_experience: profile.years_experience ?? "",
        is_active: profile.is_active,
        language: profile.language ?? "ko",
        specialties: profile.specialties ?? [],
        tech_stack_tags: profile.tech_stack_tags ?? [],
        industry_tags: profile.industry_tags ?? [],
        preferred_solution_types: profile.preferred_solution_types ?? [],
      });
    }
  }, [profile, reset]);

  useEffect(() => {
    if (token && !mdLoaded) {
      pmMarkdown
        .get(token, profileId)
        .then((md) => { setMarkdownText(md); setMdLoaded(true); })
        .catch(() => toast.error("Markdown 로드에 실패했습니다."));
    }
  }, [token, profileId, mdLoaded]);

  const updateMutation = useMutation({
    mutationFn: (data: PMProfileUpdateRequest) => pmProfiles.update(token, profileId, data),
    onSuccess: () => {
      toast.success("PM 프로필이 업데이트되었습니다.");
      qc.invalidateQueries({ queryKey: ["admin-pm-profiles"] });
      qc.invalidateQueries({ queryKey: ["pm-profile-detail", profileId] });
      setMdLoaded(false);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const mdUpdateMutation = useMutation({
    mutationFn: (md: string) => pmMarkdown.update(token, profileId, md),
    onSuccess: () => {
      toast.success("Markdown이 저장되었습니다.");
      setMdDirty(false);
      qc.invalidateQueries({ queryKey: ["admin-pm-profiles"] });
      qc.invalidateQueries({ queryKey: ["pm-profile-detail", profileId] });
      reset(undefined, { keepValues: true });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const onSubmit = (data: PMProfileFormData) => {
    const payload: PMProfileUpdateRequest = {
      name: data.name,
      slug: data.slug,
      title: data.title || null,
      avatar_url: data.avatar_url || null,
      domain: data.domain || null,
      description: data.description || null,
      bio_long: data.bio_long || null,
      years_experience: data.years_experience !== "" && data.years_experience !== undefined
        ? Number(data.years_experience)
        : null,
      is_active: data.is_active,
      language: data.language,
      specialties: data.specialties,
      tech_stack_tags: data.tech_stack_tags,
      industry_tags: data.industry_tags,
      preferred_solution_types: data.preferred_solution_types,
    };
    updateMutation.mutate(payload);
  };

  if (isLoading) {
    return <div className="py-12 text-center text-sm text-slate-500">불러오는 중...</div>;
  }
  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
        <AlertCircle className="h-4 w-4 shrink-0" />
        {(error as Error).message}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
          {mdDirty ? (
            <button
              type="button"
              onClick={() => mdUpdateMutation.mutate(markdownText)}
              disabled={mdUpdateMutation.isPending}
              className="flex items-center gap-1.5 rounded-xl bg-amber-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-amber-500 disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              {mdUpdateMutation.isPending ? "저장 중..." : "MD 저장"}
            </button>
          ) : null}
          <button
            type="submit"
            disabled={updateMutation.isPending || !isDirty}
            className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
          >
            <Save className="h-3.5 w-3.5" />
            {updateMutation.isPending ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>

      {/* 블록 1: 기본 정보 */}
      <CollapsibleSection title="기본 정보" defaultOpen>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="block text-xs text-slate-400 mb-1">이름 *</label>
            <input
              {...register("name")}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
            />
            {errors.name && <p className="mt-1 text-xs text-red-400">{errors.name.message}</p>}
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">슬러그 *</label>
            <input
              {...register("slug")}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
            />
            {errors.slug && <p className="mt-1 text-xs text-red-400">{errors.slug.message}</p>}
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">직함</label>
            <input
              {...register("title")}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">도메인</label>
            <input
              {...register("domain")}
              placeholder="예: saas, fintech"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Avatar URL</label>
            <input
              {...register("avatar_url")}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
            />
            {errors.avatar_url && <p className="mt-1 text-xs text-red-400">{errors.avatar_url.message}</p>}
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">연차</label>
            <input
              type="number"
              {...register("years_experience")}
              min={0}
              max={50}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">언어</label>
            <select
              {...register("language")}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
            >
              <option value="ko">한국어</option>
              <option value="en">English</option>
            </select>
          </div>
          <div className="flex items-center gap-2 pt-5">
            <input
              id="is_active"
              type="checkbox"
              {...register("is_active")}
              className="h-4 w-4 rounded border-white/20"
            />
            <label htmlFor="is_active" className="text-sm text-slate-300">활성 상태</label>
          </div>
        </div>
      </CollapsibleSection>

      {/* 블록 2: 태그 */}
      <CollapsibleSection title="전문분야 태그">
        <Controller
          name="specialties"
          control={control}
          render={({ field }) => (
            <TagInput
              label="전문분야 (specialties)"
              values={field.value}
              onChange={field.onChange}
              placeholder="예: product, saas"
            />
          )}
        />
        <Controller
          name="preferred_solution_types"
          control={control}
          render={({ field }) => (
            <TagInput
              label="선호 솔루션 유형"
              values={field.value}
              onChange={field.onChange}
              placeholder="예: saas, rest-api"
            />
          )}
        />
      </CollapsibleSection>

      {/* 블록 3: 자유서술 */}
      <CollapsibleSection title="자유서술">
        <div>
          <label className="block text-xs text-slate-400 mb-1">한 줄 설명</label>
          <input
            {...register("description")}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">
            상세 소개 (bio_long) — Claude PM 추천 시 전달
          </label>
          <textarea
            {...register("bio_long")}
            rows={6}
            placeholder="PM의 전문성, 경험, 스타일을 상세히 기술해 주세요."
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
          />
          <p className="mt-1 text-xs text-slate-600">
            구체적이고 상세할수록 Claude 추천 품질이 높아집니다.
          </p>
        </div>
      </CollapsibleSection>

      {/* 블록 4: MD 전체 */}
      <PMMarkdownPane
        value={markdownText}
        onChange={(v) => { setMarkdownText(v); setMdDirty(true); }}
      />

      {/* 블록 5: SKILL (기술 스택) */}
      <CollapsibleSection title="SKILL — 기술 스택 태그">
        <Controller
          name="tech_stack_tags"
          control={control}
          render={({ field }) => (
            <TagInput
              label="기술 스택 태그"
              values={field.value}
              onChange={field.onChange}
              placeholder="예: nextjs, fastapi, react"
            />
          )}
        />
      </CollapsibleSection>

      {/* 블록 6: AGENT (산업) */}
      <CollapsibleSection title="AGENT — 산업 태그">
        <Controller
          name="industry_tags"
          control={control}
          render={({ field }) => (
            <TagInput
              label="산업 태그"
              values={field.value}
              onChange={field.onChange}
              placeholder="예: fintech, ecommerce, healthtech"
            />
          )}
        />
      </CollapsibleSection>

      {/* 블록 7: 기타 — 구성 관리 링크 */}
      <CollapsibleSection title="기타" defaultOpen={false}>
        <div className="rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3">
          <p className="text-xs text-slate-500 mb-2">
            PM에 할당된 Skill, Agent, Hook, MCP 구성은 별도 페이지에서 관리합니다.
          </p>
          <Link
            href={`/admin/pm/${profileId}/composition`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:bg-white/5"
          >
            <Layers className="h-3.5 w-3.5" />
            구성 관리 페이지로 이동
          </Link>
        </div>
      </CollapsibleSection>
    </form>
  );
}

export function PMEditForm({ profileId }: { profileId: string }) {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <PMEditFormInner profileId={profileId} />
    </RoleGuard>
  );
}
