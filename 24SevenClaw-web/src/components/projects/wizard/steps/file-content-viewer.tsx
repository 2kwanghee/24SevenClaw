"use client";

import { Copy, Check, FileCode2 } from "lucide-react";
import { useState, useCallback } from "react";

interface FileContentViewerProps {
  path: string | null;
  content: string | null;
}

const EXT_LANG_MAP: Record<string, string> = {
  ts: "TypeScript",
  tsx: "TypeScript (React)",
  js: "JavaScript",
  jsx: "JavaScript (React)",
  py: "Python",
  md: "Markdown",
  json: "JSON",
  yaml: "YAML",
  yml: "YAML",
  toml: "TOML",
  sh: "Shell",
  env: "Environment",
  css: "CSS",
  html: "HTML",
};

function getLanguageLabel(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  return EXT_LANG_MAP[ext] ?? (ext.toUpperCase() || "Text");
}

export function FileContentViewer({ path, content }: FileContentViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    if (!content) return;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [content]);

  if (!path || content === null) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
        <FileCode2 className="h-10 w-10 text-slate-600" />
        <p className="text-sm text-slate-500">
          파일을 선택하면 내용을 미리볼 수 있습니다
        </p>
      </div>
    );
  }

  const fileName = path.split("/").pop() ?? path;
  const langLabel = getLanguageLabel(path);
  const lines = content.split("\n");

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* 파일 헤더 */}
      <div className="flex items-center justify-between border-b border-white/5 px-4 py-2">
        <div className="flex items-center gap-2 overflow-hidden">
          <FileCode2 className="h-3.5 w-3.5 shrink-0 text-violet-400" />
          <span className="truncate text-xs font-medium text-slate-300">
            {fileName}
          </span>
          <span className="shrink-0 rounded bg-white/5 px-1.5 py-0.5 text-[10px] text-slate-500">
            {langLabel}
          </span>
        </div>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300"
          title="클립보드에 복사"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-400" />
              <span className="text-emerald-400">복사됨</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>복사</span>
            </>
          )}
        </button>
      </div>

      {/* 코드 영역 */}
      <div className="flex-1 overflow-auto">
        <div className="flex min-w-0">
          {/* 라인 넘버 */}
          <div className="sticky left-0 shrink-0 border-r border-white/5 bg-black/20 px-3 py-3 text-right">
            {lines.map((_, i) => (
              <div
                key={i}
                className="text-[11px] leading-5 text-slate-600 select-none"
              >
                {i + 1}
              </div>
            ))}
          </div>
          {/* 코드 내용 */}
          <pre className="flex-1 overflow-x-auto px-4 py-3">
            <code className="text-[11px] leading-5 text-slate-300">
              {content}
            </code>
          </pre>
        </div>
      </div>
    </div>
  );
}
