/** 딜리버리 진행 보드 로딩 스켈레톤 — 레인 3~4개 뼈대. */
export function DeliveryBoardSkeleton() {
  return (
    <div className="space-y-3" aria-hidden="true">
      {[0, 1, 2, 3].map((row) => (
        <div
          key={row}
          className="flex items-center gap-3 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-3"
        >
          <div className="h-4 w-28 shrink-0 animate-pulse rounded bg-[var(--border-subtle)]" />
          <div className="grid flex-1 grid-cols-8 gap-2">
            {Array.from({ length: 8 }).map((_, col) => (
              <div
                key={col}
                className="h-8 animate-pulse rounded bg-[var(--border-subtle)]"
                style={{ animationDelay: `${col * 60}ms` }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
