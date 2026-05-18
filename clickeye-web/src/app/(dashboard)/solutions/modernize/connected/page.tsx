"use client";

import { CheckCircle2 } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { isModernizeEnabled } from "@/lib/feature-flags";

/**
 * GitHub App 설치 완료 후 ClickEye 서버 callback 이 redirect 하는 페이지.
 *
 * 받은 `installation_id` 를 store 에 직접 저장하지는 않고, 위저드 페이지로 redirect 만 한다.
 * 위저드는 `/modernize/installations` API 로 최신 목록을 다시 조회하므로 단일 source of truth.
 *
 * popup 으로 열린 경우 부모창에 postMessage 전송 후 자동 닫기.
 */
export default function ModernizeConnectedPage() {
  const router = useRouter();
  const params = useSearchParams();
  const installationId = params.get("installation_id");

  useEffect(() => {
    if (!isModernizeEnabled()) {
      router.replace("/projects");
      return;
    }

    // popup 인지 확인 (부모창이 있고 같은 origin)
    if (window.opener && !window.opener.closed) {
      try {
        window.opener.postMessage(
          { type: "clickeye-modernize-installed", installation_id: installationId },
          window.location.origin,
        );
        window.close();
        return;
      } catch {
        // postMessage 실패 시 일반 redirect 로 폴백
      }
    }

    // 일반 redirect — 잠시 안내 후 위저드로 이동
    const timer = setTimeout(() => {
      router.replace("/solutions/modernize/new");
    }, 1500);
    return () => clearTimeout(timer);
  }, [installationId, router]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <CheckCircle2 className="mb-4 h-12 w-12 text-emerald-600" />
      <h1 className="mb-2 text-xl font-semibold text-zinc-950">
        GitHub 연결 완료
      </h1>
      <p className="text-sm text-zinc-500">
        잠시 후 위저드로 자동 이동합니다…
      </p>
      {installationId && (
        <p className="mt-3 font-mono text-xs text-zinc-400">
          installation_id: {installationId}
        </p>
      )}
    </div>
  );
}
