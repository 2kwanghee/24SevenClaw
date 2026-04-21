# @clickeye/cli

CLI-First AI 개발 자동화 플랫폼 — 하네스 엔지니어링이 탑재된 Claude Code 워크플로우를 한 줄 명령으로 구축합니다.

## 설치

```bash
# npx로 바로 실행 (설치 불필요)
npx @clickeye/cli init

# 또는 글로벌 설치
npm install -g @clickeye/cli
24sc init
```

**요구사항**: Node.js >= 18.0.0

## 빠른 시작

```bash
# 1. 새 프로젝트에서 AI 워크플로우 설정
npx @clickeye/cli init

# 2. 인터랙티브 위자드가 안내합니다
#    - 프로젝트 타입 선택 (웹앱, REST API, 풀스택, 커스텀)
#    - 기술 스택 선택 (FastAPI+Next.js, Django+React 등 6종)
#    - 에이전트 선택 (백엔드, 프론트엔드, UI/UX, DevOps 등)
#    - 워크플로우 선택 (TDD, AI 코드리뷰, Linear 연동 등)

# 3. 생성된 프로젝트에서 Claude Code 실행
cd my-project
claude
```

## 명령어

### `24sc init`

새 프로젝트에 AI 에이전트 워크플로우를 설정합니다.

```bash
24sc init              # 인터랙티브 모드
24sc init --yes        # 기본값으로 모든 질문 스킵
24sc init --dry-run    # 생성할 파일 목록만 미리 보기
```

**생성되는 구조:**

```
my-project/
├── .claude/
│   ├── agents/          # 에이전트 프로필 (.md)
│   ├── skills/          # 워크플로우 스킬 (.md)
│   └── settings.json    # Claude Code 설정
├── scripts/             # 자동화 스크립트
└── CLAUDE.md            # 프로젝트 가이드라인
```

### `24sc add <category> <id>`

기존 프로젝트에 에이전트, 스킬, Hook을 추가합니다.

```bash
# 에이전트 추가
24sc add agent frontend
24sc add agent devops

# 스킬 추가
24sc add skill tdd
24sc add skill ai-critique

# Hook 추가
24sc add hook harness-gate
```

### `24sc doctor`

현재 프로젝트의 ClickEye 설정 상태를 진단합니다.

```bash
24sc doctor
# ✅ .claude/ 디렉토리 존재
# ✅ CLAUDE.md 존재
# ✅ settings.json 유효
# ✅ Hook 스크립트 실행 권한 정상
# ✅ 에이전트 파일 참조 정상
# ✅ .env 파일 존재
```

## 에이전트 카탈로그

| ID | 이름 | 역할 |
|----|------|------|
| `backend` | Backend Engineer | API 설계, DB, 서버 로직 |
| `frontend` | Frontend Expert | 컴포넌트, 상태관리, 라우팅 |
| `uiux` | UI/UX Designer | 접근성, 반응형, 디자인 시스템 |
| `devops` | DevOps Engineer | Docker, CI/CD, 배포 |
| `fullstack` | Fullstack Senior | 백엔드+프론트 통합 |
| `harness` | Harness Engineer | 4단계 품질 게이트 (필수) |

## 스킬 카탈로그

| ID | 이름 | 설명 |
|----|------|------|
| `tdd` | TDD Smart Coding | 테스트 먼저 → 코드 → 리팩토링 |
| `ai-critique` | AI Code Review | 코딩 후 자동 리뷰 + 제안 |
| `linear` | Linear Sync | 이슈 기반 작업 추적 |
| `ralph-loop` | Ralph Autonomous Loop | fix_plan.md 기반 자율 개발 |
| `harness-gate` | Harness Gate | lint + typecheck + test 게이트키퍼 |

## 기술 스택 프리셋

| ID | 백엔드 | 프론트엔드 |
|----|--------|-----------|
| `fastapi-nextjs` | FastAPI + SQLAlchemy | Next.js 15 + Tailwind |
| `django-react` | Django + DRF | React + Vite |
| `express-vue` | Express + Prisma | Vue 3 + Vite |
| `nestjs-nextjs` | NestJS + TypeORM | Next.js 15 |
| `flask-react` | Flask + SQLAlchemy | React + Vite |
| `custom` | 사용자 정의 | 사용자 정의 |

## 하네스 엔지니어링

AI 코드 작성을 4단계로 통제하여 환각/오류를 사전 차단하는 품질 프레임워크입니다.

```
사용자 요청
  → [1. Router] 의도 분석 — 모호하면 되묻고, 명확하면 루프로
  → [2. Context] 필요한 정보만 선별 제공 (가림막)
  → [3. Loop] 코드 작성 → 테스트 → 실패 시 수정 (최대 5회)
  → [4. Worker] 코드 작성 / 테스트 / 리뷰 / 보안 역할 분리
```

## 라이선스

MIT
