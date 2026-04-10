"use client";

import { useEffect } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error("[ErrorBoundary]", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-red-500/10">
          <AlertTriangle className="h-8 w-8 text-red-400" />
        </div>
        <h1 className="mt-6 text-xl font-bold text-white">
          문제가 발생했습니다
        </h1>
        <p className="mt-2 text-sm text-slate-400">
          {error.message || "알 수 없는 오류가 발생했습니다. 다시 시도해 주세요."}
        </p>
        <button
          onClick={reset}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-violet-600/25 transition-all hover:bg-violet-500"
        >
          <RotateCcw className="h-4 w-4" />
          다시 시도
        </button>
      </div>
    </div>
  );
}
