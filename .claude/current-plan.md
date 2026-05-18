## 목표
위저드 input sanitize 동작을 vitest + React Testing Library 로 실제 React 렌더링 + paste 이벤트 레벨에서 결정적 검증한다. WSL 환경에서 GUI 브라우저 자동화가 어려우므로 jsdom 컴포넌트 테스트로 사용자 입력 시뮬레이션.

## 변경 파일 목록
- `clickeye-web/src/components/solutions/wizard/steps/step-solution-env.tsx`:
  - `RequiredKeyRow` 함수에 `export` 추가 (RTL 테스트에서 직접 import 하기 위함). 동작 변화 없음.
- `clickeye-web/src/components/solutions/wizard/steps/__tests__/required-key-row.test.tsx`: **신규**
  - 한글 paste → 잘림 검증 (state 에 한글 안 들어감)
  - amber 안내 메시지 노출 검증
  - ASCII 입력은 그대로 통과 검증
  - 저장 버튼 → onChange 콜백 호출 검증

## 구현 단계
1. step-solution-env.tsx: `function RequiredKeyRow` → `export function RequiredKeyRow`
2. 테스트 파일 작성 (RTL + userEvent.paste)
3. vitest 실행
4. (보너스) dev 서버 + 변경 반영 확인 + 사용자 측 브라우저 시나리오 가이드

## 예상 영향 범위
- export 추가만 — 다른 사용처 영향 없음
- RTL 테스트로 sanitize 가 React 이벤트 단계에서 동작함을 결정적 확인
- 위저드 step 9 의 핵심 입력 컴포넌트 동작 회귀 방지

## STATUS: APPROVED
