---
route: /admin/contracts
title: 중앙 계약 관리
status: implemented
version: 1.0.0
pages:
  - src/app/(dashboard)/admin/contracts/page.tsx
store: useRBACStore (admin+)
last_updated: 2026-04-16
---

## 목적
모든 프로젝트의 AI 작업 계약을 중앙에서 관리 (생성/조회/상태 변경).

---

## 기능 요구사항

- [x] 계약 목록 테이블
- [x] 계약 생성 버튼 + 모달/폼
- [x] 계약 상태 관리 (active / draft / archived)
- [x] 계약 상세 링크 (`/admin/contracts/{id}`)
- [x] RoleGuard (admin+)
- [ ] 계약 검색/필터 (프로젝트별, 상태별)
- [ ] 계약 일괄 내보내기
- [ ] 계약 템플릿
