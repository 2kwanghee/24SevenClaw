import Link from "next/link";
import { ArrowRight, BookOpen } from "lucide-react";
import { getAllGuides } from "@/lib/guide-loader";
import { GuideToc } from "@/components/guide/guide-toc";

export default function GuidePage() {
  const guides = getAllGuides();

  return (
    <div className="flex gap-8">
      <GuideToc guides={guides} />

      <div className="min-w-0 flex-1">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            사용 가이드
          </h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            ClickEye 플랫폼 사용법을 단계별로 안내합니다.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {guides.map((guide) => (
            <Link
              key={guide.slug}
              href={`/guide/${guide.slug}`}
              className="group rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 transition-all hover:border-[var(--border-medium)] hover:shadow-sm"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4 shrink-0 text-[var(--text-muted)]" />
                  <h2 className="font-medium text-[var(--text-primary)]">
                    {guide.title}
                  </h2>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-[var(--text-muted)] transition-transform group-hover:translate-x-0.5" />
              </div>
              {guide.description && (
                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  {guide.description}
                </p>
              )}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
