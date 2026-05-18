## 목표
위저드의 모든 환경변수 입력 input 에도 sanitizeIntegrationInput 을 적용해, 한글/이모지/제어문자가 envVars 에 절대 들어가지 않도록 한다. project page 와 동일 정책.

## 변경 파일 목록
- `clickeye-web/src/components/solutions/wizard/steps/step-solution-env.tsx`:
  - `RequiredKeyRow` 의 draft 입력 onChange 에 sanitize 적용 + 잘림 발생 시 inline 경고
  - 추가 환경변수 폼 (newKey/newValue) 의 newValue 에 sanitize
  - ngrok 인증 토큰 input 에도 sanitize
- `clickeye-web/src/components/solutions/wizard/steps/step-confirmation.tsx`:
  - "미입력 API 키 게이트" 의 draftDeferred input 에 sanitize + 잘림 안내

## 구현 단계
1. step-solution-env.tsx 의 RequiredKeyRow 보강 (sanitize + 안내 flag)
2. 환경변수 추가 input · ngrok 토큰 input 에 sanitize 적용
3. step-confirmation.tsx 의 deferred input 에 sanitize + 안내
4. typecheck + lint + vitest

## 예상 영향 범위
- 위저드 7-Step 환경변수 입력 모두 ASCII-only 보장
- IME 합성 결과로 한글이 한 번에 들어와도 envVars 에 절대 저장 안 됨
- 백엔드 라이브 검증 fetch 는 항상 ASCII body 로만 호출됨

## STATUS: APPROVED
