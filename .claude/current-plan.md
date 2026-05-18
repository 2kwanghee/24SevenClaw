## 목표
M1 — Feature flag (`FEATURE_MODERNIZE_ENABLED`) + wizard-store 의 `mode` 분기 도입.
plan 의 비침습성 원칙 입증을 위해 **기존 사용처 시그니처 변경 0**, **기존 SOLUTION_WIZARD_STEPS export 그대로 유지**, **default mode='new'** 로 기존 동작 100% 유지.

## 변경 파일 목록

### 프론트엔드 (추가 only)
- `clickeye-web/src/types/solution-wizard.ts`:
  - 추가: `SolutionWizardMode = "new" | "modernize"` 타입
  - 추가: `MODERNIZE_WIZARD_STEPS` placeholder 배열 (M4 에서 채워짐)
  - 추가: `getWizardSteps(mode)` helper — mode 에 따라 적절한 STEPS 배열 반환
  - **기존 `SOLUTION_WIZARD_STEPS` 미변경**
- `clickeye-web/src/stores/solution-wizard-store.ts`:
  - state 에 `mode: SolutionWizardMode` 필드 추가 (initialState.mode = "new")
  - actions 에 `setMode(mode)` 추가
  - **기존 setter 시그니처 미변경, 기본 동작 100% 유지**
- `clickeye-web/src/lib/feature-flags.ts` — **신규**:
  - `isModernizeEnabled()` → `process.env.NEXT_PUBLIC_FEATURE_MODERNIZE_ENABLED === "true"`
- `clickeye-web/.env.example`:
  - `NEXT_PUBLIC_FEATURE_MODERNIZE_ENABLED=false` 추가

### 백엔드 (추가 only)
- `clickeye-api/app/config.py`:
  - `Settings` 에 `feature_modernize_enabled: bool = False` 필드 추가
- `clickeye-api/.env.example`:
  - `FEATURE_MODERNIZE_ENABLED=false` 추가

### 테스트
- `clickeye-web/src/lib/__tests__/feature-flags.test.ts` — **신규** (3 케이스)
- `clickeye-web/src/stores/__tests__/solution-wizard-store.test.ts` — 기존 케이스 확인 + `mode` default + `setMode` 추가 검증 (R-5 회귀 안전 확인)
- (선택) `clickeye-api/tests/test_config.py` — feature flag 기본값 false 확인

## 구현 단계
1. types/solution-wizard.ts: SolutionWizardMode + MODERNIZE_WIZARD_STEPS placeholder + getWizardSteps helper 추가
2. solution-wizard-store.ts: mode 필드 + setMode 추가 (기존 코드 미변경)
3. lib/feature-flags.ts: helper 신규
4. .env.example 양쪽 추가
5. config.py: 백엔드 settings 필드 추가
6. wizard-store.test.ts: R-5 회귀 + mode 추가 케이스
7. feature-flags.test.ts 신규
8. vitest + tsc + ruff/mypy 검증

## 예상 영향 범위
- 기존 SOLUTION_WIZARD_STEPS / setter 시그니처 / 호출 결과 변화 없음
- mode 미설정 시 기존 'new' 동작 100% 유지
- Feature flag 미설정 시 false (Modernize 비활성)
- 기존 vitest / pytest 100% 통과 보장 (R-5)

## STATUS: APPROVED
