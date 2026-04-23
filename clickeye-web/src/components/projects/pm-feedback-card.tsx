"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Heart, Frown, SendHorizontal, UserCircle2, Star } from "lucide-react";

import { cn } from "@/lib/utils";
import { pmProfiles, type PMProfileWithMetrics } from "@/lib/api-client";

interface PMFeedbackCardProps {
  projectId: string;
  pmProfileId: string;
  sessionId: string;
}

const STORAGE_KEY = (projectId: string) => `pm_rated_${projectId}`;

export function PMFeedbackCard({
  projectId,
  pmProfileId,
  sessionId,
}: PMFeedbackCardProps) {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const [pmProfile, setPmProfile] = useState<PMProfileWithMetrics | null>(null);
  const [reaction, setReaction] = useState<"like" | "dislike" | null>(null);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  // 이미 제출했으면 숨김
  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY(projectId));
    if (done === "1") setDismissed(true);
  }, [projectId]);

  // PM 프로필 로드
  useEffect(() => {
    if (!token || !pmProfileId) return;
    void pmProfiles.get(token, pmProfileId).then(setPmProfile).catch(() => {});
  }, [token, pmProfileId]);

  const handleSubmit = async () => {
    if (!reaction) return;
    setLoading(true);
    try {
      await pmProfiles.createRating(token, pmProfileId, {
        session_id: sessionId,
        reaction,
        comment: comment.trim() || undefined,
      });
    } catch {
      // 실패해도 제출 완료로 처리
    } finally {
      setLoading(false);
      setSubmitted(true);
      localStorage.setItem(STORAGE_KEY(projectId), "1");
    }
  };

  const handleDismiss = () => {
    setDismissed(true);
    localStorage.setItem(STORAGE_KEY(projectId), "1");
  };

  if (dismissed) return null;

  return (
    <div className="mt-6 rounded-2xl border border-violet-500/20 bg-violet-500/5 p-6">
      <div className="mb-4 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-violet-500/15">
            <Star className="h-4 w-4 text-violet-400" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">PM 피드백</h3>
            <p className="text-xs text-slate-500">
              사용 중인 PM에 대한 평가를 남겨주세요
            </p>
          </div>
        </div>
        {!submitted && (
          <button
            type="button"
            onClick={handleDismiss}
            className="text-[11px] text-slate-600 hover:text-slate-400 transition-colors"
          >
            나중에
          </button>
        )}
      </div>

      {/* PM 정보 */}
      {pmProfile && (
        <div className="mb-4 flex items-center gap-2.5 rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-500/10">
            <UserCircle2 className="h-4.5 w-4.5 text-violet-400" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-slate-200">
              {pmProfile.name}
            </p>
            <p className="truncate text-[11px] text-slate-500">
              {pmProfile.title ?? pmProfile.domain ?? pmProfile.specialties?.[0] ?? ""}
            </p>
          </div>
          <div className="ml-auto shrink-0 text-right">
            <p className="text-xs font-medium text-violet-300">
              {pmProfile.usage_count}회
            </p>
            <p className="text-[10px] text-slate-600">사용됨</p>
          </div>
        </div>
      )}

      {submitted ? (
        <div className="flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2.5">
          <Heart className="h-4 w-4 text-emerald-400" aria-hidden="true" />
          <p className="text-xs text-emerald-300">
            피드백을 보내주셔서 감사합니다. PM 개선에 반영됩니다.
          </p>
        </div>
      ) : (
        <>
          {/* 리액션 버튼 */}
          <div className="mb-3 flex gap-2">
            <button
              type="button"
              onClick={() => setReaction("like")}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 rounded-xl border py-2.5 text-sm font-medium transition-all",
                reaction === "like"
                  ? "border-rose-500/50 bg-rose-500/15 text-rose-300"
                  : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20 hover:bg-white/[0.06]",
              )}
            >
              <Heart
                className={cn(
                  "h-4 w-4",
                  reaction === "like" ? "fill-rose-400 text-rose-400" : "",
                )}
                aria-hidden="true"
              />
              좋아요
            </button>
            <button
              type="button"
              onClick={() => setReaction("dislike")}
              className={cn(
                "flex flex-1 items-center justify-center gap-2 rounded-xl border py-2.5 text-sm font-medium transition-all",
                reaction === "dislike"
                  ? "border-sky-500/50 bg-sky-500/15 text-sky-300"
                  : "border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/20 hover:bg-white/[0.06]",
              )}
            >
              <Frown className="h-4 w-4" aria-hidden="true" />
              별루예요
            </button>
          </div>

          {/* 텍스트 피드백 */}
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="어떤 업무를 잘 처리하는지, 어떤 점이 아쉬웠는지 자유롭게 적어주세요. PM 개선에 큰 도움이 됩니다."
            rows={3}
            className="mb-3 w-full resize-none rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-slate-300 placeholder-slate-600 focus:border-violet-500/40 focus:outline-none focus:ring-1 focus:ring-violet-500/20 transition-colors"
          />

          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={!reaction || loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 py-2.5 text-sm font-medium text-white shadow-lg shadow-violet-600/20 transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <SendHorizontal className="h-4 w-4" aria-hidden="true" />
            {loading ? "전송 중..." : "피드백 보내기"}
          </button>
        </>
      )}
    </div>
  );
}
