---
route: /admin/registry
title: Registry 관리 (Agent / Skill / MCP Server)
category: page
status: implemented
version: 1.0.0
roles: superadmin, admin
last_updated: 2026-04-17
---

## 목적

관리자가 **Agent**, **Skill**, **MCP Server** 카탈로그를 GUI로 CRUD하는 전용 화면이다. Registry에 등록된 항목은 PM Composition에서 참조되며, 딜리버리 플랫폼 커스터마이제이션의 핵심이다.

---

## 접근 권한

`superadmin` 또는 `admin` 역할 + `registry:manage` 권한이 있어야 메뉴가 표시되고 접근 가능하다. 백엔드는 `require_permission("registry:manage")`로 이중 보호된다.

---

## 페이지 구성

### 공통 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│  [Agents]  [Skills]  [MCP Servers]           탭 내비     │
├─────────────────────────────────────────────────────────┤
│  검색: [__________]  카테고리: [전체▼]  공개: [전체▼]   │
│  ──────────────────────────────────────────────────────  │
│  이름         Slug          카테고리   공개  생성일       │
│  ──────────────────────────────────────────────────────  │
│  코드 리뷰어  code-reviewer  dev       ✅   2026-01-10   │
│  Jira 스킬   jira-sync      ops       ❌   2026-02-05   │
│  ...                                                     │
├─────────────────────────────────────────────────────────┤
│  [페이지네이션]                          [+ 새 항목 추가] │
└─────────────────────────────────────────────────────────┘
```

### Agent 관리 (`/admin/registry/agents`)

Agent는 위저드에서 사용자가 선택할 수 있는 AI 에이전트 역할 파일이다.

| 필드 | 설명 |
|------|------|
| `name` | 표시 이름 (예: "코드 리뷰어") |
| `slug` | 고유 식별자 — ZIP 내 파일명 기준 (예: `code-reviewer`) |
| `category` | 그룹 분류 (예: `dev`, `ops`, `data`) |
| `description` | 에이전트 역할 설명 (한 줄 요약) |
| `template` | 사용할 Jinja2 템플릿 파일명 (예: `code_reviewer.md.j2`) |
| `output_file` | ZIP 내 에이전트 파일명 (예: `code-reviewer.md`) |
| `is_public` | 위저드에서 일반 사용자에게 표시 여부 |
| `tags` | 연관 기술 태그 배열 |

**추가/수정 폼**:
- 슬러그는 이름 자동 변환 (kebab-case) 후 수동 수정 가능
- 템플릿 파일명은 서버에 존재해야 하며 목록에서 선택

### Skill 관리 (`/admin/registry/skills`)

Skill은 위저드에서 선택되어 settings.json hook과 `.claude/skills/` 파일로 생성되는 자동화 스킬이다.

| 필드 | 설명 |
|------|------|
| `name` | 표시 이름 (예: "하네스 게이트") |
| `slug` | 고유 식별자 (예: `harness-gate`) |
| `category` | 그룹 분류 (예: `automation`, `quality`, `security`) |
| `description` | 스킬 역할 설명 |
| `template` | Jinja2 템플릿 파일명 |
| `output_file` | ZIP 내 스킬 파일명 |
| `hooks` | 연결할 hook 이벤트 배열 (예: `["PostToolUse"]`) |
| `env_vars` | 이 스킬이 요구하는 환경변수 키 목록 |
| `is_public` | 공개 여부 |

### MCP Server 관리 (`/admin/registry/mcp-servers`)

MCP Server는 settings.json의 `mcpServers` 블록에 추가되는 외부 도구 서버다.

| 필드 | 설명 |
|------|------|
| `name` | 표시 이름 (예: "Context7") |
| `slug` | 고유 식별자 (예: `context7`) |
| `category` | 그룹 분류 (예: `docs`, `search`, `db`) |
| `description` | MCP 서버 역할 설명 |
| `command` | 실행 명령어 (예: `npx @upstash/context7-mcp`) |
| `args` | 실행 인자 배열 (JSON) |
| `env_keys` | 필요한 환경변수 키 목록 |
| `is_public` | 공개 여부 |

---

## API 엔드포인트

### Agent

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/v1/admin/registry/agents` | 목록 조회 (필터: category, is_public) |
| `POST` | `/api/v1/admin/registry/agents` | 생성 |
| `GET` | `/api/v1/admin/registry/agents/{id}` | 단건 조회 |
| `PUT` | `/api/v1/admin/registry/agents/{id}` | 수정 |
| `DELETE` | `/api/v1/admin/registry/agents/{id}` | 삭제 |

### Skill

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/v1/admin/registry/skills` | 목록 조회 |
| `POST` | `/api/v1/admin/registry/skills` | 생성 |
| `GET` | `/api/v1/admin/registry/skills/{id}` | 단건 조회 |
| `PUT` | `/api/v1/admin/registry/skills/{id}` | 수정 |
| `DELETE` | `/api/v1/admin/registry/skills/{id}` | 삭제 |

### MCP Server

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/v1/admin/registry/mcp-servers` | 목록 조회 |
| `POST` | `/api/v1/admin/registry/mcp-servers` | 생성 |
| `GET` | `/api/v1/admin/registry/mcp-servers/{id}` | 단건 조회 |
| `PUT` | `/api/v1/admin/registry/mcp-servers/{id}` | 수정 |
| `DELETE` | `/api/v1/admin/registry/mcp-servers/{id}` | 삭제 |

모든 엔드포인트는 `registry:manage` 권한 필요.

---

## PM Composition 연동

Registry에 등록된 Agent/Skill은 **PM Composition 관리** (`/admin/pm/[id]/composition`)에서 검색·선택하여 PM에 연결할 수 있다. 연결된 항목은 ZIP 생성 시 PM compositions 우선 병합 로직에 따라 에이전트·스킬 파일로 생성된다.

Registry에서 항목을 삭제해도 이미 연결된 PM Composition 레코드는 유지되지만 **"Registry 연결 끊김"** 경고 배지가 표시된다.

---

## 스토리보드

**시나리오 1: 새 Agent 등록**
1. `/admin/registry` 진입 → Agents 탭 선택
2. `+ 새 항목 추가` 클릭 → 슬라이드 폼 열림
3. 이름 입력 → slug 자동 생성 확인 → 수정 가능
4. 템플릿 파일 선택, 카테고리·태그 입력
5. `저장` 클릭 → 목록에 즉시 반영

**시나리오 2: 권한 없는 접근 (일반 user)**
1. `/admin/registry` 직접 URL 입력
2. `RoleGuard` → 403 AccessDenied 페이지로 리다이렉트

**시나리오 3: Registry 항목 삭제**
1. 삭제 버튼 클릭 → "이 항목을 사용하는 PM Composition N개가 있습니다. 계속하시겠습니까?" confirm
2. 확인 → 삭제, 연결된 Composition에 경고 배지 추가

---

## 접근성 / 반응형

- [x] `role="tablist"` — Agents / Skills / MCP Servers 탭
- [x] 검색 필드 `aria-label="항목 검색"`
- [x] 삭제 confirm 다이얼로그 focus trap
- [x] 모바일: 카드 뷰 전환 (테이블 대신)

---

## 구현 노트

- 슬러그 중복 체크: POST/PUT 시 백엔드에서 409 Conflict 반환, 프론트에서 인라인 에러 표시
- 템플릿 파일 목록은 `/api/v1/admin/registry/templates` (별도 읽기 전용 엔드포인트) 에서 조회
- 삭제 시 연결된 Composition 수 확인: `GET /api/v1/admin/registry/agents/{id}/compositions`
