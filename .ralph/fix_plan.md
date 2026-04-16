# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] Step 3 프로토타입 선택 UI**
  > 요청사항: src/components/solutions/wizard/steps/step-prototype-selection.tsx

3\~4개 프로토타입을 카드형으로 비교 선택.

컴포넌트:

* prototype-card.tsx: 썸네일 + 제목 + 설명 + 디자인패턴 배지 + 메뉴구조 요약
* prototype-preview.tsx: UI 구조 JSON → 자체 렌더링 (메뉴 트리 + 페이지 레이아웃 + 컬러팔레트)

동작:

* 카드 클릭 → 선택 하이라이트 + 프리뷰 확대
* 선택 후 PATCH /prototype-sessions/{id} (selected_prototype_id)
* "다음" 클릭 → Step 4로 이동

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [web] Step 3 프로토타입 선택 UI | ✅ 완료 | step-prototype-selection.tsx 생성, prototype-card/preview 강화 |
