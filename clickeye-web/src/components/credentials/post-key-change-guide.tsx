"use client";

import { useState, useCallback } from "react";
import { Check, Copy, KeyRound, X } from "lucide-react";
import { type ProjectResponse } from "@/lib/api-client";

interface PostKeyChangeGuideProps {
  open: boolean;
  onClose: () => void;
  channel: "anthropic" | "linear";
  staleProjects: ProjectResponse[];
}

const STEPS = [
  {
    label: "1. 로컬 프로젝트 루트의 .env 파일을 엽니다",
  },
  {
    label: "2. 변경된 키 값을 새 값으로 덮어씁니다",
  },
  {
    label: "3. 갱신 스크립트 실행",
    code: "bash scripts/refresh-env.sh",
  },
  {
    label: "4. (선택) Claude Code 세션이 열려있다면 재시작",
    detail: "Ctrl+C → claude (프로젝트 루트에서)",
  },
];

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className="ml-2 p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
      title="복사"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

export function PostKeyChangeGuide({
  open,
  onClose,
  channel,
  staleProjects,
}: PostKeyChangeGuideProps) {
  if (!open) return null;

  const channelLabel = channel === "anthropic" ? "Anthropic" : "Linear";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="relative w-full max-w-lg rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-xl overflow-hidden">
        {/* 헤더 */}
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100">
              <KeyRound className="h-4 w-4 text-amber-600" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                {channelLabel} API 키가 변경되었습니다
              </h2>
              <p className="text-xs text-[var(--text-muted)]">
                로컬 .env 파일을 갱신해야 새 키가 적용됩니다
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--text-muted)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="overflow-y-auto max-h-[70vh] px-6 py-5 space-y-5">
          {/* 영향 받는 프로젝트 */}
          {staleProjects.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-[var(--text-secondary)]">
                .env 갱신이 필요한 프로젝트 ({staleProjects.length}개)
              </p>
              <div className="space-y-2">
                {staleProjects.map((p) => (
                  <div
                    key={p.id}
                    className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-hover)] px-4 py-3"
                  >
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">{p.name}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 단계별 가이드 */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-[var(--text-secondary)]">로컬 적용 방법</p>
            <ol className="space-y-3">
              {STEPS.map((step, i) => (
                <li key={i} className="flex gap-3">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--bg-hover)] text-xs font-semibold text-[var(--text-secondary)]">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-[var(--text-primary)]">{step.label}</p>
                    {step.code && (
                      <div className="mt-1.5 flex items-center rounded-md bg-zinc-900 px-3 py-1.5">
                        <code className="flex-1 text-xs text-zinc-100 font-mono select-all">
                          {step.code}
                        </code>
                        <CopyButton text={step.code} />
                      </div>
                    )}
                    {step.detail && (
                      <p className="mt-1 text-xs text-[var(--text-muted)]">{step.detail}</p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {/* 푸터 */}
        <div className="border-t border-[var(--border-subtle)] px-6 py-4 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
          >
            확인
          </button>
        </div>
      </div>
    </div>
  );
}
