# ClickEye 개발 파이프라인 — 동작 원리 전체 설명

> **"ClickEye 가 ClickEye 를 만든다."**
>
> 이 문서는 ClickEye 라는 제품 자체를 어떤 AI 자동화 파이프라인으로 개발하는지를 설명합니다.
> 즉, 제품 사용자가 받는 ZIP 안의 자동화는 사실 **개발사 자신이 매일 쓰고 있는 시스템** 의 패키지화입니다.

---

## 목차

1. [개발 철학 — Dogfooding](#1-개발-철학--dogfooding)
2. [전체 파이프라인 한눈에](#2-전체-파이프라인-한눈에)
3. [모델 라우팅 — Opus / Sonnet / Haiku](#3-모델-라우팅--opus--sonnet--haiku)
4. [PM Agent + Deep Thinker (Phase 0)](#4-pm-agent--deep-thinker-phase-0)
5. [하네스 엔지니어링 4 단계](#5-하네스-엔지니어링-4-단계)
6. [Plan Gate (`.claude/current-plan.md`)](#6-plan-gate-claudecurrent-planmd)
7. [Linear 기반 작업 흐름](#7-linear-기반-작업-흐름)
8. [auto_dev_pipeline.sh — 멀티 Agent 자동 개발](#8-auto_dev_pipelinesh--멀티-agent-자동-개발)
9. [Webhook + ngrok 인프라](#9-webhook--ngrok-인프라)
10. [비침습성 회귀 검증 R-1 ~ R-7](#10-비침습성-회귀-검증-r-1--r-7)
11. [Hook 시점 별 자동 검증](#11-hook-시점-별-자동-검증)
12. [실 적용 예시 — Modernize MVP-2-A 가 만들어진 과정](#12-실-적용-예시--modernize-mvp-2-a-가-만들어진-과정)
13. [메트릭과 향후 확장](#13-메트릭과-향후-확장)

---

## 1. 개발 철학 — Dogfooding

> "우리가 파는 자동화 도구를, 우리가 매일 쓰지 않으면 어떻게 고객에게 추천하겠는가?"

ClickEye 는 다음 원칙을 따릅니다:

1. **자기 자신을 만든다** — ClickEye 제품 자체의 모든 신규 기능(예: 본 문서가 작성될 시점의 MVP-2-A Modernize) 은 ClickEye 가 생성하는 자동화 흐름과 **동일한 시스템** 으로 만들어진다.
2. **비침습성 (Non-Invasive)** — 신규 기능 추가 시 기존 코드는 단 한 줄도 동작이 바뀌지 않는다. R-1 ~ R-7 회귀 검증 통과 필수.
3. **Plan-first** — 모든 코드 작성 전에 `.claude/current-plan.md` 에 계획 + 사용자 승인 마커. 즉흥 코드 작성 금지.
4. **Multi-AI 합의** — 단일 AI 환각 방지를 위해 Gemini(기획) → Claude(구현) → Codex(QA) 의 다단계 검토.
5. **Budget-aware** — Opus 는 계획·설계만, 구현은 Sonnet, 단순 작업은 Haiku. 토큰 비용 최적화.

### 결과 (MVP-2-A 8 마일스톤 기준)

- 단일 개발자 1 인 × 8 세션으로 **백엔드 5 모델 + 11 endpoint + 9 service + 30+ 단위 테스트 + 프론트엔드 5 step 컴포넌트 + 회귀 체크리스트** 까지 완성.
- 매 세션 중간 ETA 손실 없이 진행. 매 마일스톤 R-3/R-5/R-6 회귀 자동 검증.

---

## 2. 전체 파이프라인 한눈에

```
사용자 요청 (Linear 티켓 / 채팅)
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  Phase 0:  PM Agent (Opus)                            │
│   - 복잡도 ≥ 0.7 이면 호출                              │
│   - 구현 스펙 생성 → deep-thinker 위임 가능              │
└──────────────────────────────────────────────────────┘
        │ Spec
        ▼
┌──────────────────────────────────────────────────────┐
│  Phase 1:  Harness Router (Sonnet)                    │
│   - 모호 → 인터뷰  /  명확 → Loop  /  대화 → 표준응답      │
└──────────────────────────────────────────────────────┘
        │ 명확한 구현 작업
        ▼
┌──────────────────────────────────────────────────────┐
│  Phase 2:  Context Manager (Haiku)                    │
│   - CLAUDE.md + 모듈 agent.md + PLAN.md + 관련 src 만   │
│   - "가림막 원칙": 불필요한 파일 차단                     │
└──────────────────────────────────────────────────────┘
        │ 선별된 컨텍스트
        ▼
┌──────────────────────────────────────────────────────┐
│  Phase 3:  Harness Loop (Sonnet, MAX 5회)             │
│   ┌────────────────────────────────────────────────┐  │
│   │  WRITE_CODE (Worker 1)                          │  │
│   │      ↓                                          │  │
│   │  자동 검증 (lint → typecheck → test)             │  │
│   │      ↓ 실패                                     │  │
│   │  에러 피드백 → 다시 WRITE_CODE                    │  │
│   │      ↓ 통과                                     │  │
│   │  CODE_REVIEW (Worker 2)                         │  │
│   └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
        │ 검증된 코드
        ▼
┌──────────────────────────────────────────────────────┐
│  Phase 4:  Hook 게이트                                │
│   - PreToolUse(git commit): harness-gate.sh 실행      │
│   - PostToolUse(Edit|Write): 검증 리마인더              │
│   - Stop: fix_plan 완료 + 테스트 통과 확인              │
└──────────────────────────────────────────────────────┘
        │ 커밋
        ▼
   Linear 상태 자동 전이 + PR 생성 + Telegram 알림
```

---

## 3. 모델 라우팅 — Opus / Sonnet / Haiku

`.claude/MODEL-ROUTING.md` 에 정의된 매 작업의 최적 모델:

| 티어 | 모델 | 용도 | 비용 |
|---|---|---|---|
| **고급 사고** | Opus 4.7 (1M context) | 계획, 설계, 트레이드오프 분석 | $$$$ |
| **표준** | Sonnet 4.6 | 코드 작성, 검증, 리뷰 | $$ |
| **경량** | Haiku 4.5 | 컨텍스트 선별, 단순 분류 | $ |

### Agent / Skill 별 배정

| Agent / Skill | 모델 | 호출 시점 |
|---|---|---|
| `pm-agent` | **opus** | 세션 시작, `--think` 플래그, 블로킹 이슈 |
| `deep-thinker` | **opus** | pm-agent 가 복잡도 ≥ 0.7 감지 시 |
| `harness-router` | sonnet | 의도 분석 |
| `harness-context` | **haiku** | 컨텍스트 선별 (대량 파일 빠르게 필터) |
| `harness-loop` | sonnet | 코드 작성 + 검증 루프 |
| `harness-worker` | 역할별 | WRITE_CODE/TEST/REVIEW/SECURITY |
| `code-reviewer` (Auto) | sonnet | 코드 변경 후 자동 |

### 격상 / 격하 규칙

- 작업 실패가 3 회 연속 → 자동으로 한 티어 격상 (Sonnet → Opus)
- 단순 변경 (1 줄 typo, naming) → Haiku 로 격하
- 사용자가 `--think` / `--ultrathink` 플래그 명시 → Opus 강제

---

## 4. PM Agent + Deep Thinker (Phase 0)

### 호출 조건

- 세션 시작 시 사용자 의도 분석
- 복잡도 ≥ 0.7 (다중 도메인, 시스템 영향 큰 변경, 새 기능 도입)
- 또는 사용자가 명시적으로 `--think` / `--ultrathink`

### PM Agent 산출

```markdown
# 구현 스펙 (PM 작성)

## 목표
M5 — 코드 분석 엔진 7-step pipeline + step-modernize-diagnose UI

## 분해된 작업
1. clone.py — git clone (App JWT 사용)
2. scan.py — 확장자 분포
3. manifest.py — pyproject / package.json 파싱
4. outdated.py — pypi / npm 호출
...

## 트레이드오프 분석
- 한 세션에 다 끝낼 수 있나? → 핵심 골격만 + LLM 정교화는 M6 로 분리
- 외부 의존성? → Anthropic key 미설정 시 placeholder fallback 필요
```

### Deep Thinker 위임

PM 이 복잡도가 매우 높은 결정 (예: "기존 코드 무영향 보장 방법") 만나면 `deep-thinker` 서브에이전트에 위임. Deep thinker 는 Opus 1M 컨텍스트로 plan agent (Phase 2) 와 협력해 multi-perspective 분석.

---

## 5. 하네스 엔지니어링 4 단계

### Stage 1 — Harness Router (`harness-router` 스킬)

사용자 입력의 의도를 3 가지로 분류:

| 의도 | 처리 |
|---|---|
| **모호** ("좀 더 나은 방향?") | 소크라테스식 인터뷰 — 5W1H 질문 |
| **명확** ("M5 진행해") | 즉시 Harness Loop 진입 |
| **대화** ("안녕") | 표준 응답 |

### Stage 2 — Context Manager (`harness-context` 스킬)

> "AI 가 너무 많은 파일을 보면 핵심 제약을 잊는다."

`load-recent-changes.sh` + 모듈별 `agents/*.md` + 현재 작업 관련 src 만 선별 로딩.

```
[가림막 원칙]
  ✅ 로딩: CLAUDE.md, .claude/agents/api-agent.md, scripts/modernize/pipeline.py
  ❌ 차단: 전체 코드베이스 grep, node_modules, .git
```

### Stage 3 — Harness Loop (`harness-loop` 스킬)

**MAX 5 회 반복** — 환각/오류 사전 차단의 핵심.

```
1. WRITE_CODE (시도 1)
       ↓
2. lint / typecheck / test 자동 실행
       ↓ 실패
3. 에러 메시지를 다시 WRITE_CODE 에 피드백
       ↓
4. WRITE_CODE (시도 2)
       ...
5. MAX 5 회 도달 시 → 사용자에게 차단 보고 (예: "테스트 통과 못함, 사용자 검토 필요")
```

### Stage 4 — Worker (`harness-worker` 스킬)

역할별로 컨텍스트 완전히 분리:

| Worker | 역할 | 사용 스킬 |
|---|---|---|
| WRITE_CODE | 코드 작성 | `fullstack` + 모듈별 agent.md |
| TEST_WRITER | 테스트 작성 | `tdd-smart-coding` |
| CODE_REVIEW | 리뷰 | `ai-critique` (GPT + Gemini 동시) |
| SECURITY_REVIEW | 보안 검토 | OWASP Top 10 |

> **컨텍스트 분리 이유**: 같은 AI 가 코드를 쓰고 리뷰하면 자기 작품에 관대해진다.

---

## 6. Plan Gate (`.claude/current-plan.md`)

> **모든 `Edit` / `Write` 도구 호출 전 검증 필수.**

### 동작

1. 사용자 요청 → AI 가 plan 작성 (`.claude/current-plan.md`)
2. Plan 파일 끝에 `## STATUS: APPROVED` 마커가 있어야 코드 수정 가능
3. PreToolUse hook (`.claude/hooks/...`) 가 매 Edit/Write 호출 전 검증
4. APPROVED 없으면 도구 호출 차단 + 사용자에게 알림

### Plan 파일 형식

```markdown
## 목표
(무엇을 구현하는지 1~2 문장)

## 변경 파일 목록
- 파일경로: 변경 내용

## 구현 단계
1. 단계 1
2. 단계 2

## 예상 영향 범위
(다른 기능/모듈에 미치는 영향)

## STATUS: APPROVED   ← 사용자 승인 후 추가
```

### 가치

- **즉흥 코드 작성 차단** — AI 가 "이정도면 되겠지" 로 코드 쓰는 것 방지
- **사용자 동의 확인** — 변경 범위가 사용자 의도와 일치
- **회고 가능** — Plan 파일이 변경 이력의 일부

---

## 7. Linear 기반 작업 흐름

### Linear 워크플로 상태

```
Backlog ──(수동)──→ Wait ──(수동)──→ DayQueued / NightQueued
                                       │
                            ┌──────────┴──────────┐
                            │  Webhook 감지       │
                            │  또는 수동 실행      │
                            └──────────┬──────────┘
                                       ↓
                                  In Progress
                                       │
                                  [AI 자율 작업]
                                  [테스트/린트 통과]
                                       │
                            ┌──────────┴──────────┐
                            ↓                     ↓
                          Done                 Backlog
                     (머지 또는 PR)         (실패/건너뜀)
                            │
                  ┌─────────┴─────────┐
                  ↓                   ↓
            AUTO_MERGE ON        AUTO_MERGE OFF
            (직접 머지→push)      (PR→CI→머지)
                  │                   │
                  │            ┌──────┴──────┐
                  │            │ CI 통과      │
                  │            │ AI Review    │
                  │            │ auto-merge   │
                  │            └──────┬──────┘
                  └─────────┬─────────┘
                            ↓
                       post-merge.yml
                       Linear → Done
                       Telegram 알림
                            ↓
                       다음 Queued 이슈
                       (순차 반복)
```

### 핵심 자동 전이

- **DayQueued/NightQueued/Queued** → AI 가 작업 시작 → **In Progress**
- 작업 완료 → PR 생성 → CI 통과 → **Done**
- `Confirm` 상태 변경 → `linear_confirmer.py` 자동 머지

### 모듈 토글 (`.env` 의 `FLOWOPS_*`)

```env
FLOWOPS_LINEAR_WATCHER=true     # Linear 이슈 감지
FLOWOPS_GEMINI_PLAN=true        # Gemini 기획 단계 활성
FLOWOPS_CODEX_REVIEW=true       # Codex QA 활성
FLOWOPS_AUTO_MERGE=true         # 직접 머지 (false: PR 생성)
FLOWOPS_TELEGRAM=true           # 텔레그램 알림
```

각 단계를 독립적으로 ON/OFF 가능 → 단계별 디버깅 / 점진 도입 용이.

---

## 8. auto_dev_pipeline.sh — 멀티 Agent 자동 개발

`scripts/auto_dev_pipeline.sh` (v6) 가 본 파이프라인의 오케스트레이터.

### 흐름

```
[STEP 0] FLOWOPS_* 환경변수 로드 + DB(Postgres+Redis) docker-compose 자동 기동
       ↓
[STEP 1] linear_watcher.py — DayQueued 이슈 1건 감지
       ├─ fix_plan.md 생성 → .ralph/tasks/{ISSUE_KEY}.md
       └─ 태스크 매핑 → .ralph/.task_mapping.json
       ↓
[STEP 2] Gemini 기획 (generate_plan_with_gemini.sh)
       └─ .ralph/PLAN.md 생성 (요약 / 범위 / 작업단계 / 수용기준 / 리스크)
       ↓
[STEP 3] 브랜치 자동 생성 ralph/{24S-XX}
       └─ Linear 상태 → In Progress
       ↓
[STEP 4] Claude 구현
       ├─ 하네스 4단계 적용 (Router → Context → Loop → Worker)
       ├─ harness-gate.sh 매 커밋 검증
       └─ .ralph/TASK.md 생성 (변경 파일 / 구현 / 테스트 / 남은 이슈)
       ↓
[STEP 5] Codex QA 리뷰 (run_codex_review.sh)
       └─ .ralph/REVIEW.md (요구충족 / 리스크 / 테스트 부족 / PR 코멘트)
       ↓
[STEP 6] linear_reporter.py — Linear 이슈에 결과 코멘트
       ↓
[STEP 7-A] AUTO_MERGE=true: git merge --no-ff → push origin main
[STEP 7-B] AUTO_MERGE=false: auto_pr_creator.py → gh pr create
       ↓
[STEP 8] GitHub Actions
       ├─ ci.yml — pytest + ruff + pnpm lint + build
       ├─ ai-review.yml — ChatGPT FC 코드 리뷰 → PR 코멘트
       └─ post-merge.yml — Linear Done + Telegram
       ↓
[STEP 9] 다음 Queued 이슈 자동 반복 (--once 시 종료)
```

### 멀티 Agent 의 역할 분담 (재강조)

| Agent | 모델 | 입력 | 출력 | 목적 |
|---|---|---|---|---|
| **Gemini** | gemini-2.5 (예) | 이슈 + fix_plan | `PLAN.md` | 폭넓은 기획·long-context |
| **Claude** | Sonnet 4.6 | PLAN.md + 코드베이스 | `TASK.md` + 실제 코드 | 정확한 구현 |
| **Codex** | gpt-5 (예) | PLAN.md + TASK.md + diff | `REVIEW.md` | 외부 시각 QA |

> 세 AI 가 합의해야 머지. 단일 AI 환각이 다른 둘에 의해 잡힘.

---

## 9. Webhook + ngrok 인프라

Linear 이슈 상태 변경 즉시 트리거를 위한 인프라.

### 진단·기동·검증 자동 스크립트

```bash
bash scripts/webhook-doctor.sh
```

기능:
1. 포트 9876/4040 점유 진단 (본 프로젝트 vs 타 프로젝트 식별 — `/proc/$PID/cwd`)
2. 자체 webhook 서버 + ngrok 정리
3. webhook_server.py 기동
4. ngrok (reserved 도메인) 기동
5. 로컬 + 외부 `/health` 검증
6. Linear 등록 webhook URL ↔ ngrok 도메인 매칭 확인

### 동작

```
Linear (DayQueued/NightQueued/Confirm 상태 전이)
   ↓ HTTPS POST
ngrok 터널
   ↓
webhook_server.py (포트 9876)
   ↓ 서명 검증
event 처리
   ↓
auto_dev_pipeline.sh 백그라운드 실행
```

### 보안

- `WEBHOOK_SECRET` 으로 Linear 서명 검증 (HMAC-SHA256)
- 30 초 간격 중복 트리거 방지
- 메모리 lock 으로 파이프라인 동시 실행 차단

---

## 10. 비침습성 회귀 검증 R-1 ~ R-7

`docs/modernize-regression-checklist.md` 에 정의된 자동화 R-1 ~ R-7. 매 PR 머지 전 통과 필수.

| R# | 항목 | 자동화 |
|---|---|---|
| **R-1** | 기존 위저드 E2E | 수동 + 향후 Playwright |
| **R-2** | ZIP 골든파일 | pytest (`test_zip_builder.py`) |
| **R-3** | OpenAPI diff | git diff `openapi.json` |
| **R-4** | 카탈로그 변경 0 건 | `scripts/modernize-check-catalog-unchanged.sh` |
| **R-5** | wizard-store snapshot | vitest 회귀 (현재 77/77) |
| **R-6** | Feature flag OFF | `scripts/modernize-check-flag-off.sh` |
| **R-7** | Alembic downgrade | `python -m alembic downgrade` |

### 비침습성 원칙 — 4 가지 명시 규칙

1. **추가 only** — 기존 코드는 한 줄도 동작이 바뀌면 안 됨
2. **Feature flag default OFF** — 신규 기능은 명시적 활성화만 노출
3. **신규 모델은 신규 테이블만** — 기존 컬럼 변경 0
4. **API breaking 0** — 기존 endpoint path/method/response schema 변경 0

> 비침습성 검증은 **고객 환경 무손실 보장**의 핵심. 우리가 우리 자신의 자동화로 검증 → 그대로 고객 ZIP 으로 전수.

---

## 11. Hook 시점 별 자동 검증

`.claude/settings.json` 의 hook 등록.

| Hook 시점 | 호출 | 역할 |
|---|---|---|
| `UserPromptSubmit` | 매 사용자 프롬프트 | 하네스 Router 지침 + TODO 리마인더 주입 |
| `PreToolUse(Edit\|Write)` | Edit/Write 직전 | Plan Gate 확인 (`.claude/current-plan.md` 의 STATUS: APPROVED) |
| `PreToolUse(git commit)` | git commit 직전 | `harness-gate.sh` 실행 — 모듈별 lint/type/test |
| `PostToolUse(Edit\|Write)` | Edit/Write 직후 | 검증 리마인더 ("Gate 미통과 시 커밋 차단 경고") |
| `Stop` | AI 종료 직전 | `ralph-stop-hook.sh` — fix_plan 완료 + 테스트 통과 확인. 미충족 시 루프 block |

### harness-gate.sh 모듈별 Gate

| 모듈 | Gate 1: Lint | Gate 2: Type | Gate 3: Test |
|---|---|---|---|
| `clickeye-api` | `uv run ruff check .` | `uv run mypy app/` | `uv run pytest --tb=short -q` |
| `clickeye-web` | `npm run lint` | `npx tsc --noEmit` | — |
| `clickeye-agent` | `uv run ruff check .` | `uv run mypy agent/` | `uv run pytest --tb=short -q` |
| `clickeye-contracts` | — | `npx tsc --noEmit` | — |

변경된 모듈만 자동 감지 → 해당 모듈 Gate 만 실행. docs/scripts 만 변경 시 Gate 건너뜀.

---

## 12. 실 적용 예시 — Modernize MVP-2-A 가 만들어진 과정

본 파이프라인이 **실제로 잘 동작한다**는 증거. ClickEye 의 **기존 코드 현대화 기능 (MVP-2-A)** 은 8 마일스톤으로 완성되었습니다.

### 마일스톤 진행

```
[✓] M1 — Feature flag + wizard-store mode 분기   (회귀 안전 기반)
[✓] M2 — 백엔드 모델 5 종 + Alembic 039
[✓] M3 — GitHub App 인프라 + install/callback/webhook 엔드포인트
[✓] M4 — 진입 카드 + repo-connect/select step + repo 목록 API
[✓] M5 — 코드 분석 엔진 7-step + diagnose UI
[✓] M6 — VersionUp 권장안 LLM + diagnosis-review UI
[✓] M7 — Linear 자동 등록 + ZIP 생성 + finalize 흐름
[✓] M8 — 회귀 R-1~R-7 자동화 + 단위 테스트 30 케이스 + 체크리스트 문서
```

### 매 마일스톤 적용된 패턴

```
1.  AskUserQuestion — 사용자에게 어디까지 진행할지 묻기 (option A/B/C)
       ↓
2.  Plan Gate 갱신 (.claude/current-plan.md)
       ↓
3.  TaskUpdate — 해당 마일스톤 in_progress 표시
       ↓
4.  Explore agent — 기존 패턴 파악 (변경 대상 파일 + 재사용 자산)
       ↓
5.  코드 작성 (Sonnet)
   ├─ backend (모델 / service / endpoint / schemas)
   └─ frontend (api-client / step 컴포넌트 / page 확장)
       ↓
6.  검증 자동 실행
   ├─ ruff format + check
   ├─ mypy (신규 파일만 격리)
   ├─ tsc --noEmit
   ├─ vitest 전체 (회귀)
   └─ R-7 alembic upgrade/downgrade (M2 만)
       ↓
7.  TaskUpdate — completed 표시
       ↓
8.  사용자 보고 — 변경 요약 + 검증 결과 + 다음 마일스톤 안내
```

### 한 마일스톤 = 한 세션 평균

- 작성 코드량: 백엔드 200~600 라인 + 프론트엔드 150~500 라인 + 테스트 100~300 라인
- 검증 통과: vitest 77/77, mypy 0 errors, ruff All checks passed
- 사용자 개입: AskUserQuestion 1~2 회 + 다음 마일스톤 진행 신호 1 회

### MVP-2-A 의 핵심 자산

| 자산 | 수량 |
|---|---|
| 백엔드 신규 모델 | 5 (github_installations / github_repos / modernize_sessions / codebase_analyses / modernize_recommendations) |
| 백엔드 신규 service | 9 (clone / scan / manifest / outdated / sample / llm_summary / recommendations / pipeline / finalize / zip_builder / github_app_service / repo_service) |
| 백엔드 신규 endpoint | 11 (`/integrations/github/app/*` 3 + `/modernize/*` 8) |
| 프론트엔드 신규 step | 5 (repo-connect / repo-select / diagnose / diagnosis-review / confirm) |
| 단위 테스트 | 30 (scan 8 + manifest 8 + recommendations 5 + zip_builder 9) |
| 회귀 자동화 | R-1~R-7 (스크립트 2 + 문서 1) |
| 비침습성 보장 | 기존 vitest 77/77 + 기존 OpenAPI endpoint 시그니처 변경 0 |

> 모든 변경은 **신규 추가 only** — 기존 `/solutions/new` 위저드, `generator.generate_all()`, 카탈로그 데이터, 기존 모델 컬럼 모두 한 줄도 안 건드림.

---

## 13. 메트릭과 향후 확장

### 현재 측정 가능한 메트릭

| 메트릭 | 출처 |
|---|---|
| 마일스톤당 평균 토큰 사용량 | Anthropic API usage |
| 마일스톤당 vitest pass rate | `npx vitest run` 결과 |
| 회귀 검증 통과율 (R-1~R-7) | `bash scripts/modernize-check-*.sh` |
| 자동 PR 생성 → 머지 전환율 | GitHub Actions `post-merge.yml` 로그 |
| Linear 이슈 평균 해결 시간 | Linear API |
| harness-gate 1차 통과율 | `logs/gate_*.log` |

### 향후 확장 (로드맵)

| 확장 | 시점 | 내용 |
|---|---|---|
| **MVP-2-B Refactor** | 직후 | LLM 시나리오 시스템 프롬프트 정교화 (code smells, layering) |
| **MVP-2-C LanguageMigrate** | MVP-2-B 이후 | target_stack 입력 UI + scaffolding → cutover 단계형 출력 |
| **MVP-3 Cloud 실행** | MVP-2 GA 이후 | ClickEye 서버가 직접 git clone + PR 작성 (GitHub App PR write scope 승격 + Celery 워커 풀) |
| **GHE 지원** | MVP-3 이후 | GitHub Enterprise / GitLab 통합 |
| **Multi-tenant 강화** | Enterprise 플랜 | organization-level isolation, audit log, custom 카탈로그 |
| **AI Review v2** | 지속 | Gemini + GPT + Claude 3 자 합의 라벨 |

---

## 부록 A — 파이프라인 트리거 명령 (개발자용)

### 즉시 실행

```bash
# 신규 Queued 이슈 1건 처리
bash scripts/auto_dev_pipeline.sh --once

# 오버나이트 (긴 반복)
bash scripts/auto_dev_pipeline.sh --max-iterations 50

# 시연 (짧은 루프)
bash scripts/auto_dev_pipeline.sh --max-turns 5
```

### Webhook 기동 (지속 실행)

```bash
# 진단·정리·기동·검증 올인원
bash scripts/webhook-doctor.sh

# 또는 개별
nohup python3 scripts/webhook_server.py > logs/webhook.log 2>&1 &
nohup ~/bin/ngrok http 9876 --url=https://your-reserved.ngrok-free.dev > logs/ngrok.log 2>&1 &
```

### Linear 이슈 등록 (수동)

```bash
python3 scripts/linear_tracker.py task \
  --title "사용자 프로필 API 추가" \
  --summary "GET /api/users/{id} 엔드포인트 구현. 응답에 이름, 이메일, 가입일 포함." \
  --tags "backend,api" \
  --status "DayQueued"
```

### PRD → Linear (한 번에)

```
/prd-to-linear docs/prd-v2.md
```

ClickCode 의 `prd-to-linear` 스킬이 PRD 마크다운을 분석 → 태스크 분해 (P1/P2/P3) → 사용자 확인 → Linear 일괄 등록.

---

## 부록 B — 핵심 파일 참조

| 파일 | 역할 |
|---|---|
| `CLAUDE.md` | 프로젝트 진입점 + 개발 규칙 |
| `.claude/agents/pm-agent.md` | PM Agent 시스템 프롬프트 |
| `.claude/agents/deep-thinker.md` | Deep thinker 위임 가이드 |
| `.claude/agents/harness-guide.md` | 하네스 4 단계 전체 가이드 |
| `.claude/MODEL-ROUTING.md` | 모델 라우팅 표 |
| `.claude/settings.json` | Hook 등록 + 도구 권한 |
| `.claude/hooks/harness-gate.sh` | 모듈별 lint/type/test Gate |
| `scripts/auto_dev_pipeline.sh` | 멀티 Agent 자동 개발 (v6) |
| `scripts/webhook-doctor.sh` | webhook 진단·기동·검증 |
| `scripts/webhook_server.py` | Linear webhook 수신 데몬 |
| `scripts/linear_watcher.py` | Queued 이슈 감지 |
| `scripts/linear_tracker.py` | Linear CRUD 유틸 |
| `scripts/generate_plan_with_gemini.sh` | Gemini 기획 단계 |
| `scripts/run_codex_review.sh` | Codex QA 단계 |
| `scripts/pipeline_config.sh` | FLOWOPS_* 모듈 토글 |
| `docs/pipeline-guide.md` | 본 파이프라인 사용자 가이드 |
| `docs/modernize-regression-checklist.md` | 비침습성 R-1~R-7 체크리스트 |

---

## 부록 C — 한 줄 핵심 메시지 (발표용)

> **"우리는 ClickEye 라는 자동화 도구를 만들기 위해, ClickEye 의 자동화를 매일 사용합니다."**

세 가지 키워드:
1. **Plan-first** — 코드 작성 전 사용자 승인 마커
2. **Multi-Agent 합의** — Gemini(기획) + Claude(구현) + Codex(QA) 3 자 검토
3. **비침습성 자동 검증** — 매 마일스톤 R-1~R-7 통과 보장 (회귀 0)

---

## 부록 D — 발표 시 강조 포인트 (1 페이지 요약)

### Why? — 왜 ClickEye 같은 도구가 필요한가
> AI 코드 작성이 환각/오류로 신뢰 못 받는 시대, **하네스로 통제된 자동화** 만이 실무 도입 가능.

### How? — 어떻게 그 신뢰를 만드나
> (1) Plan-first + 사용자 승인. (2) 멀티 AI 합의. (3) 매 커밋 Gate (lint/type/test). (4) 회귀 R-1~R-7 자동 검증.

### What? — 무엇이 결과로 나오나
> 사용자는 ZIP 한 번. 그 ZIP 안에 우리 자체 자동화의 8 개월 누적 자산이 들어있음. 받자마자 동일 흐름 시작 가능.

### Proof — 어떻게 증명하나
> ClickEye 의 **기존 코드 현대화 기능 (MVP-2-A)** 자체가 본 파이프라인으로 8 마일스톤에 완성됨. 매 마일스톤 회귀 77/77 통과.
