# 24SevenClaw - Development Guide

## Project Overview
라이센스 기반 AI 에이전트 개발 오케스트레이션 플랫폼.
- Cloud(컨트롤 플레인) + Customer Server(실행 플레인) 아키텍처
- 5개 레포: web, api, agent, infra, contracts

## Repository Map
| Repo | Tech | Port | 역할 |
|------|------|------|------|
| `24SevenClaw-web` | Next.js 15 | 3000 | 클라우드 프론트엔드 |
| `24SevenClaw-api` | FastAPI | 8000 | 클라우드 백엔드 |
| `24SevenClaw-agent` | Python | - | 고객 서버 에이전트 데몬 |
| `24SevenClaw-infra` | Docker/YAML | - | 인프라 설정 |
| `24SevenClaw-contracts` | TypeScript | - | 공유 타입/프로토콜 |

## Development Rules
1. **모듈별 CLAUDE.md 참조**: 각 레포 디렉토리의 CLAUDE.md를 반드시 읽고 따를 것
2. **Contract 우선**: API 변경 시 contracts 레포의 스키마를 먼저 업데이트
3. **Agent↔Cloud 프로토콜**: `docs/agent-protocol.md` 참조
4. **절대 경로 사용**: 모든 파일 참조는 절대 경로
5. **한국어 커밋/주석**: 커밋 메시지와 주석은 한국어로 작성

## Architecture Quick Reference
```
Cloud (web + api) ←── WebSocket ──→ Agent (고객 서버)
      │                                    │
      ├── PostgreSQL + Redis               ├── Docker Engine
      ├── 레지스트리 (에이전트/스킬/MCP)      ├── Claude 인스턴스
      ├── 라이센스 관리                      ├── Git 저장소
      └── 티켓/이슈 관리                     └── 빌드/실행 환경
```

## Key Documents
- `PjPlan.md` — 전체 프로젝트 계획
- `TODO.md` — 일별 태스크
- `docs/architecture-overview.md` — 아키텍처 상세
- `docs/agent-protocol.md` — 통신 프로토콜
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

## Harness Engineering (하네스 엔지니어링)
AI 코드 작성을 4단계로 통제하여 환각/오류를 사전 차단하는 개발 워크플로.
전체 가이드: `.claude/agents/harness-guide.md`

```
사용자 요청
  → [1. Router] 의도 분석: 모호→되물어보기 / 명확→루프 / 대화→표준응답
  → [2. Context Manager] 필요한 정보만 선별 제공 (가림막)
  → [3. Harness Loop] 코드작성→테스트→실패시 수정 반복 (MAX 5회)
  → [4. Worker] WRITE_CODE / TEST_WRITER / CODE_REVIEW / SECURITY_REVIEW 역할 분리
```

| 단계 | 스킬 | 기존 연동 |
|------|------|----------|
| Router | `harness-router` | — (신규) |
| Context | `harness-context` | `load-recent-changes.sh`, agents/*.md |
| Loop | `harness-loop` | `ralph-loop`, `tdd-smart-coding`, `run-tests` |
| Worker | `harness-worker` | `fullstack`, `ai-critique`, `uiux` |

## Model Routing
에이전트/스킬별 최적 모델(opus/sonnet/haiku)을 지정하여 토큰 비용을 최적화한다.
- `.claude/MODEL-ROUTING.md` — 모델 라우팅 가이드 (티어 정의, 배정표, 격상/격하 규칙)

## Skills
- `.claude/skills/dev-skills.md` — 10개 개발 워크플로 스킬 + 4개 하네스 스킬
- `.claude/skills/` — flow-ops 자동화 스킬 13개 (run-pipeline, ralph-loop 등)

## Conventions
- **브랜치**: `feature/{module}/{description}`, `fix/{module}/{description}`
- **커밋**: `[module] 작업 내용` (예: `[api] 인증 엔드포인트 구현`)
- **PR**: 모듈별 독립 PR, cross-module 변경 시 contracts 먼저
- **테스트**: 새 기능은 반드시 테스트 동반, 커버리지 ≥70%
