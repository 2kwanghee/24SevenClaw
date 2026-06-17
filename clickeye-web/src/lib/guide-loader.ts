import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

export interface GuideMeta {
  slug: string;
  title: string;
  description: string;
  order: number;
}

export interface GuideContent extends GuideMeta {
  content: string;
}

const GUIDE_DIR = path.join(process.cwd(), 'public', 'user-guide');

// 로케일별 마크다운은 `<slug>.<locale>.md` 접미사로 둔다.
// 기본(한국어)은 접미사 없는 `<slug>.md`. 해당 로케일 파일이 없으면 한국어로 폴백.
const LOCALE_SUFFIXES = ['en', 'ja', 'id'] as const;
const LOCALE_FILE_RE = /\.(en|ja|id)\.md$/;

/** 정규 slug 목록의 기준이 되는 기본(한국어) 파일들. */
function baseFiles(): string[] {
  return fs
    .readdirSync(GUIDE_DIR)
    .filter((f) => f.endsWith('.md') && !LOCALE_FILE_RE.test(f));
}

/** slug + locale 에 해당하는 실제 파일 경로(없으면 한국어 폴백, 그것도 없으면 null). */
function resolveFile(slug: string, locale?: string): string | null {
  if (locale && (LOCALE_SUFFIXES as readonly string[]).includes(locale)) {
    const localized = path.join(GUIDE_DIR, `${slug}.${locale}.md`);
    if (fs.existsSync(localized)) return localized;
  }
  const base = path.join(GUIDE_DIR, `${slug}.md`);
  return fs.existsSync(base) ? base : null;
}

export function getAllGuides(locale?: string): GuideMeta[] {
  if (!fs.existsSync(GUIDE_DIR)) return [];
  return baseFiles()
    .map((file) => {
      const slug = file.replace(/\.md$/, '');
      const filePath = resolveFile(slug, locale) ?? path.join(GUIDE_DIR, file);
      const raw = fs.readFileSync(filePath, 'utf-8');
      const { data } = matter(raw);
      return {
        slug,
        title: (data.title as string) ?? slug,
        description: (data.description as string) ?? '',
        order: (data.order as number) ?? 99,
      };
    })
    .sort((a, b) => a.order - b.order);
}

export function getGuide(slug: string, locale?: string): GuideContent | null {
  const filePath = resolveFile(slug, locale);
  if (!filePath) return null;
  const raw = fs.readFileSync(filePath, 'utf-8');
  const { data, content } = matter(raw);
  return {
    slug,
    title: (data.title as string) ?? slug,
    description: (data.description as string) ?? '',
    order: (data.order as number) ?? 99,
    content,
  };
}
