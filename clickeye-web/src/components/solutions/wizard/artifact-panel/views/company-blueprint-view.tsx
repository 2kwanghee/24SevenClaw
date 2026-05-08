import Link from "next/link";
import { Zap, Users, Layers, Code2, CheckCircle2, KeyRound } from "lucide-react";

interface CompanyBlueprintViewProps {
  result: Record<string, unknown>;
}

const COMPLEXITY_LABEL: Record<string, string> = {
  low: "낮음",
  medium: "중간",
  high: "높음",
};

const COMPLEXITY_COLOR: Record<string, string> = {
  low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  high: "bg-red-50 text-red-700 border-red-200",
};

export function CompanyBlueprintView({ result }: CompanyBlueprintViewProps) {
  if (result.status === "too_short") {
    return (
      <p className="text-xs text-zinc-400">
        솔루션 요구사항을 조금 더 입력하면 청사진이 나타납니다.
      </p>
    );
  }

  if (result.status === "api_credit_error") {
    return (
      <div className="space-y-2">
        <p className="text-xs text-amber-600">
          Anthropic API 크레딧이 부족합니다.
          {result.key_source === "server" ? " 서버 공용 키의 크레딧이 소진되었습니다." : " Plans & Billing에서 충전 후 다시 시도하세요."}
        </p>
        {result.key_source === "server" && (
          <Link
            href="/settings/anthropic"
            className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-100"
          >
            <KeyRound className="h-3 w-3" aria-hidden="true" />
            내 API 키 등록하기 →
          </Link>
        )}
      </div>
    );
  }

  if (result.status === "api_auth_error") {
    return (
      <div className="space-y-2">
        <p className="text-xs text-red-600">
          API 키 인증에 실패했습니다.
          {result.key_source === "user" ? " 설정 페이지에서 키를 확인하세요." : " ANTHROPIC_API_KEY 설정을 확인하세요."}
        </p>
        {result.key_source === "user" && (
          <Link
            href="/settings/anthropic"
            className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-100"
          >
            <KeyRound className="h-3 w-3" aria-hidden="true" />
            API 키 재설정 →
          </Link>
        )}
      </div>
    );
  }

  if (result.status === "api_error" || result.status === "error") {
    return (
      <p className="text-xs text-zinc-400">
        일시적인 오류가 발생했습니다. 잠시 후 다시 입력해 보세요.
      </p>
    );
  }

  const primaryTag = (result.primary_tag as string) ?? "";
  const tags = (result.tags as string[]) ?? [];
  const features = (result.features as string[]) ?? [];
  const complexity = (result.complexity as string) ?? "medium";
  const targetUsers = (result.target_users as string) ?? "";
  const techStack = (result.tech_stack as Record<string, string>) ?? {};
  const keyRequirements = (result.key_requirements as string[]) ?? [];

  return (
    <div className="space-y-4 text-sm">
      {/* 솔루션 타입 + 복잡도 */}
      <div className="flex items-center gap-2 flex-wrap">
        {primaryTag && (
          <span className="inline-flex items-center rounded-full bg-zinc-900 px-2.5 py-0.5 text-xs font-semibold text-white">
            {primaryTag}
          </span>
        )}
        {tags.filter((t) => t !== primaryTag).slice(0, 3).map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center rounded-full border border-zinc-200 px-2.5 py-0.5 text-xs text-zinc-600"
          >
            {tag}
          </span>
        ))}
        {complexity && (
          <span
            className={`ml-auto inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${COMPLEXITY_COLOR[complexity] ?? COMPLEXITY_COLOR.medium}`}
          >
            <Zap className="mr-1 h-3 w-3" aria-hidden="true" />
            복잡도 {COMPLEXITY_LABEL[complexity] ?? complexity}
          </span>
        )}
      </div>

      {/* 대상 사용자 */}
      {targetUsers && (
        <div className="flex items-start gap-2">
          <Users className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-400" aria-hidden="true" />
          <p className="text-xs text-zinc-600 leading-relaxed">{targetUsers}</p>
        </div>
      )}

      {/* 핵심 기능 */}
      {features.length > 0 && (
        <div>
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            <Layers className="h-3 w-3" aria-hidden="true" />
            핵심 기능
          </p>
          <ul className="space-y-1">
            {features.slice(0, 5).map((f) => (
              <li key={f} className="flex items-start gap-1.5 text-xs text-zinc-700">
                <CheckCircle2 className="mt-0.5 h-3 w-3 shrink-0 text-emerald-500" aria-hidden="true" />
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 추천 기술 스택 */}
      {Object.keys(techStack).length > 0 && (
        <div>
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            <Code2 className="h-3 w-3" aria-hidden="true" />
            추천 기술 스택
          </p>
          <div className="rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 space-y-1">
            {Object.entries(techStack)
              .filter(([, v]) => v && v !== "null")
              .map(([k, v]) => (
                <div key={k} className="flex items-center justify-between text-xs">
                  <span className="text-zinc-500 capitalize">{k}</span>
                  <span className="font-medium text-zinc-800">{v}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* 핵심 요구사항 */}
      {keyRequirements.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            핵심 요구사항
          </p>
          <ul className="space-y-1">
            {keyRequirements.slice(0, 4).map((r) => (
              <li key={r} className="text-xs text-zinc-600 pl-3 border-l-2 border-zinc-200">
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
