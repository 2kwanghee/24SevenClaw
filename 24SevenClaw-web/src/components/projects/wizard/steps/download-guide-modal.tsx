"use client";

import { useState } from "react";
import {
  X,
  Terminal,
  FolderOpen,
  CheckCircle2,
  Copy,
  Check,
  Rocket,
  FileCode2,
} from "lucide-react";
import type { PlatformId } from "@/lib/engine/platforms/types";

/* ── 플랫폼별 가이드 데이터 ── */

interface PlatformGuide {
  label: string;
  icon: string;
  steps: string[];
  command: string;
}

const PLATFORM_GUIDES: Record<string, PlatformGuide> = {
  "claude-code": {
    label: "Claude Code",
    icon: "🤖",
    steps: [
      "다운로드한 ZIP 파일을 압축 해제합니다",
      "터미널에서 프로젝트 디렉토리로 이동합니다",
      "claude 명령어를 실행합니다",
      "AI가 CLAUDE.md를 읽고 자동으로 개발을 시작합니다",
    ],
    command: "unzip project.zip && cd project && claude",
  },
  "gemini-cli": {
    label: "Gemini CLI",
    icon: "💎",
    steps: [
      "다운로드한 ZIP 파일을 압축 해제합니다",
      "터미널에서 프로젝트 디렉토리로 이동합니다",
      "gemini 명령어를 실행합니다",
      "AI가 .gemini/ 설정을 읽고 자동으로 개발을 시작합니다",
    ],
    command: "unzip project.zip && cd project && gemini",
  },
  cursor: {
    label: "Cursor",
    icon: "📝",
    steps: [
      "다운로드한 ZIP 파일을 압축 해제합니다",
      'Cursor에서 "Open Folder"로 프로젝트를 엽니다',
      ".cursorrules 파일이 자동으로 로드됩니다",
      "Cmd+L (Chat) 또는 Cmd+K (Edit)로 AI 개발을 시작합니다",
    ],
    command: "unzip project.zip && cursor project/",
  },
  codex: {
    label: "Codex",
    icon: "⚡",
    steps: [
      "다운로드한 ZIP 파일을 압축 해제합니다",
      "터미널에서 프로젝트 디렉토리로 이동합니다",
      "codex 명령어를 실행합니다",
      "AI가 설정 파일을 읽고 자동으로 개발을 시작합니다",
    ],
    command: "unzip project.zip && cd project && codex",
  },
};

/* ── 체크리스트 항목 ── */

const CHECKLIST_ITEMS = [
  { id: "unzip", label: "ZIP 파일 압축 해제" },
  { id: "env", label: ".env 파일에 API 키 설정" },
  { id: "deps", label: "의존성 설치 (npm install / pip install)" },
  { id: "run", label: "AI 에이전트 실행" },
];

/* ── Props ── */

interface DownloadGuideModalProps {
  open: boolean;
  onClose: () => void;
  platformId: PlatformId | null;
  projectName: string;
}

/* ── 메인 컴포넌트 ── */

export function DownloadGuideModal({
  open,
  onClose,
  platformId,
  projectName,
}: DownloadGuideModalProps) {
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState(false);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  if (!open) return null;

  const guide = PLATFORM_GUIDES[platformId ?? "claude-code"] ?? PLATFORM_GUIDES["claude-code"];
  const actualCommand = guide.command.replace(/project/g, projectName || "project");

  const toggleCheck = (id: string) => {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(actualCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    if (dontShowAgain) {
      try {
        localStorage.setItem("24sc-hide-download-guide", "true");
      } catch {
        // localStorage 접근 불가 시 무시
      }
    }
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 배경 오버레이 */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
        onKeyDown={(e) => e.key === "Escape" && handleClose()}
        role="button"
        tabIndex={0}
        aria-label="닫기"
      />

      {/* 모달 */}
      <div className="relative w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl shadow-black/50 sm:p-8">
        {/* 헤더 */}
        <div className="mb-6 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-lg">
              <Rocket className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">
                다운로드 완료!
              </h2>
              <p className="text-xs text-slate-400">
                {projectName}.zip 파일이 다운로드되었습니다
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* 플랫폼 실행 가이드 */}
        <div className="mb-5 rounded-xl border border-white/5 bg-white/[0.02] p-4">
          <div className="mb-3 flex items-center gap-2">
            <Terminal className="h-4 w-4 text-violet-400" />
            <span className="text-sm font-medium text-slate-200">
              {guide.icon} {guide.label} 실행 가이드
            </span>
          </div>
          <ol className="space-y-2">
            {guide.steps.map((step, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-violet-500/10 text-[10px] font-bold text-violet-400">
                  {i + 1}
                </span>
                <span className="text-sm text-slate-300">{step}</span>
              </li>
            ))}
          </ol>

          {/* 커맨드 복사 */}
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-black/30 px-3 py-2">
            <code className="flex-1 text-xs text-emerald-400 font-mono break-all">
              {actualCommand}
            </code>
            <button
              type="button"
              onClick={handleCopy}
              className="flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-300"
              title="명령어 복사"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
        </div>

        {/* 생성된 파일 구조 설명 */}
        <div className="mb-5 rounded-xl border border-white/5 bg-white/[0.02] p-4">
          <div className="mb-2 flex items-center gap-2">
            <FileCode2 className="h-4 w-4 text-violet-400" />
            <span className="text-sm font-medium text-slate-200">
              생성된 파일 구조
            </span>
          </div>
          <div className="space-y-1.5 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <FolderOpen className="h-3.5 w-3.5 text-amber-400/60" />
              <span>
                <span className="text-slate-300 font-medium">CLAUDE.md / .gemini/ / .cursorrules</span>
                {" "}— AI 에이전트 설정 파일
              </span>
            </div>
            <div className="flex items-center gap-2">
              <FolderOpen className="h-3.5 w-3.5 text-amber-400/60" />
              <span>
                <span className="text-slate-300 font-medium">.env</span>
                {" "}— API 키 및 환경 변수 (수정 필요)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <FolderOpen className="h-3.5 w-3.5 text-amber-400/60" />
              <span>
                <span className="text-slate-300 font-medium">docs/</span>
                {" "}— 프로젝트 문서 및 가이드
              </span>
            </div>
            <div className="flex items-center gap-2">
              <FolderOpen className="h-3.5 w-3.5 text-amber-400/60" />
              <span>
                <span className="text-slate-300 font-medium">scripts/</span>
                {" "}— 자동화 파이프라인 스크립트
              </span>
            </div>
          </div>
        </div>

        {/* 다음 단계 체크리스트 */}
        <div className="mb-5 rounded-xl border border-white/5 bg-white/[0.02] p-4">
          <div className="mb-3 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-violet-400" />
            <span className="text-sm font-medium text-slate-200">
              다음 단계
            </span>
          </div>
          <div className="space-y-2">
            {CHECKLIST_ITEMS.map((item) => (
              <label
                key={item.id}
                className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors hover:bg-white/[0.03]"
              >
                <input
                  type="checkbox"
                  checked={checkedItems.has(item.id)}
                  onChange={() => toggleCheck(item.id)}
                  className="h-4 w-4 rounded border-white/20 bg-white/5 text-violet-500 focus:ring-violet-500/30"
                />
                <span
                  className={`text-sm transition-colors ${
                    checkedItems.has(item.id)
                      ? "text-slate-500 line-through"
                      : "text-slate-300"
                  }`}
                >
                  {item.label}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* 하단: 다시 보지 않기 + 닫기 */}
        <div className="flex items-center justify-between">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={dontShowAgain}
              onChange={(e) => setDontShowAgain(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-white/20 bg-white/5 text-violet-500 focus:ring-violet-500/30"
            />
            <span className="text-xs text-slate-500">다시 보지 않기</span>
          </label>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-medium text-white transition-all hover:bg-violet-500"
          >
            시작하기
          </button>
        </div>
      </div>
    </div>
  );
}
