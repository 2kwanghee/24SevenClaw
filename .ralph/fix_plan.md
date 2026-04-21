# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] 위저드 Step 6 하드코딩 제거 + 카탈로그 API 동적 렌더링**
  > 요청사항: ## 목적

관리자가 `/admin/registry/agents|skills`에서 편집한 내용이 사용자 위저드에 즉시 반영되도록 연결.

## 작업 범위

* `src/components/solutions/wizard/steps/step-solution-agents.tsx`에서 `AGENT_LABELS` / `SKILL_LABELS` 하드코딩 제거
* `useCatalog` 훅으로 교체
* 로딩 스켈레톤 + 에러 상태 UI 추가
* `solutionWizardStore`의 `selectedAgents`/`selectedSkills` 스키마 호환성 유지 (ID 기반 선택)

## 완료 기준

* 관리자가 `/admin/registry/agents`에서 새 항목 추가 → 새 위저드 세션 Step 6에 즉시 노출
* 관리자가 항목 삭제 → 다음 위저드 세션에서 사라짐
* `npm run typecheck && npm run build` 통과

## 선행 조건

24S-174 완료 (useCatalog 훅)

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | [web] 위저드 Step 6 하드코딩 제거 + 카탈로그 API 동적 렌더링 | ✅ 완료 | useCatalogAgents/useCatalogSkills 교체, 로딩 스켈레톤+에러 상태 추가, 빌드 통과 |