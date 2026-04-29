"use client";

import { Star } from "lucide-react";

import { cn } from "@/lib/utils";

interface PMRatingStarsProps {
  rating: number;
  maxStars?: number;
  size?: "sm" | "md";
  showValue?: boolean;
  className?: string;
}

export function PMRatingStars({
  rating,
  maxStars = 5,
  size = "sm",
  showValue = false,
  className,
}: PMRatingStarsProps) {
  const starSize = size === "sm" ? "h-3 w-3" : "h-4 w-4";
  const clamped = Math.max(0, Math.min(rating, maxStars));

  return (
    <div className={cn("flex items-center gap-0.5", className)}>
      {Array.from({ length: maxStars }, (_, i) => {
        const filled = i < Math.floor(clamped);
        const partial = !filled && i < clamped;
        return (
          <span key={i} className="relative inline-flex">
            {/* 빈 별 */}
            <Star className={cn(starSize, "fill-zinc-200 text-zinc-200")} />
            {/* 채워진 별 (full 또는 partial) */}
            {(filled || partial) && (
              <Star
                className={cn(
                  starSize,
                  "absolute inset-0 fill-yellow-400 text-yellow-400",
                  partial && "opacity-50",
                )}
              />
            )}
          </span>
        );
      })}
      {showValue && (
        <span className="ml-1 text-xs font-medium text-[var(--text-muted)]">
          {clamped.toFixed(1)}
        </span>
      )}
    </div>
  );
}
