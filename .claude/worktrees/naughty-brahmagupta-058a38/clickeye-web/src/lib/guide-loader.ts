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

export function getAllGuides(): GuideMeta[] {
  if (!fs.existsSync(GUIDE_DIR)) return [];
  const files = fs.readdirSync(GUIDE_DIR).filter((f) => f.endsWith('.md'));
  return files
    .map((file) => {
      const slug = file.replace(/\.md$/, '');
      const raw = fs.readFileSync(path.join(GUIDE_DIR, file), 'utf-8');
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

export function getGuide(slug: string): GuideContent | null {
  const filePath = path.join(GUIDE_DIR, `${slug}.md`);
  if (!fs.existsSync(filePath)) return null;
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
