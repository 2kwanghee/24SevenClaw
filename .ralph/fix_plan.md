# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] Step 4-5 PM 추천 + 선택 UI**
  > 요청사항: Step 4: src/components/solutions/wizard/steps/step-pm-recommendation.tsx

* 프로토타입 선택 후 POST /prototype-sessions/{id}/recommend-pms 호출
* 로딩 중 스켈레톤 카드 표시
* 완료 시 자동으로 Step 5로 전환

Step 5: src/components/solutions/wizard/steps/step-pm-selection.tsx

* PM 카드형 UI (pm-profile-card.tsx):
  * 아바타 + 이름 + 직함
  * 별점 (pm-rating-stars.tsx) + 평점
  * 프로젝트 완료건수, 사용빈도, 성공률, 평균 완료일
  * 전문 분야 태그
* 카드 클릭 → 선택 하이라이트
* PATCH /prototype-sessions/{id} (selected_pm_id)

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [web] Step 4-5 PM 추천 + 선택 UI | ✅ 완료 | step-pm-recommendation.tsx + step-pm-selection.tsx 생성, SOLUTION_WIZARD_STEPS 9단계로 분리, PMProfileCard 4메트릭 추가 |