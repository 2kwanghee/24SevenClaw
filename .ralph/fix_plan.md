# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] Step 6 PM 구성 확인 UI**
  > 요청사항: src/components/solutions/wizard/steps/step-pm-composition.tsx

GET /pm-profiles/{id}/composition 호출하여 PM 구성 표시.

pm-composition-view.tsx:

* 5개 카테고리별 섹션: Agent, Skill, Hook, MCP Server, Plugin
* 각 항목: 아이콘 + 이름 + 슬러그 + 필수/선택 배지 + 간단 설명
* 카테고리별 접기/펴기

액션:

* "이대로 진행" → Step 7로 이동
* "PM 재선택" → Step 5로 돌아가기

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [web] Step 6 PM 구성 확인 UI | ✅ | step-pm-composition.tsx 생성, SOLUTION_WIZARD_STEPS 업데이트 |