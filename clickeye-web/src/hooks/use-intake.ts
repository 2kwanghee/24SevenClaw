"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAccessToken } from "@/hooks/use-access-token";
import {
  apiClient,
  intake,
  intakeServiceKeys,
  type IntakeStatus,
} from "@/lib/api-client";

/** 인테이크 목록 query key 루트 (상태 필터별 하위 키 공유) */
const INTAKE_KEY = ["admin", "intake"] as const;
const SERVICE_KEYS_KEY = ["admin", "intake-service-keys"] as const;
/** CE-337: 프로젝트 스코프 인테이크 query key 루트 (admin 키와 캐시 분리) */
const PROJECT_INTAKE_KEY = ["project", "intake"] as const;

/** 인테이크 검토 목록 — statusFilter 미지정 시 전체 */
export function useIntakeList(statusFilter?: IntakeStatus) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...INTAKE_KEY, statusFilter ?? "all"],
    queryFn: () => intake.list(token, statusFilter),
    enabled: !!token,
    retry: false, // FEATURE_INTAKE off → 404 를 즉시 안내로 전환 (재시도 무의미)
  });
}

/** 승인 — 성공 시 인테이크 목록 + 프로젝트 목록(신규 생성) 무효화 */
export function useAcceptIntake() {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (intakeId: string) => intake.accept(token, intakeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: INTAKE_KEY });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

/** 반려 — 사유(선택) 포함 */
export function useRejectIntake() {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ intakeId, reason }: { intakeId: string; reason?: string }) =>
      intake.reject(token, intakeId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: INTAKE_KEY });
    },
  });
}

/**
 * P9: 무인 체인 단계별 집계 — 콘솔 헤더용.
 * 헤더는 보조 정보이므로 실패해도 조용히 넘긴다(호출부에서 미표시 처리).
 */
export function useIntakeOverview() {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...INTAKE_KEY, "overview"],
    queryFn: () => intake.overview(token),
    enabled: !!token,
    retry: false,
  });
}

/** P9: 인테이크 1건 전이 타임라인 — 행 확장 시에만 enabled */
export function useIntakeTimeline(intakeId: string, enabled = true) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...INTAKE_KEY, "timeline", intakeId],
    queryFn: () => intake.timeline(token, intakeId),
    enabled: !!token && enabled,
    retry: false,
  });
}

/**
 * CE-337: 프로젝트를 생성한 인테이크(역조회) — 딜리버리 콘솔 원장 뷰.
 * 인테이크 유래가 아닌 프로젝트는 404 → retry:false 로 즉시 폴백 처리한다.
 */
export function useProjectIntake(projectId: string, enabled = true) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...PROJECT_INTAKE_KEY, projectId],
    queryFn: () => apiClient.projects.getIntake(token, projectId),
    enabled: !!token && !!projectId && enabled,
    retry: false,
  });
}

/**
 * CE-337: 프로젝트 스코프 인테이크 전이 타임라인 — admin 타임라인과 별개 경로.
 * events 는 발생 순(오름차순). 인테이크 없으면 404 → retry:false.
 */
export function useProjectIntakeTimeline(projectId: string, enabled = true) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...PROJECT_INTAKE_KEY, "timeline", projectId],
    queryFn: () => apiClient.projects.getIntakeTimeline(token, projectId),
    enabled: !!token && !!projectId && enabled,
    retry: false,
  });
}

/** 서비스 키 목록 — superadmin 전용 화면에서만 enabled=true 로 호출 */
export function useIntakeServiceKeys(enabled = true) {
  const token = useAccessToken();

  return useQuery({
    queryKey: [...SERVICE_KEYS_KEY],
    queryFn: () => intakeServiceKeys.list(token),
    enabled: !!token && enabled,
    retry: false,
  });
}

/** 서비스 키 발급 — 응답 key(평문)는 1회만 노출되므로 caller가 즉시 표시 */
export function useCreateIntakeServiceKey() {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      name,
      organizationId,
    }: {
      name: string;
      organizationId?: string;
    }) => intakeServiceKeys.create(token, name, organizationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SERVICE_KEYS_KEY });
    },
  });
}

/** 서비스 키 비활성화 */
export function useDeactivateIntakeServiceKey() {
  const token = useAccessToken();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (keyId: string) => intakeServiceKeys.deactivate(token, keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: SERVICE_KEYS_KEY });
    },
  });
}
