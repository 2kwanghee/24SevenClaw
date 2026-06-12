# ClickEye — 제품 사용 안내 & 동작 원리

> **AI 개발 자동화 솔루션 빌더**
> 브라우저에서 솔루션을 설계하면 ZIP 한 번으로 AI 가 코드를 만들기 시작합니다.
>
> 본 문서는 ClickEye 를 처음 접하는 분들께 **사용 방법**과 **기술 동작 원리**를 안내합니다.

---

## 목차

1. [한눈에 보는 ClickEye](#1-한눈에-보는-clickeye)
2. [어떤 문제를 해결하나](#2-어떤-문제를-해결하나)
3. [두 가지 진입점](#3-두-가지-진입점)
4. [사용 안내 ① — 신규 솔루션 (7-Step 위저드)](#4-사용-안내--신규-솔루션-7-step-위저드)
5. [사용 안내 ② — 기존 코드 현대화 (Modernize, MVP-2-A)](#5-사용-안내--기존-코드-현대화-modernize-mvp-2-a)
6. [동작 원리 — 클라우드 + 로컬 하이브리드 아키텍처](#6-동작-원리--클라우드--로컬-하이브리드-아키텍처)
7. [AI 자동 개발 흐름 (ZIP 풀고 실행)](#7-ai-자동-개발-흐름-zip-풀고-실행)
8. [멀티 Agent 플랫폼 지원](#8-멀티-agent-플랫폼-지원)
9. [경쟁사 대비 차별점](#9-경쟁사-대비-차별점)
10. [보안 / 라이센스 / 가격](#10-보안--라이센스--가격)
11. [데모 시연 가이드](#11-데모-시연-가이드)
12. [FAQ](#12-faq)

---

## 1. 한눈에 보는 ClickEye

ClickEye 는 다음을 한 번에 해결합니다:

| 단계 | 사용자가 하는 일 | 시간 |
|------|---|---|
| ① 설계 | 브라우저에서 7-Step 위저드 진행 | **5~10 분** |
| ② 다운로드 | ZIP 한 개 | **1 클릭** |
| ③ 실행 | 로컬에서 `bash start.sh` | **수분 내 자동 시작** |
| ④ 결과 | AI 가 코드 작성 + Linear 이슈 자동 등록 + PR 자동 생성 | **사용자 부재 중 진행** |

### 핵심 가치

> **"브라우저에서 5분 만에 설계한 솔루션이, 내 로컬 PC 에서 AI 가 자율적으로 코드를 작성하기 시작한다."**

기존: 환경 설정·도구 통합·프롬프트 작성에 **수시간 ~ 수일** 소요
ClickEye: 위저드 → ZIP → 실행 → **즉시 AI 가 일을 시작**

---

## 2. 어떤 문제를 해결하나

### Pain Point — 현장에서 보는 문제

```
"Claude Code 좋다는데 막상 도입하려니..."

  □ Anthropic / OpenAI / Google 중 어떤 AI 를 써야 하지?
  □ .claude/agents/ 디렉토리 구조는 어떻게 잡지?
  □ Linear / Notion / Slack 연동 코드는 매번 새로 짜야 하나?
  □ 회사 PM 처럼 일정·우선순위 관리해 줄 AI 는 없나?
  □ 기존 레거시 코드를 Python 3.12 / Node 22 로 올리고 싶은데 어디부터?
  □ 보안 — 우리 코드를 외부 클라우드에 보내고 싶지 않아.
```

### ClickEye 의 답

| Pain | 해결 방식 |
|---|---|
| AI 플랫폼 선택 | 4 종 (Claude Code / Gemini / Codex / Cursor) 중 위저드에서 선택 |
| 에이전트·도구 구조 | 카탈로그 (Agent 7종, Skill 18종, MCP, Hook, Pipeline) 중 체크 |
| 외부 도구 연동 | 자동 생성된 `.env` + 검증 + 가이드 |
| PM 자동화 | 20+ AI PM 프로파일 — 산업×전문 매트릭스에서 선택 |
| 기존 코드 현대화 | GitHub repo 연결 → 진단 → Linear 자동 등록 (MVP-2-A) |
| 보안 | **ZIP-first** — 코드는 사용자 로컬에만 존재. 클라우드는 설계 메타만 보관 |

---

## 3. 두 가지 진입점

대시보드 메인에서 두 카드 중 선택:

```
┌────────────────────────────────────────────────────┐
│  ✨ 새 솔루션 위저드                                  │
│     "AI 가 솔루션을 처음부터 설계합니다"               │
│                                       [솔루션 설계 →] │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│  🔧 기존 코드 현대화 [BETA]                          │
│     "GitHub 저장소를 분석해 현대화 작업을 자동 등록"   │
│                                       [저장소 연결 →] │
└────────────────────────────────────────────────────┘
```

- **신규 솔루션** — 0 에서 시작. "이런 시스템이 필요해" 라는 자연어로 솔루션 설계.
- **Modernize** — 이미 있는 코드. GitHub repo → 진단 → 시나리오(VersionUp/Refactor/LanguageMigrate) → Linear 자동 등록.

---

## 4. 사용 안내 ① — 신규 솔루션 (7-Step 위저드)

대시보드 → "솔루션 설계 시작" → `/solutions/new`

총 12 단계 (사용자 입력 9 단계 + 자동 진행 3 단계).
브라우저 평균 소요: 5~10 분.

### Step 0. 회사 정보

| 입력 | 예시 |
|---|---|
| 회사명 | "Acme Corp" |
| 회사 규모 | 1인 / 소규모 / 중소 / 중견 / 대기업 |
| 업종 | IT / 핀테크 / 커머스 / 헬스케어 / 교육 / 제조 / 물류 / 마케팅 / 게임 / 기타 |
| 비즈니스 유형 | B2B / B2C / B2B2C / 사내 |
| 주력 제품 | 자유 입력 |
| 솔루션 요청 | "자동화된 채용 관리 시스템이 필요합니다." 같은 자연어 |

### Step 1. 솔루션 생성 (자동)

AI 가 회사정보 + 요청을 분석해 **솔루션 프로토타입 후보 N 개** 생성. 약 20~40 초.

### Step 2. 프로토타입 선택

생성된 후보 카드들을 비교 → 1 개 선택.
각 카드: 솔루션 타입, 핵심 컴포넌트, 예상 효과.

### Step 3. PM 추천 (자동)

선택한 프로토타입에 가장 어울리는 **AI PM (Project Manager) 후보 3~5 명** 추천.

각 PM 은:
- 도메인 전문 (예: "이커머스 PM", "핀테크 PM", "B2B SaaS PM")
- 산업 태그
- 추천 점수 + 사유

### Step 4. PM 선택

PM 카드 1 개 선택. 별점 / 도메인 / 산업 표시.

### Step 5. PM 구성 확인

선택한 PM 이 데려오는 **기본 팀** 검토:
- 에이전트 N 명 (백엔드/프론트엔드/UI-UX 등)
- 스킬 N 개 (Linear, GitHub, Notion, TDD, ...)
- MCP 서버 N 개
- Hook N 개

### Step 6. 에이전트 (사용자 선택)

PM 기본 팀에 더해 자유 추가/변경.

**티켓 소스 필수** (Linear / Notion 중 1 개). PM 이 이미 잠근 경우 단일 선택 자동 보장.

### Step 7. 플랫폼

| 플랫폼 | 비고 |
|---|---|
| **Claude Code** | Anthropic. 가장 강력. (기본) |
| **Gemini CLI** | Google. |
| **Codex** | OpenAI. |
| **Cursor** | IDE 통합형. |

선택한 플랫폼에 맞춰 `.claude/` / `.gemini/` / `.cursor/` 구조로 ZIP 생성.

### Step 8. OS 환경

실행 환경 선택 (WSL2 / Linux / macOS).

### Step 9. 환경변수 (API 키)

- `ANTHROPIC_API_KEY` (필수, "나중에 입력" 옵션)
- `LINEAR_API_KEY` + `LINEAR_TEAM_ID` (Linear 선택 시)
- `NOTION_API_KEY` + `NOTION_DATABASE_ID` (Notion 선택 시)
- 그 외 스킬별 키

**라이브 검증** — Linear/Notion 키는 입력 즉시 실제 API 호출로 인증 확인. 잘못된 키는 다음 단계 차단.

**한글/이모지 자동 차단** — input onChange 단계에서 비-ASCII 즉시 제거. 사고 방지.

### Step 10. ROI 비교 (자동)

기존 인력 비용 vs ClickEye 도입 비용 → 예상 절감액 + 절감률 계산.

### Step 11. 최종 확인

설정 요약 카드 + "이대로 진행" 클릭 → 프로젝트 생성 + ZIP 다운로드.

### 산출 ZIP 구조

```
my-project.zip
├── .claude/                    # Claude Code 가 읽는 설정
│   ├── agents/                 # 선택한 에이전트별 .md
│   ├── commands/               # 슬래시 커맨드
│   │   ├── ClickEyeStart.md
│   │   └── ClickEyeRemove.md
│   └── skills/                 # 선택한 스킬 .md
├── scripts/                    # 자동화 스크립트
│   ├── auto_dev_pipeline.sh    # 멀티 Agent 자동 개발 흐름
│   ├── harness-gate.sh         # lint/type/test Gate
│   ├── linear_tracker.py       # Linear API 통합
│   └── webhook_server.py       # Linear webhook 수신
├── docs/                       # 사용자 가이드
│   ├── setup-guide.pptx
│   └── api-keys/
├── .env.example                # 환경변수 템플릿
├── CLAUDE.md                   # Claude 시스템 가이드
└── README.md                   # 1-pager 실행 가이드
```

---

## 5. 사용 안내 ② — 기존 코드 현대화 (Modernize, MVP-2-A)

대시보드 → "저장소 연결하기" → `/solutions/modernize/new`

> **사용 사례**: 사내에 5년 된 Django 3.2 + Python 3.8 모놀리스가 있다. EOL 대응이 필요한데 어디부터 손대야 할지 모르겠다.

### Step 0. GitHub 연결

- "GitHub 연결" 버튼 → ClickEye GitHub App 설치 (private repo 지원)
- 최소 권한: Contents (read), Metadata (read), Pull requests (read)
- 설치 완료 시 자동으로 다음 단계 진입

### Step 1. 저장소 선택

설치된 repo 목록에서 선택 → branch 선택 (default branch 추천).
> 24 시간 캐시 — 즉시 응답.

### Step 2. 코드 진단 (자동)

ClickEye 백엔드가 7 단계 분석:

```
1. clone        (--depth=1, installation token)
2. scan         확장자 분포 → 사용 언어 비중
3. manifest     pyproject.toml / package.json / go.mod / Dockerfile 파싱
4. outdated     pypi / npm registry 호출 → 버전 차이
5. sample       entry-point 코드 스니펫 수집 (≤ 80k tokens)
6. LLM summary  Claude 가 코드베이스 진단 요약 markdown 생성
7. cleanup      /tmp 워크스페이스 즉시 삭제 (코드 비보관)
```

소요: 30~90 초. 진행률 + 단계 체크리스트 실시간 표시.

### Step 3. 진단 검토

화면 구성:
- **감지된 스택** chip — `python 78%`, `typescript 12%`, ...
- **프레임워크/런타임** — `django: 3.2.18`, `python: 3.8`
- **위험 플래그** — 🚨 `python_eol_3_8`
- **AI 진단 요약** (접이식 markdown)
- **시나리오 선택** (라디오):
  - `VersionUp` — 버전 업그레이드 + EOL 대응 (MVP-2-A 우선)
  - `Refactor` — 코드 스멜 / 레이어링 정리 (MVP-2-B)
  - `LanguageMigrate` — 스택 전환 (MVP-2-C)
- **권장사항 카드 N 건** — 각 카드 체크박스 + risk/effort/우선순위 표시

각 권장안은 다음을 포함:
- 제목 (예: "Django 3.2 → 5.0 업그레이드")
- 근거 (markdown)
- before/after (current/latest 버전)
- breaking changes 리스트
- AI 작업 지시 (`prompt_md`)

### Step 4. 최종 확인 (finalize)

"Linear 자동 등록 + ZIP 다운로드" 한 번 클릭으로:

```
1. 선택된 권장안 priority 정렬
2. Linear 부모 이슈 생성 ("Modernize: acme/api (versionup)")
3. 각 권장안마다 Linear 자식 이슈 생성 (parent 연결)
4. ZIP 빌드
   ├── .clickeye/linear-issues.json  (이슈 매핑)
   ├── .ralph/tasks/<CE-101>.md       (AI 작업 지시)
   ├── docs/diagnosis.md / .json       (분석 결과)
   └── MODERNIZE_README.md             (실행 가이드)
5. ZIP 자동 다운로드 (브라우저 fetch + blob)
```

### 산출 ZIP 사용

```bash
unzip modernize_acme_api_<session>.zip
cp .env.example .env   # LINEAR_API_KEY / ANTHROPIC_API_KEY 입력

# (별도 ClickEye 솔루션 ZIP 의 auto_dev_pipeline.sh 와 결합 시)
bash scripts/auto_dev_pipeline.sh
```

→ Linear 이슈가 `DayQueued` → `In Progress` 로 자동 전이되고 AI 가 각 이슈마다 PR 생성.

---

## 6. 동작 원리 — 클라우드 + 로컬 하이브리드 아키텍처

ClickEye 는 **두 레이어** 로 동작합니다:

```
┌──────────────────────────────────────────────────────┐
│  ☁  Cloud Control Plane (clickeye-web + clickeye-api)│
│   ├─ 솔루션 설계 위저드                                │
│   ├─ 카탈로그 (Agent / Skill / MCP / PM)              │
│   ├─ ZIP 생성 엔진                                    │
│   ├─ 라이센스 관리                                    │
│   └─ Modernize 진단 (코드 클론은 휘발성)               │
└────────────────┬─────────────────────────────────────┘
                 │  ZIP 다운로드 (1 회)
                 ▼
┌──────────────────────────────────────────────────────┐
│  💻 Customer Execution Plane (사용자 로컬 PC / 서버)  │
│   ├─ 다운받은 ZIP 압축 해제                            │
│   ├─ .claude/ 또는 .gemini/                          │
│   ├─ .env (API 키 — 사용자 머신에만 존재)              │
│   ├─ scripts/auto_dev_pipeline.sh                    │
│   └─ Agent 플랫폼 실행 (claude / gemini / ...)        │
└──────────────────────────────────────────────────────┘
```

### 보안 핵심

| 데이터 | 위치 |
|---|---|
| 사용자 소스 코드 (Modernize 분석 시) | **클라우드 메모리만, 즉시 삭제** — DB 비저장 |
| Anthropic / Linear / Notion API 키 | **사용자 로컬 `.env` 만** |
| 솔루션 설계 메타 (회사명, 선택 카탈로그) | 클라우드 DB |
| 분석 요약 (markdown) | 클라우드 DB (선택적, 사용자 동의) |
| AI 가 생성한 코드 | **사용자 로컬 PC** |

> 비교: ClickEye 는 GitHub Self-hosted Runner 와 유사 아키텍처 — **클라우드는 오케스트레이션, 실행은 고객 서버**.

### Webhook 통합 (선택)

사용자가 로컬에서 webhook 서버 + ngrok 을 띄우면 Linear 이슈 상태 변경 시 자동 트리거:

```
Linear (DayQueued)
   ↓ webhook
사용자 로컬 webhook_server.py
   ↓
auto_dev_pipeline.sh 자동 실행
   ↓
AI 가 이슈 1건 → PR 1개
```

### Cloud Control Plane 기술 스택

- **Frontend**: Next.js 15 (App Router) + TypeScript + Tailwind + Zustand + TanStack Query
- **Backend**: FastAPI 0.115 + Python 3.12 + SQLAlchemy 2.0 (async) + Alembic + PostgreSQL + Redis
- **AI**: Anthropic Claude (Opus 4.7 / Sonnet 4.6 / Haiku 4.5) + Google Gemini + OpenAI Codex

---

## 7. AI 자동 개발 흐름 (ZIP 풀고 실행)

ZIP 안 `scripts/auto_dev_pipeline.sh` 가 실행되면:

```
사용자: bash scripts/auto_dev_pipeline.sh
                ↓
[Linear watcher] DayQueued 이슈 1건 감지
                ↓
[Claude 메타프롬프트] PLAN.md + .ralph/refined/ 생성 (관측형 사전 정제: 요구분석·범위·수용기준·리스크)
                ↓
[Claude Code] 코드 작성 → TASK.md
   ├─ 브랜치 자동 생성 (fix/{ISSUE}/{slug})
   ├─ 하네스 4단계 (Router → Context → Loop → Worker)
   └─ harness-gate.sh (lint / type / test) 매 커밋 검증
                ↓
[Codex] REVIEW.md (요구충족 / 리스크 / 테스트 부족 / PR 코멘트)
                ↓
[거버넌스 게이트] pre_merge_gate.py — 머지 직전 정합성·위험 검증 (HIGH-tier→PR 강등)
                ↓
[Linear] 상태 자동 전이 In Progress → Done
                ↓
[GitHub] PR 생성 (Linear URL + 변경요약 자동 포함)
                ↓
[Telegram] 알림 (선택)
```

### 멀티 Agent 의 역할

| Agent | 모델 | 역할 | 결과물 |
|---|---|---|---|
| **Claude (메타프롬프트)** | Sonnet | 기획(관측형 사전 정제) | `PLAN.md` + `refined/` |
| **Claude** | Sonnet 4.6 | 구현 | `TASK.md` + 코드 |
| **Codex** | gpt-5 (예) | QA | `REVIEW.md` |
| _Gemini (폴백)_ | gemini-2.5 (예) | 레거시 기획 | `FLOWOPS_METAPROMPT=false` 시 |

각 단계는 `FLOWOPS_*` 환경변수로 ON/OFF. 머지 직전 거버넌스 게이트(`pre_merge_gate.py`)가 정합성·위험을 최종 검증.

---

## 8. 멀티 Agent 플랫폼 지원

ClickEye 가 만드는 ZIP 은 어느 플랫폼에서도 동작:

| 플랫폼 | 진입 명령 | ZIP 안 구조 |
|---|---|---|
| Claude Code | `claude` | `.claude/agents/`, `.claude/skills/`, `CLAUDE.md` |
| Gemini CLI | `gemini` | `.gemini/agents/`, `GEMINI.md` |
| Codex | `codex` | `.codex/`, `CODEX.md` |
| Cursor | Cursor IDE 열기 | `.cursor/rules/`, `CURSOR.md` |

> **동일한 위저드 입력** → **플랫폼별 최적화 ZIP**.

---

## 9. 경쟁사 대비 차별점

| 항목 | GitHub Copilot Workspace | Devin | Sweep | **ClickEye** |
|---|---|---|---|---|
| 실행 위치 | GitHub Cloud | 자체 Cloud | GitHub Cloud | **사용자 로컬 (ZIP-first)** |
| 코드 외부 유출 | O | O | O | **X** |
| AI 토큰 비용 | 플랫폼 부담 (요금 inc) | 플랫폼 부담 | 플랫폼 부담 | **사용자 부담 (BYOK)** |
| 한국 도구 통합 | △ Linear | △ | △ | **O Linear + Notion + Telegram** |
| 위저드 UX | 단순 | CLI 중심 | 이슈 단위 | **7-Step 시각화** |
| PM AI | X | X | X | **O (20+ 프로파일)** |
| 기존 코드 현대화 | △ | O | O | **O (VersionUp 우선)** |
| 멀티 플랫폼 ZIP | X | X | X | **O (4 종)** |
| 가격 | $30+/월 | $500/월 | $50+/월 | **Free/Pro 추후 검증** |

### ClickEye 만의 강점

1. **ZIP-first 보안** — 코드가 ClickEye 클라우드에 영구 저장되지 않음. Modernize 의 분석조차 메모리만 사용.
2. **한국 시장 친화** — Linear 워크플로 (`DayQueued`/`NightQueued`/`Confirm`), Notion 통합, Telegram 알림, 한국어 PM/Agent 카탈로그.
3. **BYOK** — Anthropic / Google / OpenAI 토큰은 사용자가 직접 관리. 토큰 비용 투명.
4. **하네스 엔지니어링** — AI 코드 작성을 4 단계로 통제 (환각/오류 사전 차단). `harness-gate.sh` 가 매 커밋 lint/type/test 검증.
5. **멀티 Agent + 거버넌스** — Claude 메타프롬프트(기획) → Claude(구현) → Codex(QA) → 머지 직전 거버넌스 게이트(정합성·위험). (Gemini 기획은 폴백)

---

## 10. 보안 / 라이센스 / 가격

### 보안 보장

| 영역 | 보장 |
|---|---|
| 소스 코드 | ZIP 다운로드 후에는 사용자 로컬에만 존재 |
| API 키 | 사용자 로컬 `.env` 만. ClickEye 서버는 받지 않음 (Linear 자격증명 저장 옵션 제외) |
| Modernize 분석 | `/tmp/modernize/<session>/` → Step 7 종료 직후 `shutil.rmtree` |
| GitHub 접근 | App installation token (1h 유효, 자동 회전), 최소 권한 (read-only) |
| Linear 자격증명 | `app/core/crypto.py` Fernet 암호화 후 DB 저장 (선택) |
| Webhook | HMAC-SHA256 서명 검증 (`X-Hub-Signature-256`) |

### 라이센스 모델

| 항목 | Free | Pro | Enterprise |
|---|---|---|---|
| 프로젝트 수 | 1 | 5 | Unlimited |
| Agent 연결 | 1 | 3 | Unlimited |
| 카탈로그 (Agent/Skill/MCP) | 기본 | 전체 | 전체 + 커스텀 |
| 동시 티켓 | 1 | 10 | Unlimited |
| 기술 지원 | 커뮤니티 | 이메일 | 전담 |
| 가격 | **무료** | TBD/월 | TBD/월 |

> 가격은 시장 검증 후 결정. Modernize 베타는 화이트리스트 가입 후 무료.

### 비용 구조

```
사용자 비용 = ClickEye 라이센스 (월) + Anthropic/OpenAI 토큰 (사용량)

[ClickEye 라이센스]
  └─ 카탈로그 사용권, 클라우드 진단, ZIP 생성, 기술 지원

[AI 토큰 — BYOK]
  └─ 사용자가 직접 관리. ClickEye 가 위에 마진 안 붙임. 투명.
```

---

## 11. 데모 시연 가이드

### 사전 준비 (발표자)

```bash
# 1. dev 서버 두 개 기동
cd /mnt/c/workspace/ClickEye/clickeye-web && npm run dev   # 3000
cd /mnt/c/workspace/ClickEye/clickeye-api && uv run uvicorn app.main:app --reload --port 8000

# 2. webhook + ngrok (선택)
bash scripts/webhook-doctor.sh

# 3. .env 확인
echo $ANTHROPIC_API_KEY | head -c 20
```

### 시연 시나리오 ① — 신규 솔루션 (5 분)

1. 대시보드 → "솔루션 설계 시작"
2. Step 0~11 차례 진행 (회사: 데모, 솔루션: "고객 채팅봇")
3. 환경변수 — "나중에 입력" 시연
4. ZIP 다운로드 → 압축 해제
5. ZIP 안 구조 보여주기 (`.claude/agents/`, `scripts/`, `.env.example`)

### 시연 시나리오 ② — Modernize (7 분)

1. 대시보드 → "기존 코드 현대화 BETA" 카드
2. GitHub App 설치 (사전 등록된 demo App 사용)
3. repo 선택 (사전 준비된 EOL Django repo)
4. 진단 자동 진행 (실측 30~60 초) — 진행률 체크리스트 보여주기
5. 진단 검토 — chip / risk_flags / 권장 카드
6. "Linear 자동 등록 + ZIP 다운로드"
7. Linear UI 에서 신규 이슈 N 개 확인

### 시연 시나리오 ③ — 자동 개발 (선택, 10 분)

ZIP 풀고 `bash scripts/auto_dev_pipeline.sh` 실행 → Linear 이슈가 In Progress → AI 가 PR 생성하는 흐름 라이브 시연. **사전 녹화 추천** (실시간은 변수 많음).

### 자주 받는 질문 준비

1. "코드를 외부로 보내지 않는다는 게 확실한가?"
   → Modernize 의 분석 워크스페이스가 Step 7 직후 `shutil.rmtree` 로 삭제됨. 분석 메타만 DB 영속.

2. "Claude / Gemini / Codex 중 뭐가 제일 좋나?"
   → 작업 성격별 권장. Claude = 구현, Gemini = 기획·long-context, Codex = QA. ClickEye 는 셋 다 동시 사용 가능.

3. "기존 사내 GitHub Enterprise 도 지원되나?"
   → MVP-2-A 는 github.com 만. GHE 는 MVP-2-D 로드맵.

4. "기존 Jenkins / GitLab CI 와 충돌 안 하나?"
   → ClickEye 는 코드 작성까지만 담당. 빌드/배포는 기존 CI 그대로.

---

## 12. FAQ

### Q1. 처음 시작하는 데 얼마나 걸리나요?
> 위저드 5 분 + ZIP 다운로드 즉시 + 로컬 첫 실행 5 분 = **~10 분**.

### Q2. AI 가 작성한 코드의 품질은 어떻게 보장되나요?
> ZIP 안 `harness-gate.sh` 가 매 커밋마다 lint + type + test 를 자동 실행. 실패 시 커밋 차단.

### Q3. 우리 회사 사내 도구 (Jira, Confluence) 연동도 가능한가요?
> 현재 Linear / Notion 우선. Jira / Confluence 는 카탈로그 추가 예정. Enterprise 플랜에서 커스텀 스킬 작성 지원.

### Q4. Anthropic 토큰 비용이 얼마나 드나요?
> 사용량 의존. 평균 신규 위저드 1 회 = $0.5~$2, Modernize 분석 1 회 = $1~$5 (코드베이스 크기). 자동 개발 단계는 작업당 $0.5~$10.

### Q5. 오프라인 (인터넷 없는 환경) 에서 동작하나요?
> ZIP 다운로드 후 로컬 실행은 인터넷 필요 (Anthropic / Linear API 호출). 완전 오프라인은 Enterprise 플랜에서 별도 검토.

### Q6. 기존 코드 현대화 (Modernize) 의 권장안은 얼마나 정확한가요?
> VersionUp 시나리오는 deterministic — pypi/npm 의 최신 버전과 outdated 자동 감지. LLM 은 위에 우선순위 + breaking changes 분석을 더함. Refactor / LanguageMigrate 는 LLM 의존도 높아 사용자 검토 필수.

### Q7. 다른 AI 도구 (Claude Code, Gemini CLI) 를 이미 쓰고 있는데 ClickEye 가 추가로 무엇을 주나요?
> 통합 환경 + 자동화. 개별 AI 도구는 도구만. ClickEye 는 도구 + 멀티 Agent 오케스트레이션 + Linear 연동 + 자동 PR 생성 + 진단 + 멀티 플랫폼 ZIP 까지 통합 패키지.

### Q8. 라이센스 위반이 의심되면 어떻게 하나요?
> Pro/Enterprise 라이센스에는 audit log + 사용량 모니터링. 위반 발견 시 정지·환불 정책 (라이센스 약관에 명시 예정).

---

## 부록 A — 핵심 문서 링크

| 문서 | 위치 |
|---|---|
| 마스터 로드맵 | `LoadMap_v3.md` |
| 아키텍처 상세 | `docs/architecture-overview.md` |
| Agent 프로토콜 | `docs/agent-protocol.md` |
| CLI 가이드 | `docs/cli-guide.md` |
| 자동화 파이프라인 | `docs/pipeline-guide.md` |
| 경쟁사 비교 | `docs/comparison.md` |
| 라이센스 모델 | `docs/license-model.md` |
| Modernize GitHub App 설정 | `docs/modernize-github-app-setup.md` |
| 회귀 체크리스트 | `docs/modernize-regression-checklist.md` |

## 부록 B — 한 줄 핵심 메시지 (발표용)

> **"ClickEye 는 AI 개발을 위한 '설계 도구 + ZIP-first 배포 + 자기 자신을 발전시키는 자동화 파이프라인' 의 종합 솔루션입니다."**

세 가지 키워드:
1. **5 분 설계** — 브라우저 위저드 → ZIP
2. **로컬 실행** — 코드 외부 유출 없음
3. **자율 진화** — Linear → 멀티 Agent → PR (사용자 부재 중에도 진행)
