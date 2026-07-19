---
title: ClickEye SI 팩토리 전환 — 마스터 설계 기준
category: architecture
status: current
last_updated: 2026-07-16
related:
  - docs/hybrid-runner-headless-poc.md
  - docs/architecture-overview.md
  - docs/pipeline-guide.md
  - docs/agent-protocol.md
  - CLAUDE.md
---

# ClickEye SI 팩토리 전환 — 마스터 설계 기준

**확정일**: 2026-07-15  
**적용 범위**: P0~P4 모든 작업의 공용 기준점 (P0 티켓 CE-296~301 섹션 참조 기준)

---

## 1. 전략 재정의

### 1.1 실행 계층 균일 추상화

ClickEye를 **"위저드→ZIP 빌더"** (대외 판매 SaaS)에서 **사내 SI 딜리버리 팩토리 / 관제 플레인**으로 전환합니다.
회사가 수주한 20~50개+ SI 프로젝트를 **AI 에이전트로 동시 개발·관리**하는 내부 운영 무기입니다.

**핵심 통찰**:
- 클라이언트는 진행 모니터링 미실시 (완성품 납품만)
- 딜리버리팀 내부 전용 운영
- 기존 web+api는 **기획·조율 컨트롤 플레인** 역할 (실제 AI 코딩 실행은 로컬에서만 수행)
- 실행 기원: 로컬 `claude -p` 구독 세션 + 단일 PID락 + 단일 워킹트리 + 완전 순차 bash `auto_dev_pipeline.sh`
- "프로젝트" 개념 폐기 → **작업 단위 = Linear 이슈**

---

## 2. 확정된 핵심 결정 3가지 (2026-07-15)

### 2.1 실행 인증 = 구독 시트 주력

- **하이브리드는 유지하되**, 구독 시트(claude.ai OAuth)를 주력으로 확정
- 데스크탑 러너 = 구독 시트 주력
- 조직 API 키 / 클라우드 팔 = 최소 폴백으로 격하
- **크레딧 지양** → 고정가 SI 경제성 기반 구축

### 2.2 오케스트레이터 = Temporal 자체 호스팅

- Temporal 단일 노드 시작 (clickeye-infra)
- 필요시 스케일 아웃 (K8s는 P4 필요 측정 시만)

### 2.3 적정 시작 복잡도

- 소규모 컨테이너 풀
- Kubernetes는 P4에서 필요 측정 후 도입
- 언어 변경 ≈ 0 (Python·FastAPI·Next.js 유지)
- 신규: Temporal 인프라 1개만 추가

---

## 3. 목표 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  클라우드 — 컨트롤 플레인 (clickeye-api)                    │
│  ├── control_tower          (다중 고객·프로젝트 관제, KEEP)  │
│  ├── roi                    (고정가 SI 견적·마진, KEEP)      │
│  ├── governance 커널        (거버넌스 게이트 SSOT, ADAPT)   │
│  ├── LLM 게이트웨이+원장    (토큰/비용 추적, NEW)            │
│  └── Temporal 오케스트레이션(NEW)                            │
│                                                              │
│  오케스트레이션 코어: Temporal 워크플로우 (NEW)              │
│                                                              │
│  하이브리드 러너 패턴 (§2.4)                                │
│  ├── 데스크탑 러너          (구독 시트, 주력)               │
│  └── 클라우드 컨테이너      (조직 API 키, 폴백)             │
│      └── clickeye-agent (전송층 실재·실행 핸들러, ADAPT)    │
│                                                              │
│  Runner 태스크 프로토콜                                      │
│  └── commands.ts/messages.ts (위치 무관 실행 계약, ADAPT)   │
└─────────────────────────────────────────────────────────────┘
        │  
        │  ZIP 다운로드 / 작업 제출 / 상태 폴링
        ▼
┌─────────────────────────────────────────────────────────────┐
│  사용자 로컬 PC                                              │
│  └── auto_dev_pipeline.sh (점진 교살→Temporal 이주, P1~P2)  │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 컨트롤 플레인 계층

| 모듈 | 역할 | 처리 | 근거 |
|------|------|------|------|
| `control_tower_service` | 다중 고객·프로젝트 관제 | KEEP | 기존 구조 유지 |
| `roi_service` | 고정가 SI 견적·마진 계산 | KEEP | 기존 구조 유지 |
| `governance 커널` | 거버넌스 게이트 SSOT | ADAPT | CE-298 구현 |
| `LLM 게이트웨이+원장` | 토큰/비용 추적·예산집행 | NEW | CE-299 구현 |

### 3.2 하이브리드 러너 패턴 (§2.4)

데스크탑 러너와 클라우드 컨테이너가 **동일하게 소비하는 위치 무관 실행 추상화**:

- **데스크탑 러너**: claude.ai 구독 세션 (주력)
- **클라우드 컨테이너**: 조직 API 키 (폴백)
- **clickeye-agent**: 전송층 실재 + 실행 핸들러 (§1.1 실행 계층)
- **Runner 태스크 프로토콜** (commands.ts/messages.ts): 위치 무관 실행 계약

### 3.3 오케스트레이션 코어

- **Temporal**: 워크플로우 상태 관리, 작업 스케줄링, 재시도
- 단일 노드부터 시작, 필요시 스케일

---

## 4. 중심 설계 원칙 — 스트랭글러 패턴

### 마이그레이션 전략

**빅뱅 없음**. 기존 bash 파이프라인을 두고 새 Temporal 레일을 옆에 세워 **프로젝트 단위 점진 이주**:

1. P0: 기초 인프라 (Temporal + governance + LLM 게이트웨이)
2. P1: 새 레일 섀도우 병행, 기존과 동일 출력 비교 후 컷오버
3. P2 이후: 동시성·거버넌스 강화
4. **모든 단계 FLOWOPS_* 토글**: off 시 회귀 0 (안전성)

### SSOT 원칙

- 로직 중복 없음
- 각 컴포넌트 한 곳에서만 소스
- 거버넌스 게이트 = 유일한 제어점 (pre_merge_gate.py)

### 회귀 기준

각 P0 티켓 완료 기준에 **"회귀 없음"** 반복:
- 기존 파이프라인은 여전히 작동
- 새 경로는 병행 또는 폴백 가능

---

## 5. 자산 처리표 (부분 요약)

P0 티켓들의 "자산 처리" 라인에서 재구성한 부분집합입니다.  
**주의**: 34자산 전체표는 deep-reasoner 원본 분석에만 존재하며, 미저장 상태입니다.  
아래 표는 P0~P1에 영향을 미치는 핵심 자산만 정리한 것입니다.

| 자산 | 처리 | 상세 | 근거 티켓 |
|------|------|------|----------|
| `pre_merge_gate.py` | ADAPT | 거버넌스 커널 SSOT, 이진 게이트 → P2 3단 주의 라우터로 진화 준비 | CE-298 |
| `control_tower_service` | KEEP | 기존 고객/프로젝트 관제 유지 | — |
| `roi_service` | KEEP | 고정가 SI 견적 계산 유지 | — |
| `commands.ts` | KEEP/ADAPT | Runner 프로토콜 표준화, 위치 무관 인터페이스 | CE-301 |
| `messages.ts` | KEEP/ADAPT | Runner 메시지 스키마 표준화 | CE-301 |
| `clickeye-agent` | ADAPT | 전송층 ~30-40% 실재, 핸드셰이크 버그 수정 + 재접속 검증(P0), 실행 핸들러는 P3 신규 | CE-300 |
| `Temporal` | NEW | 워크플로우 오케스트레이션, 단일 노드 | CE-296 |
| `LLM 게이트웨이+원장` | NEW | 토큰/비용 추적, 예산집행 | CE-299 |
| `auto_dev_pipeline.sh` | 점진 교살 | P1~P2에 걸쳐 Temporal로 이주, FLOWOPS_* 토글 유지 | P1~P2 |

---

## 6. §3 리소스 거버넌스

### 현황

구독 시트 기반 동시성 세마포어 체계 구축 예정 (P2 확정).

### 현재 블로킹 사항

- 구독 시트 수 확인 필요 (사람 액션)
- 크레딧 충전 (선택적)
- TPM / RPM 실측 필요 (둘 다 사람 액션)

### 참고 자료

`docs/hybrid-runner-headless-poc.md` (CE-297 SPIKE 결과):
- 컨테이너 조직-키 헤드리스 = 조건부 가능 (인증 경로 유효, 크레딧 부족으로 실응답 미검증)
- TPM/RPM 측정 불가 (크레딧 부족으로 레이트리밋 헤더 미수신)
- 구독 시트 수는 **Anthropic Console에서 사람이 수동 확인** 필요 (API/CLI 조회 불가)

---

## 7. §4 거버넌스 게이트

### 현행 시스템 (2단 이진 게이트)

`pre_merge_gate.py` = SSOT 권위 게이트:
- 경로 1: direct-merge (유일한 비보호 경로) → `merge_decision: direct`
- 경로 2: PR (승인 필수) → `merge_decision: pr`
- 경로 3: 차단 → `merge_decision: block`

### §4.2 리스크 티어링 (현행 = 2단 이진)

현행 `classify_risk`는 **HIGH/LOW 2단 이진 분류**입니다 (MEDIUM 티어는 코드에 없음 — `medium-risk`는 Linear 라벨일 뿐 게이트 판정 티어가 아님):

| 위험 티어 | 판정 기준 (경로 prefix + 정규식) | 직접머지 가능? |
|----------|------|---|
| HIGH | `clickeye-contracts/`·`clickeye-infra/` prefix + `auth`/`secur`/`secret`/`crypto`/`password`/`token`/`rbac`/`permission`/`credential` 정규식 | 불가 → PR 강등 (RISK_DEMOTE on 시) |
| LOW | 그 외 전부 | 자동 (AUTO_MERGE=on 시 direct) |

### P2 진화 예상 (3단 주의-트리아지 라우터)

§4.2 이진 게이트를 기반으로 P2에서 3단 주의-트리아지 라우터로 확장 예정 (아래는 방향성 예측 — 미확정):
- HIGH 위험 자동 PR 라우팅 강화
- 위험 점수 동적화 (복잡도·변경 범위·테스트 커버리지 기반)
- governance 커널(CE-298)이 이 확장의 심장

---

## 8. P0~P4 로드맵

### P0: 토대 (현재)

**목표**: 기초 인프라 확보, 새 레일 준비

- **Temporal 단일노드 기동** (CE-296)
- **governance 커널** SSOT 확정 (CE-298)
- **LLM 게이트웨이+원장** 구현 (CE-299)
- **clickeye-agent 핸드셰이크 수정** (CE-300)
- **Runner 프로토콜 표준화** (CE-301)
- **구독 시트 동시성 SPIKE** (CE-297 — 사람 액션 대기)

**특징**: 가산적 (additive) 회귀 0  
모든 작업은 기존 파이프라인을 손상시키지 않으면서 새 인프라 추가

### P1: 단일 새 레일 섀도우

**목표**: Temporal 병행 실행, 기존과 비교 후 컷오버

- 새 Temporal 워크플로우로 기존 파이프라인과 동일 결과 생성
- 현장 테스트 (선택 프로젝트)
- FLOWOPS_* 토글로 회귀 경로 유지
- 검증 후 컷오버 (기존→Temporal 단계 이동)

**첫 섀도우 워크플로 (CE-297)**: `ShadowDeliveryWorkflow`(clickeye-api/app/temporal/)가 P1의
첫 미러링 레일이다. `auto_dev_pipeline.sh`가 이슈/브랜치 확정 직후, `FLOWOPS_TEMPORAL`이 명시적으로
활성일 때만 `scripts/temporal_shadow_trigger.py`로 워크플로를 fire-and-forget 트리거한다. 셸 트리거는
bash 거버넌스 게이트와 **동일한 three-dot**(`git diff --name-only main...<head>`)으로 변경 파일을 계산해
인자로 전달하고, 워크플로는 `evaluate_governance_activity`(governance 커널 호출)만 실행해 거버넌스 결정
(merge_decision/tier/verdict)을 **대조 로깅**한다. **부작용은 0** — 머지/커밋/PR/Linear-write는 포함하지
않으며, Temporal 미가용·연결 실패 시에도 파이프라인을 막지 않는다(비블로킹, 회귀 0). 실제 컷오버(부작용
activity 배선·Linear fetch)는 후속 단계로 남긴다.

### P2: 동시성 + 거버넌스 강화 (전략 성과 터닝)

**목표**: WFQ(Work-Stealing Queue) 기반 예산집행 + 3단 주의-트리아지 라우터

- governance 커널이 심장 역할
- 토큰/비용 원장 기반 실시간 레이트 제어
- HIGH 위험 자동 PR 라우팅 (§4.2 진화)
- 첫 대규모 병렬 실행 (20~30개 프로젝트 동시)

### P3: 하이브리드 러너 완성 + 수주 인테이크

**목표**: 완전 하이브리드 (데스크탑+클라우드) 실행 핸들러 완성, 신규 프로젝트 인테이크 자동화

- clickeye-agent 실행 핸들러 P3 신규 구현
- 라우터: 프로젝트→데스크탑 또는 클라우드 자동 배치
- 수주 인테이크 자동화 (Linear 티켓→ZIP→실행)
- 마진 추적·보고 (ROI 고도화)

#### P3 설계 노트 (실동작 이월 — 스켈레톤/설계만)

**수주 인테이크 자동화 (실동작 이월):** 인테이크 자동화는 기존 modernize 흐름
(레거시 분석 → Linear 티켓화 → ZIP 산출)과 신규 agent 실행 핸들러
(`clickeye-agent`의 `RunnerHandler`, 메시지 타입 `command.run_task`)를 잇는 배선이다.
트리거 지점은 modernize 세션의 **finalize/ZIP 생성 직후** — 이 시점에서 프로젝트를
러너(데스크탑=구독 시트 주력 / 클라우드=조직 키 폴백)로 `RunnerTaskPayload`
(`task_id`/`project_id`/`target`/`ticket_id`|`prompt`|`command`)로 push 한다.
실동작 배선(러너 push, 라우터 배치)은 범위 폭발 방지를 위해 이월하며, 코드 앵커는
modernize finalize 서비스와 `clickeye-agent`의 `RunnerHandler` docstring TODO로 표시한다.

**마진 관리 (실동작 이월):** 실마진 = ROI 견적(추정 `clickeye_cost`, `roi_service.py`)
대비 실제 비용(LLM 원장 실 cost, `llm_ledger_service.py` + 향후 인건비/시간).
두 축은 `project_id`를 상관키로 조인한다. 현재 ROI는 인건비(일/역할) 기반 KRW,
LLM 원장은 토큰 기반 cost로 **단위가 불일치**하므로 실마진 정의(인건비 vs 토큰비
단위 통일)를 선행 설계해야 한다. 실동작 집계·리포트는 이월하며, 코드 앵커는
`roi_service.py`/`llm_ledger_service.py`의 TODO 주석으로 표시한다.

### P4: 스케일 + 경화 + 레거시 폐기

**목표**: 엔터프라이즈 스케일, 필요시 K8s, 기존 SaaS 기능 폐기

- Kubernetes 도입 (필요 측정 후)
- 12단계 위저드 / 공개 라이센싱 / 공개 카탈로그 = 폐기
- ClickEye = 순수 내부 SI 팩토리로 정체성 확정

---

## 9. P0 티켓 매핑 표

| 티켓 | 담당 | 제목 | 상태 | 우선도 | 완료 기준 |
|------|------|------|------|--------|----------|
| CE-296 | infra | Temporal 단일노드 기동 | Wait | low | Temporal 서버+UI running, 빈 워크플로 실행, 토글 off 시 회귀 0 |
| CE-297 | spike | 구독시트 동시성 실측 | Backlog | high | 시트 수 확인·TPM/RPM 실측 (사람 액션 대기) |
| CE-298 | api | governance 커널 SSOT | 진행중 | medium | 커널 추출·회귀 0·HTTP 독립 호출·HIGH 차단 보존 |
| CE-299 | api | LLM 게이트웨이+원장 | Wait | high | 모든 AI 호출 계측·프로젝트별 토큰/비용 원장(로깅만) |
| CE-300 | agent | 핸드셰이크 수정 + 재접속 검증 | Wait | low | agent_id↔token 핸드셰이크 수정, 끊김→자동 재접속(실행 핸들러 P3) |
| CE-301 | contracts | Runner 프로토콜 표준화 | Wait | medium | 위치 무관 태스크 실행/결과/스트리밍 스키마 + drift 통과 |

**Linear 프로젝트**: "ClickEye SI 팩토리 전환" (id: 9980f21e-0b5f-4c1c-9ead-3533203cad92)  
**팀**: ClickEye (키: CE)

---

## 10. 구현 원칙

### 10.1 회귀 없음

모든 작업은 FLOWOPS_* 토글로 장금되어, 필요시 완전 회귀 가능:

```bash
# 회귀 모드
export FLOWOPS_TEMPORAL=off        # Temporal 비활성화
export FLOWOPS_GOVERNANCE=off      # 거버넌스 게이트 비활성화 (pre_merge_gate.py 스킵)
export FLOWOPS_LLM_GATEWAY=off     # LLM 게이트웨이 비활성화

# 기존 파이프라인이 그대로 작동
bash auto_dev_pipeline.sh
```

### 10.2 단계적 마이그레이션

스트랭글러 패턴으로 단일 프로젝트 / 팀 단위 이주:

```
기존 파이프라인                  신규 Temporal 레일
│                             │
├─ project-A (기존)           │
├─ project-B (기존)           ├─ project-C (신규, 섀도우)
├─ project-D (기존)           │  │
│                             │  └─ 검증 → 컷오버
└─ ...                        └─ project-E (신규)
```

### 10.3 SSOT 유지

로직은 한 곳에서만 정의:
- **거버넌스**: `pre_merge_gate.py` (하나의 권위점)
- **실행**: `auto_dev_pipeline.sh` (단계적으로 Temporal로 이주)
- **계약**: `commands.ts` / `messages.ts` (위치 무관)

---

## 부록: 용어 정의

| 용어 | 정의 |
|------|------|
| **컨트롤 플레인** | 고객·프로젝트 관제, 견적·ROI, 거버넌스 결정 (clickeye-api) |
| **실행 계층** | 로컬/클라우드에서 AI 코딩 실행하는 인터페이스 (§1.1 제시) |
| **하이브리드 러너** | 데스크탑(구독 시트) + 클라우드 컨테이너(API 키) 이중 경로 |
| **스트랭글러 패턴** | 기존 시스템을 두고 새 시스템을 옆에 세워 점진 마이그레이션 |
| **FLOWOPS_* 토글** | 각 신규 기능을 on/off 가능하게 하여 회귀 경로 보장 |
| **SSOT** | Single Source of Truth — 로직 중복 없이 한 곳에서 정의 |

---

**마지막 검토**: 2026-07-16  
**상태**: 현재 적용 중 (P0 작업 기초)
