# Slack 봇 설정 가이드

## 1. Slack App 생성

1. [api.slack.com/apps](https://api.slack.com/apps) 접속 → **Create New App**
2. **From scratch** 선택
3. 앱 이름 입력 (예: `ClickEye`)
4. 워크스페이스 선택 후 **Create App**

## 2. Bot Token 발급

1. 좌측 메뉴 **OAuth & Permissions** 클릭
2. **Scopes → Bot Token Scopes** 에서 추가:
   - `chat:write` — 메시지 전송
   - `channels:read` — 채널 조회 (선택)
3. 상단 **Install to Workspace** 클릭 → 권한 승인
4. **Bot User OAuth Token** 복사 — 형식: `xoxb-...`

## 3. 채널에 봇 초대

1. Slack에서 알림 받을 채널 열기
2. 채널 설명 클릭 → **Integrations → Add an App**
3. 생성한 앱 추가

## 4. Channel ID 확인

- 채널 이름 클릭 → 하단 **Channel ID** 복사 (예: `C1234ABCD`)
- 또는 채널 이름 그대로 사용 (`#general` → `general`)

## 5. .env 설정

```
SLACK_BOT_TOKEN=xoxb-여기에토큰
SLACK_CHANNEL=C1234ABCD
```

## 문제 해결

- `not_in_channel`: 봇이 채널에 초대되지 않음
- `invalid_auth`: Bot Token 재확인 (`xoxb-` 접두사)
- 메시지 미수신: Scopes에 `chat:write` 추가됐는지 확인
