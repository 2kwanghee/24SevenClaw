# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] Step 2 프로토타입 생성 로딩 UI**
  > 요청사항: src/components/solutions/wizard/steps/step-prototype-generation.tsx

Step 1에서 "다음" 클릭 시:

1. POST /prototype-sessions (세션 생성)
2. POST /prototype-sessions/{id}/prototypes/generate (생성 트리거)
3. GET /prototype-sessions/{id}/status 폴링 (3초 간격)

UI:

* 전체 진행률 표시 (0/4 → 1/4 → ... → 4/4)
* 각 프로토타입별 생성 상태 카드 (generating → ready)
* 로딩 애니메이션 (스켈레톤 + 스피너)
* 실패 시 재시도 버튼
* 모두 완료 시 자동으로 Step 3으로 이동

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [web] Step 2 프로토타입 생성 로딩 UI | ✅ 완료 | step-prototype-generation.tsx 신규 생성, SOLUTION_WIZARD_STEPS에 generation 단계 추가, step-prototypes.tsx 순수 선택 컴포넌트로 분리 |