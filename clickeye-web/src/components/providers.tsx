"use client";

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SessionProvider, signOut, useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";

import { ApiClientError } from "@/lib/api-client";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return error.detail;
  if (error instanceof Error) return error.message;
  return "요청 처리 중 오류가 발생했습니다";
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

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
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
            toast.error(getErrorMessage(error));
          },
        }),
      }),
  );

  return (
    <SessionProvider refetchInterval={4 * 60} refetchOnWindowFocus={true}>
      <SessionGuard>
        <QueryClientProvider client={queryClient}>
          {children}
          <Toaster
            position="bottom-right"
            theme="light"
            richColors
          />
        </QueryClientProvider>
      </SessionGuard>
    </SessionProvider>
  );
}
