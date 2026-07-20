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
    <div className="grid grid-cols-2 gap-0 rounded-xl border border-[var(--border-subtle)] overflow-hidden">
      {/* 편집 패널 */}
      <div className="flex flex-col border-r border-[var(--border-subtle)]">
        <div className="border-b border-[var(--border-subtle)] px-3 py-1.5">
          <span className="text-xs text-[var(--text-muted)]">편집</span>
        </div>
        <textarea data-gramm="false" data-gramm_editor="false"
          spellCheck={false}
          style={{ height: `${rows * 1.5}rem` }}
          className="w-full flex-1 resize-none bg-[var(--bg-base)] px-4 py-3 font-mono text-sm text-[var(--text-primary)] focus:outline-none"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>

      {/* 미리보기 패널 */}
      <div className="flex flex-col">
        <div className="border-b border-[var(--border-subtle)] px-3 py-1.5">
          <span className="text-xs text-[var(--text-muted)]">미리보기</span>
        </div>
        <div
          style={{ height: `${rows * 1.5}rem` }}
          className="overflow-y-auto bg-[var(--bg-surface)] px-5 py-4"
        >
          <div className="prose prose-sm max-w-none prose-headings:text-[var(--text-primary)] prose-p:text-[var(--text-secondary)] prose-code:text-[var(--accent)] prose-pre:bg-[var(--bg-base)] prose-a:text-[var(--accent)] prose-strong:text-[var(--text-primary)] prose-li:text-[var(--text-secondary)]">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {value || "*내용을 입력하면 여기에 미리보기가 표시됩니다.*"}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
