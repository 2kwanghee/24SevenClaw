## 목표

위저드 Step 1~3 (회사 정보 입력 → 프로토타입 생성 → 프로토타입 선택)의 하드코딩 한국어 텍스트를 next-intl 카탈로그 키로 치환하여 영문 locale 전환을 지원한다.

## 변경 파일 목록

- `messages/ko.json`: `wizard.step1`, `wizard.step2`, `wizard.step3` 키 묶음 추가
- `messages/en.json`: 동일 키 영문 값 추가
- `clickeye-web/src/components/solutions/wizard/steps/step-company-solution.tsx`: useTranslations 적용
- `clickeye-web/src/components/solutions/wizard/steps/step-prototype-generation.tsx`: useTranslations 적용
- `clickeye-web/src/components/solutions/wizard/steps/step-prototype-selection.tsx`: useTranslations 적용
- `clickeye-web/src/components/solutions/wizard/prototype-card.tsx`: useTranslations 적용
- `clickeye-web/src/components/prototypes/prototype-comparison-table.tsx`: useTranslations 적용
- `clickeye-web/src/components/prototypes/metric-badges.tsx`: useTranslations 적용 (유지보수 라벨, 주/명 단위)

## 구현 단계

1. `messages/ko.json` + `messages/en.json`에 wizard.step1/step2/step3 키 추가
2. step-company-solution.tsx → useTranslations("wizard.step1") 적용
3. step-prototype-generation.tsx → useTranslations("wizard.step2") 적용
4. step-prototype-selection.tsx → useTranslations("wizard.step3") 적용
5. prototype-card.tsx → useTranslations("wizard.prototypeCard") 적용
6. prototype-comparison-table.tsx → useTranslations("wizard.comparisonTable") 적용
7. metric-badges.tsx → useTranslations("wizard.metricBadges") 적용
8. npm run typecheck && npm run build 검증

## 예상 영향 범위

- 위저드 Step 1~3 UI 텍스트 전부 i18n화
- AI 분석 텍스트(reasoning/rationale/matchReasoning)는 백엔드가 한국어로 반환하므로 그대로 유지
- AI 분석 임시 안내 라벨 추가: "AI analysis text is currently shown in Korean. Backend i18n in progress."

## STATUS: APPROVED
