# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[web] Step 7 최종 확인 + 프로젝트 생성**
  > 요청사항: src/components/solutions/wizard/steps/step-confirmation.tsx

전체 요약 카드:

* 회사 정보 요약
* 선택된 프로토타입 썸네일 + 정보
* 선택된 PM 카드 미니 버전
* PM 구성 요약 (agent/skill/hook/mcp/plugin 수)

액션:

* "이대로 진행" → POST /prototype-sessions/{id}/finalize → 프로젝트 생성 → /projects/{id}로 이동
* "재선택" → 특정 스텝으로 돌아가기

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [web] Step 7 최종 확인 + 프로젝트 생성 | ✅ 완료 | step-confirmation.tsx 신규 생성, finalize API 연동, 재선택 버튼 구현 |