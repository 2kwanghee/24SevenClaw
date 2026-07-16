---
title: 자동화 파이프라인 가이드 (v6)
category: guide
status: needs-revision
last_updated: 2026-06-12
related:
  - scripts/auto_dev_pipeline.sh
  - scripts/pre_merge_gate.py
---

# 자동화 파이프라인 가이드

> 이 문서는 ClickEye 자동화 파이프라인의 **전체 아키텍처, 실행 방법, 트리거 방식**을 설명합니다.

---

## 전체 아키텍처

```
                        ┌─────────────────────┐
                        │   PRD / 요구사항      │
                        └─────────┬───────────┘
                                  ↓
                        ┌─────────────────────┐
                        │  /prd-to-linear     │  Claude Code 스킬
                        │  (태스크 분해+등록)   │  또는 수동 등록
                        └─────────┬───────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────┐
│                     Linear (Queued)                          │
│                     Team: 24Seven (24S-*)                    │
└──────────┬──────────────────────────────────┬────────────────┘
           │                                  │
    ┌──────┴──────┐                    ┌──────┴──────┐
    │  Webhook    │                    │  수동 실행   │
    │  (즉시)     │                    │ /run-pipeline│
    └──────┬──────┘                    └──────┬──────┘
           └──────────────┬───────────────────┘
                          ↓
              ┌───────────────────────┐
              │ auto_dev_pipeline.sh  │
              │ (v6 — 멀티 Agent)     │
              └───────────┬───────────┘
                          ↓
              ┌───────────────────────┐
              │ Queued 이슈 1개 감지   │  linear_watcher.py
              │ fix_plan.md 생성       │
              └───────────┬───────────┘
                          ↓
              ┌───────────────────────┐
              │ [Claude] 메타프롬프트  │  PLAN.md + .ralph/refined/
              │ 관측형 사전 정제       │  {ISSUE}.md 생성 (멱등)
              │ (기획+정제 일체)       │  → Linear 코멘트 기록
              └───────────┬───────────┘  ※ FLOWOPS_METAPROMPT=false
                          ↓                  시 Gemini 기획 폴백
                          ↓
              ┌───────────────────────┐
              │ 브랜치 생성            │  ralph/{24S-XX}
              │ [Claude] 구현          │  TASK.md 생성
              └───────────┬───────────┘
                          ↓
              ┌───────────────────────┐
              │ [Codex] QA 리뷰       │  REVIEW.md 생성
              │ run_codex_review.sh   │  (요구충족/리스크/테스트)
              └───────────┬───────────┘
                          ↓
              ┌───────────────────────┐
              │ linear_reporter.py    │  Linear 결과 보고
              └───────────┬───────────┘
                          ↓
              ┌───────────────────────┐
              │ [거버넌스 게이트]      │  pre_merge_gate.py (머지 직전 권위)
              │ contract/ticket/risk  │  검증 실패→차단·Backlog
              └───────────┬───────────┘  HIGH-tier→직접머지 금지·PR 강등
                          ↓
                 ┌────────┴────────┐
                 ↓                 ↓
       AUTO_MERGE ON & LOW   AUTO_MERGE OFF / HIGH-tier
          (직접 머지→push)   (auto_pr_creator → PR→CI)
                 │                 │
                 │          ┌──────┴──────┐
                 │          │ GitHub Actions│
                 │          │ ├─ CI        │
                 │          │ ├─ AI Review │
                 │          │ └─ auto-merge│
                 │          └──────┬──────┘
                 └────────┬───────┘
                          ↓
              ┌───────────────────────┐
              │ post-merge.yml        │
              │ Linear → Done         │
              │ Telegram 알림         │
              └───────────┬───────────┘
                          ↓
              ┌───────────────────────┐
              │ 다음 Queued 이슈 반복  │  (--once 시 종료)
              └───────────────────────┘
```

---

## 트리거 방식 (2가지)

### 1. Webhook — 실시간 자동 트리거

Linear에서 이슈 상태가 **DayQueued / NightQueued / Queued**로 바뀌는 순간 파이프라인이 자동 실행됩니다.

#### 시작 방법 — `webhook-doctor.sh` (권장)

한 번의 명령으로 **진단 → 자체 정리 → webhook+ngrok 기동 → 로컬/외부 health 검증 → Linear 등록 URL 매칭 확인**까지 모두 수행합니다. 다른 프로젝트가 같은 reserved 도메인 또는 포트를 점유하는 충돌도 자동 감지합니다.

```bash
bash scripts/webhook-doctor.sh             # 기본: 진단 → 정리 → 기동 → 검증
bash scripts/webhook-doctor.sh --check     # 진단만 (상태 점검)
bash scripts/webhook-doctor.sh --stop      # 자체 webhook+ngrok 종료
bash scripts/webhook-doctor.sh --force     # 타 프로젝트 ngrok도 종료 후 기동
bash scripts/webhook-doctor.sh --no-ngrok  # webhook만 (ngrok skip)
bash scripts/webhook-doctor.sh --help      # 옵션 전체 도움말
```

진단 단계에서 다음을 확인합니다:

| 항목 | 내용 |
|------|------|
| [1/4] 포트 점유 | 9876 (webhook) / 4040 (ngrok web UI) — 본 프로젝트 vs 타 프로젝트 식별 |
| [2/4] webhook 프로세스 | `/proc/$PID/cwd`로 본 프로젝트 webhook_server.py 와 타 프로젝트 webhook 분리 |
| [3/4] ngrok 프로세스 | 동일 — reserved 도메인 점유 충돌 사전 감지 |
| [4/4] Linear 등록 매칭 | Linear에 등록된 webhook URL이 현재 ngrok 도메인을 가리키는지 확인 |

**안전장치**: 타 프로젝트 프로세스는 `--force` 없이는 절대 종료하지 않습니다. 충돌 시 reserved 도메인 안내 메시지와 함께 `exit 3`으로 안전하게 멈춥니다.

#### 환경 변수 (`.env`)

```env
WEBHOOK_PORT=9876                                                       # 기본 9876
NGROK_DOMAIN=understandingly-unforecasted-raymundo.ngrok-free.dev      # reserved 도메인
NGROK_WEB_PORT=4040                                                     # ngrok 로컬 UI
WEBHOOK_SECRET=<Linear signing secret>                                  # 권장 (서명 검증)
```

#### 수동 기동 (레거시 — doctor를 사용할 수 없을 때만)

```bash
# 서버 시작 (백그라운드)
nohup python3 scripts/webhook_server.py > logs/webhook.log 2>&1 &

# ngrok 터널 (로컬 PC에서 실행 시)
nohup ~/bin/ngrok http 9876 --url=https://<your-reserved-domain> > logs/ngrok.log 2>&1 &

# 공개 URL 확인
curl -s http://localhost:4040/api/tunnels | python3 -c "
import json,sys
for t in json.load(sys.stdin)['tunnels']:
    print(t['public_url'])
"
```

#### Linear Webhook 등록

1. **Linear Settings → API → Webhooks → New webhook**
2. URL: `https://<ngrok-url>/webhook/linear`
3. 데이터 변경 이벤트: **Issues** 체크
4. 저장

#### 보안 (선택)

`.env`에 `WEBHOOK_SECRET`을 설정하면 Linear 서명 검증이 활성화됩니다:
```env
WEBHOOK_SECRET=<Linear webhook signing secret>
```

#### 동작 흐름

```
Linear 이슈 상태 → Queued
    ↓ (HTTP POST, 즉시)
webhook_server.py (포트 9876)
    ↓ (Queued 이벤트만 필터링)
auto_dev_pipeline.sh 백그라운드 실행
```

- Queued가 아닌 이벤트는 무시
- 30초 간격 제한으로 중복 트리거 방지
- lock 파일(`.ralph/.pipeline_lock`)로 파이프라인 중복 실행 방지

#### 모니터링

```bash
# Webhook 로그
tail -f logs/webhook.log

# 상태 확인
curl http://localhost:9876/health
```

### 2. 수동 실행 — Claude Code 또는 CLI

#### Claude Code에서

```
/run-pipeline
```

또는 대화에서 "파이프라인 실행해", "Queued 이슈 처리해" 등으로 요청.

#### CLI에서

```bash
# 기본 실행 (Queued 이슈 순차 처리, 최대 30회 반복)
bash scripts/auto_dev_pipeline.sh

# 시연/테스트용 (짧은 Claude 루프)
bash scripts/auto_dev_pipeline.sh --max-turns 5

# 오버나이트 (긴 반복)
bash scripts/auto_dev_pipeline.sh --max-iterations 50

# 1개만 처리 후 종료
bash scripts/auto_dev_pipeline.sh --once
```

---

## 파이프라인 단계별 상세

### Step 1: 이슈 감지 — `linear_watcher.py`

```bash
python3 scripts/linear_watcher.py --per-task --limit 1
```

- Linear에서 **Queued** 상태 이슈를 우선순위순으로 1개 조회
- 태스크별 `fix_plan.md` 생성 → `.ralph/tasks/{ISSUE_KEY}.md`
- 태스크 매핑 저장 → `.ralph/.task_mapping.json`

**ChatGPT Fix Plan 옵션:**
```bash
python3 scripts/linear_watcher.py --per-task --use-gpt-plan
```
ChatGPT Function Calling으로 코드베이스 맥락을 포함한 구조화된 fix_plan을 생성합니다.
(수정 대상 파일, 구현 단계, 테스트 케이스 포함)

### Step 2: 메타프롬프트 정제 (관측형 사전 정제 — 기획+정제 일체)

`FLOWOPS_METAPROMPT=true`(기본) + `.claude/skills/metaprompt/SKILL.md` 존재 시 실행:
- 거친 태스크(제목/설명 + fix_plan)를 **Claude 구독 세션**(`ANTHROPIC_API_KEY` unset, `claude -p --model sonnet`)으로 정제
- 출력: 구현 스펙(목표/가정/대상 파일/구현 단계/테스트/컨벤션) → `.ralph/refined/{ISSUE_KEY}.md`
- `.ralph/PLAN.md`로 동기화(다운스트림 Codex QA가 PLAN.md 소비) + Linear 이슈 코멘트로 기록
- **멱등성**: 이미 정제된 `.ralph/refined/{ISSUE_KEY}.md`가 있으면 재호출하지 않고 재사용 (중복 토큰 방지). 태스크 완료 시 정리됨
- **failsafe**: 정제 실패/빈 출력 시 `fix_plan.md → PLAN.md` 폴백 후 정제 없이 구현 진행
- **레거시 폴백**: `FLOWOPS_METAPROMPT=false`면 `FLOWOPS_GEMINI_PLAN` 활성 시 기존 Gemini 기획(`generate_plan_with_gemini.sh`)으로 동작

> 방법론 정의는 `.claude/skills/metaprompt/SKILL.md`. 대화형 하네스의 구현 스펙 생성도 동일 스킬을 참조한다.

### Step 3: Claude 구현 — 브랜치 + 동기 실행

각 태스크마다 (1개씩 순차):
1. `git checkout -b ralph/{24S-XX}` → 작업 브랜치 생성
2. `.ralph/tasks/{ISSUE_KEY}.md` → `.ralph/fix_plan.md`로 복사
3. Linear 상태 → **In Progress**
4. UI/UX 작업 감지 시 `RALPH_UIUX_MODE=true` 자동 활성화
5. 정제 스펙(`.ralph/refined/{ISSUE_KEY}.md`)이 있으면 구현 프롬프트 맨 앞에 prepend → Claude가 정제 스펙 우선 참고하여 구현
6. 완료 후 `.ralph/TASK.md` 생성 (변경 파일, 구현 내용, 테스트 결과, 남은 이슈)

```bash
# Claude 실행 로그 확인
tail -f logs/claude_24S-XX_*.log
```

### Step 4: Codex QA 리뷰 — `run_codex_review.sh`

`FLOWOPS_CODEX_REVIEW=true` 시 실행:
- `.ralph/PLAN.md` + `.ralph/TASK.md` + git diff를 Codex에 전달
- `.ralph/REVIEW.md` 생성 (주요 발견, 요구사항 충족 여부, 리스크, 테스트 부족, PR 코멘트 제안)
- Codex 실패 시 기본 REVIEW.md 생성 (수동 리뷰 권고)

```bash
# 수동 실행
bash scripts/run_codex_review.sh
```

### Step 5: 결과 보고 — `linear_reporter.py`

각 태스크 완료 후:
- fix_plan.md 완료 상태 파싱
- Linear 이슈에 결과 코멘트 추가 (구현 내역 + 커밋 + 테스트)

### Step 5.5: 거버넌스 게이트 — `pre_merge_gate.py` (머지 직전, 권위)

머지 결정 직전에 **검증 + 위험분류를 단일 SSOT 모듈**(`scripts/pre_merge_gate.py`)로 수행한다.
`direct-merge + push origin main`이 유일한 비보호 경로이므로 **이 인파이프라인 호출이 권위 게이트**이고,
CI(`ci.yml`의 `governance` 잡)는 동일 모듈을 PR에서 재확인하는 **미러**다(중복 로직 없음).

| 검사 | 내용 | 실패 시 |
|------|------|---------|
| contract-drift | API 계약면(`app/api\|schemas\|models\|ws`, `clickeye-contracts/**`) 변경에 `openapi/openapi.json`·generated 클라이언트 동반 여부 | **차단** |
| ticket-ref | 브랜치 `ralph/<KEY>`에서 이슈 키 추출, 형태 `^[A-Z0-9]+-\d+$` 검증 (키 없으면 skip) | **차단** |
| plan-trace | `.ralph/refined/<KEY>.md`·`PLAN.md` 연관성 점검 (산출물 없으면 자동 skip) | 권고(비차단) |

**위험분류 → 머지경로 강등** (새 승인장치 없음):
- **HIGH** (`clickeye-contracts/**`·`clickeye-infra/**`·`*auth*`·보안): `AUTO_MERGE=on`이어도 직접머지 금지 →
  기존 `auto_pr_creator` PR 경로로 강등(기존 CI·사람 머지 게이트 적용).
- **LOW**: 현행 유지.

검증 실패(exit 2) 시 기존 실패 패턴 재사용: Linear → Backlog + Telegram 알림 + 다음 이슈로 continue.

토글: `FLOWOPS_GOVERNANCE`(마스터) + `_CONTRACT`/`_TICKET`/`_TRACE`/`_RISK_DEMOTE`. **마스터 off면 게이트 전체 우회 → 기존 동작과 동일(회귀 0).**

### Step 6: 머지 — 2가지 경로

> 거버넌스 게이트(Step 5.5)가 먼저 판정한다. HIGH-tier면 아래 경로와 무관하게 PR로 강등된다.

#### A. AUTO_MERGE ON (직접 머지 — LOW-tier 한정)
`FLOWOPS_AUTO_MERGE=true` 설정 시:
1. `git merge --no-ff` → main에 직접 머지
2. `git push origin main`
3. 머지 로그 생성 (`logs/merge_*.log`)
4. 머지된 브랜치 자동 삭제
5. 머지 실패 시 → PR 생성으로 폴백
6. **추적성 승격**(`FLOWOPS_GOVERNANCE_PROMOTE`): 고복잡도(변경파일 ≥`FLOWOPS_PROMOTE_MIN_FILES`
   또는 diff 라인 ≥`FLOWOPS_PROMOTE_MIN_LINES`) 직접머지는 cleanup 전 `REVIEW.md`·`refined`·머지로그 경로를
   `logs/governance/<KEY>/`로 아카이브(재생성 없이 승격만 — refined 원본은 Linear 코멘트, diff는 머지로그에 이미 존재).

#### B. AUTO_MERGE OFF (PR 생성)
기본 동작:
1. `auto_pr_creator.py --branch ralph/{24S-XX} --auto-merge`
2. `git push -u origin ralph/{24S-XX}`
3. `gh pr create` — PR body에 Linear URL + fix_plan 결과 + 테스트 요약 + 변경 파일
4. `--auto-merge` 시 CI 통과 후 자동 squash-merge 설정

### Step 7: CI/CD — GitHub Actions

PR 생성 시 자동 실행:

| Workflow | 트리거 | 역할 |
|----------|--------|------|
| `ci.yml` | PR 생성/업데이트 | Backend pytest+ruff, Frontend pnpm lint+build, **거버넌스 게이트 미러**(`governance` 잡) |
| `ai-review.yml` | ralph/* PR 생성 | ChatGPT FC로 코드 리뷰 → PR 코멘트 |
| `post-merge.yml` | PR 머지 | Linear Done + Telegram 알림 (키 추출 `[A-Z0-9]+-\d+`) |

> `governance` 잡은 권위 게이트의 PR 미러다(동일 `pre_merge_gate.py` 호출). 현재 비차단이며,
> GitHub 브랜치 보호의 필수 체크로 지정하면 PR 차단으로 승격된다.

### Step 8: 수동 확인 머지 — `linear_confirmer.py`

사용자가 Linear에서 **Confirm**으로 변경 시:
- `linear_confirmer.py` 실행 → PR이 있으면 `gh pr merge --squash`, 없으면 로컬 `git merge`

### Step 9: 다음 이슈 반복

- 파이프라인은 다음 Queued 이슈를 자동으로 감지하여 반복
- `--once` 옵션: 1개만 처리 후 종료
- Queued 이슈가 없으면 자동 종료

---

## 이슈 등록 방법

### 방법 1: Claude Code 스킬 — `/prd-to-linear`

PRD 마크다운을 분석하여 태스크를 자동 분해 + Linear Queued 등록:

```
/prd-to-linear docs/prd-v2.md
```

1. PRD 파일 분석
2. 구현 태스크로 분해 (P1/P2/P3)
3. 사용자 확인
4. Linear에 Queued 상태로 일괄 등록

### 방법 2: Linear 웹 UI에서 수동 등록

1. Linear에서 이슈 생성 (Team: **24Seven**)
2. **title**: 구현할 기능/수정 사항 (간결하게)
3. **description**: AI가 읽고 구현할 상세 요구사항
4. **priority**: Urgent(P1), Medium(P2), Low(P3)
5. **state**: **Queued** 선택

### 방법 3: CLI

```bash
python3 scripts/linear_tracker.py task \
  --title "사용자 프로필 API 추가" \
  --summary "GET /api/users/{id} 엔드포인트 구현. 응답에 이름, 이메일, 가입일 포함." \
  --tags "backend,api" \
  --status "Queued"
```

---

## 하네스 엔지니어링 (Hook 기반 품질 통제)

파이프라인 내부에서 Claude가 코드를 작성할 때, **4개 Hook 시점**에 걸쳐 하네스 엔지니어링이 자동 적용됩니다.
전체 가이드: `.claude/agents/harness-guide.md`

### 하네스 4단계 + Hook 매핑

```
사용자/파이프라인 요청
    │
    v
[Hook: UserPromptSubmit] ─── 하네스 Router 지침 주입
    │                         "코드 작성 요청이면 harness-guide.md를 따르세요"
    │                         1.Router → 2.Context → 3.Loop → 4.Worker
    v
[1단계: Router] 의도 분석
    ├─ 모호 → 되물어보기 (소크라테스식 인터뷰)
    ├─ 명확 → 제약 추출 → 하네스 루프 진입
    └─ 일반 대화 → 표준 응답
    v
[2단계: Context Manager] 필요한 파일만 로딩
    ├─ CLAUDE.md + 해당 모듈 agent.md
    ├─ PLAN.md (Gemini 기획서)
    └─ 관련 소스 파일만 선별
    v
[3단계: Harness Loop] 코드 → 검증 → 수정 반복 (MAX 5회)
    │
    ├──→ Worker(WRITE_CODE) 코드 작성
    │
    ├──→ [Hook: PostToolUse(Edit|Write)] ─── 검증 리마인더
    │         "코드 수정됨 → 커밋 전 lint/typecheck/test 실행하세요"
    │
    ├──→ 자동 검증 (lint → typecheck → test)
    │
    ├──→ [Hook: PreToolUse(git commit)] ─── harness-gate.sh 실행
    │         변경 모듈 자동 감지 → 모듈별 Gate 실행
    │         ├─ Gate1: Lint   (ruff check / npm run lint)
    │         ├─ Gate2: Type   (mypy / tsc --noEmit)
    │         └─ Gate3: Test   (pytest / vitest)
    │         실패 시 → 🚨 커밋 차단 + 에러 피드백 → 루프 재진입
    │         통과 시 → ✅ 커밋 허용
    │
    └──→ Worker(CODE_REVIEW) 최종 리뷰
    v
[4단계: Worker] 역할 분리
    ├─ WRITE_CODE:      fullstack + 모듈별 agent.md
    ├─ TEST_WRITER:     tdd-smart-coding
    ├─ CODE_REVIEW:     ai-critique (GPT + Gemini)
    └─ SECURITY_REVIEW: OWASP Top 10
    v
[Hook: Stop] ─── ralph-stop-hook.sh
    ├─ fix_plan.md 미완료 항목 확인
    ├─ 테스트/린트 최종 검증
    ├─ 미충족 시 → 루프 계속 (block)
    ├─ 충족 시 → 종료 허용 (allow)
    └─ max-iterations 도달 시 → 강제 종료 + Telegram 알림
```

### Hook 설정 상세

| Hook 시점 | 설정 위치 | 역할 |
|-----------|----------|------|
| `UserPromptSubmit` | `.claude/settings.json` | 모든 프롬프트에 하네스 Router 지침 주입 + TODO 리마인더 |
| `PreToolUse(git commit)` | `.claude/settings.json` → `.claude/hooks/harness-gate.sh` | 커밋 전 모듈별 lint/type/test Gate 실행, 실패 시 커밋 차단 |
| `PostToolUse(Edit\|Write)` | `.claude/settings.json` | 코드 수정 후 검증 리마인더 (Gate 미통과 시 커밋 차단 경고) |
| `Stop` | `.claude/settings.json` → `scripts/ralph-stop-hook.sh` | fix_plan 완료 여부 + 검증 상태 확인, 미충족 시 루프 block |

### harness-gate.sh 모듈별 Gate

| 모듈 | Gate1: Lint | Gate2: Type | Gate3: Test |
|------|------------|-------------|-------------|
| `api` | `uv run ruff check .` | `uv run mypy app/` | `uv run pytest --tb=short -q` |
| `web` | `npm run lint` | `npx tsc --noEmit` | — |
| `agent` | `uv run ruff check .` | `uv run mypy agent/` | `uv run pytest --tb=short -q` |
| `contracts` | — | `npx tsc --noEmit` | — |

> 변경된 모듈만 자동 감지하여 해당 모듈의 Gate만 실행. docs/scripts만 변경 시 Gate 건너뜀.

### 하네스 스킬

| 스킬 | 단계 | 설명 |
|------|------|------|
| `/harness-router` | 1단계 | 의도 분석 + 라우팅 (모호→인터뷰, 명확→루프) |
| `/harness-context` | 2단계 | 컨텍스트 로딩 프로토콜 (가림막 원칙) |
| `/harness-loop` | 3단계 | 자동 교정 루프 (코드→검증→수정 반복) |
| `/harness-worker` | 4단계 | 역할 분리 실행 (작성/테스트/리뷰/보안) |

---

## 모듈 토글 설정

`.env` 파일에서 `FLOWOPS_*` 변수로 파이프라인 모듈을 ON/OFF 할 수 있습니다:

```env
# 모듈 토글 (미설정 시 기본값: true)
FLOWOPS_LINEAR_WATCHER=true     # Linear 이슈 감지
FLOWOPS_METAPROMPT=true         # Claude 메타프롬프트 기획(관측형 사전 정제) → PLAN.md/refined
FLOWOPS_GEMINI_PLAN=false       # 레거시 Gemini 기획(METAPROMPT=false일 때 폴백)
FLOWOPS_CODEX_REVIEW=true       # Codex QA → REVIEW.md 생성
FLOWOPS_AUTO_MERGE=true         # 직접 머지 (false: PR 생성)
FLOWOPS_TELEGRAM=true           # Telegram 알림
# 거버넌스 게이트(머지 직전 SSOT) — 상세: 위 "Step 5.5"
FLOWOPS_GOVERNANCE=true         # 마스터(off면 게이트 전체 우회·회귀 0)
FLOWOPS_GOVERNANCE_CONTRACT=true     # contract-drift 차단
FLOWOPS_GOVERNANCE_TICKET=true       # ticket-ref 차단
FLOWOPS_GOVERNANCE_TRACE=true        # plan-trace 권고(비차단)
FLOWOPS_GOVERNANCE_RISK_DEMOTE=true  # HIGH-tier→PR 강등
FLOWOPS_GOVERNANCE_PROMOTE=true      # 고복잡도 direct-merge 산출물 승격
```

설정 로더: `scripts/pipeline_config.sh`
- `is_enabled "FLOWOPS_*"` 함수로 활성화 여부 확인
- 미설정 변수는 기본 `true`
- `false`, `0`, `off`, `no` → 비활성화

---

## 로컬 검증 vs CI 검증

| 검증 주체 | 역할 | 시점 | 검증 항목 |
|-----------|------|------|-----------|
| `ralph-stop-hook.sh` | 빠른 피드백 (Claude 루프 내) | 매 iteration | fix_plan 완료 + pytest + ruff |
| **거버넌스 게이트** | **권위** (머지 직전, 인파이프라인) | 머지 직전 | `pre_merge_gate.py` — contract/ticket/risk |
| GitHub Actions CI | 공식 게이트 (PR 머지 조건) + `governance` 미러 | PR 생성/업데이트 | pytest + ruff + pnpm lint + build + 게이트 미러 |
| AI Review (GPT) | 코드 품질 검증 | PR 생성 | 버그/보안/성능/설계 리뷰 |

---

## 전체 상태 흐름

```
Backlog ──(수동)──→ Wait ──(수동)──→ Queued
                                       │
                               ┌───────┴───────┐
                               │ Webhook 감지   │
                               │ 또는 수동 실행  │
                               └───────┬───────┘
                                       ↓
                                  In Progress
                                       │
                                  [Claude 자율 작업]
                                  [테스트/린트 검증]
                                       │
                              ┌────────┴────────┐
                              ↓                 ↓
                            Done             Backlog
                       (머지 또는 PR)      (실패/건너뜀)
                              │
                     ┌────────┴────────┐
                     ↓                 ↓
               AUTO_MERGE ON    AUTO_MERGE OFF
               (직접 머지→push)  (PR→CI→머지)
                     │                 │
                     │          ┌──────┴──────┐
                     │          │ CI 통과      │
                     │          │ AI Review    │
                     │          │ auto-merge   │
                     │          └──────┬──────┘
                     └────────┬───────┘
                              ↓
                        post-merge.yml
                        Linear → Done
                        Telegram 알림
                              ↓
                        다음 Queued 이슈
                        (순차 반복)
```

---

## 스크립트 참조

| 스크립트 | 용도 | 실행 주체 |
|----------|------|-----------|
| `auto_dev_pipeline.sh` | 파이프라인 오케스트레이터 (v6 멀티 Agent) | Webhook / 수동 |
| `webhook-doctor.sh` | webhook 환경 자동 진단·정리·기동·검증 (권장 진입점) | 수동 1회 실행 |
| `webhook_doctor_linear_check.py` | Linear 등록 webhook URL ↔ ngrok 도메인 매칭 확인 헬퍼 | doctor에서 호출 |
| `webhook_server.py` | Linear Webhook 수신 서버 | 상시 실행 데몬 |
| `linear_watcher.py` | Queued 이슈 감지 → fix_plan 생성 | 파이프라인 Step 1 |
| `fix_plan_generator.py` | ChatGPT FC로 구조화된 fix_plan 생성 | watcher (--use-gpt-plan) |
| `generate_plan_with_gemini.sh` | Gemini CLI로 PLAN.md 기획서 생성 | 파이프라인 Step 2 |
| `run_codex_review.sh` | Codex CLI로 REVIEW.md QA 리뷰 생성 | 파이프라인 Step 4 |
| `linear_reporter.py` | 결과 → Linear 보고 | 파이프라인 Step 3 |
| `auto_pr_creator.py` | 자동 PR 생성 + auto-merge 설정 | 파이프라인 Step 4 |
| `linear_confirmer.py` | Confirm → PR merge 또는 로컬 merge | 수동 / Cron |
| `linear_tracker.py` | Linear CRUD 유틸 | 스킬 / 수동 |
| `gpt_pr_review.py` | ChatGPT FC PR 코드 리뷰 | GitHub Actions |
| `telegram_notify.py` | Telegram 알림 | 각 스크립트에서 호출 |
| `ralph-stop-hook.sh` | Claude 종료 조건 검증 | Stop Hook |
| `ralph-loop.sh` | Ralph 자율 루프 실행 | 수동 |
| `pipeline_config.sh` | 모듈 토글 설정 로더 | 파이프라인에서 source |
| `pipeline_config.py` | Python용 설정 로더 | Python 스크립트에서 import |
| `start-webhook.sh` | Webhook 서버 + ngrok 시작 | 수동 |
| `stop-webhook.sh` | Webhook 서버 + ngrok 중지 | 수동 |

---

## 환경 설정

환경변수, GitHub Secrets, Branch Protection 설정은 **[docs/setupClaude.md](setupClaude.md)**를 참조하세요.

---

*초기 셋업: [docs/setupClaude.md](setupClaude.md) | 스킬 가이드: [docs/skills.md](skills.md)*
