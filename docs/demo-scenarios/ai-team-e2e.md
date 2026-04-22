# AI Team E2E 데모 시나리오

> **목표**: 위저드로 프로젝트 생성 → AI Team이 Linear에 이슈 자동 등록 → Linear 상태 변경 → 로컬 Claude가 감지하여 작업 시작까지 전 구간 실연.

---

## 준비물 체크리스트

| 항목 | 확인 방법 |
|------|----------|
| Anthropic API 키 (`ANTHROPIC_API_KEY`) | [console.anthropic.com](https://console.anthropic.com) |
| Linear API 키 (`LINEAR_API_KEY`) | [linear.app/settings/api](https://linear.app/settings/api) → Personal API keys |
| Linear 팀 ID (`LINEAR_TEAM_ID`) | Linear → 팀 설정 → 팀 URL의 UUID |
| cloudflared 설치 | `which cloudflared` 또는 `brew install cloudflare/cloudflare/cloudflared` |
| Claude Code CLI | `which claude` — 없으면 `npm install -g @anthropic-ai/claude-code` |
| Linear 워크스페이스에 `Queued` 상태 존재 | 팀 → 워크플로 → "Queued" 상태 추가 (없으면 직접 생성) |

---

## 1단계: 위저드 → 프로젝트 생성

1. `http://localhost:3000/solutions/new` 접속
2. **Step 1** — 회사명, 솔루션 설명 입력 → "솔루션 생성" 클릭
3. **Step 2** — AI 프로토타입 생성 대기 (20–40초)
4. **Step 3** — 프로토타입 카드 선택
5. **Step 4** → **Step 5** — PM 추천 확인 / 선택
6. **Step 6** — PM 구성 확인
7. **Step 7 (에이전트)** — 스킬 목록에서 **Linear** 반드시 체크
8. **Step 8 (플랫폼)** — Claude Code 선택
9. **Step 9 (환경변수)**
   - `ANTHROPIC_API_KEY` 입력 → ✅ 확인
   - `LINEAR_API_KEY` 입력 후 `LINEAR_TEAM_ID` 입력 → "Linear 검증 중..." → ✅ **Linear 유효성 확인**
   - 터널 방식: Cloudflare Tunnel 선택 (기본값)
10. **Step 10 (최종 확인)** — "이대로 진행" 클릭 → **SetupGuideModal 등장** (9단계 표시 확인)

> **스크린샷 포인트**: Step 9 Linear ✅ 상태 + Step 10 SetupGuideModal 9단계 표시

---

## 2단계: ZIP → 로컬 설정

SetupGuideModal 단계를 따라 진행하거나 아래를 직접 실행:

```bash
# 1. ZIP 다운로드 (프로젝트 상세 페이지 → "ZIP 다운로드" 버튼 또는 모달 링크)
# 2. 압축 해제
unzip <project-name>.zip -d my-project && cd my-project

# 3. .env 파일 작성
cp .env.example .env
# 편집기로 .env 열어서 ANTHROPIC_API_KEY, LINEAR_API_KEY, LINEAR_TEAM_ID 입력
```

**예상 ZIP 구조**:
```
my-project/
├── .claude/
│   └── CLAUDE.md
├── scripts/
│   ├── setup-tunnel.sh       # cloudflared 설치 + 터널 실행
│   ├── start-webhook.sh      # 로컬 webhook 서버 실행
│   └── webhook_server.py     # Linear webhook 수신 → claude 트리거
├── docs/
│   └── webhook/
│       └── WEBHOOK_SETUP.md
└── .env.example
```

---

## 3단계: 터널 + Webhook 서버 기동

```bash
# 터미널 A — 터널 실행
bash scripts/setup-tunnel.sh
# 출력 예시: https://abc-123-xyz.trycloudflare.com
```

> **스크린샷 포인트**: 터널 URL 출력 확인 (`https://xxx.trycloudflare.com`)

```bash
# 터미널 B — webhook 서버 실행
bash scripts/start-webhook.sh
# 출력 예시: Webhook server listening on port 9876
```

---

## 4단계: ClickEye Linear 설정 등록

1. `http://localhost:3000/settings/linear` 접속
2. 아래 항목 입력:
   - **Linear API 키**: 이미 자동 저장되어 있음 (마스킹 표시 확인) — tunnel URL만 추가 입력
   - **Linear 팀 ID**: 이미 저장됨
   - **Tunnel URL**: 터미널 A에서 출력된 `https://xxx.trycloudflare.com`
   - **Webhook Secret**: 빈칸 (선택)
3. "저장" 클릭 → 응답에 `linear_webhook_id` 포함 확인 (웹훅 자동 등록)

---

## 5단계: 프리플라이트 확인

`http://localhost:3000/projects/<project-id>` 접속

**Linear 연동 준비 상태** 카드에서 4개 항목 모두 ✅ 확인:
- ✅ 자격증명 저장됨 (팀명 표시)
- ✅ 터널 URL 등록됨
- ✅ 터널 응답 확인됨
- ✅ Linear Webhook 등록됨

> **스크린샷 포인트**: 프리플라이트 카드 4개 모두 ✅

---

## 6단계: AI Team → Linear 이슈 자동 생성

1. 프로젝트 상세 → "AI Team 시작하기" 버튼 클릭
2. `http://localhost:3000/projects/<id>/ai-team` 접속
3. "새 작업 요청" 클릭 → 세션 생성
4. 작업 설명 입력 후 "AI 초안 생성" 클릭
5. 생성 완료 후 자동으로 Linear push 진행 (30초 ~ 2분)
6. UI에 Linear 이슈 URL 링크가 표시됨을 확인

> **스크린샷 포인트**: AI Team UI에 Linear 이슈 URL 카드 표시

**Linear 웹 확인**:
- [linear.app](https://linear.app) → 팀 → 이슈 → `[ai-team]` 라벨이 붙은 이슈 2개 이상 확인

---

## 7단계: Linear → 로컬 Claude 트리거 (핵심)

1. Linear 웹에서 생성된 이슈 하나 클릭
2. 상태를 → **`Queued`** 로 변경

**터미널 B (webhook 서버) 확인**:
```
[WEBHOOK] POST /webhook/linear state=Queued issue=XXX-42 "이슈 제목"
TRIGGER: XXX-42 — '이슈 제목'
Running: claude -p "..."
```

**Claude 프로세스 확인**:
```bash
ps aux | grep claude
# claude -p "..." 프로세스가 실행 중이어야 함
```

> **스크린샷 포인트**: webhook 로그 + claude 프로세스 실행 확인

**중복 방지 확인** (동일 이슈를 한 번 더 수정):
```
[WEBHOOK] SKIP: XXX-42 — 이미 실행 중
```

---

## 트러블슈팅 맵

| 증상 | 원인 | 해결 |
|------|------|------|
| Linear ✅ 인데 `linear_webhook_id` 없음 | tunnel_url 미등록 상태에서 저장 | `/settings/linear`에서 tunnel URL 추가 후 재저장 |
| 터널 응답 ❌ | cloudflared 미실행 | `bash scripts/setup-tunnel.sh` 재실행 |
| Queued로 바꿔도 webhook 로그 없음 | webhook 서버 미실행 or 포트 불일치 | `bash scripts/start-webhook.sh` 재실행; `netstat -tlnp | grep 9876` 확인 |
| webhook 수신 됐지만 Claude 안 뜸 | `ANTHROPIC_API_KEY` 미설정 or Claude CLI 없음 | `.env` 확인; `which claude` 확인 |
| Linear 팀에 `Queued` 상태 없음 | 커스텀 상태 미생성 | Linear → 팀 → 워크플로 → 상태 추가 (이름: `Queued`) |
| AI Team push 실패 | Linear 자격증명 만료 or 팀 ID 오류 | `/settings/linear`에서 키 재저장 + 팀 ID 확인 |
| `curl {tunnel}/health` 404 | webhook_server.py에 `/health` 엔드포인트 없음 | `scripts/webhook_server.py` 업데이트 확인 |

**빠른 디버그 명령어**:
```bash
# tunnel 응답 확인
curl -I https://xxx.trycloudflare.com/health

# webhook 서버 포트 확인
netstat -tlnp | grep 9876

# Linear webhook 목록 조회 (API 키 필요)
curl -H "Authorization: Bearer $LINEAR_API_KEY" \
  -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ webhooks { nodes { id url enabled } } }"}'
```

---

## E2E 체크리스트 (최종 검증)

### 환경 준비
- [ ] `clickeye-api` 실행 중 (localhost:8000)
- [ ] `clickeye-web` 실행 중 (localhost:3000)
- [ ] cloudflared 설치됨 (`which cloudflared`)
- [ ] Claude Code CLI 설치됨 (`which claude`)
- [ ] Linear 워크스페이스에 `Queued` 상태 존재

### 위저드 → 프로젝트 생성
- [ ] Step 7에서 Linear 스킬 선택
- [ ] Step 9에서 Linear ✅ 유효성 표시
- [ ] Step 10 SetupGuideModal **9단계** 표시 확인

### ZIP → 로컬 설정
- [ ] ZIP 다운로드 성공
- [ ] `scripts/webhook_server.py`, `scripts/setup-tunnel.sh`, `scripts/start-webhook.sh` 포함
- [ ] `.env` 키 작성 완료
- [ ] `bash scripts/setup-tunnel.sh` → `https://xxx.trycloudflare.com` 출력
- [ ] `/settings/linear`에서 tunnel URL 저장 → `linear_webhook_id` 반환 확인
- [ ] `bash scripts/start-webhook.sh` → 포트 9876 Listening

### 프리플라이트
- [ ] `/projects/:id` 프리플라이트 카드 4개 모두 ✅
- [ ] 터널 끄면 "터널 응답 확인됨" 만 ❌로 변경됨 (선택 확인)

### AI Team → Linear
- [ ] `/projects/:id/ai-team` 세션 생성
- [ ] "AI 초안 생성" → Linear push → 이슈 2개+ 생성 확인
- [ ] UI에 Linear 이슈 URL 링크 표시

### Linear → 로컬 Claude 트리거 (핵심)
- [ ] 이슈 상태 → `Queued` 변경
- [ ] webhook 로그: `TRIGGER: XXX-42 — '...'` 출력
- [ ] `claude -p "..."` 프로세스 실행 확인 (`ps aux | grep claude`)
- [ ] 동일 이슈 재변경 시 `SKIP: ... 이미 실행 중` 로그
