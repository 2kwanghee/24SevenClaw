---
route: /solutions/new (Step 7)
title: 플랫폼 선택
status: implemented
version: 1.0.0
components:
  - src/components/solutions/wizard/steps/step-solution-platform.tsx
store: useSolutionWizardStore → setPlatform
last_updated: 2026-04-16
---

## 목적
로컬에서 AI 개발을 실행할 에이전트 플랫폼 선택 (Claude Code / Gemini CLI / Cursor / Codex).

---

## 레이아웃

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ Claude Code  │  │  Gemini CLI  │            │
│  │ ⭐ 권장      │  │              │            │
│  │ 설명 텍스트  │  │ 설명 텍스트  │            │
│  │  ✅ 선택됨   │  │  > 선택      │            │
│  └──────────────┘  └──────────────┘            │
│                                                 │
│  ┌──────────────┐  ┌──────────────┐            │
│  │    Cursor    │  │    Codex     │            │
│  │              │  │              │            │
│  │ 설명 텍스트  │  │ 설명 텍스트  │            │
│  │  > 선택      │  │  > 선택      │            │
│  └──────────────┘  └──────────────┘            │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │ 📁 폴더 구조 프리뷰 (선택 플랫폼 기준)   │   │
│  │ my-project/                              │   │
│  │ ├── .claude/                             │   │
│  │ │   ├── CLAUDE.md                        │   │
│  │ │   └── settings.json                   │   │
│  │ └── ...                                  │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 기능 요구사항

- [x] 4개 플랫폼 카드 (Claude Code / Gemini CLI / Cursor / Codex)
- [x] Claude Code 권장 배지
- [x] 단일 선택
- [x] 선택 시 폴더 구조 프리뷰 표시
- [x] `canProceed`: platformId 존재
- [ ] 플랫폼별 요구사항/제한사항 안내
- [ ] 플랫폼 비교 표

---

## 구현 노트

- 플랫폼 ID: `claude-code` | `gemini-cli` | `cursor` | `codex`
- 폴더 구조는 `lib/engine/platforms/` 의 생성 로직 기반
