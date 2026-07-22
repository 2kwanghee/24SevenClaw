---
title: ROI 단가/공수 표준
category: page
status: implemented
version: 1.0.0
route: /admin/roi-standards
pages:
  - src/app/(dashboard)/admin/roi-standards/page.tsx
components:
  - src/components/admin/roi/roi-standards-table.tsx
store: 없음 (TanStack Query)
last_updated: 2026-07-22
related:
  - src/app/(dashboard)/admin/roi-standards/page.tsx
---

## 목적

Admin이 위저드의 ROI 비교 산출에 사용되는 표준 파라미터(직군 단가, 솔루션 공수, 복잡도 계수)를 관리하는 페이지. 변경 사항은 새 세션에 즉시 반영.

---

## 레이아웃

```
┌────────────────────────────────────────────────────┐
│ ROI 단가/공수 표준                                  │
│ 위저드 ROI 비교 산출에 사용되는 표준 파라미터 관리  │
├────────────────────────────────────────────────────┤
│                                                    │
│ [직군 단가] [솔루션 공수] [복잡도 계수]            │
│                                                    │
├────────────────────────────────────────────────────┤
│                                                    │
│ 직군 단가 (KRW/day)                                │
│ ┌──────────────────────────────────────────────┐  │
│ │ 직군      │ 단가 (KRW) │ 액션              │  │
│ ├──────────────────────────────────────────────┤  │
│ │ Backend  │ 500,000    │ [편집] [삭제]     │  │
│ │ Frontend │ 400,000    │ [편집] [삭제]     │  │
│ │ DevOps   │ 600,000    │ [편집] [삭제]     │  │
│ │ [+ 추가] │           │                    │  │
│ └──────────────────────────────────────────────┘  │
│                                                    │
│ 변경 사항은 새 세션에 즉시 반영됩니다.             │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 직군 단가 조회**
1. `/admin/roi-standards` 진입
2. 탭 "직군 단가" 선택 (기본)
3. `RoiStandardsTable category="role_rate"` → 테이블 렌더링

**시나리오 2: 솔루션 공수 탭 전환**
1. "솔루션 공수" 탭 클릭
2. 상태 업데이트 (tab="solution_effort")
3. 테이블 재렌더링 (솔루션 타입별 직군별 baseline 표시)

**시나리오 3: 복잡도 계수 탭 전환**
1. "복잡도 계수" 탭 클릭
2. 상태 업데이트 (tab="complexity_multiplier")
3. 복잡도별 공수 배율 표시

**시나리오 4: 항목 수정**
1. 테이블에서 [편집] 버튼 클릭
2. 인라인 폼 또는 모달 열기
3. 값 입력 후 저장
4. 서버 업데이트 후 즉시 반영

---

## 기능 요구사항

- [x] 3개 탭 인터페이스 (role_rate / solution_effort / complexity_multiplier)
- [x] 각 탭별 테이블 표시
- [x] 항목 추가/수정/삭제 (CRUD)
- [x] 변경 사항 실시간 저장
- [x] 설명 문구 (각 탭별)
- [x] 권한 제한 (superadmin/admin)
- [ ] 일괄 가져오기 (CSV)
- [ ] 변경 이력
- [ ] 기본값 리셋

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `tab` | `"role_rate" \| "solution_effort" \| "complexity_multiplier"` | 로컬 (useState) | 현재 탭 |
| `standards` | `Standard[]` | `RoiStandardsTable` (TanStack Query) | 표준 항목 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/admin/roi/{category}` | 탭 선택 | 표준 항목 조회 |
| `POST` | `/api/v1/admin/roi/{category}` | [+ 추가] 클릭 | 항목 생성 |
| `PUT` | `/api/v1/admin/roi/{category}/{id}` | [편집] 저장 | 항목 수정 |
| `DELETE` | `/api/v1/admin/roi/{category}/{id}` | [삭제] 클릭 | 항목 삭제 |

---

## 접근성 / 반응형

- [x] RoleGuard (superadmin/admin)
- [x] 탭 `role="tablist"` / `aria-selected`
- [x] 테이블 `role="table"` / `aria-label`
- [x] 동작 버튼 `aria-label` 제공
- [x] 모바일: 카드 뷰 (테이블 대신 세로 레이아웃)

---

## 구현 노트

- **탭 상태**: `useState<Tab>` 로컬 관리 (URL 상태 유지 선택사항).
- **즉시 반영**: 새 세션 생성 시 최신 표준 사용.
- **category별 테이블**: `RoiStandardsTable` 컴포넌트에서 API 호출 (React Query).
- **권한**: `require_permission("roi:manage")` 또는 superadmin 자동 포함.
