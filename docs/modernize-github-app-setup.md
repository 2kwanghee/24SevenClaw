# ClickEye Modernize — GitHub App 등록 가이드

> 이 문서는 ClickEye Modernize 파이프라인(MVP-2-A) 을 활성화하기 위한 **GitHub App 등록 절차** 를 정리합니다.
> 코드는 이미 M3 에서 작성되었으나 GitHub 측 App 이 등록되어 있어야 endpoint 가 503 이 아닌 정상 응답합니다.

## 사전 조건

- ClickEye 백엔드에 관리자 권한
- GitHub 조직(또는 개인) 계정 — App 의 owner 가 됨
- 외부 도달 가능한 ClickEye 백엔드 URL (개발 단계는 ngrok / cloudflared 권장)

## 1. GitHub 에 App 생성

GitHub → Settings → Developer settings → GitHub Apps → **New GitHub App**

| 필드 | 값 |
|---|---|
| GitHub App name | `ClickEye Modernize` (또는 환경별 suffix — `-dev` / `-staging`) |
| Homepage URL | `https://<your-clickeye-domain>` |
| Callback URL | `https://<your-clickeye-domain>/api/v1/integrations/github/app/callback` |
| Request user authorization (OAuth) during installation | ☑ 체크 |
| Setup URL (after install) | (Callback URL 과 동일하게 두면 설치 직후 자동 콜백) |
| Webhook URL | `https://<your-clickeye-domain>/api/v1/integrations/github/app/webhook` |
| Webhook secret | 무작위 32+ 문자열 (`openssl rand -hex 32`) — `GITHUB_APP_WEBHOOK_SECRET` 으로 저장 |

### Repository permissions (최소 권한)

| Scope | 권한 |
|---|---|
| Contents | Read-only |
| Metadata | Read-only (기본) |
| Pull requests | Read-only (MVP-2 — MVP-3 의 자동 PR 생성 시 Write 로 승격) |

### User permissions

| Scope | 권한 |
|---|---|
| Email addresses | Read-only |

### Subscribe to events

- ☑ Installation
- ☑ Installation repositories
- ☑ Repository (선택 — MVP-3 에서 push→재분석 시)

저장 후 **App ID** 와 **slug** 를 확인합니다 (URL: `https://github.com/settings/apps/<slug>`).

## 2. Private key 발급

App 상세 페이지 → "Private keys" → **Generate a private key** → `.pem` 파일 다운로드.

> ⚠️ PEM 은 즉시 사용 환경변수로 옮기고 디스크에서 제거. ClickEye 서버는 PEM 을 환경변수로만 받아 메모리에 보관.

## 3. ClickEye 환경변수 설정

`clickeye-api/.env` 에 다음 값 입력:

```
FEATURE_MODERNIZE_ENABLED=true

GITHUB_APP_ID=<App ID 숫자>
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
... (다음 줄 그대로)
-----END RSA PRIVATE KEY-----"
GITHUB_APP_CLIENT_ID=<App Client ID — App 페이지에서 확인>
GITHUB_APP_CLIENT_SECRET=<App Client Secret — Generate a new client secret>
GITHUB_APP_WEBHOOK_SECRET=<위 1번에서 생성한 임의 문자열>
GITHUB_APP_SLUG=<App URL 의 slug — 예: clickeye-modernize-dev>

FRONTEND_URL=https://<your-clickeye-web-domain>
```

`.env` 의 멀티라인 PEM 은 `python-dotenv` 가 따옴표로 감싼 형태를 지원합니다. 따옴표 안에서 줄바꿈을 그대로 사용하세요.

`clickeye-web/.env.local` 에:

```
NEXT_PUBLIC_FEATURE_MODERNIZE_ENABLED=true
```

## 4. 동작 검증

```bash
# 백엔드 재시작 후
curl -i https://<your-clickeye-domain>/api/v1/integrations/github/app/install-url \
  -H "Authorization: Bearer <user-jwt>"
```

응답 예시:

```json
{
  "install_url": "https://github.com/apps/clickeye-modernize-dev/installations/new",
  "state": "<JWT — 10 분 만료>"
}
```

`install_url` 을 브라우저에서 열어 GitHub 의 설치 UI 진행 → ClickEye `/callback` 으로 redirect → frontend `/solutions/modernize/connected?installation_id=...` 페이지 (M4 에서 구현) 로 이동.

## 5. webhook 검증

GitHub App 페이지 → **Advanced** → **Recent Deliveries** 에서 webhook payload 와 응답을 확인. 정상 응답: `204 No Content`. 401 이면 `GITHUB_APP_WEBHOOK_SECRET` 불일치.

## 6. 베타 / 화이트리스트 운영

- `FEATURE_MODERNIZE_ENABLED=false` 인 환경에서는 모든 신규 endpoint 가 404 — 일반 사용자에게 노출되지 않음
- 베타 사용자에게는 환경별 별도 App + flag=true 적용

## 트러블슈팅

| 증상 | 원인 / 조치 |
|---|---|
| `/install-url` 가 503 | `is_configured()` False — 6 env 값 모두 채웠는지 확인 |
| `/install-url` 가 404 | `FEATURE_MODERNIZE_ENABLED=false` — true 로 변경 후 재시작 |
| `/callback` 가 400 "state 만료" | 사용자가 GitHub 설치 화면에 10 분 이상 머무름 — 재시도 |
| `/webhook` 가 401 | GitHub App 의 webhook secret 과 `GITHUB_APP_WEBHOOK_SECRET` 불일치 |
| 신규 installation 이 DB 에 안 생김 | callback 이 실제로 호출되었는지 GitHub App **Recent Deliveries** 확인 |

## 다음 단계 (M4)

- `/solutions/modernize/connected` 프론트엔드 페이지 + 설치 배지
- `/modernize/installations` / `/modernize/installations/{id}/repos` 엔드포인트로 repo 목록 노출
- step-modernize-repo-connect / step-modernize-repo-select UI
