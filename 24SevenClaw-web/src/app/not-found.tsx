import Link from "next/link";
import { Home, SearchX } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-500/10">
          <SearchX className="h-8 w-8 text-violet-400" />
        </div>
        <h1 className="mt-6 text-4xl font-bold text-white">404</h1>
        <p className="mt-2 text-sm text-slate-400">
          요청하신 페이지를 찾을 수 없습니다
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-violet-600/25 transition-all hover:bg-violet-500"
        >
          <Home className="h-4 w-4" />
          홈으로 돌아가기
        </Link>
      </div>
    </div>
  );
}
