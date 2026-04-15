# 구현 결과 — [web] RBAC 관리 UI (사용자/조직/감사로그)

## 상태: ✅ 완료

## 변경 파일

### 새 페이지
- `24SevenClaw-web/src/app/(dashboard)/admin/users/page.tsx` — 사용자 목록 + 역할 변경 UI
- `24SevenClaw-web/src/app/(dashboard)/admin/audit/page.tsx` — 감사 로그 테이블 (필터링/페이지네이션)
- `24SevenClaw-web/src/app/(dashboard)/settings/members/page.tsx` — 조직 멤버 초대/제거 UI

### 새 컴포넌트
- `24SevenClaw-web/src/components/common/role-guard.tsx` — 역할 기반 UI 가드

### 새 스토어/훅
- `24SevenClaw-web/src/stores/rbac-store.ts` — 현재 사용자 권한 캐시
- `24SevenClaw-web/src/hooks/use-rbac.ts` — RBAC 관련 TanStack Query 훅

## 구현 내용

1. **사용자 관리 (admin/users)**: 전체 사용자 목록 테이블 + RoleSelect 드롭다운으로 역할 즉시 변경
2. **감사 로그 (admin/audit)**: 감사 로그 테이블 + 액션 타입 필터 + 페이지네이션 (20건/페이지)
3. **조직 멤버 (settings/members)**: 멤버 초대 폼 (UUID + 역할 선택) + 삭제 확인 다이얼로그
4. **RoleGuard**: roles/permissions 기반 조건부 렌더링 (admin 페이지는 superadmin/admin만)
5. **접근 제어**: RoleGuard 컴포넌트로 admin 경로 보호

## 검증 결과

- TypeScript typecheck: ✅ 통과 (에러 0)
- ESLint: ⚠️ next lint 설정 이슈 (기존 문제, RBAC 관련 아님)

## 남은 이슈

- `settings/members/page.tsx`에서 DEFAULT_ORG_ID 하드코딩 → 세션/URL에서 실제 org_id 가져오는 로직 필요
- next lint 설정 문제는 별도 수정 필요
