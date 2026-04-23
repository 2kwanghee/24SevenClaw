# Telegram 봇 설정 가이드

## 1. Bot 생성 (BotFather)

1. Telegram 앱에서 **[@BotFather](https://t.me/BotFather)** 검색 후 Start
2. `/newbot` 명령 입력
3. 봇 이름 입력 (예: `ClickEye Alert Bot`)
4. 봇 사용자명 입력 — `_bot`으로 끝나야 함 (예: `clickeye_alert_bot`)
5. 발급된 토큰 복사 — 형식: `1234567890:ABCdef...`

## 2. Chat ID 확인

### 개인 채팅
1. 생성한 봇에게 임의 메시지 전송
2. 아래 URL 브라우저에서 열기:
   ```
   https://api.telegram.org/bot<토큰>/getUpdates
   ```
3. 응답 JSON에서 `result[0].message.chat.id` 값 복사 (양수 숫자)

### 채널 알림
1. 채널에 봇을 관리자로 추가
2. 채널에 메시지 전송 후 위 URL 조회
3. `chat.id`는 음수값 (예: `-1001234567890`)

## 3. .env 설정

```
TELEGRAM_BOT_TOKEN=1234567890:ABCdef여기에토큰
TELEGRAM_CHAT_ID=여기에Chat_ID
```

## 문제 해결

- `401 Unauthorized`: 토큰 오류 → BotFather에서 재발급
- `400 Bad Request`: Chat ID 확인 — 봇이 대화 시작했는지 확인
- 채널 알림 없음: 봇이 채널 관리자인지 확인
