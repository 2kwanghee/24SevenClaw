# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] 카탈로그 Notion 스킬 추가 및 ZIP 템플릿 구현**
  > 요청사항: ## 배경

위저드에서 Linear/Notion 중 정확히 하나를 티켓 소스로 필수 선택하도록 변경 예정.
현재 카탈로그에 Notion 스킬이 없어 백엔드 카탈로그/템플릿 추가가 선행 필요.

## 작업 내용

- `clickeye-api/app/engine/catalog.py` `SKILLS`에 `notion` 항목 추가
  - id, label, description, env_vars: NOTION_API_KEY, NOTION_DATABASE_ID
  - category 필드 신설 (값: "ticket_source" — Linear/Notion 공통 분류용)
- 카탈로그 응답 스키마에 category 필드 추가 (`app/schemas/catalog.py`)
- `clickeye-api/app/engine/templates/skills/notion.md.hbs` 생성
  - 기존 `skills/linear.md.hbs` 구조 준수
  - Notion API 사용법 / 데이터베이스 ID 획득 / 페이지 생성 예시
- `clickeye-api/app/engine/generator.py` 템플릿 로더 검증 (linear와 동일 경로 처리 확인)
- 카탈로그 API 응답 스냅샷 테스트 업데이트

## 검증

* `GET /api/v1/catalog/skills` 응답에 notion 포함 확인
* ZIP 생성 시 `selectedSkills=["notion"]`이면 `skills/notion.md` 파일 포함
* 기존 Linear 선택 경로 회귀 없음

## 관련 파일

* `clickeye-api/app/engine/catalog.py:58-113`
* `clickeye-api/app/engine/generator.py:156,241`
* `clickeye-api/app/engine/templates/skills/linear.md.hbs` (참고용)
* `clickeye-api/app/schemas/catalog.py`

## 다음 작업

이 이슈 완료 후 → \[web\] 위저드 XOR UI 이슈 착수 가능

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | Notion 스킬 확인 + notion.md.j2 ClickEye 브랜딩 수정 | ✅ | catalog.py/JSON/template 이미 구현, .j2 브랜딩만 교체, 테스트 21개 통과 |