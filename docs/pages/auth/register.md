---
route: /register
title: 회원가입
category: page
status: implemented
version: 1.0.0
pages:
  - src/app/(auth)/register/page.tsx
store: 없음
last_updated: 2026-04-16
---

## 목적
이메일/비밀번호로 신규 계정 생성.

---

## 기능 요구사항

- [x] 이메일, 비밀번호, 표시 이름 입력
- [x] React Hook Form + Zod 유효성 검사
- [x] 비밀번호 표시/숨기기 토글
- [x] 가입 완료 후 로그인 페이지 이동
- [x] 이미 계정 있음 → 로그인 링크
- [ ] 이메일 인증 (가입 후 인증 메일 발송)
- [ ] 비밀번호 강도 표시기
- [ ] 서비스 이용 약관 동의 체크박스
