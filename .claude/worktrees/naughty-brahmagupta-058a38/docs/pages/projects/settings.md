---
route: /projects/[id]/settings
title: 프로젝트 설정
status: implemented
version: 1.0.0
pages:
  - src/app/(dashboard)/projects/[projectId]/settings/page.tsx
components:
  - src/components/projects/project-form.tsx
store: 없음 (TanStack Query)
last_updated: 2026-04-16
---

## 목적
프로젝트 이름, 설명, 상태 등 기본 설정을 수정하고 프로젝트 아카이브/삭제 관리.

---

## 기능 요구사항

- [x] 프로젝트 이름 수정
- [x] 설명 수정
- [x] 저장 버튼
- [ ] 프로젝트 아카이브 (비가역적 경고)
- [ ] 위험 구역 (Danger Zone) 섹션
- [ ] 슬러그 수정
- [ ] 팀 멤버 권한 설정
