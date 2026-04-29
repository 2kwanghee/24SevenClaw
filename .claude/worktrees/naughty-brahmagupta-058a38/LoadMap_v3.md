# ClickEye - Development Roadmap v3

> AI 개발 자동화 솔루션 빌더 — 브라우저에서 솔루션 설계 → 인력(Agent) 채용 → 스킬 장착 → ZIP 다운로드 → 즉시 개발 시작
> 로드맵 기간: 2026-04-07 ~ 2026-04-20 (2주)
> 업무 관리: Linear 티켓 기반

---

## 용어 정의

| 용어 | 의미 |
|------|------|
| **유저** | 서비스 이용자 (개발자, PM, 비개발자) |
| **관리자** | ClickEye 운영팀 (우리) |
| **웹** | ClickEye 웹 서비스 |
| **Agent 플랫폼** | Claude Code, Gemini CLI, Codex, Cursor 등 AI 코딩 도구 |
| **에이전트** | 웹에서 채용하는 가상 인력 (백엔드 엔지니어, 프론트엔드 등) |
| **스킬** | 에이전트가 사용하는 외부 도구 연동 (Notion, Linear, Teams, DB 등) |

---

## 서비스 비전

- **핵심 가치**: 브라우저에서 AI 개발 자동화 환경을 설계하고, ZIP 하나로 즉시 사용
- **대상 유저**: 개발자, PM, 스타트업 — 터미널 경험 불문
- **비용 모델**: 1계정 1프로젝트 무료, 추가 프로젝트 유료 라이센스
- **Agent 토큰**: 유저 부담 (BYOK — Bring Your Own Key)
- **CLI 병행**: CLI는 파워유저용으로 유지 (동일 생성 엔진 공유)

---

## 완료된 자산 (Phase 0)

### 웹 (clickeye-web)
- [x] 랜딩 페이지 (히어로 + CTA + 특징 + 가격)
- [x] 회원가입 / 로그인 (Auth.js v5 + JWT)
- [x] 대시보드 레이아웃
- [x] 프로젝트 목록 / 생성 / 상세 / 설정 페이지 (기본 CRUD)
- [x] 레지스트리 페이지 (기본 구조)

### API (clickeye-api)
- [x] 인증 엔드포인트 (JWT)
- [x] 프로젝트 CRUD API
- [x] User / Project / ProjectConfig / Registry / License / Ticket 모델
- [x] 헬스체크

### CLI (clickeye-cli)
- [x] 에이전트 카탈로그 6종 (backend, frontend, uiux, devops, fullstack, harness)
- [x] 스킬 카탈로그 5종 (TDD, AI 코드 리뷰, Linear, Ralph 루프, 하네스 Gate)
- [x] 스택 프리셋 6종 (FastAPI+Next.js, Django+React, Express+Vue 등)
- [x] Handlebars 템플릿 (에이전트 6종 + 스킬 5종 + CLAUDE.md)
- [x] 파일 생성 엔진 (generators/*.ts)

---

## 솔루션 플로우 (7-Step 위저드)

```
[로그인 완료 → 대시보드]

Step 1: 회사 정보 입력
  ├── 회사명, 규모 (1인/소규모/중소/대기업)
  ├── 업종 (IT/금융/커머스/헬스케어/교육/기타)
  └── 기존 사용 기술 스택 (선택)

Step 2: 솔루션 정의
  ├── 프로젝트명
  ├── 솔루션 유형 (SaaS / REST API / 풀스택 앱 / 내부 도구 / MVP / 커스텀)
  ├── 목표 설명 (자유 기술 텍스트)
  └── 🤖 자동 추천: 입력 기반으로 에이전트/스킬/파이프라인 추천
      (Phase 1: 규칙 기반 매칭, Phase 2: LLM 기반 추천)

Step 3: 인력 채용 (에이전트 선택)
  ├── 카드 UI: 백엔드 / 프론트엔드 / UI/UX / DevOps / 풀스택 / 하네스
  ├── Step 2 추천 기반 사전 체크
  ├── 각 에이전트별 역할 설명 + 생성 파일 프리뷰
  └── 💡 지속 업데이트: 관리자가 새 에이전트 추가 가능

Step 4: 스킬 장착 (도구 연동)
  ├── 카드/리스트 UI: Notion / Linear / Teams / Slack / DB / GitHub 등
  ├── 각 스킬별 설명 + 필요 정보 안내
  ├── 🔑 API 키 필요 시: 인라인 입력 폼 표시
  │     └── 입력된 키 → .env 파일로 ZIP에만 포함 (서버 미저장)
  └── 💡 지속 업데이트: 관리자가 새 스킬 추가 가능

Step 5: 자동화 파이프라인 설정
  ├── 토글 리스트:
  │     ☐ 하네스 엔지니어링 (4단계 품질 통제)
  │     ☐ TDD (테스트 주도 개발)
  │     ☐ AI 코드 리뷰
  │     ☐ 텔레그램 알림
  │     ☐ 린트/타입체크 Gate (커밋 차단)
  │     ☐ Ralph 자율 개발 루프
  └── 각 파이프라인 설명 + 의존성 안내

Step 6: Agent 플랫폼 선택
  ├── 카드 UI:
  │     ☐ Claude Code    → .claude/ 구조
  │     ☐ Gemini CLI     → .gemini/ 구조
  │     ☐ Codex          → codex 전용 구조
  │     ☐ Cursor         → .cursor/rules/ 구조
  ├── 플랫폼별 폴더 구조 프리뷰 표시
  └── 💡 지속 업데이트: 새 Agent 플랫폼 추가 가능

Step 7: 프리뷰 + 다운로드
  ├── [왼쪽] 파일 트리 프리뷰 (플랫폼별 구조 반영)
  ├── [오른쪽] 파일 내용 미리보기 (클릭 시)
  ├── 전체 설정 요약 카드
  ├── [다운로드 버튼] → project-name.zip
  └── 다운로드 후 가이드: "unzip → cd → agent 실행" 안내
```

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15 — Vercel)                             │
│                                                             │
│  app/(dashboard)/                                           │
│    ├── projects/                                            │
│    │   └── new/                    # 7-Step 위저드           │
│    │       ├── page.tsx            # 위저드 메인 (Stepper)   │
│    │       └── components/                                  │
│    │           ├── CompanyForm.tsx       # Step 1            │
│    │           ├── SolutionForm.tsx      # Step 2            │
│    │           ├── AgentSelector.tsx     # Step 3            │
│    │           ├── SkillSelector.tsx     # Step 4            │
│    │           ├── PipelineToggle.tsx    # Step 5            │
│    │           ├── PlatformSelector.tsx  # Step 6            │
│    │           ├── PreviewPanel.tsx      # Step 7            │
│    │           ├── FileTreePreview.tsx   # 트리 프리뷰        │
│    │           ├── FileContentViewer.tsx # 파일 내용 보기     │
│    │           └── DownloadButton.tsx    # ZIP 다운로드       │
│    └── projects/[projectId]/       # 프로젝트 상세/재다운로드 │
│                                                             │
│  lib/                                                       │
│    ├── engine/                     # CLI에서 이식한 생성 엔진 │
│    │   ├── generators/             # agent, skill, hook, etc │
│    │   ├── templates/              # .hbs 템플릿 (플랫폼별)  │
│    │   ├── catalog/                # agents.json, skills.json│
│    │   └── platforms/              # 플랫폼별 구조 정의      │
│    ├── zip.ts                      # ZIP 생성 유틸           │
│    └── recommender.ts              # 규칙 기반 추천 엔진      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Backend (FastAPI — Railway/Fly.io)                         │
│                                                             │
│  app/api/v1/                                                │
│    ├── auth.py                     # 인증 (완료)             │
│    ├── projects.py                 # 프로젝트 CRUD (완료)    │
│    ├── catalog.py                  # 카탈로그 조회 API (신규) │
│    ├── generate.py                 # ZIP 생성 API (신규)     │
│    └── organizations.py            # 회사 정보 API (신규)    │
│                                                             │
│  app/models/                                                │
│    ├── user.py                     # 유저 (완료)             │
│    ├── project.py                  # 프로젝트 (완료)         │
│    ├── project_config.py           # 프로젝트 설정 (확장)    │
│    └── organization.py             # 회사 정보 (신규)        │
└─────────────────────────────────────────────────────────────┘
```

### API 설계

```
# 기존 (완료)
POST /api/v1/auth/register          → 회원가입
POST /api/v1/auth/login             → 로그인
GET  /api/v1/projects               → 프로젝트 목록
POST /api/v1/projects               → 프로젝트 생성
GET  /api/v1/projects/{id}          → 프로젝트 상세

# 신규
POST /api/v1/organizations          → 회사 정보 등록/수정
GET  /api/v1/organizations/me       → 내 회사 정보 조회

GET  /api/v1/catalog/agents         → 에이전트 목록
GET  /api/v1/catalog/skills         → 스킬 목록
GET  /api/v1/catalog/stacks         → 스택 프리셋 목록
GET  /api/v1/catalog/platforms      → Agent 플랫폼 목록
GET  /api/v1/catalog/pipelines      → 자동화 파이프라인 목록

POST /api/v1/projects/{id}/config   → 프로젝트 설정 저장 (위저드 전체 결과)
GET  /api/v1/projects/{id}/config   → 프로젝트 설정 조회

POST /api/v1/projects/{id}/preview  → 파일 트리 + 내용 프리뷰
POST /api/v1/projects/{id}/generate → ZIP 파일 스트림 다운로드

POST /api/v1/recommend              → 솔루션 기반 추천 (에이전트/스킬/파이프라인)
```

---

## 에이전트 카탈로그

> CLI에서 계승 + 웹 UI 카드로 표시. 관리자가 지속 추가 가능.

| ID | 에이전트 | 역할 | 생성 파일 |
|----|---------|------|----------|
| `backend` | 시니어 백엔드 엔지니어 | API 설계, DB, 서버 로직 | `api-agent.md` |
| `frontend` | 프론트엔드 전문가 | 컴포넌트, 상태관리, 라우팅 | `web-agent.md` |
| `uiux` | UI/UX 디자이너 | 접근성, 반응형, 디자인 시스템 | `uiux-agent.md` |
| `devops` | DevOps 엔지니어 | Docker, CI/CD, 배포 | `infra-agent.md` |
| `fullstack` | 풀스택 시니어 | 백엔드+프론트 통합 | `fullstack-agent.md` |
| `harness` | 하네스 엔지니어 | 4단계 품질 통제 | `harness-guide.md` + 스킬 4종 |

## 스킬 카탈로그

> 두 종류: **워크플로우 스킬** (CLI 계승) + **외부 도구 스킬** (신규)

### 워크플로우 스킬 (CLI 계승)

| ID | 스킬 | API 키 | 설명 |
|----|------|--------|------|
| `tdd` | TDD 스마트 코딩 | 불필요 | 테스트 → 구현 → 리팩터링 |
| `ai-critique` | AI 코드 리뷰 | 불필요 | 자동 리뷰 + 개선 제안 |
| `ralph-loop` | Ralph 자율 루프 | 불필요 | 자율 개발 루프 |
| `harness-gate` | 하네스 Gate | 불필요 | lint+test 통과 후 커밋 허용 |

### 외부 도구 스킬 (신규 — 지속 업데이트)

| ID | 스킬 | API 키 | .env 변수 |
|----|------|--------|----------|
| `linear` | Linear 연동 | 필요 | `LINEAR_API_KEY` |
| `notion` | Notion 연동 | 필요 | `NOTION_API_KEY` |
| `slack` | Slack 알림 | 필요 | `SLACK_WEBHOOK_URL` |
| `telegram` | Telegram 알림 | 필요 | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| `github` | GitHub 연동 | 필요 | `GITHUB_TOKEN` |
| `teams` | Teams 알림 | 필요 | `TEAMS_WEBHOOK_URL` |
| `database` | DB 연결 | 필요 | `DATABASE_URL` |

## Agent 플랫폼

> 유저가 선택하는 AI 코딩 도구에 따라 폴더 구조가 달라짐

| ID | 플랫폼 | 설정 디렉토리 | 에이전트 파일 위치 | 설정 파일 |
|----|--------|-------------|-------------------|----------|
| `claude-code` | Claude Code | `.claude/` | `.claude/agents/` | `.claude/settings.json` |
| `gemini-cli` | Gemini CLI | `.gemini/` | `.gemini/agents/` | `.gemini/settings.json` |
| `codex` | Codex (OpenAI) | `.codex/` | `.codex/agents/` | `codex.json` |
| `cursor` | Cursor | `.cursor/rules/` | `.cursor/rules/` | `.cursorrules` |

---

## Linear 티켓 구조

### 프로젝트 라벨

| 라벨 | 용도 |
|------|------|
| `web` | 프론트엔드 (Next.js) |
| `api` | 백엔드 (FastAPI) |
| `engine` | 생성 엔진 (lib/engine) |
| `infra` | 인프라/배포 |

### 티켓 사이즈 기준

| 사이즈 | 예상 소요 | 예시 |
|--------|----------|------|
| `XS` | ~2시간 | 카탈로그 JSON 추가, 타입 정의 |
| `S` | ~4시간 | 단일 API 엔드포인트, 단일 컴포넌트 |
| `M` | ~1일 | 위저드 Step 1개, API + 프론트 연동 |
| `L` | ~2일 | 생성 엔진 이식, 멀티플랫폼 템플릿 |
| `XL` | ~3일+ | E2E 플로우 통합, 프리뷰 시스템 |

---

## Week 1: 생성 엔진 이식 + 백엔드 API + 위저드 Step 1~4 (04-07 ~ 04-13)

> 목표: 유저가 회사 정보 입력 → 솔루션 정의 → 에이전트 채용 → 스킬 장착까지 진행 가능

### Day 1-2 (04-07 ~ 04-08): 기반 구축

**[api] Organization 모델 + API** `M`
- Organization 모델 생성 (company_name, size, industry, tech_stack)
- POST /api/v1/organizations — 회사 정보 등록/수정
- GET /api/v1/organizations/me — 내 회사 정보 조회
- User ↔ Organization 1:1 관계

**[api] 카탈로그 API** `S`
- GET /api/v1/catalog/agents — agents.json 반환
- GET /api/v1/catalog/skills — skills.json 반환 (워크플로우 + 외부 도구)
- GET /api/v1/catalog/platforms — platforms.json 반환
- GET /api/v1/catalog/pipelines — pipelines.json 반환
- JSON 파일 기반, DB 불필요

**[engine] 카탈로그 JSON 확장** `S`
- skills.json — 외부 도구 스킬 추가 (notion, slack, telegram, github, teams, database)
- platforms.json 신규 생성 (claude-code, gemini-cli, codex, cursor)
- pipelines.json 신규 생성 (harness, tdd, ai-critique, telegram, lint-gate, ralph-loop)

**[api] ProjectConfig 모델 확장** `S`
- 위저드 전체 결과를 저장하는 JSONB 컬럼
- POST /api/v1/projects/{id}/config — 설정 저장
- GET /api/v1/projects/{id}/config — 설정 조회

### Day 3-4 (04-09 ~ 04-10): 위저드 Step 1~3

**[web] 위저드 Stepper 프레임** `M`
- 7-Step Stepper 컴포넌트 (진행률 표시)
- 이전/다음 네비게이션 + 상태 관리 (Zustand)
- 위저드 데이터 타입 정의 (WizardState)
- /projects/new 페이지를 위저드로 전환

**[web] Step 1: 회사 정보 (CompanyForm)** `S`
- 회사명 입력
- 규모 선택 (1인/소규모/중소/대기업)
- 업종 선택 (IT/금융/커머스/헬스케어/교육/기타)
- 기존 기술 스택 선택 (멀티셀렉트, 선택사항)
- Organization API 연동

**[web] Step 2: 솔루션 정의 (SolutionForm)** `S`
- 프로젝트명 입력 + 밸리데이션 (영문, 하이픈 허용)
- 솔루션 유형 선택 (SaaS/REST API/풀스택/내부 도구/MVP/커스텀)
- 기술 스택 프리셋 선택 (카드 UI)
- 목표 설명 텍스트에어리어

**[web] Step 3: 에이전트 채용 (AgentSelector)** `M`
- 카탈로그 API에서 에이전트 목록 로드
- 카드 그리드: 아이콘 + 이름 + 역할 설명 + 생성 파일
- 선택/해제 토글
- Step 2 입력 기반 사전 추천 체크 (규칙 기반)

### Day 5 (04-11): 위저드 Step 4

**[web] Step 4: 스킬 장착 (SkillSelector)** `M`
- 카탈로그 API에서 스킬 목록 로드
- 워크플로우 스킬 섹션 + 외부 도구 스킬 섹션 분리
- API 키 필요 스킬: 선택 시 인라인 입력 폼 확장
- 입력된 키 값은 Zustand 상태에만 저장 (서버 미전송)
- 키 마스킹 표시 (보안 UX)

**[api] 추천 엔진 (규칙 기반)** `S`
- POST /api/v1/recommend
- 솔루션 유형 → 추천 에이전트 매핑 규칙
- 솔루션 유형 → 추천 스킬 매핑 규칙
- 솔루션 유형 → 추천 파이프라인 매핑 규칙

### Day 6-7 (04-12 ~ 04-13): 엔진 이식 + 통합

**[engine] CLI 생성 엔진 웹 이식** `L`
- CLI의 generators/*.ts를 lib/engine/generators/로 이식
- 파일시스템 출력 → 메모리 버퍼(Map<string, string>) 반환으로 변환
- agent.ts — 에이전트 .md 생성 (문자열 반환)
- skill.ts — 스킬 .md 생성 (문자열 반환)
- hook.ts — Hook .sh 생성 (문자열 반환)
- settings.ts — settings.json 생성 (객체 반환)
- claude-md.ts — CLAUDE.md 생성 (문자열 반환)
- templates/*.hbs 복사

**[engine] 멀티플랫폼 지원 기초** `M`
- lib/engine/platforms/ 디렉토리 구조
- 플랫폼별 디렉토리 매핑 정의 (claude → .claude/, cursor → .cursor/rules/)
- 플랫폼별 설정 파일 생성기 (settings.json, .cursorrules 등)
- Claude Code 플랫폼 완전 구현 (기존 CLI 로직 재활용)

---

## Week 2: 위저드 Step 5~7 + 프리뷰 + ZIP 생성 + 통합 테스트 (04-14 ~ 04-20)

> 목표: 전체 위저드 완성 → 프리뷰 → ZIP 다운로드 → 실사용 검증

### Day 1 (04-14): 위저드 Step 5~6

**[web] Step 5: 자동화 파이프라인 (PipelineToggle)** `S`
- 카탈로그 API에서 파이프라인 목록 로드
- 토글 리스트: 각 파이프라인 ON/OFF
- 각 항목별 설명 + 의존성 안내 (예: "Linear 연동이 필요합니다")
- Step 4에서 선택한 스킬과 연동 표시

**[web] Step 6: Agent 플랫폼 선택 (PlatformSelector)** `S`
- 카탈로그 API에서 플랫폼 목록 로드
- 카드 UI: 로고 + 이름 + 생성 폴더 구조 프리뷰
- 단일 선택 (라디오)
- 선택 시 하단에 폴더 구조 미니 프리뷰

### Day 2-3 (04-15 ~ 04-16): 프리뷰 + ZIP 생성

**[api] 프리뷰 API** `M`
- POST /api/v1/projects/{id}/preview
- 위저드 설정 기반으로 파일 트리 + 파일 내용 생성
- 생성 엔진 호출 → { fileTree: [...], files: { path: content } } 반환
- 플랫폼별 구조 반영

**[api] ZIP 생성 API** `M`
- POST /api/v1/projects/{id}/generate
- 위저드 설정 + API 키(.env) 기반 ZIP 스트림 생성
- .env 파일: 클라이언트에서 전달된 키만 포함 (서버 미저장)
- Content-Type: application/zip 스트리밍 응답
- Python zipfile 모듈 사용

**[web] Step 7: 프리뷰 + 다운로드 (PreviewPanel)** `L`
- 프리뷰 API 호출 → 파일 트리 렌더링
- FileTreePreview: 폴더/파일 트리 컴포넌트
- FileContentViewer: 파일 클릭 시 내용 미리보기 (코드 하이라이트)
- 전체 설정 요약 카드 (회사/솔루션/에이전트/스킬/파이프라인/플랫폼)
- DownloadButton: ZIP 다운로드 + 진행률

### Day 4 (04-17): .env 생성 + 다운로드 후 가이드

**[engine] .env 생성기** `S`
- 스킬에서 수집된 API 키 → .env 파일 내용 생성
- 키 유효성 기본 검증 (형식 체크)
- .env.example 파일도 함께 생성 (키 값 제외, 변수명만)

**[web] 다운로드 후 가이드** `S`
- ZIP 다운로드 완료 후 가이드 모달/페이지
- 플랫폼별 실행 가이드 (Claude Code: `claude`, Cursor: "Open Folder" 등)
- 생성된 파일 구조 설명
- "다음 단계" 체크리스트

**[api] 프로젝트 설정 저장 연동** `S`
- 위저드 완료 시 전체 설정을 ProjectConfig에 저장
- 프로젝트 상세 페이지에서 설정 조회 + 재다운로드 가능

### Day 5 (04-18): 추가 플랫폼 + 추천 고도화

**[engine] Gemini CLI 플랫폼 템플릿** `M`
- .gemini/ 구조 정의
- 에이전트/스킬 템플릿을 Gemini 형식으로 변환
- settings 파일 생성기

**[engine] Cursor 플랫폼 템플릿** `M`
- .cursor/rules/ 구조 정의
- 에이전트 내용을 .cursorrules 형식으로 변환
- Cursor 설정 파일 생성기

**[web] 추천 엔진 UI 연동** `S`
- Step 2 입력 변경 시 /api/v1/recommend 호출
- Step 3, 4, 5에서 추천 결과 반영 (사전 체크 + 뱃지)
- "추천" 뱃지 표시

### Day 6-7 (04-19 ~ 04-20): 통합 테스트 + 폴리싱

**[web] E2E 위저드 플로우 테스트** `M`
- Step 1 → 7 전체 플로우 수동 테스트
- ZIP 다운로드 → 해제 → 파일 구조 검증
- Claude Code 플랫폼: unzip → `claude` 실행 확인
- 모든 에이전트/스킬 조합 기본 검증

**[web] UX 폴리싱** `M`
- 로딩 상태 (스켈레톤, 스피너)
- 에러 핸들링 (API 실패 시 재시도/안내)
- 반응형 레이아웃 점검 (모바일/태블릿)
- 다크모드 호환 확인

**[api] 통합 테스트** `S`
- 카탈로그 API 응답 검증
- 프리뷰 API → 파일 트리 구조 검증
- ZIP 생성 → 파일 내용 검증
- .env 파일 포함 여부 검증

---

## Linear 에픽 / 티켓 매핑

### Epic 1: 생성 엔진 이식 (Week 1)
| # | 티켓 | 라벨 | 사이즈 | 일정 |
|---|------|------|--------|------|
| 1 | Organization 모델 + API 구현 | `api` | M | 04-07~08 |
| 2 | 카탈로그 API (agents/skills/platforms/pipelines) | `api` | S | 04-07~08 |
| 3 | 카탈로그 JSON 확장 (외부 스킬, 플랫폼, 파이프라인) | `engine` | S | 04-07~08 |
| 4 | ProjectConfig 모델 확장 (JSONB 위저드 결과) | `api` | S | 04-07~08 |
| 5 | 위저드 Stepper 프레임 + 상태 관리 | `web` | M | 04-09~10 |
| 6 | Step 1: 회사 정보 폼 (CompanyForm) | `web` | S | 04-09~10 |
| 7 | Step 2: 솔루션 정의 폼 (SolutionForm) | `web` | S | 04-09~10 |
| 8 | Step 3: 에이전트 채용 카드 UI (AgentSelector) | `web` | M | 04-09~10 |
| 9 | Step 4: 스킬 장착 + API 키 입력 (SkillSelector) | `web` | M | 04-11 |
| 10 | 추천 엔진 API (규칙 기반) | `api` | S | 04-11 |
| 11 | CLI 생성 엔진 웹 이식 (generators + templates) | `engine` | L | 04-12~13 |
| 12 | 멀티플랫폼 지원 기초 (Claude Code 완전 구현) | `engine` | M | 04-12~13 |

### Epic 2: 위저드 완성 + ZIP 생성 (Week 2)
| # | 티켓 | 라벨 | 사이즈 | 일정 |
|---|------|------|--------|------|
| 13 | Step 5: 자동화 파이프라인 토글 (PipelineToggle) | `web` | S | 04-14 |
| 14 | Step 6: Agent 플랫폼 선택 (PlatformSelector) | `web` | S | 04-14 |
| 15 | 프리뷰 API (파일 트리 + 내용 생성) | `api` | M | 04-15~16 |
| 16 | ZIP 생성 API (스트리밍 + .env 포함) | `api` | M | 04-15~16 |
| 17 | Step 7: 프리뷰 패널 + 다운로드 (PreviewPanel) | `web` | L | 04-15~16 |
| 18 | .env 생성기 + .env.example | `engine` | S | 04-17 |
| 19 | 다운로드 후 가이드 모달 | `web` | S | 04-17 |
| 20 | 프로젝트 설정 저장/조회 연동 | `api` | S | 04-17 |
| 21 | Gemini CLI 플랫폼 템플릿 | `engine` | M | 04-18 |
| 22 | Cursor 플랫폼 템플릿 | `engine` | M | 04-18 |
| 23 | 추천 엔진 UI 연동 | `web` | S | 04-18 |
| 24 | E2E 위저드 플로우 테스트 | `web` | M | 04-19~20 |
| 25 | UX 폴리싱 (로딩/에러/반응형/다크모드) | `web` | M | 04-19~20 |
| 26 | API 통합 테스트 | `api` | S | 04-19~20 |

**총 26개 티켓** | XS: 0 / S: 11 / M: 11 / L: 3 / XL: 1

---

## Phase 2 예고 (04-21 이후)

> Phase 1 (2주) 완료 후 확장

- **LLM 기반 추천**: 규칙 기반 → Claude/GPT 활용 지능형 추천
- **Codex 플랫폼 템플릿**: OpenAI Codex 전용 구조
- **커뮤니티 에이전트**: 유저가 커스텀 에이전트 업로드/공유
- **에이전트 마켓플레이스**: 프리미엄 에이전트 유료 판매
- **프로젝트 재편집**: 다운로드 후 설정 변경 → 재다운로드
- **사용 통계 대시보드**: 인기 에이전트/스킬/플랫폼 조합 분석
- **CLI ↔ 웹 동기화**: CLI에서 웹 설정 가져오기
- **GitHub 연동**: 생성된 파일을 새 레포에 직접 push
- **라이센스 시스템**: 1계정 1프로젝트 무료, 추가 유료

---

## 핵심 원칙

1. **솔루션 중심**: 기술 스택이 아닌 "무엇을 만들 것인가"부터 시작
2. **프리뷰 우선**: 다운로드 전에 생성될 파일을 반드시 미리보기
3. **API 키 보안**: 유저 키는 클라이언트에서만 처리, 서버 미저장, .env로만 ZIP에 포함
4. **멀티플랫폼**: Claude Code 외에도 Gemini, Codex, Cursor 지원
5. **지속 확장**: 에이전트/스킬/플랫폼은 관리자가 카탈로그 JSON 추가만으로 확장
6. **CLI 자산 재활용**: 생성 엔진, 템플릿, 카탈로그를 CLI와 웹이 공유
7. **Linear 기반 업무**: 모든 작업은 Linear 티켓으로 추적

---

## 계획 변경 이력

| 변경일 | 변경 내용 | 사유 |
|--------|----------|------|
| 2026-03-31 | 서비스 피벗: 고객 서버 에이전트 → 클라우드 SaaS | paperclip.ing 참고 |
| 2026-04-01 | LoadMap v2: 4주 → 5주 확장, 설계 갭 보완 | Codex adversarial review |
| 2026-04-02 | v3 → v4: CLI-First 하이브리드 | MVP 속도 우선 |
| 2026-04-03 | v4 → v5: CLI-First → Web-First | 진입 장벽 제거 |
| 2026-04-03 | v5 → v3(신규): 솔루션 플랜 재설계 | 7-Step 위저드, 멀티플랫폼, 스킬 확장, 2주 집중 |

---

## 참조 문서

- `LoadMap_v2.md` — 이전 로드맵 (Web-First v5, 4주)
- `LoadMap.md` — 이전 로드맵 (CLI-First v4)
- `clickeye-cli/` — CLI 생성 엔진 소스 (이식 대상)
- `clickeye-web/` — 웹 프론트엔드 (기 구현: 랜딩/인증/대시보드)
- `clickeye-api/` — 백엔드 API (기 구현: 인증/프로젝트 CRUD)
- `.claude/agents/harness-guide.md` — 하네스 엔지니어링 가이드
- `.claude/skills/dev-skills.md` — 개발 스킬 레지스트리
