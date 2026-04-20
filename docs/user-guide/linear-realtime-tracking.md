# Linear 실시간 연동 가이드

ZIP 다운로드부터 Local Claude Code가 Linear 이슈를 실시간으로 감지해 자동 개발을 트리거하기까지, 처음부터 끝까지 따라하는 가이드입니다.

---

## 전체 흐름 한눈에 보기

```
[24SevenClaw 위저드] → ZIP 다운로드
         │
         ▼
[설정 페이지] Linear 자격증명 저장
         │
         ▼
[AI Team] "첫 작업 요청하기" + "AI 초안 생성"
         │ ← 서버가 사용자 Linear에 이슈 자동 등록
         ▼
[로컬 PC] bash scripts/setup-tunnel.sh     ← 터널 기동 (선택)
         │ 또는
         │   python scripts/linear_watcher.py  ← 폴링 모드
         ▼
[Linear] 이슈 상태 → Queued 변경
         │
         ▼
[로컬 Claude Code] 자동 개발 파이프라인 실행
```

---

## Step 1. 위저드에서 프로젝트 생성 & ZIP 다운로드

1. 24SevenClaw 웹(<https://app.24sevenclaw.com>)에 로그인합니다.
2. **새 솔루션 만들기** → 7-Step 위저드를 완료합니다.
   - **Step 8 (환경 변수)** 에서 Linear 스킬을 사용할 경우 터널 방식을 선택하세요.
     | 선택지 | 비용 | URL 고정 여부 | 권장 대상 |
     |--------|------|--------------|----------|
     | **Cloudflare Tunnel** (기본) | 무료 | ✅ 정적 | 대부분의 사용자 |
     | ngrok | 유료 $8/월 고정 / 무료 임시 | ⚠️ 재시작 시 변경 | ngrok 계정 보유 사용자 |
     | 폴링 모드 | 무료 | — | 터널 설정이 어려운 경우 |
3. **ZIP 다운로드** 버튼을 클릭해 `{project-name}.zip`을 받습니다.
4. 압축을 해제합니다.

```bash
unzip your-project.zip -d my-project
cd my-project
```

---

## Step 2. Linear 자격증명 저장

24SevenClaw가 사용자 본인의 Linear 워크스페이스에 이슈를 등록하려면 API 키가 필요합니다.  
키는 **Fernet 암호화**로 서버에 안전하게 저장되며, 사용자가 명시적으로 저장한 경우에만 사용됩니다.

### 2-1. Linear API 키 발급

1. <https://linear.app/settings/api> 접속
2. **Personal API keys → Create key** 클릭
3. 이름 예: `24SevenClaw`, 권한: **Full access** 또는 최소 `issues:write`, `webhooks:write`
4. 발급된 키를 복사해 둡니다 (`lin_api_...` 형식).

### 2-2. Team ID 확인

1. Linear 앱 → 좌측 사이드바에서 팀을 우클릭 → **Copy Team ID**  
   또는 URL `https://linear.app/{workspace}/team/{TEAM_ID}/issues`에서 확인

### 2-3. 24SevenClaw 설정 페이지에서 저장

1. <https://app.24sevenclaw.com/settings/linear> 접속
2. 다음 항목을 입력합니다.

   | 필드 | 설명 | 필수 |
   |------|------|------|
   | Linear API Key | `lin_api_...` | ✅ |
   | Team ID | 이슈를 등록할 팀 | ✅ |
   | Webhook Secret | 로컬 webhook 서버 HMAC 검증용 임의 문자열 | 선택 |
   | Tunnel URL | `setup-tunnel.sh` 실행 후 발급되는 공개 URL | 선택 |

3. **저장** 버튼을 클릭합니다.
   - Tunnel URL이 입력된 경우, 서버가 자동으로 사용자 Linear 워크스페이스에 **Webhook을 등록**합니다.

> **보안 팁**: Webhook Secret는 `openssl rand -hex 32`로 강력한 무작위 문자열을 생성해 사용하세요.

---

## Step 3. "첫 작업 요청하기" → Linear 이슈 자동 등록

1. 24SevenClaw → 해당 프로젝트 → **AI Team** 탭으로 이동합니다.
2. **첫 작업 요청하기** 버튼을 클릭해 세션을 생성합니다.
3. 세션이 `assigned` 상태가 되면 **AI 초안 생성** 버튼이 활성화됩니다.
4. **AI 초안 생성** 클릭 → 두 가지 작업이 자동으로 순서대로 실행됩니다.
   - ① AI가 작업을 분석해 서브태스크 초안을 생성합니다.
   - ② 서버가 저장된 API 키로 Linear에 이슈를 등록합니다.
5. 화면 하단에 등록된 이슈 ID (예: `24S-123`) 목록이 표시됩니다.

### 자격증명 미저장 시

자격증명이 없으면 `설정 페이지에서 Linear 자격증명을 등록하세요` 안내 배너가 표시됩니다.  
[Step 2](#step-2-linear-자격증명-저장)로 돌아가 저장 후 다시 시도하세요.

---

## Step 4. 로컬 환경 설정 (ZIP 기반)

압축 해제한 프로젝트 디렉토리에서 `.env` 파일을 편집합니다.

```bash
# .env 최소 설정 예시
LINEAR_API_KEY=lin_api_xxxxxxxxxxxx
LINEAR_TEAM_ID=your-team-id
WEBHOOK_SECRET=your-webhook-secret   # Step 2와 동일한 값
WEBHOOK_PORT=9876
TUNNEL_PROVIDER=cloudflare           # cloudflare | ngrok | polling
```

---

## Step 5. 터널 기동 (Cloudflare Tunnel 추천)

> 폴링 모드를 선택한 경우 이 단계를 건너뛰고 [Step 6b](#step-6b-폴링-모드-fallback)로 이동하세요.

### Step 5a. Cloudflare Tunnel (무료, 정적 URL)

```bash
bash scripts/setup-tunnel.sh
```

스크립트가 자동으로:
1. `cloudflared`가 없으면 설치합니다 (Homebrew / apt / snap).
2. 터널을 기동하고 `https://xxxx.trycloudflare.com` 형식의 URL을 발급합니다.
3. `.env`의 `WEBHOOK_PUBLIC_URL`을 업데이트합니다.

```
☁️  Cloudflare Tunnel 설정 중...
   터널 기동 중 (포트 9876)...

   ✅ Cloudflare Tunnel URL: https://sample-example-abc.trycloudflare.com
   .env의 WEBHOOK_PUBLIC_URL을 업데이트했습니다.
```

**발급된 URL을 24SevenClaw 설정 페이지 → Tunnel URL 필드에 저장하세요.**  
저장 즉시 서버가 사용자 Linear에 Webhook을 자동 등록합니다.

> ⚠️ 이 터미널 창을 닫으면 터널이 종료됩니다. 별도 터미널에서 유지하거나 `nohup`으로 백그라운드 실행하세요.

### Step 5b. ngrok (유료 고정 URL / 무료 임시 URL)

```bash
TUNNEL_PROVIDER=ngrok bash scripts/setup-tunnel.sh
```

ngrok이 설치되어 있지 않으면 설치 안내가 표시됩니다.  
`NGROK_AUTH_TOKEN`을 `.env`에 설정하면 자동으로 인증합니다.

> ⚠️ 무료 플랜은 재시작마다 URL이 변경됩니다. URL 변경 시 설정 페이지에서 다시 저장해야 합니다.

---

## Step 6. 로컬 Webhook 서버 기동

새 터미널 창에서 실행합니다.

```bash
bash scripts/start-webhook.sh
```

```
🚀 Webhook 서버 시작 중...
   포트: 9876
   Linear 서명 검증: 활성화
   서버 준비 완료
```

### 헬스 체크

```bash
curl http://localhost:9876/health
# {"status":"ok","port":9876}
```

### Step 6b. 폴링 모드 (Fallback)

터널을 구성하지 않거나 Webhook 서버를 실행하기 어려운 경우, 30초 폴링으로 동일한 효과를 얻을 수 있습니다.

```bash
python scripts/linear_watcher.py
```

또는 백그라운드 실행:

```bash
python scripts/linear_watcher.py &
```

---

## Step 7. 동작 확인

### 7-1. Linear에서 이슈 상태 변경

1. [Step 3](#step-3-첫-작업-요청하기--linear-이슈-자동-등록)에서 등록된 이슈를 Linear에서 엽니다.
2. 상태를 **Queued** (또는 `DayQueued`, `NightQueued`)로 변경합니다.

### 7-2. 로컬 자동 개발 파이프라인 트리거 확인

- **Webhook 모드**: `start-webhook.sh` 터미널에서 다음 로그를 확인합니다.
  ```
  [24SevenClaw] Linear webhook 수신: 이슈 ABC-123 → Queued
  [24SevenClaw] 자동 개발 파이프라인 트리거
  ```
- **폴링 모드**: `linear_watcher.py` 터미널에서 확인합니다.
  ```
  [watcher] 이슈 발견: ABC-123 (Queued) → 파이프라인 실행
  ```

두 경우 모두 `.claude/` 또는 로컬 `claude` 명령이 자동으로 개발을 시작합니다.

---

## 문제 해결

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| "Linear 이슈 생성 실패" 배너 표시 | 자격증명 미저장 또는 만료 | 설정 페이지에서 API 키 재저장 |
| Webhook 수신 없음 | Tunnel URL 불일치 | 설정 페이지에서 현재 Tunnel URL 재저장 |
| 서명 검증 실패 (401) | Webhook Secret 불일치 | `.env`와 설정 페이지의 Secret 동일 여부 확인 |
| `cloudflared` 설치 실패 | 인터넷 연결 또는 권한 문제 | 수동 설치: <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/> |
| ngrok URL 변경됨 | 무료 플랜 재시작 | 설정 페이지에서 새 URL 재저장 또는 유료 플랜 사용 |
| 폴링이 이슈를 감지 못함 | `LINEAR_TEAM_ID` 오류 | `.env`의 TEAM_ID가 올바른지 Linear에서 확인 |

---

## 보안 체크리스트

- [ ] Linear API 키가 `.env`에만 있고, 버전 관리에 커밋되지 않았는가? (`.gitignore` 확인)
- [ ] Webhook Secret이 충분히 강력한가? (`openssl rand -hex 32` 권장)
- [ ] `start-webhook.sh`가 로컬 호스트에서만 수신하는가? (외부 포트 9876 노출 불필요)
- [ ] Cloudflare/ngrok 터널이 포트 9876만 노출하는가?

---

## 관련 문서

- [Webhook 상세 설정 가이드](../webhook/WEBHOOK_SETUP.md)
- [24SevenClaw 아키텍처 개요](../architecture-overview.md)
- [AI 파이프라인 가이드](../pipeline-guide.md)
