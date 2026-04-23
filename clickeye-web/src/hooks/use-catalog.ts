"use client";

import { useQuery } from "@tanstack/react-query";

import { catalog } from "@/lib/api-client";

const CATALOG_STALE_TIME = 5 * 60 * 1000;

export function useCatalogAgents() {
  return useQuery({
    queryKey: ["catalog", "agents"],
    queryFn: () => catalog.agents.list(),
    staleTime: CATALOG_STALE_TIME,
  });
}

export function useCatalogSkills() {
  return useQuery({
    queryKey: ["catalog", "skills"],
    queryFn: () => catalog.skills.list(),
    staleTime: CATALOG_STALE_TIME,
  });
}

export function useCatalogHooks() {
  return useQuery({
    queryKey: ["catalog", "hooks"],
    queryFn: () => catalog.hooks.list(),
    staleTime: CATALOG_STALE_TIME,
  });
}
