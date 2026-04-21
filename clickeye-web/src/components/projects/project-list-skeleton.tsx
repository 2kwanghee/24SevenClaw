export function ProjectListSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="animate-pulse rounded-2xl border border-white/5 bg-white/[0.02] p-6"
        >
          <div className="flex items-start gap-4">
            <div className="h-10 w-10 shrink-0 rounded-xl bg-white/5" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <div className="h-5 w-32 rounded-md bg-white/5" />
                <div className="h-5 w-12 rounded-md bg-white/5" />
              </div>
              <div className="mt-1.5 h-3 w-24 rounded bg-white/5" />
            </div>
          </div>
          <div className="mt-4 space-y-2">
            <div className="h-4 w-full rounded bg-white/5" />
            <div className="h-4 w-2/3 rounded bg-white/5" />
          </div>
          <div className="mt-4 h-3 w-20 rounded bg-white/5" />
        </div>
      ))}
    </div>
  );
}
