# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[frontend] Phase 1-A — 공통 컴포넌트 + Toast + Zod validation i18n**
  > 요청사항: ## 목표

토스트 메시지, Zod 스키마 validation 메시지, 공통 컴포넌트의 모든 한국어를 next-intl 카탈로그 키로 치환한다.

## 변경 파일

* `clickeye-web/src/lib/validations/*.ts` (\~10개) — zod.errorMap 글로벌 설정 + 메시지 키 치환
* 모든 `toast.success/error` 호출처 (\~15개) — `useTranslations("toast")` 적용
* 공통 컴포넌트(`common/*`, `ui/*` 사용처)의 라벨/버튼 텍스트

## 변경 카탈로그

* `messages/ko.json`: `common.*`, `toast.*`, `validation.*` 키 채움 (기존 한국어 그대로)
* `messages/en.json`: 동일 키 영문 번역

## 검증

* Zod validation 메시지가 locale에 따라 정상 표시
* 모든 토스트 한·영 분기 정상
* 공통 컴포넌트(버튼, 모달 등) 라벨 양 언어

## 의존성

* 선행: [CE-250](https://linear.app/flow-ops/issue/CE-250/infra-phase-0-next-intl-인프라-미들웨어-토글-ui) (Phase 0 인프라)
* 후속 이슈 3, 4가 본 이슈에 의존

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-05-27 | Phase 1-A | 완료 | messages 카탈로그 93키 한/영 작성, ZodLocaleProvider 신규(z.config locale 자동 전환), `lib/validations/pm.ts` factory 패턴 전환. login/register/project-form zod schema useMemo factory 적용. 사용자 향 toast 8파일 + admin toast 12파일 i18n 처리(71개 호출). 공통 컴포넌트 base-modal/locale-toggle/role-guard/header/create-project-dialog/delete-project-dialog 라벨/aria i18n. typecheck/build 통과. |
