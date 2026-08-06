"use client";

import { useEffect, useState } from "react";

interface DeliveryBoardFlowAnimationProps {
  /** 컬럼 강조색과 동일한 톤(기존 --chart- 계열 / --accent 토큰) */
  color: string;
}

/**
 * 티켓이 직전 단계에서 현재 단계로 넘어온 흐름을 짧은 SVG path + 파티클로 표현한다.
 * `prefers-reduced-motion: reduce` 이면 흐름 애니메이션 대신 정적 펄스(opacity keyframe)로 대체한다.
 *
 * 카드 로컬 좌표 기준으로 "왼쪽(직전 컬럼 방향)에서 카드로 들어오는" 흐름을 표현한다 —
 * 8컬럼 그리드 전체의 절대 픽셀 위치를 측정하지 않는 단순화된 표현이다.
 */
export function DeliveryBoardFlowAnimation({ color }: DeliveryBoardFlowAnimationProps) {
  const [reducedMotion, setReducedMotion] = useState(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");

    const onChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  if (reducedMotion) {
    return (
      <span
        data-testid="delivery-board-flow-static"
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 rounded-xl"
        style={{
          backgroundColor: color,
          opacity: 0.15,
          animation: "delivery-board-static-pulse 2s ease-in-out infinite",
        }}
      >
        <style>{`
          @keyframes delivery-board-static-pulse {
            0%, 100% { opacity: 0.08; }
            50% { opacity: 0.22; }
          }
        `}</style>
      </span>
    );
  }

  const path = "M0 12 C 18 12, 28 12, 56 12";

  return (
    <svg
      data-testid="delivery-board-flow-animated"
      aria-hidden="true"
      className="pointer-events-none absolute -left-8 top-1/2 h-6 w-14 -translate-y-1/2 overflow-visible"
      viewBox="0 0 56 24"
    >
      <style>{`
        @keyframes delivery-board-dash {
          to { stroke-dashoffset: -16; }
        }
      `}</style>
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeDasharray="4 4"
        strokeLinecap="round"
        opacity={0.6}
        style={{ animation: "delivery-board-dash 1s linear infinite" }}
      />
      <circle r={2.5} fill={color}>
        <animateMotion dur="1.2s" repeatCount="indefinite" path={path} />
      </circle>
    </svg>
  );
}
