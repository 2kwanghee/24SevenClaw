"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { FolderKanban, FileText, AlertCircle, ArrowRight } from "lucide-react";

type ProjectFormData = {
  name: string;
  description?: string;
};

interface ProjectFormProps {
  defaultValues?: Partial<ProjectFormData>;
  onSubmit: (data: ProjectFormData) => void;
  isSubmitting?: boolean;
  submitLabel?: string;
}

export function ProjectForm({
  defaultValues,
  onSubmit,
  isSubmitting = false,
  submitLabel,
}: ProjectFormProps) {
  const tV = useTranslations("validation");
  const tC = useTranslations("common");

  const projectSchema = useMemo(
    () =>
      z.object({
        name: z.string().min(1, tV("projectName")).max(200, tV("max200")),
        description: z.string().optional(),
      }),
    [tV],
  );

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema),
    defaultValues: {
      name: defaultValues?.name ?? "",
      description: defaultValues?.description ?? "",
    },
  });

  const resolvedSubmitLabel = submitLabel ?? tC("actions.create");

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="space-y-2">
        <label
          htmlFor="name"
          className="block text-sm font-medium text-[var(--text-secondary)]"
        >
          {tC("projectForm.nameLabel")} <span className="text-red-400">*</span>
        </label>
        <div className="relative">
          <FolderKanban className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            id="name"
            type="text"
            {...register("name")}
            className="w-full rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-3 pl-11 pr-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-all focus:border-zinc-400 focus:bg-[var(--bg-hover)] focus:ring-2 focus:ring-zinc-400/20"
            placeholder={tC("projectForm.namePlaceholder")}
          />
        </div>
        {errors.name && (
          <p className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-3 w-3" />
            {errors.name.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <label
          htmlFor="description"
          className="block text-sm font-medium text-[var(--text-secondary)]"
        >
          {tC("projectForm.descriptionLabel")}
        </label>
        <div className="relative">
          <FileText className="pointer-events-none absolute left-3.5 top-3.5 h-4 w-4 text-[var(--text-muted)]" />
          <textarea data-gramm="false" data-gramm_editor="false"
            id="description"
            rows={3}
            {...register("description")}
            className="w-full rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-3 pl-11 pr-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-all focus:border-zinc-400 focus:bg-[var(--bg-hover)] focus:ring-2 focus:ring-zinc-400/20 resize-none"
            placeholder={tC("projectForm.descriptionPlaceholder")}
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="group relative flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-zinc-900 px-4 py-3 text-sm font-semibold text-white shadow-lg transition-all hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span className="absolute inset-0 bg-gradient-to-r from-zinc-800 to-zinc-700 opacity-0 transition-opacity group-hover:opacity-100" />
        <span className="relative">
          {isSubmitting ? tC("actions.processing") : resolvedSubmitLabel}
        </span>
        {!isSubmitting && (
          <ArrowRight className="relative h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        )}
      </button>
    </form>
  );
}
