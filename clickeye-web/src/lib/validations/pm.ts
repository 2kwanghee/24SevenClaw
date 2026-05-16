import { z } from "zod";

export const pmProfileSchema = z.object({
  name: z.string().min(1, "이름을 입력하세요"),
  slug: z.string().min(1, "슬러그를 입력하세요").regex(/^[a-z0-9-]+$/, "소문자, 숫자, 하이픈만 사용 가능"),
  title: z.string().optional(),
  avatar_url: z.string().url("올바른 URL을 입력하세요").optional().or(z.literal("")),
  domain: z.string().optional(),
  description: z.string().optional(),
  bio_long: z.string().optional(),
  years_experience: z
    .preprocess(
      (v) => (v === "" || v === null || v === undefined ? undefined : Number(v)),
      z.number().int().min(0).max(50).optional(),
    ),
  is_active: z.boolean(),
  language: z.string(),
  specialties: z.array(z.string()),
  tech_stack_tags: z.array(z.string()),
  industry_tags: z.array(z.string()),
  preferred_solution_types: z.array(z.string()),
  supported_platforms: z.array(z.string()),
});

export type PMProfileFormData = {
  name: string;
  slug: string;
  title?: string;
  avatar_url?: string;
  domain?: string;
  description?: string;
  bio_long?: string;
  years_experience?: number | string;
  is_active: boolean;
  language: string;
  specialties: string[];
  tech_stack_tags: string[];
  industry_tags: string[];
  preferred_solution_types: string[];
  supported_platforms: string[];
};
