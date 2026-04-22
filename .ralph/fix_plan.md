# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] Linear API Key 유효성 검증 엔드포인트 구현**
  > 요청사항: ## 작업 목적

Step 8에서 사용자가 Linear API Key + Team ID를 입력하면, 저장 전에 실제로 유효한 자격증명인지 서버 측에서 검증한다.

## 구현 명세

### 엔드포인트

```
POST /api/v1/integrations/linear/validate
```

### 요청 바디

```json
{
  "api_key": "lin_api_xxxxxxxxxxxxxxxx",
  "team_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### 처리 로직

1. Linear GraphQL API (`https://api.linear.app/graphql`) 호출
2. 쿼리: `{ team(id: $teamId) { id name } }` — API Key를 Bearer 토큰으로 사용
3. 응답 분기:
   * HTTP 401 또는 errors 포함 → `{"valid": false, "error": "API Key가 유효하지 않습니다"}`
   * team이 null (존재하지 않는 팀) → `{"valid": false, "error": "팀 ID를 찾을 수 없습니다"}`
   * 정상 → `{"valid": true, "team_name": "팀 이름"}`

### 응답 스키마

```json
{
  "valid": true,
  "team_name": "My Team"   // valid=true 시만 포함
}
```

또는

```json
{
  "valid": false,
  "error": "API Key가 유효하지 않습니다"
}
```

### 보안

* 이 엔드포인트는 인증 필요 (`get_current_user` 의존성)
* API Key를 응답에 포함하지 않음
* 타임아웃: 5초 (Linear 서버 장애 대응)

## 참조 파일

* `app/api/v1/linear_credentials.py` — 기존 Linear 엔드포인트
* `app/services/linear_service.py` — GraphQL 호출 로직 참조
* `app/api/v1/router.py` — 라우터 등록 필요

## 완료 기준

- `POST /api/v1/integrations/linear/validate` 엔드포인트 동작
- 유효한 key+teamId → `valid: true` + team_name 반환
- 잘못된 key → `valid: false` + 에러 메시지
- 존재하지 않는 team_id → `valid: false` + 에러 메시지
- 5초 타임아웃 처리

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-22 | [api] Linear validate endpoint | ✅ | `POST /api/v1/integrations/linear/validate` 구현, 5초 타임아웃, team_name/error 응답 |