# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] useCatalog 훅 + api-client 카탈로그 모듈 추가**
  > 요청사항: ## 목적

위저드 Step 6 동적화에 필요한 프론트엔드 데이터 레이어 구축.

## 작업 범위

* `src/lib/api-client.ts`에 `catalog.agents.list()`, `catalog.skills.list()` 추가
* `src/hooks/use-catalog.ts` 신규 (TanStack Query, staleTime 5분)
* TypeScript 타입 정의 (`CatalogAgent`, `CatalogSkill`)

## 완료 기준

* `npm run typecheck` 통과
* 훅 호출 시 `/api/v1/catalog/agents` 정상 응답 수신 확인

## 선행 조건

24S-173 완료 (Catalog API 검증 + seed)

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | [web] useCatalog 훅 + api-client 카탈로그 모듈 추가 | ✅ 완료 | typecheck 통과 |