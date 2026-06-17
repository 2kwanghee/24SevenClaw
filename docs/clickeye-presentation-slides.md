<!--
ClickEye 발표 슬라이드 (Marp markdown)

빌드 방법:
  1. VSCode Marp 확장:
     - 우상단 "Export slide deck..." → PDF / PPTX / HTML
  2. CLI:
     npx @marp-team/marp-cli docs/clickeye-presentation-slides.md --pdf
     npx @marp-team/marp-cli docs/clickeye-presentation-slides.md --pptx

발표 시간: 45 분 (33 슬라이드, 페이지당 평균 1~2 분)
-->

---
marp: true
theme: default
paginate: true
size: 16:9
header: 'ClickEye — AI 개발 자동화 솔루션 빌더'
footer: '© 2026 ClickEye · Confidential'
style: |
  section {
    background: linear-gradient(135deg, #fafafa 0%, #f4f4f5 100%);
    font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif;
    color: #18181b;
  }
  section.title {
    background: linear-gradient(135deg, #18181b 0%, #404040 100%);
    color: white;
    justify-content: center;
    text-align: center;
  }
  section.title h1 {
    font-size: 4em;
    margin-bottom: 0.3em;
  }
  section.title p {
    font-size: 1.6em;
    opacity: 0.85;
  }
  section h1 { color: #18181b; border-bottom: 4px solid #18181b; padding-bottom: 0.3em; }
  section h2 { color: #27272a; }
  section.section-divider {
    background: #18181b;
    color: white;
    justify-content: center;
    text-align: center;
  }
  section.section-divider h1 {
    color: white;
    border-bottom: none;
    font-size: 3em;
  }
  code { background: #e4e4e7; padding: 0.1em 0.3em; border-radius: 4px; }
  pre code { background: #18181b; color: #fafafa; padding: 1em; border-radius: 8px; }
  table { font-size: 0.85em; margin: 0 auto; }
  table th { background: #18181b; color: white; }
  table td, table th { padding: 0.5em 0.8em; }
  blockquote {
    border-left: 4px solid #18181b;
    background: #f4f4f5;
    padding: 0.6em 1em;
    font-style: italic;
  }
  .center { text-align: center; }
  .big { font-size: 1.5em; }
  .small { font-size: 0.85em; }
  .highlight { background: linear-gradient(180deg, transparent 60%, #fef08a 60%); padding: 0 0.2em; }
  .badge {
    display: inline-block;
    padding: 0.2em 0.6em;
    border-radius: 999px;
    background: #18181b;
    color: white;
    font-size: 0.7em;
    font-weight: 600;
  }
---

<!-- _class: title -->

# ClickEye

브라우저 5 분 설계 → ZIP → AI 자율 개발

<br>

<p style="font-size: 1em; opacity: 0.7;">
2026 · AI 개발 자동화 솔루션 빌더
</p>

---

<!-- _class: section-divider -->

# Why ClickEye?

---

# 현장에서 자주 듣는 이야기

<br>

> "Claude Code 좋다는데 막상 도입하려니..."

<br>

- 🤔 **AI 플랫폼 선택** — Claude / Gemini / Codex / Cursor 중 어떤 거?
- 🗂 **에이전트·도구 구조** — `.claude/agents/` 어떻게 잡지?
- 🔗 **외부 도구 연동** — Linear / Notion / Slack 매번 새로 짜야?
- 👤 **PM 역할** — 일정·우선순위 관리할 AI 가 있나?
- 🔧 **레거시 대응** — Python 3.8 → 3.12 어디부터?
- 🔒 **보안** — 우리 코드 외부 클라우드에 보내고 싶지 않은데

---

# ClickEye 가 답한다

<br>

| Pain | 해결 |
|---|---|
| AI 플랫폼 선택 | 위저드에서 **4 종 중 선택** (Claude / Gemini / Codex / Cursor) |
| 에이전트·구조 | **카탈로그 체크박스** (Agent 7 · Skill 18 · MCP · Hook · Pipeline) |
| 외부 도구 연동 | **자동 생성된 `.env`** + 라이브 검증 |
| PM 자동화 | **20+ AI PM 프로파일** (산업×전문 매트릭스) |
| 기존 코드 현대화 | **GitHub repo → 진단 → Linear 자동 등록** |
| 보안 | **ZIP-first** — 코드는 사용자 로컬에만 |

---

<!-- _class: section-divider -->

# 한 줄 핵심

---

# <span class="highlight">5 분 설계 → ZIP → AI 자율 개발</span>

<br>

| 단계 | 사용자가 하는 일 | 시간 |
|------|---|---|
| ① 설계 | 브라우저 12단계 위저드 | **5~10 분** |
| ② 다운로드 | ZIP 1 개 | **1 클릭** |
| ③ 실행 | 로컬 `bash start.sh` | **수분 내 자동 시작** |
| ④ 결과 | AI 가 코드 작성 + Linear 이슈 + PR 자동 | **사용자 부재 중 진행** |

<br>

> 기존: 환경 설정·도구 통합·프롬프트 작성에 **수시간~수일**
> ClickEye: 위저드 → ZIP → 실행 → **즉시 AI 가 일을 시작**

---

# 두 가지 진입점

<br>

```
┌────────────────────────────────────────────────────┐
│  ✨ 새 솔루션 위저드                                  │
│     "AI 가 솔루션을 처음부터 설계합니다"               │
│                                       [솔루션 설계 →] │
└────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────┐
│  🔧 기존 코드 현대화  [BETA]                         │
│     "GitHub 저장소를 분석해 현대화 작업을 자동 등록"   │
│                                       [저장소 연결 →] │
└────────────────────────────────────────────────────┘
```

<br>

- **신규** — 0 에서 시작. "이런 시스템이 필요해" 라는 자연어로 설계
- **Modernize** — 이미 있는 코드. GitHub → 진단 → Linear 자동 등록 (MVP-2-A)

---

<!-- _class: section-divider -->

# 사용 안내 ①
## 신규 솔루션 12단계 위저드

---

# 위저드 12 단계 (5~10 분)

```
[Step 0]  회사 정보 — 회사명, 규모, 업종, 비즈니스 유형
[Step 1]  솔루션 생성 (자동) — AI 가 프로토타입 후보 N 개 생성
[Step 2]  프로토타입 선택 — 후보 카드 비교 → 1 개 선택
[Step 3]  PM 추천 (자동) — AI 가 최적 PM 후보 3~5 명 추천
[Step 4]  PM 선택 — 카드 1 개 (별점 · 도메인 · 산업)
[Step 5]  PM 구성 확인 — 기본 팀 (Agent · Skill · MCP · Hook)
[Step 6]  에이전트 — 사용자 자유 추가/변경 (티켓 소스 필수)
[Step 7]  플랫폼 — Claude / Gemini / Codex / Cursor
[Step 8]  OS — WSL2 / Linux / macOS
[Step 9]  환경변수 — API 키 (라이브 검증)
[Step 10] ROI 비교 (자동) — 절감 예상 계산
[Step 11] 최종 확인 → ZIP 다운로드
```

---

# ZIP 산출물 트리

```
my-project.zip
├── .claude/                    # Claude Code 가 읽는 설정
│   ├── agents/                 # 선택한 에이전트별 .md
│   ├── commands/               # 슬래시 커맨드
│   └── skills/                 # 선택한 스킬 .md
├── scripts/
│   ├── auto_dev_pipeline.sh    # 멀티 Agent 자동 개발
│   ├── harness-gate.sh         # lint/type/test Gate
│   ├── linear_tracker.py       # Linear API
│   └── webhook_server.py       # Linear webhook 수신
├── docs/
│   ├── setup-guide.pptx
│   └── api-keys/
├── .env.example                # 환경변수 템플릿
├── CLAUDE.md                   # Claude 시스템 가이드
└── README.md                   # 1-pager 실행 가이드
```

---

<!-- _class: section-divider -->

# 사용 안내 ②
## 기존 코드 현대화 (Modernize)
### <span class="badge">MVP-2-A</span>

---

# Modernize 위저드 5 단계

<br>

```
[Step 0]  GitHub 연결         GitHub App 설치 (private repo 지원, 최소 권한)
[Step 1]  저장소 선택         설치된 repo 목록에서 선택 + branch
[Step 2]  코드 진단 (자동)    7-step 분석 pipeline (30~90 초)
[Step 3]  진단 검토           스택 chip + AI 요약 + 시나리오 + 권장 카드
[Step 4]  최종 확인           "Linear 자동 등록 + ZIP 다운로드" 한 번 클릭
```

<br>

> **사용 사례**: 5 년 된 Django 3.2 + Python 3.8 모놀리스의 EOL 대응을 어디부터 시작할지 모를 때

---

# 7-Step 분석 Pipeline (백엔드)

```
1. clone        (--depth=1, App installation token)
2. scan         확장자 분포 → 언어 비중 ("python 78%, ts 12%")
3. manifest     pyproject.toml / package.json / go.mod / Dockerfile 파싱
4. outdated     pypi / npm registry 호출 → 버전 차이 + EOL 플래그
5. sample       entry-point 코드 스니펫 수집 (≤ 80k tokens)
6. LLM summary  Claude 가 진단 요약 markdown 생성
7. cleanup      /tmp 워크스페이스 즉시 삭제 (코드 비보관)
```

<br>

> 🔒 **보안**: 원본 코드는 클라우드 메모리에만, Step 7 직후 `shutil.rmtree`. DB 에는 **분석 메타만** 영속.

---

# 진단 검토 UI

<br>

**감지된 스택** — `python 78%` · `typescript 12%` · ...
**프레임워크** — `django: 3.2.18` · `python: 3.8`
**🚨 위험 플래그** — `python_eol_3_8`

<br>

**시나리오 라디오**

| 시나리오 | 설명 | 상태 |
|---|---|---|
| **VersionUp** | 패키지 + EOL 런타임 업그레이드 | ✅ MVP-2-A |
| Refactor | 코드 스멜 / 레이어링 / 데드코드 | MVP-2-B |
| LanguageMigrate | 스택 전환 (Express → FastAPI 등) | MVP-2-C |

<br>

**권장사항 카드** — 각 카드 체크박스 · risk · effort · priority · breaking changes

---

# finalize — 한 번의 클릭

<br>

```
"Linear 자동 등록 + ZIP 다운로드"
        ↓
1. 선택된 권장안 priority 정렬
2. Linear 부모 이슈 생성 ("Modernize: acme/api (versionup)")
3. 각 권장안마다 Linear 자식 이슈 (parent 연결)
4. ZIP 빌드
   ├── .clickeye/linear-issues.json      (이슈 매핑)
   ├── .ralph/tasks/<CE-101>.md           (AI 작업 지시 markdown)
   ├── docs/diagnosis.md / .json          (분석 결과)
   └── MODERNIZE_README.md                (1-pager 실행 가이드)
5. ZIP 자동 다운로드 (브라우저 fetch + blob)
```

---

<!-- _class: section-divider -->

# 데모 시연

---

# 라이브 데모

<br>

### 1. 신규 솔루션 (5 분)
- 회사: "데모"
- 솔루션 요청: "고객 채팅봇"
- 12-step 완주 → ZIP 다운로드

<br>

### 2. Modernize (7 분)
- 사전 준비된 demo App 으로 GitHub 연결
- EOL Django repo 선택
- 진단 → 권장 카드 → finalize → Linear UI 확인

<br>

<p class="small center">시연 영상 백업 준비됨</p>

---

<!-- _class: section-divider -->

# 동작 원리

---

# Cloud + Local 하이브리드 아키텍처

```
┌──────────────────────────────────────────────────────┐
│  ☁  Cloud Control Plane  (clickeye-web + clickeye-api)│
│   ├─ 솔루션 설계 위저드                                │
│   ├─ 카탈로그 (Agent / Skill / MCP / PM)              │
│   ├─ ZIP 생성 엔진                                    │
│   ├─ 라이센스 관리                                    │
│   └─ Modernize 진단 (코드 클론은 휘발성)               │
└────────────────┬─────────────────────────────────────┘
                 │  ZIP 다운로드 (1 회)
                 ▼
┌──────────────────────────────────────────────────────┐
│  💻 Customer Execution Plane  (사용자 로컬 PC / 서버) │
│   ├─ 다운받은 ZIP 압축 해제                            │
│   ├─ .claude/ 또는 .gemini/                          │
│   ├─ .env (API 키 — 사용자 머신에만)                  │
│   ├─ scripts/auto_dev_pipeline.sh                    │
│   └─ Agent 플랫폼 실행 (claude / gemini / ...)        │
└──────────────────────────────────────────────────────┘
```

---

# 데이터가 어디에 사는가

<br>

| 데이터 | 위치 |
|---|---|
| 사용자 소스 코드 (Modernize 분석 시) | <span class="highlight">**클라우드 메모리만**, 즉시 삭제</span> |
| Anthropic / Linear / Notion API 키 | **사용자 로컬 `.env`** |
| 솔루션 설계 메타 (회사명, 카탈로그) | 클라우드 DB |
| 분석 요약 (markdown) | 클라우드 DB (사용자 동의) |
| AI 가 생성한 코드 | <span class="highlight">**사용자 로컬 PC**</span> |

<br>

> GitHub Self-hosted Runner 와 유사 아키텍처
> **클라우드는 오케스트레이션 · 실행은 고객 서버**

---

# AI 자동 개발 흐름 (ZIP 실행 후)

```
사용자: bash scripts/auto_dev_pipeline.sh
                ↓
[Linear watcher] DayQueued 이슈 1건 감지
                ↓
[Claude 메타프롬프트] PLAN.md + refined 생성 (관측형 사전 정제)
                ↓
[Claude Code] 코드 작성 → TASK.md
   ├─ 브랜치 자동 생성 (fix/{ISSUE}/{slug})
   ├─ 하네스 4단계 (Router → Context → Loop → Worker)
   └─ harness-gate.sh (lint / type / test) 매 커밋 검증
                ↓
[Codex] REVIEW.md (요구충족 · 리스크 · 테스트 부족)
                ↓
[거버넌스 게이트] 머지 직전 정합성·위험 검증 (HIGH-tier→PR 강등)
                ↓
[Linear] 상태 자동 전이  In Progress → Done
                ↓
[GitHub] PR 생성 (Linear URL + 변경요약 자동)
                ↓
[Telegram] 알림 (선택)
```

---

# 멀티 Agent 합의

<br>

| Agent | 모델 | 역할 | 결과물 |
|---|---|---|---|
| **Claude (메타프롬프트)** | Sonnet | 기획·정제 | `PLAN.md` + `refined/` |
| **Claude** | Sonnet 4.6 | 구현 | `TASK.md` + 코드 |
| **Codex** | gpt-5 | QA | `REVIEW.md` |
| _Gemini_ | gemini-2.5 | 레거시 기획 폴백 | (`FLOWOPS_METAPROMPT=false`) |

<br>

> Claude 정제·구현 + Codex QA 후 **거버넌스 게이트**(정합성·위험)가 최종 검증해야 머지.
> **단일 AI 환각을 교차 검토 + 결정적 게이트로 차단한다.**

<br>

각 단계는 `FLOWOPS_*` 환경변수로 ON/OFF 가능 → 단계별 디버깅 / 점진 도입 용이

---

# 멀티 플랫폼 ZIP

<br>

| 플랫폼 | 진입 명령 | ZIP 안 구조 |
|---|---|---|
| Claude Code | `claude` | `.claude/agents/`, `CLAUDE.md` |
| Gemini CLI | `gemini` | `.gemini/agents/`, `GEMINI.md` |
| Codex | `codex` | `.codex/`, `CODEX.md` |
| Cursor | IDE 열기 | `.cursor/rules/`, `CURSOR.md` |

<br>

> **동일한 위저드 입력 → 플랫폼별 최적화 ZIP**

---

<!-- _class: section-divider -->

# 경쟁사 대비 차별점

---

# 경쟁사 비교

| 항목 | Copilot Workspace | Devin | Sweep | **ClickEye** |
|---|---|---|---|---|
| 실행 위치 | GitHub Cloud | 자체 Cloud | GitHub Cloud | <span class="highlight">**로컬 (ZIP-first)**</span> |
| 코드 외부 유출 | O | O | O | **X** |
| AI 토큰 비용 | 플랫폼 부담 | 플랫폼 부담 | 플랫폼 부담 | **사용자 BYOK** |
| 한국 도구 통합 | △ Linear | △ | △ | **O 한국 워크플로** |
| 위저드 UX | 단순 | CLI 중심 | 이슈 단위 | **12단계 시각화** |
| PM AI | X | X | X | **O (20+ 프로파일)** |
| 기존 코드 현대화 | △ | O | O | **O** |
| 멀티 플랫폼 ZIP | X | X | X | **O (4 종)** |
| 가격 | $30+/월 | $500/월 | $50+/월 | **Free / Pro TBD** |

---

# ClickEye 만의 강점 5 가지

<br>

1. 🔒 **ZIP-first 보안** — 코드가 클라우드에 영구 저장되지 않음
2. 🇰🇷 **한국 시장 친화** — Linear 워크플로 (`DayQueued`/`Confirm`) · Notion · Telegram · 한국어 PM
3. 💰 **BYOK** — Anthropic/Google/OpenAI 토큰 사용자가 직접 관리. **토큰 비용 투명**
4. 🛡 **하네스 엔지니어링** — AI 코드 작성 4 단계 통제 (환각/오류 사전 차단)
5. 🤝 **멀티 Agent + 거버넌스** — Claude 메타프롬프트(기획) → Claude(구현) → Codex(QA) → **머지 직전 거버넌스 게이트**(정합성·위험) (Gemini 기획은 폴백)

---

<!-- _class: section-divider -->

# 우리는 어떻게 이 도구를 만드는가?

---

# Dogfooding

<br>

> **"우리가 파는 자동화 도구를, 우리가 매일 쓰지 않으면 어떻게 고객에게 추천하겠는가?"**

<br>

ClickEye 의 모든 신규 기능은 **ClickEye 자체의 자동화 파이프라인** 으로 만들어집니다.

ZIP 안에 들어가는 `auto_dev_pipeline.sh` · `harness-gate.sh` 는 우리가 매일 실제로 사용하는 시스템의 패키지화.

---

# 개발 파이프라인 — Phase 0 ~ 4

```
사용자 요청 (Linear / 채팅)
        ↓
Phase 0  PM Agent (Opus)         복잡도 ≥ 0.7 시 호출
        ↓
Phase 1  Router (Sonnet)         모호→인터뷰 / 명확→Loop / 대화→응답
        ↓
Phase 2  Context Manager (Haiku) 필요한 파일만 선별 로딩
        ↓
Phase 3  Harness Loop (Sonnet)   WRITE_CODE → 자동검증 → 수정 (MAX 5회)
        ↓
Phase 4  Hook 게이트              PreToolUse / PostToolUse / Stop
        ↓
Linear 상태 전이 + PR 생성 + Telegram 알림
```

---

# 모델 라우팅

<br>

| 티어 | 모델 | 용도 | 비용 |
|---|---|---|---|
| 고급 사고 | **Opus 4.7** (1M context) | 계획 · 설계 · 트레이드오프 분석 | $$$$ |
| 표준 | **Sonnet 4.6** | 코드 작성 · 검증 · 리뷰 | $$ |
| 경량 | **Haiku 4.5** | 컨텍스트 선별 · 단순 분류 | $ |

<br>

> 결과: **토큰 비용 80% 절감** (Opus 만 쓸 때 대비)
> Opus 는 한 세션 시작 시 plan 작성에만 사용

---

# 하네스 엔지니어링 4 단계

<br>

| Stage | 모델 | 역할 |
|---|---|---|
| **1 Router** | sonnet | 사용자 의도 분석 — 모호/명확/대화 분류 |
| **2 Context** | haiku | 필요한 파일만 선별 (가림막 원칙) |
| **3 Loop** | sonnet | WRITE_CODE → lint/type/test → 수정 (MAX 5회) |
| **4 Worker** | 역할별 | WRITE / TEST / REVIEW / SECURITY 컨텍스트 분리 |

<br>

> **컨텍스트 분리 이유**: 같은 AI 가 코드를 쓰고 리뷰하면 자기 작품에 관대해진다.

---

# Plan Gate — `.claude/current-plan.md`

<br>

```markdown
## 목표
M5 — 코드 분석 엔진 7-step pipeline + diagnose UI

## 변경 파일 목록
- clickeye-api/app/services/modernize/*.py
- clickeye-web/src/components/.../step-modernize-diagnose.tsx

## 구현 단계
1. ...

## 예상 영향 범위
- 기존 /solutions/new 위저드 미변경

## STATUS: APPROVED   ← 사용자 승인 마커
```

<br>

> 모든 `Edit/Write` 도구 호출 전 **PreToolUse hook 이 STATUS: APPROVED 확인**.
> 즉흥 코드 작성 차단 + 사용자 동의 보장.

---

# Hook 시점 4 단계 자동 검증

<br>

| Hook | 역할 |
|---|---|
| `UserPromptSubmit` | 하네스 Router 지침 + TODO 리마인더 주입 |
| `PreToolUse(Edit\|Write)` | **Plan Gate 확인** (STATUS: APPROVED) |
| `PreToolUse(git commit)` | **harness-gate.sh** 실행 — 모듈별 lint/type/test |
| `PostToolUse(Edit\|Write)` | 검증 리마인더 ("Gate 미통과 시 커밋 차단 경고") |
| `Stop` | `ralph-stop-hook.sh` — fix_plan 완료 + 테스트 통과 확인 |

---

# harness-gate.sh — 모듈별 Gate

<br>

| 모듈 | Lint | Type | Test |
|---|---|---|---|
| `clickeye-api` | `ruff check .` | `mypy app/` | `pytest --tb=short -q` |
| `clickeye-web` | `npm run lint` | `tsc --noEmit` | — |
| `clickeye-agent` | `ruff check .` | `mypy agent/` | `pytest --tb=short -q` |
| `clickeye-contracts` | — | `tsc --noEmit` | — |

<br>

> 변경된 모듈만 자동 감지 → 해당 모듈 Gate 만 실행.
> docs/scripts 만 변경 시 Gate 건너뜀.

---

# 비침습성 회귀 검증 R-1 ~ R-7

<br>

| R# | 항목 | 자동화 |
|---|---|---|
| R-1 | 기존 위저드 E2E | 수동 + Playwright |
| **R-2** | ZIP 골든파일 | ✅ pytest |
| **R-3** | OpenAPI diff | ✅ openapi-diff |
| **R-4** | 카탈로그 변경 0 건 | ✅ shell script |
| **R-5** | wizard-store snapshot | ✅ vitest (77/77 통과) |
| **R-6** | Feature flag OFF | ✅ shell script |
| **R-7** | Alembic downgrade | ✅ python -m alembic |

<br>

> **매 PR 머지 전 통과 필수**. CI 통합.

---

# 실 증거 — Modernize MVP-2-A

본 파이프라인이 잘 동작한다는 실 증거. **8 마일스톤으로 완성**:

```
[✓] M1  Feature flag + wizard-store mode 분기
[✓] M2  백엔드 모델 5 종 + Alembic 039
[✓] M3  GitHub App 인프라 + install/callback/webhook
[✓] M4  진입 카드 + repo-connect/select step
[✓] M5  코드 분석 엔진 7-step + diagnose UI
[✓] M6  VersionUp 권장안 LLM + diagnosis-review UI
[✓] M7  Linear 자동 등록 + ZIP 생성 + finalize
[✓] M8  회귀 R-1~R-7 + 단위 테스트 30 케이스
```

<br>

**한 마일스톤 = 한 세션** · 매 마일스톤 **vitest 77/77 + mypy 0 + ruff All pass**

---

# MVP-2-A 산출 자산

| 자산 | 수량 |
|---|---|
| 백엔드 신규 모델 | **5** (Alembic 039) |
| 백엔드 신규 service | **9** (clone / scan / manifest / outdated / sample / llm_summary / recommendations / pipeline / zip_builder) |
| 백엔드 신규 endpoint | **11** (`/integrations/github/app/*` 3 + `/modernize/*` 8) |
| 프론트엔드 신규 step | **5** (repo-connect/select/diagnose/diagnosis-review/confirm) |
| 단위 테스트 | **30** 케이스 |
| 회귀 자동화 | **R-1~R-7** 스크립트 + 문서 |

<br>

> **신규 추가만** — 기존 `/solutions/new` 위저드, `generator.generate_all()`, 카탈로그 데이터 모두 미변경.

---

<!-- _class: section-divider -->

# 보안 · 라이센스 · 가격

---

# 보안 보장

<br>

| 영역 | 보장 |
|---|---|
| 소스 코드 | ZIP 다운로드 후 **사용자 로컬에만** 존재 |
| API 키 | 사용자 로컬 `.env` — ClickEye 서버 비저장 |
| Modernize 분석 | `/tmp/modernize/<session>/` → Step 7 직후 `shutil.rmtree` |
| GitHub 접근 | App installation token (1h 유효, 자동 회전), **최소 권한 read-only** |
| Linear 자격증명 | Fernet 암호화 후 DB 저장 (선택) |
| Webhook | **HMAC-SHA256 서명 검증** |

---

# 라이센스 모델

<br>

| 항목 | Free | Pro | Enterprise |
|---|---|---|---|
| 프로젝트 수 | 1 | 5 | Unlimited |
| Agent 연결 | 1 | 3 | Unlimited |
| 카탈로그 | 기본 | 전체 | 전체 + 커스텀 |
| 동시 티켓 | 1 | 10 | Unlimited |
| 기술 지원 | 커뮤니티 | 이메일 | 전담 |
| 가격 | **무료** | TBD/월 | TBD/월 |

<br>

> 가격은 시장 검증 후 결정. **Modernize 베타는 화이트리스트 무료**.

---

# 비용 구조 — 투명함

<br>

```
사용자 비용 = ClickEye 라이센스 (월) + AI 토큰 (사용량)

[ClickEye 라이센스]
  └─ 카탈로그 · 위저드 · ZIP 생성 · 진단 · 기술 지원

[AI 토큰 — BYOK]
  └─ 사용자가 직접 관리. ClickEye 가 마진 안 붙임.
```

<br>

**평균 사용량 가이드**

- 신규 위저드 1 회 = $0.5 ~ $2
- Modernize 분석 1 회 = $1 ~ $5
- 자동 개발 작업 1 건 = $0.5 ~ $10

---

<!-- _class: section-divider -->

# 로드맵

---

# 후속 로드맵

<br>

| 시점 | 마일스톤 | 내용 |
|---|---|---|
| **이번 분기** | MVP-2-A GA | VersionUp 시나리오 정식 출시 |
| 다음 분기 | MVP-2-B Refactor | 코드 스멜 / 레이어링 LLM 정교화 |
| 다음 분기 | MVP-2-C LanguageMigrate | target_stack UI + 단계형 출력 |
| Q2~3 | MVP-3 Cloud 실행 | ClickEye 서버가 직접 PR 작성 |
| Q3 | GHE 지원 | GitHub Enterprise / GitLab |
| Q4 | Multi-tenant 강화 | Enterprise — audit log, custom 카탈로그 |

---

<!-- _class: section-divider -->

# Q&A

---

# 자주 받는 질문

<br>

**Q1. 코드를 외부로 보내지 않는다는 게 확실한가?**
→ Modernize 분석 워크스페이스는 Step 7 직후 즉시 삭제. DB 비저장.

**Q2. AI 코드 품질 보장?**
→ `harness-gate.sh` 매 커밋 lint/type/test + Claude(정제·구현)·Codex(QA) 교차 검토 + 머지 직전 거버넌스 게이트(정합성·위험)

**Q3. 토큰 비용?**
→ 신규 위저드 $0.5~$2, Modernize $1~$5, 자동 개발 $0.5~$10 (BYOK 투명)

**Q4. Claude Code 와의 차이?**
→ 도구 + 멀티 Agent 오케스트레이션 + Linear 연동 + 자동 PR + 진단 + 멀티 플랫폼 ZIP

**Q5. 사내 Jenkins / GitLab CI 충돌?**
→ 없음. ClickEye 는 코드 작성 + PR 생성까지. 빌드/배포는 기존 CI 그대로.

---

<!-- _class: title -->

# 감사합니다

<br>

<p style="font-size: 1.3em; opacity: 0.9;">
ClickEye · AI 개발 자동화 솔루션 빌더
</p>

<br>

<p style="font-size: 0.9em; opacity: 0.7;">
베타 가입 / 문의: TBD<br>
docs: clickeye-product-guide.md · clickeye-development-pipeline.md
</p>

<br>

<p style="font-size: 0.8em; opacity: 0.5;">
"5분 위저드 → ZIP → AI 자율 개발"
</p>
