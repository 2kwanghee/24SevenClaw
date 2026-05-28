# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[backend] Phase 2 — User.language + AppError + Claude locale 분기**
  > 요청사항: ## 목표

백엔드가 사용자 locale을 인지하고 에러 메시지/Claude 응답을 한국어/영어로 분기한다. 관리자 API(`/admin/*`)는 항상 한국어 응답 유지.

## 변경 파일

### 모델 + 마이그레이션

* `clickeye-api/app/models/user.py` — `language: Column(String(8), default="en")`
* `clickeye-api/alembic/versions/039_user_language.py` (신규) — 컬럼 추가. 기존 사용자 default "en"

### 디펜던시

* `clickeye-api/app/dependencies/locale.py` (신규) — `get_locale(user, request) -> "ko" | "en"`
  * 인증 사용자: `user.language`
  * 비인증: `Accept-Language` 헤더 파싱
  * 둘 다 없음: `"en"` fallback

### 에러 메시지 i18n

* `clickeye-api/app/i18n/error_messages.py` (신규) — `{code: {ko: "...", en: "..."}}`
* `clickeye-api/app/core/exceptions.py` — locale 기반 메시지 결정
* 기존 호출처는 그대로 두되 새 발생 케이스부터 key 사용 (점진)

### Claude 시스템 프롬프트 분기

* `clickeye-api/app/services/claude_service.py`:
  * `_GENERATE_UI_STRUCTURE_SYSTEM`, `_ANALYZE_SOLUTION_SYSTEM`, `_RECOMMEND_PM_SYSTEM` 등을 `_get_system_prompt(name, locale)` 함수로 래핑
  * locale="en"이면 "Korean sentence" → "English sentence" 치환, 한글 예시 → 영문 예시
  * `analyze_solution`, `generate_ui_structure`, `recommend_pm` 등 메서드에 `locale: str = "ko"` 매개변수 추가
* 호출처(`prototype_service`, `presets/analyze-text`) locale 전달

### 사용자 설정 연동

* `clickeye-api/app/schemas/user.py` — language 필드 추가
* `PATCH /api/v1/users/me` 엔드포인트에서 language 변경 가능

## 검증

1. `PATCH /api/v1/users/me`로 language="en" 변경 후 prototype 생성 시 `variant_rationale`, `match_reasoning` 영어로 생성
2. ko 사용자는 기존대로 한국어 응답
3. `/admin/*` API는 locale 헤더 무시하고 항상 한국어 응답
4. alembic up/down 양방향 무손실

## 의존성

* 선행: [CE-255](https://linear.app/flow-ops/issue/CE-255/frontend-phase-1-e-온보딩-솔루션프로젝트설정가이드공개-레지스트리-i18n) (Phase 1-E — 프론트가 Accept-Language 송신 + 사용자 설정 UI 준비)
* 후속 CE-257이 본 이슈에 의존

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-05-28 | Phase 2 — User.language + AppError + Claude locale 분기 | ✅ 완료 | 10개 파일 변경, ruff 통과, mypy 2개 pre-existing 오류만 잔존 |