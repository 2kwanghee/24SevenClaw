---
title: 다프로젝트 무인 딜리버리 아키텍처 (3-서비스 체인 · YAML 제어면 · 구독형 전용)
category: architecture
status: current
last_updated: 2026-07-31
related:
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
6. **락 세분화** — 전역 PID 락 → 프로젝트 단위 락.

### 5-4. 리뷰 독립성과 시트

§4-3 의 문제가 여기서 풀린다. 리뷰 2인 정족수를 **서로 다른 시트**에 배정하면 종량 API 없이도
독립 리뷰가 성립한다. 시트 풀은 동시성 자원이자 **역할 분리 자원**이다.

---

## 6. 실행면 — 완주 오케스트레이션

### 6-1. 실패 티켓이 조용히 사라진다

무인 운전에서 가장 위험한 결함이며 현재 실재한다.

```
auto_dev_pipeline.sh   실패 시 → Linear 상태 "Backlog"
                       (:197 브랜치실패 · :208 fix_plan없음 · :440 거버넌스차단 · :605-618 일괄)
webhook_server.py:59   _check_and_retrigger() → DayQueued/NightQueued 만 조회
```

Backlog 는 Queued 가 아니므로 실패 티켓은 재트리거 대상에서 제외되고, 루프는
`"IDLE: 잔여 이슈 없음"` 으로 **정상 종료**한다. 즉 **일부 티켓이 실패한 채로 완료가
보고된다.** "발급된 티켓 전부를 A-Z" 가 구조적으로 보장되지 않는다.

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
티켓→워크스페이스 자동 매핑, Tier 2(인테이크 설계→도메인 제약)·Tier 3(메트릭 기반
진화)는 후속 단계.

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
| **P5** | **다프로젝트 실행** (§5-3) | ✅ v1 완료 (2026-07-29) — watcher 프로젝트 필터 + project_runner(시트×범위×파이프라인 합성, 순차-다프로젝트). **병렬 확정 설계**: 단일 체크아웃 병렬은 git 구조 충돌(main 점유·머지 경합, 실측)로 배제 — 러너 수평 확장(프로젝트별 클론/컨테이너, 하이브리드 러너 방향) + main 머지 직렬화 요구. **선행 과제**: 시트별 레이트 카운터는 로컬 claude 사용량의 원장 인제스트 배관 이후(관측 불가 데이터 위에 카운터를 세우지 않는다) |
| **P6** | **티켓 전량 자동 발급** — 인테이크 → Linear, 사람 확인 제거 (§6-3) | ✅ 완료 (2026-07-28) — 기계수락(opt-in)·분해 배치·3상 발급기·원장/콜백 |
| **P7** | **정합성 테스트 게이트** — 전 티켓 완주 후 통합 검증 (§6-2) | ✅ 완료 (2026-07-28) — 완주판정·게이트 실행·verified/gate_failed·최종 콜백 |
| **P8** | 집행면 게이트 엔진 + 룰 플러그인 | ⏸ **후속 보류**(2026-07-29 사용자 결정). 방식은 §8-1 로 확정(층 분리 이식). 지금 막는 것 없음 — T3 티어에서만 필요하고 현재 실행은 순차(P5 v1) |
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

### 8-2. 후속 과제 (착수 대기)

| # | 과제 | 값 / 차단 |
|---|---|---|
| **F-1** | **사용량 인제스트 배관** — 로컬 `claude -p` 사용량을 서버 원장(`LlmUsageLedger`, seat_id 축)으로 | 🔄 **v1 완료 (2026-07-29, CE-328)** — 서버 인제스트(`POST /llm/ingest/usage`, 202 비블로킹·seat 사전검증·(session_id,model) 멱등) + ① 구현 스텝(`auto_dev_pipeline.sh` stream-json 사후 파싱, 토글 `FLOWOPS_USAGE_INGEST`/`FEATURE_LLM_USAGE_INGEST` opt-in, off면 회귀 0)까지. **후속(별도 티켓)**: ② 정제·③ 분해/인테이크 지점의 json 전환(엔벨로프 오염 다중 회귀 경로 재설계 필요). P5 유보분(시트별 레이트 카운터)의 선행 해소 |
| **F-2** | **실토큰 다계정 실증** — 레이트 한도가 계정별 독립인지 | P4 가정 미확정. 팀원 시트 첫 등록 시 |
| **F-3** | P8 집행면 (§8-1 방식) | T3 티어 착수 시 |
| **F-4** | 제어면 YAML `gates` → 검증 배치 자동 해석 | 현재 `VERIFY_GATES_FILE` 수동. 다프로젝트 워크스페이스 배선과 함께 |
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
