## 목표
최종 확인 단계(step-confirmation)에서 deferred한 Linear/Notion 키를 추가 입력할 때 라이브 검증이 작동하지 않는 버그 수정. 검증 결과(valid/invalid) 뱃지를 노출하고, ZIP 다운로드 직전에도 잘못된 키를 사전에 잡아낸다.

## 변경 파일 목록
- `clickeye-web/src/components/solutions/wizard/integration-validation-badge.tsx`: **신규** — step-solution-env.tsx 안의 검증 뱃지 컴포넌트를 분리해 재사용 가능하게 함
- `clickeye-web/src/components/solutions/wizard/steps/step-solution-env.tsx`: 내부 정의 제거 → 분리된 컴포넌트 import
- `clickeye-web/src/components/solutions/wizard/steps/step-confirmation.tsx`:
  - `integrations`, store의 `envValidation/setEnvValidation` import 추가
  - `useEffect`로 envVars.LINEAR_API_KEY + LINEAR_TEAM_ID 변경 시 debounce 검증
  - Notion(NOTION_API_KEY + NOTION_DATABASE_ID) 동일 처리
  - "미입력 API 키" 섹션 하단에 IntegrationValidationBadge 표시

## 구현 단계
1. integration-validation-badge.tsx 추출 (props/타입 유지)
2. step-solution-env.tsx에서 인라인 정의 제거 + import 교체
3. step-confirmation.tsx에 검증 useEffect 두 개 + 뱃지 노출
4. typecheck + lint

## 예상 영향 범위
- step-solution-env.tsx: 동작 변화 없음(컴포넌트만 분리)
- step-confirmation.tsx: deferred 키 입력 시 자동 검증 + invalid 시 사용자 인지 가능 (게이트 차단은 별도 — 이 PR에서는 안내만 추가)
- 라이브 검증은 키 두 개가 모두 truthy 일 때만 호출됨 → 한 쪽만 입력해도 안전

## STATUS: APPROVED
