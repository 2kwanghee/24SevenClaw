---
route: /admin/contracts/[id]
title: 계약 상세
status: implemented
version: 1.0.0
pages:
  - src/app/(dashboard)/admin/contracts/[id]/page.tsx
components:
  - src/components/contracts/contract-viewer.tsx
  - src/components/contracts/contract-audit-table.tsx
store: useRBACStore (admin+)
last_updated: 2026-04-16
---

## 목적
개별 계약의 상세 내용 조회, 편집, 변경 이력(감사 테이블) 확인.

---

## 기능 요구사항

- [x] 계약 내용 뷰어
- [x] 계약 편집 폼
- [x] 감사 로그 테이블 (언제/누가/무엇을 변경)
- [x] RoleGuard (admin+)
- [ ] 계약 버전 비교 (diff 뷰)
- [ ] 계약 승인 워크플로우
