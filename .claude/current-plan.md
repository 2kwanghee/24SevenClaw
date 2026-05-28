## 목표

온보딩 + 솔루션/프로젝트/설정/가이드 사용자 향 페이지 전부 i18n. Phase 1-E (CE-255).
하드코딩 한국어 텍스트를 next-intl 키로 치환하여 영문 locale 전환을 지원한다.

## 변경 파일 목록

- `clickeye-web/messages/en.json`: onboarding.*, solutions.*, projects.*, settings.*, guide.* 키 추가
- `clickeye-web/messages/ko.json`: 동일 키 한국어 값 추가
- `src/app/(dashboard)/onboarding/preset/page.tsx`: useTranslations 적용
- `src/app/(dashboard)/onboarding/maturity/page.tsx`: useTranslations 적용
- `src/components/presets/natural-language-input.tsx`: useTranslations 적용
- `src/components/onboarding/maturity-questionnaire.tsx`: useTranslations 적용
- `src/components/onboarding/maturity-result.tsx`: useTranslations 적용
- `src/app/(dashboard)/solutions/page.tsx`: useTranslations 적용
- `src/app/(dashboard)/solutions/new/page.tsx`: useTranslations 적용
- `src/app/(dashboard)/solutions/[sessionId]/page.tsx`: useTranslations 적용
- `src/app/(dashboard)/projects/page.tsx`: useTranslations 적용
- `src/app/(dashboard)/projects/[projectId]/page.tsx`: useTranslations 적용
- `src/app/(dashboard)/settings/members/page.tsx`: useTranslations 적용
- `src/app/(dashboard)/settings/linear/page.tsx`: useTranslations 적용
- `src/app/(dashboard)/settings/anthropic/page.tsx`: useTranslations 적용
- `src/app/(dashboard)/guide/page.tsx`: useTranslations 적용

## 구현 단계

1. messages/en.json + ko.json에 신규 키 묶음 추가
2. 각 페이지/컴포넌트에 useTranslations 적용
3. npm run lint && npm run typecheck 검증

## 예상 영향 범위

- 위저드 외 사용자 향 페이지 전부 i18n화
- DB에서 오는 데이터(가이드 내용, 질문/응답 텍스트 등)는 번역 불가 → 그대로 유지
- guide 페이지: 페이지 헤더/설명만 번역, 마크다운 콘텐츠는 그대로
- settings/linear: 가이드 블록 내 한국어도 i18n화

## STATUS: APPROVED
