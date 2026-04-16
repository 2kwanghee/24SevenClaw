# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] 솔루션 위저드 레이아웃 + stepper**
  > 요청사항: 위저드 기본 프레임 구현.

* src/components/solutions/wizard/solution-wizard-layout.tsx: 레이아웃 + 네비게이션(이전/다음)
* src/components/solutions/wizard/solution-stepper.tsx: 7단계 인디케이터 (기존 stepper.tsx 참고)
* src/app/(dashboard)/solutions/new/page.tsx: 위저드 진입점
* src/app/(dashboard)/solutions/new/layout.tsx: 위저드 레이아웃
* src/app/(dashboard)/solutions/\[sessionId\]/page.tsx: 세션 재진입

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [web] 솔루션 위저드 레이아웃 + stepper | 완료 | layout.tsx 생성 (solution-wizard-layout, stepper, new/page, [sessionId]/page 이미 구현됨) |