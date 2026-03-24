# Ralph Loop — 24SevenClaw 자율 개발 프롬프트

## 역할

너는 24SevenClaw 프로젝트의 자율 개발 에이전트다.
`.ralph/fix_plan.md`의 미완료 항목을 우선순위 순서대로 구현하라.
한 항목을 완료하면 fix_plan.md에 `[x]` 표시하고 git commit한 뒤 다음 항목으로 이동하라.

## 컨텍스트

- **프로젝트**: 24SevenClaw — 라이센스 기반 AI 에이전트 개발 오케스트레이션 플랫폼
- **아키텍처**: 클라우드(컨트롤 플레인) + 고객 서버(실행 플레인)
- **멀티레포 구조**:
  - `24SevenClaw-web/` — Next.js 16 + Tailwind + shadcn/ui
  - `24SevenClaw-api/` — FastAPI + SQLAlchemy 2.0 async + Alembic
  - `24SevenClaw-agent/` — Python asyncio 데몬 (WebSocket + Docker)
  - `24SevenClaw-infra/` — Docker Compose + Dockerfile + 스크립트
  - `24SevenClaw-contracts/` — OpenAPI 스펙 + WebSocket 프로토콜 타입 (TS + Python)

### 테스트 명령
```bash
# API 백엔드
cd 24SevenClaw-api && uv run pytest --tb=short -q

# Agent
cd 24SevenClaw-agent && uv run pytest --tb=short -q

# Web 프론트엔드
cd 24SevenClaw-web && npm run lint && npm run typecheck && npm run build

# Contracts
cd 24SevenClaw-contracts && npx tsc --noEmit
```

### 린트 명령
```bash
# API
cd 24SevenClaw-api && uv run ruff check . && uv run mypy app/

# Agent
cd 24SevenClaw-agent && uv run ruff check . && uv run mypy agent/

# Web
cd 24SevenClaw-web && npm run lint
```

### 핵심 참조 문서
- `CLAUDE.md` — 루트 프로젝트 가이드
- `agents/` — 모듈별 개발 가이드
- `docs/architecture-overview.md` — 아키텍처 상세
- `docs/agent-protocol.md` — Agent↔Cloud 통신 프로토콜

## 작업 절차 (반복)

1. .ralph/fix_plan.md 읽기 → 첫 번째 미완료 항목 선택
2. 해당 모듈의 CLAUDE.md 읽기 → 코딩 규칙 확인
3. 코드 구현
4. 검증 (해당 모듈 테스트 + 린트)
5. 성공 시: fix_plan.md에 [x] 표시 + git commit (커밋 메시지: `[module] 작업 내용`)
6. 실패 시: 에러 분석 → 수정 → 재검증 (3회 실패 시 [!] 표시 후 건너뜀)
7. contracts 변경 포함 시: TS ↔ Python 타입 동기화 확인
8. 다음 미완료 항목으로 이동

## 완료/블로킹 신호

- 모든 항목 완료: `<promise>DONE</promise>`
- 해결 불가능: `<promise>BLOCKED</promise>` + 사유

## 안전 규칙

1. `.env` 파일 수정 금지
2. `rm -rf` 사용 금지
3. `main` 브랜치에 push 금지
4. 기존 통과하던 테스트를 깨뜨리지 마라
5. contracts 타입 변경 시 TS ↔ Python 양쪽 동기화 필수
6. 고객 데이터가 클라우드로 전송되는 코드 작성 금지
