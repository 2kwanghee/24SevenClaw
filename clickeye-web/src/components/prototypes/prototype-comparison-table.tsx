"use client";

import { CheckCircle2, Star } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PrototypeOption } from "@/types/solution-wizard";

interface PrototypeComparisonTableProps {
  prototypes: PrototypeOption[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
}

/* ── 우수 지표 판정 헬퍼 ─────────────────────────────────────────────────────
   비교 대상에서 가장 낮은 개발 기간/팀 규모/비용은 ⭐ 표시.
   가장 높은 확장성은 ⭐. 복잡도는 낮을수록 ⭐ (단순).
*/

function bestIndexByMin(values: (number | null | undefined)[]): number | null {
  let best: number | null = null;
  let bestIdx: number | null = null;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v == null) continue;
    if (best === null || v < best) {
      best = v;
      bestIdx = i;
    }
  }
  return bestIdx;
}

function bestIndexByMax(values: (number | null | undefined)[]): number | null {
  let best: number | null = null;
  let bestIdx: number | null = null;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v == null) continue;
    if (best === null || v > best) {
      best = v;
      bestIdx = i;
    }
  }
  return bestIdx;
}

function rangeLabel(min?: number | null, max?: number | null, unit = ""): string {
  if (min == null && max == null) return "—";
  if (min == null) return `~${max}${unit}`;
  if (max == null) return `${min}~${unit}`;
  if (min === max) return `${min}${unit}`;
  return `${min}~${max}${unit}`;
}

function StarIcon() {
  return (
    <Star
      className="inline h-3 w-3 fill-yellow-400 text-yellow-500"
      aria-label="best in comparison"
    />
  );
}

export function PrototypeComparisonTable({
  prototypes,
  selectedId,
  onSelect,
}: PrototypeComparisonTableProps) {
  if (prototypes.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-zinc-500">
        비교할 프로토타입이 없습니다.
      </p>
    );
  }

  // 우수 지표 인덱스 계산
  const bestWeeks = bestIndexByMin(prototypes.map((p) => p.estimatedWeeksMin));
  const bestTeam = bestIndexByMin(prototypes.map((p) => p.teamSizeMin));
  const bestCost = bestIndexByMin(prototypes.map((p) => p.monthlyCostMinUsd));
  const bestComplexity = bestIndexByMin(prototypes.map((p) => p.complexityScore));
  const bestScalability = bestIndexByMax(prototypes.map((p) => p.scalabilityScore));

  // 차별점 하이라이트: 한 행에서 값이 모두 같으면 강조 안 함
  function highlight<T>(values: T[], idx: number, isBest: boolean): string {
    const allSame = values.every((v) => JSON.stringify(v) === JSON.stringify(values[0]));
    if (allSame) return "";
    if (isBest) return "bg-yellow-50 font-semibold text-zinc-900";
    return "";
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white">
      <table className="w-full min-w-[680px] text-sm">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50">
            <th className="px-3 py-2.5 text-left text-xs font-medium text-zinc-600 sticky left-0 bg-zinc-50">
              지표
            </th>
            {prototypes.map((p) => {
              const selected = selectedId === p.id;
              return (
                <th
                  key={p.id}
                  className={cn(
                    "px-3 py-2.5 text-left text-xs",
                    selected ? "bg-emerald-50" : "",
                  )}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(p.id)}
                    className="flex items-center gap-1.5 text-left"
                  >
                    {selected && (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                    )}
                    <span className="font-semibold text-zinc-900">{p.name}</span>
                    {p.isRecommended && (
                      <span className="inline-flex items-center gap-0.5 rounded border border-yellow-300 bg-yellow-50 px-1.5 py-0.5 text-[10px] font-medium text-yellow-700">
                        <Star className="h-2.5 w-2.5" />
                        추천
                      </span>
                    )}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {/* 아키텍처 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              아키텍처
            </td>
            {prototypes.map((p) => (
              <td key={p.id} className="px-3 py-2 text-xs text-zinc-800">
                {p.architecturePattern ?? "—"}
              </td>
            ))}
          </tr>

          {/* 개발 기간 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              개발 기간
            </td>
            {prototypes.map((p, i) => (
              <td
                key={p.id}
                className={cn(
                  "px-3 py-2 text-xs text-zinc-800",
                  highlight(
                    prototypes.map((x) => x.estimatedWeeksMin),
                    i,
                    bestWeeks === i,
                  ),
                )}
              >
                {bestWeeks === i && <StarIcon />}{" "}
                {rangeLabel(p.estimatedWeeksMin, p.estimatedWeeksMax, "주")}
              </td>
            ))}
          </tr>

          {/* 팀 규모 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              팀 규모
            </td>
            {prototypes.map((p, i) => (
              <td
                key={p.id}
                className={cn(
                  "px-3 py-2 text-xs text-zinc-800",
                  highlight(
                    prototypes.map((x) => x.teamSizeMin),
                    i,
                    bestTeam === i,
                  ),
                )}
              >
                {bestTeam === i && <StarIcon />}{" "}
                {rangeLabel(p.teamSizeMin, p.teamSizeMax, "명")}
                {p.teamRoles && p.teamRoles.length > 0 && (
                  <span className="ml-1 text-[10px] text-zinc-500">
                    ({p.teamRoles.join("/")})
                  </span>
                )}
              </td>
            ))}
          </tr>

          {/* 월 운영비 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              월 운영비
            </td>
            {prototypes.map((p, i) => (
              <td
                key={p.id}
                className={cn(
                  "px-3 py-2 text-xs text-zinc-800",
                  highlight(
                    prototypes.map((x) => x.monthlyCostMinUsd),
                    i,
                    bestCost === i,
                  ),
                )}
              >
                {bestCost === i && <StarIcon />} $
                {rangeLabel(p.monthlyCostMinUsd, p.monthlyCostMaxUsd)}
              </td>
            ))}
          </tr>

          {/* 복잡도 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              복잡도 (낮을수록 단순)
            </td>
            {prototypes.map((p, i) => (
              <td
                key={p.id}
                className={cn(
                  "px-3 py-2 text-xs text-zinc-800",
                  highlight(
                    prototypes.map((x) => x.complexityScore),
                    i,
                    bestComplexity === i,
                  ),
                )}
              >
                {bestComplexity === i && <StarIcon />}{" "}
                {p.complexityScore != null ? `${p.complexityScore}/10` : "—"}
              </td>
            ))}
          </tr>

          {/* 확장성 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              확장성 (높을수록 우수)
            </td>
            {prototypes.map((p, i) => (
              <td
                key={p.id}
                className={cn(
                  "px-3 py-2 text-xs text-zinc-800",
                  highlight(
                    prototypes.map((x) => x.scalabilityScore),
                    i,
                    bestScalability === i,
                  ),
                )}
              >
                {bestScalability === i && <StarIcon />}{" "}
                {p.scalabilityScore != null ? `${p.scalabilityScore}/10` : "—"}
              </td>
            ))}
          </tr>

          {/* 유지보수 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              유지보수 난이도
            </td>
            {prototypes.map((p) => (
              <td key={p.id} className="px-3 py-2 text-xs text-zinc-800">
                {p.maintenanceDifficulty === "low"
                  ? "낮음"
                  : p.maintenanceDifficulty === "high"
                    ? "높음"
                    : p.maintenanceDifficulty === "medium"
                      ? "보통"
                      : "—"}
              </td>
            ))}
          </tr>

          {/* 기술 스택 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              기술 스택
            </td>
            {prototypes.map((p) => (
              <td key={p.id} className="px-3 py-2 text-xs text-zinc-800">
                {p.techStack && p.techStack.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {p.techStack.map((t) => (
                      <span
                        key={t}
                        className="rounded border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 text-[10px]"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                ) : (
                  "—"
                )}
              </td>
            ))}
          </tr>

          {/* 필요 역량 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              필요 역량
            </td>
            {prototypes.map((p) => (
              <td key={p.id} className="px-3 py-2 text-xs text-zinc-800">
                {p.skillRequirements && p.skillRequirements.length > 0
                  ? p.skillRequirements.join(", ")
                  : "—"}
              </td>
            ))}
          </tr>

          {/* AI 매칭 근거 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              회사 적합성
            </td>
            {prototypes.map((p) => (
              <td key={p.id} className="px-3 py-2 text-xs leading-relaxed text-violet-800">
                {p.matchReasoning ?? "—"}
              </td>
            ))}
          </tr>

          {/* 장점 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              장점
            </td>
            {prototypes.map((p) => (
              <td key={p.id} className="px-3 py-2 text-xs text-zinc-800">
                {p.pros && p.pros.length > 0 ? (
                  <ul className="space-y-0.5 list-disc pl-3.5">
                    {p.pros.map((v, i) => (
                      <li key={i}>{v}</li>
                    ))}
                  </ul>
                ) : (
                  "—"
                )}
              </td>
            ))}
          </tr>

          {/* 단점 */}
          <tr>
            <td className="px-3 py-2 text-xs text-zinc-500 sticky left-0 bg-white">
              단점
            </td>
            {prototypes.map((p) => (
              <td key={p.id} className="px-3 py-2 text-xs text-zinc-800">
                {p.cons && p.cons.length > 0 ? (
                  <ul className="space-y-0.5 list-disc pl-3.5">
                    {p.cons.map((v, i) => (
                      <li key={i}>{v}</li>
                    ))}
                  </ul>
                ) : (
                  "—"
                )}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
