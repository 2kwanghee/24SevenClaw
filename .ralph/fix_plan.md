# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] 솔루션 위저드 Zustand 스토어**
  > 요청사항: src/stores/solution-wizard-store.ts 신규 작성.

기존 wizard-store.ts 패턴(create, set, get) 따름.

상태: currentStep, sessionId, company, solutionPrompt, prototypes, selectedPrototypeId, generationStatus, recommendedPMs, selectedPMId, pmComposition

액션: nextStep, prevStep, goToStep, setCompany, setSolutionPrompt, setPrototypes, selectPrototype, setRecommendedPMs, selectPM, setPMComposition, reset

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 17:45 | [web] 솔루션 위저드 Zustand 스토어 | ✅ 완료 | solution-wizard-store.ts 구현 확인, 15/15 테스트 통과 |