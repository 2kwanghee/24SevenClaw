# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] Notion API Key 유효성 검증 엔드포인트 구현**
  > 요청사항: ## 작업 목적

Step 8에서 사용자가 Notion API Key + Database ID를 입력하면, 실제로 유효한 자격증명인지 서버 측에서 검증한다.

## 구현 명세

### 엔드포인트

```
POST /api/v1/integrations/notion/validate
```

### 요청 바디

```json
{
  "api_key": "secret_xxxxxxxxxxxxxxxx",
  "database_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

### 처리 로직

1. Notion REST API 호출: `GET https://api.notion.com/v1/databases/{database_id}`
   * Header: `Authorization: Bearer {api_key}`, `Notion-Version: 2022-06-28`
2. 응답 분기:
   * HTTP 401 → `{"valid": false, "error": "Notion API Key가 유효하지 않습니다"}`
   * HTTP 404 → `{"valid": false, "error": "데이터베이스를 찾을 수 없습니다. 데이터베이스 ID를 확인하거나 Integration을 공유했는지 확인하세요"}`
   * HTTP 400 (Invalid UUID) → `{"valid": false, "error": "데이터베이스 ID 형식이 올바르지 않습니다"}`
   * HTTP 200 → `{"valid": true, "database_title": "DB 제목"}`
3. `database_title`: 응답 JSON의 `title[0].plain_text` 또는 빈 문자열

### 응답 스키마

```json
{
  "valid": true,
  "database_title": "My Tasks DB"
}
```

또는

```json
{
  "valid": false,
  "error": "..."
}
```

### 보안

* 인증 필요 (`get_current_user` 의존성)
* 타임아웃: 5초

## 추가 고려사항

Notion Integration이 해당 데이터베이스에 **공유**되지 않으면 403이 반환될 수 있음.
→ HTTP 403 → `{"valid": false, "error": "Integration이 해당 데이터베이스에 공유되지 않았습니다. Notion에서 데이터베이스 공유 설정을 확인하세요"}`

## 참조 파일

* `app/api/v1/linear_credentials.py` — 구조 참조
* `app/api/v1/router.py` — 라우터 등록 필요

## 완료 기준

- `POST /api/v1/integrations/notion/validate` 엔드포인트 동작
- 유효한 key + database_id → `valid: true` + database_title
- 잘못된 API Key → `valid: false` + 에러
- 공유 안 된 DB → `valid: false` + 가이드 에러
- 잘못된 database_id → `valid: false` + 에러
- 5초 타임아웃 처리

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-22 | [api] Notion API Key 유효성 검증 엔드포인트 구현 | ✅ 완료 | POST /integrations/notion/validate, HTTP 상태코드별 분기 |