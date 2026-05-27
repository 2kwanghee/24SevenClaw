# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[infra] Phase 0 — next-intl 인프라 + 미들웨어 + 토글 UI**
  > 요청사항: ## 목표

next-intl 기반 i18n 인프라를 도입한다. 쿠키 기반 로케일 결정, Accept-Language fallback, 사용자 향 페이지에 언어 토글 UI 노출, `/admin/*` 경로는 한국어 강제.

## 변경 파일

* `clickeye-web/package.json` — next-intl@^4 추가
* `clickeye-web/src/middleware.ts` (신규) — locale 결정 로직 (쿠키 > Accept-Language > "en" fallback). `/admin/*`은 무조건 `ko` 강제
* `clickeye-web/src/i18n/routing.ts` (신규) — locale 목록 `["ko", "en"]`
* `clickeye-web/src/i18n/request.ts` (신규) — next-intl getRequestConfig
* `clickeye-web/messages/ko.json`, `messages/en.json` (신규 빈 카탈로그 — 후속 이슈에서 채움)
* `clickeye-web/src/app/layout.tsx` — `<NextIntlClientProvider>` 래핑
* `clickeye-web/src/components/common/locale-toggle.tsx` (신규) — 헤더에 마운트. 사용자 향 layout에만 노출

## 정책

* 쿠키 키: `clickeye-locale`, 만료: 1년
* 사용자 향 페이지에서만 토글 노출. `/admin/*`에는 미노출
* en 카탈로그 미입력 키는 ko로 fallback

## 검증

1. `npm install next-intl` 후 빌드 성공
2. 쿠키 비우고 Accept-Language=en으로 접속 → 영어 자동 선택
3. 토글 누름 → `clickeye-locale` 쿠키 저장 + 페이지 재렌더링
4. `/admin/pm` 접속 시 토글 영향 없이 한국어 유지

## 의존성

* root 이슈 (선행 없음)
* 후속 이슈 2, 7이 본 이슈에 의존

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-05-27 | Phase 0 next-intl 인프라 | 완료 | next.config.ts 플러그인, src/i18n/routing.ts·request.ts, messages/{ko,en}.json, src/proxy.ts에 locale 통합(Next.js 16은 middleware.ts/proxy.ts 공존 불가 — proxy.ts 확장), layout.tsx에 NextIntlClientProvider, locale-toggle.tsx + header.tsx 마운트. `npm run typecheck` 통과. |