---
title: Linear 실시간 연동 가이드 (딜리버리 콘솔)
category: guide
status: needs-revision
last_updated: 2026-07-22
related:
  - scripts/linear_watcher.py
  - clickeye-web/src/app/(dashboard)/settings/linear
  - docs/spec/run_guide.md
  - docs/clickeye-product-guide.md
---

# Linear 실시간 연동 가이드

클라우드 콘솔에서 인게이지먼트를 생성하고, Linear 자격증명을 저장한 후, 로컬 Claude Code가 Linear 이슈를 감지해 자동 개발을 트리거하기까지의 완전 가이드입니다.

> 이 문서는 **딜리버리 콘솔을 사용하는 엔드유저**용입니다. ClickEye 서비스 자체를 운영하는 관리자 절차(webhook_server.py + ngrok)는 [run_guide.md](../spec/run_guide.md)를 참조하세요.

---

## 전체 흐름 한눈에 보기

```
[ClickEye 콘솔] 인게이지먼트 생성
         │
         ▼
[설정 페이지] /settings/linear → 자격증명 저장
         │
         ▼
[콘솔 프로젝트] "AI 초안 생성" → Linear 이슈 자동 등록
         │                      (Queued 상태)
         ▼
[로컬 PC] webhook 감지 또는 폴링
         │ (linear_watcher.py)
         ▼
[로컬 Claude Code] auto_dev_pipeline.sh 자동 실행
         │
         ▼
[Linear] 상태 자동 전이: DayQueued → In Progress → Done
```

---

## Step 1. Linear 자격증명 준비

콘솔에서 자격증명을 저장하기 전에 미리 준비하세요.

### 1-1. Linear API 키 발급

1. <https://linear.app/settings/api> 접속
2. **Personal API keys → Create key** 클릭
3. 이름 예: `ClickEye`, 권한: **Full access** 또는 최소 `issues:write`, `webhooks:write`
4. 발급된 키 복사 (`lin_api_...` 형식)

### 1-2. Team ID 확인

1. Linear 앱 → 좌측 사이드바에서 팀을 우클릭 → **Copy Team ID**  
   또는 URL `https://linear.app/{workspace}/team/{TEAM_ID}/issues`에서 확인

---

## Step 2. ClickEye 콘솔에서 자격증명 저장

1. ClickEye 콘솔 (<http://localhost:3000>) 접속
2. 우상단 **Settings** → **Linear** 탭
3. 다음 항목을 입력합니다.

   | 필드 | 설명 | 필수 |
   |------|------|------|
   | Linear API Key | Step 1-1에서 발급한 `lin_api_...` | ✅ |
   | Team ID | Step 1-2에서 확인한 팀 ID | ✅ |
   | Webhook Secret | 로컬 webhook 서명 검증용 (선택) | — |

4. **저장** 버튼 클릭 (Fernet 암호화로 보안 저장됨)

> **보안 팁**: Webhook Secret는 강력한 임의 문자열 생성:  
> `openssl rand -hex 32`

---

## Step 3. 인게이지먼트 생성 및 Linear 이슈 등록

1. ClickEye 콘솔 → **Projects** → 프로젝트 선택 → **Delivery**
2. **[+ 새 인게이지먼트]** 클릭
3. 요구사항 입력 + AI Team 프로필 선택
4. **[AI 초안 생성]** 클릭 → 서브태스크 초안 생성 (자동)
5. 초안 검토 후 **[작업 요청]** 클릭
   - 콘솔이 저장된 Linear 자격증명으로 이슈 자동 등록
   - 상태: `Queued` (또는 `DayQueued`, `NightQueued`)
6. 화면 하단에 등록된 이슈 ID (예: `CE-123`) 목록 표시

### 자격증명 미저장 시

`Linear 자격증명이 필요합니다` 안내 배너 표시 → Step 2로 돌아가 저장 후 재시도

---

## Step 4. 로컬 claude Code 설정

### 4-1. 프로젝트 디렉토리 준비

콘솔에서 "AI 초안 생성" 후, 시스템이 로컬용 설정을 자동으로 제공합니다.

또는 수동으로:
```bash
# 선택: 초기 설정 파일 다운로드 (필요 시)
# 콘솔 → Projects → [projectId] → [다운로드] → 설정 패키지
```

### 4-2. .env 파일 설정

로컬 프로젝트 루트에 `.env` 파일 생성:

```bash
# 필수
LINEAR_API_KEY=lin_api_xxxxxxxxxxxx
LINEAR_TEAM_ID=your-team-id
ANTHROPIC_API_KEY=sk-ant-xxxxx

# 선택 (webhook 또는 폴링 모드)
WEBHOOK_SECRET=your-secret
WEBHOOK_PORT=9876
TUNNEL_PROVIDER=cloudflare           # cloudflare | ngrok | polling
```

---

## Step 5. Linear 이슈 감지 설정

### 5-1. Webhook 모드 (권장)

> 웹훅이 포함된 프로젝트를 받았다면 이 단계 건너뛰기

```bash
cd /mnt/c/workspace/ClickEye  # ClickEye 루트 (또는 프로젝트 루트)

# webhook 서버 + ngrok 자동 설정 (진단, 기동, 검증)
bash scripts/webhook-doctor.sh
```

또는 수동:
```bash
# 터미널 1: webhook 서버 기동
nohup python3 scripts/webhook_server.py >> logs/webhook.log 2>&1 &

# 터미널 2: ngrok 터널 (또는 Cloudflare Tunnel 대체)
nohup ngrok http 9876 >> logs/ngrok.log 2>&1 &
```

### 5-2. 폴링 모드 (Fallback)

webhook 설정이 어려운 경우:

```bash
# 터미널에서 지속 실행 또는 백그라운드
python scripts/linear_watcher.py
# 또는
python scripts/linear_watcher.py &
```

30초 간격으로 Queued 이슈 감지

---

## Step 6. 자동 개발 파이프라인 실행

### 6-1. Claude Code 설정 로드

로컬 프로젝트에 `.claude/` 디렉토리가 있는지 확인:

```bash
ls -la .claude/
# agents/, skills/, CLAUDE.md 등이 포함되어야 함
```

### 6-2. Claude Code 시작

```bash
cd /프로젝트/루트
claude  # Claude Code 시작
```

또는 자동 트리거 설정:

```bash
# 백그라운드에서 Linear 이슈 감지 → 자동 실행
bash scripts/auto_dev_pipeline.sh --once
# 또는
bash scripts/auto_dev_pipeline.sh  # 연속 실행
```

---

## Step 7. 동작 확인

### 7-1. Linear 이슈 상태 변경

Step 3에서 등록된 이슈를 Linear에서 열고 상태를 **Queued** (또는 `DayQueued`)로 변경합니다.

### 7-2. 파이프라인 트리거 확인

**Webhook 모드**:
```
logs/webhook.log에서 확인:
[ClickEye] EVENT: CE-123 → Queued
[ClickEye] TRIGGER: auto_dev_pipeline.sh 실행
```

**폴링 모드**:
```
터미널에서 확인:
[watcher] 이슈 발견: CE-123 (Queued) → 파이프라인 실행
```

### 7-3. Claude Code 자동 실행 확인

로컬 Claude Code 또는 terminal 터미널에서:
```
[Claude] PLAN.md 생성 중...
[Claude] 코드 작성 시작
[Claude] 테스트 실행 중...
[Claude] PR 생성 완료 → CE-123 링크 추가
```

---

## 문제 해결

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| "Linear 이슈 생성 실패" 배너 | 자격증명 미저장/만료 | Settings → Linear에서 API 키 재저장 |
| 파이프라인이 실행 안 됨 | webhook 서버 또는 폴링 꺼짐 | `pgrep -f webhook_server.py` 확인, 또는 `python scripts/linear_watcher.py` 실행 |
| `LINEAR_TEAM_ID` 오류 | .env에 잘못된 팀 ID | Linear → 팀 우클릭 → Copy Team ID 확인 |
| Webhook Secret 불일치 | .env ≠ 콘솔 설정 | 양쪽 값 동일 확인 |
| ngrok URL 변경 | 무료 플랜 재시작 | 콘솔 Settings → Linear에서 새 URL 저장 |

---

## 보안 체크리스트

- [ ] LINEAR_API_KEY가 `.env`에만 있고, `.gitignore`에 등재되었는가?
- [ ] Webhook Secret이 강력한가? (`openssl rand -hex 32` 권장)
- [ ] webhook 서버가 localhost 수신만 하는가? (외부 노출 불필요)
- [ ] Cloudflare/ngrok 터널이 9876 포트만 노출하는가?

---

## 다음 단계

1. **인게이지먼트 모니터링** → 콘솔 Delivery 탭에서 진행 상황 실시간 확인
2. **PR 검토** → GitHub에서 자동 생성된 PR 확인
3. **결과 승인** → Linear 이슈 상태가 Done으로 자동 전이

---

## 관련 문서

- [ClickEye 딜리버리 제품 안내](../clickeye-product-guide.md)
- [서비스 구동 가이드 (운영자용)](../spec/run_guide.md)
- [개발 파이프라인](../clickeye-development-pipeline.md)
