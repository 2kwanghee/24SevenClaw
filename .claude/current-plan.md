## 목표
1. 위저드 step 9에서 API 키 입력을 선택적으로 만들어, ZIP 다운로드 직전에 미입력 키를 일괄 수집
2. `listSessions()` 추가 + `ce init` 실행 시 저장된 세션 목록 표시하여 임시저장 재개 UX 개선

## 변경 파일 목록
- `src/wizard/state.ts`: EnvStep에 `deferredEnvVars?: string[]` 필드 추가
- `src/wizard/session.ts`: SessionSummary 타입 + listSessions() 함수 추가
- `src/wizard/steps/09-env.ts`: 모든 시크릿 입력에 "나중에 입력" 건너뛰기 옵션 추가
- `src/wizard/steps/11-confirm.ts`: 다운로드 직전 미입력 환경 변수 일괄 수집 단계 추가
- `src/commands/init.ts`: 저장된 세션 목록 표시 + 선택 흐름 추가
- `tests/wizard-steps-7-10.test.ts`: step09 건너뛰기 케이스 + listSessions 테스트
- `tests/wizard-step-11.test.ts`: 사전 다운로드 env var 수집 테스트

## 구현 단계

### Phase A — State 확장 + Session 목록 조회
1. `state.ts`: `EnvStep.deferredEnvVars?: string[]` 추가
2. `session.ts`: `SessionSummary` 타입 + `listSessions()` 구현
   - `~/.config/clickeye/session-*.json` 파일 스캔
   - `{ sessionId, companyName, currentStep, savedAt }` 배열 반환 (최신순)

### Phase B — step09: API 키 건너뛰기
3. `step09-env.ts` 수정:
   - **Claude api_key**: `validate` 제거, 빈 입력 허용. 빈 값이면 `deferredEnvVars`에 추가
   - **oauth_setup_token**: 동일하게 선택적으로
   - **Linear**: "지금 설정 / 나중에 입력" list 선택지 추가. "나중에"면 LINEAR_API_KEY, LINEAR_TEAM_ID를 deferredEnvVars에 추가하고 validation 건너뜀
   - **Notion**: 동일
   - **스킬 required env_vars**: 빈 입력 허용, 빈 값이면 deferredEnvVars에 추가
   - 완료 메시지에 `(${deferred.length}개 나중에 입력 예정)` 표시

### Phase C — step11: 다운로드 직전 수집
4. `step11-confirm.ts` 수정:
   - 사용자 confirm 이후, `downloadAndExtract` 이전에 deferredEnvVars 처리 추가:
     ```
     ⚠️  다음 환경 변수가 아직 입력되지 않았습니다. 지금 입력하거나 Enter로 건너뛸 수 있습니다.
       → 건너뛰면 프로젝트 .env 파일에 빈 값으로 포함됩니다.
     ```
   - 각 deferredVar에 대해 password prompt (optional: 빈 값 허용)
   - 입력된 값만 envVars에 병합
   - `finalize` 페이로드는 기존 그대로 (null이면 null로 전송 — 이미 백엔드 지원)

### Phase D — init.ts: 세션 목록 UI
5. `init.ts` 수정:
   - `flags.resume` 없을 때: `listSessions()` 호출
   - 세션이 1개 이상이면:
     ```
     💾 저장된 진행 중 세션:
       ❯ [Step 9/11] 테스트 주식회사 — 2026-05-11 14:32
         [Step 5/11] ABC Corp — 2026-05-10 09:15
         새로 시작
     ```
   - 선택 시 해당 session을 loadSession으로 복원, resume 흐름과 동일하게 진행

### Phase E — 테스트 + 검증
6. `tests/wizard-steps-7-10.test.ts` 업데이트:
   - step09: "건너뛰기" 선택 시 deferredEnvVars에 추가되는 케이스
   - step09: Linear 건너뛰기 시 validation API 호출 안 됨
   - `listSessions`: 세션 없음, 세션 다수 케이스
7. `tests/wizard-step-11.test.ts` 업데이트:
   - deferredEnvVars 있을 때 prompt 표시 테스트
   - deferredEnvVars 없을 때 prompt 생략 테스트
8. `pnpm typecheck && pnpm test` 전체 통과 확인

## 예상 영향 범위
- `--resume` 기존 동작 유지 (그대로 동작)
- finalize API 호출 로직 변경 없음 (null 값은 이미 지원됨)
- `downloadAndExtract` 시그니처 변경 없음
- 기존 테스트 일부 mock 업데이트 필요 (step09 입력 시퀀스 변경)
