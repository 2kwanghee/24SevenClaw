## 목표

위저드 Step 4~7 (PM 추천/선택/구성, 에이전트/스킬, 플랫폼/OS, 환경변수/ROI, 확인/다운로드) 하드코딩 한국어 텍스트를 next-intl 카탈로그 키로 치환하여 영문 locale 전환을 지원한다.

## 변경 파일 목록

- `clickeye-web/messages/en.json`: wizard.step4~step7 + setupGuide.* 키 추가
- `clickeye-web/messages/ko.json`: 동일 키 한국어 값 추가
- `src/components/solutions/wizard/steps/step-pm-recommendation.tsx`: useTranslations 적용
- `src/components/solutions/wizard/steps/step-pm-select.tsx`: useTranslations 적용
- `src/components/solutions/wizard/steps/step-pm-selection.tsx`: useTranslations 적용
- `src/components/solutions/wizard/steps/step-pm-composition.tsx`: useTranslations 적용 (CATEGORY_CONFIG 인라인화)
- `src/components/solutions/wizard/steps/step-solution-agents.tsx`: useTranslations 적용
- `src/components/solutions/wizard/steps/step-solution-platform.tsx`: useTranslations 적용 (PLATFORM_OPTIONS 인라인화)
- `src/components/solutions/wizard/steps/step-solution-os.tsx`: useTranslations 적용 (OS_OPTIONS 인라인화)
- `src/components/solutions/wizard/steps/step-solution-env.tsx`: useTranslations 적용
- `src/components/solutions/wizard/steps/step-solution-roi.tsx`: useTranslations 적용 (ROLE_LABELS 인라인화)
- `src/components/solutions/wizard/steps/step-solution-confirm.tsx`: useTranslations 적용 (레이블 맵 인라인화)
- `src/components/solutions/wizard/steps/step-confirmation.tsx`: useTranslations 적용 (레이블 맵 + SetupGuideModal 인라인화)
- `src/components/solutions/wizard/pm-composition-view.tsx`: useTranslations 적용

## 구현 단계

1. messages/en.json + ko.json에 wizard.step4~step7 + setupGuide 키 추가
2. 각 컴포넌트에 useTranslations 적용 (모듈 스코프 상수의 한국어 레이블을 컴포넌트 내부로 이동)
3. npm run lint && npm run typecheck && npm run build 검증

## 예상 영향 범위

- 위저드 Step 4~7 UI 텍스트 전부 i18n화
- SetupGuideModal 텍스트 영문화
- step-pm-select.tsx, step-solution-confirm.tsx는 미사용(legacy)이나 스펙에 포함되어 처리
- DB에서 오는 데이터(PM 이름, composition 칩의 component_name 등)는 번역 불가 → 그대로 유지

## STATUS: APPROVED
