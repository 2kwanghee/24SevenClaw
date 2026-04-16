# 24SevenClaw - Development Guide

## Project Overview
AI 개발 자동화 솔루션 빌더 플랫폼.
- **Web-First 아키텍처**: 브라우저에서 7-Step 위저드로 솔루션 설계 → ZIP 다운로드 → 로컬에서 AI 개발
- **멀티 Agent 플랫폼**: Claude Code / Gemini CLI / Cursor / Codex 지원
- **CLI 병행**: CLI는 파워유저용으로 유지 (동일 생성 엔진 공유)
- 6개 레포: web, api, agent, infra, contracts, cli

## Repository Map
| Repo | Tech | Port | 역할 |
|------|------|------|------|
| `24SevenClaw-web` | Next.js 15 | 3000 | 웹 프론트엔드 (위저드 UI + 대시보드) |
| `24SevenClaw-api` | FastAPI | 8000 | 백엔드 API (카탈로그 + ZIP 생성) |
| `24SevenClaw-cli` | TypeScript (Node.js) | - | CLI 도구 (`@24sevenclaw/cli`) |
| `24SevenClaw-agent` | Python | - | 고객 서버 에이전트 데몬 |
| `24SevenClaw-infra` | Docker/YAML | - | 인프라 설정 |
| `24SevenClaw-contracts` | TypeScript | - | 공유 타입/프로토콜 |

## Development Rules
1. **모듈별 CLAUDE.md 참조**: 각 레포 디렉토리의 CLAUDE.md를 반드시 읽고 따를 것
2. **Contract 우선**: API 변경 시 contracts 레포의 스키마를 먼저 업데이트
3. **절대 경로 사용**: 모든 파일 참조는 절대 경로
4. **한국어 커밋/주석**: 커밋 메시지와 주석은 한국어로 작성
5. **Linear 티켓 기반**: 업무는 Linear 24Seven 팀 (24S-*) 티켓으로 추적

## Architecture Quick Reference
```
┌─────────────────────────────────────────────┐
│  Cloud (web + api)                          │
│  ├── PostgreSQL + Redis                     │
│  ├── 7-Step 위저드 (솔루션 설계)              │
│  ├── 카탈로그 (에이전트/스킬/플랫폼)           │
│  ├── ZIP 생성 엔진 (프리뷰 + 다운로드)        │
│  └── 라이센스 관리                            │
└──────────────┬──────────────────────────────┘
               │ ZIP 다운로드
               ▼
┌─────────────────────────────────────────────┐
│  사용자 로컬 PC                               │
│  ├── unzip → 프로젝트 디렉토리                 │
│  ├── .claude/ 또는 .gemini/ 또는 .cursor/     │
│  ├── .env (API 키)                           │
│  └── Agent 플랫폼 실행 (claude / gemini / etc)│
└─────────────────────────────────────────────┘
```

## Key Documents
- `LoadMap_v3.md` — 마스터 로드맵 (2주 스프린트, 7-Step 위저드)
- `TODO.md` — 일별 태스크
- `docs/architecture-overview.md` — 아키텍처 상세
- `docs/agent-protocol.md` — 통신 프로토콜
- `docs/cli-guide.md` — CLI 상세 가이드 (에이전트 카탈로그, 스택 프리셋)
- `docs/pipeline-guide.md` — 자동화 파이프라인 가이드 (v5 순차 실행)
- `docs/comparison.md` — 유사 플랫폼 비교
- `docs/license-model.md` — 라이센스 정책

## Module Agent Files
각 모듈 개발 시 해당 에이전트 파일을 참조:
- `.claude/agents/web-agent.md` — 프론트엔드 개발 가이드
- `.claude/agents/uiux-agent.md` — UI/UX 전담 에이전트 (Figma MCP 연동)
- `.claude/agents/api-agent.md` — 백엔드 API 개발 가이드
- `.claude/agents/agent-agent.md` — 고객 서버 에이전트 개발 가이드
- `.claude/agents/infra-agent.md` — 인프라/DevOps 가이드
- `.claude/agents/contracts-agent.md` — 공유 계약/프로토콜 가이드
- `.claude/agents/harness-guide.md` — 하네스 엔지니어링 전체 흐름 가이드

## UI/UX 작업 규칙
프론트엔드 UI 작업 시 반드시 UI/UX 에이전트(`uiux-agent.md`)를 참조한다.
- Figma MCP로 디자인 데이터 조회 → 코드 변환
- `/uiux` 스킬 + `design-checklist.md`로 품질 검증
- 접근성(WCAG AA), 반응형, 다크모드 필수

## PM Agent Pipeline (모델 라우팅 파이프라인)
Opus는 계획/설계에만, Sonnet은 구현에만 투입하여 토큰 비용을 최적화한다.
전체 가이드: `.claude/agents/pm-agent.md`, `.claude/agents/deep-thinker.md`

```
사용자 요청
  → [0. PM Agent / Opus] 세션 시작 & 복잡도 ≥ 0.7 시 호출 → 구현 스펙 생성
      → [deep-thinker / Opus] 복잡한 설계/트레이드오프 분석 (pm-agent가 위임)
  → 이후 Sonnet + Haiku로 구현 실행
```

| 에이전트 | 모델 | 호출 시점 |
|----------|------|----------|
| `pm-agent` | opus | 세션 시작, `--think` 플래그, 블로킹 이슈 |
| `deep-thinker` | opus | pm-agent가 복잡도 ≥ 0.7 감지 시 |

## Harness Engineering (하네스 엔지니어링)
AI 코드 작성을 5단계로 통제하여 환각/오류를 사전 차단하는 개발 워크플로.
전체 가이드: `.claude/agents/harness-guide.md`

```
사용자 요청
  → [0. PM Agent / Opus] 복잡도 판단 + 구현 스펙 (deep-thinker 서브에이전트 위임)
  → [1. Router / Sonnet] 의도 분석: 모호→되물어보기 / 명확→루프 / 대화→표준응답
  → [2. Context Manager / Haiku] 필요한 정보만 선별 제공 (가림막)
  → [3. Harness Loop / Sonnet] 코드작성→테스트→실패시 수정 반복 (MAX 5회)
  → [4. Worker] WRITE_CODE / TEST_WRITER / CODE_REVIEW / SECURITY_REVIEW 역할 분리
```

| 단계 | 스킬/에이전트 | 모델 | 기존 연동 |
|------|-------------|------|----------|
| PM | `pm-agent` + `deep-thinker` | **opus** | — (신규) |
| Router | `harness-router` | sonnet | — |
| Context | `harness-context` | haiku | `load-recent-changes.sh`, agents/*.md |
| Loop | `harness-loop` | sonnet | `ralph-loop`, `tdd-smart-coding`, `run-tests` |
| Worker | `harness-worker` | 역할별 | `fullstack`, `ai-critique`, `uiux` |

## Model Routing
에이전트/스킬별 최적 모델(opus/sonnet/haiku)을 지정하여 토큰 비용을 최적화한다.
- `.claude/MODEL-ROUTING.md` — 모델 라우팅 가이드 (티어 정의, 배정표, 격상/격하 규칙)

## Skills
- `.claude/skills/dev-skills.md` — 10개 개발 워크플로 스킬 + 4개 하네스 스킬
- `.claude/skills/` — 자동화 스킬 (run-pipeline, ralph-loop 등)

## Conventions
- **브랜치**: `feature/{module}/{description}`, `fix/{module}/{description}`
- **커밋**: `[module] 작업 내용` (예: `[api] 인증 엔드포인트 구현`)
- **PR**: 모듈별 독립 PR, cross-module 변경 시 contracts 먼저
- **테스트**: 새 기능은 반드시 테스트 동반, 커버리지 ≥70%
- **Linear**: 24Seven 팀, 티켓 상태 Wait → Queued → In Progress → Done
