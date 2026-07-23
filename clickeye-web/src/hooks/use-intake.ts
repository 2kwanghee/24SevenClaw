"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAccessToken } from "@/hooks/use-access-token";
import {
  intake,
  intakeServiceKeys,
  type IntakeStatus,
} from "@/lib/api-client";

/** 인테이크 목록 query key 루트 (상태 필터별 하위 키 공유) */
const INTAKE_KEY = ["admin", "intake"] as const;
const SERVICE_KEYS_KEY = ["admin", "intake-service-keys"] as const;

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
