---
title: 다프로젝트 무인 딜리버리 아키텍처 (3-서비스 체인 · YAML 제어면 · 구독형 전용)
category: architecture
status: current
last_updated: 2026-08-04
related:
  - clickeye-api/app/api/v1/intake.py
  - templates/harness-core/enforce/src/enforce.ts
  - templates/harness-core/enforce/src/gitguard.ts
  - templates/harness-core/enforce/src/secrets.ts
  - templates/harness-core/hooks/gitguard-gate.cjs
  - scripts/tests/test_enforcement_gate.sh
  - scripts/workspace_map.py
  - scripts/seat_map.py
  - scripts/with_seat.sh
  - scripts/runner_dispatcher.sh
  - scripts/runner_clone.sh
  - scripts/auto_dev_pipeline.sh
  - scripts/delivery_verify.sh
  - scripts/workspace_provision.sh
  - scripts/tests/test_workspace_delivery.sh
  - templates/harness-core/governance-workspace.policy.json
  - clickeye-api/app/models/intake.py
  - clickeye-api/app/models/llm_usage_ledger.py
  - clickeye-api/app/models/user_anthropic_credentials.py
  - clickeye-api/app/models/delivery_profile.py
  - clickeye-api/app/services/llm_gateway.py
  - clickeye-api/app/api/v1/llm.py
  - clickeye-api/app/api/v1/governance.py
  - scripts/usage_ingest.py
  - governance/policy.py
  - governance/core.py
  - scripts/auto_dev_pipeline.sh
  - scripts/webhook_server.py
  - templates/harness-core/PROMPT.workspace.md
  - scripts/webhook_worker.py
  - scripts/clickeye_cron.txt
  - scripts/linear_watcher.py
---

# 다프로젝트 무인 딜리버리 아키텍처

ClickEye 는 3-서비스 체인의 **구현부**다. 팀원의 손을 거치지 않고 수주부터 정합성 테스트까지
완주하는 것이 존재 이유다.

> **이 문서는 2026-07-28 전면 재작성본이다.** 초판은 제어면 SSOT 를 DB 로 두고(`D-3`) 실행면을
> "샤드 병렬"로 잡았다. 둘 다 틀렸다 — 제어면 정본은 **서비스 #2 가 자동 생성하는 YAML** 이고,
> 실행면의 핵심은 병렬성이 아니라 **완주 보장 + 다계정 동시 실행**이다. 변경 이력은 §9.

---

## 1. 3-서비스 체인

```
[서비스 1] 크롤링 — SI 수주 사이트 리서치 → 수주 후보 제안
                          │
                          ▼  (수주 확정)
[서비스 2] 기획 + YAML 자동 생성·선택 — 프로젝트 성격에 맞는 개발가이드 YAML 을 생성/선택
                          │
                          ▼  POST /api/v1/intake  (기획 + YAML)
[서비스 3] ClickEye 딜리버리
   ① 인테이크 수신·정제(메타프롬프팅)
   ② Linear 에 설계·구현 티켓 **전량** 발급
   ③ webhook 순차 실행 — 티켓 하나 완료 → 다음 티켓
   ④ 전 티켓 A-Z 완주 (실패 무유실)
   ⑤ 프로젝트 정합성 테스트
   ⑥ 서비스 2 로 콜백
```

**무인(unattended)이 요구사항이다.** ①~⑥ 어디에도 사람의 확인 단계가 있으면 체인이 끊긴다.
이것이 아래 모든 결정의 상위 제약이다.

### 1-1. 수신면은 이미 있다

`clickeye-api/app/models/intake.py` 의 `IntakeRequest` 가 이 체인 형태와 일치한다.

| 필드 | 체인에서의 역할 |
|---|---|
| `IntakeServiceKey`(`key_hash`, `organization_id`) | 서비스 #2 의 기계 인증 |
| `source_url` | 서비스 #1 의 크롤링 출처 |
| `input_type` · `payload`(JSON) · `target` · `priority` | 기획 + **YAML 페이로드** |
| `idempotency_key` | 재전송 중복 방지 |
| `normalized_text` → `refined_text` · `refine_status` | 메타프롬프팅 정제 |
| `callback_url` · `callback_status` · `callback_attempts` · `callback_next_retry_at` | 서비스 #2 회신 |
| `project_id` | 프로젝트 승격 |

→ **①은 구현돼 있다.** 남은 것은 payload 에 실릴 **YAML 스키마 계약**(§3)이다.

---

## 2. 5-Plane

| Plane | 책임 | 현재 | 목표 |
|---|---|---|---|
| **① 판정면** | 검증·위험분류·트리아지 | 순수함수 + `Policy` 주입 완료 | YAML 정책 소비 |
| **② 제어면** | 모드·승인·차단조건·한도 | `FLOWOPS_*` env | **서비스 #2 생성 YAML**(정본) + DB 미러 |
| **③ 집행면** | 툴 호출 **전** 차단 | 플랜/커밋 게이트 2개 | 프로젝트 중립 게이트 엔진 |
| **④ 실행면** | **완주 + 다계정 동시 실행** | 전역 락 · 단일 순차 | 시트 풀 · 프로젝트 N 병행 · 무유실 |
| **⑤ 기록면** | 결정·경위·수명주기·**시트별 토큰** | ✅ `delivery_events` 1급(P9) + 원장 | 시트 축(P4) |

초판과 달라진 곳은 ②(정본 위치)와 ④(핵심 정의)다.

---

## 3. 제어면 — 기계 생성 YAML

### 3-1. `D-3` 철회

| | 초판 | **재작성** |
|---|---|---|
| 정본 | DB `DeliveryProfile` | **서비스 #2 가 생성한 YAML** |
| DB 역할 | SSOT | 런타임 미러 / 캐시 |
| 근거 | "파일 방식은 전사 배포가 안 됨" | 배포 주체가 **사람이 아니라 서비스 #2** 이므로 그 논거가 성립하지 않는다 |

### 3-2. 사람이 쓰는 YAML 과 기계가 쓰는 YAML 은 다르다

참조 구조(infraeye3 `CONTROL.yaml`)는 **사용자 소유·수동 편집·에이전트 수정 금지**를 전제로
설계됐다. 우리 YAML 은 **서비스 #2 가 자동 생성·선택**한다. 전제가 다르므로 설계도 달라야 한다.

| 축 | 사람 저작 (참조 구조) | **기계 저작 (우리)** |
|---|---|---|
| 신뢰 근거 | 사용자가 직접 썼다 | **서비스 #2 서명 + 스키마 버전** |
| 오류 처리 | 사용자가 고친다 | **fail-closed + 서비스 #2 로 거부 콜백** |
| 주석 | 사람용 설명 | **provenance**(어느 템플릿·어떤 근거로 선택됐는가) |
| 변경 감지 | `records-lint` RL-08(서명 없는 변경) | 서명 검증 + 해시 대조 |
| 미지정 필드 | 사용자 부주의 | **기본값 승계**(이미 `Policy.from_dict` 가 이렇게 동작) |

**핵심 함의:** YAML 이 기계 생성물이면 "사용자만 편집 가능"이라는 보호는 성립하지 않는다.
대신 **출처 인증**이 그 자리를 대신한다 — 서비스 #2 의 서비스 키로 서명되지 않은 YAML 은
거부한다. ClickEye 내부 에이전트의 수정 금지는 그대로 유지한다(집행면 `G-04` 상당).

### 3-3. 참조 구조에서 가져올 것 / 버릴 것

| 절 | 판정 |
|---|---|
| `global`(mode/state/pause_strategy) · `auto_stop_conditions` · `retry_limits` | **가져온다.** 무인 운전의 안전 정지 조건 |
| `concurrency`(슬롯·샤드·리뷰어 정족수·self_review 금지) | **가져온다.** §5 다계정 실행의 상한 |
| `git`(forbidden/per_use_approval) · `gates`(compile/test/check) · `continuous_gates` | **가져온다.** 프로젝트 스택별로 달라지는 부분 = 플러그인 |
| `gate`(v1_gates/protected_paths/fail_closed) · `identity`(cwd→role) | **가져온다.** 집행면 설정 |
| `blockers` | **가져온다.** 단 소유자가 외부이므로 무인 진행 시 **정지 사유**가 된다 |
| `cycle_approval: REQUIRED` · `approvals` 절 | **버린다.** 사람 승인 게이트는 무인 체인을 끊는다. 대신 **자동 승인 + auto_stop_conditions 위반 시에만 정지** |
| `fuzzing` | 보류. 파싱 진입점이 생긴 뒤 재상정 |

### 3-4. `Policy` 는 그대로 쓴다

P0 에서 만든 `governance/policy.py` 는 YAML 채택과 **충돌하지 않는다.** YAML→dict 파싱을
앞단에 두면 `Policy.from_dict()` 가 그대로 소비한다. 이미 갖춘 성질이 여기서 값을 한다:

- **미지정 필드 기본값 승계** — 서비스 #2 가 최소 필드만 채워도 동작
- **알 수 없는 키 거부** — 템플릿 오타로 정책이 조용히 무시되는 것 차단
- **static 모드(env 미조회)** — 프로젝트 간 정책 누출 차단. 다계정 동시 실행의 전제
- **fail-closed 파싱** — §3-2 의 거부 콜백에 그대로 연결

`Policy` 의 커버리지는 현재 머지게이트 정책(계약면·고위험 경로·이슈 키·토글·임계값)뿐이다.
§3-3 의 나머지 절은 **`Policy` 를 확장하지 말고 형제 값객체로 분리**한다 — 판정면 정책과
실행면 제어를 한 객체에 섞으면 커널의 순수성이 깨진다.

---

## 4. 구독형 전용 (신규 핵심가치)

**모든 설계·개발·구현은 내부 OAuth 구독형 토큰으로만 수행한다. 종량 API(크레딧) 경로는
사용하지 않는다.** 구독형 내에서 최상위 모델로 올리는 것은 허용한다.

### 4-1. 현재 상태 — 절반은 이미 맞다

파이프라인은 이미 올바르게 동작한다.

```
scripts/auto_dev_pipeline.sh:266,322   unset ANTHROPIC_API_KEY   # 구독 세션 사용
scripts/ralph-loop.sh:97               unset ANTHROPIC_API_KEY
scripts/prompt-evolve-eval.sh:117      unset ANTHROPIC_API_KEY
```

원장도 두 출처를 이미 구분한다 — `LlmKeySource.subscription_seat` / `org_api_key`,
그리고 `_compute_cost()` 는 구독시트에 대해 `cost = NULL` 을 반환한다.

### 4-2. 문제 — 분류기일 뿐 강제기가 아니다

`clickeye-api/app/services/llm_gateway.py:174` `_resolve_key_source()` 는 **어떤 키가
쓰였는지 사후 분류**한다. 조직 키가 설정돼 있으면 그것을 **그대로 사용하고** `org_api_key`
로 기록한다. 거부하지 않는다.

| 필요 | 상태 |
|---|---|
| 종량 경로 **거부** | ❌ 없음 |
| 종량 경로 **기록** | ✅ 있음 |

→ ✅ **구현 완료(2026-07-28, P3)** — `FLOWOPS_SUBSCRIPTION_ONLY`(opt-in) 활성 시 `org_api_key`
해석 호출과 OpenAI 폴백(무조건 종량)을 **실행 전 거부**(`SubscriptionOnlyError`), 거부도 원장에
error 행으로 기록(D-9). 부수 발견·수정: Anthropic 키 부재 시 유료 OpenAI 폴백이
`subscription_seat`·cost=None 으로 **무료 위장 기록**되던 누수 — 폴백 실사용 시 `org_api_key` 로
정정. 토글은 P2 에서 제어면 YAML `auto_stop_conditions.cost_incurring_operation` 으로 이관.

### 4-3. 감사 대상 — 종량 잔존 경로

아래는 종량 API 를 쓸 가능성이 있어 **전수 감사 후 구독형으로 전환하거나 제거**해야 한다.

`scripts/gpt_pr_review.py` · `scripts/fix_plan_generator.py` → **제거 완료(2026-07-30, F-5)**.
`scripts/run_codex_review.sh`(codex CLI 구독형) · `scripts/generate_plan_with_gemini.sh`(gemini CLI 구독형)은
종량이 아니라 구독형 CLI 로 확정 — 감사 종료. 잔존 감사 대상은 clickeye-api 제품면뿐:
`clickeye-api/app/api/v1/presets.py` · `clickeye-api/app/services/claude_service.py`

파이프라인 STEP C(Codex QA 리뷰)와 레거시 Gemini 기획이 여기 포함된다. **리뷰 2인 정족수를
구독형으로 어떻게 확보할지**가 별도 설계 과제다(같은 구독 계정으로 2인 리뷰를 세면 독립성이
없다 → §5 의 시트 풀과 연결된다).

### 4-4. 최상위 모델 승격

`llm_gateway._tier_model()`(`:141`)이 `anthropic_model_advanced` / `_default` / `_light`
티어를 이미 라우팅한다. "구독형을 최상위 모델로 변경 가능"은 **이 티어 설정으로 수용**되며
새 메커니즘이 필요 없다. 티어 선택은 제어면 YAML 에 둔다.

### 4-5. 거버넌스 트리아지 예산 축 전환

구독형 전용에서는 `cost` 가 **항상 NULL** 이다. 따라서 현재 트리아지의 비용 축
(`assess_budget` 의 `COST_LIMIT`/`COST_WARN`)은 **무의미해진다.**

| 축 | 구독형 전용에서의 의미 |
|---|---|
| `cost` | ❌ 항상 NULL → 판정 불가 |
| **tokens** | ✅ 유효. 시트별 누적 |
| **rate(rpm/tpm)** | ✅ **필수로 승격.** 현재 `assess_rate` 는 윈도우 카운터 부재로 항상 skip 되는 "전방 훅" |

→ `assess_rate` 의 슬라이딩 윈도우 카운터가 **선택 기능에서 필수 기능으로 바뀐다.** 구독형은
레이트 한도가 실질 제약이고, 다계정 동시 실행에서는 시트별로 관측해야 한다.

---

## 5. 다계정 동시 실행 (신규 핵심가치)

**여러 프로젝트를 동시 다발로 구현할 수 있어야 한다.** 계정을 여러 개 만들어야 한다면 만들고,
그 경우 **계정마다 토큰을 모니터링**해야 한다.

### 5-1. 현재 상태 — 구조적으로 불가능

| 차단 지점 | 코드 | 성질 |
|---|---|---|
| 전역 파이프라인 락 | `auto_dev_pipeline.sh:32,89-100` — `.ralph/.pipeline_lock` PID 단일 락. 실행 중이면 `exit 0` | **동시 실행 원천 차단** |
| 단일 티켓 워처 | `auto_dev_pipeline.sh:139` — `linear_watcher.py --per-task --limit 1` | 1건씩 순차 |
| 프로젝트 전역 작업 경로 | `.ralph/fix_plan.md` · `.ralph/PLAN.md` · `.ralph/TASK.md` 단일 경로 | 병행 시 상호 덮어씀 |
| 프로세스 전역 세마포어 | `llm_gateway.py:43` — `asyncio.Semaphore(llm_gateway_max_concurrency)` | 시트별이 아님 |
| 단일 자격증명 | `user_anthropic_credentials.py:13` — `credential_type = "api_key" 고정`, `UniqueConstraint(user_id, credential_type)` | **OAuth/시트 타입 없음. 풀 개념 없음** |

### 5-2. 원장에 시트 축이 없다

`LlmUsageLedger` 컬럼: `project_id` · `task_id` · `provider` · `key_source` · `model` ·
`input_tokens` · `output_tokens` · `cost` · `request_kind` · `meta` · `status`.

**어느 계정(시트)이 썼는지 식별하는 컬럼이 없다.** "구독시트였다"는 알 수 있지만 "몇 번
시트였다"는 알 수 없다. → **"각각의 계정마다 토큰 모니터링"이 현재 불가능하다.**

> **현행화(2026-07-29, D-8/P4·F-1):** `seat_id`(FK `user_anthropic_credentials`, ondelete
> SET NULL) 1급 컬럼이 추가됐고, 로컬 `claude -p` 배치 사용량을 이 축으로 원장에 적재하는
> 인제스트 배관(`POST /api/v1/llm/ingest/usage` · `scripts/usage_ingest.py`, CE-328)이
> 완료됐다. `session_id` 컬럼(멱등 키)도 함께 추가. 이로써 계정별 토큰 모니터링의 나머지
> 절반(로컬 소비)이 연결된다. 잔여(정제·분해 지점 json 전환)는 F-1 후속.

### 5-3. 필요한 것

1. **Seat 레지스트리** — `credential_type` 에 OAuth/구독 시트를 추가하고, `user_id` 1:1
   제약을 풀어 **시트 풀**로 만든다. 시트마다 상태(가용/한도도달/차단)를 갖는다.
2. **프로젝트 ↔ 시트 배정** — 동시 실행 프로젝트 수 ≤ 가용 시트 수. 배정은 제어면 YAML 의
   `concurrency` 상한을 따른다.
3. **원장에 `seat_id` 추가** — 시트별 토큰/레이트 집계의 전제. `meta`(JSONB)에 밀어넣지 말고
   1급 컬럼으로 둔다(모니터링 쿼리·게이트 판정이 이 축을 읽는다).
4. **시트별 세마포어·레이트 카운터** — 프로세스 전역 → 시트 스코프.
5. **작업 경로 격리** — `.ralph/` 단일 경로 → 프로젝트별(또는 worktree별) 경로.
6. **락 세분화** — 전역 PID 락 → 프로젝트 단위 락. → 🔄 v1 (2026-08-01, CE-339): 전용
   워크스페이스 러너는 키별 락(`.ralph/.pipeline_lock.<key>`), 단일 automap 러너는 전역 락 유지.

#### 시트 풀 매핑 v1 (2026-08-03, CE-345)

위 2번(프로젝트↔시트 배정)의 **로컬 절반**. 워크스페이스별 전용 러너가 자기 시트로 `claude`
를 실행한다. 운영 원칙은 **"전용 러너 = 전용 시트"** — 시트 하나를 두 워크스페이스에 걸면
`assign` 이 `--force` 없이 거부한다(같은 계정 동시 실행 = 원장·레이트 한도가 거짓이 된다).

- **원장**: `.ralph/seats.json`(git 미추적) — `scripts/seat_map.py` 가 관리(stdlib·오프라인·멱등).
  토큰 **값**은 원장에도 stdout 에도 담지 않는다(경로만). `.ralph/workspaces.json` 과는
  완전 분리 — 서로 읽지 않으며 assignments 키는 workspace_key 문자열일 뿐이다.
- **주입 지점**: `auto_dev_pipeline.sh` `apply_seat_env()` 가 STEP A(정제)·STEP B(구현)
  **서브셸 내부**에서 호출된다(export 가 서브셸 로컬 → 이터레이션 간 누출 없음).
- **서버 경로와의 관계**: `scripts/with_seat.sh`(P4 T3, 서버 원장에서 시트 토큰 수령)가 이미
  `CLAUDE_CODE_OAUTH_TOKEN`/`CLICKEYE_SEAT_ID` 를 주입했으면 로컬 경로는 **아무 것도 하지
  않는다**(상위 주입 존중 = 상호배타). 두 경로는 공존하며 이중 시트가 생기지 않는다.
- **토글**: `FLOWOPS_SEAT_POOL`(미설정=off → 현행 로그인 세션, 회귀 0) ·
  `FLOWOPS_SEAT_POOL_STRICT=true`(미배정/타 러너 점유 시 폴백 대신 해당 단계 스킵).
  off 가 아니어도 미배정·`pending_login`·인증 파일 미판독은 경고 후 기본 세션 폴백.
- **오귀속 금지 2종**(STRICT 무관): ① 배정 시트가 `disabled` 면 폴백하지 않고 단계를 막는다
  ② 토큰이 안 읽히거나 비면 `CLICKEYE_SEAT_ID` 를 붙이지 않는다(시트 참칭 금지).
  스킵된 티켓은 빈 브랜치로 소진되지 않고 기존 실패 경로(재시도 복귀/Backlog)로 되돌아간다.

**부트스트랩**(시트 계정마다 1회, 그 계정으로 로그인된 클린 셸에서):

```bash
mkdir -p .ralph/seats && umask 077
claude setup-token                       # 시트 계정 OAuth 토큰 발급 → 출력값 복사
read -rs TOKEN                           # 셸 히스토리에 남기지 않고 입력(에코 없음)
printf '%s' "$TOKEN" > .ralph/seats/seat-a.token && unset TOKEN
ls -l .ralph/seats/seat-a.token          # -rw------- (600) 확인
python3 scripts/seat_map.py register-seat --id seat-a --token-file .ralph/seats/seat-a.token
python3 scripts/seat_map.py assign --workspace <workspace_key> --seat seat-a
python3 scripts/seat_map.py resolve --resolve-key <workspace_key>   # 비면 배정/상태 점검
```

한도 도달 계정은 `set-status --seat seat-a --status disabled` 로 내린다 — 해당 워크스페이스는
기본 계정으로 폴백하지 않고 **단계를 건너뛴다**(오귀속 금지). 잔여: 서버 원장 시트 축과의
동기화·자동 재배정.

#### 러너 디스패처 v1 (2026-08-03, CE-346)

CE-339(키별 락)·CE-345(시트 원장)가 만든 것은 병행의 **허용 조건**이었다. 디스패처는 그 위에서
실제로 병행을 **만들어내는** 층이다 — 5분 틱마다 두 원장을 읽어 워크스페이스별 전용 러너를
스폰·감시·회수한다(`scripts/runner_dispatcher.sh`, cron `*/5 9-18 * * 1-5`).

- **git 격리 = 워크스페이스별 로컬 clone**(`scripts/runner_clone.sh`, 기본 루트
  `$HOME/.clickeye-runners/<key>`). 한 체크아웃을 공유하면 키 없는 스크래치
  (`.ralph/fix_plan.md`·`.ralph/.task_mapping.json`)가 레이스하고 이터레이션 내내 공유 HEAD 를
  점유해 러너들이 서로를 깨뜨린다. `git worktree` 는 **같은 브랜치를 두 곳에 체크아웃할 수
  없어**(main 상시 충돌) 기각했다. clone 은 독립 refs + 독립 `.ralph` 를 공짜로 준다.
- **clone 의 origin 은 PRIMARY 가 아니라 PRIMARY 의 origin(GitHub)** 으로 재지정한다.
  `git clone <PRIMARY>` 의 기본 origin 을 그대로 두면 러너의 `push origin main` 과
  `push origin --delete ralph/<KEY>` 가 **PRIMARY 체크아웃을 겨냥한다**(브랜치 삭제까지
  성사됨을 실측). 재지정으로 push/PR/pull 대상이 현행 단일 러너와 같아지고, "PRIMARY git
  무접촉" 불변식이 실질적으로 성립하며, clone 의 main 최신성도 canonical 로 해결된다.
- **공유는 심볼릭 6종만**: `.env` · `.ralph/seats.json` · `.ralph/seats/` ·
  `.ralph/workspaces.json` · `workspaces/`(키별 서브디렉터리라 무충돌) · `logs/`(관측 일원화).
  나머지 `.ralph/` 는 clone-로컬 — 락·스크래치 격리가 이 설계의 본질이다. 프로비저닝은 멱등이며
  링크 자리에 실체가 있으면 덮어쓰지 않고 건너뛴다.
- **스폰 산정**(모두 통과해야 스폰): mapped → 시트 배정 + `active` → 그 키의 러너 미실행
  → 그 **시트**의 러너 미실행 → 캡(라이브+이번 틱 스폰 < active 시트 수) → 해당 접두사
  Queued 실재(`linear_watcher --check-only`, 파일 무기록). Queued 확인이 마지막인 이유는
  어차피 스폰 못 할 후보에 Linear API 비용을 치르지 않기 위해서다. 틱 중첩은
  `flock .ralph/dispatch/.dispatch_lock` 이 막는다.
- **시트 배타는 디스패처가 담당한다.** 파이프라인의 `.ralph/.seat_lock.<seat_id>` 는
  **clone-로컬**이라 clone 간 상호배제가 되지 않는다(실측). 같은 시트가 두 워크스페이스에
  걸리면 두 러너가 같은 계정으로 동시에 돌아 원장·레이트 한도가 거짓이 된다. 방어는 두
  겹이다: ① `seat_map.py assign` 의 1:1 가드(`--force` 없이 중복 배정 거부) ② 디스패처
  마커의 `seat_id` — 그 시트를 쓰는 라이브 러너가 있으면 스폰하지 않는다.
- **회수는 마커 정리까지만**: 마커 형식은 `<pid> <epoch> <seat_id>`. `kill -0` 뿐 아니라
  `/proc/<pid>/cmdline` 으로 신원까지 확인해 **PID 재사용**(마커가 남은 사이 OS 가 그 PID 를
  재배정)을 회수한다 — 확인하지 않으면 남의 프로세스를 러너로 오인해 그 키가 영구 스킵된다.
  `/proc` 를 못 읽는 환경에서는 판단을 보류(생존 인정)하며, 확인 불가를 회수 근거로 삼지
  않는다. `DISPATCH_STALE_HOURS`(기본 6) 초과 생존은 경고만 하고 **강제 종료하지 않는다**
  (러너가 브랜치 중간 상태를 들고 있을 수 있다).
- **스폰 env 가 공유 `.env` 를 이긴다**: 러너 clone 은 PRIMARY 의 `.env` 를 심볼릭으로
  공유하는데, `pipeline_config.sh` 의 기본 동작은 무조건 덮어쓰기다. 운영자가 `.env` 에
  `FLOWOPS_SEAT_POOL=false` 를 써두면 전 러너가 개인 계정으로 폴백해 CE-345 가 막은 오귀속이
  재발한다. 디스패처는 `FLOWOPS_ENV_KEEP_EXISTING=true` 를 함께 넘겨 **이미 set 된 값은
  `.env` 가 덮지 못하게** 한다(이 마커가 없으면 로더 동작은 이전과 동일 — 회귀 0).
- **PRIMARY git 무접촉**: 디스패처·프로비저닝은 PRIMARY 저장소에서 checkout/commit 을 하지
  않는다. 인터랙티브 작업과 cron 이 같은 체크아웃을 놓고 싸우지 않기 위한 불변식이다.
- **토글**: `FLOWOPS_RUNNER_DISPATCH`(이중 opt-in, 미설정=SKIP exit 0 → cron 등록해도 무해) ·
  `FLOWOPS_RUNNER_DISPATCH_DRYRUN`(산정 결과만 출력).
**활성 절차** (순서를 지킬 것 — 1번을 건너뛰면 티켓이 두 러너에 이중 수거된다):

1. **단일 러너에서 전용 프로젝트를 제외한다.** cron 정본의 `auto_dev_pipeline.sh --once`
   라인에 `WATCHER_EXCLUDE_PREFIXES` 를 붙인다(**탭 구분** — 접두사가 공백을 포함하므로 공백
   구분은 안전하지 않다). `linear_watcher.py` 가 이 env 를 직접 읽으므로 파이프라인 본체는
   손대지 않는다. 검증: `python3 scripts/linear_watcher.py --dry-run` 에 제외 대상이 없을 것.
   ```bash
   WATCHER_EXCLUDE_PREFIXES="$(printf '[수주:aaa11111] \t[수주:bbb22222] ')" \
     bash scripts/auto_dev_pipeline.sh --once
   ```
2. 워크스페이스마다 시트를 배정한다(`seat_map.py assign`, 1시트:1워크스페이스).
3. `FLOWOPS_RUNNER_DISPATCH_DRYRUN=true` 로 산정 결과를 먼저 읽는다.
4. `FLOWOPS_RUNNER_DISPATCH=true` 로 전환한다.

> **사실 A — 워크스페이스 딜리버리는 배선되었다(CE-347, `FLOWOPS_WORKSPACE_DELIVERY`).**
> 이전 판의 "허상" 서술은 이 토글이 없던 상태를 가리킨다. 그때는 구현이
> `workspaces/<key>`(남의 레포)에서 일어나는데 브랜치·커밋확인·머지·push 는 ClickEye 레포를
> 대상으로 돌아가서, GitHub main 에는 빈 커밋에 가까운 부기만 남고 Linear 티켓은 Done 까지
> 갔다 — "완주했는데 산출물이 없다". 이제 토글이 명시 활성이고 구현 대상이 self-repo 가
> 아니면 브랜치 생성·구현 커밋 확인·거버넌스·push 가 모두 고객 clone 을 향한다(§5-5).
> **v1 은 태스크 브랜치만 고객 origin 에 push 한다** — 고객 기본 브랜치로의 머지는 고객
> 소유이며 파이프라인이 대신 하지 않는다. 토글 미설정 또는 자기레포 이슈는 기존 경로 그대로다.
>
> **v1 관측 한계(운영 수동 정리)**: ① clone 회수 정책이 없다 — `$HOME/.clickeye-runners/<key>`
> 는 계속 쌓이며 워크스페이스가 폐기돼도 자동 삭제되지 않는다. ② `logs/` 를 전 러너가 공유하므로
> 머지 로그(`merge_<초단위>.log`)가 같은 초에 겹치면 덮어쓰기가 나고, 메트릭 원장
> (`logs/metrics/pipeline_runs.jsonl`)은 러너별 레코드가 인터리브된다. 두 항목 모두 러너 수가
> 늘기 전에 정리 정책이 필요하다.

### 5-4. 리뷰 독립성과 시트

§4-3 의 문제가 여기서 풀린다. 리뷰 2인 정족수를 **서로 다른 시트**에 배정하면 종량 API 없이도
독립 리뷰가 성립한다. 시트 풀은 동시성 자원이자 **역할 분리 자원**이다.

### 5-5. 고객 레포 딜리버리 리다이렉트 v1 (CE-347)

§5-3 사실 A 가 지목한 결함을 해소한다. 워크스페이스 모드에서 git 조작 대상을 ClickEye 레포
(`PROJECT_DIR`)에서 고객 clone(`IMPL_WORKDIR`)으로 돌린다.

**발동 조건(3중 게이트, 하나라도 불충족이면 기존 경로 그대로)**

1. `FLOWOPS_WORKSPACE_DELIVERY` 이중 opt-in(`is_enabled` + 비어있지 않음) — 미설정 = off
2. `FLOWOPS_WORKSPACE` + `WORKSPACE_KEY` + `workspaces/<key>` 존재 (`resolve_impl_workdir` 내포)
3. `IMPL_WORKDIR != PROJECT_DIR` — 자기레포 이슈는 켜져 있어도 기존 머지 경로

**리다이렉트 지점** — 전부 `git -C "$IMPL_WORKDIR"`(헬퍼 `impl_git`) 경유.

| 지점 | 기존(자기레포) | 워크스페이스 딜리버리 |
|---|---|---|
| 기준 브랜치 | `checkout main` + `pull origin main` (ClickEye) | `checkout <고객 기본 브랜치>` + `pull origin <같음>` (고객 clone). ClickEye 는 무접촉 |
| 태스크 브랜치 | ClickEye 에 `checkout -b` | **STEP B 이전에** 고객 clone 에 생성 → 에이전트 커밋이 이 브랜치에 얹힌다 |
| 머지된 동명 브랜치 정리 | `branch -d` | 생략(고객 레포 브랜치를 삭제하지 않음) |
| 구현 커밋 확인 | 없음(빈 머지가 "성공") | 브랜치 확보 직후의 tip 을 기억해 `rev-list --count <tip_before>..HEAD` 로 **이번 런 델타**를 본다. 0 이면 실패 확정 |
| Linear 처분 | `linear_reporter.py`(PRIMARY fix_plan·git 요약 기준) | reporter 생략. push 성공 시 `linear_tracker update --status Done` + 딜리버리 코멘트 |
| 거버넌스 | HTTP 서비스 또는 로컬 shim, `base=main`, ClickEye 정책 | 로컬 shim 만, `--project-dir <clone> --base <고객 기본 브랜치> --policy templates/harness-core/governance-workspace.policy.json` |
| 최종 반영 | `merge --no-ff` → `push origin main` → `branch -d` | 머지 없음. `push origin <태스크 브랜치>` 만 |
| PR | `auto_pr_creator.py` | 호출하지 않음(`gh` 가 ClickEye GitHub 을 겨냥하므로 잘못된 대상) |

**고객 기본 브랜치 감지 3단** — `main` 추측 금지(틀린 base 는 잘못된 diff·push 로 이어진다).

1. `git symbolic-ref --short refs/remotes/origin/HEAD` → `origin/` 스트립.
   비어 있으면 `git remote set-head -a origin` 으로 **1회 복구를 시도**한 뒤 재판정한다
   (origin/HEAD 는 삭제·구버전 clone·부분 fetch 로 없을 수 있다)
2. `<clone>/.clickeye_default_branch` — `workspace_provision.sh` 가 clone 직후 기록하는 메모.
   unborn/detached HEAD 면 리터럴 `HEAD` 를 쓰지 않고 기록을 **생략**한다
3. 둘 다 없으면 **실패 처리** — 감지 못한 채로 진행하지 않는다

**clone 위생 — 지우지 않고 비켜두기.** 고객 clone 은 여러 티켓이 재사용하므로 이전 런의 잔재가
다음 런을 막는다. 세 가지를 브랜치 확보 전에 처리하며, 모두 **유실 0**을 지킨다.

| 잔재 | 처리 |
|---|---|
| 미커밋 변경(에이전트가 죽은 자리) | `git stash push --include-untracked -m "clickeye-auto-preserve <KEY> <ts>"` 로 보존 후 진행. 복구: `git -C <clone> stash list` → `git stash apply <ref>`. **stash 실패 시에만** 실패 처리 |
| detached HEAD(이전 런 크래시) | `CUST_BASE` 계보 밖이면 `rescue/<KEY>-detached-<ts>` 브랜치로 보존 후 진행 |
| ClickEye 주입물(`.claude/`·`CLAUDE.md`·`.clickeye_default_branch`) | clone 로컬 `.git/info/exclude` 에 등재(provision + 파이프라인 양쪽에서 멱등 top-up). 등재하지 않으면 ① 더러운 트리 판정이 항상 참이 되어 stash 가 하네스 프래그먼트를 걷어가고 ② 에이전트의 `git add -A` 가 이들을 고객 브랜치에 커밋한다 |

**오염 가드**: R4 통과 후 이번 런 델타에 `.ralph/`·`.claude/`·`fix_plan.md`·`LoadMap_v3.md`·
`TODO.md` 가 있으면 실패 처리한다(fail-closed). ralph PROMPT 가 에이전트에게 fix_plan 갱신·커밋을
지시하므로 WS cwd 에서 ClickEye 운영 파일이 고객 브랜치로 새어나갈 수 있다.

**detached HEAD 에서의 구현은 실패다**: 커밋이 태스크 브랜치 ref 에 얹히지 않아 push 는 성공해도
산출물이 나가지 않는다(= 허상 재발). `rescue/<KEY>-<ts>` 로 보존하고 실패 처리한다.

**중립 정책** `templates/harness-core/governance-workspace.policy.json` (JSON 이라 주석 불가 —
용도는 여기에 기재): 남의 레포에는 ClickEye 계약면·모듈 경로 정책이 성립하지 않으므로
`contract_surface_prefixes`/`high_prefixes`/`high_path_patterns` 를 비우고
`FLOWOPS_GOVERNANCE_CONTRACT` 를 끈다. 결과적으로 실효 검증은 **ticket-ref** 뿐이며(브랜치의
이슈 키 형태), 고객 레포의 `auth/**` 변경이 HIGH 로 오분류되어 PR 강등되는 일이 없다.
plan-trace 는 고객 clone 에 `.ralph` 가 없어 자동 skip(비블로킹)이다. 프로젝트별 실질 정책은
`DeliveryProfile.policy` 로 승격하는 P8/CE-329 의 범위다.

**실패 모드** — 전부 `handle_task_failure`(재시도 복귀 또는 Backlog) + 다음 이슈로 진행.

| 실패 | 조건 | 부수 효과 |
|---|---|---|
| 고객 origin 없음 | `remote get-url origin` 비어 있음 | 착수 전 차단(push 대상 없음) |
| 고객 origin 이 ClickEye | origin 이 `PROJECT_DIR` 또는 PRIMARY 의 origin 과 동일 | 착수 전 차단 — 그대로 두면 브랜치가 ClickEye 로 올라가고 고객에겐 아무 것도 안 간다 |
| 기본 브랜치 감지 실패 | 위 3단 모두 실패(복구 시도 포함) | 착수 전 차단 |
| 중립 정책 파일 없음 | 거버넌스 활성 + 정책 판독 불가 | 착수 전 차단(게이트 시점까지 끌면 원인이 "거버넌스 차단"으로 오표기) |
| 미커밋 변경 보존 실패 | `stash push` 실패 | 브랜치 생성 전 차단(수동 정리 필요) |
| 기준 브랜치 checkout/pull 실패 | 충돌·네트워크·권한 | 브랜치 생성 전 차단 |
| 태스크 브랜치 생성 실패 | `checkout -b`·`checkout` 모두 실패 | — |
| HEAD 해석 실패 | 빈 레포 등 | tip 기준선을 못 잡으면 델타 판정이 불가 |
| detached HEAD 구현 | STEP B 후 `symbolic-ref HEAD` 실패 | `rescue/<KEY>-<ts>` 보존, push 미수행 |
| 이번 런 구현 커밋 없음 | `rev-list <tip_before>..HEAD` 0 | push 미수행. 잔여 커밋이 있는 재사용 브랜치도 소진되지 않는다 |
| 하네스 산출물 오염 | 델타에 `.ralph/`·`.claude/`·`fix_plan.md` 등 | push 미수행(fail-closed) |
| push 거부 | 보호 브랜치·권한·비패스트포워드 | **로컬 브랜치·커밋 보존**. `branch -d`·`push --delete` 를 실행하지 않는다(유실 0) |

git stderr 는 삼키지 않고 `logs/ws_delivery_<KEY>_<ts>.log` 에 남긴다(실패 로그가 그 경로를 가리킨다).

**자격 증명 전제**: 고객 origin 에 대한 push 권한은 러너 환경이 이미 갖고 있어야 한다
(clone 에 심긴 credential helper·SSH 키·토큰 URL). 파이프라인은 자격 증명을 주입하지 않으며,
없으면 위 표의 "push 거부"로 떨어진다.

**Done 시점**: WS 경로에서는 `linear_reporter.py` 를 **호출하지 않는다**. reporter 는 PRIMARY 의
`fix_plan.md` 와 ClickEye git 요약을 읽으므로 WS 모드에선 항상 `incomplete` → **Backlog** 로
되돌리고 엉뚱한 커밋 요약을 코멘트한다(설계 초안의 "조기 Done" 전제는 실측으로 반증됐다).
대신 **push 성공 직후가 유일한 성공 확정 지점**이며, 그 자리에서 `linear_tracker update
--status Done` + 딜리버리 코멘트(원격·브랜치·base·변경 요약, "머지는 고객 측")를 올린다.
실패는 `ws_delivery_fail` → `handle_task_failure`(재시도 복귀/Backlog)가 확정한다.

**재사용 브랜치의 커밋 스택**: 재시도로 같은 브랜치를 다시 쓰면 push 는 지난 런 커밋까지
함께 올린다(유실 금지 원칙상 지우지 않는다). 판정만 이번 런 델타로 하며, 고객에게는 누적
브랜치가 보인다 — 티켓 1건이 여러 번 재시도된 경우 커밋 정리는 고객 머지 시점의 몫이다.

**러너 clone 신선도**: `runner_clone.sh` 는 clone 재사용 시 canonical origin 에서 기본 브랜치를
`--ff-only` 로 당긴다(best-effort — 실패는 경고만, 스폰은 계속). 구버전 clone 이 남아 그 러너만
리다이렉트 없는 판으로 도는 **혼합 함대**를 완화한다. 로컬 커밋·충돌이 있으면 당기지 않는다.

**v1 제외**: ① 고객 기본 브랜치 자동 머지 ② 고객 레포 PR 자동 생성 ③ Done 전이 완전 지연
④ 고객 레포별 실질 거버넌스 정책(중립 정책으로 대체) ⑤ 재사용 브랜치 커밋 정리.

**테스트**: `scripts/tests/test_workspace_delivery.sh` — bare 고객 레포 + 스텁 PRIMARY 픽스처로
실제 파이프라인을 `--once` 구동한다(14 시나리오/64 단언: 토글 off 무회귀 · 자기레포 무발동 ·
감지 3단 + origin/HEAD 복구 · 정상 push · 커밋 없음 · push 거부 보존 · 중립 정책 · 기본 브랜치
`develop` · 재시도 델타 판정 · 더러운 clone stash · Linear 처분(reporter 미호출 + tracker Done) ·
오염 차단 · detached 회수 · origin 오조달 차단).

### 5-6. 워크스페이스 전용 구현 프롬프트 (CE-356)

§5-5 는 **git 조작**을 고객 clone 으로 돌렸지만 **에이전트의 입력 계약**은 self-repo 를 전제한
채 남아 있었다. 그 결과 리허설 종단(CE-355, 2026-08-04)에서 딜리버리가 100% 실패했다:

```
파생형 하네스: 구현 cwd → 워크스페이스 3be49b62        ← 여기까지 정상
cat: workspaces/3be49b62/.ralph/PLAN.md: No such file
<promise>BLOCKED</promise> — 계획 파일도 없고 clickeye-web/api 도 없다
→ 커밋 0 → ws_delivery_fail → Backlog
```

`.ralph/PROMPT.md` 가 `.ralph/PLAN.md`·`fix_plan.md` 를 **상대경로**로 읽으라 지시하고 ClickEye
5개 레포 구조·`LoadMap_v3.md` 동기화를 전제하기 때문이다. cwd 를 옮기는 순간 그 입력이 사라진다.

**해법: 프롬프트를 갈라 계획을 인라인한다.** 계획 산출물을 워크스페이스로 복사하는 안은 기각했다
— `LoadMap_v3.md` 동기화 지시가 남아 고객 레포 오염을 별도로 또 막아야 한다.

- `templates/harness-core/PROMPT.workspace.md`(Tier 0) — "계획은 프롬프트 안에 있다, 파일을
  찾지 마라"가 입력 규약이다. self-repo 전제(레포 구조·테스트/린트 하드코딩·LoadMap)를 전량
  제거하고 `CLAUDE.md` → `.claude/CLAUDE.stack.md` → `.claude/harness-gates.txt` 순으로 그
  저장소를 스스로 파악하게 한다. git 소유권도 분리한다(브랜치는 파이프라인, 에이전트는 커밋만).
  이 파일은 워크스페이스로 **복사하지 않는다** — 파이프라인이 ClickEye 쪽 경로에서 직접 읽어
  항상 최신본이며 고객 저장소에 파일을 늘리지 않는다.
- `build_impl_prompt()`(순수 함수) — self/워크스페이스 분기. 스펙 출처 우선순위는
  정제 스펙 > `PLAN.md` > 없음이고, 스펙을 확보하지 못하면 "구현하지 말고 BLOCKED"를 명시해
  빈 스펙으로 남의 저장소를 건드리지 않는다. 전용 프롬프트 부재 시 self 로 안전 폴백.
- **self-repo 출력은 바이트 동일**(회귀 0) — `scripts/tests/test_impl_prompt.sh` 14케이스가
  이 단정을 고정한다.

**종단 실측(2026-08-04 15:45~15:48, 3분 31초)**: 정제 → 구현 커밋 1건 → 거버넌스 LOW →
고객 레포 `ralph/CE-355` push → Linear Done. 고객 커밋의 변경 파일은 `README.md` **1개**
(하네스 산출물 오염 0). 프롬프트가 `.ralph/`·`LoadMap_v3.md` 갱신을 더 이상 지시하지 않으므로
G6 오염 가드가 발동할 상황 자체가 사라졌다.

---

## 6. 실행면 — 완주 오케스트레이션

### 6-1. 실패 티켓이 조용히 사라진다

무인 운전에서 가장 위험한 결함이며 현재 실재한다.

```
auto_dev_pipeline.sh    실패 시 → Linear 상태 "Backlog"
                        (:197 브랜치실패 · :208 fix_plan없음 · :440 거버넌스차단 · :605-618 일괄)
webhook_server.py:119   _check_and_retrigger() → DayQueued/NightQueued/Queued 만 조회
```

Backlog 는 Queued 가 아니므로 실패 티켓은 재트리거 대상에서 제외되고, 루프는
`"IDLE: 잔여 이슈 없음"` 으로 **정상 종료**한다. 즉 **일부 티켓이 실패한 채로 완료가
보고된다.** "발급된 티켓 전부를 A-Z" 가 구조적으로 보장되지 않는다.

> **재트리거 체인은 이제 무한하지 않다(CE-349, 2026-08-04).** 위 조회가 "잔여 이슈 있음"을
> 돌려주더라도, 직전 실행이 진척을 만들지 못했으면 체인을 끊는다 — `_live_lock_holder()`
> (`webhook_server.py:93`)가 `.ralph/.pipeline_lock` 보유 PID 생존을 확정 신호로 보고 즉시
> 중단하고, 그 밖의 원인(시트 `disabled`·제외 접두사 불일치)은 `MAX_RETRIGGER_CHAIN=5`
> 상한이 받는다. 이 결함의 실측 증상은 **6초 주기 무한 스핀**이었다(25초에 5회, 스핀마다
> 쓰레기 로그 1개). 중단 후 복구는 폴링 cron 이 담당하므로 위 "실패 티켓 유실" 문제와는
> 층이 다르다 — 이 절의 요구(재시도 상태화)는 여전히 유효하다.

**요구:** 실패는 종료 사유가 아니라 재시도 상태다. 재시도 한도(`retry_limits`) 소진 시에만
정지하고, 그때는 **완료가 아니라 정지로 보고**한다.

### 6-2. 프로젝트 정합성 테스트 단계가 없다

파이프라인은 티켓별 QA 리뷰(STEP C)만 한다. 전 티켓 완료 후 A-Z 통합·정합성 검증 단계가
`auto_dev_pipeline.sh`·`pipeline_orchestrator.py` 에 존재하지 않는다.

**요구:** 전 티켓 완주 후 정합성 게이트를 통과해야 프로젝트가 완료다. 게이트 명령은 스택별로
다르므로 제어면 YAML 의 `gates` 에서 온다.

→ ✅ **구현 완료(2026-07-28, P7).** `delivery_verifier.py`(완주 판정 — 원장×Linear,
미지 티켓=잔존 fail-closed / 게이트 전량 실행 / exit 계약 0·3·4·5) +
`delivery_verify.sh`(opt-in `FLOWOPS_DELIVERY_VERIFY`) + `verified`(최종 상태·하향
불가)/`gate_failed`(명시 재검증만) 전이 + 최종 콜백(체인 ⑥). 게이트 부재는 통과가
아니라 **검증 불가(exit 5)**. 제어면 YAML gates 의 프로젝트별 자동 해석은 P5/P8
워크스페이스 배선과 함께.

→ 🔄 **워크스페이스 조달 v1 (2026-07-31, CE-340 — 파생형 하네스 1단계).**
`workspace_provision.sh`(프로젝트 키+레포 소스 → `workspaces/<key>/` clone, 멱등) 시점에
하네스를 물질화한다: Tier 0 불변 코어(`templates/harness-core/` — CLAUDE.core.md·최소
settings) 복사 + Tier 1 스택 프로파일(`stack_profiler.py` — stdlib 전용 결정론 스캔,
모노레포 1-depth) 도출. 산출 3종 = `harness-profile.json`(감지 실패는 null, 추측 금지) ·
`CLAUDE.stack.md` · `harness-gates.txt`(VERIFY_GATES_FILE 호환 — **F-4 게이트 자동
도출분 해소**, 제어면 YAML 연동은 잔존). 파이프라인 배선은 `FLOWOPS_WORKSPACE` +
`WORKSPACE_KEY` 이중 opt-in 시 STEP B 구현 cwd 만 워크스페이스로 전환(기본 off = 회귀 0).
Tier 3(메트릭 기반 진화)는 후속 단계.

→ 🔄 **실행면 automap + 락 분리 v1 (2026-08-01, CE-339 — 결손 ②③④ 부분 해소).**
CE-340 조달 위에 "남의 프로젝트" 실행면의 남은 배관을 얹는다:
- **머신 조회면** — `GET /api/v1/intake/machine/projects`(X-ClickEye-Service-Key 머신 인증,
  사용자 JWT 불요). 서비스 키 조직의 인테이크 유래 프로젝트 목록 + 서버가 재현한
  `ticket_prefix`(`[수주:<intake_id 앞 8자>] `, intake_issue.sh 규약)를 내려준다 — 러너가
  project_id 만으로 유도 못 하던 접두사 문제(project_runner.sh 주석) 해소.
- **자동 매핑 원장** — `scripts/workspace_map.py`(stdlib)가 머신 조회를 폴링해
  `.ralph/workspaces.json`(ticket_prefix → workspace_key/intake/project/repo_source/status)을
  멱등 갱신. repo_source 미확보는 `pending_source` 표기만(**추측 clone 금지**), 수동 기입값 보존.
- **pending_source 등재 CLI (2026-08-03, CE-343)** — `workspace_map.py --set-source
  <ticket_prefix|workspace_key> <repo_source>`가 원장 항목을 검증 후 `mapped`로 전환(멱등,
  미존재 키는 비0 종료로 거부·항목 창작 금지). `--list`는 원장 상태 요약을 출력. 둘 다
  오프라인(네트워크·서비스 키 불요) — JSON 수동 편집을 대체.
- **settings.json 보존 정책 v1 (2026-08-03, CE-344)** — `workspace_provision.sh` Tier 0
  코어 복사 시 대상 레포에 기존 `.claude/settings.json`이 없으면 현행대로 코어 버전을
  그대로 복사한다. **있으면**(실 고객 레포 투입 시 자체 훅·권한·env를 가진 경우) 원본을
  건드리지 않고 보존하며, 코어 버전은 `.claude/settings.core.json`으로 병치 + 경고 로그
  출력(수동 병합 필요 안내) — `CLAUDE.md` 처리(④, 있으면 덮어쓰지 않음)와 대칭되는 보수적
  정책이다. 키 단위 자동 병합(고객 훅 + 코어 훅 병합 규칙)은 v2 범위 밖.
- **automap 배선** — `auto_dev_pipeline.sh`가 이슈 제목 접두사로 원장을 조회
  (`workspace_map.py --resolve-title`, 단일 소스)해 `mapped` 항목만 `WORKSPACE_KEY` 를 자동
  설정. 토글 `FLOWOPS_WORKSPACE_AUTOMAP`(이중 opt-in). 미매핑/pending_source/원장 없음은 self-repo.
- **락 분리(동시 실행 1단계)** — 전역 `.ralph/.pipeline_lock` → 전용 워크스페이스 러너는
  키별 `.ralph/.pipeline_lock.<key>`. self-repo/automap 단일 러너는 기존 파일명 유지 = 무회귀.
  같은 워크스페이스만 직렬화, 다른 워크스페이스는 병행 허용(§5-1 전역 락 차단의 1단계 완화).
- **검증 배치 연동(F-4 잔여)** — `delivery_verify.sh`가 명시 env 부재 시 워크스페이스로
  `VERIFY_WORKDIR`·`VERIFY_GATES_FILE`(워크스페이스 `harness-gates.txt`) 기본값을 채운다
  (명시 설정은 항상 우선).
여전히 범위 밖(후속): **시트 풀 매핑·러너 수평 확장(P5 본체 병렬)·집행면(P8)** — 이번 락 분리는
동시 실행 1단계일 뿐, 진짜 병렬(다중 체크아웃/컨테이너 + main 머지 직렬화)은 미해소.

→ 🔄 **Tier 2 도메인 제약 도출 (2026-07-31, CE-341 — 파생형 하네스 2단계).**
도출 원천은 STEP A 정제 산출물(`.ralph/refined/<KEY>.md`)이다 — metaprompt SKILL 의
선택 섹션 `## 도메인 제약 (Domain Constraints)`(데이터 민감도·금지 사항·정합성 규칙·
용어집)을 `domain_profile_merge.py`(stdlib 전용 결정론)가 추출해 대상 워크디렉터리의
`.claude/CLAUDE.domain.md` 에 **티켓 키 마커 블록**(`<!-- domain:CE-XXX begin/end -->`)으로
멱등 누적한다(같은 키 재실행 시 블록 교체, 없으면 append). 섹션 부재 시 아무 것도 쓰지
않는다(no-op — 근거 없는 도메인 규칙 창작 금지, Tier 1 "감지 실패=null"과 동일 원칙).
파이프라인 배선은 `FLOWOPS_DOMAIN_PROFILE` 이중 opt-in 시 STEP A 사후에만 실행(기본
off = 회귀 0), 대상은 STEP B 구현 cwd 와 동일 해석(self-repo 모드에서도 동일 적용).

→ 🔄 **Tier 3a 메트릭 수집 (2026-07-31, CE-342 — 파생형 하네스 3단계 기반).**
하네스 변형의 성능 주장을 측정 가능하게 하는 기반이다. 티켓 1건 처리마다 단계 경계
5종 이벤트(`refine_done`·`impl_done`·`qa_done`·`gate_done`·`run_done`)를
`pipeline_metrics.py`(stdlib 전용)가 `logs/metrics/pipeline_runs.jsonl` 원장에 1줄씩
append 한다(스키마 `{version, ts, run_id, event, data}` — `version` 으로 후방 호환).
이 원장이 이후 **prompt-evolve 루프(3b, 별도 범위)의 채점 입력**이 된다 — 이번 단계는
**수집만** 하고 집계·판단·대시보드는 하지 않는다. 배선 원칙은 **관측 비차단**:
`FLOWOPS_METRICS` 이중 opt-in(기본 off = 회귀 0), 기록 실패는 exit 0 으로 삼켜
파이프라인을 절대 막지 않으며, 값 확보를 위해 파이프라인 로직을 바꾸지 않는다(확보
불가 필드는 생략).

### 6-3. 티켓 전량 발급이 무인이 아니다

`prd-to-linear` 스킬은 대화형이며 사용자 확인을 요구한다
(`"이대로 Linear에 등록할까요?"`). 인테이크에서 Linear 티켓을 생성하는 서버 경로는 없다.

**요구:** 인테이크 정제 완료 → 티켓 전량 자동 발급(사람 확인 없음). 발급 결과는 기록면에
남기고, 발급 자체가 실패하면 서비스 #2 로 거부 콜백한다.

→ ✅ **구현 완료(2026-07-28, P6).** `machine_accept`(opt-in `FLOWOPS_INTAKE_AUTO_ACCEPT`,
서버 강제) + 발급 배치 `scripts/intake_issue.sh`(claude -p 구독 분해) +
`scripts/linear_issuer.py`(fail-closed 검증·3상 발급 — 부분 실패 = 실행 0건) +
발급 원장(`tickets_status` 멱등 앵커) + 콜백 확장. depends_on → blockedBy 배선으로
순차 A-Z 는 watcher 기존 코드 무변경 성립.

### 6-4. 딜리버리 콘솔이 원장을 비추지 못한다

무인 체인(인테이크→발급→검증)은 서버·기록면에 다 남지만, 사용자 딜리버리 콘솔은
그것을 못 봤다. 인테이크 유래 프로젝트는 세션이 없어(생성도 막힘) 상세 화면이
"세션 없음" 빈 상태로 떨어지고, 티켓 원장·타임라인은 admin(control_tower:read)
경로에만 있어 member 가 볼 수 없었다. 관제면과 무인 체인이 끊겨 있었다.

→ ✅ **구현 완료(2026-07-31, CE-337).** 프로젝트 스코프 역조회 API 2개
(`GET /projects/{id}/intake`·`/intake/timeline`, `project:read` + owner 스코프 —
admin 권한 완화 없이 신규 경로로 해결)를 신설하고, `intake.project_id` 인덱스로
저렴하게 역조회한다(`IntakeService.get_by_project_id`). 콘솔은 인테이크 프로젝트에서
체인 단계 배지·티켓 원장·전이 타임라인을 렌더한다(단일 `IntakeTimeline` 컴포넌트를
projectId 스코프로 재사용 — admin 뷰와 공유). CE-336 갭도 함께 보완: 인테이크 유래
프로젝트의 **세션 생성을 서버 측에서 409 차단**(클라이언트 가드만으로는 우회 가능).
비인테이크(수동) 프로젝트의 세션 축은 그대로 유지된다.

---

## 7. 결정 (ADR)

| # | 결정 | 근거 |
|---|---|---|
| **D-1** | 정책을 `Policy` 값객체로 커널에 주입. 기본값 = 오늘의 상수 | 회귀 0. **P0 완료** |
| **D-2** | `is_enabled()` 를 check 함수에서 제거, 정책으로 이동 | 다프로젝트화의 실제 관문. **P0 완료** |
| **D-3** | ~~제어면 SSOT = DB~~ → **정본은 서비스 #2 생성 YAML.** DB 는 런타임 미러 | 배포 주체가 사람이 아니라 서비스다(§3-1) |
| **D-4** | 명시 정책의 파싱 실패는 fail-closed | 적용 범위는 §3-2·§3-4 |
| **D-5** | 집행면 게이트 엔진을 ClickEye 제품 산출물로 배포 | 선행 구현 흡수 시 §8 전제조건 |
| **D-6** | 게이트 룰은 플러그인. 스택별 `gates`·`continuous_gates` 는 YAML 에서 | 대형 프로젝트의 스택은 우리와 다르다 |
| **D-7** | ~~샤드 병렬~~ → **프로젝트 N 병행 + 시트 풀.** 샤드 병렬은 선택 | 요구는 병렬성이 아니라 동시 다발 + 완주(§5·§6) |
| **D-8** | 기록면 DB 1급화 + **`seat_id` 축 추가** | 계정별 토큰 모니터링의 전제(§5-2) |
| **D-9** | 감사로그에 허용 판정도 기록 | 게이트 off 여부 사후 판별 |
| **D-10** 🆕 | **구독형 전용 강제 모드.** 게이트웨이가 `org_api_key` 해석 호출을 실행 전 거부 | 분류기를 강제기로(§4-2) |
| **D-11** 🆕 | **트리아지 예산 축을 cost → seat token/rate 로 전환.** `assess_rate` 윈도우 카운터를 필수로 승격 | 구독형에서 cost 는 항상 NULL(§4-5) |
| **D-12** 🆕 | **사람 승인 게이트 제거.** `cycle_approval` 대신 자동 승인 + `auto_stop_conditions` 위반 시에만 정지 | 무인 체인(§1·§3-3) |
| **D-13** 🆕 | **실패는 종료 사유가 아니라 재시도 상태.** 한도 소진 시 완료가 아니라 **정지**로 보고 | 조용한 유실 차단(§6-1) |
| **D-14** 🆕 | YAML 신뢰 근거는 소유권이 아니라 **서비스 #2 서명 + 스키마 버전** | 기계 저작물(§3-2) |

---

## 8. Phase

| Phase | 내용 | 상태 |
|---|---|---|
| **P0** | 거버넌스 정책 외부화(`Policy` 주입) | ✅ 커널 완료(219 passed). `DeliveryProfile` 은 §3-1 에 맞춰 역할 재정의 필요 |
| **P1** | **완주 오케스트레이터** — 실패 무유실·재개·재시도 한도·정지 보고 (§6-1) | ✅ 완료 (2026-07-28) — `scripts/retry_ledger.py` + `auto_dev_pipeline.sh` 실패 4경로 원장 경유. 토글 `FLOWOPS_COMPLETION`(opt-in), webhook 무변경 |
| **P2** | **YAML 제어면 계약** — 스키마·버전·서명·fail-closed·거부 콜백 (§3) | ✅ 완료 (2026-07-28) — `governance/control.py`(ControlPlane v1) + `PUT /governance/control-plane`(서비스 키 인증, 422=기계 소비형 거부). 서명 v1=인증 채널+sha256 해시(비대칭 서명은 후속) |
| **P3** | **구독형 전용 강제** — 게이트웨이 강제 모드 + 종량 잔존 경로 감사·전환 (§4) | ✅ 강제 모드 완료 (2026-07-28). 잔존 경로 처분 완료 (2026-07-30, F-5) — gpt_pr_review·fix_plan_generator 제거, codex/gemini 는 구독형 CLI 로 확정. clickeye-api 제품면 감사만 잔존 |
| **P4** | **시트 풀 + 계정별 토큰 모니터링** — 레지스트리·배정·`seat_id` 원장·시트별 레이트 (§5) | ✅ 완료 (2026-07-29) — 등록형 시트(사용자당 1개=ToS 방어)·머신 수령·`with_seat.sh` 주입 래퍼(스위칭 0회, 공식 경로 setup-token→CLAUDE_CODE_OAUTH_TOKEN)·PoC 실증(동시 격리·fail-closed). **재실증 대기**: 실토큰 다계정·레이트 N배(팀원 시트 첫 등록 시). 시트별 레이트 카운터는 P5 |
| **P5** | **다프로젝트 실행** (§5-3) | ✅ v1 완료 (2026-07-29) — watcher 프로젝트 필터 + project_runner(시트×범위×파이프라인 합성, 순차-다프로젝트). **병렬 확정 설계**: 단일 체크아웃 병렬은 git 구조 충돌(main 점유·머지 경합, 실측)로 배제 — 러너 수평 확장(프로젝트별 클론/컨테이너, 하이브리드 러너 방향) + main 머지 직렬화 요구. **선행 과제**: 시트별 레이트 카운터는 로컬 claude 사용량의 원장 인제스트 배관 이후(관측 불가 데이터 위에 카운터를 세우지 않는다). **automap·락 분리 1단계 (2026-08-01, CE-339)**: 머신 조회면 + `workspace_map.py` 매핑 원장 + 이슈 접두사 automap + 워크스페이스별 락으로 다른 워크스페이스 병행 허용. 러너 수평 확장(진짜 병렬)·시트별 레이트 카운터·시트 풀 매핑은 여전히 후속 |
| **P6** | **티켓 전량 자동 발급** — 인테이크 → Linear, 사람 확인 제거 (§6-3) | ✅ 완료 (2026-07-28) — 기계수락(opt-in)·분해 배치·3상 발급기·원장/콜백 |
| **P7** | **정합성 테스트 게이트** — 전 티켓 완주 후 통합 검증 (§6-2) | ✅ 완료 (2026-07-28) — 완주판정·게이트 실행·verified/gate_failed·최종 콜백 |
| **P8** | 집행면 게이트 엔진 + 룰 플러그인 | 🔄 **v1 착수 (2026-08-03, CE-329)** — 층 A(gitguard F1~F7 · secrets S1~S4) 무수정 이식 + 워크스페이스 `.claude/settings.json` PreToolUse 배선. 토글 `FLOWOPS_ENFORCEMENT`(이중 opt-in, 미설정=off → 조달 산출물 현행 동일). 방식 근거는 §8-1, v1 범위/제외는 §8-1-1 |
| **P9** | 기록면 1급화 + 대시보드 | ✅ 완료 (2026-07-29) — `delivery_events`(전이 이력 append-only, 실패 전이 포함 D-9) + 타임라인/집계 API + 인테이크 콘솔 체인 뷰. seat 축은 P4 에서 추가 |

**순서의 근거:** P1(완주)이 없으면 나머지가 전부 무의미하다 — 티켓이 조용히 유실되는 위에
동시성을 얹으면 유실이 병렬로 늘어난다. P3(구독형)를 P4(시트)보다 앞에 두는 이유는, 강제
모드가 없으면 시트 풀을 만들어도 종량 경로로 새기 때문이다.

### 8-1. P8 방식 확정 — 층 분리 이식 (2026-07-29 실측 기반)

**⚠️ 이전 판의 "선행 구현이 리뷰 미결(우회 7계열·비밀정보 미탐 43%)" 서술은 낡았다.
2026-07-29 실측으로 정정한다** — 그 결함은 이미 해소됐다:

```
infraeye-harness (실측 2026-07-29)
  LIFETIMES: S0 REVIEW_APPROVED(rev-A·B) · S1 REVIEW_APPROVED(rev-C·D, §15 정족수+공격자 충족)
  테스트    : 241 pass / 0 fail / 1 skip
  우회 7계열: F1~F7 로 분류 + 계열별 커버리지 테스트로 승격
             (픽스처만으로는 "동어반복"이라는 리뷰 지적까지 반영된 2판)
  미탐 43% : S2 계열로 편입 처리
  잔여 미충족: install.sh 부재(NOT_MET) — 엔진이 아니라 **설치 배관** 문제
```

**따라서 "결함 승계" 논거는 성립하지 않는다.** 실제 분기점은 다른 데 있다 —
**실행 모델의 축이 다르다.**

| 측정 | 값 | 함의 |
|---|---|---|
| 엔진 규모 | 5,756줄 (gitguard 1,544 · protect 1,063 · gate 793 · secrets 593) | 우회 방어가 알짜 자산 |
| 프로젝트 종속 | `worktree` **108회** · `shard` **104회** · `CONTROL.yaml` 34 · `assignment.json` 19 | infraeye3 의 "4샤드 worktree + cwd 역할판정" 전용 |
| 기동 지연 | node 번들 21~22ms / python 15~16ms / 현행 bash 훅 28~30ms | **런타임은 선택 근거가 못 된다**(현행 bash 가 가장 느림) |

**확정 방식 — 층을 나눠 각각 다르게 조달한다:**

| 층 | 내용 | 조달 |
|---|---|---|
| **A 규칙 판정** | 우회 방어 F1~F7(git 내장 셸 이스케이프·경로 정규화·plumbing 등가물·셸 재호출·변수 전개·바이너리 직접 실행) · 비밀정보 S1~S4 | **이식** — 프로젝트 중립이고, 처음 만들면 반드시 빠뜨리는 종류다(gitguard+secrets 2,137줄) |
| **B 실행 모델** | 누가 무엇을 만질 권한이 있는가 | **자체** — ClickEye 축은 프로젝트→시트→러너(P4·P5 에서 이미 구축). worktree/shard 212회는 대부분 이 층(identity·ownership·config)이라 가져올 대상이 아니다 |

포크 대신 층 분리를 택하는 이유: 저장소 소유가 infraeye3 이므로 통째 개조하면 두 프로젝트가
같은 코드를 다른 방향으로 끌어당긴다. 규칙 테이블·패턴은 언어를 넘겨도 그대로 옮겨진다.

**P8 을 보류한 근거(사용자 결정 2026-07-29):** 집행면은 **T3 Enterprise 티어에서만** 필요하고,
현재 무인 체인은 머지 게이트(P0·P2) + 완주 오케스트레이터(P1) + 정합성 게이트(P7)로 닫혀
있으며 실행은 순차(P5 v1)다 — **집행면 부재로 지금 막히는 것이 없다.**

보류 판단이 뒤집힌 계기는 티어가 아니라 **실행 형태**다. CE-346(러너 디스패처)·CE-347(딜리버리
리다이렉트)로 `claude -p --dangerously-skip-permissions` 가 **고객 clone 안에서 병렬로** 돌기
시작했다. 순차 자기레포 실행에서는 사고 반경이 PRIMARY 한 곳이었지만, 지금은 에이전트의
`git add -A` 한 번이 고객 브랜치를 오염시킨다. 그래서 v1 을 착수했다.

### 8-1-1. P8 v1 — 층 A 이식 + PreToolUse 배선 (2026-08-03, CE-329)

> **⚠️ v1 이 제공하는 보증 수준 — 먼저 읽을 것.**
> 이 게이트는 **우발적 위반 방어**다: 에이전트가 잘못 판단해서 저지르는 `git add -A`,
> `--no-verify`, `force-push`, plumbing 등가물, 작업면 밖 쓰기, 평문 비밀 기록을 막는다.
> 여기에 **흔한 우회 시그니처**(파이프로 셸 먹이기·인터프리터 인라인 git·대시 디스패치·
> 게이트 자기 삭제) 몇 가지를 얹었다.
> **적대적 우회 집행이 아니다.** 우회하려고 마음먹은 실행 주체는 막지 못한다 — 변수 조립,
> 인코딩, `npm run`/`make`/스크립트 경유 간접 실행이 전부 열려 있다.
> 이유는 구조적이다: 층 A(`gitguard.ts`)는 **"허용된 git 명령의 의미"** 만 판정하고,
> **"무엇을 실행·기록할 수 있는가"** 는 층 B 의 G-11 Bash 화이트리스트에 명시 위임돼 있다
> (`gitguard.ts:1476-1523` 주석). 화이트리스트 없이 블랙리스트만으로는 이 성질이 바뀌지 않는다.
> **v2 조건: 층 B 이식**(G-11 화이트리스트 · 정체성 · 소유권 · `protect.ts` 보호 경로).

**들어온 것 (층 A, 무수정 이식):** `templates/harness-core/enforce/src/` 에 `gitguard.ts`(1,544줄,
F1~F7: force-push · `git -c alias..=!…` 셸주입 · `--no-verify` · plumbing 등가물(`read-tree`/
`update-index`) · `git -C` 경계 이탈 · 변수 전개 · 바이너리 직접 실행)와 `secrets.ts`(593줄,
S1~S4 비밀 패턴 + 마크다운 표 셀 유출)를 원본 그대로 두고, 승계 테스트 80케이스도 같이 옮겼다.
두 모듈은 파일시스템·환경변수 접근이 없는 순수 함수라 의존성 드래그가 0이다.

**신규는 어댑터 하나뿐이다:** `enforce/src/enforce.ts` 가 stdin payload 를 읽어 판정기에
컨텍스트를 주입하고 종료코드로 옮긴다. 배포물은 esbuild 자족 CJS 번들
`templates/harness-core/hooks/gitguard-gate.cjs` 1파일(node 내장 모듈만 require — 워크스페이스에
node_modules 가 없어도 동작).

**exit 2 만 차단이다 (실측).** PreToolUse 훅은 skip-permissions 에서도 실행되지만 `exit 1` 은
자문형(non-blocking)이라 툴이 그대로 실행된다. 기존 `harness-plan-gate.sh` 가 `exit 1` 이라
**실질적으로 비차단**인 것도 같은 실측에서 확인됐다(플랜 게이트는 리마인더로 남는다).
그래서 집행면은 통과 `exit 0` 하나, 나머지 전부 `exit 2` 로 닫았고 — 번들 최상단
fail-closed 배너가 모듈 로딩 예외까지 `exit 2` 로 끌어내린다.

**`ask` 도 거부다.** 무인 실행에는 사용자 확인 채널이 없으므로 `ask` 를 허용으로 흘리면
판정 불능이 곧 우회가 된다. 이 강경 매핑이 딜리버리 흐름을 끊지 않는 이유는 두 가지다:
어댑터가 `integrateRoots: [cwd]`(clone 루트 = 통합 작업면)를 주입해 에이전트의 정상 조작
(`git add <파일>` · `git commit`)이 이미 `allow` 이고, push·브랜치 조작은 파이프라인
`impl_git` 소관이라 훅을 거치지 않는다.

**배선 (`scripts/workspace_provision.sh`):** 토글 `FLOWOPS_ENFORCEMENT` 이중 opt-in
(`is_enabled` + 비어있지 않음). on 일 때만 번들을 `.claude/hooks/` 로 복사하고
settings.json 에 PreToolUse 엔트리 1개를 **가산 병합**한다
(matcher `Bash|Write|Edit|MultiEdit|NotebookEdit`, timeout 15). 신규 조달과 CE-344 보존
경로(고객 settings 존재)를 같은 멱등 병합으로 덮으며, 다른 키는 건드리지 않고 이미
등록돼 있으면 무변경이다. 고객 JSON 이 손상돼 병합이 실패하면 경고만 남기고 조달은
계속한다(비차단). **off 면 settings 산출물이 현행과 바이트 동일**하다.

**감사는 best-effort 다.** 차단 판정만 `<cwd>/.harness/enforce-audit.jsonl` 에 1줄 append 하고
실패는 무시한다 — 감사 실패가 판정을 바꾸면 감사가 곧 우회 수단이 된다. 층 A 는 탐지된
비밀 값을 사유에 싣지 않으므로 로그에도 남지 않는다.

**v1 집행 범위 — 무엇을 막고 무엇을 못 막는가 (2인 리뷰 반영):**

| 대상 | 막는다 | 못 막는다 |
|---|---|---|
| **Bash git 조작** (층 A 이식) | `git add -A`/`git add .` 및 정규화 등가물 · `--no-verify` · `push --force` · `git -c alias..=!…` 셸주입 · plumbing 등가물(`read-tree`/`update-index`) · `cd`·`git -C` 로 clone 이탈 · 명령 이름이 변수(ask→거부) | 새 우회 계열(층 A 가 모르는 git 표면). 판정 불능은 거부로 떨어지므로 조용히 열리지는 않는다 |
| **쓰기 툴 경계** (어댑터가 집행, E-01) | `..`·절대경로·심볼릭 링크로 clone 밖을 겨냥한 Write/Edit/MultiEdit/NotebookEdit · 경로 부재 · cwd 자체 겨냥 | clone **안**에서의 파일 선택은 보지 않는다 — 소유권·보호 경로 판정은 층 B 소관이고 미이식이다 |
| **쓰기 툴 내용** (층 A S1~S4) | AWS 키·고정 토큰 패턴 · 키-값 자격증명 · 마크다운 표 셀 유출 · `.harness/secrets-deny.txt` 등재 값 | 인코딩(base64)·변수 조립·외부 다운로드 |
| **Bash 경유 비밀 기록** (원본 범위 밖, v1 보강) | 흔한 평문 경로 — `echo`·`printf`·heredoc·`tee` 로 쓰는 자격증명 | **완전 차단이 아니다.** 인코딩·변수 조립·`curl`로 받아 쓰기는 통과한다. 방어 깊이용 한 겹이지 경계가 아니다 |
| **게이트 자기보호** (어댑터, E-02) | `.claude/hooks/`·`.claude/settings.json`·`.harness/` 를 겨냥한 삭제·이동·복사·권한변경·리다이렉트 덮어쓰기·`sed -i`·`git rm`/`checkout --`, 그리고 쓰기 툴로 같은 경로에 쓰기 | **문자열·토큰 기반이라 변수 조립으로 우회된다**(`P=.claude/hooks; rm -f $P/x`). 읽기는 막지 않는다. 근본 해법은 층 B `protect.ts` |
| **불투명 실행 표면** (어댑터, E-03) | 파이프로 셸 먹이기(`\| bash`, `curl \| bash`) · `bash <파일>`/`sh -s`/`source`/`.` · 인터프리터 인라인 코드 안의 git(`python3 -c`/`node -e`/`perl -e`/`ruby -e`) · `find -exec git`/`xargs … git` · `git-<sub>` 대시 디스패치 · `git apply`/`git am` | **`npm run`·`make`·`pytest`·`uv run`·`./x.sh` 는 허용한다** — 막으면 무인 체인이 마비된다. 따라서 **간접 실행을 통한 git 조작은 v1 이 막지 못한다**(스크립트 파일 안의 git, package.json script 안의 git). 이것이 층 B G-11 화이트리스트가 필요한 정확한 이유다 |
| **툴 표면 자체** | matcher 에 열거된 `Bash`·`Write`·`Edit`·`MultiEdit`·`NotebookEdit` | `Task`·`WebFetch` 등 비열거 툴. 서브에이전트가 도는 동안의 툴 호출에도 프로젝트 `settings.json` 훅이 적용되는지가 관건인데, **부분 관측만 있다**(아래) |

두 가지를 정직하게 적어 둔다. ① **쓰기 경계 집행은 원본에 없던 것이다** — 원본은 이 판정
(`targetsFrom()` 의 `rel === null`)을 층 B(ownership)에서 집행하는데 층 B 를 이식하지
않았으므로 집행이 비어 있었고, 실측으로 `Write ../../etc/evil.txt` 가 통과했다. 판정식은
원본을 그대로 옮기고 집행만 어댑터가 한다. ② **Bash 비밀 스캔도 원본 범위 밖이다** —
원본 G-03 은 쓰기 툴만 본다. 그 판단은 원본 환경에서 옳지만, 여기서는 결과가 고객 레포로
push 되므로 한 겹 더 얹었다.

**관측된 오탐 1건(수정하지 않음):** `echo "DATABASE_URL=postgresql://user:${DB_PASSWORD}@localhost/db" >> .env.example`
처럼 **URL 안의 자리표시자 비밀번호**는 `URL 내 basic-auth 자격증명` 으로 거부된다
(층 A 의 자리표시자 완화가 키-값 경로에만 적용되고 URL 경로에는 적용되지 않는다).
일상 명령 42건 표본에서 유일한 오탐이고(약 2.4%), `secrets.ts` 무수정 원칙 때문에
패턴을 끄지 않았다. 거부는 사유와 함께 stderr 로 나가므로 에이전트가 표현을 바꿔
진행할 수 있다. **관측된 미탐 1건:** `printf "password: <값>\n" > f` 형태는 통과한다
(위 표의 "완전 차단이 아니다" 가 가리키는 바로 그 한계다).

**v1 이 하지 않는 것:**

| 제외 | 이유 |
|---|---|
| 프로젝트별 F/S 정책 (룰 플러그인) | 지금은 전 워크스페이스 동일 규칙. 제어면 YAML 로 규칙을 주입하는 층은 F-4 와 함께 설계 |
| 티어 해석 (T1~T3 별 강도) | 티어 축을 훅에 넣으면 층 B 를 끌고 오게 된다 |
| 감사 1급화 | `.harness/enforce-audit.jsonl` 은 워크스페이스 로컬 파일이다. `delivery_events`(P9) 편입은 별건 |
| 층 B 정체성 집행 (누가 무엇을 만질 권한이 있는가) | `CONTROL.yaml`·`assignment.json`·shard worktree 전제가 ClickEye 축(프로젝트→시트→러너)과 맞지 않는다 — §8-1 의 층 분리 판단 그대로. 단 **작업면 경계**만은 어댑터로 끌어왔다(위 범위표) |
| 보호 경로의 **정본 집행** (`protect.ts` 1,063줄) | v1 은 어댑터의 문자열 기반 자기보호(E-02)로 값싼 구멍만 닫았다. 변수 조립 우회가 남으므로 정본은 층 B 이식 시 |
| Bash 화이트리스트 (G-11) | **v2 의 핵심.** 블랙리스트로는 간접 실행을 닫을 수 없다 — 층 A 주석이 이 위임을 명시한다 |

**서브에이전트 표면 — 부분 관측(완전 검증 아님).** CE-329 구현 세션에서 **서브에이전트로 실행 중인
툴 호출에 프로젝트 `settings.json` 의 `PostToolUse(Edit|Write)` 훅이 실제로 발화**하는 것을
관측했다(`docs-sync-reminder.sh` 가 서브에이전트의 편집을 잡아 영향 문서를 `needs-revision` 으로
표시했다). 훅 배선 기제가 같으므로 `PreToolUse` 도 동일하게 적용될 가능성이 높지만,
**`Task` 툴 자체를 대상으로 한 직접 검증은 하지 않았다.** 만약 서브에이전트 세션이 훅을 타지
않는 구성이 존재한다면 `Task` 하나로 전 규칙을 우회할 수 있다. matcher 에 `Task` 를 추가하는
것은 정상 기능(서브에이전트 위임) 차단 위험이 커서 v1 에서 하지 않았다 — v2 에서 직접 검증 후 판단한다.

**배선 층 fail-closed (F8).** 훅 명령은
`node "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/gitguard-gate.cjs || exit 2` 다. 두 겹으로
조용히 열리는 경로를 닫는다: ① `CLAUDE_PROJECT_DIR` 미설정 시 `node /.claude/…` 를 실행해
rc=1(자문형)이 되던 것을 cwd 폴백으로 막고, ② 번들이 지워지거나 손상돼 node 가 rc=1 로
죽어도 셸이 2 로 바꾼다. `exit 1` 이 자문형이라는 실측 사실에 대한, 게이트 바깥의 방어선이다.
통과(0)는 `||` 를 타지 않으므로 정상 흐름은 그대로다.

**토글 강등 방지 (F3).** 조달 스크립트는 `pipeline_config.sh` 를 source 하기 전에
`FLOWOPS_ENV_KEEP_EXISTING=true` 를 세운다. 이것이 없으면 `.env` 의 `FLOWOPS_ENFORCEMENT=false`
가 호출자 env 의 `true` 를 덮어 **조용히 미배선**된다(CE-345/346 에서 겪은 오귀속 계열).
호출자가 말이 없으면 `.env` 설정이 그대로 적용된다.

### 8-2. 후속 과제 (착수 대기)

| # | 과제 | 값 / 차단 |
|---|---|---|
| **F-1** | **사용량 인제스트 배관** — 로컬 `claude -p` 사용량을 서버 원장(`LlmUsageLedger`, seat_id 축)으로 | 🔄 **v1 완료 (2026-07-29, CE-328)** — 서버 인제스트(`POST /llm/ingest/usage`, 202 비블로킹·seat 사전검증·(session_id,model) 멱등) + ① 구현 스텝(`auto_dev_pipeline.sh` stream-json 사후 파싱, 토글 `FLOWOPS_USAGE_INGEST`/`FEATURE_LLM_USAGE_INGEST` opt-in, off면 회귀 0)까지. **후속(별도 티켓)**: ② 정제·③ 분해/인테이크 지점의 json 전환(엔벨로프 오염 다중 회귀 경로 재설계 필요). P5 유보분(시트별 레이트 카운터)의 선행 해소 |
| **F-2** | **실토큰 다계정 실증** — 레이트 한도가 계정별 독립인지 | P4 가정 미확정. 팀원 시트 첫 등록 시 |
| **F-3** | P8 집행면 (§8-1 방식) | 🔄 **v1 완료 (2026-08-03, CE-329)** — 층 A 이식 + PreToolUse 배선(§8-1-1). **잔여**: 프로젝트별 F/S 정책 · 티어 해석 · 감사 1급화 · 층 B 정체성 집행 |
| **F-4** | 제어면 YAML `gates` → 검증 배치 자동 해석 | 🔄 **워크스페이스 자동 해석 (2026-08-01, CE-339)** — `delivery_verify.sh`가 명시 env 부재 시 워크스페이스 `harness-gates.txt`(stack_profiler 도출)를 `VERIFY_GATES_FILE` 기본값으로, 워크스페이스 경로를 `VERIFY_WORKDIR` 기본값으로 채택(명시 항상 우선). **잔여**: 제어면 YAML `gates` 직접 소비(harness-gates.txt 는 스택 도출분이지 YAML 정본이 아니다) |
| **F-5** | 종량 잔존 스크립트 처분 — `gpt_pr_review.py`·`fix_plan_generator.py`(OPENAI_API_KEY) | ✅ **완료 (2026-07-30)** — 개발 파이프라인 종량 경로 전량 제거(`gpt_pr_review.py`·`fix_plan_generator.py`·`ai-review.yml`·`ai-critique` 스킬)·`--use-gpt-plan` 분기 삭제. `.env` 키는 clickeye-api 제품면이 참조하므로 유지(폐기는 사용자 판단) |

> **거버넌스 예산 상호작용(CE-328 §M2):** `governance_gate_service._usage_from_ledger` 는
> key_source/request_kind 구분 없이 토큰을 합산하므로, `FLOWOPS_GOVERNANCE_TRIAGE_BUDGET`
> opt-in + `token_limit>0` 환경에서는 F-1 로 유입되는 로컬 배치 토큰(`request_kind='local_batch_%'`)이
> 예산 판정에 포함돼 자율 파이프라인이 자기 사용량으로 block 될 수 있다. **v1 결정: 집계 로직은
> 변경하지 않는다**(기본 `token_limit=0` → skip 이라 기본 동작 불변). 로컬 유입분 제외 여부는
> P5 시트별 레이트 카운터 설계 시 결정한다.

---

## 9. 변경 이력

| 일자 | 변경 | 사유 |
|---|---|---|
| 2026-07-27 | 초판 — 5-Plane · Tier T1~T3 · `D-1`~`D-9` | 다프로젝트화 착수 |
| 2026-07-28 | **전면 재작성** — `D-3` 철회(YAML 정본) · `D-7` 재정의(동시 다발+완주) · `D-10`~`D-14` 신설 · Phase 재정렬 | 3-서비스 체인·구독형 전용·다계정 동시 실행이 핵심가치로 확정됨 |
| 2026-07-29 | **P8 방식 확정(층 분리 이식)·보류 결정 + 후속 과제 F-1~F-5 등재.** 이전 판의 "선행 구현 리뷰 미결" 서술을 실측으로 정정(241 pass·리뷰어 정족수 통과, 잔여는 install.sh 부재) | 낡은 스냅샷을 반복 인용하고 있었음 — 실측으로 교체 |
| 2026-07-29 | **F-1 v1 완료(CE-328)** — 로컬 `claude -p` 사용량 → 서버 원장 인제스트 배관(seat_id 축·session_id 멱등·202 비블로킹) + ① 구현 스텝 배선. §5-2 현행화(seat_id/session_id 컬럼·배관 완료)·§8-2 F-1 진행 반영·거버넌스 예산 상호작용(M2) 기록 | 계정별 토큰 모니터링의 로컬 절반 연결 |
| 2026-07-28 | **E2E 리허설 통과** — 모의 수주 1건 ①~⑥ live 관통(정제·분해=claude 구독, Linear 실물 CE-320~323, verified 확정). 실증 결함 2건 수정: 완주 판정 name→**type 기준**(팀 커스텀 Confirm=completed 대응) · 발급 기본 상태 →Queued. 미배선 확인: 제어면 gates→검증 배치 자동 해석(P5/P8) | 코드 검증만으로 못 잡는 팀별 워크플로 차이를 실증으로 확인 |
| 2026-08-03 | **러너 디스패처 v1(CE-346)** — 워크스페이스별 전용 러너 스폰·감시·회수(`runner_dispatcher.sh`) + 러너별 로컬 clone 프로비저닝(`runner_clone.sh`, worktree 기각 근거 기록). `linear_watcher.py` `--exclude-prefix`/`--check-only`/`WATCHER_EXCLUDE_PREFIXES`. 2인 리뷰 반영 4건: clone origin 을 PRIMARY→canonical 로 재지정(러너 push 가 PRIMARY 브랜치를 지우는 것 차단) · 스폰 env 권위(`FLOWOPS_ENV_KEEP_EXISTING`) · 시트 단위 이중 스폰 가드(clone-로컬 `.seat_lock` 무력 보완) · `--check-only` 비활성 오판(exit 2). §5-3 에 디스패처 절 신설 + **딜리버리 리다이렉트 미배선(CE-347)** 명시 | 병행 허용 조건(CE-339·CE-345) 위에 실제 병행을 만드는 층이 없었음 |
| 2026-08-03 | **딜리버리 리다이렉트 v1(CE-347)** — 워크스페이스 모드의 브랜치 생성·구현 커밋 확인·거버넌스·push 를 고객 clone(`IMPL_WORKDIR`)으로 리다이렉트(`FLOWOPS_WORKSPACE_DELIVERY`, 이중 opt-in). 태스크 브랜치만 고객 origin 에 push(머지·PR 없음) · 기본 브랜치 감지 3단(`main` 추측 금지) · 중립 정책 `templates/harness-core/governance-workspace.policy.json` · push 거부 시 로컬 브랜치 보존. §5-3 사실 A 를 "허상"→"배선"으로 정정 + §5-5 신설. **2인 리뷰 반영**: 이번 런 델타로 커밋 판정(재시도 잔여 브랜치가 빈손 런을 성공 처리하는 것 차단) · 더러운 clone stash 자기치유(영구 wedge 해소) · WS 경로 `linear_reporter` 생략 + push 성공 시 명시 Done(reporter 가 PRIMARY 기준으로 Backlog 되돌리던 것 — "조기 Done" 전제가 실측 반증됨) · detached HEAD 회수 브랜치 · 하네스 산출물 오염 fail-closed · origin 오조달 차단 · git stderr 보존 · clone 신선도 ff-only | 러너 병행(CE-346)이 만든 산출물이 고객 레포로 나가지 못하고 있었음 |
| 2026-08-03 | **P8 집행면 v1(CE-329)** — 층 A(`gitguard.ts` F1~F7 · `secrets.ts` S1~S4) 무수정 이식 + 승계 테스트 80케이스 + 신규 어댑터(`enforce.ts`) → 자족 CJS 번들 `hooks/gitguard-gate.cjs`. `workspace_provision.sh` 이중 opt-in 배선(`FLOWOPS_ENFORCEMENT`, 신규/CE-344 보존 경로 공통 멱등 병합, off=바이트 동일). **실측 근거**: PreToolUse 는 skip-permissions 에서도 실행되지만 `exit 2` 만 차단 — 기존 `harness-plan-gate.sh`(exit 1)는 자문형이었다. `ask`→거부(무인 실행에 확인 채널 없음), 정상 조작은 `integrateRoots:[cwd]` 주입으로 allow. §8-1-1 신설 + P8·F-3 상태 갱신. **2인 리뷰 반영**: 쓰기 툴 작업면 경계 집행(E-01 — 원본은 층 B 소관이라 미이식 구간이었고 `Write ../../etc/evil.txt` 실측 통과, 심볼릭 링크 경유까지 차단) · Bash 명령 문자열 비밀 스캔(원본 범위 밖, 평문 경로 방어 깊이) · exclude 짝 목록 불변식 복원 · fail-open 가시성(병합 실패 시 "게이트 없음" 명시) · 멱등 판정을 번들 파일명 기준으로 완화. **적대적 리뷰 반영**: 게이트 자기보호(E-02 — `rm -f <훅>` 등이 실측 통과했고, 번들이 사라지면 훅이 rc=1 자문형이 되어 게이트가 조용히 열린다) · 비문자열 command 거부 · 불투명 실행 표면 좁은 표적 차단(E-03: 파이프 셸·인라인 인터프리터 git·대시 디스패치·`git apply`/`am`, 단 `npm run`/`make`/`./x.sh` 는 허용 유지) · 배선 층 fail-closed(`${CLAUDE_PROJECT_DIR:-.}` + `\|\| exit 2`) · `.env` 토글 강등 방지. **보증 수준을 "우발적 위반 방어"로 정정**하고 적대적 우회 집행이 아님을 명시(층 B G-11 화이트리스트가 v2 조건) | CE-346·CE-347 로 skip-permissions 에이전트가 고객 clone 에서 병렬 실행되기 시작 — 사고 반경이 PRIMARY 에서 고객 레포로 넓어졌다 |
| 2026-08-04 | **다프로젝트 딜리버리 종단 최초 성공(CE-356·CE-357·CE-350).** 리허설 레포(`24seven-delivery-rehearsal`)로 활성 절차를 실제로 밟아 `Linear Queued → automap → 고객 clone 구현 → 커밋 → 거버넌스 → 고객 origin push → Done` 을 3분 31초에 관통. 고객 커밋 변경 파일은 `README.md` 1개(오염 0). **그 과정에서 드러난 3건**: ① 워크스페이스 모드 구현 프롬프트가 self-repo 전제라 100% BLOCKED(§5-6, CE-356 — 프롬프트 분기 + 계획 인라인) ② 메타프롬프트 정제가 **전 티켓에서 조용히 실패**(CE-357 — `SKILL.md` 프론트매터 `---` 가 `claude -p` 첫 인자로 가 CLI 가 옵션으로 파싱. 폴백이 흡수해 관측 불가였다) ③ 머신 서비스 키 발급이 superadmin 웹 로그인 전용이라 헤드리스 활성 불가(CE-350 — 발급 CLI). **활성 구성 결정**: 디스패처는 워크스페이스마다 배정 시트를 무조건 요구하므로(`runner_dispatcher.sh:186`, `FLOWOPS_SEAT_POOL` 무관) 구독 계정 1개 환경에서는 디스패처를 끄고 단일 러너 automap 으로 운영한다 — 시트 없이 제외 접두사만 걸면 아무도 처리하지 않는 죽은 조합이 된다(실측) | 부품을 다 만들어 두고 한 번도 종단으로 통과시키지 않았음 — 통과시키는 순간 3건이 드러났다 |
| 2026-08-04 | **무인 점화 종단 검증(CE-338 완료) + 결함 3건 수정(CE-349).** 체인이 실제로 관통함을 실측: Linear 이벤트 → ngrok(예약 도메인) → 수신 컨테이너 적재 → Redis 큐 → 호스트 워커 → 파이프라인 디스패치. crontab 을 정본(`scripts/clickeye_cron.txt`)과 완전 일치하게 재설치(경로가 죽은 옛 항목 제거). **검증 중 실측한 결함**: ① 재트리거 무한 루프 — 파일락 SKIP(진척 0) 시 6초 주기 무한 스핀 → 락 보유자 생존 판정 + 체인 상한 5회(§6-1 주석) ② `webhook-doctor.sh` 가 컨테이너 소유 PID 를 "호스트 잔재"로 오탐해 `--force` 종료 대상에 넣음(운영 중 수신부를 죽이는 경로) → cgroup 판정 ③ ngrok watchdog 이 `--url` 없이 되살려 랜덤 URL 배정 → Linear 등록 URL 불일치로 이벤트 조용히 유실 → `NGROK_DOMAIN` 고정. **활성 절차의 잔여 블로커 등재**: 머신 서비스 키 발급 경로 부재(CE-350 — 평문 복구 불가·발급이 superadmin JWT 전용이라 헤드리스 활성 불가), 재부팅 내구성 부재(CE-351 — db·redis `RestartPolicy=no` 실측), 큐 at-most-once(CE-352) | 부품은 다 있었지만 종단으로 한 번도 통과시키지 않았음 — 통과시키는 순간 3건이 드러났다 |
| 2026-07-30 | **F-5 완료** — 개발 파이프라인 종량 경로 제거(`gpt_pr_review.py`·`fix_plan_generator.py`·`.github/workflows/ai-review.yml`·`ai-critique` 스킬)·`--use-gpt-plan` 분기 삭제. CODE_REVIEW 문서를 구독형 경로(codex CLI + `code-reviewer` 서브에이전트)로 현행화. §4-3 잔존 경로·P3·F-5 상태 갱신 | 구독형 전용 원칙 정합 — 종량 API 키 호출자 4개(OpenAI 3+Gemini 1) 소멸 |

---

## 10. 강제되지 않는 것

기계적 규칙은 강제 가능하지만 의미적 품질은 불가능하다. 이 경계를 흐리면 "하네스가 품질을
보증한다"는 착각이 생긴다.

| 항목 | 사유 |
|---|---|
| 리뷰어의 실제 독립 판단 | 시트 상이 여부까지만 검사 가능(§5-4) |
| 기록 진술의 진위 | 존재·구조만 검사 |
| 구현의 정확성 | 테스트의 영역 |
| 서비스 #2 가 생성한 YAML 의 적절성 | 스키마 적합성까지만 검사. **프로젝트 성격에 맞는지는 검사 불가** |

**게이트 통과 = 올바름이 아니다.**
