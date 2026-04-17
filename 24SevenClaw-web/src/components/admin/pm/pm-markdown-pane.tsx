"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Code2 } from "lucide-react";
import { MarkdownEditor } from "@/components/admin/markdown/markdown-editor";

interface PMMarkdownPaneProps {
  value: string;
  onChange: (v: string) => void;
  defaultOpen?: boolean;
}

export function PMMarkdownPane({ value, onChange, defaultOpen = false }: PMMarkdownPaneProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-3.5 text-left"
      >
        <div className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="h-3.5 w-3.5 text-slate-500" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-slate-500" />
          )}
          <Code2 className="h-3.5 w-3.5 text-violet-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            MD 전체 편집
          </span>
        </div>
        <span className="text-xs text-slate-600">
          YAML frontmatter 포함 전체 마크다운
        </span>
      </button>
      {open && (
        <div className="border-t border-white/10 px-5 py-4 space-y-3">
          <p className="text-xs text-slate-600">
            <code className="rounded bg-white/5 px-1 text-slate-400">---bio---</code>
            {" "}아래 내용이 Claude PM 추천 시 사용됩니다. 저장 버튼을 눌러 적용하세요.
          </p>
          <MarkdownEditor value={value} onChange={onChange} rows={24} />
        </div>
      )}
    </div>
  );
}
