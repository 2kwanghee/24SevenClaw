"use client";

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SessionProvider, signOut, useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
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
      <Toaster
        position="bottom-right"
        theme="light"
        richColors
      />
    </QueryClientProvider>
  );
}

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <SessionProvider refetchInterval={4 * 60} refetchOnWindowFocus={true}>
      <SessionGuard>
        <ZodLocaleProvider>
          <QueryProvider>{children}</QueryProvider>
        </ZodLocaleProvider>
      </SessionGuard>
    </SessionProvider>
  );
}
