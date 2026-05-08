"use client";

import { useState } from "react";
import { AlertTriangle } from "lucide-react";

interface ResetProjectDialogProps {
  projectName: string;
  isOpen: boolean;
  isResetting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ResetProjectDialog({
  projectName,
  isOpen,
  isResetting,
  onConfirm,
  onCancel,
}: ResetProjectDialogProps) {
  const [inputValue, setInputValue] = useState("");

  if (!isOpen) return null;

  const isConfirmEnabled = inputValue === projectName && !isResetting;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
        onKeyDown={(e) => e.key === "Escape" && onCancel()}
        role="button"
        tabIndex={0}
        aria-label="닫기"
      />

      <div className="relative w-full max-w-md mx-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8 shadow-2xl shadow-black/10">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-50">
          <AlertTriangle className="h-6 w-6 text-amber-700" />
        </div>

        <h3 className="mt-4 text-lg font-semibold text-[var(--text-primary)]">프로젝트 초기화</h3>
        <p className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">
          <strong className="text-[var(--text-secondary)]">{projectName}</strong> 프로젝트를 초기화하면
          아래 데이터가 영구적으로 삭제됩니다. 이 작업은 되돌릴 수 없습니다.
        </p>

        <ul className="mt-3 space-y-1 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
          <li>위자드 설정 (wizard_data)</li>
          <li>티켓 및 이벤트</li>
          <li>오케스트레이터 세션 및 메시지</li>
          <li>산출물 (Artifacts)</li>
          <li>에이전트 연결 정보</li>
          <li>프로젝트 설정 (project_configs)</li>
          <li>계약 오버라이드</li>
          <li>라이선스 키 (새 키로 재발급)</li>
        </ul>

        <div className="mt-4">
          <label className="block text-xs text-[var(--text-muted)] mb-1.5">
            확인을 위해 프로젝트 이름{" "}
            <strong className="text-[var(--text-secondary)]">{projectName}</strong>을 입력하세요
          </label>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={projectName}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-200"
          />
        </div>

        <div className="mt-5 flex gap-3">
          <button
            type="button"
            onClick={() => { setInputValue(""); onCancel(); }}
            className="flex-1 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          >
            취소
          </button>
          <button
            type="button"
            onClick={() => { setInputValue(""); onConfirm(); }}
            disabled={!isConfirmEnabled}
            className="flex-1 rounded-xl bg-amber-600 py-2.5 text-sm font-medium text-white shadow-lg shadow-amber-600/25 transition-all hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isResetting ? "초기화 중..." : "초기화"}
          </button>
        </div>
      </div>
    </div>
  );
}
