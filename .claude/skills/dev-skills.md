# ClickEye - Development Skills Registry

> 프로젝트 개발에 사용되는 스킬(자동화 워크플로) 정의

---

## Skill 1: setup-module
**용도**: 새 모듈(레포) 초기화
**트리거**: 레포 디렉토리가 비어있을 때

### Steps
```
1. agents/{module}-agent.md 읽기 → 기술 스택 파악
2. 프로젝트 scaffolding 실행
   - web: npx create-next-app@latest
   - api: uv init + FastAPI 구조
   - agent: uv init + 데몬 구조
   - infra: Docker Compose + scripts
   - contracts: npm init + 스키마 구조
3. agents/{module}-agent.md를 {module}/CLAUDE.md로 복사
4. .gitignore, .env.example 생성
5. git init + 초기 커밋
```

---

## Skill 2: api-endpoint
**용도**: 새 REST API 엔드포인트 추가
**트리거**: API 엔드포인트 구현 요청 시

### Steps
```
1. schemas/{resource}.py 생성 (Pydantic 요청/응답)
2. models/{resource}.py 생성/수정 (SQLAlchemy 모델)
3. services/{resource}_service.py 생성 (비즈니스 로직)
4. api/v1/{resource}.py 생성 (라우터)
5. api/v1/router.py에 라우터 등록
6. Alembic 마이그레이션 생성 (모델 변경 시)
7. tests/test_{resource}.py 생성
8. 테스트 실행 + 린트 확인
```

---

## Skill 3: ui-page
**용도**: 새 페이지/컴포넌트 추가
**트리거**: UI 페이지 또는 컴포넌트 구현 요청 시

### Steps
```
1. 필요한 shadcn/ui 컴포넌트 확인 + 설치
2. app/{route}/page.tsx 생성
3. components/{domain}/{component}.tsx 생성
4. hooks/use-{data}.ts 생성 (TanStack Query 훅)
5. 필요 시 stores/{domain}-store.ts 수정
6. 타입은 contracts에서 import 확인
7. 린트 + 타입체크 실행
```

---

## Skill 4: agent-handler
**용도**: 새 Agent 핸들러 추가
**트리거**: Agent에 새 명령 처리 기능 추가 시

### Steps
```
1. contracts/protocol에 메시지 타입 정의
2. contracts/python/protocol.py에 Pydantic 모델 추가
3. agent/handlers/{name}_handler.py 생성 (BaseHandler 상속)
4. agent/dispatcher.py에 핸들러 등록
5. 테스트 작성
6. docs/agent-protocol.md 업데이트
```

---

## Skill 5: db-migration
**용도**: DB 스키마 변경
**트리거**: 모델 변경 또는 새 테이블 추가 시

### Steps
```
1. models/{table}.py 수정/생성
2. alembic revision --autogenerate -m "설명"
3. 마이그레이션 파일 리뷰 (자동 생성 확인)
4. alembic upgrade head (로컬 DB 적용)
5. 테스트 실행으로 기존 기능 정상 확인
6. contracts 스키마 변경 필요 시 동기화
```

---

## Skill 6: contract-sync
**용도**: API 변경 후 contracts 동기화
**트리거**: API 엔드포인트 변경 후

### Steps
```
1. [api] openapi_export.py 실행 → openapi.json 생성
2. [contracts] openapi/openapi.json 업데이트
3. [contracts] scripts/generate-ts.sh 실행
4. [contracts] generated/ 파일 검증 (tsc --noEmit)
5. [web] 새 타입/클라이언트 사용하여 코드 업데이트
6. 양쪽 린트 + 타입체크 확인
```

---

## Skill 7: run-tests
**용도**: 테스트 실행
**트리거**: 코드 변경 후 검증 시

### Module별 테스트 커맨드
```yaml
api:
  lint: "uv run ruff check ."
  typecheck: "uv run mypy app/"
  test: "uv run pytest --cov=app -v"
  all: "uv run ruff check . && uv run mypy app/ && uv run pytest --cov=app"

web:
  lint: "npm run lint"
  typecheck: "npx tsc --noEmit"
  test: "npm run test"
  build: "npm run build"
  all: "npm run lint && npx tsc --noEmit && npm run test && npm run build"

agent:
  lint: "uv run ruff check ."
  typecheck: "uv run mypy agent/"
  test: "uv run pytest -v"
  all: "uv run ruff check . && uv run mypy agent/ && uv run pytest"

contracts:
  validate: "npx tsc --noEmit"
  generate: "./scripts/generate-ts.sh"
```

---

## Skill 8: docker-env
**용도**: Docker 개발 환경 관리
**트리거**: 개발 환경 시작/중지/리셋 시

### Commands
```yaml
start: "cd clickeye-infra && docker compose up -d"
stop: "cd clickeye-infra && docker compose down"
reset: "cd clickeye-infra && docker compose down -v && docker compose up -d"
logs: "cd clickeye-infra && docker compose logs -f"
status: "cd clickeye-infra && docker compose ps"
migrate: "cd clickeye-api && uv run alembic upgrade head"
seed: "cd clickeye-infra && ./scripts/seed-db.sh"
full-setup: "cd clickeye-infra && ./scripts/setup-dev.sh"
```

---

## Skill 9: pre-commit-check
**용도**: 커밋 전 품질 검증
**트리거**: git commit 전

### Steps
```
1. 변경된 파일의 모듈 감지
2. 해당 모듈 lint 실행
3. 해당 모듈 typecheck 실행
4. 해당 모듈 테스트 실행 (변경 관련만)
5. contracts 변경 시 → 양쪽 동기화 확인
6. 모두 통과 → 커밋 허용
```

---

## Skill 10: kickoff-day
**용도**: 개발 일과 시작
**트리거**: 매일 개발 시작 시

### Steps
```
1. TODO.md 읽기 → 오늘의 태스크 확인
2. Docker 개발 환경 상태 확인 (필요 시 시작)
3. 각 모듈 git status 확인 (미커밋 변경 확인)
4. 오늘 할 작업을 Task로 생성
5. 첫 번째 태스크부터 시작
```

---

## 하네스 엔지니어링 스킬 (Harness Engineering)

> AI 코드 작성을 `라우팅 → 컨텍스트 제어 → 자동 교정 루프 → 역할 분리` 4단계로 통제.
> 전체 가이드: `.claude/agents/harness-guide.md`

### Skill H1: harness-router
**용도**: 사용자 요청의 의도 분석 + 라우팅 게이트웨이
**위치**: `.claude/skills/harness-router/SKILL.md`
**동작**: 모호한 요청 → 되물어보기, 명확한 작업 → 하네스 루프, 일반 대화 → 표준 응답

### Skill H2: harness-context
**용도**: 현재 작업에 필요한 정보만 선별 제공 (가림막)
**위치**: `.claude/skills/harness-context/SKILL.md`
**동작**: 전역 제약 고정 + 모듈별 agent.md 로딩 + 완료된 코드 자동 정리

### Skill H3: harness-loop
**용도**: 코드 작성 → 자동 테스트 → 에러 피드백 → 수정 반복 루프
**위치**: `.claude/skills/harness-loop/SKILL.md`
**동작**: Gate 1~4 (lint/type/test/integration) 통과까지 MAX 5회 반복
**연동**: ralph-loop (다수 작업 반복), tdd-smart-coding (Red-Green-Refactor)

### Skill H4: harness-worker
**용도**: 코드 작성자 / 리뷰어 / 보안 검토자 역할 분리
**위치**: `.claude/skills/harness-worker/SKILL.md`
**역할**: WRITE_CODE (fullstack), TEST_WRITER (tdd), CODE_REVIEW (ai-critique), SECURITY_REVIEW

---

## 메타프롬프팅 스킬 (관측형 사전 정제)

### Skill: metaprompt
**용도**: 거친 태스크를 구현 직전에 고품질 "구현 스펙"으로 다듬는 관측형 사전 정제
**위치**: `.claude/skills/metaprompt/SKILL.md`
**트리거**: 구현(harness-loop) 전 단계 / 자동 파이프라인의 기획 단계
**동작**: Context(가림막: CLAUDE.md·module-agent.md 컨벤션 인용) → Router(가정 명시) → 구현 스펙 마크다운만 출력(코드 금지) → 자기 점검
**연동**:
- **자동 파이프라인**: `scripts/auto_dev_pipeline.sh` STEP A가 `FLOWOPS_METAPROMPT=true`(기본)일 때 기획 단계로 비대화형(`claude -p`) 호출 → `.ralph/refined/{ISSUE}.md` + `.ralph/PLAN.md` + Linear 코멘트. `false`면 레거시 Gemini 기획(`FLOWOPS_GEMINI_PLAN`)으로 폴백. 머지 직전 거버넌스 게이트(`pre_merge_gate.py`)가 정합성·위험을 검증.
- **대화형 하네스**: harness-loop 구현 전 구현 스펙 생성 단계로 사용 ([[pm-agent]] 참조)

---

## 보고 스킬

### Skill: weekly-report
**용도**: 금주(이번 주 월요일~오늘) git 커밋을 모아 주간보고 마크다운 생성
**위치**: `.claude/skills/weekly-report/SKILL.md`
**트리거**: "주간보고", "금주 작업 내역", "이번 주 작업 정리", "weekly report"
**동작**: `scripts/collect_week.sh`로 주차·제목·출력경로·커밋 결정론적 수집 → 모델이 불릿 큐레이션 → `docs/WeeklyWorkReport/<주월요일>/weekly-report.md` 작성. 지난 주는 `--week-offset N`.
