# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[frontend] Phase 1-D — 위저드 Step 4~7 i18n**
  > 요청사항: ## 목표

위저드 후반부 — PM 추천/선택/구성 확인, 에이전트/스킬, 플랫폼/OS, 환경변수, 확인/다운로드 단계의 한국어 텍스트를 카탈로그 키로 치환.

## 변경 파일

* PM 단계: `step-pm-recommendation.tsx`, `step-pm-select.tsx`, `step-pm-selection.tsx`, `step-pm-composition.tsx`
* 구성 단계: `step-solution-agents.tsx`, `step-solution-platform.tsx`, `step-solution-os.tsx`
* 환경/ROI: `step-solution-env.tsx`, `step-solution-roi.tsx`
* 확인: `step-solution-confirm.tsx`, `step-confirmation.tsx` (`SetupGuideModal` 포함)
* PM 표시: `pm-composition-view.tsx`, `pm-rating-stars.tsx`

## 변경 카탈로그

* `messages/{ko,en}.json`: `wizard.step4` \~ `wizard.step7` + `setupGuide.*` 키 묶음

## 검증

* en locale로 위저드 Step 4\~7 완주 + ZIP 다운로드 안내 영문
* SetupGuideModal의 압축 해제/런처 실행/환경변수 안내 영문 표시
* PM 카드/구성 요소 라벨 영문 (composition 칩의 한국어 이름은 DB값이라 별도 — CE-257에서 처리)

## 의존성

* 선행: [CE-253](https://linear.app/flow-ops/issue/CE-253/frontend-phase-1-c-위저드-step-13-i18n) (Phase 1-C 위저드 Step 1\~3)
* 후속 CE-255가 본 이슈에 의존

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-05-28 | Phase 1-D 전체 (Step 4~7 i18n) 완료 | ✅ 완료 | 14개 컴포넌트 + messages/{en,ko}.json 업데이트, typecheck/build 통과 |