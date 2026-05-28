import { z } from "zod";

type ValidationT = (key: string) => string;

export function createPmProfileSchema(t: ValidationT) {
  return z.object({
    name: z.string().min(1, t("name")),
    slug: z
      .string()
      .min(1, t("slug"))
      .regex(/^[a-z0-9-]+$/, t("slugPattern")),
    title: z.string().optional(),
    avatar_url: z.string().url(t("url")).optional().or(z.literal("")),
    domain: z.string().optional(),
    description: z.string().optional(),
    bio_long: z.string().optional(),
    years_experience: z.preprocess(
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
}

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
