"use client";

import { useQuery } from "@tanstack/react-query";

import { useAccessToken } from "@/hooks/use-access-token";
import {
  observability,
  type PipelineRunListParams,
  type UsagePivotParams,
} from "@/lib/api-client";

/** 관측 화면 query key 루트 — admin/intake 캐시와 분리 */
const OBSERVABILITY_KEY = ["observability"] as const;

/** 대시보드 홈 위젯 집계 — days 로 기간 프리셋(7/14/30) 전환, 변경 시 캐시 분리 + 재조회 */
export function useObservabilitySummary(days: number = 7) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...OBSERVABILITY_KEY, "summary", days],
    queryFn: () => observability.getSummary(token, { days }),
    enabled: !!token,
    retry: false, // FEATURE off / 권한 없음 → 404 를 즉시 안내로 전환
  });
}

/** 사용량 원장 피벗 — group_by/기간/task_id 필터 변경 시 재조회 */
export function useUsagePivot(params: UsagePivotParams) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...OBSERVABILITY_KEY, "usage", params],
    queryFn: () => observability.getUsage(token, params),
    enabled: !!token,
    retry: false,
  });
}

/** 실행 이력 목록 */
export function useRunsList(params: PipelineRunListParams = {}) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...OBSERVABILITY_KEY, "runs", params],
    queryFn: () => observability.getRuns(token, params),
    enabled: !!token,
    retry: false,
  });
}

/** run 상세(issue_key 스레드) — 선택된 행에 대해서만 enabled */
export function useRunDetail(issueKey: string, enabled = true) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...OBSERVABILITY_KEY, "runs", "detail", issueKey],
    queryFn: () => observability.getRunDetail(token, issueKey),
    enabled: !!token && !!issueKey && enabled,
    retry: false,
  });
}

/** 프로젝트 상세 드릴다운(토큰/기간/계정) — 대시보드 hover 상세용, 선택된 프로젝트에 대해서만 enabled */
export function useProjectSummary(projectId: string, enabled = true) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...OBSERVABILITY_KEY, "projects", projectId, "summary"],
    queryFn: () => observability.getProjectSummary(token, projectId),
    enabled: !!token && !!projectId && enabled,
    retry: false,
  });
}

/** 시트 잔량 */
export function useSeats() {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...OBSERVABILITY_KEY, "seats"],
    queryFn: () => observability.getSeats(token),
    enabled: !!token,
    retry: false,
  });
}

/** 딜리버리 진행 보드 — 프로젝트별 티켓×단계 타임라인 (CE-411). 30s 폴링으로 진행 상황을 갱신한다. */
export function useDeliveryBoard() {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...OBSERVABILITY_KEY, "delivery-board"],
    queryFn: () => observability.deliveryBoard(token),
    enabled: !!token,
    retry: false,
    refetchInterval: 30_000,
  });
}

/** 티켓 상세(Linear 원본) — 카드 클릭 시에만 조회(lazy), 60s 동안 fresh 로 캐시. */
export function useTicketDetail(issueId: string | null | undefined, enabled = true) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...OBSERVABILITY_KEY, "delivery-board", "ticket", issueId],
    queryFn: () => observability.getTicketDetail(token, issueId as string),
    enabled: !!token && !!issueId && enabled,
    retry: false,
    staleTime: 60_000,
  });
}
