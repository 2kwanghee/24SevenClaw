# 24SevenClaw - Development Roadmap v5

> Web-First AI 개발 자동화 플랫폼 — 브라우저에서 에이전트 구성 → ZIP 다운로드 → Claude Code 즉시 사용
> CLI 자산(템플릿, 카탈로그, 생성 로직)을 웹 서비스로 전환하여 진입 장벽 제거
> 로드맵 기간: 2026-04-07 ~ 2026-05-04 (4주)

---

## 서비스 비전 (v5 — Web-First)

- **사용자**: 브라우저 접속 → 프로젝트 설정 → 에이전트/스킬 선택 → ZIP 다운로드 → `unzip` → `claude`
- **핵심 가치**: 터미널/Node.js 없이도 하네스 엔지니어링이 탑재된 AI 워크플로우를 구축
- **비용 모델**: Claude 토큰 = 사용자 부담 (BYOK), 웹 서비스 = 무료
- **라이센스**: 기본 에이전트/스킬 무료, 프리미엄 에이전트는 향후 유료화
- **CLI 유지**: CLI는 파워유저용으로 병행 유지 (동일한 생성 엔진 공유)

### v4 → v5 전환 이유

| v4 (CLI-First) | v5 (Web-First) |
|----------------|----------------|
| npm/Node.js 필수 | 브라우저만 있으면 됨 |
| 터미널 익숙한 개발자만 사용 | PM, 주니어, 비개발자도 접근 가능 |
| npx 실행 시 npm publish 필요 | 배포 즉시 사용 가능 |
| 텍스트 기반 선택 UI | 시각적 카드 UI + 실시간 프리뷰 |
| 로컬에서만 결과 확인 | 생성될 파일 트리를 브라우저에서 미리보기 |

### CLI 자산 재활용

현재 CLI에 구현된 모든 것을 웹에서 재사용:

| CLI 자산 | 웹 전환 방식 |
|----------|-------------|
| `catalog/agents.json` | API에서 에이전트 목록 제공 |
| `catalog/skills.json` | API에서 스킬 목록 제공 |
| `catalog/stacks.json` | API에서 스택 프리셋 제공 |
| `templates/**/*.hbs` | 서버사이드 Handlebars 렌더링 |
| `generators/*.ts` | API 핸들러에서 호출 |
| `wizard/*.ts` (입력 로직) | 웹 폼 UI로 대체 |

---

## Tech Stack

### Frontend (Next.js 15)
- **프레임워크**: Next.js 15 (App Router)
- **스타일**: Tailwind CSS + shadcn/ui
- **상태관리**: React Hook Form (폼 상태) + Zustand (전역 상태)
- **파일 트리 프리뷰**: 커스텀 트리 컴포넌트
- **다운로드**: JSZip (클라이언트 사이드 ZIP 생성) 또는 서버 ZIP 스트림

### Backend (FastAPI)
- **프레임워크**: FastAPI
- **템플릿 엔진**: Jinja2 (Handlebars .hbs → Jinja2 .j2 변환) 또는 Node.js 사이드카
- **ZIP 생성**: Python zipfile 모듈
- **카탈로그 관리**: JSON 파일 기반 (DB 불필요)
- **CORS**: 프론트엔드 도메인 허용

### 인프라
- **배포**: Vercel (프론트) + Railway/Fly.io (백엔드)
- **DB**: 없음 (상태 비저장, 카탈로그는 JSON 파일)
- **비용**: 거의 0 (무상태 서비스)

### 대안: 풀 Next.js (API Routes)
> 백엔드를 FastAPI 대신 Next.js API Routes로 통합하면 배포가 Vercel 하나로 단순화됨.
> 템플릿 엔진도 Handlebars를 그대로 사용 가능 (Node.js 런타임).
> **추천: Phase 1은 Next.js 단일 스택으로 시작, 복잡해지면 FastAPI 분리.**

---

## 서비스 플로우

```
[브라우저]

사용자 → 24sevenclaw.dev 접속
    │
    ├── Step 1: 프로젝트 기본 정보 (폼)
    │     ├── 프로젝트 이름         → my-saas-app
    │     ├── 프로젝트 유형         → 웹앱 / REST API / 풀스택 / 커스텀
    │     └── 기술 스택 선택        → FastAPI+Next.js / Django+React / ...
    │
    ├── Step 2: 에이전트 고용 (카드 UI)
    │     ☑ 시니어 백엔드 엔지니어     💡 설명 + 생성 파일 미리보기
    │     ☑ 프론트엔드 전문가          💡 설명 + 생성 파일 미리보기
    │     ☐ DevOps 엔지니어
    │     ☑ UI/UX 디자이너
    │     ☑ 하네스 엔지니어 (필수)     🔒 항상 포함
    │
    ├── Step 3: 워크플로우 옵션 (토글 UI)
    │     ☑ TDD (테스트 주도 개발)
    │     ☑ AI 코드 리뷰
    │     ☐ Linear 연동
    │     ☐ 자율 반복 루프 (Ralph)
    │     ☑ 하네스 Gate (커밋 차단)
    │
    ├── Step 4: 프리뷰 + 다운로드
    │     │
    │     ├── [왼쪽] 파일 트리 프리뷰
    │     │     my-saas-app/
    │     │       ├── CLAUDE.md          ← 클릭하면 내용 미리보기
    │     │       ├── .claude/
    │     │       │   ├── agents/
    │     │       │   ├── skills/
    │     │       │   └── settings.json
    │     │       └── scripts/
    │     │
    │     └── [오른쪽] 파일 내용 미리보기 (선택한 파일)
    │
    └── [다운로드 버튼] → my-saas-app.zip
          │
          v
    $ unzip my-saas-app.zip
    $ cd my-saas-app
    $ claude    ← Claude Code 실행, 하네스 자동 적용
```

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15 — Vercel)                             │
│                                                             │
│  app/                                                       │
│    ├── page.tsx              # 랜딩 페이지 (히어로 + CTA)    │
│    ├── generate/                                            │
│    │   ├── page.tsx          # 메인: 4-Step 위저드 폼        │
│    │   └── components/                                      │
│    │       ├── ProjectForm.tsx    # Step 1: 프로젝트 정보    │
│    │       ├── AgentSelector.tsx  # Step 2: 에이전트 카드    │
│    │       ├── WorkflowToggle.tsx # Step 3: 워크플로우 토글  │
│    │       ├── FileTreePreview.tsx # Step 4: 트리 프리뷰     │
│    │       ├── FileContentViewer.tsx # 파일 내용 미리보기    │
│    │       └── DownloadButton.tsx  # ZIP 다운로드 버튼       │
│    └── api/                                                 │
│        ├── catalog/route.ts   # GET: 에이전트/스킬/스택 목록 │
│        ├── preview/route.ts   # POST: 파일 트리 + 내용 생성  │
│        └── generate/route.ts  # POST: ZIP 파일 스트림 응답   │
│                                                             │
│  lib/                                                       │
│    ├── engine/               # CLI에서 가져온 생성 엔진       │
│    │   ├── generators/       # agent.ts, skill.ts, hook.ts  │
│    │   ├── templates/        # .hbs 템플릿 파일들             │
│    │   └── catalog/          # agents.json, skills.json     │
│    ├── zip.ts                # ZIP 생성 유틸 (archiver)      │
│    └── types.ts              # 공유 타입 정의                 │
└─────────────────────────────────────────────────────────────┘
```

### API 설계

```
GET  /api/catalog
  → { agents: [...], skills: [...], stacks: [...] }

POST /api/preview
  Body: { projectName, projectType, stack, agents: [], workflows: [] }
  → { fileTree: [...], files: { "CLAUDE.md": "내용...", ... } }

POST /api/generate
  Body: { projectName, projectType, stack, agents: [], workflows: [] }
  → Content-Type: application/zip (스트림 다운로드)
```

---

## 에이전트 카탈로그

> CLI v4에서 그대로 계승. 웹 UI에서는 카드 형태로 표시.

| ID | 에이전트 | 설명 | 생성 파일 |
|----|---------|------|----------|
| `backend` | 시니어 백엔드 엔지니어 | API 설계, DB, 서버 로직 | `api-agent.md` |
| `frontend` | 프론트엔드 전문가 | 컴포넌트, 상태관리, 라우팅 | `web-agent.md` |
| `uiux` | UI/UX 디자이너 | 접근성, 반응형, 디자인 시스템 | `uiux-agent.md` |
| `devops` | DevOps 엔지니어 | Docker, CI/CD, 배포 | `infra-agent.md` |
| `fullstack` | 풀스택 시니어 | 백엔드+프론트 통합 | `fullstack/SKILL.md` |
| `harness` | 하네스 엔지니어 (필수) | 4단계 품질 통제 | `harness-guide.md` + 4 스킬 |

### 기술 스택 프리셋

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

### CLI 자산 (v4에서 완성)
- [x] 하네스 엔지니어링 4단계 스킬 (harness-router/context/loop/worker)
- [x] 에이전트 Handlebars 템플릿 6종
- [x] 스킬 Handlebars 템플릿 5종
- [x] Hook 템플릿 (harness-gate.sh)
- [x] 카탈로그 JSON 3종 (agents, skills, stacks)
- [x] 파일 생성 엔진 (generators/*.ts)
- [x] settings.json 생성 로직
- [x] CLAUDE.md 생성 로직

---

## Phase 1: Week 1 — 프로젝트 셋업 + 생성 엔진 이식 (04-07 ~ 04-13)

### 목표
Next.js 프로젝트 초기화 + CLI 생성 엔진을 웹 서버용으로 이식

### 프로젝트 초기화

- [ ] `24SevenClaw-web/` Next.js 15 프로젝트 생성 (App Router + TypeScript)
- [ ] Tailwind CSS + shadcn/ui 설정
- [ ] 프로젝트 구조 설계 (`app/`, `lib/`, `components/`)
- [ ] ESLint + Prettier 설정
- [ ] Vercel 배포 연결 (dev 환경)

### 생성 엔진 이식

- [ ] `lib/engine/` 디렉토리 생성
- [ ] CLI의 `generators/*.ts`를 웹용으로 이식 (파일시스템 → 메모리 버퍼)
  - `agent.ts` — 에이전트 .md 생성 (문자열 반환)
  - `skill.ts` — 스킬 .md 생성 (문자열 반환)
  - `hook.ts` — Hook .sh 생성 (문자열 반환)
  - `settings.ts` — settings.json 생성 (객체 반환)
  - `claude-md.ts` — CLAUDE.md 생성 (문자열 반환)
- [ ] CLI의 `templates/` 복사 (Handlebars .hbs 파일)
- [ ] CLI의 `catalog/` 복사 (agents.json, skills.json, stacks.json)
- [ ] `lib/types.ts` — 공유 타입 정의 (CLI의 types.ts 기반)

### API 라우트 구현

- [ ] `app/api/catalog/route.ts` — GET: 카탈로그 목록 반환
- [ ] `app/api/preview/route.ts` — POST: 파일 트리 + 내용 프리뷰 생성
- [ ] `app/api/generate/route.ts` — POST: ZIP 스트림 응답
- [ ] `lib/zip.ts` — archiver 기반 ZIP 생성 유틸

### 테스트

- [ ] 생성 엔진 유닛 테스트 (CLI 테스트 이식)
- [ ] API 라우트 통합 테스트 (카탈로그 응답, ZIP 생성)

---

## Phase 1: Week 2 — 위저드 UI + 프리뷰 (04-14 ~ 04-20)

### 목표
4-Step 위저드 폼 UI + 실시간 파일 트리 프리뷰 구현

### Step 1: 프로젝트 정보 폼

- [ ] `ProjectForm.tsx` — 프로젝트 이름, 유형, 기술 스택 입력
- [ ] 스택 프리셋 카드 UI (로고 + 기술 목록 + 설명)
- [ ] 커스텀 스택 입력 폼 (custom 선택 시)
- [ ] React Hook Form 폼 밸리데이션

### Step 2: 에이전트 선택 UI

- [ ] `AgentSelector.tsx` — 에이전트 카드 그리드
- [ ] 카드 구성: 아이콘 + 이름 + 역할 설명 + 생성 파일 목록
- [ ] 하네스 엔지니어 카드 — 선택 해제 불가 (필수 표시)
- [ ] 선택/해제 토글 애니메이션

### Step 3: 워크플로우 옵션 UI

- [ ] `WorkflowToggle.tsx` — 워크플로우 토글 리스트
- [ ] 각 워크플로우 설명 + 의존성 표시 (예: Linear 연동 → .env 필요)
- [ ] 하네스 Gate 토글 — 기본 ON

### Step 4: 프리뷰 + 다운로드

- [ ] `FileTreePreview.tsx` — 생성될 파일/디렉토리 트리 표시
- [ ] `FileContentViewer.tsx` — 트리에서 파일 클릭 시 내용 미리보기
- [ ] 실시간 프리뷰: Step 1~3 변경 시 /api/preview 호출 → 트리 업데이트
- [ ] `DownloadButton.tsx` — /api/generate 호출 → ZIP 다운로드
- [ ] 다운로드 후 안내 메시지: "unzip → cd → claude 실행" 가이드

### 위저드 네비게이션

- [ ] Stepper 컴포넌트 (Step 1 → 2 → 3 → 4 진행 표시)
- [ ] 이전/다음 버튼 + 키보드 네비게이션
- [ ] 모바일 반응형 레이아웃

---

## Phase 1: Week 3 — 랜딩 페이지 + UX 폴리싱 (04-21 ~ 04-27)

### 목표
랜딩 페이지 + 다운로드 후 가이드 + 전체 UX 폴리싱

### 랜딩 페이지

- [ ] 히어로 섹션: 핵심 메시지 + CTA ("지금 시작하기")
- [ ] 작동 원리 섹션: 3-Step 시각화 (선택 → 다운로드 → 실행)
- [ ] 에이전트 소개 섹션: 6종 에이전트 카드 + 역할 설명
- [ ] 하네스 엔지니어링 설명 섹션: 4단계 워크플로우 다이어그램
- [ ] FAQ 섹션
- [ ] 푸터: GitHub 링크, 문서 링크

### 다운로드 후 가이드 페이지

- [ ] ZIP 다운로드 완료 후 가이드 페이지/모달 표시
- [ ] OS별 설치 가이드 (unzip 명령어, Claude Code 설치)
- [ ] 생성된 파일 구조 설명
- [ ] "다음 단계" 체크리스트

### UX 폴리싱

- [ ] 로딩 상태 (스피너, 스켈레톤)
- [ ] 에러 핸들링 (API 실패 시 재시도 안내)
- [ ] 다크모드 지원
- [ ] SEO 메타태그 + OG 이미지
- [ ] 접근성 검증 (WCAG AA)
- [ ] 모바일/태블릿 반응형 최종 점검

### 테스트

- [ ] E2E 테스트: 전체 위저드 → 다운로드 플로우
- [ ] ZIP 내용 검증: 다운로드된 ZIP 해제 → 파일 구조 확인
- [ ] 크로스 브라우저 테스트 (Chrome, Safari, Firefox)

---

## Phase 1: Week 4 — 배포 + 문서 + 최종 검증 (04-28 ~ 05-04)

### 목표
프로덕션 배포 + 문서 + 실사용 검증

### 배포

- [ ] Vercel 프로덕션 배포 (도메인 연결)
- [ ] 도메인 설정 (24sevenclaw.dev 또는 유사)
- [ ] 환경변수 설정 (필요 시)
- [ ] Vercel Analytics 연동 (방문자 추적)

### 문서

- [ ] README.md 업데이트: 웹 서비스 사용법 + 스크린샷
- [ ] docs/web-guide.md — 웹 서비스 상세 가이드
- [ ] docs/cli-guide.md 업데이트 — CLI도 계속 사용 가능함을 안내
- [ ] CLAUDE.md 갱신: Web-First 아키텍처 반영

### 실사용 검증

- [ ] 웹에서 생성 → 다운로드 → unzip → Claude Code 실행 → 하네스 작동 확인
- [ ] 모든 스택 프리셋 검증 (fastapi-nextjs, django-react, express-vue 등)
- [ ] 모든 에이전트/스킬 조합 검증
- [ ] harness-gate.sh 실제 동작 확인 (lint/test 실패 시 차단)
- [ ] 모바일 브라우저 접속 → 다운로드 테스트

### CLI 병행 유지

- [ ] CLI README에 "웹에서도 사용 가능" 안내 추가
- [ ] CLI와 웹이 동일한 템플릿/카탈로그를 사용하는지 확인
- [ ] npm publish (CLI 유지 — 파워유저용)

---

## Phase 2 예고 (5월 이후)

> Phase 1에서 웹 서비스가 검증되면 확장

- **사용자 계정 + 프로젝트 저장**: 생성한 설정을 재다운로드/수정
- **커뮤니티 에이전트**: 사용자가 커스텀 에이전트 업로드/공유
- **에이전트 마켓플레이스**: 프리미엄 에이전트 유료 판매
- **사용 통계 대시보드**: 어떤 에이전트/스택 조합이 인기 있는지
- **CLI ↔ 웹 동기화**: CLI에서 `24sc sync`로 웹 설정 가져오기
- **GitHub 연동**: 생성된 파일을 바로 새 레포에 push

---

## 핵심 원칙

1. **Web-First**: 브라우저만으로 완전한 경험 제공, CLI는 파워유저용 병행
2. **하네스 필수**: 모든 프로젝트에 하네스 엔지니어링 기본 탑재
3. **프리뷰 우선**: 다운로드 전에 생성될 파일을 반드시 미리보기
4. **무상태 서비스**: DB 없이 JSON 카탈로그 + 템플릿만으로 동작
5. **CLI 자산 재활용**: 생성 엔진, 템플릿, 카탈로그를 CLI와 웹이 공유
6. **점진적 확장**: Web MVP → 검증 → 계정/커뮤니티/마켓플레이스

---

## 계획 변경 이력

| 변경일 | 변경 내용 | 사유 |
|--------|----------|------|
| 2026-03-31 | 서비스 피벗: 고객 서버 에이전트 → 클라우드 SaaS | paperclip.ing 참고 |
| 2026-04-01 | LoadMap v2: 4주 → 5주 확장, 설계 갭 보완 | Codex adversarial review |
| 2026-04-02 | v3 → v4: CLI-First 하이브리드 | MVP 속도 우선, 인프라 비용 0 |
| 2026-04-03 | v4 → v5: CLI-First → Web-First | CLI의 본질이 "입력→파일 생성"이라 웹 전환 자연스러움, 진입 장벽 제거 |

---

## 참조 문서

- `LoadMap.md` — 이전 로드맵 v4 (CLI-First)
- `24SevenClaw-cli/` — CLI 생성 엔진 소스 (이식 대상)
- `.claude/agents/harness-guide.md` — 하네스 엔지니어링 가이드
- `.claude/skills/dev-skills.md` — 개발 스킬 레지스트리
- `docs/cli-guide.md` — CLI 상세 가이드
