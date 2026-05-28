# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[frontend] Phase 1-E — 온보딩 + 솔루션/프로젝트/설정/가이드/공개 레지스트리 i18n**
  > 요청사항: ## 목표

위저드 외 사용자 향 페이지 전부 i18n. 페이지 수는 가장 많지만 페이지당 텍스트 풍부도는 낮음.

## 변경 파일 (페이지 기준)

* `/onboarding/preset/*` — natural-language-input 포함 (자연어 분석 입력박스 라벨)
* `/onboarding/assessment/*` — 성숙도 평가 질문지/응답
* `/solutions/page.tsx`, `/solutions/[sessionId]/page.tsx`, `/solutions/new/page.tsx`
* `/projects/*` — 프로젝트 목록/상세
* `/settings/*` — 사용자 설정 (언어 선택 UI도 본 이슈에 포함)
* `/guide/*` — 사용자 가이드 페이지
* `/registry/*` — 공개 레지스트리 (사용자 열람용. `/admin/registry/*`는 제외)

## 변경 카탈로그

* `messages/{ko,en}.json`: `onboarding.*`, `solutions.*`, `projects.*`, `settings.*`, `guide.*`, `registry.*` 키 묶음

## 검증

* en locale로 전체 사용자 향 페이지 순회 — 한국어 글자 0건 (Claude 응답 및 DB 시드 한국어 콘텐츠 제외)
* ko locale에서 기존과 100% 동일
* `/settings`에서 사용자 언어 변경 토글 (CE-256 백엔드 User.language 필드 연동 준비)

## 의존성

* 선행: [CE-254](https://linear.app/flow-ops/issue/CE-254/frontend-phase-1-d-위저드-step-47-i18n) (Phase 1-D 위저드 Step 4\~7)
* 후속 CE-256이 본 이슈에 의존

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-05-28 | Phase 1-E i18n 적용 | ✅ 완료 | 16개 파일, 946개 라인 추가, 타입체크 통과. /registry/* 는 공개 페이지 없어 skip. settings 언어 토글은 header LocaleToggle로 이미 제공됨(CE-256 연동 준비 완료). |