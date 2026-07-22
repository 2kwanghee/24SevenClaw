---
title: 전역 설정
category: page
status: implemented
version: 1.0.0
route: /admin/settings
pages:
  - src/app/(dashboard)/admin/settings/page.tsx
components:
  - src/components/admin/app-settings-panel.tsx
store: 없음 (TanStack Query)
last_updated: 2026-07-22
related:
  - src/app/(dashboard)/admin/settings/page.tsx
---

## 목적

Superadmin/Admin이 딜리버리/시스템 동작에 영향을 주는 전역 설정(플래그, 파라미터)을 관리하는 페이지.

---

## 레이아웃

```
┌────────────────────────────────────────────────────┐
│ 전역 설정                                          │
│ 딜리버리/시스템 동작에 영향을 주는 전역 설정을 관리합니다 │
├────────────────────────────────────────────────────┤
│                                                    │
│ ┌────────────────────────────────────────────────┐ │
│ │ AppSettings Panel                              │ │
│ │ [설정 항목들 + 토글/입력 필드]                  │ │
│ │ ...                                            │ │
│ └────────────────────────────────────────────────┘ │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 설정 페이지 진입**
1. `/admin/settings` 진입
2. RoleGuard (superadmin/admin 검증)
3. `AppSettingsPanel` 컴포넌트 렌더링

**시나리오 2: 설정 변경**
1. 패널 내 설정 항목(토글/입력) 수정
2. 변경사항 API로 저장
3. 변경된 설정 즉시 반영

---

## 기능 요구사항

- [x] 권한 제한 (superadmin/admin)
- [x] 전역 설정 표시 및 수정
- [x] 설정 저장 (API)
- [x] 성공/에러 메시지
- [ ] 설정 카테고리별 섹션
- [ ] 기본값 리셋
- [ ] 설정 변경 이력

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `settings` | `AppSettings` | `AppSettingsPanel` (TanStack Query) | 전역 설정 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/admin/settings` | 페이지 로드 | 전역 설정 조회 |
| `PATCH` | `/api/v1/admin/settings` | 저장 버튼 클릭 | 설정 업데이트 |

---

## 접근성 / 반응형

- [x] RoleGuard (superadmin/admin)
- [x] 토글 `role="switch"` / `aria-checked`
- [x] 입력 필드 라벨 `<label>`
- [x] 설명 텍스트 명확
- [x] 모바일 반응형

---

## 구현 노트

- **AppSettingsPanel**: `components/admin/app-settings-panel.tsx`에서 전체 UI 구현.
- **권한**: `require_permission("settings:manage")` 또는 superadmin 자동.
- **설정 항목**: app_settings DB 테이블에 저장.
