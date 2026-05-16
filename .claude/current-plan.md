## 목표
Linear/Notion API Key 라이브 검증 호출 전에 클라이언트 측 사전 검증을 추가해, 한글/공백/제어문자 등 백엔드까지 보낼 수 없는 입력이 들어오면 fetch 호출 자체를 건너뛰고 명확한 invalid 메시지를 노출한다. catch 절도 보강해 dev 콘솔 stacktrace를 줄이고 사용자 친화 메시지를 표시한다.

## 변경 파일 목록
- `clickeye-web/src/lib/integration-validators.ts`: **신규** — `sanitizeForIntegrationApi(value)` / `assertAsciiInput(value)` 헬퍼 (중복 코드 회피)
- `clickeye-web/src/app/(dashboard)/projects/[projectId]/page.tsx`:
  - triggerLinearValidation / triggerNotionValidation 에서 사전 검증 (헬퍼 사용)
  - catch 절 보강 (err 메시지 표시)
- `clickeye-web/src/components/solutions/wizard/steps/step-solution-env.tsx`:
  - 동일 적용
- `clickeye-web/src/components/solutions/wizard/steps/step-confirmation.tsx`:
  - 동일 적용

## 구현 단계
1. lib/integration-validators.ts 신규 작성 (ASCII-only 검사, 메시지 반환)
2. 세 컴포넌트의 trigger* 두 함수 보강 (사전 검증 → fetch 건너뜀, invalid 처리)
3. catch (err) 보강 — Error 인스턴스의 message 추출, 친절한 안내
4. typecheck + lint

## 예상 영향 범위
- 잘못된 입력으로 인한 fetch 실패 → dev 콘솔 stacktrace 노출 차단
- 한글/이모지/공백 입력 시 즉시 invalid 메시지 노출 (백엔드 호출 X)
- 정상 입력 동작은 변경 없음
- catch 처리 일관: 네트워크 에러 / API 에러 모두 invalid 뱃지로 통합

## STATUS: APPROVED
