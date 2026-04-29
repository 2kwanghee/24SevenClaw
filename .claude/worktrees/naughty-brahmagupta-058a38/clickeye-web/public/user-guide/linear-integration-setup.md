---
title: Linear 연동 설정
description: Linear API 키 등록, Webhook 설정, DayQueued 플로우까지 단계별로 안내합니다.
order: 5
---

# Linear 연동 설정

ClickEye의 AI Team이 생성한 서브태스크를 Linear 이슈로 자동 등록하고, 이슈 상태가 `Queued`로 변경되면 로컬 Claude Code가 자동으로 개발을 시작하는 전체 흐름을 설정합니다.

---

## 전체 흐름

```
[ClickEye AI Team] AI 초안 생성
         │ → Linear 이슈 자동 등록
         ▼
[Linear] 이슈 상태 → Queued 변경
         │
         ▼
[로컬 PC] Webhook 수신 또는 폴링
         │
         ▼
[Claude Code] 자동 개발 파이프라인 실행
```

---

## Step 1 — Linear API 키 발급

1. [https://linear.app/settings/api](https://linear.app/settings/api) 접속
2. **Personal API keys → Create key** 클릭
3. 이름 입력 (예: `ClickEye`)
4. 권한: **Full access** 또는 최소 `issues:write`
5. 발급된 키(`lin_api_...`)를 복사합니다

---

## Step 2 — Linear 팀 ID 확인

Linear의 **팀 ID**가 필요합니다. 다음 방법으로 확인하세요:

- Linear 앱 → 좌측 사이드바에서 팀 이름 우클릭 → **Copy Team ID**
- 또는 URL에서 확인: `https://linear.app/{workspace}/team/{TEAM_ID}/issues`

---

## Step 3 — ClickEye 설정 페이지에서 저장

1. [ClickEye 설정 → Linear](https://app.24sevenclaw.com/settings/linear) 접속
2. 다음 항목을 입력합니다:

| 필드 | 설명 | 필수 |
|------|------|------|
| Linear API Key | `lin_api_...` 형식 | ✅ |
| Team ID | 이슈를 생성할 팀의 UUID | ✅ |
| Webhook Secret | HMAC 서명 검증용 임의 문자열 | ⬜ |
| Tunnel URL | 로컬 webhook 서버의 공개 URL | ⬜ |

3. **저장** 클릭

> **보안 팁**: Webhook Secret은 `openssl rand -hex 32`로 생성한 강력한 무작위 문자열을 사용하세요.

> **Tunnel URL 저장 시**: 서버가 자동으로 Linear 워크스페이스에 Webhook을 등록합니다.

---

## Step 4 — 위저드에서 Linear 스킬 선택 (ZIP 생성 시)

7-Step 위저드 Step 5(에이전트 & 스킬)에서 **Linear** 스킬을 선택하면 ZIP에 Linear 연동 스크립트가 포함됩니다.

ZIP 압축 해제 후 `.env` 파일에 다음 값이 필요합니다:

```bash
LINEAR_API_KEY=lin_api_xxxxxxxxxxxx
LINEAR_TEAM_ID=your-team-uuid
WEBHOOK_SECRET=your-webhook-secret
TUNNEL_PROVIDER=cloudflare   # cloudflare | ngrok | polling
```

---

## Step 5 — 실시간 트래킹 방식 선택

### 방식 A: Cloudflare Tunnel (권장)

무료이며 정적 URL을 제공합니다.

```bash
bash scripts/setup-tunnel.sh
```

스크립트 실행 시:
1. `cloudflared`가 자동으로 설치됩니다 (Homebrew / apt / snap)
2. 터널이 기동되고 `https://xxxx.trycloudflare.com` URL이 발급됩니다
3. `.env`의 `WEBHOOK_PUBLIC_URL`이 자동으로 업데이트됩니다

발급된 URL을 [ClickEye 설정 페이지](https://app.24sevenclaw.com/settings/linear)의 **Tunnel URL** 필드에 저장하세요.

> ⚠️ 이 터미널 창을 닫으면 터널이 종료됩니다. 백그라운드 실행: `nohup bash scripts/setup-tunnel.sh &`

### 방식 B: ngrok

```bash
TUNNEL_PROVIDER=ngrok bash scripts/setup-tunnel.sh
```

- 무료 플랜: 재시작마다 URL이 변경됩니다. URL 변경 시 설정 페이지에서 재저장 필요
- 유료 고정 URL: `NGROK_AUTH_TOKEN`을 `.env`에 설정하면 자동 인증됩니다

### 방식 C: 30초 폴링 (터널 없이)

Webhook 없이 30초마다 Linear를 폴링합니다. 터널 설정이 어려운 환경에 적합합니다.

```bash
python scripts/linear_watcher.py
```

백그라운드 실행:

```bash
python scripts/linear_watcher.py &
```

---

## Step 6 — 로컬 Webhook 서버 기동 (Cloudflare/ngrok 방식)

새 터미널에서 실행합니다:

```bash
bash scripts/start-webhook.sh
```

헬스 체크:

```bash
curl http://localhost:9876/health
# {"status":"ok","port":9876}
```

---

## Step 7 — DayQueued 플로우 확인

모든 설정이 완료되면 다음 플로우로 자동 개발이 트리거됩니다:

1. ClickEye AI Team → **AI 초안 생성** 클릭
2. Linear에 이슈가 자동 등록됩니다 (예: `24S-123`)
3. Linear에서 이슈 상태를 **Queued** (또는 `DayQueued`, `NightQueued`)로 변경합니다
4. 로컬 환경에서 파이프라인이 자동으로 실행됩니다:

   - **Webhook 모드**: `start-webhook.sh` 터미널에서 확인
     ```
     [ClickEye] Linear webhook 수신: 이슈 24S-123 → Queued
     [ClickEye] 자동 개발 파이프라인 트리거
     ```
   - **폴링 모드**: `linear_watcher.py` 터미널에서 확인
     ```
     [watcher] 이슈 발견: 24S-123 (Queued) → 파이프라인 실행
     ```

---

## 문제 해결

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| "Linear 자격증명이 없습니다" 배너 | API 키 미저장 | 설정 페이지에서 API 키 저장 |
| Linear 이슈 생성 실패 | API 키 만료 또는 권한 부족 | 새 키 발급 후 재저장 |
| Webhook 수신 없음 | Tunnel URL 불일치 | 설정 페이지에서 현재 Tunnel URL 재저장 |
| 서명 검증 실패 (401) | Webhook Secret 불일치 | `.env`와 설정 페이지의 Secret 동일 여부 확인 |
| `cloudflared` 설치 실패 | 인터넷 연결 또는 권한 문제 | [수동 설치 가이드](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) |
| ngrok URL 변경됨 | 무료 플랜 재시작 | 설정 페이지에서 새 URL 재저장 또는 유료 플랜 사용 |
| 폴링이 이슈를 감지 못함 | `LINEAR_TEAM_ID` 오류 | `.env`의 TEAM_ID가 올바른지 Linear에서 확인 |

---

## 보안 체크리스트

- [ ] Linear API 키가 `.env`에만 있고 Git에 커밋되지 않았는가? (`.gitignore` 확인)
- [ ] Webhook Secret이 충분히 강력한가? (`openssl rand -hex 32` 권장)
- [ ] `start-webhook.sh`가 로컬 호스트에서만 수신하는가? (포트 9876 외부 노출 불필요)
- [ ] Cloudflare/ngrok 터널이 포트 9876만 노출하는가?

---

## 관련 가이드

- [7-Step 솔루션 위저드](/guide/wizard-7-step) — 위저드에서 Linear 스킬 선택하기
- [AI Team 관리](/guide/ai-team-management) — AI 초안 생성 및 Linear 이슈 확인
