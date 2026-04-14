# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] RBAC 모델 + 서비스 + 권한 미들웨어**
  > 요청사항: ## 개요

역할 기반 접근 제어(RBAC) 시스템을 API에 구현한다. 시스템 역할(superadmin/admin/member/viewer) + 조직 역할 + 권한 검증 미들웨어.

## 선행 조건

* 24S-201 (RBAC 타입 스키마) 완료 필수

## 범위

### DB 모델

* `models/user.py` 수정: `system_role` 컬럼 추가 (String(20), server_default='member')
* `models/rbac.py` 신규:
  * `OrganizationMembership`: user_id, organization_id, org_role, invited_by, joined_at, is_active
  * `RoleAuditLog`: actor_id, target_user_id, action, old_value, new_value, resource, created_at

### 서비스

* `services/rbac_service.py` 신규:
  * `check_permission(user, permission) → bool`
  * `assign_system_role(target_user_id, role, actor_user)`
  * `add_org_member()`, `remove_org_member()`, `get_org_members()`
  * `list_role_audit(filters)`
  * `ROLE_PERMISSIONS` 상수: superadmin=전체, admin=rbac:manage 제외, member=프로젝트+리포트, viewer=읽기전용

### 의존성 주입

* `dependencies.py`에 `require_permission(permission)` 팩토리 추가

### 엔드포인트 (`api/v1/rbac.py` 신규)

* `GET /rbac/permissions` — 내 권한 목록
* `GET /admin/users` — 전체 사용자 (superadmin)
* `PATCH /admin/users/{user_id}/role` — 역할 변경
* `GET/POST/DELETE /organizations/{org_id}/members` — 조직 멤버 관리
* `GET /admin/audit-log` — 감사 로그 (admin+)

### 마이그레이션

* `006_add_rbac_tables.py`

## 완료 조건

- [x] DB 모델 + 마이그레이션 완료
- [x] RBAC 서비스 + 권한 체크 로직
- [x] require_permission 의존성 주입 동작
- [x] 모든 엔드포인트 pytest 테스트 (성공/인증실패/권한부족)
- [x] 기존 엔드포인트에 require_permission 적용

## 크기: L

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-14 | DB 모델 + 마이그레이션 | 완료 | models/rbac.py, user.py system_role, 005 migration |
| 2026-04-14 | RBAC 서비스 + 스키마 | 완료 | services/rbac_service.py, schemas/rbac.py |
| 2026-04-14 | 의존성 주입 | 완료 | require_permission() in dependencies.py |
| 2026-04-14 | 엔드포인트 | 완료 | api/v1/rbac.py (7개 엔드포인트) |
| 2026-04-14 | 기존 엔드포인트 적용 | 완료 | projects, reports에 적용 |
| 2026-04-14 | 테스트 | 완료 | 14개 RBAC 테스트 + 전체 275개 통과 |