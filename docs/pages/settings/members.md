---
route: /settings/members
title: 조직 멤버 관리
status: implemented
version: 1.0.0
pages:
  - src/app/(dashboard)/settings/members/page.tsx
store: useRBACStore (org:manage 권한)
last_updated: 2026-04-16
---

## 목적
조직의 멤버를 초대하고 역할을 관리 (org:manage 권한자만).

---

## 레이아웃

```
┌──────────────────────────────────────────────────┐
│ 조직 멤버                          [+ 멤버 초대]  │
├──────────────────────────────────────────────────┤
│ 이름         이메일        역할          액션      │
│ ─────────────────────────────────────────────── │
│ 홍길동       hong@...    [org_admin]    [제거]    │
│ 김철수       kim@...     [org_member]  [제거]    │
└──────────────────────────────────────────────────┘
```

---

## 기능 요구사항

- [x] 멤버 목록 테이블
- [x] 멤버 초대 (이메일 입력)
- [x] 멤버 제거 (확인 다이얼로그)
- [x] 역할 표시 (org_admin / org_member / org_viewer)
- [x] RoleGuard (org:manage 권한)
- [ ] 역할 변경 드롭다운
- [ ] 초대 링크 복사
- [ ] 대기 중 초대 목록 (pending invitations)
