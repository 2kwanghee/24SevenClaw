## 목표

clickeye-web에 next-intl v4 기반 i18n 인프라(Phase 0)를 도입한다. 쿠키 기반 로케일 결정, Accept-Language fallback, `/admin/*` 한국어 강제, 사용자 향 페이지에 토글 UI 노출. fix_plan.md P1 "[infra] Phase 0" 항목 구현.

## 변경 파일 목록

- `clickeye-web/next.config.ts` — `createNextIntlPlugin('./src/i18n/request.ts')` 래핑
- `clickeye-web/src/proxy.ts` (수정) — 기존 auth proxy에 locale 로직 통합. Next.js 16은 `middleware.ts`와 `proxy.ts` 공존 시 빌드 에러를 던지므로(`Both middleware ... and proxy ... are detected`) 신규 `middleware.ts` 대신 기존 `proxy.ts`를 확장한다.
- `clickeye-web/src/i18n/routing.ts` (신규) — `locales: ["ko","en"]`, `defaultLocale: "en"`, 쿠키명 상수
- `clickeye-web/src/i18n/request.ts` (신규) — `getRequestConfig`: 쿠키 → Accept-Language → "en" fallback, `/admin/*`은 ko 강제, ko 카탈로그로 en fallback
- `clickeye-web/messages/ko.json`, `clickeye-web/messages/en.json` (신규) — 빈 카탈로그 `{}`
- `clickeye-web/src/app/layout.tsx` — `<NextIntlClientProvider>` 래핑 + `<html lang>` 동적화
- `clickeye-web/src/components/common/locale-toggle.tsx` (신규) — 쿠키 set + `router.refresh()`
- `clickeye-web/src/components/layout/header.tsx` — LocaleToggle 마운트, `/admin/*` 경로는 미노출
- `.ralph/fix_plan.md` — Phase 0 항목 `[x]` 처리 + 진행 로그

## 구현 단계

1. `next.config.ts`에 `createNextIntlPlugin` 적용
2. `src/i18n/routing.ts`, `src/i18n/request.ts` 작성
3. `messages/ko.json`, `messages/en.json` 빈 카탈로그 생성
4. `src/proxy.ts` 확장: `x-pathname` 헤더 주입 + locale 쿠키 자동 설정 + 매처 확장
5. `src/app/layout.tsx`에 NextIntlClientProvider 적용 (서버에서 getLocale/getMessages)
6. `src/components/common/locale-toggle.tsx` 작성
7. `src/components/layout/header.tsx`에 토글 조건부 마운트 (`/admin/*` 미노출)
8. `cd clickeye-web && npm run typecheck`로 빌드 검증
9. `.ralph/fix_plan.md` 항목 `[x]` 처리 + 진행 로그 기록

## 예상 영향 범위

- 전체 페이지가 `NextIntlClientProvider` 컨텍스트 아래에서 렌더링됨. 현 단계에서는 메시지 카탈로그가 비어있어 시각 변화 없음.
- `<html lang>`이 고정 `"ko"` → 사용자 로케일에 따라 동적.
- `proxy.ts` 매처가 `/admin/*` 한정에서 모든 사용자 향 경로로 확장됨. 매처를 두 개로 분리하거나 `/((?!api|_next|favicon).*)`로 확장.
- 후속 이슈에서 메시지 키 도입 시 본 인프라 사용.

## STATUS: APPROVED
