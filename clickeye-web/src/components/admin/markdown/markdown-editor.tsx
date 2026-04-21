"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownEditorProps {
  value: string;
  onChange: (v: string) => void;
  rows?: number;
}

export function MarkdownEditor({ value, onChange, rows = 28 }: MarkdownEditorProps) {
  return (
    <div className="grid grid-cols-2 gap-0 rounded-xl border border-white/10 overflow-hidden">
      {/* 편집 패널 */}
      <div className="flex flex-col border-r border-white/10">
        <div className="border-b border-white/10 px-3 py-1.5">
          <span className="text-xs text-slate-500">편집</span>
        </div>
        <textarea
          spellCheck={false}
          style={{ height: `${rows * 1.5}rem` }}
          className="w-full flex-1 resize-none bg-black/30 px-4 py-3 font-mono text-sm text-slate-300 focus:outline-none"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>

      {/* 미리보기 패널 */}
      <div className="flex flex-col">
        <div className="border-b border-white/10 px-3 py-1.5">
          <span className="text-xs text-slate-500">미리보기</span>
        </div>
        <div
          style={{ height: `${rows * 1.5}rem` }}
          className="overflow-y-auto bg-white/[0.01] px-5 py-4"
        >
          <div className="prose prose-sm prose-invert max-w-none prose-headings:text-slate-200 prose-p:text-slate-300 prose-code:text-violet-300 prose-pre:bg-black/40 prose-a:text-violet-400 prose-strong:text-slate-200 prose-li:text-slate-300">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {value || "*내용을 입력하면 여기에 미리보기가 표시됩니다.*"}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
