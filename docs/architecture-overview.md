---
title: 아키텍처 개요
category: architecture
status: current
last_updated: 2026-07-22
related:
  - clickeye-web
  - clickeye-api
  - clickeye-api/app/api/v1/router.py
  - clickeye-api/app/api/v1/projects.py
  - clickeye-api/app/api/v1/governance.py
  - clickeye-api/app/api/v1/ops_*.py
  - clickeye-api/app/models/managed_env_var.py
  - clickeye-contracts/protocol/commands.ts
  - clickeye-contracts/protocol/messages.ts
---

# ClickEye - Architecture Overview

## 1. 시스템 개요

ClickEye는 **인게이지먼트 기반 딜리버리 콘솔 + 하이브리드 러너(데스크탑 구독 / 클라우드 컨테이너)** 아키텍처를 채택한 AI 개발 자동화 SaaS 플랫폼이다.

- **웹 콘솔 (Cloud)**: 사용자가 인게이지먼트(작업 정의) 생성 → 실행 추적 → 거버넌스 & 운영 관리
- **데스크탑 러너**: 구독 사용자가 로컬 `claude -p` 모드로 AI 개발 실행 (구독시트 포함)
- **클라우드 러너**: 조직이 API 키로 클라우드 컨테이너에서 자동화 실행

비개발자도 브라우저에서 인게이지먼트를 생성하고, 개발팀은 로컬 또는 클라우드에서 실행·추적할 수 있다.

### 유사 서비스 비교
- **Vercel**: 웹에서 프로젝트 설정 → CLI로 배포
- **Firebase**: 콘솔에서 구성 → CLI로 개발/배포
- **우리**: 웹에서 인게이지먼트 생성 → 데스크탑/클라우드 러너로 AI 개발 실행 → 웹에서 추적/거버넌스

---

## 2. 전체 아키텍처 다이어그램

```
┌──────────────────────────────────────────────────────────────────┐
│  ClickEye Cloud (SaaS — 인게이지먼트 콘솔 + 거버넌스 + 운영)    │
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐                            │
│  │ Next.js     │◄──►│ FastAPI      │                            │
│  │ Frontend    │    │ Backend      │                            │
│  │             │    │              │                            │
│  │ - 대시보드  │    │ - REST API   │                            │
│  │ - 인게이지  │    │ - 인게이지   │                            │
│  │   먼트관리  │    │   관리       │                            │
│  │ - 실행 추적 │    │ - 실행 추적  │                            │
│  │ - 거버넌스  │    │ - 거버넌스   │                            │
│  │ - 운영 패널 │    │ - 운영 API   │                            │
│  └─────────────┘    └──────┬───────┘                            │
│                            │                                    │
│               ┌────────────┴────────────┐                       │
│               │                         │                       │
│        ┌──────┴──────┐          ┌───────┴──────┐                │
│        │ PostgreSQL  │          │ Redis        │                │
│        │             │          │              │                │
│        │ - 사용자    │          │ - 세션 캐시  │                │
│        │ - 조직      │          │ - 인게이지   │                │
│        │ - 인게이지  │          │   먼트 상태  │                │
│        │   먼트      │          │ - 실행 큐    │                │
│        │ - 라이센스  │          └──────────────┘                │
│        └─────────────┘                                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        │ Task API (gRPC/REST)        │
        │              │              │
        ▼              ▼              ▼
┌─────────────────┐ ┌─────────────────┐ ┌──────────────────────┐
│ 데스크탑 러너    │ │ 클라우드 러너    │ │ 클라우드 러너        │
│ (구독 사용자)    │ │ (컨테이너 A)    │ │ (컨테이너 B)        │
│                 │ │                 │ │                      │
│ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────────┐ │
│ │ claude -p   │ │ │ │ API Key     │ │ │ │ API Key         │ │
│ │ (구독시트)   │ │ │ │ (조직 키)    │ │ │ │ (조직 키)        │ │
│ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────────┘ │
│        │        │ │        │        │ │        │            │
│        ▼        │ │        ▼        │ │        ▼            │
│ [Execution]     │ │ [Execution]     │ │ [Execution]         │
│ Task 1, 2, 3 → │ │ Task 1, 2 ──────────► Task 1 ─────────┐ │
│ Report to API   │ │ Report to API   │ │ Report to API   │ │
└─────────────────┘ └─────────────────┘ └──────────────────────┘
        │                 │                      │
        └─────────────────┼──────────────────────┘
                          │
                          ▼
                  ┌──────────────────┐
                  │ Cloud API        │
                  │ (상태 저장 +     │
                  │  거버넌스 검증)   │
                  └──────────────────┘
                          │
                          ▼
                  ┌──────────────────┐
                  │ 웹 콘솔           │
                  │ (실시간 대시보드) │
                  └──────────────────┘
```

---

## 3. 웹 콘솔 (Cloud) 상세

### 3.1 역할과 책임

| 역할 | 설명 |
|------|------|
| **사용자 인증** | 계정 관리, 로그인, JWT 토큰 + organization_id/system_role 노출(CE-302) |
| **조직 스코핑** | 인게이지먼트 생성 시 대상 조직(organization_id) 지정 + 멤버십 기반 인가(CE-302) |
| **인게이지먼트 관리** | 인게이지먼트 생성, 편집, 삭제, 목록 조회 |
| **실행 추적** | 데스크탑/클라우드 러너 실행 상태 모니터링 (큐 → 실행 중 → 완료/실패) |
| **거버넌스 정책** | GET /governance/policy 커널 SSOT — 자동화 가이드라인(계약 정책/규칙) 노출(CE-303) |
| **운영 패널** | Superadmin 전용 컨테이너/env/테이블 관리 + Temporal 링크(CE-305) |
| **라이센스 관리** | 플랜 관리, 프로젝트/인게이지먼트 한도 |

### 3.2 저장하는 데이터

```yaml
저장함:
  - 사용자 계정 (email, password_hash)
  - 조직 정보 (company_name, size, industry, tech_stack)
  - 인게이지먼트 메타데이터 (이름, 설명, 상태, 실행 결과)
  - 실행 기록 (runner_type, start_time, end_time, status, logs)
  - 라이센스/플랜 정보

저장하지 않음:
  - 사용자의 API 키 (로컬 .env 에만 — 클라우드 러너는 조직 키)
  - 사용자 소스 코드
  - 사용자의 Claude/Gemini API 키
  - 사용자의 비즈니스 데이터
```

### 3.3 웹 라우트 & 컴포넌트 구조

```
clickeye-web (Next.js 15)
├── 랜딩 페이지                              (완료)
├── 인증 (로그인/회원가입)                    (완료)
├── 딜리버리 콘솔 (/delivery)                 ← 메인 플로우
│   ├── 인게이지먼트 목록 (/delivery)          (mock 토글: stores/mock-mode-store)
│   └── 인게이지먼트 상세 (/delivery/[engagementId])
│       ├── 콘솔 헤더 / 딜리버리 스테퍼        (components/delivery/*)
│       ├── 이슈 보드 (issue-board)
│       ├── 검토 라운드 (review-list)
│       ├── 비용 카드 (cost-card, LLM 원장)
│       └── 거버넌스 정책 패널                 (governance-policy-panel, CE-303)
│     * 실데이터는 projects API(useProject) 재사용, 미배선 데이터(세션/팀상태/원장/리뷰)는
│       mock(lib/delivery-mock.ts) — 전용 인게이지먼트 엔드포인트는 로드맵
├── 프로젝트 (/projects, /projects/[projectId]/{dashboard,ai-team,contracts,insights,settings})
├── 온보딩 (/onboarding/{maturity,preset})
├── 가이드 (/guide/[slug])                     (guide-loader + markdown-content)
├── 운영 패널 (/admin/ops, Superadmin)         (CE-305)
│   └── /containers · /env · /tables[/[table]]
├── 관리자 (/admin/{control-tower,registry,recommendations,roi-standards,pm,users,audit,contracts,settings})
└── 설정 (/settings/{anthropic,linear,members})  (CE-302)

clickeye-api (FastAPI, /api/v1 — app/api/v1/router.py 실 등록 라우터)
├── REST API
│   ├── 인증/조직/RBAC (auth, organizations, rbac)            (완료·CE-302)
│   ├── 프로젝트 (projects + /preview, catalog, artifacts)     (완료)
│   ├── 오케스트레이션 (orchestrator, review_pipeline, quality_gate)
│   ├── PM/추천/성숙도/프리셋 (pm_profiles, admin_recommendations, maturity, presets)
│   ├── 계약 (contracts, project_contracts, contracts_sync)
│   ├── 거버넌스 정책 API (governance)                         (CE-303)
│   ├── 운영 API (ops_infra/env/db)                            (CE-305)
│   ├── 컨트롤타워/ROI/원장 (control_tower, roi, llm_ledger)
│   └── 연동 (integrations, github_app, *_credentials, setup_bootstrap)
└── Task Protocol / WebSocket (app/ws/*)
    └── 러너 ↔ 클라우드 API 통신 (agent-protocol §7)
```

---

## 4. 러너 (Runner) 상세

### 4.1 역할과 책임

#### 데스크탑 러너 (구독 사용자)
| 역할 | 설명 |
|------|------|
| **구독시트 포함** | 로컬 `.claude/` 디렉토리에 에이전트/스킬/파이프라인 포함 |
| **로컬 실행** | `claude -p` 프롬프트 모드로 AI 개발 수행 |
| **실행 결과 보고** | 완료/실패 상태를 Cloud API에 전송 |
| **BYOK** | 사용자 자신의 Claude API 키 사용 |

#### 클라우드 러너 (조직)
| 역할 | 설명 |
|------|------|
| **조직 API 키** | 조직 키로 인증 (사용자 구독 불필요) |
| **컨테이너 실행** | 클라우드 컨테이너에서 Task 자동 실행 |
| **병렬 처리** | 여러 인게이지먼트 동시 실행 가능 |
| **실행 결과 보고** | 로그/결과를 Cloud API에 저장 |

### 4.2 데스크탑 러너 구조 (구독시트)

```
my-subscription/
├── CLAUDE.md                # 프로젝트 가이드
├── .claude/
│   ├── agents/              # 에이전트 .md 파일들
│   ├── skills/              # 스킬 .md 파일들
│   └── settings.json        # Claude Code 설정
├── .env                     # API 키 (유저 입력값)
├── .env.example             # API 키 템플릿
└── scripts/                 # Hook 스크립트

# 사용 방법
$ claude -p                 # 구독 모드 실행
> engagement <engagement-id>  # 인게이지먼트 ID 지정
> run                         # 실행 시작
> report                      # 결과를 Cloud API에 전송
```

### 4.3 클라우드 러너 구조 (컨테이너)

```
# 클라우드 러너는 stateless 컨테이너로 동작
ClickEye Cloud
├── Container Runner Pool
│   ├── Container A (Task 1, 2)
│   ├── Container B (Task 3, 4)
│   └── Container C (Task 5)
│
└── Task Queue (Redis)
    ├── Task 1 (pending) → Container A (executing) → completed
    ├── Task 2 (pending) → Container A (executing) → completed
    ├── Task 3 (pending) → Container B (executing) → failed
    ├── Task 4 (pending) → Container B (queued)
    └── Task 5 (pending) → Container C (executing)
```

### 4.4 실행 흐름

#### 데스크탑 러너 흐름
```
[웹: 인게이지먼트 생성]
        │
        ▼
[웹: "실행" 버튼 클릭]
        │
        ▼
[데스크탑: `claude -p` 모드]
        │
        ▼
[데스크탑: engagement <id> 입력]
        │
        ▼
[데스크탑: 에이전트/스킬 로드]
        │
        ▼
[데스크탑: AI 개발 수행 (sandbox)]
        │
        ▼
[데스크탑: 완료/실패]
        │
        ▼
[데스크탑: `report` → Cloud API 전송]
        │
        ▼
[웹: 실시간 대시보드 업데이트]
```

#### 클라우드 러너 흐름
```
[웹: 인게이지먼트 생성 + 조직 키 지정]
        │
        ▼
[웹: "실행" 버튼 클릭]
        │
        ▼
[Cloud API: Task → Redis 큐에 추가]
        │
        ▼
[Container Pool: 아이들 컨테이너 Task 획득]
        │
        ▼
[Container: 에이전트/스킬 로드]
        │
        ▼
[Container: AI 개발 수행]
        │
        ▼
[Container: 완료/실패]
        │
        ▼
[Container: 결과 → Cloud API 저장]
        │
        ▼
[웹: 실시간 대시보드 업데이트]
```

---

## 5. 통신 & 실행계약

### 5.1 통신 계층

```
웹 브라우저 ─────(HTTPS)────► Cloud API (FastAPI)
                                ├── Engagements CRUD
                                ├── Execution Tracking
                                └── Governance/Ops

데스크탑 러너 ─────(HTTPS)────► Cloud API
                                └── Task Status Report

클라우드 러너 ────(gRPC)──────► Cloud API
       (컨테이너)                └── Task Pull + Result Push
```

### 5.2 API 엔드포인트 요약

```
# 인증 (완료)
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me                    # organization_id/system_role 포함(CE-302)

# 조직 (CE-302)
POST /api/v1/organizations
GET  /api/v1/organizations/me
GET  /api/v1/organizations/{id}/members
PUT  /api/v1/organizations/{id}

# 딜리버리 콘솔 백엔드 (현재: projects API 재사용 + mock)
GET  /api/v1/projects                   # 인게이지먼트 목록 (딜리버리 콘솔 소스)
GET  /api/v1/projects/{id}              # 인게이지먼트 상세
POST /api/v1/projects/{id}/preview      # 산출물 프리뷰 (projects.py)
POST /api/v1/projects/draft/preview     # 드래프트 프리뷰
#  * 세션/팀상태/LLM원장/리뷰 데이터는 아직 mock(mock-mode-toggle) 기반;
#    전용 인게이지먼트/실행추적 엔드포인트는 로드맵(LoadMap_v3, 미구현)

# 러너 보고 (데스크탑/클라우드 공통)
POST /api/v1/runner/report              # 실행 결과 제출
  {
    "execution_id": "uuid",
    "status": "completed|failed",
    "result": {...},
    "logs": "..."
  }

# 거버넌스 (CE-303)
GET  /api/v1/governance/policy          # 커널 SSOT(define/rules/tiers)

# 운영 (Superadmin, CE-305)
GET  /api/v1/admin/ops/containers       # 실행중 컨테이너(read-only)
GET  /api/v1/admin/ops/ports            # 포트 프로브 결과(read-only)
GET  /api/v1/admin/ops/env              # 관리형 env(Fernet 암호화)
PUT  /api/v1/admin/ops/env/{key}        # env 수정
DELETE /api/v1/admin/ops/env/{key}      # env 삭제
POST /api/v1/admin/ops/env/render       # 명령 미리보기(docker 미실행)
GET  /api/v1/admin/ops/tables           # 화이트리스트 테이블 CRUD
POST /api/v1/admin/ops/tables
PUT  /api/v1/admin/ops/tables/{id}
DELETE /api/v1/admin/ops/tables/{id}
```

### 5.3 Task Protocol (Runner ↔ Cloud API)

```yaml
# 데스크탑 러너가 데스크탑 구독시트로 인게이지먼트 실행 후 결과 보고
POST /api/v1/runner/report
Content-Type: application/json

{
  "runner_type": "desktop",                    # "desktop" | "cloud"
  "execution_id": "exec-uuid-123",
  "status": "completed",                       # "completed" | "failed" | "timeout"
  "start_time": "2026-07-22T10:00:00Z",
  "end_time": "2026-07-22T10:05:30Z",
  "result": {
    "output": "Generated project files...",
    "files_created": ["/path/to/file1", "/path/to/file2"],
    "exit_code": 0
  },
  "logs": "Agent execution logs...",
  "error": null
}

# 클라우드 러너가 컨테이너에서 실행 후 결과 보고 (동일 스키마)
POST /api/v1/runner/report
{
  "runner_type": "cloud",
  "execution_id": "exec-uuid-456",
  "status": "completed",
  ...
}

# 웹 콘솔이 러너 풀에서 Task 풀링 (클라우드만)
GET /api/v1/runner/tasks/pull?runner_id=runner-abc&limit=5

Response:
{
  "tasks": [
    {
      "execution_id": "exec-uuid-1",
      "engagement_id": "eng-uuid-1",
      "payload": {...}
    }
  ]
}
```

---

## 6. 보안 고려사항

### 6.1 통신 보안
- **TLS**: 모든 통신은 HTTPS
- **인증**: Auth.js v5 + JWT (웹), API Key (클라우드 러너)
- **조직 격리**: 조직별 데이터 완전 격리

### 6.2 데이터 보안
- **로컬 API 키**: 데스크탑 .env에만 저장, 클라우드 미전송
- **조직 API 키**: 클라우드 러너 전용, HashiCorp Vault 또는 Fernet 암호화
- **런타임 격리**: 각 컨테이너는 독립 sandbox 환경
- **로그 격리**: 조직별 로그 접근 제어

### 6.3 라이센스 보안
- 1계정 1 데스크탑 구독 무료
- 추가 클라우드 러너 및 인게이지먼트는 유료 (Phase 2)
- API 키 기반 사용량 추적

---

## 7. 확장성 설계

### 7.1 수평 확장
- **Cloud**: FastAPI + Redis로 API 수평 확장 가능
- **컨테이너 풀**: 자동 스케일링으로 Task 처리량 증가

### 7.2 데이터 확장
- 인게이지먼트/실행 기록은 PostgreSQL 파티셔닝 가능
- Redis로 실시간 상태 캐싱

### 7.3 Phase 2 확장
- 사용자 커스텀 에이전트 업로드
- 에이전트 마켓플레이스
- 사용 통계 & 분석 대시보드
- SLA 기반 우선순위 큐
