# 24SevenClaw - Development Roadmap v4

> CLI-First AI 개발 자동화 플랫폼 — npm 패키지로 에이전트 구성 + 하네스 엔지니어링 자동 적용
> `npx @24sevenclaw/cli init` → 에이전트 고용 → .claude/ 생성 → Claude Code로 자동화 개발
> 로드맵 기간: 2026-04-07 ~ 2026-04-30 (4주)

---

## 서비스 비전 (v4 — CLI-First 하이브리드)

- **사용자**: `npx @24sevenclaw/cli init` → 대화형 위저드 → 에이전트 선택 → 로컬에 .claude/ 자동 생성
- **핵심 가치**: 하네스 엔지니어링이 탑재된 AI 개발 워크플로우를 한 줄 명령으로 구축
- **비용 모델**: Claude 토큰 = 사용자 부담 (BYOK), CLI 패키지 = 무료 (오픈소스)
- **라이센스**: CLI는 무료 공개, 프리미엄 에이전트/스킬은 향후 유료화
- **Phase 2 예고**: CLI에서 검증된 에이전트 카탈로그를 웹 마켓플레이스로 확장

### v3 → v4 전환 이유

| v3 (Cloud SaaS 중심) | v4 (CLI-First) |
|----------------------|----------------|
| 웹 + API + CLI 동시 개발 (5주) | CLI 패키지만 집중 (4주) |
| 인프라 비용 발생 (PostgreSQL, Redis) | 인프라 비용 0 |
| 웹 UI 온보딩 필수 | 터미널 한 줄로 시작 |
| 모니터링 대시보드 | 로컬 실행 (향후 웹 확장) |

---

## Tech Stack

- **CLI 패키지**: Node.js (TypeScript) — `@24sevenclaw/cli`
- **대화형 위저드**: inquirer / prompts
- **템플릿 엔진**: Handlebars (에이전트/스킬 파일 생성)
- **AI 엔진**: Claude Code CLI (사용자 BYOK)
- **패키지 관리**: npm (publish to npmjs.com)
- **테스트**: vitest
- **빌드**: tsup (TypeScript → JS 번들링)
- **기존 자산 재활용**: .claude/ (에이전트, 스킬, 훅), scripts/ (자동화)

---

## 서비스 플로우

```
[사용자 터미널]

$ npx @24sevenclaw/cli init
    │
    ├── Step 1: 프로젝트 기본 정보
    │     ├── 프로젝트 이름?       → my-saas-app
    │     ├── 프로젝트 유형?       → 웹앱 / REST API / 풀스택 / 커스텀
    │     └── 기술 스택?           → FastAPI+Next.js / Django+React / Express+Vue / ...
    │
    ├── Step 2: 에이전트 고용 (체크박스)
    │     ☑ 시니어 백엔드 엔지니어     → api-agent.md 생성
    │     ☑ 프론트엔드 전문가          → web-agent.md 생성
    │     ☐ DevOps 엔지니어           → infra-agent.md 생성
    │     ☑ UI/UX 디자이너            → uiux-agent.md 생성
    │     ☑ 하네스 엔지니어 (필수)     → harness-guide.md (항상 포함)
    │
    ├── Step 3: 워크플로우 옵션
    │     ☑ TDD (테스트 주도 개발)     → tdd-smart-coding 스킬
    │     ☑ AI 코드 리뷰              → ai-critique 스킬
    │     ☐ Linear 연동               → log-work, run-pipeline 스킬
    │     ☐ 자율 반복 루프 (Ralph)     → ralph-loop 스킬
    │     ☑ 하네스 Gate (커밋 차단)    → harness-gate.sh Hook
    │
    └── Step 4: 파일 생성 + 완료
          │
          v
    ┌─────────────────────────────────────────┐
    │  my-saas-app/.claude/                   │
    │    ├── agents/     (고용된 에이전트)      │
    │    ├── skills/     (선택한 워크플로우)     │
    │    ├── hooks/      (하네스 Gate)         │
    │    └── settings.json (권한 + Hook)       │
    │  my-saas-app/scripts/  (자동화 스크립트)  │
    │  my-saas-app/CLAUDE.md (프로젝트 규칙)    │
    │  my-saas-app/.env.example               │
    └─────────────────────────────────────────┘
          │
          v
    $ cd my-saas-app
    $ claude    ← Claude Code 실행, 하네스 자동 적용
```

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│  @24sevenclaw/cli (npm 패키지)                           │
│                                                         │
│  src/                                                   │
│    ├── cli.ts           # 진입점 (Commander.js)          │
│    ├── commands/                                        │
│    │   ├── init.ts      # init 명령어 (메인 위저드)      │
│    │   ├── add.ts       # 에이전트/스킬 추가             │
│    │   └── doctor.ts    # 설정 검증                      │
│    ├── wizard/                                          │
│    │   ├── project.ts   # Step 1: 프로젝트 정보          │
│    │   ├── agents.ts    # Step 2: 에이전트 선택           │
│    │   └── workflow.ts  # Step 3: 워크플로우 옵션         │
│    ├── generators/                                      │
│    │   ├── agent.ts     # 에이전트 .md 파일 생성          │
│    │   ├── skill.ts     # 스킬 SKILL.md 생성             │
│    │   ├── hook.ts      # Hook .sh 생성                  │
│    │   └── settings.ts  # settings.json 생성             │
│    ├── catalog/                                         │
│    │   ├── agents.json  # 에이전트 카탈로그               │
│    │   ├── skills.json  # 스킬 카탈로그                   │
│    │   └── stacks.json  # 기술 스택 프리셋                │
│    └── templates/       # Handlebars 템플릿               │
│        ├── agents/      # 에이전트 .md 템플릿              │
│        ├── skills/      # 스킬 SKILL.md 템플릿            │
│        ├── hooks/       # Hook .sh 템플릿                 │
│        └── claude.md.hbs # CLAUDE.md 템플릿               │
│                                                         │
│  bin/cli.js             # npx 진입점                     │
│  package.json           # "bin": { "24sc": "./bin/cli.js" }
└─────────────────────────────────────────────────────────┘
```

---

## 에이전트 카탈로그

CLI가 제공하는 에이전트 목록. 사용자가 선택하면 해당 .md 파일이 생성된다.

| ID | 에이전트 | 설명 | 생성 파일 |
|----|---------|------|----------|
| `backend` | 시니어 백엔드 엔지니어 | API 설계, DB, 서버 로직 | `api-agent.md` |
| `frontend` | 프론트엔드 전문가 | 컴포넌트, 상태관리, 라우팅 | `web-agent.md` |
| `uiux` | UI/UX 디자이너 | 접근성, 반응형, 디자인 시스템 | `uiux-agent.md` |
| `devops` | DevOps 엔지니어 | Docker, CI/CD, 배포 | `infra-agent.md` |
| `fullstack` | 풀스택 시니어 | 백엔드+프론트 통합 | `fullstack/SKILL.md` |
| `harness` | 하네스 엔지니어 (필수) | 4단계 품질 통제 | `harness-guide.md` + 4 스킬 |

### 기술 스택 프리셋

에이전트 템플릿은 선택한 스택에 맞게 커스터마이징된다.

| 프리셋 | 백엔드 | 프론트엔드 | 테스트 | 린트 |
|--------|--------|-----------|--------|------|
| `fastapi-nextjs` | FastAPI + SQLAlchemy | Next.js 15 + Tailwind | pytest + vitest | ruff + ESLint |
| `django-react` | Django + DRF | React + Vite | pytest + vitest | ruff + ESLint |
| `express-vue` | Express + Prisma | Vue 3 + Vite | jest + vitest | eslint | 
| `nestjs-nextjs` | NestJS + TypeORM | Next.js 15 | jest + vitest | eslint |
| `flask-react` | Flask + SQLAlchemy | React + Vite | pytest + vitest | ruff + ESLint |
| `custom` | 사용자 직접 입력 | 사용자 직접 입력 | 사용자 직접 입력 | 사용자 직접 입력 |

---

## Phase 0: 기존 자산 — ✅ 완료

기존 24SevenClaw에서 재활용하는 자산:

- [x] 하네스 엔지니어링 4단계 스킬 (harness-router/context/loop/worker)
- [x] harness-gate.sh Hook (커밋 전 Gate 강제)
- [x] 에이전트 가이드 10개 (api, web, uiux, infra, contracts, ...)
- [x] 개발 워크플로우 스킬 15개 (tdd, ralph-loop, ai-critique, ...)
- [x] 자동화 스크립트 20개 (linear_tracker, telegram_notify, ...)
- [x] settings.json Hook 구조 (UserPromptSubmit, PreToolUse, PostToolUse, Stop)
- [x] WorkflowAutomation 범용 템플릿 프로젝트

---

## Phase 1: Week 1 — CLI 패키지 스캐폴딩 + 핵심 엔진 (04-07 ~ 04-13)

### 목표
CLI 패키지 초기화 + `24sc init` 명령어의 기본 위저드 + 파일 생성 엔진

### CLI 패키지 초기화

- [x] `24SevenClaw-cli/` 레포 생성 (TypeScript + tsup + vitest)
- [x] `package.json` 설정 (`name: @24sevenclaw/cli`, `bin: { "24sc": "./bin/cli.js" }`)
- [x] `tsconfig.json` + `tsup.config.ts` (빌드 설정)
- [x] Commander.js 기반 CLI 진입점 (`src/cli.ts`)
- [x] `bin/cli.js` (shebang + dist 연결)

### 대화형 위저드 (Step 1~2)

- [x] `src/commands/init.ts` — init 명령어 메인 로직
- [x] `src/wizard/project.ts` — Step 1: 프로젝트 이름, 유형, 기술 스택 선택
- [x] `src/wizard/agents.ts` — Step 2: 에이전트 고용 (체크박스 선택)
- [x] `src/catalog/agents.json` — 에이전트 카탈로그 (id, name, description, template)
- [x] `src/catalog/stacks.json` — 기술 스택 프리셋 (lint/test/type 명령어 매핑)

### 파일 생성 엔진

- [x] `src/generators/agent.ts` — 에이전트 .md 파일 생성 (템플릿 → 출력)
- [x] `src/generators/settings.ts` — settings.json 생성 (선택한 옵션 반영)
- [x] `src/generators/claude-md.ts` — CLAUDE.md 생성 (프로젝트 정보 삽입)
- [x] `src/templates/agents/` — 에이전트 Handlebars 템플릿 (기존 .md를 템플릿화)
- [x] `src/templates/claude.md.hbs` — CLAUDE.md 템플릿

### 테스트

- [x] `tests/wizard.test.ts` — 위저드 입력 → 옵션 객체 생성 검증
- [x] `tests/generators.test.ts` — 파일 생성기 유닛 테스트
- [ ] 로컬 실행 테스트: `npx tsx src/cli.ts init` → 파일 생성 확인

---

## Phase 1: Week 2 — 스킬/Hook 생성 + 하네스 통합 (04-14 ~ 04-20)

### 목표
워크플로우 옵션 선택 + 스킬/Hook/스크립트 생성 + 하네스 엔지니어링 자동 적용

### 대화형 위저드 (Step 3)

- [ ] `src/wizard/workflow.ts` — Step 3: 워크플로우 옵션 선택
  - TDD, AI 코드 리뷰, Linear 연동, Ralph 자율 루프, 하네스 Gate
- [ ] 옵션에 따른 스킬/Hook 매핑 로직

### 스킬 생성 엔진

- [ ] `src/generators/skill.ts` — 스킬 SKILL.md 생성
- [ ] `src/generators/hook.ts` — Hook .sh 생성 (harness-gate.sh 커스터마이징)
- [ ] `src/generators/scripts.ts` — scripts/ 자동화 스크립트 생성 (선택한 옵션만)
- [ ] `src/catalog/skills.json` — 스킬 카탈로그 (id, name, dependencies, template)
- [ ] `src/templates/skills/` — 스킬 Handlebars 템플릿
- [ ] `src/templates/hooks/` — Hook 템플릿 (harness-gate.sh.hbs)

### 하네스 엔지니어링 자동 통합

- [ ] harness-guide.md 항상 포함 (선택 불가, 기본 탑재)
- [ ] harness-gate.sh → 선택한 기술 스택의 lint/test 명령어로 자동 설정
- [ ] settings.json → UserPromptSubmit/PreToolUse/PostToolUse Hook 자동 등록
- [ ] 기술 스택별 Gate 명령어 매핑:
  ```
  fastapi-nextjs → ruff + mypy + pytest / eslint + tsc + vitest
  django-react   → ruff + mypy + pytest / eslint + tsc + vitest
  express-vue    → eslint + tsc + jest / eslint + tsc + vitest
  ```

### 테스트

- [ ] `tests/skill-generator.test.ts` — 스킬 생성 유닛 테스트
- [ ] `tests/hook-generator.test.ts` — Hook 생성 + Gate 명령어 검증
- [ ] `tests/integration.test.ts` — 전체 init 플로우 E2E (tmp 디렉토리 생성 → 검증 → 삭제)

---

## Phase 1: Week 3 — add 명령어 + doctor + 폴리싱 (04-21 ~ 04-27)

### 목표
에이전트/스킬 추가 명령어 + 설정 검증 + CLI UX 폴리싱

### add 명령어

- [ ] `src/commands/add.ts` — 기존 프로젝트에 에이전트/스킬 추가
  - `24sc add agent backend` → api-agent.md 추가
  - `24sc add skill tdd` → tdd-smart-coding 스킬 추가
  - `24sc add hook harness-gate` → Hook 추가
- [ ] 기존 설정과 충돌 감지 (이미 있으면 덮어쓸지 확인)
- [ ] settings.json 자동 업데이트 (Hook/권한 추가)

### doctor 명령어

- [ ] `src/commands/doctor.ts` — 설정 상태 검증
  - .claude/ 디렉토리 존재 여부
  - settings.json 유효성 (JSON 파싱 + 필수 필드)
  - Hook 스크립트 실행 권한 확인
  - 에이전트 파일 참조 무결성 (CLAUDE.md에 나열된 파일 존재 확인)
  - .env 필수 변수 확인 (선택한 옵션에 따라)
- [ ] 결과를 ✅/❌ 체크리스트로 출력

### CLI UX 폴리싱

- [ ] 컬러 출력 (chalk 라이브러리)
- [ ] 진행 스피너 (ora 라이브러리)
- [ ] 에러 메시지 한국어 + 해결 가이드
- [ ] `--yes` 플래그 (기본값으로 모든 질문 스킵)
- [ ] `--dry-run` 플래그 (생성할 파일 목록만 출력, 실제 생성 안 함)
- [ ] `24sc --help` + `24sc init --help` 도움말

### 테스트

- [ ] `tests/add.test.ts` — add 명령어 테스트
- [ ] `tests/doctor.test.ts` — doctor 검증 테스트
- [ ] `tests/e2e.test.ts` — 전체 시나리오 E2E

---

## Phase 1: Week 4 — npm 배포 + 문서 + 최종 검증 (04-28 ~ 04-30)

### 목표
npm publish + README + 실사용 테스트

### npm 배포 준비

- [ ] `npm login` (npmjs.com 계정)
- [ ] `package.json` 최종 정리 (version, description, keywords, repository)
- [ ] `tsup` 빌드 검증 (`npm run build`)
- [ ] `.npmignore` 또는 `files` 필드 (불필요한 파일 제외)
- [ ] `npm pack` → 로컬 테스트 (`npx ./24sevenclaw-cli-0.1.0.tgz init`)
- [ ] `npm publish --access public` (첫 배포)

### 문서

- [ ] `24SevenClaw-cli/README.md` — 설치 가이드 + 사용법 + 스크린샷
- [ ] `24SevenClaw-cli/CHANGELOG.md` — v0.1.0 릴리즈 노트
- [ ] `docs/cli-guide.md` — CLI 상세 가이드 (에이전트 카탈로그, 스택 프리셋 목록)

### 실사용 테스트

- [ ] 빈 디렉토리에서 `npx @24sevenclaw/cli init` → 전체 플로우 검증
- [ ] 생성된 .claude/로 Claude Code 실행 → 하네스 작동 확인
- [ ] harness-gate.sh → 실제 lint/test 실패 시 커밋 차단 확인
- [ ] 다른 기술 스택 (Django+React)으로 테스트
- [ ] Windows/Mac/Linux 호환성 확인

### 기존 레포 정리

- [ ] CLAUDE.md 갱신: CLI-First 아키텍처 반영
- [ ] LoadMap.md 상태 업데이트: Phase 1 완료 체크

---

## Phase 2 예고 (5월 이후 — 웹 마켓플레이스 확장)

> Phase 1에서 CLI가 검증되면, 기존 24SevenClaw web/api 코드를 활용하여 웹으로 확장

- 에이전트 마켓플레이스 웹 UI (기존 Next.js 활용)
- 커뮤니티 에이전트 업로드/공유
- 프로젝트 모니터링 대시보드
- 라이센스 관리 (프리미엄 에이전트)
- CLI가 웹에서 생성한 설정을 다운로드하는 클라이언트로 확장

---

## 핵심 원칙

1. **CLI-First**: 웹 없이 CLI만으로 완전한 경험 제공
2. **하네스 필수**: 모든 프로젝트에 하네스 엔지니어링 기본 탑재
3. **템플릿 기반**: 에이전트/스킬은 Handlebars 템플릿으로 관리
4. **기존 자산 재활용**: Phase 0에서 만든 .claude/ 구조를 템플릿으로 변환
5. **프리셋 + 커스텀**: 일반적인 스택은 프리셋 제공, 특수 스택은 커스텀 입력
6. **점진적 확장**: CLI MVP → 검증 → 웹 마켓플레이스

---

## 계획 변경 이력

| 변경일 | 변경 내용 | 사유 |
|--------|----------|------|
| 2026-03-31 | 서비스 피벗: 고객 서버 에이전트 중심 → 클라우드 SaaS 중심 | paperclip.ing 참고, 서비스 방향 전환 |
| 2026-03-31 | PjPlan.md → docs/archive/PjPlan_v1.md 백업, LoadMap.md 생성 | 신규 로드맵 수립 |
| 2026-04-01 | LoadMap v2: 4주 → 5주 확장, 설계 갭 보완 | Codex adversarial review 기반 재설계 |
| 2026-04-01 | ADR 5개 추가 | 아키텍처 결정 문서화 |
| 2026-04-02 | v2 → v3: Agent 데몬 → CLI 패키지 | 비용 구조 현실화 (BYOK + 로컬 실행) |
| 2026-04-02 | 하네스 엔지니어링 4단계 도입 | AI 코드 품질 통제 (Router→Context→Loop→Worker) |
| 2026-04-02 | v3 → v4: Cloud SaaS 중심 → CLI-First 하이브리드 | MVP 속도 우선, 인프라 비용 0, 개발자 친화적 |
| 2026-04-02 | 로드맵 기간 변경: 5주 → 4주 (04-07 ~ 04-30) | CLI 패키지 집중으로 범위 축소 |
| 2026-04-02 | 기존 web/api/agent 레포 → Phase 2로 이연 | Phase 1은 CLI 패키지 1개에 집중 |

---

## 참조 문서

- `docs/archive/PjPlan_v1.md` — 이전 프로젝트 계획 v1
- `docs/architecture-overview.md` — 아키텍처 (Phase 2에서 갱신 예정)
- `.claude/agents/harness-guide.md` — 하네스 엔지니어링 가이드
- `.claude/skills/dev-skills.md` — 개발 스킬 레지스트리
