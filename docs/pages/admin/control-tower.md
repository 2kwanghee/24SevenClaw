---
title: 컨트롤 타워 (고객사 관리)
category: page
status: implemented
version: 1.0.0
route: /admin/control-tower
pages:
  - src/app/(dashboard)/admin/control-tower/page.tsx
  - src/app/(dashboard)/admin/control-tower/customers/[orgId]/page.tsx
components:
  - src/components/admin/control-tower/customer-list.tsx
store: 없음 (로컬 상태 useState)
last_updated: 2026-07-22
related:
  - src/app/(dashboard)/admin/control-tower/page.tsx
  - src/lib/api-client.ts (controlTower)
---

## 목적

Superadmin이 모든 고객사(고객)의 프로젝트 현황, 진행 중 세션 수, 상태(활성/일시정지/종료)를 한눈에 관리하는 대시보드.

---

## 레이아웃

```
┌──────────────────────────────────────────────────────┐
│ 컨트롤 타워  [새로고침 버튼]                          │
│ 고객사별 프로젝트 현황을 관리합니다                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│ [검색: __________]  [상태 필터: 전체▼]               │
│                                                      │
│ 총 N개 고객사                                         │
│                                                      │
├──────────────────────────────────────────────────────┤
│ 고객사 카드 그리드 (1열/2열/3열 반응형):              │
│                                                      │
│ ┌────────────────────┐  ┌────────────────────┐      │
│ │ [🏢] ABC Corp      │  │ [🏢] XYZ Ltd       │      │
│ │ [active] ✓         │  │ [paused]           │      │
│ │                    │  │                    │      │
│ │ 📦 프로젝트 5개    │  │ 📦 프로젝트 3개    │      │
│ │ 👥 진행 중 2건     │  │ 👥 진행 중 0건     │      │
│ │                    │  │                    │      │
│ │ 담당: 김경희       │  │ 담당: 미정         │      │
│ └────────────────────┘  └────────────────────┘      │
│                                                      │
│ [더 보기 / 페이지네이션]                              │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 고객사 목록 조회**
1. `/admin/control-tower` 진입
2. `controlTower.listCustomers()` → 고객사 목록 + 요약 조회
3. 상태별 배지, 프로젝트/세션 수 표시

**시나리오 2: 검색 + 필터**
1. 검색창에 고객사명 입력
2. 상태 필터 (active/paused/archived) 선택
3. `listCustomers({ search, status })` → 결과 갱신

**시나리오 3: 상세 페이지 이동**
1. 고객사 카드 클릭
2. `/admin/control-tower/customers/{orgId}` 이동
3. 고객사별 프로젝트 상세 페이지 (별도 구현)

**시나리오 4: 새로고침**
1. [새로고침] 버튼 클릭
2. `load()` 호출 → 데이터 재조회
3. 로딩 스켈레톤 표시 후 갱신

---

## 기능 요구사항

- [x] 고객사 카드 그리드 (1/2/3 열 반응형)
- [x] 검색 (고객사명)
- [x] 상태 필터 (전체/활성/일시정지/종료)
- [x] 프로젝트 수, 진행 중 세션 수 표시
- [x] 담당 Account Manager 표시
- [x] 새로고침 버튼
- [x] 로딩 상태 (스켈레톤)
- [x] 빈 상태 (고객사 없음)
- [ ] 상세 페이지 (고객사별 프로젝트 목록)
- [ ] 상태 변경 (운영 중 → 일시정지)
- [ ] 고객사 추가/삭제

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `customers` | `CustomerSummary[]` | `controlTower.listCustomers()` | 고객사 목록 |
| `total` | `number` | API 응답 | 전체 고객사 수 |
| `search` | `string` | 로컬 (useState) | 검색 쿼리 |
| `statusFilter` | `string` | 로컬 (useState) | 상태 필터 |
| `loading` | `boolean` | 로컬 (useState) | 로딩 상태 |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `GET` | `controlTower.listCustomers(token, { search, status })` | 진입/필터 변경 | 고객사 목록 + 요약 |

---

## 접근성 / 반응형

- [x] Superadmin 역할 제한 (RoleGuard)
- [x] 검색 필드 `aria-label="고객사 검색"`
- [x] 상태 필터 `aria-label="상태 필터"`
- [x] 카드 호버 상태 (border 강조, shadow 증가)
- [x] 모바일 (sm): 1열, 태블릿 (md): 2열, 데스크톱 (lg): 3열
- [x] 로딩/빈 상태 메시지

---

## 구현 노트

- **고객사 요약**: `CustomerSummary` 타입으로 프로젝트/세션 수 포함.
- **상태 필터**: `active | paused | archived`.
- **새로고침**: 세션이 있을 때만 작동 (useSession).
- **카드 클릭**: 상세 페이지로 라우팅 (`/admin/control-tower/customers/{orgId}`).
