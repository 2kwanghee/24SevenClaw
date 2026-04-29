---
route: /solutions/[sessionId]
title: 솔루션 세션 재개
status: implemented
version: 1.0.0
pages:
  - src/app/(dashboard)/solutions/[sessionId]/page.tsx
components:
  - src/components/solutions/wizard/solution-wizard-layout.tsx
  - src/components/solutions/wizard/steps/step-company.tsx
store: useSolutionWizardStore
last_updated: 2026-04-16
---

## 목적
진행 중인 솔루션 세션을 URL로 직접 접근하거나 Step 0 완료 후 URL 교체 시 위저드를 이어서 진행.

---

## 스토리보드

1. `/solutions/{sessionId}` 진입
2. 세션 ID를 스토어에 저장
3. `current_step` 기반으로 해당 스텝으로 이동
4. 이후는 `/solutions/new`와 동일한 위저드 플로우

---

## 기능 요구사항

- [x] sessionId URL 파라미터 → 스토어 `setSessionId`
- [x] Step 0 = `StepCompany` (기존 회사정보 조회 버전)
- [x] 나머지 스텝은 `/solutions/new`와 동일
- [ ] 세션 상태 API 조회 후 `current_step` 복원
- [ ] 완료된 세션 접근 시 프로젝트 페이지 리다이렉트
- [ ] 실패 세션 접근 시 재시작 안내

---

## 구현 노트

- `StepCompany` (회사정보 조회 버전) vs `StepCompanySolution` (입력 버전) 구분
- `/solutions/new` → Step 0 완료 → `router.replace(/solutions/{id})`로 URL 전환
