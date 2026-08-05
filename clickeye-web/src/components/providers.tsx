"use client";

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SessionProvider, signOut, useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { ThemeProvider, useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";

import { ApiClientError } from "@/lib/api-client";
import { ZodLocaleProvider } from "@/components/providers/zod-locale-provider";

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiClientError) return error.detail;
  if (error instanceof Error) return error.message;
  return fallback;
}

/** Refresh Token 갱신 실패 시 자동 로그아웃 */
function SessionGuard({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();

  useEffect(() => {
    if (session?.error === "RefreshTokenError") {
      signOut({ callbackUrl: "/login" });
    }
  }, [session?.error]);

  return <>{children}</>;
}

/** next-themes 값을 sonner Toaster 테마로 반영 */
function ThemedToaster() {
  const { resolvedTheme } = useTheme();
  const theme = resolvedTheme === "dark" ? "dark" : "light";

  return <Toaster position="bottom-right" theme={theme} richColors />;
}

function QueryProvider({ children }: { children: React.ReactNode }) {
  const t = useTranslations("toast.generic");
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
          },
        },
        mutationCache: new MutationCache({
          onError: (error) => {
            toast.error(getErrorMessage(error, t("requestError")));
          },
        }),
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ThemedToaster />
    </QueryClientProvider>
  );
}

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <ThemeProvider
      attribute="class"
      // 라이트 고정(CE-373). 다크 테마 품질을 아직 보증하지 못해 기본을 라이트로 못박고
      // 시스템 추종을 끈다. `.dark` CSS 변수와 `theme-switcher.tsx` 는 **삭제하지 않았다** —
      // 되살릴 때 이 두 줄과 헤더 한 줄만 되돌리면 된다.
      defaultTheme="light"
      enableSystem={false}
      forcedTheme="light"
      disableTransitionOnChange
    >
      <SessionProvider refetchInterval={4 * 60} refetchOnWindowFocus={true}>
        <SessionGuard>
          <ZodLocaleProvider>
            <QueryProvider>{children}</QueryProvider>
          </ZodLocaleProvider>
        </SessionGuard>
      </SessionProvider>
    </ThemeProvider>
  );
}
