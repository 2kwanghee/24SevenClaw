"use client";

import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { systemFeatures } from "@/lib/api-client";

export function useSystemFeatures() {
  const { data: session } = useSession();
  const token = (session as { accessToken?: string })?.accessToken ?? "";
  return useQuery({
    queryKey: ["system-features"],
    queryFn: () => systemFeatures.get(token),
    enabled: !!token,
    staleTime: 60_000,
  });
}
