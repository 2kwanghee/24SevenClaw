---
route: /download/pm-environment (참조 문서, 독립 페이지 없음)
title: 플랫폼별 PM 배포 파일 매핑
category: page
status: implemented
version: 1.0.0
last_updated: 2026-04-17
---

## 목적

ZIP 다운로드 후 사용자의 로컬 환경에서 AI 플랫폼이 PM 파일을 읽는 경로와 형식을 정의한다. 관리자가 Registry에서 PM을 구성하거나 위저드에서 플랫폼을 선택할 때 이 매핑을 참조한다.

---

## 플랫폼별 디렉토리 구조

### Claude Code

```
my-project/
├── CLAUDE.md                      ← 루트 가이드 (에이전트 참조 포함)
├── .claude/
│   ├── settings.json              ← 권한 + hook 설정
│   ├── agents/
│   │   ├── code-reviewer.md
│   │   └── ...
│   ├── skills/
│   │   ├── harness-gate.md
│   │   └── ...
│   └── pm/
│       └── {pm-slug}.md           ← PM 파일 ★
└── .env.example
```

**PM 파일 경로**: `.claude/pm/{pm-slug}.md`

**PM 파일 형식**: Markdown. `CLAUDE.md`에서 `@.claude/pm/{pm-slug}.md` 로 참조되어 Claude Code 세션 시작 시 자동 로드된다.

---

### Gemini CLI

```
my-project/
├── GEMINI.md                      ← 루트 가이드
├── .gemini/
│   ├── settings.json
│   ├── agents/
│   │   └── ...
│   ├── skills/
│   │   └── ...
│   └── pm/
│       └── {pm-slug}.md           ← PM 파일 ★
└── .env.example
```

**PM 파일 경로**: `.gemini/pm/{pm-slug}.md`

**PM 파일 형식**: Markdown. `GEMINI.md`에서 참조.

---

### Cursor

```
my-project/
├── .cursorrules                   ← 루트 가이드
├── .cursor/
│   ├── settings.json
│   └── rules/
│       ├── code-reviewer.md
│       ├── ...
│       └── pm-{pm-slug}.md        ← PM 파일 ★ (rules/ 하위 배치)
└── .env.example
```

**PM 파일 경로**: `.cursor/rules/pm-{pm-slug}.md`

**PM 파일 형식**: Markdown. Cursor는 `.cursor/rules/` 디렉토리의 모든 `.md` 파일을 Context Rule로 자동 로드하므로 별도 참조 불필요.

---

### Codex (OpenAI)

```
my-project/
├── CODEX.md                       ← 루트 가이드
├── .codex/
│   ├── settings.json
│   ├── agents/
│   │   └── ...
│   └── pm/
│       └── {pm-slug}.py           ← PM 파일 ★ (Python 형식)
└── .env.example
```

**PM 파일 경로**: `.codex/pm/{pm-slug}.py`

**PM 파일 형식**: Python 모듈. `pm_markdown` 원문이 docstring으로 래핑된다.

```python
"""
# PM 이름
## 역할 & 전문 분야
...
(pm_markdown 원문)
"""

PM_SLUG = "alex-pm"
```

---

## 파일 매핑 요약표

| 플랫폼 | 루트 가이드 | 에이전트 디렉토리 | 스킬 디렉토리 | PM 파일 경로 | 파일 형식 |
|--------|-------------|-------------------|---------------|-------------|-----------|
| Claude Code | `CLAUDE.md` | `.claude/agents/` | `.claude/skills/` | `.claude/pm/{slug}.md` | Markdown |
| Gemini CLI | `GEMINI.md` | `.gemini/agents/` | `.gemini/skills/` | `.gemini/pm/{slug}.md` | Markdown |
| Cursor | `.cursorrules` | `.cursor/rules/` | `.cursor/rules/` | `.cursor/rules/pm-{slug}.md` | Markdown |
| Codex | `CODEX.md` | `.codex/agents/` | `.codex/skills/` | `.codex/pm/{slug}.py` | Python |

---

## PM 파일 내용 구조 (Markdown 플랫폼 공통)

관리자가 `/admin/pm/[id]`의 **PM 마크다운 편집** 탭에서 작성하는 원문이 그대로 ZIP에 포함된다.

```markdown
# {PM 이름}

## 역할 & 전문 분야
{bio_long 또는 description 내용}

## 기술 스택
{tech_stack_tags 기반 자동 생성 또는 수동 작성}

## 작업 스타일
{personality JSON 기반 텍스트}

## 전문 영역
{specialties 배열}

## 협업 원칙
{관리자 직접 작성}
```

---

## ZIP 파일 내용 일치 검증

위저드 → 프로젝트 생성 → ZIP 다운로드 후 다음을 확인한다.

```bash
# Claude Code 예시
unzip solution.zip -d my-project
cat my-project/.claude/pm/alex-pm.md
# → 관리자가 작성한 pm_markdown 원문과 일치해야 함

cat my-project/CLAUDE.md
# → @.claude/pm/alex-pm.md 참조 라인 포함 여부 확인
```

---

## 권한 회귀 시나리오

| 역할 | `/admin/registry/*` | `/admin/pm/*` | 결과 |
|------|---------------------|---------------|------|
| superadmin | ✅ 접근 허용 | ✅ 접근 허용 | 정상 |
| admin | ✅ 접근 허용 | ✅ 접근 허용 | 정상 |
| member | ❌ 403 AccessDenied | ❌ 403 AccessDenied | RoleGuard 차단 |
| viewer | ❌ 403 AccessDenied | ❌ 403 AccessDenied | RoleGuard 차단 |

백엔드 이중 보호: `require_permission("registry:manage")` / `require_permission("pm:manage")` 미충족 시 HTTP 403 반환.
