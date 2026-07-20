# ClickEye - Development Guide

## Project Overview
AI 개발 자동화 솔루션 빌더 플랫폼.
- **Web-First 아키텍처**: 브라우저에서 12단계 위저드로 솔루션 설계 → ZIP 다운로드 → 로컬에서 AI 개발
- **멀티 Agent 플랫폼**: Claude Code / Gemini CLI / Cursor / Codex 지원
- **CLI 병행**: CLI는 파워유저용으로 유지 (동일 생성 엔진 공유)
- 6개 레포: web, api, agent, infra, contracts, cli

## Repository Map
| Repo | Tech | Port | 역할 |
|------|------|------|------|
| `clickeye-web` | Next.js 15 | 3000 | 웹 프론트엔드 (위저드 UI + 대시보드) |
| `clickeye-api` | FastAPI | 8000 | 백엔드 API (카탈로그 + ZIP 생성) |
| `clickeye-cli` | TypeScript (Node.js) | - | CLI 도구 (`@clickeye/cli`) |
| `clickeye-agent` | Python | - | 고객 서버 에이전트 데몬 |
| `clickeye-infra` | Docker/YAML | - | 인프라 설정 |
| `clickeye-contracts` | TypeScript | - | 공유 타입/프로토콜 |

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
│  ├── 12단계 위저드 (솔루션 설계)              │
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
- `docs/README.md` — **문서 매니페스트** (전체 docs/ 정식 레지스트리 + 정규화 프론트매터 규약). 새 문서는 반드시 여기 등재.
- `LoadMap_v3.md` — 마스터 로드맵 (2주 스프린트, 12단계 위저드)
- `TODO.md` — 일별 태스크
- `docs/architecture-overview.md` — 아키텍처 상세
- `docs/agent-protocol.md` — 통신 프로토콜
- `docs/cli-guide.md` — CLI 상세 가이드 (에이전트 카탈로그, 스택 프리셋)
- `docs/pipeline-guide.md` — 자동화 파이프라인 가이드 (v6 — 메타프롬프트 기획 + 거버넌스 게이트)
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

## Plan Gate (필수 워크플로)

이 프로젝트는 `Edit`/`Write` 도구 호출 전 `.claude/current-plan.md` 파일 존재와
사용자 승인 마커(`## STATUS: APPROVED`)를 PreToolUse hook으로 검증한다.

**코드 수정 작업 시작 시 반드시 아래 순서를 따를 것:**

1. `.claude/current-plan.md`를 작성 (목표 / 변경 파일 목록 / 구현 단계 / 예상 영향 범위)
2. 플랜을 사용자에게 보여주고 확인 대기
3. 사용자가 "승인" / "진행해" / "OK" 등으로 응답 → 파일 끝에 아래 줄 추가:
   ```
   ## STATUS: APPROVED
   ```
4. 이후 구현 시작

플랜 파일 형식:
```markdown
## 목표
(무엇을 구현하는지 1-2문장)

## 변경 파일 목록
- 파일경로: 변경 내용

## 구현 단계
1. 단계 1
2. 단계 2

## 예상 영향 범위
(다른 기능/모듈에 미치는 영향)

## STATUS: APPROVED   ← 사용자 승인 후 추가
```

작업 완료 또는 플랜 폐기 시 `.claude/current-plan.md`를 삭제하거나 새 작업용으로 덮어쓴다.

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

## Governance Gate (자동 워크플로우 머지 게이트)
자율 파이프라인이 main에 직접 머지(유일한 비보호 경로)하기 직전, 검증+위험분류를 단일 SSOT 모듈로 통과시킨다.
- `scripts/pre_merge_gate.py` — SSOT. `auto_dev_pipeline.sh`가 머지 직전 권위 호출 + `ci.yml` `governance` 잡이 PR 미러(동일 모듈, 중복 없음).
- **검증**: contract-drift(계약면↔openapi.json/generated 동반, 차단) · ticket-ref(브랜치 `ralph/<KEY>` 형태, 차단) · plan-trace(refined/PLAN 연관성, 권고).
- **위험강등**: HIGH(`clickeye-contracts/**`·`clickeye-infra/**`·`*auth*`·보안)는 `AUTO_MERGE=on`이어도 직접머지 금지 → 기존 PR 경로로 강등(새 승인장치 없음).
- **추적성**: 고복잡도 direct-merge 산출물을 cleanup 전 `logs/governance/<KEY>/`로 승격(재생성 없이).
- **토글**: `FLOWOPS_GOVERNANCE`(마스터, off면 회귀 0) + `_CONTRACT`/`_TICKET`/`_TRACE`/`_RISK_DEMOTE`/`_PROMOTE`. 상세: `docs/pipeline-guide.md` Step 5.5.

## Skills
- `.claude/skills/dev-skills.md` — 10개 개발 워크플로 스킬 + 4개 하네스 스킬 + metaprompt
- `.claude/skills/metaprompt/SKILL.md` — 관측형 사전 정제. 구현 전 거친 태스크를 구현 스펙으로 정제.
  자동 파이프라인(`auto_dev_pipeline.sh` STEP A, Gemini 기획 대체, 토글 `FLOWOPS_METAPROMPT`)과
  대화형 하네스(구현 스펙 생성)에서 공통 사용
- `.claude/skills/` — 자동화 스킬 (run-pipeline, ralph-loop 등)
- `.claude/skills/docs-sync/SKILL.md` — 코드 변경 후 `docs/` 현행화. 유의미 변경 후 자율 호출.

## Documentation Workflow (문서 지속 현행화)
문서는 최소 필수 세트로 유지하고 코드와 함께 현행화한다.
- **단일 레지스트리**: `docs/README.md` 매니페스트가 전체 `docs/` 정식 목록 + 정규화 프론트매터 규약(SSoT). 매니페스트에 없는 `docs/` 문서 = 아카이브 후보(자동 아카이브 `WeeklyWorkReport/`·`daily/` 제외).
- **정규화 포맷**: 모든 문서 상단 프론트매터(`title`/`category`/`status`/`last_updated`/`related`). 페이지 스펙은 `docs/pages/_template.md` 슈퍼셋. Marp 덱은 제외.
- **강제 갱신(훅)**: `PostToolUse(Edit|Write)` 훅 `.claude/hooks/docs-sync-reminder.sh`(순수 스크립트, **LLM 0토큰**)가 코드 편집마다 실행 → 편집 파일을 문서 `related`와 매칭해 영향 문서를 `status: needs-revision`으로 표시 + 리마인더. 실제 본문 현행화(LLM)는 리마인더를 보고 **커밋 전 `/docs-sync` 1회**(영향 문서·변경 구간만, 배치)로 수행 → `status: current` 복귀. 토글 `FLOWOPS_DOCS_SYNC=off`(회귀 0). 문서 작성/구조 변경은 `docs` 에이전트가 매니페스트·규약 준수.
- **신규 문서 최소화**: 신규 생성보다 기존 문서 갱신 우선. 새 문서는 매니페스트 등재 필수.

## Conventions
- **브랜치**: `{type}/{module}/{TICKET-KEY}-{description}` (Linear 키 병기 필수 — 거버넌스 ticket-ref 통과). 예: `feature/web/CE-302-delivery-console`, `fix/api/24S-142-auth-bug`. 게이트가 브랜치 어디서든 `^[A-Z0-9]+-\d+$` 키를 탐색하므로 서술적 이름과 병용 가능
- **커밋**: `[module] 작업 내용` (예: `[api] 인증 엔드포인트 구현`)
- **PR**: 모듈별 독립 PR, cross-module 변경 시 contracts 먼저
- **테스트**: 새 기능은 반드시 테스트 동반, 커버리지 ≥70%
- **Linear**: 24Seven 팀, 티켓 상태 Wait → Queued → In Progress → Done
