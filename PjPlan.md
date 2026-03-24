# 24SevenClaw - Project Plan

> 라이센스 기반 AI 에이전트 개발 오케스트레이션 플랫폼
> 클라우드(컨트롤 플레인) + 고객 서버(실행 플레인) 아키텍처
> 시작일: 2026-03-23

---

## 비즈니스 모델

- **우리**: 클라우드 웹서비스(SaaS) + 라이센스 제공
- **고객**: 자사 서버에서 실행, 모든 데이터는 고객 소유
- **라이센스**: 프로젝트 단위 (에이전트/스킬 포함, 세부 정책은 추후)
- **핵심 가치**: 클라우드 UI로 고객 서버의 개발 환경 원격 구성 + 개발 프로세스 오케스트레이션

---

## Tech Stack

- **Frontend**: Next.js 15 (App Router) + Tailwind + shadcn/ui + Zustand + TanStack Query
- **Backend (Cloud)**: FastAPI + SQLAlchemy 2.0 async + Alembic
- **Backend (Agent)**: FastAPI (경량) 또는 Python 데몬
- **Database (Cloud)**: PostgreSQL 16 + Redis 7
- **Database (고객 서버)**: SQLite 또는 PostgreSQL (Agent 로컬)
- **통신**: WebSocket (Agent → Cloud 아웃바운드 연결)
- **Auth**: Auth.js v5 (JWT) + FastAPI JWT
- **Contract**: OpenAPI → @hey-api/openapi-ts 자동 생성
- **Infra**: Docker Compose (dev) → K8s (prod)
- **CI/CD**: GitHub Actions

---

## Repository Structure

| Repo | 역할 | 실행 위치 |
|------|------|-----------|
| `24SevenClaw-web` | 클라우드 프론트엔드 | 클라우드 |
| `24SevenClaw-api` | 클라우드 백엔드 (오케스트레이션) | 클라우드 |
| `24SevenClaw-agent` | 고객 서버 에이전트 데몬 | 고객 서버 |
| `24SevenClaw-infra` | Docker, CI/CD, 배포 설정 | 양쪽 |
| `24SevenClaw-contracts` | 클라우드↔에이전트 통신 프로토콜 + OpenAPI | 공유 |

---

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│  24SevenClaw Cloud (컨트롤 플레인)                        │
│                                                         │
│  [사용자 브라우저]                                        │
│       │                                                 │
│       v                                                 │
│  [Next.js Frontend] ←→ [Auth.js v5]                     │
│       │                                                 │
│       │ REST API                                        │
│       v                                                 │
│  [FastAPI Backend] ←→ [PostgreSQL] + [Redis]            │
│       │                                                 │
│       ├── 에이전트/스킬/MCP 레지스트리 (우리 IP)           │
│       ├── 라이센스 관리                                   │
│       ├── 프로젝트 메타데이터                              │
│       └── 티켓/이슈 발행                                  │
│       │                                                 │
└───────┼─────────────────────────────────────────────────┘
        │ WebSocket (Agent → Cloud 아웃바운드)
        │ 방화벽 친화적: 고객 에이전트가 클라우드로 연결
        v
┌─────────────────────────────────────────────────────────┐
│  고객사 서버 (실행 플레인)                                 │
│                                                         │
│  [24SevenClaw Agent 데몬]                                │
│       │                                                 │
│       ├── Docker 환경 생성/관리                            │
│       ├── Claude 인스턴스 관리                             │
│       ├── Git 저장소 관리                                  │
│       ├── 빌드/실행 관리                                   │
│       └── 상태 보고 → 클라우드                             │
│                                                         │
│  [Docker Container A] [Docker Container B] ...           │
│    ├── 에이전트 런타임      ├── 에이전트 런타임             │
│    ├── 스킬 서버           ├── 스킬 서버                  │
│    ├── MCP 서버            ├── MCP 서버                   │
│    └── Claude              └── Claude                    │
│                                                         │
│  ※ 모든 코드, 데이터, 빌드 결과물은 이 서버에 저장          │
└─────────────────────────────────────────────────────────┘
```

---

## 클라우드 DB (우리가 저장하는 것)

| 테이블 | 설명 |
|--------|------|
| `users` | 고객 계정 (로그인용) |
| `licenses` | 프로젝트별 라이센스 |
| `projects` | 프로젝트 메타데이터 (이름, 설정 참조) |
| `agents` | 에이전트 레지스트리 (우리 IP) |
| `skills` | 스킬 레지스트리 (우리 IP) |
| `mcp_servers` | MCP 레지스트리 (우리 IP) |
| `project_configs` | 프로젝트별 에이전트/스킬/MCP 설정 |
| `agent_connections` | 고객 에이전트 연결 상태 |
| `tickets` | 개발 티켓/이슈 |
| `ticket_events` | 티켓 진행 상태 이벤트 |

**저장하지 않는 것**: 고객 코드, 빌드 결과물, 실행 로그 원본, Git 데이터

---

## Phase별 개발 계획

### Phase 0: 프로젝트 셋업 (Week 1-2)
- [ ] 5개 레포 초기화 (web, api, agent, infra, contracts)
- [ ] Docker Compose (클라우드: PostgreSQL + Redis)
- [ ] FastAPI 스켈레톤 + DB 연결
- [ ] 인증 시스템 (회원가입/로그인/JWT)
- [ ] Next.js 스켈레톤 + 인증 UI
- [ ] CI/CD 파이프라인
- [ ] Projects CRUD (API + UI)
- [ ] OpenAPI Contract 파이프라인
- [ ] 환경 강화 (에러 핸들링, 로깅, Rate Limiting)

### Phase 1: MVP Core + Agent 기본 통신 (Week 3-5)
- [ ] 에이전트/스킬/MCP 레지스트리 연동 (외부 MCP)
- [ ] 레지스트리 브라우저 UI
- [ ] 프로젝트 설정 UI (JSON Schema 기반 동적 설정)
- [ ] **Agent 데몬 기본 구조 구현**
- [ ] **Agent ↔ Cloud WebSocket 통신 프로토콜**
- [ ] **Agent 등록/인증 흐름**
- [ ] 대시보드 셸 + 에이전트 연결 상태 표시

### Phase 2: Agent - Docker 프로비저닝 + 환경 셋업 (Week 6-9)
- [ ] Agent: Docker 컨테이너 생성/삭제/관리
- [ ] Agent: 환경 템플릿 시스템 (프로젝트 설정 → Docker 구성)
- [ ] Agent: 선택된 에이전트/스킬/MCP 자동 설치
- [ ] Agent: Claude 인스턴스 설치 + 구성
- [ ] Agent: Git 저장소 초기화
- [ ] 클라우드 UI: 환경 셋업 마법사 + 실시간 진행 표시
- [ ] 클라우드 UI: 고객 서버 환경 상태 모니터링

### Phase 3: 티켓/이슈 시스템 + Claude 연동 (Week 10-13)
- [ ] 클라우드: 티켓/이슈 발행 시스템
- [ ] 클라우드 → Agent: 티켓 전달 프로토콜
- [ ] Agent → Claude: 작업 지시 연동
- [ ] Claude → Agent: 작업 결과 수집
- [ ] Agent → 클라우드: 진행 상황 실시간 보고
- [ ] 클라우드 UI: 실시간 개발 진행 모니터링 대시보드
- [ ] Agent: 코드 → Git 자동 커밋/푸시

### Phase 4: 파이프라인 자동화 + 빌드/실행 (Week 14-16)
- [ ] 파이프라인 정의 스키마 (DAG)
- [ ] 비주얼 파이프라인 빌더 UI
- [ ] Agent: 파이프라인 실행 엔진
- [ ] Agent: 빌드 실행 + 로그 스트리밍
- [ ] 트리거 시스템 (수동, 스케줄, 웹훅, git push)
- [ ] 클라우드 UI: 빌드/실행 결과 모니터링

### Phase 5: 라이센스 + 상용화 (Week 17-20)
- [ ] 라이센스 관리 시스템 (프로젝트 단위)
- [ ] Stripe 결제 연동
- [ ] Agent 설치 스크립트 자동화 (원클릭)
- [ ] 관리자 대시보드
- [ ] 랜딩 페이지 + 문서화
- [ ] 성능 최적화 + 보안 감사
- [ ] 모니터링 (Sentry/Grafana)
- [ ] 프로덕션 배포 설정

---

## 일자별 개발 계획 (2026-03-23 ~ 2026-04-30)

> 1인 개발 기준. 계획 변경 시 수정일을 기록한다.
> ✅ 완료 | 🔄 진행중 | ⏳ 예정 | ❌ 변경/취소

### Phase 0: 프로젝트 셋업 (03-23 ~ 04-05)

| 일자 | 작업 내용 | 모듈 | 상태 |
|------|----------|------|------|
| **03-23 (일)** | Day 1: 5개 레포 초기화, 디렉토리 구조, 의존성, .gitignore | all | ✅ |
| **03-24 (월)** | Day 2: FastAPI 스켈레톤 완성 + DB 연결 + health 엔드포인트 + Alembic users 마이그레이션 | api, infra | ✅ |
| **03-25 (화)** | Day 3: 인증 백엔드 (bcrypt, JWT, auth 엔드포인트 4개, get_current_user, test_auth) | api | ⏳ |
| **03-26 (수)** | Day 4: Next.js 인증 UI (Auth.js v5, shadcn 컴포넌트, 로그인/회원가입, 대시보드 레이아웃) | web | ⏳ |
| **03-27 (목)** | Day 5: CI/CD 파이프라인 (API/Web/Agent/Contracts CI, 브랜치 보호) | infra | ⏳ |
| **03-28 (금)** | Day 6: DB 스키마 전체 (licenses, projects, agent_connections 등) + Alembic 마이그레이션 | api | ⏳ |
| **03-29 (토)** | Day 7: Projects CRUD (API 서비스 + 라우터 + 테스트) | api | ⏳ |
| **03-30 (일)** | Day 8: OpenAPI Contract 파이프라인 (스펙 생성 → TS 클라이언트 자동 생성) | contracts, api | ⏳ |
| **03-31 (월)** | Day 9: 프로젝트 목록/생성 UI (TanStack Query + Zustand + use-projects 훅) | web | ⏳ |
| **04-01 (화)** | Day 10: 환경 강화 (에러 핸들링 미들웨어, 구조화 로깅, Rate Limiting) | api | ⏳ |
| **04-02 (수)** | Day 11: Agent 기본 데몬 구조 (main, config, connection, dispatcher) | agent | ⏳ |
| **04-03 (목)** | Day 12: Agent → Cloud WebSocket 연결 + 재연결 전략 + heartbeat | agent, api | ⏳ |
| **04-04 (금)** | Day 13: E2E 통합 테스트 (Docker Compose up → API → Web → Agent 연결) | all | ⏳ |
| **04-05 (토)** | Day 14: Phase 0 마무리 — README 완성, .env.example, v0.1.0-phase0 태깅 | all | ⏳ |

### Phase 1: MVP Core + Agent 기본 통신 (04-06 ~ 04-19)

| 일자 | 작업 내용 | 모듈 | 상태 |
|------|----------|------|------|
| **04-06 (일)** | Day 15: 에이전트 레지스트리 모델 + CRUD API | api | ⏳ |
| **04-07 (월)** | Day 16: 스킬/MCP 레지스트리 모델 + CRUD API | api | ⏳ |
| **04-08 (화)** | Day 17: 레지스트리 브라우저 UI (목록, 검색, 상세) | web | ⏳ |
| **04-09 (수)** | Day 18: 프로젝트 설정 UI (JSON Schema 기반 동적 폼) — 에이전트/스킬/MCP 선택 | web | ⏳ |
| **04-10 (목)** | Day 19: project_configs API + 프로젝트↔레지스트리 연결 로직 | api | ⏳ |
| **04-11 (금)** | Day 20: Agent 등록/인증 흐름 (라이센스 키 검증 → 토큰 발급) | agent, api | ⏳ |
| **04-12 (토)** | Day 21: WebSocket Hub 구현 (Agent 연결 관리, Redis Pub/Sub) | api | ⏳ |
| **04-13 (일)** | Day 22: Agent 메시지 디스패처 + 핸들러 인터페이스 | agent | ⏳ |
| **04-14 (월)** | Day 23: Cloud → Agent 명령 전송 (command.setup_env, config.update) | api, agent | ⏳ |
| **04-15 (화)** | Day 24: Agent 상태 보고 (heartbeat, status, result) → Cloud 수신 처리 | agent, api | ⏳ |
| **04-16 (수)** | Day 25: 대시보드 셸 — 에이전트 연결 상태 실시간 표시 (WebSocket → UI) | web | ⏳ |
| **04-17 (목)** | Day 26: Contracts 동기화 — TS ↔ Python 타입 검증 + 자동화 스크립트 | contracts | ⏳ |
| **04-18 (금)** | Day 27: Phase 1 통합 테스트 + 버그 수정 | all | ⏳ |
| **04-19 (토)** | Day 28: Phase 1 마무리 — 문서 업데이트, v0.2.0-phase1 태깅 | all | ⏳ |

### Phase 2 시작: Agent Docker 프로비저닝 (04-20 ~ 04-30)

| 일자 | 작업 내용 | 모듈 | 상태 |
|------|----------|------|------|
| **04-20 (일)** | Day 29: docker_handler 구현 (컨테이너 생성/시작/중지/삭제) | agent | ⏳ |
| **04-21 (월)** | Day 30: 환경 템플릿 시스템 (프로젝트 설정 → Docker Compose 생성) | agent | ⏳ |
| **04-22 (화)** | Day 31: env_handler (에이전트/스킬/MCP 자동 설치 파이프라인) | agent | ⏳ |
| **04-23 (수)** | Day 32: claude_handler (Claude 인스턴스 설치 + 구성) | agent | ⏳ |
| **04-24 (목)** | Day 33: git_handler (Git 저장소 초기화 + 기본 워크플로) | agent | ⏳ |
| **04-25 (금)** | Day 34: 클라우드 UI — 환경 셋업 마법사 (단계별 위자드) | web | ⏳ |
| **04-26 (토)** | Day 35: 클라우드 UI — 셋업 실시간 진행 표시 (WebSocket 스트리밍) | web | ⏳ |
| **04-27 (일)** | Day 36: 클라우드 UI — 고객 서버 환경 상태 모니터링 대시보드 | web | ⏳ |
| **04-28 (월)** | Day 37: Agent 핸들러 통합 테스트 (Docker 환경 프로비저닝 E2E) | agent | ⏳ |
| **04-29 (화)** | Day 38: 버그 수정 + 엣지 케이스 처리 | all | ⏳ |
| **04-30 (수)** | Day 39: 4월 마무리 — Phase 2 중간 점검, 문서 업데이트, 회고 | all | ⏳ |

> Phase 2 나머지 + Phase 3~5는 5월 이후 계획에서 상세화

---

## 계획 변경 이력

| 변경일 | 변경 내용 | 사유 |
|--------|----------|------|
| 2026-03-24 | 일자별 계획 최초 작성 (03-23 ~ 04-30) | fix_plan 요청: 일자별 순차 플랜 |

---

## 참조 문서
- `docs/architecture-overview.md` — 컨트롤 플레인/실행 플레인 상세 설계
- `docs/agent-protocol.md` — Agent ↔ Cloud 통신 프로토콜
- `docs/comparison.md` — GitHub Actions Runner / Ansible Tower 비교 분석
- `docs/license-model.md` — 라이센스 정책
