"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import {
  CheckCircle2,
  Download,
  Eye,
  FolderTree,
  Loader2,
  AlertCircle,
  RefreshCw,
  FileCode2,
  Building2,
  Layers,
  Bot,
  Wrench,
  GitBranch,
  Monitor,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useWizardStore } from "@/stores/wizard-store";
import {
  apiClient,
  ApiClientError,
  type PreviewRequest,
  type PreviewResponse,
} from "@/lib/api-client";

import { FileTreePreview } from "./file-tree-preview";
import { FileContentViewer } from "./file-content-viewer";
import { DownloadGuideModal } from "./download-guide-modal";

/* ── 라벨 맵 ── */

const SOLUTION_TYPE_LABELS: Record<string, string> = {
  saas: "SaaS",
  "rest-api": "REST API",
  fullstack: "풀스택",
  "internal-tool": "내부 도구",
  mvp: "MVP",
  custom: "커스텀",
};

const PLATFORM_LABELS: Record<string, string> = {
  "claude-code": "Claude Code",
  "gemini-cli": "Gemini CLI",
  codex: "Codex",
  cursor: "Cursor",
};

/* ── 진행 단계 시뮬레이션 메시지 ── */

const PROGRESS_MESSAGES = [
  "에이전트 프로필 생성 중...",
  "스킬 설정 파일 구성 중...",
  "파이프라인 워크플로우 작성 중...",
  "프로젝트 가이드(CLAUDE.md) 생성 중...",
  "파일 구조 최종 정리 중...",
];

/* ── 위저드 데이터 → API 요청 변환 ── */

function buildPreviewRequest(): PreviewRequest {
  const { data } = useWizardStore.getState();
  return {
    organization: data.organization as unknown as Record<string, unknown>,
    solution: data.solution as unknown as Record<string, unknown>,
    agents: data.agents.selectedAgents,
    skills: data.skills.selectedSkills.map((s) => s.id),
    pipelines: data.pipelines.selectedPipelines,
    platform: data.platform as unknown as Record<string, unknown>,
  };
}

/* ── 메인 컴포넌트 ── */

export function StepPreview() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const organization = useWizardStore((s) => s.data.organization);
  const solution = useWizardStore((s) => s.data.solution);
  const agents = useWizardStore((s) => s.data.agents);
  const skills = useWizardStore((s) => s.data.skills);
  const pipelines = useWizardStore((s) => s.data.pipelines);
  const platform = useWizardStore((s) => s.data.platform);

  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(false);

  /* 진행 상황 시뮬레이션 */
  const [progressStep, setProgressStep] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);

  useEffect(() => {
    if (!loading) return;
    setProgressStep(0);
    setProgressPercent(0);

    let elapsed = 0;
    const stepDuration = 1500;
    const totalDuration = PROGRESS_MESSAGES.length * stepDuration;
    const tickInterval = 80;

    const timer = setInterval(() => {
      elapsed += tickInterval;
      const step = Math.min(
        Math.floor(elapsed / stepDuration),
        PROGRESS_MESSAGES.length - 1,
      );
      setProgressStep(step);
      setProgressPercent(Math.min(90, (elapsed / totalDuration) * 90));
    }, tickInterval);

    return () => clearInterval(timer);
  }, [loading]);

  /* 프리뷰 로드 */
  const loadPreview = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const req = buildPreviewRequest();
      const res = await apiClient.projects.previewDraft(token, req);
      setPreview(res);
      // 첫 번째 파일 자동 선택
      const firstFile = findFirstFile(res.file_tree);
      if (firstFile) setSelectedFile(firstFile);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.detail);
      } else {
        setError("프리뷰를 불러오는 중 오류가 발생했습니다");
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadPreview();
  }, [loadPreview]);

  /* ZIP 다운로드 */
  const handleDownload = useCallback(async () => {
    if (!token) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      const req = buildPreviewRequest();
      const blob = await apiClient.projects.generateZipDraft(token, {
        ...req,
        env_vars: {},
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${solution.projectName || "project"}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      // "다시 보지 않기" 설정이 없으면 가이드 모달 표시
      try {
        if (localStorage.getItem("24sc-hide-download-guide") !== "true") {
          setShowGuide(true);
        }
      } catch {
        setShowGuide(true);
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        setDownloadError(err.detail);
      } else {
        setDownloadError("ZIP 다운로드에 실패했습니다");
      }
    } finally {
      setDownloading(false);
    }
  }, [token, solution.projectName]);

  const fileCount = preview ? Object.keys(preview.files).length : 0;
  const totalBytes = useMemo(() => {
    if (!preview) return 0;
    const encoder = new TextEncoder();
    return Object.values(preview.files).reduce(
      (sum, content) => sum + encoder.encode(content).length,
      0,
    );
  }, [preview]);
  const selectedContent =
    preview && selectedFile ? (preview.files[selectedFile] ?? null) : null;

  return (
    <div className="space-y-6">
      {/* 설정 요약 카드 */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        <SummaryBadge
          icon={Building2}
          label="회사"
          value={organization.companyName || "미설정"}
        />
        <SummaryBadge
          icon={Layers}
          label="솔루션"
          value={
            solution.solutionType
              ? SOLUTION_TYPE_LABELS[solution.solutionType] ?? solution.solutionType
              : "미설정"
          }
        />
        <SummaryBadge
          icon={Bot}
          label="에이전트"
          value={
            agents.selectedAgents.length > 0
              ? `${agents.selectedAgents.length}개`
              : "미설정"
          }
        />
        <SummaryBadge
          icon={Wrench}
          label="스킬"
          value={
            skills.selectedSkills.length > 0
              ? `${skills.selectedSkills.length}개`
              : "미설정"
          }
        />
        <SummaryBadge
          icon={GitBranch}
          label="파이프라인"
          value={
            pipelines.selectedPipelines.length > 0
              ? `${pipelines.selectedPipelines.length}개`
              : "미설정"
          }
        />
        <SummaryBadge
          icon={Monitor}
          label="플랫폼"
          value={
            platform.platformId
              ? PLATFORM_LABELS[platform.platformId] ?? platform.platformId
              : "미설정"
          }
        />
      </div>

      {/* 에러 표시 */}
      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
          <p className="flex-1 text-sm text-red-300">{error}</p>
          <button
            type="button"
            onClick={loadPreview}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-red-300 transition-colors hover:bg-red-500/10"
          >
            <RefreshCw className="h-3 w-3" />
            재시도
          </button>
        </div>
      )}

      {/* 로딩 - 진행 상황 시뮬레이션 */}
      {loading && (
        <div className="flex flex-col items-center justify-center gap-5 py-12">
          <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
          <div className="w-full max-w-sm space-y-3">
            <div
              className="h-1.5 w-full overflow-hidden rounded-full bg-white/5"
              role="progressbar"
              aria-valuenow={Math.round(progressPercent)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="프리뷰 생성 진행률"
            >
              <div
                className="h-full rounded-full bg-violet-500 transition-all duration-300 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <p className="text-center text-sm text-slate-400">
              {PROGRESS_MESSAGES[progressStep]}
            </p>
          </div>
        </div>
      )}

      {/* 생성 완료 요약 */}
      {!loading && preview && (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
            <span className="text-sm font-medium text-emerald-300">
              {fileCount}개 파일 생성 완료
            </span>
            <span className="text-xs text-slate-500">
              · 총 {formatBytes(totalBytes)}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            이 파일들은 선택한 설정을 기반으로 자동 생성되었습니다
          </p>
        </div>
      )}

      {/* 프리뷰 패널 (2-column) */}
      {!loading && preview && (
        <>
          {/* 헤더 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-violet-400" />
              <span className="text-sm font-medium text-slate-300">
                생성 파일 프리뷰
              </span>
              <span className="rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-slate-500">
                {fileCount}개 파일
              </span>
            </div>
            <button
              type="button"
              onClick={loadPreview}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300"
              title="프리뷰 새로고침"
            >
              <RefreshCw className="h-3 w-3" />
              새로고침
            </button>
          </div>

          {/* 2-column 레이아웃 (모바일: 탭 전환, 데스크탑: 나란히) */}
          <div className="overflow-hidden rounded-xl border border-white/10 bg-white/[0.02]">
            {/* 모바일: 탭 토글 */}
            <div className="flex border-b border-white/5 sm:hidden">
              <button
                type="button"
                onClick={() => setSelectedFile(null)}
                className={cn(
                  "flex-1 px-4 py-2 text-xs font-medium transition-colors",
                  !selectedFile
                    ? "border-b-2 border-violet-500 text-violet-300"
                    : "text-slate-500 hover:text-slate-300",
                )}
              >
                <FolderTree className="mr-1.5 inline-block h-3.5 w-3.5" />
                파일 트리
              </button>
              <button
                type="button"
                onClick={() => {
                  if (!selectedFile) {
                    const first = findFirstFile(preview.file_tree);
                    if (first) setSelectedFile(first);
                  }
                }}
                className={cn(
                  "flex-1 px-4 py-2 text-xs font-medium transition-colors",
                  selectedFile
                    ? "border-b-2 border-violet-500 text-violet-300"
                    : "text-slate-500 hover:text-slate-300",
                )}
              >
                <FileCode2 className="mr-1.5 inline-block h-3.5 w-3.5" />
                파일 내용
              </button>
            </div>

            <div className="flex" style={{ height: "400px" }}>
              {/* 좌: 파일 트리 */}
              <div className={cn(
                "w-full shrink-0 overflow-y-auto border-r border-white/5 p-2 sm:block sm:w-60",
                selectedFile ? "hidden" : "block",
              )}>
                <div className="mb-2 flex items-center gap-1.5 px-2 py-1">
                  <FolderTree className="h-3.5 w-3.5 text-violet-400" />
                  <span className="text-[10px] font-medium uppercase tracking-wider text-slate-500">
                    파일 트리
                  </span>
                </div>
                <FileTreePreview
                  tree={preview.file_tree}
                  selectedPath={selectedFile}
                  onSelectFile={setSelectedFile}
                />
              </div>

              {/* 우: 파일 내용 */}
              <div className={cn(
                "flex-1 overflow-hidden",
                selectedFile ? "block" : "hidden sm:block",
              )}>
                <FileContentViewer
                  path={selectedFile}
                  content={selectedContent}
                />
              </div>
            </div>
          </div>
        </>
      )}

      {/* 다운로드 버튼 */}
      <div className="flex flex-col items-center gap-3 pt-2">
        {downloadError && (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
            <AlertCircle className="h-3.5 w-3.5 text-red-400" />
            <p className="text-xs text-red-300">{downloadError}</p>
          </div>
        )}
        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading || loading}
          className="flex items-center gap-2 rounded-xl bg-violet-600 px-6 py-3 text-sm font-medium text-white transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {downloading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              다운로드 중...
            </>
          ) : (
            <>
              <Download className="h-4 w-4" />
              ZIP 다운로드
            </>
          )}
        </button>
        <p className="text-xs text-slate-500">
          설정에 따라 생성된 프로젝트 파일을 다운로드합니다
        </p>
      </div>

      {/* 다운로드 후 실행 가이드 모달 */}
      <DownloadGuideModal
        open={showGuide}
        onClose={() => setShowGuide(false)}
        platformId={platform.platformId}
        projectName={solution.projectName || "project"}
      />
    </div>
  );
}

/* ── 요약 배지 ── */

interface SummaryBadgeProps {
  icon: typeof Building2;
  label: string;
  value: string;
}

function SummaryBadge({ icon: Icon, label, value }: SummaryBadgeProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2">
      <Icon className="h-3.5 w-3.5 shrink-0 text-violet-400/60" />
      <div className="min-w-0">
        <p className="text-[10px] text-slate-600">{label}</p>
        <p className="truncate text-xs font-medium text-slate-300">{value}</p>
      </div>
    </div>
  );
}

/* ── 유틸 ── */

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function findFirstFile(
  nodes: PreviewResponse["file_tree"],
): string | null {
  for (const node of nodes) {
    if (node.type === "file") return node.path;
    if (node.children.length > 0) {
      const found = findFirstFile(node.children);
      if (found) return found;
    }
  }
  return null;
}
