---
title: 서비스 실행 가이드 (운영자용)
category: guide
status: current
last_updated: 2026-07-30
related:
  - scripts/webhook_server.py
  - scripts/webhook_worker.py
  - scripts/clickeye_cron.txt
  - clickeye-infra/docker/Dockerfile.webhook
  - scripts/auto_dev_pipeline.sh
  - scripts/intake_refine.sh
  - scripts/intake_issue.sh
  - scripts/delivery_verify.sh
  - clickeye-api
  - clickeye-web
  - docs/clickeye-product-guide.md
---

# 서비스 실행 가이드

## 전제 조건

PostgreSQL, Redis를 Docker로 띄웁니다.

```bash
cd /mnt/c/workspace/ClickEye/clickeye-infra/docker

# DB + Redis 컨테이너 실행 (백그라운드)
docker compose up -d db redis

# 상태 확인
docker compose ps
# clickeye-db, clickeye-redis 모두 healthy 상태여야 정상
```

> API까지 컨테이너로 띄우려면 `--profile full` 옵션 추가:
> ```bash
> docker compose --profile full up -d
> ```

---

## 1단계: API 서버 실행

```bash
cd /mnt/c/workspace/ClickEye/clickeye-api

# 의존성 설치 (최초 1회)
uv sync

# DB 마이그레이션 적용 (pull 후 매번 필수 — 새 리비전 추가 시 기존 로컬 스키마와 불일치)
uv run python -m alembic upgrade head

# 마이그레이션 상태 확인 (미적용이 감지되면 위 명령 재실행)
docker exec clickeye-db psql -U clickeye -d clickeye -tAc "SELECT version_num FROM alembic_version"
uv run alembic heads
# 위 두 값이 다르면 마이그레이션 재적용 필수

# 시드 데이터 로딩 (PM 프로필 초기 데이터, 최초 1회)
uv run python scripts/seed_pm_data.py

# 인테이크 API 활성화 (기본 off — 없으면 /intake/* 전체 404)
# .env 또는 clickeye-api/.env 또는 clickeye-infra/managed/api.env 에 추가:
export FEATURE_INTAKE=true

# API 서버 실행 (--host 0.0.0.0: WSL2에서 Windows 브라우저 접근 허용)
uv run python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

**마이그레이션 미적용 시 증상**: 딜리버리 상세 진입 시 브라우저 콘솔에 `TypeError: Failed to fetch` 오류 → API 500 `sqlalchemy.exc.ProgrammingError: column llm_usage_ledger.session_id does not exist`

서버 기동 후 → **http://localhost:8000/docs** (Swagger UI)

---

## 2단계: 웹 프론트엔드 실행

```bash
cd /mnt/c/workspace/ClickEye/clickeye-web

# 의존성 설치 (최초 1회)
npm install

# 개발 서버 실행
npm run dev
```

브라우저 → **http://localhost:3000**

### ⚠ 프로덕션 빌드 시 주의 — 경로에 한글이 있으면 Turbopack이 패닉한다

작업 경로에 한글이 포함된 경우(예: `ClickEye-와이어프레임설계/`) `npm run build`가 실패한다.

```
thread 'tokio-runtime-worker' panicked at turbopack/crates/turbopack-core/src/ident.rs:354
start byte index 57 is not a char boundary; it is inside '계' (bytes 55..58)
FATAL: An unexpected Turbopack error occurred.
```

Turbopack이 에셋 식별자를 만들 때 경로 문자열을 **바이트 인덱스로 잘라** UTF-8 다중바이트
문자 중간을 침범해서 나는 버그다. 코드 문제가 아니며 특정 파일과 무관하게 여러 파일에서
동시에 터진다.

우회 방법 두 가지:

```bash
# 1) 웹팩으로 빌드 (dev 스크립트가 이미 --webpack 을 쓰는 이유)
npx next build --webpack

# 2) 또는 경로에 한글이 없는 위치로 체크아웃해서 빌드
```

`package.json`의 `build` 스크립트는 아직 Turbopack 기본값이다. 한글 경로에서 상시 작업한다면
`"build": "next build --webpack"` 으로 고정하는 것을 검토한다.

---

## 3단계: 자동화 파이프라인 기동

### 3-1. webhook 수신 컨테이너 시작 (Linear 이벤트 수신)

webhook 수신부는 **compose 서비스**(`webhook`)로 띄웁니다. 컨테이너는 HMAC 서명만 검증하고
검증된 이벤트를 Redis 큐(`clickeye:webhook:jobs`)에 적재만 하며(수신전용, `WEBHOOK_ENQUEUE_ONLY=true`),
실행은 하지 않습니다. `profiles: [full]`에 있으므로 기본 `up -d`에는 포함되지 않습니다.

```bash
cd /mnt/c/workspace/ClickEye/clickeye-infra/docker

# webhook 수신 컨테이너 기동 (redis 의존 — 함께 올라옵니다)
docker compose --profile full up -d webhook

# 상태 확인
docker compose ps webhook
# clickeye-webhook 이 healthy 상태여야 정상

# 정상 기동 확인 (컨테이너 포트가 호스트 9876 으로 퍼블리시됩니다)
curl -s http://127.0.0.1:9876/health
# 응답: {"status":"ok","dry_run":false,"enqueue_only":true} 이면 정상
```

> **WEBHOOK_SECRET 필수**: 수신전용 모드는 공개 노출부이므로 `WEBHOOK_SECRET`(Linear
> Settings→API→Webhooks 의 Signing Secret)이 비어 있으면 컨테이너가 기동을 거부합니다.
> 값은 `clickeye-infra/docker/.env` 또는 셸 환경에 두고 주입합니다.

### 3-1b. 호스트 실행 워커 시작 (큐 소비 → 파이프라인 실행)

큐에 적재된 job 을 꺼내(`BLPOP`) `auto_dev_pipeline.sh`를 호출하는 **호스트 프로세스**입니다.
파이프라인은 `git`·`claude` CLI·`uv`·`npm` 과 로컬 워크스페이스(시트·크리덴셜)를 쓰므로,
실행면은 컨테이너가 아닌 **호스트에 남깁니다**. 이 덕분에 인터넷에 노출되는 수신 컨테이너에는
토큰·git 크리덴셜을 두지 않습니다.

```bash
cd /mnt/c/workspace/ClickEye

# 사전 요구: redis 파이썬 패키지 (호스트에 미설치면 워커가 명확한 에러로 안내)
python3 -c "import redis" 2>/dev/null || pip install redis

# 상시 루프로 백그라운드 실행 (큐를 계속 소비)
nohup python3 scripts/webhook_worker.py >> logs/webhook-worker.log 2>&1 &
```

> `--once` 는 큐에서 1건만 처리하고 종료하는 cron 폴링용 모드입니다(빈 큐면 exit 0).
> 상시 워커의 watchdog 등록은 3-5(cron 정본 `scripts/clickeye_cron.txt`)를 참조합니다.
> 큐 키는 `clickeye:webhook:jobs`(Redis LIST), `REDIS_URL` 기본값은 `redis://localhost:6379/0`.

### 3-2. ngrok 터널 시작 (Linear → webhook 연결)

```bash
cd /mnt/c/workspace/ClickEye

# ngrok 실행
nohup ngrok http 9876 --log=logs/ngrok.log --log-format=logfmt >> /dev/null 2>&1 &

# 30초 후 public URL 확인
sleep 3 && curl -s http://127.0.0.1:4040/api/tunnels | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])"
```

> **중요**: ngrok 무료 플랜은 재시작마다 URL이 변경됩니다.
> URL이 바뀌면 아래 3-3 단계에서 Linear webhook을 반드시 갱신해야 합니다.

### 3-3. Linear Webhook URL 갱신

ngrok URL이 바뀐 경우:

1. Linear → **Settings → API → Webhooks** 접속
2. 기존 webhook 클릭 → URL 수정
3. `https://<ngrok-url>/webhook/linear` 로 교체
4. 저장 후 테스트: Linear에서 이슈 하나를 DayQueued로 변경 → `logs/webhook.log`에 `EVENT: ... DayQueued` 확인

### 3-4. 무인 체인 배치 기동

3개의 로컬 배치가 체인 ①②⑤⑥을 담당합니다. 각 배치는 opt-in 토글 + `--dry-run` 배관 검증 + 하드캡 규약을 따릅니다.

#### 3-4-1. intake_refine.sh — 인테이크 정제 (체인 ①)

metaprompt 정제: 고객 요구사항 → 구현 스펙 마크다운. 로컬 Claude 세션(`claude -p`)이 정제 LLM을 담당, 서버는 대기 목록과 결과 저장만.

```bash
cd /mnt/c/workspace/ClickEye

# 배관 검증 (권장 시작점)
scripts/intake_refine.sh --dry-run

# live 실행 (명시 활성 필수)
FLOWOPS_INTAKE_REFINE=true scripts/intake_refine.sh
```

**환경변수 오버라이드**:
- `API_URL` (기본: `http://localhost:8000`)
- `MAX_ITEMS` (기본: 5 — 건당 1회 정제, ~30초)
- `CLAUDE_TIMEOUT` (기본: 300초)

**cron 예시** (야간 배치):
```cron
0 2 * * * cd /mnt/c/workspace/ClickEye && FLOWOPS_INTAKE_REFINE=true bash scripts/intake_refine.sh >> logs/intake-refine.log 2>&1
```

#### 3-4-2. intake_issue.sh — 티켓 발급 (체인 ②)

분해: 정제 스펙 → 티켓 JSON → Linear 자동 발급. 로컬 Claude 세션이 분해 LLM 담당, 서버는 발급 원장 기록.

```bash
# 배관 검증
scripts/intake_issue.sh --dry-run

# live 실행 (기계 수락 활성화 권장)
FLOWOPS_INTAKE_ISSUE=true FLOWOPS_INTAKE_AUTO_ACCEPT=true scripts/intake_issue.sh
```

**환경변수 오버라이드**:
- `API_URL` (기본: `http://localhost:8000`)
- `MAX_ITEMS` (기본: 3 — 건당 1회 분해+발급, ~2분)
- `CLAUDE_TIMEOUT` (기본: 600초)
- `ISSUE_STATE` (기본: `Queued`)

**cron 예시** (야간 배치):
```cron
0 3 * * * cd /mnt/c/workspace/ClickEye && FLOWOPS_INTAKE_ISSUE=true FLOWOPS_INTAKE_AUTO_ACCEPT=true bash scripts/intake_issue.sh >> logs/intake-issue.log 2>&1
```

#### 3-4-3. delivery_verify.sh — 정합성 게이트 (체인 ⑤⑥)

발급 티켓 전량 완주 확인 → 통합 게이트 → 최종 상태 확정 → 서비스 #2 콜백.

```bash
# 완주 관측 (dry-run, 서버 상태 불변)
scripts/delivery_verify.sh --dry-run

# live 실행 (게이트 실행)
FLOWOPS_DELIVERY_VERIFY=true scripts/delivery_verify.sh
```

**환경변수 오버라이드**:
- `API_URL` (기본: `http://localhost:8000`)
- `MAX_ITEMS` (기본: 5 — 건당 게이트 실행, 가변)
- `VERIFY_WORKDIR` (기본: 저장소 루트)
- `GATE_TIMEOUT` (기본: 1800초)

**cron 예시** (야간 배치):
```cron
0 4 * * * cd /mnt/c/workspace/ClickEye && FLOWOPS_DELIVERY_VERIFY=true bash scripts/delivery_verify.sh >> logs/delivery-verify.log 2>&1
```

> **중요**: 위 cron 명령들은 **미등록 상태**입니다. 자동 기동이 필요하면 아래 3-5 단계에서 수동 등록합니다.

### 3-5. crontab 등록 (영구 자동 기동)

WSL 재시작 후에도 파이프라인이 자동 복구되려면 crontab이 등록돼 있어야 합니다.

등록 여부 확인 및 경로 검증:

```bash
# 등록 여부 확인
crontab -l | grep auto_dev_pipeline

# 경로 검증 (등록된 모든 cron 명령의 cd 대상 확인)
crontab -l | grep -oP "cd \K[^ &]+" | sort -u
# → 출력이 /mnt/c/workspace/ClickEye 인지 확인. 옛 경로 /mnt/c/workspace/24SevenClaw 가 섞여 있으면 정정 필수
```

등록이 안 된 경우 또는 경로가 잘못된 경우:

```bash
# cron 서비스 상태 확인
service cron status

# 꺼져 있으면 시작
sudo service cron start

# crontab 등록 (cron 정본 = scripts/clickeye_cron.txt)
(crontab -l 2>/dev/null; cat /mnt/c/workspace/ClickEye/scripts/clickeye_cron.txt) | crontab -

# 확인
crontab -l
```

> **cron 정본은 `scripts/clickeye_cron.txt` 하나입니다.** 파이프라인 폴링·야간 배치·confirmer·
> 인테이크 3배치와 watchdog 항목이 모두 이 파일에 정의돼 있으니, 개별 줄을 여기 문서에
> 중복 기재하지 않습니다. 등록 전 `SHELL`/`PATH` 지시와 로컬 `claude`/`ngrok` 설치 경로가
> 일치하는지(`command -v claude ngrok`) 파일 상단 체크리스트를 따르세요.

watchdog 항목은 **호스트 워커**(`webhook_worker.py`)와 ngrok 을 감시합니다. webhook 수신부는
이제 compose 컨테이너이므로 호스트 `webhook_server.py` watchdog 은 더 이상 등록하지 않습니다.
정본의 watchdog 형태(자기매칭을 피하는 문자클래스 pgrep 패턴):

```cron
# 웹훅 실행 워커 watchdog (10분마다, 죽으면 재기동)
*/10 * * * * pgrep -f "[w]ebhook_worker.py" > /dev/null || (cd /mnt/c/workspace/ClickEye && nohup python3 scripts/webhook_worker.py >> logs/webhook-worker.log 2>&1 &)
# ngrok watchdog (10분마다, 죽으면 재기동)
*/10 * * * * pgrep -f "[n]grok http 9876" > /dev/null || (cd /mnt/c/workspace/ClickEye && nohup ngrok http 9876 --log=logs/ngrok.log --log-format=logfmt >> /dev/null 2>&1 &)
```

> **WSL2 영구 자동 시작**: `/etc/wsl.conf`에 아래 설정을 추가하면 WSL 부팅 시 cron이 자동 시작됩니다.
> ```ini
> [boot]
> command = service cron start
> ```

---

## 4단계: 주요 기능 확인 포인트

### Swagger UI (http://localhost:8000/docs)

| 기능 | 메서드 | 경로 |
|------|--------|------|
| PM 프로필 목록 | GET | `/api/v1/pm-profiles/` |
| PM 프로필 상세 + 메트릭 | GET | `/api/v1/pm-profiles/{id}` |
| PM 구성 조회 | GET | `/api/v1/pm-profiles/{id}/composition` |
| PM 추천 | POST | `/api/v1/pm-profiles/recommend` |
| 프로젝트(인게이지먼트) 목록 | GET | `/api/v1/projects/` |
| 프로젝트(인게이지먼트) 상세 | GET | `/api/v1/projects/{id}` |
| 산출물 프리뷰 | POST | `/api/v1/projects/{id}/preview` |
| 거버넌스 정책 조회 | GET | `/api/v1/governance/policy` |

### 웹 UI (http://localhost:3000)

- **딜리버리 콘솔** — 인게이지먼트 설계·실행·추적 (/delivery/[engagementId])
- **AI Team** — 프로필 추천·구성·평가
- **Ops 패널** — 컨테이너·환경·테이블 모니터링
- **Settings** — Linear, Anthropic, 멤버 관리

---

## 5단계: DB 직접 접속 및 확인

### PostgreSQL 접속

```bash
# 컨테이너 안으로 들어가서 psql 실행
docker exec -it clickeye-db psql -U clickeye -d clickeye
```

접속 후 주요 확인 명령어:

```sql
-- 테이블 목록 확인
\dt

-- 테이블 스키마 확인
\d <테이블명>

-- 데이터 확인 예시
SELECT * FROM pm_profiles LIMIT 10;
SELECT * FROM projects ORDER BY created_at DESC LIMIT 5;

-- 마이그레이션 이력 확인 (Alembic)
SELECT * FROM alembic_version;

-- psql 종료
\q
```

한 줄 쿼리 실행 (컨테이너 진입 없이):

```bash
docker exec -it clickeye-db psql -U clickeye -d clickeye -c "\dt"
docker exec -it clickeye-db psql -U clickeye -d clickeye -c "SELECT * FROM alembic_version;"
```

### Redis 접속 및 확인

```bash
# 컨테이너 안에서 redis-cli 실행
docker exec -it clickeye-redis redis-cli

# 저장된 키 목록
KEYS *

# 특정 키 값 확인
GET <key>

# 캐시 전체 초기화 (주의: 개발 환경에서만)
FLUSHDB
```

한 줄 실행:

```bash
docker exec -it clickeye-redis redis-cli KEYS "*"
docker exec -it clickeye-redis redis-cli PING   # PONG 응답이면 정상
```

### 컨테이너 로그 확인

```bash
# DB 로그
docker logs clickeye-db --tail 50

# Redis 로그
docker logs clickeye-redis --tail 50
```

---

## 포트 정리

| 서비스 | 포트 |
|--------|------|
| API (FastAPI) | 8000 |
| Web (Next.js) | 3000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Webhook 서버 | 9876 |
| ngrok 로컬 대시보드 | 4040 |

---

## 문제 상황 진단 가이드

### 진단 체크리스트 (한눈에 보기)

```bash
cd /mnt/c/workspace/ClickEye

# 1. 수신 컨테이너 + 호스트 워커 생존 여부
docker compose -f clickeye-infra/docker/docker-compose.yml ps webhook  # clickeye-webhook healthy 여부
pgrep -af "[w]ebhook_worker.py"    # 호스트 워커 PID가 출력되면 실행 중
pgrep -af "[n]grok http 9876"      # PID가 출력되면 실행 중
service cron status                # cron 서비스 상태
crontab -l | grep pipeline         # crontab 등록 확인

# 2. 포트 바인딩 확인
ss -tlnp | grep 9876               # webhook 컨테이너 퍼블리시 포트
curl -s http://127.0.0.1:9876/health   # {"status":"ok"} 이면 정상
curl -s http://127.0.0.1:4040/api/tunnels | python3 -c \
  "import sys,json; t=json.load(sys.stdin)['tunnels']; print(t[0]['public_url'] if t else 'NO TUNNEL')"

# 3. 로그 최근 상태
tail -20 logs/webhook.log
tail -20 logs/pipeline-cron.log
tail -5  logs/ngrok.log
```

---

### 증상별 원인 및 해결

#### 딜리버리 상세 진입 시 화면이 비거나 "Failed to fetch" 오류

**원인 확인 순서** (우선순위):

1. **DB 마이그레이션 미적용** (가장 흔함 — 2026-07-30 실측)
   ```bash
   docker exec clickeye-db psql -U clickeye -d clickeye -tAc "SELECT version_num FROM alembic_version"
   cd /mnt/c/workspace/ClickEye/clickeye-api && uv run alembic heads
   # 두 값이 다르면 미적용 — 아래 명령 재실행
   uv run python -m alembic upgrade head
   ```
   브라우저 새로고침 후 확인.

2. **API 서버 미기동**
   ```bash
   curl -s http://127.0.0.1:8000/docs | head -5
   # → 응답 없으면 API 재시작
   ```

3. **CORS 설정** (로컬 테스트 환경에서는 보통 OK)
   ```bash
   grep CORS_ORIGINS /mnt/c/workspace/ClickEye/.env
   # → http://localhost:3000 포함 여부 확인
   ```

---

#### DayQueued로 옮겨도 파이프라인이 실행되지 않는다

**원인 확인 순서**:

1. **수신 컨테이너 또는 호스트 워커가 죽어 있는 경우** (가장 흔함)
   ```bash
   # 수신 컨테이너 상태 + 로그
   docker compose -f clickeye-infra/docker/docker-compose.yml ps webhook
   docker logs clickeye-webhook --tail 30
   # → 죽어 있으면 재기동
   cd /mnt/c/workspace/ClickEye/clickeye-infra/docker && docker compose --profile full up -d webhook

   # 호스트 워커(큐 소비) 확인
   pgrep -f "[w]ebhook_worker.py" || echo "워커 프로세스 없음"
   # → 없으면 재기동
   cd /mnt/c/workspace/ClickEye
   nohup python3 scripts/webhook_worker.py >> logs/webhook-worker.log 2>&1 &

   # 큐에 job 이 쌓여만 있고 소비되지 않는지 확인(워커 미기동 신호)
   docker exec clickeye-redis redis-cli LLEN clickeye:webhook:jobs
   ```

2. **ngrok 터널이 끊긴 경우**
   ```bash
   curl -s http://127.0.0.1:4040/api/tunnels | python3 -c \
     "import sys,json; t=json.load(sys.stdin)['tunnels']; print(t[0]['public_url'] if t else 'NO TUNNEL')"
   # → NO TUNNEL 이면 ngrok 재시작 + Linear webhook URL 갱신 필요
   nohup ngrok http 9876 --log=logs/ngrok.log --log-format=logfmt >> /dev/null 2>&1 &
   ```

3. **ngrok URL이 바뀌었는데 Linear webhook이 갱신 안 된 경우**
   - Linear → Settings → API → Webhooks에서 URL 확인
   - ngrok 새 URL로 교체: `https://<새URL>/webhook/linear`

4. **crontab 미등록 (폴링 백업 경로도 없는 경우)**
   ```bash
   crontab -l | grep pipeline || echo "crontab 없음"
   # → 없으면 3-4단계 참조하여 등록
   ```

5. **DayQueued 이슈가 실제로 존재하는지 확인**
   ```bash
   python3 scripts/linear_watcher.py --dry-run --limit 5
   # exit 0: 이슈 있음 / exit 2: 이슈 없음
   ```

---

#### 파이프라인 실행 중 `git index.lock` 오류

`auto_dev_pipeline.sh`에 `safe_git` 래퍼가 적용되어 있어 대부분 자동 처리됩니다.

수동으로 강제 제거가 필요한 경우:

```bash
# lock 파일 나이 확인
stat /mnt/c/workspace/ClickEye/.git/index.lock 2>/dev/null

# 60초 이상 경과한 stale lock이면 제거
rm -f /mnt/c/workspace/ClickEye/.git/index.lock
```

> `safe_git` 래퍼는 모든 git 호출 전에 15초 대기 → 그래도 lock이 있으면 자동 제거합니다.

---

#### Gemini CLI 실행 실패 (`ERROR: Gemini CLI 실행 실패`)

> 참고: 기획 단계는 기본적으로 **Claude 메타프롬프트 정제**(`FLOWOPS_METAPROMPT=true`)를 사용한다.
> Gemini는 `FLOWOPS_METAPROMPT=false`로 전환했을 때만 동작하는 레거시 폴백이므로, 아래 절차는 Gemini 폴백을 쓰는 경우에만 해당한다.

```bash
# 1. 바이너리 존재 확인
which gemini || echo "설치 안 됨"

# 2. 버전 확인 (v0.24.5 이상 권장)
gemini --version 2>/dev/null || echo "버전 확인 불가"

# 3. 인증 상태
gemini auth status 2>&1 | head -5

# 4. 수동 재현 테스트
echo "안녕" | timeout 10 gemini 2>&1 | head -5
```

**해결**:
- `command not found` → `npm install -g @google/gemini-cli` 재설치 또는 PATH 확인
- 인증 만료 → `gemini auth login` 재실행
- 기본값(`FLOWOPS_METAPROMPT=true`)이면 Gemini를 거치지 않으므로, 이 오류가 나면 `FLOWOPS_METAPROMPT=false`로 폴백을 끄거나 다시 메타프롬프트 기획으로 되돌린다 (Gemini 폴백 비활성 시 fix_plan.md를 PLAN.md로 그대로 사용)

> `scripts/generate_plan_with_gemini.sh`에 `timeout 60` 래퍼가 적용되어 있어 무한 대기는 발생하지 않습니다.

---

#### Codex CLI 실행 실패 (`WARN: Codex CLI 실행 실패`)

```bash
# 1. 바이너리 확인
which codex || echo "설치 안 됨"

# 2. 버전 확인 (0.112.0 이상 — exec 서브커맨드 필수)
codex --version 2>/dev/null

# 3. 수동 테스트
timeout 30 codex exec "테스트 프롬프트" 2>&1 | head -10
```

**해결**:
- `command not found` → `npm install -g @openai/codex` 재설치
- `stdin is not a terminal` 오류가 났다면 `codex -p` 방식 사용 금지 — `codex exec "..."` 형식으로만 호출
- 인증 만료 → `codex login`
- 실패가 지속되면 `FLOWOPS_CODEX_REVIEW=false`로 일시 비활성화

---

#### `FLOWOPS_*` 토글 확인 및 변경

```bash
# 현재 설정 전체 확인
grep ^FLOWOPS /mnt/c/workspace/ClickEye/.env

# 주요 토글
# 체인 파이프라인
# FLOWOPS_LINEAR_WATCHER=true   — Linear 이슈 감지 활성화 (false면 파이프라인 전체 스킵)
# FLOWOPS_METAPROMPT=true       — Claude 메타프롬프트 기획(관측형 사전 정제) — 기본
# FLOWOPS_GEMINI_PLAN=false     — 레거시 Gemini 기획 (METAPROMPT=false일 때 폴백)
# FLOWOPS_CODEX_REVIEW=true     — Codex QA 리뷰 단계
# FLOWOPS_AUTO_MERGE=true       — PR 없이 main 직접 머지 (HIGH-tier는 거버넌스 게이트가 PR 강등)
# FLOWOPS_GOVERNANCE=true       — 머지 직전 거버넌스 게이트 (+_CONTRACT/_TICKET/_TRACE/_RISK_DEMOTE/_PROMOTE)
# FLOWOPS_TELEGRAM=true         — Telegram 완료 알림

# 인테이크 배치 (3-4 참조)
# FLOWOPS_INTAKE_REFINE=true    — 인테이크 정제 활성화 (기본 off — opt-in)
# FLOWOPS_INTAKE_ISSUE=true     — 티켓 발급 활성화 (기본 off — opt-in)
# FLOWOPS_INTAKE_AUTO_ACCEPT=true — 기계 수락 활성화 (INTAKE_ISSUE 함께 필요)
# FLOWOPS_DELIVERY_VERIFY=true  — 딜리버리 정합성 게이트 활성화 (기본 off — opt-in)

# LLM 게이트웨이 (CE-299, CE-328)
# FLOWOPS_USAGE_INGEST=true     — 로컬 claude -p 사용량 → 서버 원장 인제스트 (기본 off)
```

---

#### 파이프라인 로그 위치

| 로그 파일 | 내용 |
|---|---|
| `docker logs clickeye-webhook` | 수신 컨테이너 — Linear webhook 수신 + 큐 적재(RPUSH) 기록 |
| `logs/webhook-worker.log` | 호스트 워커 — 큐 소비(BLPOP) + 파이프라인 트리거 기록 |
| `logs/pipeline-cron.log` | cron 폴링으로 실행된 파이프라인 로그 |
| `logs/pipeline-night.log` | 자정 NightQueued 배치 실행 로그 |
| `logs/pipeline_YYYYMMDD_HHMMSS.log` | webhook 트리거 파이프라인 개별 실행 로그 |
| `logs/claude_<이슈키>_*.log` | Claude 구현 단계 상세 로그 |
| `logs/merge_*.log` | AUTO_MERGE 실행 결과 + diff 전체 |
| `logs/confirmer.log` | 정오 Confirm → Done 전환 로그 |
| `logs/ngrok.log` | ngrok 터널 연결 상태 로그 |

최근 파이프라인 실행 확인:

```bash
# 가장 최근 실행 로그
ls -t logs/pipeline_*.log | head -1 | xargs tail -30

# webhook 수신(컨테이너) + 큐 소비(워커) 이력
docker logs clickeye-webhook --tail 20
grep "EVENT\|TRIGGER\|IDLE" logs/webhook-worker.log | tail -20

# 에러만 필터
grep -i "error\|warn\|fail" logs/pipeline-cron.log | tail -20
```

---

#### E2E 정상 동작 검증 시나리오

파이프라인이 전체적으로 잘 동작하는지 확인하려면:

1. 수신 컨테이너 + 워커 + 터널 생존 확인
   ```bash
   docker compose -f clickeye-infra/docker/docker-compose.yml ps webhook
   curl -s http://127.0.0.1:9876/health
   pgrep -af "[w]ebhook_worker.py"
   pgrep -af "[n]grok http 9876"
   ```

2. Linear에서 테스트 이슈를 **DayQueued**로 변경

3. 5초 이내 `logs/webhook.log`에 아래 순서로 출력 확인:
   ```
   EVENT: <이슈키> → DayQueued
   TRIGGER: auto_dev_pipeline.sh 실행 시작
   ```

4. Linear 이슈 상태가 **In Progress**로 자동 전이 확인

5. `logs/pipeline_*.log` 에서 단계 진행 확인:
   ```
   Claude 메타프롬프트 기획 완료
   Claude 구현 완료
   Codex QA 리뷰 완료
   ```

6. 완료 시 Linear 이슈 상태 **Done** 전이 + Telegram 알림 수신

7. `logs/webhook.log` 마지막 줄:
   ```
   IDLE: 잔여 DayQueued/NightQueued 이슈 없음
   ```
