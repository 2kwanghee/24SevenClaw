export function ArtifactSkeleton() {
  return (
    <div className="space-y-3 animate-pulse" aria-label="프리뷰 로딩 중">
      <div className="h-4 w-2/3 rounded-full bg-zinc-200" />
      <div className="h-3 w-full rounded-full bg-zinc-100" />
      <div className="h-3 w-5/6 rounded-full bg-zinc-100" />
      <div className="mt-4 h-4 w-1/2 rounded-full bg-zinc-200" />
      <div className="flex gap-2">
        <div className="h-6 w-16 rounded-full bg-zinc-100" />
        <div className="h-6 w-20 rounded-full bg-zinc-100" />
        <div className="h-6 w-14 rounded-full bg-zinc-100" />
      </div>
    </div>
  );
}
