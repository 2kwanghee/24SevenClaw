# CLI 상세 가이드

> `@clickeye/cli` v0.1.0 — 하네스 엔지니어링이 탑재된 Claude Code 워크플로우 CLI

## 개요

ClickEye CLI는 AI 에이전트 개발 환경을 한 줄 명령으로 구축하는 도구입니다.
프로젝트 타입과 기술 스택에 맞는 `.claude/` 설정을 자동 생성하며,
하네스 엔지니어링 품질 게이트를 기본 탑재합니다.

## 설치

```bash
# npx (설치 불필요)
npx @clickeye/cli init

# 글로벌 설치
npm install -g @clickeye/cli
```

**요구사항**: Node.js >= 18.0.0

---

## 명령어 상세

### `24sc init`

새 프로젝트에 AI 에이전트 워크플로우를 설정합니다.

#### 옵션

| 옵션 | 설명 |
|------|------|
| `--yes` | 모든 질문을 기본값으로 스킵 |
| `--dry-run` | 생성할 파일 목록만 출력 (실제 생성 안 함) |

#### 인터랙티브 위자드 플로우

**Step 1 — 프로젝트 정보**
- 프로젝트 이름 (기본: 현재 디렉토리명)
- 프로젝트 타입: `webapp` | `rest-api` | `fullstack` | `custom`
- 기술 스택 프리셋 선택

**Step 2 — 에이전트 선택**
- 체크리스트에서 필요한 에이전트 선택
- Harness Engineer는 필수 (자동 포함)

**Step 3 — 워크플로우 선택**
- TDD, AI 코드리뷰, Linear 연동, Ralph Loop, 하네스 게이트 중 선택

#### 생성 파일 구조

```
<project>/
├── .claude/
│   ├── agents/
│   │   ├── api-agent.md          # 백엔드 에이전트 (선택 시)
│   │   ├── web-agent.md          # 프론트엔드 에이전트 (선택 시)
│   │   ├── uiux-agent.md         # UI/UX 에이전트 (선택 시)
│   │   ├── infra-agent.md        # DevOps 에이전트 (선택 시)
│   │   ├── fullstack-agent.md    # 풀스택 에이전트 (선택 시)
│   │   └── harness-guide.md      # 하네스 가이드 (필수)
│   ├── skills/
│   │   ├── tdd-smart-coding.md   # TDD 스킬 (선택 시)
│   │   ├── ai-critique.md        # AI 리뷰 스킬 (선택 시)
│   │   ├── linear-sync.md        # Linear 연동 (선택 시)
│   │   ├── ralph-loop.md         # Ralph Loop (선택 시)
│   │   └── harness-gate.md       # 하네스 게이트 (선택 시)
│   └── settings.json             # Claude Code 설정 (hooks, permissions)
├── scripts/
│   ├── harness-gate.sh           # 품질 게이트 스크립트
│   └── run-tests.sh              # 테스트 실행 스크립트
└── CLAUDE.md                     # 프로젝트 가이드라인 (AI가 읽는 문서)
```

---

### `24sc add <category> <id>`

기존 프로젝트에 에이전트, 스킬, Hook을 추가합니다.

#### 사용법

```bash
24sc add agent <id>     # 에이전트 추가
24sc add skill <id>     # 스킬 추가
24sc add hook <id>      # Hook 추가
```

#### 옵션

| 옵션 | 설명 |
|------|------|
| `--yes` | 확인 질문 없이 덮어쓰기 |
| `--dry-run` | 생성할 파일 목록만 출력 |
| `--stack <preset>` | 기술 스택 프리셋 지정 |

#### 예시

```bash
# 프론트엔드 에이전트 추가
24sc add agent frontend

# TDD 워크플로우 추가 (hooks도 자동 등록)
24sc add skill tdd

# 하네스 게이트 Hook만 추가
24sc add hook harness-gate
```

**동작 방식**:
1. 현재 프로젝트의 CLAUDE.md에서 기술 스택을 자동 감지
2. 해당 카탈로그 항목의 Handlebars 템플릿을 렌더링
3. 파일 충돌 시 덮어쓸지 사용자에게 확인 (`--yes`로 스킵 가능)
4. 스킬 추가 시 연관 Hook을 settings.json에 자동 등록

---

### `24sc doctor`

현재 프로젝트의 ClickEye 설정 상태를 진단합니다.

#### 진단 항목

| # | 체크 항목 | 설명 |
|---|----------|------|
| 1 | `.claude/` 디렉토리 | 설정 디렉토리 존재 여부 |
| 2 | `CLAUDE.md` | 프로젝트 가이드라인 존재 여부 |
| 3 | `settings.json` | JSON 유효성 + permissions/hooks 필드 검증 |
| 4 | Hook 스크립트 권한 | .sh 파일의 실행 권한 (chmod +x) |
| 5 | 에이전트 파일 참조 | CLAUDE.md에서 참조하는 에이전트 파일 존재 여부 |
| 6 | `.env` 파일 | 환경변수 파일 존재 여부 (.env.example 대체 가능) |

#### 출력 예시

```
🔍 ClickEye 설정 진단 중...

✅ .claude/ 디렉토리 존재
✅ CLAUDE.md 존재
✅ settings.json 유효 (permissions: 3, hooks: 2)
❌ Hook 스크립트 실행 권한 없음 → chmod +x scripts/harness-gate.sh
✅ 에이전트 파일 참조 정상 (3/3)
⚠️  .env 없음 → .env.example을 복사하세요

결과: 4/6 통과
```

---

## 에이전트 카탈로그

### backend — Backend Engineer
- **역할**: API 설계, 데이터베이스, 서버 로직
- **출력 파일**: `.claude/agents/api-agent.md`
- **적합한 프로젝트**: REST API, 풀스택

### frontend — Frontend Expert
- **역할**: 컴포넌트, 상태관리, 라우팅
- **출력 파일**: `.claude/agents/web-agent.md`
- **적합한 프로젝트**: 웹앱, 풀스택

### uiux — UI/UX Designer
- **역할**: 접근성(WCAG AA), 반응형, 디자인 시스템
- **출력 파일**: `.claude/agents/uiux-agent.md`
- **적합한 프로젝트**: 디자인 중심 프로젝트

### devops — DevOps Engineer
- **역할**: Docker, CI/CD, 배포 자동화
- **출력 파일**: `.claude/agents/infra-agent.md`
- **적합한 프로젝트**: 인프라 설정이 필요한 프로젝트

### fullstack — Fullstack Senior
- **역할**: 백엔드+프론트엔드 통합 개발
- **출력 파일**: `.claude/agents/fullstack-agent.md`
- **적합한 프로젝트**: 풀스택

### harness — Harness Engineer (필수)
- **역할**: 4단계 품질 게이트 (Router → Context → Loop → Worker)
- **출력 파일**: `.claude/agents/harness-guide.md`
- **모든 프로젝트에 자동 포함**

---

## 스킬 카탈로그

### tdd — TDD Smart Coding
- **워크플로우**: 테스트 먼저 → 코드 작성 → 리팩토링
- **출력 파일**: `.claude/skills/tdd-smart-coding.md`
- **연관 Hook**: 없음

### ai-critique — AI Code Review
- **워크플로우**: 코딩 후 자동 리뷰 + 개선 제안
- **출력 파일**: `.claude/skills/ai-critique.md`
- **연관 Hook**: 없음

### linear — Linear Sync
- **워크플로우**: Linear 이슈 기반 작업 추적 + 상태 동기화
- **출력 파일**: `.claude/skills/linear-sync.md`
- **연관 Hook**: 없음

### ralph-loop — Ralph Autonomous Loop
- **워크플로우**: `fix_plan.md` 기반 자율 개발 루프
- **출력 파일**: `.claude/skills/ralph-loop.md`
- **연관 Hook**: 없음

### harness-gate — Harness Gate
- **워크플로우**: lint + typecheck + test 게이트키퍼
- **출력 파일**: `.claude/skills/harness-gate.md`
- **연관 Hook**: `scripts/harness-gate.sh` → `UserPromptSubmit` 이벤트

---

## 기술 스택 프리셋

각 프리셋은 테스트, 린트, 타입체크 명령어가 사전 정의되어 있습니다.

### fastapi-nextjs
| 구분 | 스택 |
|------|------|
| 백엔드 | FastAPI + SQLAlchemy |
| 프론트 | Next.js 15 + Tailwind |
| 테스트 | `pytest` / `vitest` |
| 린트 | `ruff check` / `eslint` |

### django-react
| 구분 | 스택 |
|------|------|
| 백엔드 | Django + DRF |
| 프론트 | React + Vite |
| 테스트 | `pytest-django` / `vitest` |
| 린트 | `ruff check` / `eslint` |

### express-vue
| 구분 | 스택 |
|------|------|
| 백엔드 | Express + Prisma |
| 프론트 | Vue 3 + Vite |
| 테스트 | `jest` / `vitest` |
| 린트 | `eslint` / `eslint` |

### nestjs-nextjs
| 구분 | 스택 |
|------|------|
| 백엔드 | NestJS + TypeORM |
| 프론트 | Next.js 15 |
| 테스트 | `jest` / `vitest` |
| 린트 | `eslint` / `eslint` |

### flask-react
| 구분 | 스택 |
|------|------|
| 백엔드 | Flask + SQLAlchemy |
| 프론트 | React + Vite |
| 테스트 | `pytest` / `vitest` |
| 린트 | `ruff check` / `eslint` |

### custom
사용자가 직접 백엔드/프론트엔드 기술과 명령어를 지정합니다.

---

## 하네스 엔지니어링

AI 코드 작성을 4단계로 통제하여 환각/오류를 사전 차단합니다.

```
사용자 요청
  ↓
[1. Router]     의도 분석 — 모호하면 되묻기, 명확하면 루프로
  ↓
[2. Context]    필요한 정보만 AI에게 선별 제공 (가림막)
  ↓
[3. Loop]       코드 작성 → 테스트 → 실패 시 수정 (최대 5회)
  ↓
[4. Worker]     역할 분리: WRITE_CODE / TEST_WRITER / CODE_REVIEW / SECURITY_REVIEW
```

### harness-gate.sh

`UserPromptSubmit` Hook으로 등록되어, AI가 코드를 제출할 때마다 자동 실행됩니다.

**검증 순서**:
1. `lint` — 코드 스타일 + 정적 분석
2. `typecheck` — 타입 안전성 검증
3. `test` — 단위/통합 테스트 실행

세 단계 모두 통과해야 커밋이 허용됩니다.

---

## 확장

### 커스텀 에이전트 추가

`src/catalog/agents.json`에 항목을 추가하고, `src/templates/agents/`에 Handlebars 템플릿을 작성합니다.

```json
{
  "id": "my-agent",
  "name": "My Custom Agent",
  "description": "커스텀 에이전트 설명",
  "outputFile": ".claude/agents/my-agent.md",
  "template": "agents/my-agent.md.hbs"
}
```

### 커스텀 스킬 추가

`src/catalog/skills.json`에 항목을 추가하고, `src/templates/skills/`에 템플릿을 작성합니다.

```json
{
  "id": "my-skill",
  "name": "My Custom Skill",
  "description": "커스텀 스킬 설명",
  "template": "skills/my-skill.md.hbs",
  "outputFile": ".claude/skills/my-skill.md",
  "dependencies": [],
  "hooks": []
}
```
