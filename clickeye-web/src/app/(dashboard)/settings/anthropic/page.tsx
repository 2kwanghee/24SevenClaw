"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { Info } from "lucide-react";

import { apiClient, type ProjectResponse } from "@/lib/api-client";
import { PostKeyChangeGuide } from "@/components/credentials/post-key-change-guide";
import { CredentialCard } from "@/components/credentials/credential-card";

export default function AnthropicSettingsPage() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

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
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Anthropic 자격증명</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Claude 인증 방식에 따라 필요한 자격증명을 등록하세요. 위저드에서 선택한 모드에 맞는 자격증명이 ZIP 생성 시 자동으로 주입됩니다.
          </p>
        </div>

        {/* 섹션 1: API 키 */}
        <section aria-labelledby="api-key-heading">
          <h2 id="api-key-heading" className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            API 키 모드
          </h2>
          <CredentialCard
            credentialType="api_key"
            title="API 키"
            description="위저드에서 'API 키' 모드를 선택한 경우 사용됩니다. ZIP의 .env에 ANTHROPIC_API_KEY로 자동 주입됩니다."
            placeholder="sk-ant-api03-..."
            validate={(v) =>
              v.startsWith("sk-ant-") && v.length >= 20
                ? null
                : "올바른 형식이 아닙니다 (sk-ant-... 로 시작, 20자 이상)"
            }
            externalLink={{
              href: "https://console.anthropic.com/settings/keys",
              label: "console.anthropic.com → API Keys에서 발급 (sk-ant-... 형식)",
            }}
            helperText="키는 서버에 Fernet 암호화로 저장됩니다. 위저드에서 솔루션 청사진 분석 시 이 키가 우선 사용되며, 서버 키보다 본인 계정의 크레딧이 우선 소진됩니다."
            onChanged={handleCredentialChanged}
          />
        </section>

        {/* 섹션 2: OAuth Setup Token */}
        <section aria-labelledby="setup-token-heading">
          <h2 id="setup-token-heading" className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            OAuth Setup Token 모드
          </h2>
          <CredentialCard
            credentialType="oauth_setup_token"
            title="OAuth Setup Token"
            description="Claude Pro/Max 구독자가 본인 구독 한도로 실행하는 경우 사용됩니다. ZIP의 .env에 CLAUDE_CODE_OAUTH_TOKEN으로 자동 주입됩니다."
            placeholder="claude setup-token 출력값 붙여넣기"
            validate={(v) =>
              v.length >= 20 && v.length <= 500
                ? null
                : "길이가 올바르지 않습니다 (20~500자)"
            }
            externalLink={{
              href: "https://docs.anthropic.com/ko/docs/claude-code/authentication",
              label: "claude setup-token 발급 방법 안내",
            }}
            totalDays={365}
            helperText="터미널에서 'claude setup-token' 명령을 실행하여 토큰을 발급받으세요. 토큰은 1년 후 만료되며, 만료 시 재발급 및 이 페이지에서 교체가 필요합니다."
            onChanged={handleCredentialChanged}
          />
        </section>

        {/* 섹션 3: OAuth 브라우저 (정보 전용) */}
        <section aria-labelledby="oauth-browser-heading">
          <h2 id="oauth-browser-heading" className="mb-3 text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            OAuth 브라우저 모드
          </h2>
          <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-6 space-y-4">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-zinc-500" />
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">별도 등록 불필요</h3>
            </div>
            <p className="text-xs text-[var(--text-muted)]">
              위저드에서 &apos;OAuth 브라우저&apos; 모드를 선택한 경우, ClickEye 클라우드에는 어떤 자격증명도 저장되지 않습니다.
            </p>
            <ul className="space-y-2 text-xs text-[var(--text-secondary)]">
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-zinc-400">•</span>
                <span>
                  ZIP 다운로드 후 로컬 PC의 별도 터미널에서{" "}
                  <code className="rounded bg-zinc-200 px-1 py-0.5 font-mono">claude login</code>{" "}
                  실행으로 인증합니다.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-zinc-400">•</span>
                <span>인증 토큰은 OS 키체인(~/.claude.json)에만 저장되며 ClickEye로 전송되지 않습니다.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-zinc-400">•</span>
                <span>이 모드는 이 페이지에서 관리할 항목이 없습니다. 위저드에서 인증 방식을 선택하고 ZIP을 다운로드하세요.</span>
              </li>
            </ul>
          </div>
        </section>
      </div>
    </>
  );
}
