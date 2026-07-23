"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Bento 레이아웃 프리미티브.
 *
 * 시각 전용 컴포넌트 — 라우팅/데이터/동작을 포함하지 않는다.
 * accent 강조는 focus 링 등 최소 1곳에만 사용(절제).
 */

/** 반응형 CSS grid 컨테이너. 모바일 1열 → sm 2열 → lg 3열, 높이 균등(auto-rows-fr). */
export function BentoGrid({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-1 auto-rows-fr gap-4 sm:grid-cols-2 lg:grid-cols-3",
        className,
      )}
    >
      {children}
    </div>
  );
}

export type BentoCardSize = "sm" | "md" | "lg" | "wide" | "tall";

/** 카드 크기 → grid span 매핑. Tailwind 정적 클래스(동적 조합 금지). */
const sizeClasses: Record<BentoCardSize, string> = {
  sm: "",
  md: "",
  lg: "sm:col-span-2",
  wide: "sm:col-span-2 lg:col-span-3",
  tall: "lg:row-span-2",
};

interface BentoCardProps {
  size?: BentoCardSize;
  /** 지정 시 Link(<a>)로 렌더 — 카드 전체가 이동형. */
  href?: string;
  /** 지정 시 button 으로 렌더 — 카드 전체가 액션형. */
  onClick?: () => void;
  icon?: ReactNode;
  title?: ReactNode;
  description?: ReactNode;
  /** 우상단 액션 슬롯. */
  action?: ReactNode;
  className?: string;
  children?: ReactNode;
  "aria-label"?: string;
}

/**
 * Bento 카드. 라운드(2xl)·subtle 보더·다크 대응.
 * 클릭형(href/onClick)이면 hover 미세 상승 + accent focus-visible 링 + 시맨틱(a/button).
 */
export function BentoCard({
  size = "md",
  href,
  onClick,
  icon,
  title,
  description,
  action,
  className,
  children,
  "aria-label": ariaLabel,
}: BentoCardProps) {
  const interactive = Boolean(href || onClick);

  const cardClass = cn(
    "group relative flex flex-col rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 text-left transition-all",
    interactive &&
      "cursor-pointer hover:-translate-y-0.5 hover:border-[var(--border-medium)] hover:bg-[var(--bg-hover)] hover:shadow-lg focus:outline-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)]",
    sizeClasses[size],
    className,
  );

  const header =
    icon || title || description || action ? (
      <div className="flex items-start gap-3">
        {icon ? <div className="shrink-0">{icon}</div> : null}
        {title || description ? (
          <div className="min-w-0 flex-1">
            {title ? (
              <h3 className="truncate text-base font-semibold text-[var(--text-primary)]">
                {title}
              </h3>
            ) : null}
            {description ? (
              <p className="mt-0.5 text-sm text-[var(--text-muted)]">{description}</p>
            ) : null}
          </div>
        ) : null}
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    ) : null;

  const inner = (
    <>
      {header}
      {children}
    </>
  );

  if (href) {
    return (
      <Link href={href} aria-label={ariaLabel} className={cardClass}>
        {inner}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button type="button" onClick={onClick} aria-label={ariaLabel} className={cardClass}>
        {inner}
      </button>
    );
  }

  return (
    <div aria-label={ariaLabel} className={cardClass}>
      {inner}
    </div>
  );
}
