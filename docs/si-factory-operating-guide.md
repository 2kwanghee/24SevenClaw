---
title: ClickEye SI 팩토리 — 전략적 실행 가이드
category: guide
status: current
last_updated: 2026-07-22
related:
  - docs/si-factory-transition.md
  - docs/pipeline-guide.md
  - docs/agent-protocol.md
  - docs/hybrid-runner-headless-poc.md
  - CLAUDE.md
  - scripts/auto_dev_pipeline.sh
  - scripts/pre_merge_gate.py
---

# ClickEye SI 팩토리 — 전략적 실행 가이드

**대상**: ClickEye 딜리버리팀 운영자  
**작성일**: 2026-07-20  
**설계 기준**: `docs/si-factory-transition.md` (마스터 설계) 참조

---

## 0. 이 문서의 목적

본 문서는 **ClickEye SI 팩토리를 안전하게 운영하기 위한 실행 순서, 토글 롤아웃 전략, 통제 포인트, 선결 조건**을 정의합니다.

설계의 배경(왜 이렇게 하는가)은 `docs/si-factory-transition.md` §1~7에서 다룹니다. 본 가이드는 **"어떻게 굴리는가"** 에 집중합니다.

---

## 1. 지금 실행 가능한 것 (구축 현황)

### P0 완료·main 머지됨

다음 항목들은 **PR #46** (거버넌스 커널)과 연관된 변경으로 main에 머지되었습니다:

| 항목 | 상태 | 설명 |
|------|------|------|
| **거버넌스 커널 (SSOT)** | ✅ 완료 | 저장소 루트 `governance/` stdlib, CLI + FastAPI `/api/v1/governance/evaluate` |
| **LLM 게이트웨이+원장** | ✅ 구현 | Alembic head 044, 모든 AI 호출 계측 가능 |
| **Temporal 단일노드** | ✅ 기동 | docker-compose profiles:[temporal], 워커 스켈레톤 준비 |
| **Agent 핸드셰이크·register** | ✅ 완료 | CE-300/F 구현, 실행 핸들러는 P3 |
| **Runner 태스크 계약** | ✅ 정의 | `RunnerTaskPayload`, 위치 무관 실행 스키마 |
| **Deploy 메뉴** | ✅ 구현 | `deploy.sh` 인터랙티브 메뉴 |

### P1~P3 증분 준비 (토글 기본 off)

다음 기능들은 구현되었으나 **운영 환경에서는 기본 off 상태**입니다. 각 단계에서 명시적으로 활성하여 관측→검증→다음 이동:

| 항목 | 토글/조건 | 설명 |
|------|---------|------|
| 거버넌스 HTTP 경유 | `FLOWOPS_GOVERNANCE_SERVICE_URL` | 로컬 shim → 컨트롤 플레인 서비스 |
| Temporal 섀도우 레일 | `FEATURE_TEMPORAL=true` + `FLOWOPS_TEMPORAL=true` | 기존 거버넌스 결정 미러링, 부작용 0 |
| LLM 게이트웨이 계측 | `FEATURE_LLM_GATEWAY=true` | AI 호출을 원장에 기록 |
| 3단 트리아지 관측 | `FLOWOPS_GOVERNANCE_TRIAGE=on` | risk_score, budget 계산 (판정 미적용) |
| 트리아지 집행 | `FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE=on` | review→PR, block→차단 (선결: CE-297) |

### 원칙: 신규 경로는 토글/opt-in, 기본 off

기존 bash 파이프라인(auto_dev_pipeline.sh)은 변경 없이 유지됩니다. 토글을 끄면 **회귀 0**입니다.

---

## 2. 배포 (로컬 스택 기동)

### 스택 구성

```
┌─────────────────┐
│  PostgreSQL     │  (DB)
├─────────────────┤
│  Redis          │  (캐시/큐)
├─────────────────┤
│  clickeye-api   │  FastAPI 8000
│  ├─ /docs       │  Swagger UI
│  ├─ /api/v1/... │  API 엔드포인트
│  ├─ /api/v1/health
│  └─ 거버넌스, LLM 게이트웨이
├─────────────────┤
│  Temporal       │  (선택) 8080 UI, 7233 gRPC
├─────────────────┤
│  (clickeye-web) │  (선택) Next.js 3000
└─────────────────┘
```

### 기동 명령

```bash
cd /mnt/c/workspace/clickeye/clickeye-infra

# 메뉴 방식 (권장)
bash scripts/deploy.sh

# 직접 명령
bash scripts/deploy.sh up      # DB→Redis→API(+alembic)→Temporal 순차 기동
bash scripts/deploy.sh down    # 컨테이너 중지 (볼륨 보존)
bash scripts/deploy.sh status  # 스택 상태 확인
bash scripts/deploy.sh logs    # 각 서비스 로그 스트리밍
bash scripts/deploy.sh reset   # 컨테이너+볼륨 전체 삭제 (초기화)
```

### 접속 포인트

| 서비스 | URL | 용도 |
|--------|-----|------|
| **FastAPI Docs** | `http://localhost:8000/docs` | API 스펙·테스트 |
| **API Health** | `http://localhost:8000/api/v1/health` | 상태 검사 |
| **Temporal UI** | `http://localhost:8080` | 워크플로 히스토리·모니터링 |
| **Redis CLI** | `redis-cli -p 6379` | 큐/캐시 조회 |

### 첫 기동 시 체크리스트

- [ ] `docker`, `docker-compose` 설치 확인
- [ ] `.env` 파일 존재 확인 (미존재 시 template 복사)
- [ ] `deploy.sh up` 실행, 모두 healthy 상태 확인
- [ ] `/api/v1/health` 응답 확인
- [ ] Temporal UI 접속 확인

---

## 3. 실행 모델 (현행 권위 경로)

### 파이프라인 흐름

작업 단위 = **Linear 이슈** (형식: `CE-XX`)

```
Linear 이슈 (DayQueued/NightQueued)
  ↓
auto_dev_pipeline.sh 감지
  ↓
STEP A: 메타프롬프트 정제 (claude -p sonnet)
  ↓
STEP B: 구현 (claude -p)
  ↓
STEP C: Codex QA
  ↓
Linear 보고 (TASK.md)
  ↓
[거버넌스 게이트] pre_merge_gate.py (머지 직전 권위 판정)
  ↓
merge_decision → {direct|pr|block}
  ↓
Auto-merge (direct) 또는 PR (review) 또는 차단 (block)
```

### 인증 (중요)

**실행 권리 = claude.ai 구독 세션**

```bash
# 구독 세션에서만 실행
unset ANTHROPIC_API_KEY          # 조직 키 제거
claude -p "..."                  # 브라우저 로그인으로 인증

# 조직 키는 폴백용 (클라우드 러너만, P3)
export ANTHROPIC_API_KEY="sk-..."
claude -p "..."                  # 헤드리스 (컨테이너 전용)
```

### 수동 실행

webhook 없이 수동으로 파이프라인 실행:

```bash
cd /mnt/c/workspace/clickeye

# 1회 사이클 (linear_watcher가 Queued 이슈를 자동으로 선택)
bash scripts/auto_dev_pipeline.sh --once
```

### 파이프라인 토글 (기본값)

| 토글 | 기본값 | 설명 |
|------|--------|------|
| `FLOWOPS_GOVERNANCE` | `on` | 거버넌스 게이트 활성 (opt-out) |
| `FLOWOPS_TEMPORAL` | `off` | Temporal 섀도우 (opt-in) |
| `FLOWOPS_METAPROMPT` | `on` | Claude 메타프롬프트 (fallback: Gemini) |
| `FLOWOPS_AUTO_MERGE` | `off` | 직접 머지 (기본 PR) |

---

## 4. 토글 롤아웃 전략 (핵심 — 순차적 활성)

기존 bash 파이프라인을 두고 새 기능을 **점진 활성**. 각 단계에서 관측→검증→다음 이동.

### 단계 1: 거버넌스 게이트 (현재 활성)

**상태**: 기본 on  
**역할**: 머지 직전 로컬 shim 판정  
**토글**: `FLOWOPS_GOVERNANCE=on` (기본)

- 변경 파일 검사 (path prefix + 정규식)
- `merge_decision` ∈ {direct, pr, block} 판정
- 파이프라인에 블로킹 (실패 시)

**모니터링**: 파이프라인 로그에서 `[governance]` 라인 확인

### 단계 2: 거버넌스 HTTP 경유 (준비 단계)

**상태**: off  
**조건**: `FLOWOPS_GOVERNANCE_SERVICE_URL` + `GOVERNANCE_SERVICE_TOKEN` 설정  
**역할**: 게이트를 컨트롤 플레인 서비스로 승격  
**특징**: 실패 시 로컬 shim 자동 폴백

```bash
export FLOWOPS_GOVERNANCE_SERVICE_URL="http://api:8000/api/v1/governance/evaluate"
export GOVERNANCE_SERVICE_TOKEN="<service-token>"
bash scripts/auto_dev_pipeline.sh
```

**활성화 기준**:
- ✅ 로컬 shim이 주기적으로 정확한 판정을 내리는지 확인 (1주 관측)
- ✅ API 엔드포인트 응답성 검증

### 단계 3: Temporal 섀도우 레일 (섀도우 병행)

**상태**: off  
**토글**: `FEATURE_TEMPORAL=true` (워커), `FLOWOPS_TEMPORAL=true` (트리거)  
**역할**: 기존 거버넌스 결정을 Temporal `ShadowDeliveryWorkflow`에서 **미러링·대조 로깅**  
**부작용**: 0 (머지/커밋/PR/Linear-write 없음)

```bash
export FEATURE_TEMPORAL=true
export FLOWOPS_TEMPORAL=true
bash scripts/auto_dev_pipeline.sh
```

**로그 비교**:
- 파이프라인 `[governance]` 판정
- Temporal UI → `ShadowDeliveryWorkflow` 히스토리 → `evaluate_governance_activity` 결과
- 두 판정 **일치 확인** = P1 컷오버 전제

**활성화 기준**:
- ✅ Temporal 서버 안정성 확인 (3일+ 24h uptime)
- ✅ bash vs 워크플로 판정 일치율 100% (샘플 20건+)
- ✅ 미러링 지연 <5초

### 단계 4: LLM 게이트웨이 계측 (계측 시작)

**상태**: off  
**토글**: `FEATURE_LLM_GATEWAY=true`  
**역할**: 모든 AI 호출을 게이트웨이 경유, LLM 원장에 토큰/비용 기록

```bash
export FEATURE_LLM_GATEWAY=true
bash scripts/auto_dev_pipeline.sh
```

**원장 조회**:
```bash
# 프로젝트별 토큰/비용
curl -s http://localhost:8000/api/v1/llm-ledger \
  -H "Authorization: Bearer $API_TOKEN"

# 요약
curl -s http://localhost:8000/api/v1/llm-ledger/summary
```

**활성화 기준**:
- ✅ 5건+ 이슈 처리 후 원장 데이터 축적 확인
- ✅ 토큰 계산 정확도 검증 (실제 비용 대비)

### 단계 5: 3단 트리아지 관측 (관측만, 판정 미적용)

**상태**: off  
**토글**: `FLOWOPS_GOVERNANCE_TRIAGE=on`  
**역할**: risk_score, budget 밴드, triage ∈ {auto, review, block} **계산만** (판정 불변)

```bash
export FLOWOPS_GOVERNANCE_TRIAGE=on
bash scripts/auto_dev_pipeline.sh
```

**로그 분석**:
- 파이프라인 로그: `[triage] risk_score=X.X triage={auto|review|block}`
- 원장: 프로젝트별 토큰 누적 vs budget 한도
- Temporal UI: `EvaluateGovernanceActivity` → triage 필드

**활성화 기준**:
- ✅ LLM 원장이 2주+ 데이터로 안정적 계산
- ✅ risk_score 분포 분석 (auto/review/block 비율)
- ✅ 한도값 설정 (CE-297 선결 필요)

### 단계 6: 예산·트리아지 집행 (판정 강등)

**상태**: off  
**토글**: `FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE=on` (+ `FLOWOPS_GOVERNANCE_TRIAGE=on`)  
**역할**: triage 판정을 `merge_decision`에 반영  
- triage=review → merge_decision=pr (강등)
- triage=block → merge_decision=block (차단)

```bash
export FLOWOPS_GOVERNANCE_TRIAGE=on
export FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE=on
bash scripts/auto_dev_pipeline.sh
```

**활성화 기준** (중요):
- ✅ CE-297 완료 (구독 시트 수, TPM/RPM 실측) ← **블로킹**
- ✅ 한도값 Anthropic Console 확인 후 설정
- ✅ 단계 3 섀도우 관측이 2주+ 검증 완료
- ✅ Operations 팀 교육 완료 (예산 초과 대응)

### 단계 7: 하이브리드 러너 실행 (P3)

**상태**: 미구현  
**범위**: agent `RunnerHandler` (command.run_task 실행)  
**역할**: Temporal 워크플로에서 데스크탑/클라우드 러너로 태스크 배치  
**선결**: 수주 인테이크 자동화 배선

**활성화 기준**:
- ✅ agent 핸드셰이크 안정성 확인 (CE-300)
- ✅ 러너 프로토콜 정의 확정 (CE-301)
- ✅ 데스크탑 러너(구독 시트) 동시성 세마포어 구현
- ✅ 3단계~6단계 완료 및 운영 안정성 확인

---

## 5. 거버넌스·리스크 통제

### 거버넌스 게이트 이진 판정

`pre_merge_gate.py` SSOT에서 판정:

| 경로 | merge_decision | 조건 | 결과 |
|------|------|------|------|
| 직접 머지 | `direct` | LOW 위험 + FLOWOPS_AUTO_MERGE=on | 즉시 push |
| PR | `pr` | HIGH 위험 또는 FLOWOPS_AUTO_MERGE=off | GitHub PR (CI 필수) |
| 차단 | `block` | contract 오류 또는 ticket 누락 | Backlog + 로그 |

### 리스크 티어링 (현행 = 2단 이진)

| 티어 | 판정 기준 | 직접머지 | 기본 경로 |
|------|---------|------|--------|
| **HIGH** | path: `clickeye-contracts/`, `clickeye-infra/` + 정규식: `auth`, `secur`, `secret`, `crypto`, `password`, `token`, `rbac`, `permission`, `credential` | ❌ 불가 | PR 강등 |
| **LOW** | 그 외 전부 | ✅ 가능 (AUTO_MERGE=on 시) | auto (또는 PR) |

### 3단 트리아지 (P2, 현재 관측만)

**선결**: 한도값 설정 + CE-297 완료

| 밴드 | 조건 | 권장 판정 |
|------|------|---------|
| **auto** | risk_score < 0.40, budget 충분 | merge_decision=direct (자동) |
| **review** | 0.40 ≤ risk_score < 0.80 또는 budget 주의 | merge_decision=pr (수동 검토) |
| **block** | risk_score ≥ 0.80 또는 budget 초과 | merge_decision=block (차단) |

**risk_score 구성** (실제 계산식):
- 변경 파일 수: n/40 (최대 ~0.30)
- HIGH tier 포함: +0.40
- 테스트 커버리지 <70%: +0.20
- diff 라인 수 >400: +0.20
- 합산: 0.0~1.0 범위 (소수점 셋째 자리 반올림)

### 도그푸딩 (ClickEye 자체)

**원칙**: ClickEye contracts·infra·auth 변경은 게이트가 **자신을 PR로 강등**

게이트가 감지하는 경로:
- `clickeye-contracts/**`
- `clickeye-infra/**`
- `*auth*` (패턴)
- `*secret*`, `*token*` 등

→ merge_decision=pr (권위 파이프라인 불허)

---

## 6. 경제성 (고정가 SI)

### 인증·비용 모델

| 실행 환경 | 인증 | 비용 처리 | 용도 |
|---------|------|---------|------|
| **데스크탑 런타임** | claude.ai 구독 세션 | 고정비 (구독) | 주력 (낮은 지연) |
| **클라우드 컨테이너** | 조직 API 키 | 종량 (원장 기록) | 폴백 (높은 동시성) |

### LLM 원장 회계

```
프로젝트별 토큰 누적:
  ├─ 구독 세션 → cost=NULL (고정비 처리)
  ├─ 조직 API 키 → cost=$$$  (가격맵 적용)
  └─ key_source로 구분

가격맵: clickeye-api/app/data/llm_pricing.json (실제 모델 및 가격)
  ├─ claude-sonnet-5: input=$3/1M, output=$15/1M
  ├─ claude-opus-4-8: input=$5/1M, output=$25/1M
  ├─ claude-haiku-4-5: input=$1/1M, output=$5/1M
  └─ claude-sonnet-4-6: (레거시, 상세 파일 참조)
```

### 원장 조회

```bash
# 전체 ledger
curl http://localhost:8000/api/v1/llm-ledger \
  -H "Authorization: Bearer $TOKEN"

# 프로젝트 요약
curl http://localhost:8000/api/v1/llm-ledger/summary

# 예상 응답 (illustrative)
{
  "CE-100": {
    "input_tokens": 125000,
    "output_tokens": 45000,
    "cost_usd": 0.89,
    "key_source": "subscription|org_key",
    "created_at": "2026-07-20T..."
  },
  ...
}
```

### 실마진 (설계 노트 이월)

| 항목 | 현황 | 선결 |
|------|------|------|
| ROI 견적 | roi_service.py (인건비 기반) | ✅ 완료 |
| LLM 원장 | llm_ledger_service.py (토큰 기반) | ✅ 계측 중 |
| **실마진** | 견적 cost vs 실제 cost 대비 | ⏳ 단위 통일 필요 |

**이월 이유**: 현재 ROI는 KRW(인건비/시간), LLM 원장은 USD(토큰)로 단위 불일치. 실마진 정의(시간당 평균 비용으로 통일)를 선행해야 한다.

**코드 앵커**:
- `clickeye-api/app/services/roi_service.py` → TODO: margin_calculation
- `clickeye-api/app/services/llm_ledger_service.py` → TODO: actual_vs_estimate

---

## 7. 블로킹·선결조건 (사람 액션 필수)

### CE-297: 구독 시트 동시성 실측

**현황**: Backlog, 사람 액션 대기  
**영향**: §5 예산·§6 원장·데스크탑 러너 스케줄  

필수 작업:

1. **Anthropic Console 접속**
   - URL: https://console.anthropic.com/
   - Organization 관리자로 로그인
   
2. **구독 시트 수 확인**
   - Settings → Billing & usage → Team members (또는 Seats)
   - claude.ai 구독 플랜의 **현재 좌석 수** 기록
   - 예: "현재 3석 구독, 최대 10석 계약" 등

3. **API 레이트 한도 측정** (선택)
   - 조직 API 키에 크레딧 충전 (부족 시)
   - `docs/hybrid-runner-headless-poc.md` §2 "재현 방법" 참고
   - curl로 `/v1/messages` 요청 → `anthropic-ratelimit-*` 헤더 기록
   - 예: `requests-limit: 40000/min`, `tokens-limit: 2000000/min`

4. **본 문서·hybrid-runner-headless-poc.md 갱신**
   - 수치 기록
   - CE-297 완료 마크 (`status: done`)

**선결 종료 기준**:
- ✅ 좌석 수 확인 + 기록
- ✅ TPM/RPM 실측 (선택) 또는 Anthropic 지원팀 문의로 기본값 확인
- ✅ 동시 헤드리스 세션 상한 실측 (구독 시트 기반)

**이후 영향**:
- 단계 6 (~예산·트리아지 집행~) 활성화 가능
- 데스크탑 러너(P2) vs 클라우드 러너(P3) 우선순위 재판단
- 동시성 세마포어(`--concurrency N`) 설정값 확정

---

## 8. 운영 체크리스트·모니터링

### 일일 운영 (권장)

#### 아침: 스택 상태

```bash
# 1. 컨테이너 헬스
bash /mnt/c/workspace/clickeye/clickeye-infra/scripts/deploy.sh status

# 2. API 응답
curl -s http://localhost:8000/api/v1/health

# 3. 로그 확인 (에러)
bash deploy.sh logs 2>&1 | grep -i error | head -20
```

#### 오전: 파이프라인 모니터링

```bash
# Linear 대시보드에서 Queued 이슈 확인 (ClickEye 팀)
# https://linear.app/clickeye/issues?state=queued

# 파이프라인 실행 중?
ps aux | grep auto_dev_pipeline.sh

# 최근 완료 이슈 확인
# Linear 대시보드 또는 TASK.md 생성 이력 참조
```

#### 오후: 원장 및 비용

```bash
# LLM 원장 요약
curl -s http://localhost:8000/api/v1/llm-ledger/summary | jq '.[] | {project, input_tokens, output_tokens, cost_usd}'

# 일일 비용 추이 (시계열)
curl -s http://localhost:8000/api/v1/llm-ledger \
  | jq '.[] | select(.created_at > "2026-07-20T00:00:00Z") | {project, input_tokens, output_tokens, cost_usd}' \
  | head -20
```

#### 저녁: Temporal 히스토리

```bash
# Temporal UI에서 워크플로 확인
# http://localhost:8080 → Workflows 탭

# 또는 CLI (tctl 설치 필요)
tctl workflow list
```

### 주간 점검 (금요일)

| 항목 | 확인 | 기준 |
|------|------|------|
| **API 가용성** | 파이프라인 성공률 | ≥95% |
| **원장 정확도** | 계산 오류 | 0건 |
| **Temporal 안정성** | 업타임 | ≥99% |
| **거버넌스 판정** | FALSE POSITIVE | ≤5% |
| **비용 추이** | WoW 증가율 | <+30% |

### 문제 발생 시 대응

#### 파이프라인 정지

```bash
# 1. 마지막 실행 상태 확인
cat .ralph/.pipeline_lock

# 2. 로그 확인 (파이프라인 출력)
# 파이프라인 실행 로그 참조 (위치는 --verbose 플래그 또는 CLAUDE_LOG 환경변수 확인)

# 3. 즉시 복구 (lock 해제)
rm .ralph/.pipeline_lock
bash scripts/auto_dev_pipeline.sh --once
```

#### API 503

```bash
# 1. 스택 재시작
bash clickeye-infra/scripts/deploy.sh down
sleep 5
bash clickeye-infra/scripts/deploy.sh up

# 2. DB 상태 확인
docker exec clickeye-db psql -U postgres -c "SELECT version();"

# 3. 긴급 폴백 (로컬 shim)
export FLOWOPS_GOVERNANCE_SERVICE_URL=""
bash scripts/auto_dev_pipeline.sh --once
```

#### Temporal 미응답

```bash
# Temporal 컨테이너 재시작
docker restart clickeye-temporal

# 또는 전체 스택 재시작
bash clickeye-infra/scripts/deploy.sh down && sleep 5 && bash clickeye-infra/scripts/deploy.sh up

# 섀도우 비활성
export FLOWOPS_TEMPORAL=off

# 파이프라인 재개
bash scripts/auto_dev_pipeline.sh --once
```

---

## 9. 로드맵 위치 (P0~P4)

### 현재 (P0 완료)

| 항목 | 상태 | 메모 |
|------|------|------|
| Temporal 단일노드 | ✅ 완료 | docker-compose |
| 거버넌스 커널 | ✅ 완료 | SSOT, cli/api |
| LLM 게이트웨이+원장 | ✅ 구현 | 계측 활성 가능 |
| agent 핸드셰이크·register | ✅ 완료 | CE-300/F 구현, 실행 핸들러는 P3 |
| Runner 프로토콜 | ✅ 정의 | 위치 무관 스키마 |
| **CE-297 구독 동시성** | ⏳ Backlog | **사람 액션 필요** |

**특징**: 모두 가산적(additive). 기존 파이프라인 손상 0.

### P1: 섀도우 병행

**목표**: Temporal 새 레일로 기존과 동일 결과 생성 후 비교 검증

- [ ] Temporal 섀도우 워크플로(`ShadowDeliveryWorkflow`) 안정 운영
- [ ] bash vs 워크플로 거버넌스 판정 **일치율 100%** 확인 (20건+)
- [ ] FLOWOPS_TEMPORAL 토글로 회귀 경로 유지
- [ ] Temporal UI 메트릭(지연, 성공률) 안정성 확인
- [ ] 선택 프로젝트(1~2개)에서 현장 테스트

**결과**: 기존→Temporal 컷오버 결정

### P2: 동시성·거버넌스 강화

**목표**: WFQ 기반 예산집행 + 3단 트리아지 라우터

- [ ] LLM 원장 2주+ 데이터로 안정화
- [ ] CE-297 완료 (시트 수, TPM/RPM 실측)
- [ ] 한도값 설정 (월별 예산 등)
- [ ] 3단 트리아지 로직 구현 + 관측 모드
- [ ] 예산·트리아지 집행 활성 (ENFORCE=on)
- [ ] **첫 대규모 병렬**: 20~30개 프로젝트 동시 실행

**특징**: 전략 성과의 핵심. 거버넌스 커널이 심장 역할.

### P3: 하이브리드 러너 + 인테이크

**목표**: 완전 하이브리드 (데스크탑+클라우드) + 수주 자동화

- [ ] agent `RunnerHandler` 구현 (command.run_task 실행)
- [ ] 러너 라우터: 프로젝트 → 데스크탑/클라우드 자동 배치
- [ ] 수주 인테이크 배선 (요구 분석 → 딜리버리 인게이지먼트 → 실행)
- [ ] 마진 추적 (ROI 견적 vs LLM 원장)

**선결**: P2 완료 + 러너 프로비저닝

### P4: 스케일·경화

**목표**: 엔터프라이즈 스케일, 기존 SaaS 기능 폐기

- [ ] Kubernetes 도입 (필요 측정 후)
- [ ] 12단계 위저드 → 폐기
- [ ] 공개 라이센싱 / 카탈로그 → 폐기
- [ ] **ClickEye = 순수 내부 SI 팩토리**로 정체성 확정

---

## 10. 참고 자료

| 문서 | 용도 |
|------|------|
| `docs/si-factory-transition.md` | **마스터 설계 기준** (왜 이렇게 하는가) |
| `docs/pipeline-guide.md` | 파이프라인 상세 (STEP A~C, 토글 설명) |
| `docs/agent-protocol.md` | agent ↔ API 통신 프로토콜 |
| `docs/hybrid-runner-headless-poc.md` | CE-297 결과 + 재현 방법 |
| `scripts/pre_merge_gate.py` | 거버넌스 게이트 권위 코드 |
| `scripts/auto_dev_pipeline.sh` | 파이프라인 메인 루프 |
| `CLAUDE.md` | 프로젝트 개발 규칙 |

---

**마지막 갱신**: 2026-07-20  
**다음 갱신**: CE-297 완료 시 (단계 6 활성화 가이드 추가)
