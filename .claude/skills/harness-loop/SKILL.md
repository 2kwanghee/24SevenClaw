---
name: harness-loop
description: 하네스 엔지니어링 3단계 — 코드 작성 → 자동 테스트 → 실패 시 에러 피드백 → 수정을 반복하는 자동 교정 루프. 테스트를 통과하기 전까지 빠져나갈 수 없다.
disable-model-invocation: false
user-invocable: false
---

# Harness Loop — 자동 교정 루프 (3단계)

> **테스트를 통과하기 전까지 AI는 이 루프를 빠져나갈 수 없다.** 사용자가 결과를 보기도 전에, AI가 스스로 오류를 수정하는 구조.

## 루프 구조

```
[하네스 루프 진입]
    │
    │  attemptCount = 0
    │  MAX_ATTEMPTS = 5
    │
    ├──→ 1. 컨텍스트 로딩 (harness-context 프로토콜)
    │       - 전역 제약 + 모듈 agent.md + 작업 관련 파일
    │
    ├──→ 2. 코드 작성 (WRITE_CODE 역할)
    │       - 제약 조건 준수하며 구현
    │       - 해당 모듈의 레이어 패턴 따름
    │       - 테스트 코드도 함께 작성 (tdd-smart-coding 원칙)
    │
    ├──→ 3. 자동 검증 실행
    │       ┌─────────────────────────────────────────────┐
    │       │ Gate 1: Lint                                 │
    │       │   api/agent: uv run ruff check .             │
    │       │   web: npm run lint                          │
    │       │   contracts: npx tsc --noEmit                │
    │       │                                              │
    │       │ Gate 2: Type Check                           │
    │       │   api: uv run mypy app/                      │
    │       │   agent: uv run mypy agent/                  │
    │       │   web: npx tsc --noEmit                      │
    │       │                                              │
    │       │ Gate 3: Unit Test                             │
    │       │   api: uv run pytest --cov=app -v            │
    │       │   agent: uv run pytest -v                    │
    │       │   web: npm run test                          │
    │       │                                              │
    │       │ Gate 4: Integration (해당 시)                 │
    │       │   api: uv run pytest tests/integration/ -v   │
    │       │   web: npm run build (빌드 검증)              │
    │       └─────────────────────────────────────────────┘
    │
    ├──→ 4-A. 전부 통과? → 최종 리뷰
    │         - CODE_REVIEW 역할로 코드 품질 검토 (ai-critique)
    │         - API 키 없으면 CODE_REVIEW 건너뛰고 완료 처리 (경고 로그)
    │         - 리뷰 통과 → ✅ 완료
    │         - 리뷰 지적 있음 → 수정 후 Gate 1부터 재검증
    │
    └──→ 4-B. 실패? → 에러 피드백 루프
              │
              ├── 에러 트레이스 구조화:
              │   {
              │     gate: "lint" | "typecheck" | "test" | "integration",
              │     module: "api" | "web" | "agent" | "contracts",
              │     errors: ["구체적 에러 메시지"],
              │     files: ["에러 발생 파일 경로"],
              │     suggestion: "수정 방향 힌트"
              │   }
              │
              ├── 태스크 업데이트:
              │   "코드가 다음 에러를 발생시켰습니다: {errorTrace}. 수정하세요."
              │
              ├── attemptCount++
              │
              └── MAX_ATTEMPTS 초과?
                  ├── NO → 루프 재진입 (Step 2부터, 컨텍스트는 유지하고 에러 트레이스만 추가)
                  └── YES → 🚨 에스컬레이션
                      - 사용자에게 알림
                      - 시도 횟수 + 반복된 에러 패턴 보고
                      - 수동 개입 요청
```

## 검증 게이트 선택 로직

모듈에 따라 자동으로 검증 명령어를 선택한다:

| 모듈 | Gate 1 (Lint) | Gate 2 (Type) | Gate 3 (Test) | Gate 4 (Integration) |
|------|--------------|---------------|---------------|---------------------|
| api | `uv run ruff check .` | `uv run mypy app/` | `uv run pytest --cov=app -v` | `uv run pytest tests/integration/` |
| web | `npm run lint` | `npx tsc --noEmit` | `npm run test` | `npm run build` |
| agent | `uv run ruff check .` | `uv run mypy agent/` | `uv run pytest -v` | — |
| contracts | `npx tsc --noEmit` | (동일) | — | `./scripts/generate-ts.sh` |

**CWD 규칙**: 각 모듈의 명령어는 해당 모듈 디렉토리에서 실행한다.
- api: `cd /mnt/c/workspace/24SevenClaw/24SevenClaw-api && ...`
- web: `cd /mnt/c/workspace/24SevenClaw/24SevenClaw-web && ...`
- agent: `cd /mnt/c/workspace/24SevenClaw/24SevenClaw-agent && ...`
- contracts: `cd /mnt/c/workspace/24SevenClaw/24SevenClaw-contracts && ...`

## 에러 피드백 프로토콜

실패한 검증의 에러를 다음 반복에 효과적으로 전달하는 방법:

### 1. 에러 구조화
```
Gate: typecheck
Module: api
Errors:
  - app/models/organization.py:15: error: "Column" is not generic [type-arg]
  - app/schemas/organization.py:8: error: Name "OrganizationBase" is not defined [name-defined]
Files: app/models/organization.py, app/schemas/organization.py
```

### 2. 피드백 주입
다음 반복의 작업 지시에 에러 트레이스를 포함:
```
이전 시도에서 다음 에러가 발생했습니다:
[구조화된 에러 트레이스]

이 에러들을 수정하면서, 나머지 기존 코드는 변경하지 마세요.
```

### 3. 연속 실패 처리
- 동일 에러 2회 연속 → 접근 방식 변경 시도 (다른 패턴/라이브러리)
- 동일 에러 3회 연속 → 에스컬레이션 (사용자에게 수동 개입 요청)

## ralph-loop과의 관계

| 항목 | harness-loop | ralph-loop |
|------|-------------|------------|
| 범위 | 단일 작업 (1개 기능/수정) | 다수 작업 (fix_plan.md 전체) |
| 반복 단위 | 코드 작성 → 테스트 (세션 내) | 세션 단위 반복 (컨텍스트 리셋) |
| 연동 | ralph-loop 안에서 각 항목을 harness-loop로 실행 가능 | harness-loop을 내부적으로 활용 |
| MAX | 5회 (작업당) | 30회 (전체 플랜) |

**통합 시나리오**: ralph-loop가 fix_plan.md의 각 항목을 순회하면서, 각 항목을 harness-loop으로 실행 → 자동 테스트 통과까지 반복 → 통과 시 다음 항목으로.

## tdd-smart-coding과의 관계

harness-loop의 "코드 작성" 단계에서 tdd-smart-coding의 Red-Green-Refactor 사이클을 적용한다:

```
harness-loop Step 2 (코드 작성):
  ├── tdd: 테스트 먼저 작성 (Red)
  ├── tdd: 최소 구현 (Green)
  ├── tdd: 리팩터링 (Refactor)
  └── harness: Gate 1~4 자동 검증
```

**중요**: 하네스 루프 내에서 tdd-smart-coding을 실행할 때, tdd의 Step 6(커밋)은 **보류**한다. 커밋은 하네스 루프가 완전히 완료된 후(모든 Gate 통과 + CODE_REVIEW 통과) 한 번만 수행한다.

## 완료 기준

하네스 루프가 "완료"로 판단하는 조건:

1. ✅ Gate 1~3 전부 통과 (lint, typecheck, unit test)
2. ✅ Gate 4 통과 (해당하는 경우)
3. ✅ CODE_REVIEW 지적사항 없음 (또는 수정 완료)
4. ✅ 기존 테스트 깨지지 않음 (regression 없음)
