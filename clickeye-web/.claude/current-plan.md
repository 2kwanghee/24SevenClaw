## 목표
CE-306 항목2·3: 대시보드에 남은 하드코딩 `PHASE_LABELS`를 `delivery.phase` i18n 재사용으로 통합하고, issue-card의 미번역 `artifact` 라벨을 `delivery.issues.artifact` 4로케일 키로 i18n한다.

## 변경 파일 목록
- clickeye-web/messages/{ko,en,ja,id}.json: `delivery.phase`에 velocity 차트 전용 키 4개(revising/in_development/validated/released) 추가 + `delivery.issues.artifact` 추가 (4로케일 동일)
- clickeye-web/src/components/dashboard/project-timeline.tsx: 로컬 PHASE_LABELS 제거 → useTranslations("delivery.phase")
- clickeye-web/src/components/dashboard/phase-velocity-chart.tsx: 로컬 PHASE_LABELS 제거 → useTranslations("delivery.phase")
- clickeye-web/src/app/(dashboard)/projects/[projectId]/ai-team/page.tsx: 로컬 PHASE_LABELS 제거 → useTranslations("delivery.phase")
- clickeye-web/src/components/delivery/issue-card.tsx: 하드코딩 "artifact" → t("issues.artifact")

## 구현 단계
1. 4로케일 JSON에 phase 4키 + issues.artifact 추가
2. 3개 컴포넌트에서 PHASE_LABELS 제거, useTranslations + t.has() fallback로 렌더
3. issue-card artifact 라벨 i18n
4. lint + tsc + vitest 검증, 잔여 하드코딩 grep

## 예상 영향 범위
- 모두 "use client" 컴포넌트 → useTranslations 사용 (server API 불필요)
- delivery.phase는 OrchestratorPhase 10키 + velocity 전용 4키 superset이 됨(딜리버리 콘솔 동작 불변)
- artifact-status-chart.tsx의 STATUS_CONFIG(color 포함, status taxonomy)는 PHASE_LABELS 아니므로 범위 외

## STATUS: APPROVED
