# 24SevenClaw - Development Roadmap v3

> 클라우드 SaaS (관리/설정/모니터링) + 로컬 CLI (실행/개발) 기반 AI 소프트웨어 프로젝트 빌딩 플랫폼
> 웹 온보딩 → 프로젝트 자동 구성 → CLI로 로컬 환경 구축 → Claude Code와 개발 → 대시보드 모니터링
> 로드맵 기간: 2026-04-07 ~ 2026-05-11 (5주)

---

## 서비스 비전

- **구매자**: 클라우드 서비스에 회원가입 → 기업 정보 등록 → 프로젝트 유형 선택 → 요구사항 입력 → CLI로 로컬 개발
- **플랫폼 (웹)**: 요구사항 기반 에이전트/스킬/Hook 자동 구성 + 프로젝트 관리 + 진행 모니터링
- **플랫폼 (CLI)**: 웹에서 구성한 설정을 로컬에 자동 구축 + Claude Code 연동 + 진행 상태 보고
- **핵심 가치**: 비개발자도 웹에서 프로젝트를 설정하고, 로컬에서 Claude Code와 함께 AI 기반 개발을 할 수 있는 원스톱 플랫폼
- **비용 모델**: Claude 토큰 = 사용자 부담 (BYOK), 인프라 = 사용자 로컬 PC, 우리 = SaaS 운영비
- **라이센스**: 1계정 1프로젝트 무료, 다중 프로젝트는 유료 라이센스

---

## Tech Stack

- **Frontend**: Next.js 15 (App Router) + Tailwind + shadcn/ui + Zustand + TanStack Query
- **Backend**: FastAPI + SQLAlchemy 2.0 async + Alembic
- **CLI**: Node.js (TypeScript) — `@24sevenclaw/cli` npm 패키지
- **AI 엔진**: Claude Code CLI (사용자 BYOK — 자체 Anthropic API 키 사용)
- **Database**: PostgreSQL 16 + Redis 7 (Cloud)
- **Auth**: Auth.js v5 (JWT) + FastAPI JWT
- **Contract**: OpenAPI → @hey-api/openapi-ts 자동 생성
- **Infra**: Docker Compose (dev) → K8s (prod)
- **CI/CD**: GitHub Actions
- **Template Engine**: Jinja2 (프로젝트 스캐폴딩 템플릿)

---

## 서비스 플로우

```
[웹 — 클라우드]                              [로컬 — 사용자 PC]

[회원가입/로그인]
      │
      v
[온보딩 위저드]
      │
      ├── Step 1: 기업 정보 등록
      │     (기업명, 위치, 사업자번호, 업종 등)
      │
      ├── Step 2: 프로젝트 유형 선택
      │     (웹앱 / REST API / 모바일앱 / 데이터 파이프라인 / 커스텀)
      │
      ├── Step 3: 요구사항 입력
      │     (프로젝트 유형별 동적 폼 — JSON Schema 기반)
      │
      └── Step 4: 배포 방식 결정
            (서비스 배포 / 소스 관리만 / Linux / Windows)
      │
      v
[프로젝트 생성 — 웹]
      │
      ├── 에이전트/스킬/Hook 자동 구성 (요구사항 기반)
      ├── 마일스톤 자동 생성 (로드맵)
      ├── 프로비저닝 상태 추적 (pending → configuring → ready)
      └── CLI 설치 가이드 + 설정 토큰 발급
      │
      v                                      
[CLI 설치 안내] ─────────────────────→ [npx @24sevenclaw/cli init]
                                              │
                                              ├── 클라우드 인증 (토큰)
                                              ├── 프로젝트 설정 다운로드
                                              ├── 로컬 개발환경 자동 구축
                                              │     ├── 프로젝트 디렉토리 생성
                                              │     ├── Git 초기화
                                              │     ├── 의존성 설치
                                              │     ├── CLAUDE.md 생성
                                              │     └── Claude Code 연동 설정
                                              ├── Claude API 키 설정 (BYOK)
                                              └── Claude Code로 개발 시작
                                              │
      ┌───────────────────────────────────────┘
      │ CLI가 진행 상태 보고 (HTTPS)
      v
[프로젝트 대시보드 — 웹]
      │
      ├── 로드맵 타임라인 (마일스톤 진척도)
      ├── 이벤트 피드 (구조화된 프로젝트 이벤트)
      ├── CLI 연결 상태 표시
      ├── 에이전트/스킬 설정 관리 (수정 가능 → CLI sync)
      └── 프로젝트 설정 변경 시 CLI에 알림
```

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│  24SevenClaw Cloud (SaaS — 관리/설정/모니터링)            │
│                                                         │
│  [사용자 브라우저]                                        │
│       │                                                 │
│       v                                                 │
│  [Next.js Frontend] ←→ [Auth.js v5]                     │
│       │                                                 │
│       │ REST API + WebSocket                            │
│       v                                                 │
│  [FastAPI Backend] ←→ [PostgreSQL] + [Redis]            │
│       │                                                 │
│       ├── 기업(Organization) 관리 + 멤버십/역할           │
│       ├── 온보딩 위저드 엔진                              │
│       ├── 프로젝트 템플릿 + 자동 구성 엔진                 │
│       ├── 에이전트/스킬/MCP/Hook 레지스트리               │
│       ├── 마일스톤 + 이벤트 + 진척도 관리                  │
│       ├── CLI 설정 배포 API (프로젝트 설정 다운로드)       │
│       ├── 라이센스 관리 (user_plans + licenses)           │
│       ├── 대시보드 데이터 API                             │
│       └── Browser WebSocket (대시보드 실시간 업데이트)     │
│       │                                                 │
└───────┼─────────────────────────────────────────────────┘
        │ HTTPS (CLI → Cloud, 주기적 보고)
        v
┌─────────────────────────────────────────────────────────┐
│  사용자 로컬 PC (실행 플레인)                              │
│                                                         │
│  [@24sevenclaw/cli — npm 패키지]                         │
│       ├── 클라우드 인증 + 프로젝트 설정 다운로드            │
│       ├── 로컬 개발환경 자동 구축 (스캐폴딩)               │
│       │     ├── 프로젝트 구조 생성                        │
│       │     ├── CLAUDE.md + 에이전트 설정 파일 생성        │
│       │     ├── Git 초기화 + 의존성 설치                  │
│       │     └── Claude Code 연동 설정                    │
│       ├── Claude Code와 AI 개발 (사용자 API 키, BYOK)    │
│       ├── 진행 상태 → 클라우드 보고 (HTTPS)               │
│       └── 클라우드 설정 변경 동기화                        │
│                                                         │
│  ※ 코드, 빌드, 실행, Git 모두 로컬                       │
│  ※ Claude 토큰 비용 = 사용자 부담 (BYOK)                 │
│  ※ CLI 연동은 Week 3-4에서 기본 구현                      │
└─────────────────────────────────────────────────────────┘
```

---

## 설계 결정 사항 (ADR)

### ADR-1: 테넌트 모델 — 멤버십 테이블 포함
- `organization_members(org_id, user_id, role)` 테이블로 역할 기반 인가
- 모든 프로젝트 API는 org 멤버십 체크 필수
- Cross-org 접근 거부 테스트 필수

### ADR-2: 데이터 경계 — 이벤트만 저장
- Cloud는 `project_events` (구조화된 이벤트)만 저장
- 코드, 빌드 결과물, Git 데이터는 모두 사용자 로컬에만 존재
- CLI가 주기적으로 진행 상태 요약을 클라우드에 HTTPS로 보고
- architecture-overview.md의 "실행 로그 원본 저장하지 않음" 원칙 준수

### ADR-3: 라이센스 모델 — 하이브리드
- `user_plans` 테이블 신규 (유저 플랜 + 한도 관리)
- 기존 `licenses` 테이블 유지 (프로젝트별 라이센스 키)
- `agent_connections.license_id` FK 유지
- 회원가입 시 Free plan 자동 생성

### ADR-4: 복합 연산 안전성
- `projects.provisioning_status` enum: `pending → configuring → ready | failed`
- 프로젝트 생성 + 자동구성 + 마일스톤을 단일 DB 트랜잭션으로 처리
- 한도 체크 시 `SELECT FOR UPDATE`로 동시 요청 방지

### ADR-5: CLI 역할 — Phase 1 기본 구현
- Week 0-2: Cloud SaaS UI 구현
- Week 3: CLI 패키지 기본 구현 (init, 클라우드 인증, 설정 다운로드, 스캐폴딩)
- Week 4: CLI ↔ Cloud 연동 (진행 상태 보고, 설정 동기화)
- CLI는 npm 패키지 (`@24sevenclaw/cli`)로 배포, `npx`로 실행 가능
- Claude Code CLI를 AI 엔진으로 활용 (우리가 에이전트 로직 직접 구현 불필요)
- 사용자는 자체 Anthropic API 키 사용 (BYOK)

---

## 클라우드 DB 스키마

### 신규 테이블

| 테이블 | 설명 | 도입 시점 |
|--------|------|----------|
| `organizations` | 기업 정보 (이름, 사업자번호, 위치 등) | Week 0 |
| `organization_members` | 멤버십 (org_id, user_id, role) | Week 0 |
| `user_plans` | 유저 플랜 (plan, projects_limit, agents_limit) | Week 0 |
| `project_templates` | 프로젝트 유형 템플릿 | Week 1 |
| `project_milestones` | 프로젝트 마일스톤 (로드맵) | Week 3 |
| `project_events` | 프로젝트 이벤트 (구조화된 요약만) | Week 3 |

### 기존 테이블 (확장)

| 테이블 | 확장 필드 | 시점 |
|--------|----------|------|
| `users` | `organization_id` FK, `onboarding_completed` | Week 0 |
| `projects` | `organization_id` FK, `template_id` FK, `requirements`, `deployment_type`, `target_os`, `provisioning_status` | Week 0 |

### 기존 테이블 (변경/유지)

| 테이블 | 설명 | 상태 |
|--------|------|------|
| `licenses` | 프로젝트별 라이센스 키 (하이브리드 모델) | 유지 |
| `agents` | 에이전트 레지스트리 | 유지 |
| `skills` | 스킬 레지스트리 | 유지 |
| `mcp_servers` | MCP 레지스트리 | 유지 |
| `project_configs` | 프로젝트별 에이전트/스킬/MCP 설정 | 유지 (CLI가 다운로드) |
| `agent_connections` | ~~에이전트 연결 상태~~ → CLI 연결 상태로 용도 변경 | 변경 |
| `tickets` | 개발 티켓/이슈 | 유지 |
| `ticket_events` | 티켓 이벤트 | 유지 |

---

## Phase 0: 프로젝트 셋업 — ✅ 완료 (03-23 ~ 04-05)

- [x] 5개 레포 초기화 (web, api, agent, infra, contracts)
- [x] Docker Compose (PostgreSQL + Redis)
- [x] FastAPI 스켈레톤 + DB + Alembic + Users 마이그레이션
- [x] 인증 시스템 (회원가입/로그인/JWT)
- [x] Next.js 스켈레톤 + 인증 UI
- [x] CI/CD 파이프라인
- [x] DB 스키마 전체 + 마이그레이션
- [x] Projects CRUD (API + UI)
- [x] OpenAPI Contract 파이프라인
- [x] 환경 강화 (에러 핸들링, 로깅, Rate Limiting)
- [x] Agent 기본 데몬 + WebSocket 연결
- [x] E2E 통합 테스트

---

## Phase 1: Week 0 — 아키텍처 결정 + 기반 마이그레이션 (04-07 ~ 04-13)

### 목표
설계 문서 갱신 + 기반 DB 스키마 + 인가 미들웨어 + 하이브리드 라이센스 기반

### Docs

- [ ] `docs/architecture-overview.md` 갱신: 데이터 경계 재정의 (이벤트만 저장, 배포파일은 on-the-fly)
- [ ] `docs/license-model.md` 갱신: 하이브리드 모델 (user_plans + licenses) 반영
- [ ] `CLAUDE.md` 갱신: SaaS 중심 비전 반영
- [ ] `docs/onboarding-flow.md` 신규: 4단계 온보딩 위저드 상세 명세

### API — DB 마이그레이션 (3개 분리)

- [ ] Migration 003: `organizations` + `organization_members` 테이블
- [ ] Migration 004: `users` 확장 (`organization_id` nullable FK, `onboarding_completed`)
- [ ] Migration 005: `user_plans` 테이블 + `projects` 확장 (`organization_id`, `template_id`, `requirements`, `deployment_type`, `target_os`, `provisioning_status`)

### API — 모델/스키마

- [ ] `models/organization.py`: Organization + OrganizationMember 모델
- [ ] `models/user_plan.py`: UserPlan 모델
- [ ] `schemas/organization.py`: CRUD 스키마
- [ ] `schemas/user_plan.py`: 응답 스키마

### API — 인가 미들웨어

- [ ] `dependencies.py`: `get_current_org_member(db, user)` 의존성 추가
- [ ] `middleware/authorization.py`: org 멤버십 체크 + 역할 기반 권한 검증
- [ ] `services/project_service.py` 수정: org-scoped 쿼리 + 멤버십 체크
- [ ] `services/auth_service.py` 수정: 회원가입 시 `user_plans` (Free) 자동 생성

### Contracts

- [ ] Organization, OrganizationMember, UserPlan 타입 추가
- [ ] OpenAPI 재생성 + TypeScript 클라이언트 동기화

### Tests

- [ ] `test_organization_auth.py`: org 멤버십 인가 (cross-org 접근 거부 검증)
- [ ] `test_user_plans.py`: 회원가입 시 Free plan 생성 검증

---

## Phase 1: Week 1 — 기업 온보딩 위저드 (04-14 ~ 04-20)

### 목표
Organization CRUD + 온보딩 Step 1 (기업 정보 입력) + Step 2 (프로젝트 유형)

### API

- [ ] Organization CRUD: routes (`POST /organizations`, `GET /{id}`, `PATCH`, `DELETE`)
- [ ] Organization Members API: `POST /organizations/{id}/members/invite`, `GET /members`
- [ ] 온보딩 상태 API: `GET /onboarding/status`, `POST /onboarding/complete-step`
- [ ] `ProjectTemplate` 모델: name, category, default_agents/skills/hooks JSON, requirements_schema JSON Schema
- [ ] 초기 템플릿 시드 데이터 (웹앱, REST API, 모바일앱, 데이터 파이프라인, 커스텀)
- [ ] `GET /project-templates` API
- [ ] Migration 006 (필요시): `project_templates` 테이블
- [ ] 테스트: `test_organizations.py`, `test_onboarding.py`, `test_project_templates.py`

### Frontend

- [ ] `(onboarding)/` 라우트 그룹 + 레이아웃 (사이드바 없음, 중앙 카드)
- [ ] `setup/company/page.tsx` — Step 1: 기업 정보 폼 (React Hook Form + Zod)
- [ ] `setup/project-type/page.tsx` — Step 2: 프로젝트 유형 카드 그리드
- [ ] `components/onboarding/step-indicator.tsx` — 4단계 진행 표시기
- [ ] `components/onboarding/company-form.tsx` — 기업 정보 입력 폼
- [ ] `components/onboarding/project-type-selector.tsx` — 유형 선택 카드
- [ ] `hooks/use-organizations.ts` — TanStack Query hooks
- [ ] `stores/onboarding-store.ts` — 위저드 상태 관리 (Zustand)
- [ ] `middleware.ts` 수정 — 온보딩 미완료 시 리다이렉트 (JWT `onboarding_completed` 클레임)

### Contracts

- [ ] ProjectTemplate 타입 추가
- [ ] OpenAPI 재생성

---

## Phase 1: Week 2 — 프로젝트 생성 + 자동 구성 (04-21 ~ 04-27)

### 목표
온보딩 Step 3-4 + 프로젝트 자동 구성 엔진 + 에이전트/스킬 관리

### API

- [ ] Registry CRUD API: `GET /agents`, `GET /skills`, `GET /mcps`
- [ ] ProjectConfig CRUD API: `GET/POST/PATCH/DELETE /projects/{id}/configs`
- [ ] `AutoConfigService`: 요구사항 + 템플릿 → 에이전트/스킬/Hook 자동 매핑
  - 순수 정적 매핑 (template.default_agents/skills/hooks → project_configs)
  - 존재하지 않는 registry 아이템 참조 시 경고 로그 + 스킵
- [ ] 프로젝트 생성 플로우 통합 (단일 트랜잭션):
  1. `user_plans.projects_limit` 체크 (`SELECT FOR UPDATE`)
  2. `projects` 생성 (`provisioning_status = pending`)
  3. AutoConfig 실행 (`provisioning_status = configuring`)
  4. 완료 (`provisioning_status = ready`) 또는 실패 (`failed`)
- [ ] 테스트: `test_auto_config.py`, `test_project_configs.py`, `test_project_creation_flow.py`

### Frontend

- [ ] `setup/requirements/page.tsx` — Step 3: JSON Schema 기반 동적 폼
- [ ] `setup/deployment/page.tsx` — Step 4: 배포 방식/OS 선택
- [ ] `components/onboarding/requirements-form.tsx` — 동적 요구사항 폼
- [ ] `components/onboarding/deployment-selector.tsx` — 배포 방식/OS 선택
- [ ] `projects/[projectId]/agents/page.tsx` — 에이전트 관리 탭
- [ ] `projects/[projectId]/skills/page.tsx` — 스킬 관리 탭
- [ ] `components/projects/agent-config-panel.tsx` — 에이전트 설정 패널
- [ ] `components/projects/skill-config-panel.tsx` — 스킬 설정 패널
- [ ] 대시보드 사이드바에 프로젝트 하위 네비게이션 추가

### Contracts

- [ ] Registry, ProjectConfig 관련 타입 추가
- [ ] OpenAPI 재생성

---

## Phase 1: Week 3 — 대시보드 + CLI 패키지 기본 구현 (04-28 ~ 05-04)

### 목표
프로젝트 대시보드 + CLI 패키지 MVP + 프로젝트 설정 배포 API

### API

- [ ] Migration 007: `project_milestones` + `project_events` 테이블
- [ ] 마일스톤 자동 생성 서비스 (템플릿/요구사항 기반)
- [ ] Milestones API: `GET /projects/{id}/milestones`, `PATCH /{milestone_id}`
- [ ] ProjectEvents API: `GET /projects/{id}/events` (페이지네이션, 필터)
- [ ] CLI 설정 배포 API:
  - `POST /projects/{id}/cli-tokens` — CLI 인증 토큰 발급
  - `GET /projects/{id}/config/download` — 프로젝트 설정 JSON 다운로드 (에이전트/스킬/Hook 구성 포함)
  - `POST /projects/{id}/events` — CLI가 진행 상태 보고
- [ ] 테스트: `test_milestones.py`, `test_project_events.py`, `test_cli_config.py`

### CLI (`@24sevenclaw/cli` npm 패키지)

- [ ] 패키지 초기화 (TypeScript, Commander.js)
- [ ] `24sc init` — 클라우드 인증 (토큰 입력) + 프로젝트 설정 다운로드
- [ ] `24sc setup` — 로컬 개발환경 스캐폴딩
  - 프로젝트 디렉토리 생성
  - Git 초기화
  - 의존성 설치 (package.json / requirements.txt 등)
  - CLAUDE.md 자동 생성 (프로젝트 설정 기반)
  - Claude Code 연동 설정 (.claude/ 디렉토리)
- [ ] `24sc auth` — Anthropic API 키 설정 (BYOK) 가이드
- [ ] 테스트: CLI 단위 테스트

### Frontend

- [ ] `projects/[projectId]/dashboard/page.tsx` — 메인 대시보드
- [ ] `components/dashboard/roadmap-view.tsx` — 세로 타임라인 마일스톤 뷰
- [ ] `components/dashboard/progress-card.tsx` — 진척도 요약 카드
- [ ] `components/dashboard/event-feed.tsx` — 이벤트 피드 (project_events 기반)
- [ ] `components/dashboard/cli-status.tsx` — CLI 연결 상태 표시
- [ ] `projects/[projectId]/cli-setup/page.tsx` — CLI 설치 가이드 + 토큰 발급
- [ ] `hooks/use-milestones.ts`, `use-project-events.ts`

---

## Phase 1: Week 4 — CLI 연동 강화 + 폴리싱 + E2E (05-05 ~ 05-11)

### 목표
CLI ↔ Cloud 실시간 연동 + 라이센스 UI + 전체 폴리싱 + E2E 테스트

### API

- [ ] CLI 상태 보고 API 완성:
  - `POST /projects/{id}/events` — CLI가 진행 이벤트 보고 (마일스톤 진척, 파일 변경 등)
  - Browser WebSocket: `GET /ws/project/{id}/stream` (JWT 인증, 대시보드 실시간 업데이트)
- [ ] Redis Pub/Sub 브릿지: CLI 보고 → Redis channel(`project:{id}:events`) → Browser WebSocket
- [ ] CLI 설정 동기화 API: `GET /projects/{id}/config/version` (변경 감지)
- [ ] Licenses API: `GET /me/plan`, `GET /me/usage`
- [ ] 테스트: `test_cli_integration.py`, `test_license_enforcement.py`, `test_full_onboarding_flow.py`

### CLI

- [ ] `24sc dev` — Claude Code 연동 개발 모드 시작 (claude 프로세스 실행)
- [ ] `24sc status` — 진행 상태 클라우드 보고
- [ ] `24sc sync` — 클라우드 설정 변경사항 로컬 동기화
- [ ] CLI 훅: Claude Code 작업 완료 시 자동 상태 보고

### Frontend

- [ ] `components/dashboard/event-timeline.tsx` — CLI 보고 이벤트 실시간 타임라인
- [ ] `hooks/use-project-websocket.ts` — 프로젝트 WebSocket 연결 훅
- [ ] `settings/license/page.tsx` — 플랜 정보 + 사용량
- [ ] `components/license/plan-card.tsx` — 플랜 비교 카드 (Free/Pro/Enterprise)
- [ ] `components/license/usage-meter.tsx` — 사용량 시각화 바
- [ ] `overview/page.tsx` — 로그인 후 랜딩 (기업 정보, 프로젝트 요약, 플랜 상태)
- [ ] 전체 UI 폴리싱: 로딩 스켈레톤, 빈 상태, 토스트 메시지, 밸리데이션
- [ ] 공통 컴포넌트: `empty-state.tsx`, `loading-skeleton.tsx`

### Docs

- [ ] `docs/architecture-overview.md` 최종 갱신 (멤버십 모델, 이벤트 모델 반영)
- [ ] `docs/agent-protocol.md` → CLI ↔ Cloud 통신 프로토콜로 재작성
- [ ] `CLAUDE.md` 아키텍처 다이어그램 갱신 (CLI 모델 반영)

---

## 핵심 원칙

1. **기존 코드 보존**: 모든 신규 필드는 nullable로 추가하여 하위 호환 유지
2. **패턴 유지**: models → schemas → services → routes 레이어 패턴 동일하게 적용
3. **contracts 우선**: API 변경 시 반드시 contracts 레포 먼저 업데이트
4. **자동 구성은 단순하게**: 템플릿 → 사전 정의 매핑으로 시작, AI 기반 파싱은 후속
5. **Stripe 연동 후속**: 라이센스 UI만 구현, 결제는 "Coming soon" 처리
6. **마이그레이션 분리**: 대규모 단일 마이그레이션 금지, 테이블/기능 단위로 분리
7. **데이터 경계 준수**: Cloud는 이벤트/메타데이터만, 코드/빌드/로그는 사용자 로컬
8. **인가 필수**: 모든 프로젝트 API에 org 멤버십 체크 포함

---

## 라이센스 정책

| 플랜 | 프로젝트 | 에이전트/프로젝트 | 가격 |
|------|---------|-----------------|------|
| Free | 1개 | 3개 | 무료 |
| Pro | 5개 | 10개 | TBD |
| Enterprise | 무제한 | 무제한 | TBD |

### 하이브리드 모델
- **user_plans**: 유저별 플랜 + 한도 관리 (프로젝트 수, 에이전트 수)
- **licenses**: 프로젝트별 라이센스 키 (Agent 등록/인증용)
- 회원가입 시 Free plan 자동 생성
- 프로젝트 생성 시 user_plans.projects_limit 체크

---

## 계획 변경 이력

| 변경일 | 변경 내용 | 사유 |
|--------|----------|------|
| 2026-03-31 | 서비스 피벗: 고객 서버 에이전트 중심 → 클라우드 SaaS 중심 | paperclip.ing 참고, 서비스 방향 전환 |
| 2026-03-31 | PjPlan.md → docs/archive/PjPlan_v1.md 백업, LoadMap.md 생성 | 신규 로드맵 수립 |
| 2026-04-01 | LoadMap v2: 4주 → 5주 확장, 설계 갭 보완 | Codex adversarial review 기반 재설계 |
| 2026-04-01 | ADR 5개 추가 (테넌트, 데이터 경계, 라이센스, 트랜잭션, Agent) | 아키텍처 결정 문서화 |
| 2026-04-01 | project_logs → project_events 변경 | architecture-overview.md 일관성 유지 |
| 2026-04-01 | user_plans 테이블 신규 + licenses 유지 (하이브리드) | 기존 agent_connections 호환성 |
| 2026-04-01 | organization_members 테이블 추가 | cross-tenant 접근 방지 |
| 2026-04-02 | 아키텍처 재설계: Agent 데몬 → CLI 패키지 | 비개발자 대상 서비스, 비용 구조 현실화 (BYOK + 로컬 실행) |
| 2026-04-02 | 실행 플레인 변경: 고객 서버 → 사용자 로컬 PC | 브라우저만으로 로컬 설치 불가 → CLI 패키지로 브릿지 |
| 2026-04-02 | v2 → v3: 배포 파일 생성 → CLI 로컬 스캐폴딩으로 변경 | 실제 개발 환경 구축이 핵심 가치 |

---

## 참조 문서

- `docs/archive/PjPlan_v1.md` — 이전 프로젝트 계획 v1 (백업)
- `docs/architecture-overview.md` — 아키텍처 상세 설계
- `docs/agent-protocol.md` — CLI ↔ Cloud 통신 프로토콜
- `docs/comparison.md` — 유사 플랫폼 비교 분석
- `docs/license-model.md` — 라이센스 정책
- `docs/onboarding-flow.md` — 온보딩 위저드 상세 (신규)


이 프로젝트를 LoadMap.md를 분석해서 어떤 방식으로 해당 서비스가 실행되는지 구조를 알려줘.                                                                                               
그리고 해당 프로젝트를 완성하기 위해 내 구축 설계 방식을 하네스 엔지니어링을 도입할꺼야. 구체적으로 하네스 엔지니어링을 설계하기 위한 가이드 플랜을 줘.                                                                                                                                                                                                                         
하네스 엔지니어링을 위한 4단계 과정이 있는데 아래를 참고해. 