# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] api-client.ts 확장 (솔루션 위저드 API)**
  > 요청사항: src/lib/api-client.ts에 신규 API 메서드 추가.

* prototypeSession: create, get, update, getStatus, getPrototypes, generatePrototypes, recommendPMs, finalize
* pmProfiles: list, get, getComposition, createRating, listRatings

TanStack Query 훅도 함께 작성:

* src/hooks/use-solution-wizard.ts
* src/hooks/use-prototypes.ts
* src/hooks/use-pm-profiles.ts

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [web] api-client.ts 확장 (솔루션 위저드 API) | ✅ | 타입 업데이트 + 신규 메서드 + TanStack Query 훅 3개 생성 |