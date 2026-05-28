"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { Info } from "lucide-react";
import { useTranslations } from "next-intl";

import { apiClient, type ProjectResponse } from "@/lib/api-client";
import { PostKeyChangeGuide } from "@/components/credentials/post-key-change-guide";
import { CredentialCard } from "@/components/credentials/credential-card";

export default function AnthropicSettingsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const t = useTranslations("settings.anthropic");

  const [guideOpen, setGuideOpen] = useState(false);
  const [staleProjects, setStaleProjects] = useState<ProjectResponse[]>([]);

  const handleCredentialChanged = async () => {
    if (!token) return;
    try {
      const resp = await apiClient.projects.list(token, { limit: 100 });
      const stale = resp.items.filter((p) => p.anthropic_key_status === "stale");
      setStaleProjects(stale);
      setGuideOpen(true);
    } catch {
      // stale 조회 실패는 무시 — 자격증명 저장 자체는 성공
    }
  };

  return (
    <>
      <PostKeyChangeGuide
        open={guideOpen}
        onClose={() => setGuideOpen(false)}
        channel="anthropic"
        staleProjects={staleProjects}
        token={token}
      />

      <div className="mx-auto max-w-2xl space-y-8">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">{t("title")}</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
        </div>

        {/* 섹션 1: API 키 */}
        <section aria-labelledby="api-key-heading">
          <h2 id="api-key-heading" className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            {t("apiKeySection")}
          </h2>
          <CredentialCard
            credentialType="api_key"
            title={t("apiKeyCardTitle")}
            description={t("apiKeyCardDescription")}
            placeholder="sk-ant-api03-..."
            validate={(v) =>
              v.startsWith("sk-ant-") && v.length >= 20
                ? null
                : t("apiKeyInvalid")
            }
            externalLink={{
              href: "https://console.anthropic.com/settings/keys",
              label: t("apiKeyExternalLink"),
            }}
            helperText={t("apiKeyHelper")}
            onChanged={handleCredentialChanged}
          />
        </section>

        {/* 섹션 2: OAuth 브라우저 (정보 전용) */}
        <section aria-labelledby="oauth-browser-heading">
          <h2 id="oauth-browser-heading" className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            {t("oauthSection")}
          </h2>
          <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-6 space-y-4">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-zinc-500" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">{t("oauthNoRegistrationTitle")}</h3>
            </div>
            <p className="text-xs text-[var(--text-muted)]">{t("oauthNoRegistrationDesc")}</p>
            <ul className="space-y-2 text-xs text-[var(--text-secondary)]">
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-zinc-400">•</span>
                <span>{t("oauthBullet1")}</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-zinc-400">•</span>
                <span>{t("oauthBullet2")}</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-zinc-400">•</span>
                <span>{t("oauthBullet3")}</span>
              </li>
            </ul>
          </div>
        </section>
      </div>
    </>
  );
}
