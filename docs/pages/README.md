---
title: 페이지 스펙 기반 개발 파이프라인 (인덱스)
category: page
status: current
last_updated: 2026-07-22
related:
  - clickeye-web/src/app
  - docs/pages/_template.md
  - docs/pages/admin/ops.md
---

# 페이지 스펙 기반 개발 파이프라인

`docs/pages/` 디렉토리는 ClickEye 웹 프로덕트의 **페이지 단위 스펙**을 관리하는 형상관리 저장소입니다.  
MD 파일을 수정하면 Claude가 해당 코드를 읽고 리팩토링하는 파이프라인의 **단일 진실 공급원(Single Source of Truth)** 역할을 합니다.

---

## 디렉토리 구조

```
docs/pages/
├── README.md                       ← 이 파일
├── _template.md                    ← 새 페이지 스펙 작성 템플릿
│
├── landing.md                      → /
├── auth/
│   ├── login.md                    → /login
│   └── register.md                 → /register
│
├── solutions/
│   ├── list.md                     → /solutions
│   └── session.md                  → /solutions/[sessionId]
│
├── projects/
│   ├── list.md                     → /projects
│   ├── detail.md                   → /projects/[id]
│   ├── dashboard.md                → /projects/[id]/dashboard
│   ├── ai-team.md                  → /projects/[id]/ai-team
│   ├── contracts.md                → /projects/[id]/contracts
│   ├── insights.md                 → /projects/[id]/insights
│   └── settings.md                → /projects/[id]/settings
│
├── onboarding/
│   ├── preset.md                   → /onboarding/preset
│   └── maturity.md                 → /onboarding/maturity
│
├── admin/
│   ├── users.md                    → /admin/users
│   ├── contracts-list.md           → /admin/contracts
│   ├── contracts-detail.md         → /admin/contracts/[id]
│   ├── audit.md                    → /admin/audit
│   ├── pm-management.md            → /admin/pm (+[id], /composition)
│   ├── registry.md                 → /admin/registry
│   ├── recommendation-logs.md      → /admin/recommendations
│   └── ops.md                      → /admin/ops (CE-305, superadmin)
│
├── download/
│   └── pm-environment.md           → (참조 문서, 독립 페이지 없음)
│
└── settings/
    └── members.md                  → /settings/members
```

---

## 파이프라인 사용법

### 기능 요구사항 변경 시
1. 해당 페이지의 MD 파일을 열어 `## 기능 요구사항` 섹션에 항목 추가/수정
2. `status` 필드를 `needs-revision`으로 변경
3. Claude에게 전달: **"[파일경로] 업데이트했어, 반영해줘"**

```
예시:
"docs/pages/projects/detail.md 업데이트했어, 반영해줘"
```

### 레이아웃/구조 변경 시
1. MD 파일의 `## 레이아웃` 또는 `## 스토리보드` 섹션 수정
2. Claude에게 전달: **"[파일경로] 레이아웃 바뀌었어, 코드 맞춰줘"**

### 새 페이지 추가 시
1. `_template.md`를 복사해 새 파일 생성
2. 모든 섹션 작성
3. Claude에게 전달: **"[파일경로] 새 페이지야, 구현해줘"**

---

## Status 필드 값

| 값 | 의미 |
|----|------|
| `draft` | 스펙 작성 중, 구현 미시작 |
| `in-progress` | 구현 진행 중 |
| `implemented` | 구현 완료, 스펙과 코드 일치 |
| `needs-revision` | 스펙 변경됨, 코드 리팩토링 필요 |

---

## 기능 요구사항 체크리스트 규칙

```markdown
- [x] 구현 완료된 기능
- [ ] 미구현 또는 개선 필요한 기능
- [~] 부분 구현 (주석으로 미완성 내용 표시)
```

---

## 연결 파일 맵

| MD 파일 | page.tsx | 주요 컴포넌트 | 스토어 |
|---------|----------|--------------|--------|
| `projects/list.md` | `projects/page.tsx` | `ProjectList`, `ProjectCard` | — |
| `admin/users.md` | `admin/users/page.tsx` | `RoleGuard`, 사용자 테이블 | `useRBACStore` |
