## 목표
M3 — GitHub App 인프라 + install/callback/webhook 엔드포인트.
사용자가 자신의 GitHub 계정/조직에 ClickEye GitHub App 을 설치하고, 그 installation 정보를 백엔드가 안전하게 수신·검증·영속하는 흐름. 실 코드 호출은 사용자가 GitHub 개발자 콘솔에서 App 등록 후 활성화.

## 비침습성 보장
- 기존 GitHub OAuth login (`auth.py`) 흐름 절대 미변경 — 별개 endpoint prefix 사용
- Feature flag `feature_modernize_enabled = False` 일 때 신규 endpoint 모두 404
- GitHub App settings (id/private_key/secret) 미설정 시 endpoint 503 + 명확한 에러
- 신규 라우터 1 개만 router.py 에 include 추가, 기존 라우터 영향 없음

## 변경 파일 목록

### 신규
- `clickeye-api/app/services/github_app_service.py` — JWT(RS256) 발급, installation token 발급, webhook 서명 검증, user-to-server OAuth code 교환
- `clickeye-api/app/schemas/github_app.py` — Pydantic 스키마 (Install URL / Installation / Webhook payload)
- `clickeye-api/app/api/v1/github_app.py` — 3 endpoint + Feature flag 가드
- `clickeye-api/tests/services/test_github_app_service.py` — JWT/서명/is_configured 단위 테스트
- `docs/modernize-github-app-setup.md` — App 등록 가이드 (사용자 측)

### 수정 (옵트인 분기)
- `clickeye-api/app/config.py` — GitHub App settings 6 필드 + frontend URL 추가 (default 비어있어 endpoint 비활성)
- `clickeye-api/app/dependencies.py` — `require_modernize_feature` 의존성 추가
- `clickeye-api/app/api/v1/router.py` — 신규 router include
- `clickeye-api/.env.example` — App 관련 env 추가 (모두 빈 값)

## 핵심 함수 시그니처

| 함수 | 시그니처 | 비고 |
|---|---|---|
| `is_configured()` | `() -> bool` | 6 settings 모두 비어있지 않은지 |
| `create_app_jwt()` | `() -> str` | iss=app_id, iat=now-60s, exp=now+9m, RS256 서명 |
| `get_installation_token(id)` | `async (int) -> dict` | `POST /app/installations/{id}/access_tokens` 호출, 1h 토큰 반환 |
| `verify_webhook_signature(payload, sig)` | `(bytes, str) -> bool` | HMAC-SHA256 with `github_app_webhook_secret` |
| `exchange_user_oauth_code(code)` | `async (str) -> dict` | user-to-server OAuth code → user token |
| `fetch_installation_meta(id)` | `async (int) -> dict` | App JWT 로 installation 상세 조회 |

## Endpoint 시그니처

| Method | Path | Auth | Body / Query | Response |
|---|---|---|---|---|
| GET | `/integrations/github/app/install-url` | user | — | `{install_url, state}` (state = 10분 만료 JWT) |
| GET | `/integrations/github/app/callback` | user + state | `?installation_id&setup_action&state&code?` | 302 → frontend `/modernize/connected?installation_id=...` |
| POST | `/integrations/github/app/webhook` | 서명 검증 | GitHub event payload | 204 |

webhook 처리 이벤트: `installation` (created/deleted/suspended/unsuspended), `installation_repositories` (added/removed)

## 구현 단계
1. config.py + .env.example 보강
2. dependencies.py — require_modernize_feature 추가
3. services/github_app_service.py 작성
4. schemas/github_app.py
5. api/v1/github_app.py + router 등록
6. 단위 테스트 (JWT, 서명, is_configured)
7. docs/modernize-github-app-setup.md 작성
8. ruff + mypy + pytest

## 비침습성 회귀 항목
- R-3 OpenAPI diff: 기존 endpoint 변경 0 — 신규 path 만 추가
- R-6 Feature flag OFF: `feature_modernize_enabled=false` 시 신규 endpoint 모두 404 (require_modernize_feature 의존성으로 보장)
- 기존 pytest: 신규 코드는 기존 흐름 import 안 함 — 영향 없음

## STATUS: APPROVED
