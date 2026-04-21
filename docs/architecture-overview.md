# ClickEye - Architecture Overview

## 1. 시스템 개요

ClickEye는 **웹 SaaS (위저드 UI + 카탈로그 + ZIP 생성) + 로컬 Agent 플랫폼 (AI 개발)** 분리 아키텍처를 채택한 AI 개발 자동화 솔루션 빌더 플랫폼이다.

- **웹 SaaS (Cloud)**: 회원가입 → 7-Step 위저드로 솔루션 설계 → 프리뷰 → ZIP 다운로드
- **로컬 (사용자 PC)**: ZIP 해제 → Agent 플랫폼(Claude Code/Gemini CLI/Cursor 등) 실행 → AI 개발
- **CLI (파워유저)**: `npx @clickeye/cli init`으로 동일한 설정 파일 생성 가능

비개발자도 브라우저에서 솔루션을 설계하고, ZIP 하나로 AI 개발 환경을 즉시 구축할 수 있다.

### 유사 서비스 비교
- **Vercel**: 웹에서 프로젝트 설정 → CLI로 배포
- **Firebase**: 콘솔에서 구성 → CLI로 개발/배포
- **우리**: 웹에서 솔루션 설계 + AI 에이전트 구성 → ZIP 다운로드 → 로컬 AI 개발

---

## 2. 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│  ClickEye Cloud (SaaS — 위저드 + ZIP 생성)            │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐                    │
│  │ Next.js     │◄──►│ FastAPI      │                    │
│  │ Frontend    │    │ Backend      │                    │
│  │             │    │              │                    │
│  │ - 랜딩     │    │ - REST API   │                    │
│  │ - 인증     │    │ - 카탈로그   │                    │
│  │ - 위저드   │    │ - 프리뷰     │                    │
│  │ - 프리뷰   │    │ - ZIP 생성   │                    │
│  │ - 대시보드 │    │ - 추천 엔진  │                    │
│  └─────────────┘    └──────┬───────┘                    │
│                            │                            │
│               ┌────────────┴────────────┐               │
│               │                         │               │
│        ┌──────┴──────┐          ┌───────┴──────┐        │
│        │ PostgreSQL  │          │ Redis        │        │
│        │             │          │              │        │
│        │ - 사용자    │          │ - 세션 캐시  │        │
│        │ - 조직 정보 │          │ - 카탈로그   │        │
│        │ - 프로젝트  │          │   캐시       │        │
│        │ - 프로젝트  │          └──────────────┘        │
│        │   설정(JSONB)│                                  │
│        │ - 라이센스  │                                  │
│        └─────────────┘                                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ ZIP 다운로드 (HTTPS)
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 사용자 A PC  │ │ 사용자 B PC  │ │ 사용자 C PC  │
│              │ │              │ │              │
│ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │
│ │ unzip    │ │ │ │ unzip    │ │ │ │ unzip    │ │
│ │ project  │ │ │ │ project  │ │ │ │ project  │ │
│ └────┬─────┘ │ │ └────┬─────┘ │ │ └────┬─────┘ │
│      │       │ │      │       │ │      │       │
│      ▼       │ │      ▼       │ │      ▼       │
│ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │
│ │프로젝트  │ │ │ │프로젝트  │ │ │ │프로젝트  │ │
│ │디렉토리  │ │ │ │디렉토리  │ │ │ │디렉토리  │ │
│ │          │ │ │ │          │ │ │ │          │ │
│ │ CLAUDE.md│ │ │ │ .gemini/ │ │ │ │.cursor/  │ │
│ │ .claude/ │ │ │ │ agents/  │ │ │ │ rules/   │ │
│ │ .env     │ │ │ │ .env     │ │ │ │ .env     │ │
│ └──────────┘ │ │ └──────────┘ │ │ └──────────┘ │
│      │       │ │      │       │ │      │       │
│      ▼       │ │      ▼       │ │      ▼       │
│ ┌──────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │
│ │Claude    │ │ │ │Gemini    │ │ │ │Cursor    │ │
│ │Code      │ │ │ │CLI       │ │ │ │IDE       │ │
│ │(BYOK)    │ │ │ │(BYOK)    │ │ │ │(BYOK)    │ │
│ └──────────┘ │ │ └──────────┘ │ │ └──────────┘ │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## 3. 웹 SaaS (Cloud) 상세

### 3.1 역할과 책임

| 역할 | 설명 |
|------|------|
| **사용자 인증** | 계정 관리, 로그인, JWT 토큰 |
| **7-Step 위저드** | 회사 정보 → 솔루션 정의 → 에이전트 채용 → 스킬 장착 → 파이프라인 → 플랫폼 선택 → 프리뷰 |
| **카탈로그 관리** | 에이전트/스킬/플랫폼/파이프라인 카탈로그 (JSON 기반) |
| **추천 엔진** | 솔루션 유형 기반 에이전트/스킬/파이프라인 자동 추천 |
| **프리뷰 생성** | 위저드 설정 → 파일 트리 + 내용 미리보기 |
| **ZIP 생성** | 위저드 설정 + API 키(.env) → ZIP 스트리밍 다운로드 |
| **프로젝트 관리** | 프로젝트 메타데이터 + 위저드 설정(JSONB) 저장 |
| **라이센스 관리** | 플랜 관리, 프로젝트 한도 (Phase 2) |

### 3.2 저장하는 데이터

```yaml
저장함:
  - 사용자 계정 (email, password_hash)
  - 조직 정보 (company_name, size, industry, tech_stack)
  - 프로젝트 메타데이터 (이름, 유형, 설정)
  - 위저드 설정 (JSONB: agents, skills, pipelines, platform)
  - 라이센스/플랜 정보

저장하지 않음:
  - 사용자의 API 키 (Notion, Linear, Slack 등 — .env로 ZIP에만 포함)
  - 사용자 소스 코드
  - 사용자의 Claude/Gemini API 키
  - 사용자의 비즈니스 데이터
```

### 3.3 컴포넌트 구조

```
clickeye-web (Next.js 15)
├── 랜딩 페이지                     (완료)
├── 인증 (로그인/회원가입)            (완료)
├── 대시보드
│   ├── 프로젝트 목록/생성            (완료)
│   └── 프로젝트 상세/설정            (완료)
├── 7-Step 위저드 (/projects/new)    (LoadMap_v3)
│   ├── Step 1: 회사 정보
│   ├── Step 2: 솔루션 정의
│   ├── Step 3: 에이전트 채용
│   ├── Step 4: 스킬 장착 (API 키 입력)
│   ├── Step 5: 자동화 파이프라인
│   ├── Step 6: Agent 플랫폼 선택
│   └── Step 7: 프리뷰 + ZIP 다운로드
└── 레지스트리 브라우저               (기본 구조)

clickeye-api (FastAPI)
├── REST API
│   ├── 인증 (회원가입/로그인/JWT)     (완료)
│   ├── Organizations CRUD            (LoadMap_v3)
│   ├── Projects CRUD                 (완료)
│   ├── ProjectConfig (위저드 설정)    (LoadMap_v3)
│   ├── 카탈로그 API (agents/skills/platforms/pipelines) (LoadMap_v3)
│   ├── 프리뷰 API (파일 트리 + 내용) (LoadMap_v3)
│   ├── ZIP 생성 API (스트리밍)        (LoadMap_v3)
│   └── 추천 API (규칙 기반)          (LoadMap_v3)
└── 생성 엔진 (CLI에서 이식)           (LoadMap_v3)
```

---

## 4. 로컬 (사용자 PC) 상세

### 4.1 역할과 책임

| 역할 | 설명 |
|------|------|
| **ZIP 해제** | 다운로드된 ZIP을 로컬에 해제 |
| **Agent 플랫폼 실행** | Claude Code / Gemini CLI / Cursor 등 실행 |
| **AI 개발** | Agent가 생성된 설정(에이전트/스킬/파이프라인)에 따라 개발 수행 |
| **BYOK** | 사용자 자신의 AI API 키 사용 |

### 4.2 ZIP 구조 (플랫폼별)

```
# Claude Code 선택 시
my-project/
├── CLAUDE.md              # 프로젝트 가이드
├── .claude/
│   ├── agents/            # 에이전트 .md 파일들
│   ├── skills/            # 스킬 .md 파일들
│   └── settings.json      # Claude Code 설정
├── .env                   # API 키 (유저 입력값)
├── .env.example           # API 키 템플릿 (값 제외)
└── scripts/               # 하네스 Gate 등 Hook 스크립트

# Gemini CLI 선택 시
my-project/
├── .gemini/
│   ├── agents/
│   └── settings.json
├── .env
└── .env.example

# Cursor 선택 시
my-project/
├── .cursor/
│   └── rules/             # 에이전트 룰 파일들
├── .cursorrules            # Cursor 설정
├── .env
└── .env.example
```

### 4.3 데이터 흐름

```
[웹에서 7-Step 위저드 완료]
        │
        ▼
[ZIP 다운로드] → project-name.zip
        │
        ▼
[unzip project-name.zip]
        │
        ▼
[cd project-name]
        │
        ▼
[Agent 플랫폼 실행]
  ├── claude          (Claude Code)
  ├── gemini          (Gemini CLI)
  └── Open in Cursor  (Cursor IDE)
        │
        ▼
[AI가 설정에 따라 개발 시작]
  ├── 에이전트 가이드 참조
  ├── 스킬(도구 연동) 활용
  └── 파이프라인(TDD/린트/리뷰) 적용
```

---

## 5. 통신 아키텍처

### 5.1 통신 방식

```
Browser ────(HTTPS)────► Cloud API ────(ZIP Stream)────► Browser

현재 구현:
- 브라우저 ↔ Cloud API: HTTPS (REST)
- ZIP 생성: 서버 스트리밍 응답

미래 확장 (Phase 2):
- Browser ↔ Cloud: WebSocket (대시보드 실시간 업데이트)
- CLI ↔ Cloud: HTTPS (설정 동기화)
```

### 5.2 API 엔드포인트 요약

```
# 인증 (완료)
POST /api/v1/auth/register
POST /api/v1/auth/login

# 프로젝트 (완료)
GET  /api/v1/projects
POST /api/v1/projects
GET  /api/v1/projects/{id}

# 조직 (LoadMap_v3)
POST /api/v1/organizations
GET  /api/v1/organizations/me

# 카탈로그 (LoadMap_v3)
GET  /api/v1/catalog/agents
GET  /api/v1/catalog/skills
GET  /api/v1/catalog/platforms
GET  /api/v1/catalog/pipelines

# 위저드 (LoadMap_v3)
POST /api/v1/projects/{id}/config
GET  /api/v1/projects/{id}/config
POST /api/v1/projects/{id}/preview
POST /api/v1/projects/{id}/generate
POST /api/v1/recommend
```

---

## 6. 보안 고려사항

### 6.1 통신 보안
- **TLS**: 모든 통신은 HTTPS
- **인증**: Auth.js v5 + JWT

### 6.2 데이터 보안
- 사용자의 외부 도구 API 키 (Notion, Linear, Slack 등)는 **서버에 저장하지 않음**
- API 키는 브라우저 메모리에서만 처리 → .env 파일로 ZIP에만 포함
- 사용자의 AI API 키 (Claude, Gemini 등)는 로컬에만 저장
- 사용자 코드/데이터는 클라우드에 전송하지 않음

### 6.3 라이센스 보안 (Phase 2)
- 1계정 1프로젝트 무료, 추가 프로젝트 유료
- 라이센스 키 기반 프로젝트 한도 관리

---

## 7. 확장성 설계

### 7.1 수평 확장
- **Cloud**: FastAPI + Redis로 API 수평 확장 가능
- **생성 엔진**: 무상태 — 요청마다 메모리에서 파일 생성, ZIP 스트리밍

### 7.2 카탈로그 확장
- 에이전트/스킬/플랫폼은 **JSON 파일 추가만으로 확장** (DB 불필요)
- 관리자가 카탈로그 JSON에 항목 추가 → API가 자동 반영

### 7.3 Phase 2 확장
- 사용자 커스텀 에이전트 업로드/공유
- 에이전트 마켓플레이스
- CLI ↔ 웹 설정 동기화
- 사용 통계 대시보드
