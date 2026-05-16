## 목표
프로젝트 상세 페이지(`projects/[projectId]/page.tsx`)의 "설정 요약 + ZIP 재다운로드" 영역에서 Linear/Notion API Key 라이브 검증을 추가하고, 검증 결과 invalid 시 ZIP 다운로드 버튼을 차단한다. 현재는 키가 채워져 있기만 하면(아무 값) 게이트가 통과되는 보안/UX 결함.

## 변경 파일 목록
- `clickeye-web/src/app/(dashboard)/projects/[projectId]/page.tsx`:
  - import 추가: `useCallback, useEffect, useMemo, useRef` (useState는 이미 있음), `integrations`, `IntegrationValidationBadge`
  - 컴포넌트 최상단에 hasLinear/hasNotion, 검증 상태 두 개, debounce 트리거 함수 두 개, useEffect 두 개 (envVars 변경 감지)
  - IIFE 안의 `downloadDisabled` 조건에 `linearValidation.status === "invalid"` / `notionValidation.status === "invalid"` 추가
  - ENV_FIELDS 그리드 아래 / 게이트 alert 위에 `IntegrationValidationBadge` 두 개 노출

## 구현 단계
1. import 보강
2. 검증 hooks/상태 추가
3. downloadDisabled 조건 보강
4. 검증 뱃지 UI 추가
5. typecheck + lint

## 예상 영향 범위
- 사용자가 잘못된 Linear/Notion 키를 입력해 ZIP을 받는 사고 차단
- 800ms debounce로 호출 빈도 제어
- idle/loading/valid 통과 — 위저드 step 9/11 정책과 일치
- 위저드 store(`envValidation`)와 무관한 로컬 상태로 관리 → 위저드 흐름 영향 없음

## STATUS: APPROVED
