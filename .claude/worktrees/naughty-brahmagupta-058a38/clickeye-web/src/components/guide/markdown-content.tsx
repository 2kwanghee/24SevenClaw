"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface MarkdownContentProps {
  content: string;
}

const components: Components = {
  h1: ({ children }) => (
    <h1 className="mb-4 mt-0 text-xl font-bold text-[var(--text-primary)]">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-3 mt-6 text-base font-semibold text-[var(--text-primary)]">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-2 mt-4 text-sm font-semibold text-[var(--text-primary)]">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="mb-3 text-sm leading-relaxed text-[var(--text-secondary)]">
      {children}
    </p>
  ),
  ul: ({ children }) => (
    <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-[var(--text-secondary)]">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-3 list-decimal space-y-1 pl-5 text-sm text-[var(--text-secondary)]">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  pre: ({ children }) => (
    <pre className="mb-3 overflow-x-auto rounded-lg bg-[var(--bg-hover)] p-4 text-xs">
      {children}
    </pre>
  ),
  code: ({ children, className }) => {
    const isBlock = Boolean(className?.includes("language-"));
    return isBlock ? (
      <code className="font-mono text-[var(--text-primary)]">{children}</code>
    ) : (
      <code className="rounded bg-[var(--bg-hover)] px-1.5 py-0.5 font-mono text-xs text-[var(--text-primary)]">
        {children}
      </code>
    );
  },
  blockquote: ({ children }) => (
    <blockquote className="mb-3 border-l-2 border-[var(--border-medium)] pl-4 text-sm text-[var(--text-muted)]">
      {children}
    </blockquote>
  ),
  a: ({ children, href }) => (
    <a
      href={href}
      className="text-[var(--nav-active-text)] underline-offset-2 hover:underline"
    >
      {children}
    </a>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-[var(--text-primary)]">
      {children}
    </strong>
  ),
  hr: () => (
    <hr className="my-6 border-[var(--border-subtle)]" />
  ),
};

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
