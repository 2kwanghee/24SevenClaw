# 24S-83 구현 결과

## [web] 중앙 계약 관리 UI

### 변경 파일

| 파일 | 변경 | 설명 |
|------|------|------|
| `24SevenClaw-web/src/lib/api-client.ts` | 수정 | contracts API 타입/메서드 추가 |
| `24SevenClaw-web/src/hooks/use-contracts.ts` | 신규 | TanStack Query 커스텀 훅 (CRUD + 오버라이드 + 감사로그 + 동기화) |
| `24SevenClaw-web/src/components/contracts/contract-viewer.tsx` | 신규 | 계약 상세 뷰어 (메타정보 + JSON 콘텐츠) |
| `24SevenClaw-web/src/components/contracts/override-editor.tsx` | 신규 | 오버라이드 JSON 편집기 (허용 필드 검증) |
| `24SevenClaw-web/src/components/contracts/contract-audit-table.tsx` | 신규 | 계약 감사 로그 테이블 (필터 + 페이지네이션) |
| `24SevenClaw-web/src/app/(dashboard)/admin/contracts/page.tsx` | 신규 | 계약 목록 페이지 (타입 필터 + 생성 다이얼로그 + 페이지네이션) |
| `24SevenClaw-web/src/app/(dashboard)/admin/contracts/[id]/page.tsx` | 신규 | 계약 상세 페이지 (뷰/수정/삭제 + 감사 로그) |
| `24SevenClaw-web/src/app/(dashboard)/projects/[projectId]/contracts/page.tsx` | 신규 | 프로젝트별 계약 오버라이드 (적용/수정/동기화) |
| `24SevenClaw-web/src/app/(dashboard)/layout.tsx` | 수정 | 사이드바에 계약 관리 링크 추가 |

### 구현 내용

1. **어드민 계약 관리**
   - 계약 목록: 타입별 필터, 페이지네이션, 생성 다이얼로그
   - 계약 상세: 뷰/수정 토글, JSON 에디터, 삭제, 감사 로그 연동
   - RoleGuard로 admin+ 권한 제한

2. **프로젝트별 계약 뷰**
   - 적용된 오버라이드 목록 (카드 형태)
   - 오버라이드 편집: JSON 에디터 + 허용 필드 검증
   - 계약 적용 다이얼로그: 중앙 계약 목록에서 선택
   - 동기화 버튼: 에이전트에 계약 전송

3. **잠금 필드 시각적 구분**
   - Lock/Unlock 아이콘 + 색상 구분 (빨강/초록)
   - 오버라이드 편집 시 허용 필드 제약 안내

4. **디자인 패턴**
   - 기존 RBAC 어드민 페이지 패턴 준수 (다크 테마, 테이블, 필터)
   - shadcn/ui 컴포넌트 사용 안 함 (기존 프로젝트 패턴에 따라 커스텀)
   - Tailwind 유틸리티 클래스, 반응형, 접근성 aria-label

### 테스트 결과

- ESLint: 경고/에러 0개 (신규 파일 기준)
- TypeScript: `tsc --noEmit` 통과
- Next.js Build: `next build` 성공 (모든 페이지 정상 생성)

### 완료 조건 검증

- [x] 계약 CRUD UI 동작
- [x] 오버라이드 편집 동작
- [x] 잠금 필드 시각적 구분
- [x] 동기화 버튼 동작
