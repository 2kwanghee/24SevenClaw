## 목표
프로젝트 상세 페이지의 ZIP 재다운로드 영역에서 Linear API Key 등 통합 키 input 에 한글이 들어가면 fetch 가 실패하는 케이스를, 가장 안쪽 layer 인 **input onChange sanitize** 로 차단한다. 비-printable ASCII 가 입력되면 그 글자는 input value 에 들어가지 않고 inline 경고가 뜬다.

## 변경 파일 목록
- `clickeye-web/src/lib/integration-validators.ts`:
  - `sanitizeIntegrationInput(value)` 헬퍼 추가 — 비-printable ASCII 를 제거한 문자열 반환
- `clickeye-web/src/app/(dashboard)/projects/[projectId]/page.tsx`:
  - ENV_FIELDS 의 input onChange 에 sanitize 적용
  - sanitize 로 글자가 잘렸을 때 inline 경고 노출 (필드별)
- `clickeye-web/src/lib/__tests__/integration-validators.test.ts`: **신규** — sanitize 시나리오 검증

## 구현 단계
1. integration-validators.ts 에 sanitizeIntegrationInput 추가
2. project page input onChange 보강 + inline 경고 state
3. 테스트 추가 + npm test

## 예상 영향 범위
- 한글/이모지 입력은 input 표시 단계에서 차단 → state 에 한글이 절대 들어가지 않음
- 따라서 useEffect 의 라이브 검증은 ASCII-only 값만 받음 → fetch 가 검증 가능한 형태로 호출
- 정상 ASCII 입력은 동작 변경 없음
- 위저드 step 9 / step 11 의 input 들은 별도 컴포넌트라 이번 PR 범위 아님 (필요 시 다음 PR)

## STATUS: APPROVED
