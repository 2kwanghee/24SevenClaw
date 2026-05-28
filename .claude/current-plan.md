## 목표
관리자가 카탈로그(agents/skills/mcp_servers/hooks)와 PM 프로필의 영문 필드를 직접 입력/수정할 수 있는 UI 추가.
미입력 항목에 "번역 미입력" 노란색 배지로 시각적 경고. (CE-258)

## 변경 파일 목록
- `clickeye-web/src/lib/api-client.ts`: RegistryItemResponse/CreateRequest/UpdateRequest, PMProfileResponse/CreateRequest에 `_en` 필드 추가
- `clickeye-web/src/lib/validations/pm.ts`: PMProfileFormData + Zod schema에 `_en` 필드 추가
- `clickeye-web/src/components/admin/registry/registry-editor-drawer.tsx`: 한국어/영어 탭 UI + `name_en`, `description_en`, `body_md_en` 입력
- `clickeye-web/src/components/admin/pm/pm-edit-form.tsx`: 영문 번역 섹션 추가 (`name_en`, `title_en`, `description_en`, `bio_long_en`)

## 구현 단계
1. api-client.ts — _en 필드 타입 추가
2. pm.ts — Zod 스키마 + PMProfileFormData _en 필드 추가
3. registry-editor-drawer.tsx — 한국어/영어 탭 + 번역 미입력 배지
4. pm-edit-form.tsx — 영문 번역 CollapsibleSection 추가

## 예상 영향 범위
- 관리자 레지스트리/PM 편집 폼만 변경 (사용자 facing UI 무영향)
- 기존 한국어 필드 동작 유지, _en 필드만 추가

## STATUS: APPROVED
