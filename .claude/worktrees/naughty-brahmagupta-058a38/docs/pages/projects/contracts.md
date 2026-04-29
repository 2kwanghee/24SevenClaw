---
route: /projects/[id]/contracts
title: 프로젝트 계약 관리
status: implemented
version: 1.0.0
pages:
  - src/app/(dashboard)/projects/[projectId]/contracts/page.tsx
components:
  - src/components/contracts/contract-viewer.tsx
  - src/components/contracts/override-editor.tsx
store: useRBACStore (권한 체크)
last_updated: 2026-04-16
---

## 목적
프로젝트별 AI 작업 계약(규칙/제약 조건)을 조회하고 오버라이드 편집.

---

## 레이아웃

```
┌──────────────────────────────────────────────────┐
│ 계약 관리                                         │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────────────────┐                      │
│  │ [ContractViewer]       │                      │
│  │ 계약 내용 읽기 전용 뷰  │                      │
│  └────────────────────────┘                      │
│                                                  │
│  오버라이드 (편집 권한자만)                        │
│  ┌────────────────────────┐                      │
│  │ [OverrideEditor]       │                      │
│  │ 규칙 추가/수정          │                      │
│  └────────────────────────┘                      │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 기능 요구사항

- [x] 계약 내용 뷰어 (읽기 전용)
- [x] 오버라이드 편집기 (권한 있는 경우)
- [x] RoleGuard 권한 체크
- [ ] 계약 버전 히스토리
- [ ] 계약 내보내기 (PDF)
- [ ] 변경 감사 로그

---

## API 연동

`use-contracts.ts` 훅으로 계약 데이터 조회/수정.
