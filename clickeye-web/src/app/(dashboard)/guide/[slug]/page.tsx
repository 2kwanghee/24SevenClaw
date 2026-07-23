import { notFound } from "next/navigation";
import { getLocale } from "next-intl/server";
import { getAllGuides, getGuide } from "@/lib/guide-loader";
import { GuideToc } from "@/components/guide/guide-toc";
import { MarkdownContent } from "@/components/guide/markdown-content";
import { BentoCard } from "@/components/ui/bento";

interface GuideSlugPageProps {
  params: Promise<{ slug: string }>;
}

export function generateStaticParams() {
  return getAllGuides().map((g) => ({ slug: g.slug }));
}

export default async function GuideSlugPage({ params }: GuideSlugPageProps) {
  const { slug } = await params;
  const locale = await getLocale();
  const guide = getGuide(slug, locale);
  if (!guide) notFound();

  const guides = getAllGuides(locale);

  return (
    <div className="flex gap-8">
      <GuideToc guides={guides} />

      <article className="min-w-0 flex-1">
        <BentoCard className="mb-6">
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            {guide.title}
          </h1>
          {guide.description && (
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              {guide.description}
            </p>
          )}
        </BentoCard>

        <BentoCard>
          <MarkdownContent content={guide.content} />
        </BentoCard>
      </article>
    </div>
  );
}
