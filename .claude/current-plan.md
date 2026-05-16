## 목표
환경변수(Step 9) 스텝에서 외부 통합 스킬(Linear/Notion 등)의 키를 미입력해도 "다음" 버튼이 활성화되도록 canProceed 게이트를 완화한다. ANTHROPIC_API_KEY만 진짜 필수로 유지하고, 라이브 검증은 invalid 상태만 차단한다.

## 변경 파일 목록
- `clickeye-web/src/app/(dashboard)/solutions/new/page.tsx`:
  - case 9에서 외부 스킬의 required env_var 강제 검증 루프 제거
  - 라이브 검증 차단 조건을 `!== "valid"` → `=== "invalid"`로 완화
- `clickeye-web/src/app/(dashboard)/solutions/[sessionId]/page.tsx`:
  - 동일 수정
  - ANTHROPIC deferred 분기를 new/page.tsx와 일관성 있게 추가

## 구현 단계
1. new/page.tsx case 9 수정
2. [sessionId]/page.tsx case 9 수정 (ANTHROPIC deferred 분기 포함)
3. lint + typecheck 확인
4. 기존 테스트(solution-wizard-store.test.ts, solution-wizard-layout.test.tsx)에 영향 있는지 확인 — canProceed 테스트가 store 외부에 있으므로 영향 적을 것

## 예상 영향 범위
- UX: 외부 통합 키 미입력 상태에서도 다음 진행 가능. ZIP에는 빈 값으로 들어가며 사용자가 로컬에서 채워 사용한다 (기존 "필수 미설정" 시각적 경고는 유지).
- 라이브 검증: 잘못된 키(invalid)는 여전히 차단 — 사용자가 잘못된 키 입력 후 진행하는 사고는 방지.
- ANTHROPIC API key 게이트는 변경 없음(api_key 모드에서 강제, deferred 우회 가능).

## STATUS: APPROVED
