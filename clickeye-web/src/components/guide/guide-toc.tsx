"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { BookOpen } from "lucide-react";
import type { GuideMeta } from "@/lib/guide-loader";

interface GuideTocProps {
  guides: GuideMeta[];
}

export function GuideToc({ guides }: GuideTocProps) {
  const pathname = usePathname();
  const t = useTranslations("guide");

  return (
    <aside className="w-52 shrink-0">
      <div className="sticky top-8">
        <div className="mb-4 flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-[var(--text-muted)]" />
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--text-muted)]">
            {t("toc")}
          </p>
        </div>
        <nav className="space-y-1">
          {guides.map((guide) => {
            const href = `/guide/${guide.slug}`;
            const isActive =
              pathname === href ||
              (pathname === "/guide" && guide.order === 1);
            return (
              <Link
                key={guide.slug}
                href={href}
                className={`block rounded-lg px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-[var(--nav-active-bg)] font-medium text-[var(--nav-active-text)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
                }`}
              >
                {guide.title}
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
