# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] Step 1 회사정보 + 자연어 솔루션 입력**
  > 요청사항: src/components/solutions/wizard/steps/step-company-solution.tsx

기존 step-organization.tsx 참고 + 자연어 입력 영역 추가.

* 회사명, 규모, 업종, 기술스택 (기존 필드)
* 주력상품, 기업유형, 회사 설명 (신규 필드)
* 자연어 솔루션 입력 (textarea, 최소 50자)
* React Hook Form + Zod 유효성 검증
* watch() → Zustand 스토어 자동 저장

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [web] Step 1 회사정보 + 자연어 솔루션 입력 | ✅ 완료 | step-company-solution.tsx 신규 생성, 타입 확장(companySize/industry/techStack), solutionRequest 50자 최소 |