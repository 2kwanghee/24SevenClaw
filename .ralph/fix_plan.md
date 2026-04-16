# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] 솔루션 위저드 타입 정의**
  > 요청사항: src/types/solution-wizard.ts 신규 작성.

기존 wizard.ts 패턴 참고하여 새 위저드용 타입 정의.

* SOLUTION_WIZARD_STEPS 상수 (7단계)
* CompanyInfo, SolutionPrompt
* Prototype, PrototypeUIStructure (메뉴/페이지/컬러)
* PMProfile, PMMetrics, PMComposition, PMCompositionItem
* SolutionWizardData (전체 상태 타입)

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [web] 솔루션 위저드 타입 정의 | ✅ 완료 | CompanyInfo, SolutionPrompt, PrototypeUIStructure, PMProfile, PMMetrics, PMComposition, PMCompositionItem 추가. tsc 타입체크 통과 |