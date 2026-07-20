"use client";

import { useEffect, useMemo, useState } from "react";
import { useForm, Controller, type Resolver, type UseFormRegister, type UseFormWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { ArrowLeft, Save, AlertCircle, Heart, Frown, MessageSquare, BarChart3 } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { RoleGuard } from "@/components/common/role-guard";
import { pmProfiles, pmMarkdown, type PMProfileUpdateRequest, type PMRatingResponse } from "@/lib/api-client";
import { createPmProfileSchema, type PMProfileFormData } from "@/lib/validations/pm";
import { CollapsibleSection } from "@/components/admin/markdown/collapsible-section";
import { PMMarkdownPane } from "@/components/admin/pm/pm-markdown-pane";
import { TagInput } from "@/components/admin/pm/tag-input";
import { CompositionPanel } from "@/components/admin/pm/composition-panel";

function TranslationMissingBadge() {
  return (
    <span className="ml-1 rounded px-1.5 py-0.5 bg-amber-100 text-amber-700 text-[10px] font-medium">
      번역 미입력
    </span>
  );
}

interface PMEnTranslationSectionProps {
  register: UseFormRegister<PMProfileFormData>;
  watch: UseFormWatch<PMProfileFormData>;
}

function PMEnTranslationSection({ register, watch }: PMEnTranslationSectionProps) {
  const nameEn = watch("name_en");
  const titleEn = watch("title_en");
  const descEn = watch("description_en");
  const bioEn = watch("bio_long_en");
  const missingCount = [nameEn, titleEn, descEn, bioEn].filter((v) => !v).length;

  const sectionTitle = (
    <span className="flex items-center gap-1.5">
      영문 번역 (i18n)
      {missingCount > 0 && (
        <span className="rounded px-1.5 py-0.5 bg-amber-100 text-amber-700 text-[10px] font-medium">
          {missingCount}개 미입력
        </span>
      )}
    </span>
  );

  return (
    <CollapsibleSection title={sectionTitle as unknown as string}>
      <p className="mb-3 text-xs text-[var(--text-muted)]">
        영문 사용자에게 표시되는 텍스트. 비워두면 한국어 원문 사용.
      </p>
      <div className="space-y-3">
        <div>
          <label className="flex items-center text-xs text-[var(--text-muted)] mb-1">
            이름 (name_en)
            {!nameEn && <TranslationMissingBadge />}
          </label>
          <input
            {...register("name_en")}
            placeholder="e.g. Full-Stack PM"
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
          />
        </div>
        <div>
          <label className="flex items-center text-xs text-[var(--text-muted)] mb-1">
            직함 (title_en)
            {!titleEn && <TranslationMissingBadge />}
          </label>
          <input
            {...register("title_en")}
            placeholder="e.g. Senior Product Manager"
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
          />
        </div>
        <div>
          <label className="flex items-center text-xs text-[var(--text-muted)] mb-1">
            한 줄 설명 (description_en)
            {!descEn && <TranslationMissingBadge />}
          </label>
          <input
            {...register("description_en")}
            placeholder="e.g. Specializes in SaaS product strategy"
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
          />
        </div>
        <div>
          <label className="flex items-center text-xs text-[var(--text-muted)] mb-1">
            상세 소개 (bio_long_en)
            {!bioEn && <TranslationMissingBadge />}
          </label>
          <textarea data-gramm="false" data-gramm_editor="false"
            {...register("bio_long_en")}
            rows={5}
            placeholder="e.g. Experienced PM with 8+ years in SaaS..."
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
          />
        </div>
      </div>
    </CollapsibleSection>
  );
}

interface PMEditFormInnerProps {
  profileId: string;
}

function PMEditFormInner({ profileId }: PMEditFormInnerProps) {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const qc = useQueryClient();
  const tV = useTranslations("validation");
  const tT = useTranslations("toast.pm");

  const [markdownText, setMarkdownText] = useState("");
  const [mdLoaded, setMdLoaded] = useState(false);
  const [mdDirty, setMdDirty] = useState(false);

  const pmProfileSchema = useMemo(() => createPmProfileSchema(tV), [tV]);

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
    watch,
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
      supported_platforms: [],
      name_en: "",
      title_en: "",
      description_en: "",
      bio_long_en: "",
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
        supported_platforms: profile.supported_platforms ?? [],
        name_en: profile.name_en ?? "",
        title_en: profile.title_en ?? "",
        description_en: profile.description_en ?? "",
        bio_long_en: profile.bio_long_en ?? "",
      });
    }
  }, [profile, reset]);

  useEffect(() => {
    if (token && !mdLoaded) {
      pmMarkdown
        .get(token, profileId)
        .then((md) => { setMarkdownText(md); setMdLoaded(true); })
        .catch(() => toast.error(tT("markdownLoadFail")));
    }
  }, [token, profileId, mdLoaded, tT]);

  const updateMutation = useMutation({
    mutationFn: (data: PMProfileUpdateRequest) => pmProfiles.update(token, profileId, data),
    onSuccess: () => {
      toast.success(tT("updateSuccess"));
      qc.invalidateQueries({ queryKey: ["admin-pm-profiles"] });
      qc.invalidateQueries({ queryKey: ["pm-profile-detail", profileId] });
      setMdLoaded(false);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const mdUpdateMutation = useMutation({
    mutationFn: (md: string) => pmMarkdown.update(token, profileId, md),
    onSuccess: () => {
      toast.success(tT("markdownSaveSuccess"));
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
      supported_platforms: data.supported_platforms,
      name_en: data.name_en || null,
      title_en: data.title_en || null,
      description_en: data.description_en || null,
      bio_long_en: data.bio_long_en || null,
    };
    updateMutation.mutate(payload);
  };

  if (isLoading) {
    return <div className="py-12 text-center text-sm text-[var(--text-muted)]">불러오는 중...</div>;
  }
  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
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
            className="flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            목록으로
          </Link>
          <span className="text-[var(--border-medium)]">/</span>
          <h1 className="text-sm font-semibold text-[var(--text-primary)]">{profile?.name}</h1>
        </div>
        <div className="flex items-center gap-2">
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
            className="flex items-center gap-1.5 rounded-xl bg-[var(--accent)] px-4 py-1.5 text-sm font-medium text-[var(--accent-fg)] transition-colors hover:opacity-90 disabled:opacity-50"
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
            <label className="block text-xs text-[var(--text-muted)] mb-1">이름 *</label>
            <input
              {...register("name")}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1">슬러그 *</label>
            <input
              {...register("slug")}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            />
            {errors.slug && <p className="mt-1 text-xs text-red-600">{errors.slug.message}</p>}
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1">직함</label>
            <input
              {...register("title")}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1">도메인</label>
            <input
              {...register("domain")}
              placeholder="예: saas, fintech"
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1">Avatar URL</label>
            <input
              {...register("avatar_url")}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            />
            {errors.avatar_url && <p className="mt-1 text-xs text-red-600">{errors.avatar_url.message}</p>}
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1">연차</label>
            <input
              type="number"
              {...register("years_experience")}
              min={0}
              max={50}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--text-muted)] mb-1">언어</label>
            <select
              {...register("language")}
              className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
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
              className="h-4 w-4 rounded border-[var(--border-medium)]"
            />
            <label htmlFor="is_active" className="text-sm text-[var(--text-secondary)]">활성 상태</label>
          </div>
        </div>
      </CollapsibleSection>

      {/* 블록 2: 구성 컴포넌트 (팀) */}
      <CollapsibleSection title="구성 컴포넌트" defaultOpen>
        <CompositionPanel profileId={profileId} />
      </CollapsibleSection>

      {/* 블록 3: 태그 */}
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
          <label className="block text-xs text-[var(--text-muted)] mb-1">한 줄 설명</label>
          <input
            {...register("description")}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-[var(--text-muted)] mb-1">
            상세 소개 (bio_long) — Claude PM 추천 시 전달
          </label>
          <textarea data-gramm="false" data-gramm_editor="false"
            {...register("bio_long")}
            rows={6}
            placeholder="PM의 전문성, 경험, 스타일을 상세히 기술해 주세요."
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--accent)] focus:outline-none"
          />
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            구체적이고 상세할수록 Claude 추천 품질이 높아집니다.
          </p>
        </div>
      </CollapsibleSection>

      {/* 블록 3-b: 영문 번역 */}
      <PMEnTranslationSection register={register} watch={watch} />

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

      {/* 블록 6-b: 지원 플랫폼 */}
      <CollapsibleSection title="지원 플랫폼">
        <Controller
          name="supported_platforms"
          control={control}
          render={({ field }) => (
            <TagInput
              label="지원 AI 플랫폼"
              values={field.value}
              onChange={field.onChange}
              placeholder="예: claude-code, cursor, gemini-cli, codex"
            />
          )}
        />
        <p className="mt-1.5 text-xs text-[var(--text-muted)]">
          이 PM이 지원하는 AI 에이전트 플랫폼 슬러그를 입력하세요.
          위저드 Step 7(플랫폼 선택)에서 미지원 플랫폼은 비활성화됩니다.
        </p>
      </CollapsibleSection>

      {/* 블록 8: 사용자 피드백 */}
      <CollapsibleSection title="사용자 피드백" defaultOpen={false}>
        <PMFeedbackPanel profileId={profileId} />
      </CollapsibleSection>
    </form>
  );
}

/* ---------------------------------------------------------------------------
   PMFeedbackPanel — PM 피드백 요약 + 목록
--------------------------------------------------------------------------- */

function PMFeedbackPanel({ profileId }: { profileId: string }) {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 10;

  const { data: metrics } = useQuery({
    queryKey: ["pm-profiles", profileId, "metrics"],
    queryFn: () => pmProfiles.getMetrics(token, profileId),
    enabled: !!token,
  });

  const { data: ratingsData, isLoading } = useQuery({
    queryKey: ["pm-profiles", profileId, "ratings", { offset: page * PAGE_SIZE }],
    queryFn: () =>
      pmProfiles.listRatings(token, profileId, {
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    enabled: !!token,
  });

  const totalPages = ratingsData ? Math.ceil(ratingsData.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-4">
      {/* 요약 카드 */}
      <div className="grid grid-cols-4 gap-3">
        <SummaryTile
          icon={<Heart className="h-4 w-4 fill-rose-500 text-rose-500" />}
          label="좋아요"
          value={metrics?.like_count ?? 0}
          color="text-rose-700"
        />
        <SummaryTile
          icon={<Frown className="h-4 w-4 text-sky-600" />}
          label="별루예요"
          value={metrics?.dislike_count ?? 0}
          color="text-sky-700"
        />
        <SummaryTile
          icon={<MessageSquare className="h-4 w-4 text-violet-600" />}
          label="총 피드백"
          value={metrics?.total_ratings ?? 0}
          color="text-violet-700"
        />
        <SummaryTile
          icon={<BarChart3 className="h-4 w-4 text-emerald-600" />}
          label="사용횟수"
          value={metrics?.usage_count ?? 0}
          color="text-emerald-700"
        />
      </div>

      {/* 피드백 목록 */}
      {isLoading ? (
        <p className="py-6 text-center text-sm text-[var(--text-muted)]">불러오는 중...</p>
      ) : ratingsData && ratingsData.items.length > 0 ? (
        <div className="space-y-2">
          {ratingsData.items.map((r: PMRatingResponse) => (
            <FeedbackEntry key={r.id} rating={r} />
          ))}
        </div>
      ) : (
        <p className="py-6 text-center text-sm text-[var(--text-muted)]">
          아직 피드백이 없습니다
        </p>
      )}

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-1 text-xs text-[var(--text-secondary)] disabled:opacity-40 hover:bg-[var(--bg-hover)]"
          >
            이전
          </button>
          <span className="text-xs text-[var(--text-muted)]">
            {page + 1} / {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="rounded-lg border border-[var(--border-subtle)] px-3 py-1 text-xs text-[var(--text-secondary)] disabled:opacity-40 hover:bg-[var(--bg-hover)]"
          >
            다음
          </button>
        </div>
      )}
    </div>
  );
}

interface SummaryTileProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}

function SummaryTile({ icon, label, value, color }: SummaryTileProps) {
  return (
    <div className="flex flex-col items-center gap-1.5 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] py-4">
      {icon}
      <span className={`text-xl font-bold ${color}`}>{value}</span>
      <span className="text-[11px] text-[var(--text-muted)]">{label}</span>
    </div>
  );
}

function FeedbackEntry({ rating }: { rating: PMRatingResponse }) {
  const date = new Date(rating.created_at).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="flex gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-4 py-3">
      <div className="mt-0.5 shrink-0">
        {rating.reaction === "like" ? (
          <Heart className="h-4 w-4 fill-rose-500 text-rose-500" aria-label="좋아요" />
        ) : rating.reaction === "dislike" ? (
          <Frown className="h-4 w-4 text-sky-600" aria-label="별루예요" />
        ) : (
          <MessageSquare className="h-4 w-4 text-[var(--text-muted)]" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        {rating.comment ? (
          <p className="text-sm text-[var(--text-secondary)]">{rating.comment}</p>
        ) : (
          <p className="text-sm italic text-[var(--text-muted)]">코멘트 없음</p>
        )}
        <p className="mt-1 text-[11px] text-[var(--text-muted)]">{date}</p>
      </div>
    </div>
  );
}

export function PMEditForm({ profileId }: { profileId: string }) {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <PMEditFormInner profileId={profileId} />
    </RoleGuard>
  );
}
