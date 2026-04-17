"use client";

import { useState } from "react";
import { AlertCircle, Save, X } from "lucide-react";

interface OverrideEditorProps {
  initialContent: Record<string, unknown>;
  allowedFields: string[];
  isLocked: boolean;
  isPending?: boolean;
  onSave: (content: Record<string, unknown>) => void;
  onCancel: () => void;
}

export function OverrideEditor({
  initialContent,
  allowedFields,
  isLocked,
  isPending,
  onSave,
  onCancel,
}: OverrideEditorProps) {
  const [jsonText, setJsonText] = useState(
    JSON.stringify(initialContent, null, 2),
  );
  const [parseError, setParseError] = useState<string | null>(null);

  const handleSave = () => {
    try {
      const parsed = JSON.parse(jsonText) as Record<string, unknown>;

      // 잠금된 계약이면 허용된 필드만 검증
      if (isLocked && allowedFields.length > 0) {
        const invalidKeys = Object.keys(parsed).filter(
          (key) => !allowedFields.includes(key),
        );
        if (invalidKeys.length > 0) {
          setParseError(
            `허용되지 않은 필드: ${invalidKeys.join(", ")}. 허용된 필드: ${allowedFields.join(", ")}`,
          );
          return;
        }
      }

      setParseError(null);
      onSave(parsed);
    } catch {
      setParseError("유효한 JSON 형식이 아닙니다");
    }
  };

  return (
    <div className="space-y-4">
      {/* 허용 필드 안내 */}
      {isLocked && allowedFields.length > 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2.5">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
          <p className="text-xs text-amber-300">
            이 계약은 잠금 상태입니다. 오버라이드 가능한 필드:{" "}
            <span className="font-medium">{allowedFields.join(", ")}</span>
          </p>
        </div>
      )}

      {/* JSON 에디터 */}
      <textarea
        value={jsonText}
        onChange={(e) => {
          setJsonText(e.target.value);
          setParseError(null);
        }}
        rows={12}
        spellCheck={false}
        className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 font-mono text-xs leading-relaxed text-slate-300 placeholder:text-slate-600 focus:border-violet-500/30 focus:outline-none focus:ring-1 focus:ring-violet-500/20"
        placeholder='{ "key": "value" }'
      />

      {/* 파싱 에러 */}
      {parseError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
          <AlertCircle className="h-3.5 w-3.5 shrink-0 text-red-400" />
          <p className="text-xs text-red-300">{parseError}</p>
        </div>
      )}

      {/* 액션 버튼 */}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm font-medium text-slate-400 transition-colors hover:bg-white/[0.05] hover:text-slate-200"
        >
          <X className="h-3.5 w-3.5" />
          취소
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={isPending}
          className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Save className="h-3.5 w-3.5" />
          {isPending ? "저장 중..." : "저장"}
        </button>
      </div>
    </div>
  );
}
