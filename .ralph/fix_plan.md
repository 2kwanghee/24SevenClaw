# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] RBAC 관리 UI (사용자/조직/감사로그)**
  > 요청사항: ## 개요

RBAC 관리를 위한 어드민/조직 페이지를 웹에 구현한다.

## 선행 조건

* [24S-73](https://linear.app/flow-ops/issue/24S-73/api-rbac-모델-서비스-권한-미들웨어) (RBAC API) 완료 필수

## 범위

### 새 페이지

* (dashboard)/admin/users/page.tsx: 사용자 목록 + 역할 관리
* (dashboard)/admin/audit/page.tsx: 감사 로그 테이블
* (dashboard)/settings/members/page.tsx: 조직 멤버 관리

### 새 컴포넌트

* components/common/role-guard.tsx: 역할 기반 UI 가드

### 미들웨어

* /admin/\* 경로 보호 (session.system_role 체크)

### 새 스토어

* stores/rbac-store.ts: 현재 사용자 권한 캐시

## 완료 조건

- 사용자 목록 + 역할 변경 UI
- 감사 로그 테이블 (필터링/페이지네이션)
- 조직 멤버 초대/제거 UI
- admin 경로 접근 제어 동작
- RoleGuard 컴포넌트 동작

## 크기: M

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-15 | [web] RBAC 관리 UI | ✅ 완료 | 커밋 0ee4be6에서 구현 완료, typecheck 통과 확인 |