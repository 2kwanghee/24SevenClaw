---
title: 서비스 실행 가이드 (운영자용)
category: guide
status: current
last_updated: 2026-08-05
related:
  - scripts/fullstack_run.sh
  - clickeye-api/scripts/service_key.py
  - scripts/webhook_server.py
  - scripts/webhook_worker.py
  - scripts/webhook-doctor.sh
  - scripts/clickeye_cron.txt
  - clickeye-infra/docker/Dockerfile.webhook
  - scripts/auto_dev_pipeline.sh
  - scripts/intake_refine.sh
  - scripts/intake_issue.sh
  - scripts/delivery_verify.sh
  - scripts/seat_map.py
  - scripts/workspace_map.py
  - scripts/workspace_provision.sh
  - scripts/runner_dispatcher.sh
  - scripts/runner_clone.sh
  - clickeye-api
  - clickeye-web
  - docs/clickeye-product-guide.md
  - docs/multiproject-delivery.md
---

# 서비스 실행 가이드

## 0단계: 한 방에 기동 (권장 시작점)

아래 1~3단계를 순서대로 하는 것과 같은 일을 한 줄로 한다. **멱등**이므로 이미 떠 있는 것은
건드리지 않고, 마지막에 요소별 상태표를 출력한다.

```bash
cd /mnt/c/workspace/ClickEye
bash scripts/fullstack_run.sh          # 전체 기동 (실측 콜드스타트 ~19초)

bash scripts/fullstack_run.sh --check  # 진단만 (아무것도 바꾸지 않음)
bash scripts/fullstack_run.sh --stop   # 이 스크립트가 띄운 것만 정지
```

기동 범위: `db`·`redis`·`migrate`(= `alembic upgrade head`)·`webhook` 컨테이너 → API(:8000)
→ 웹 dev 서버(:3000) → 호스트 워커 + ngrok(`webhook-doctor.sh` 위임) → cron 정본 대조(보고만).

알아둘 동작:

- **API 는 두 경로를 모두 지원한다.** :8000 을 이미 누가 서비스하면(호스트 uvicorn) 그대로
  인정하고 compose `api` 를 띄우지 않는다(포트 중복 바인딩 방지). 아무도 없으면 컨테이너로 띄운다.
- **마이그레이션은 compose `migrate` 게이트가 담당**한다. 이미지에 구운 `alembic/versions` 가
  DB 리비전보다 낡으면 `Can't locate revision` 으로 실패하므로(실측), 그때는 스크립트가
  `docker compose --profile full build migrate api` 를 안내한다.
- **남의 것은 건드리지 않는다.** `--stop` 은 이 레포 소유(compose 프로젝트 + cwd 가 레포 하위)만
  정지한다. 타 프로젝트 컨테이너·ngrok, 그리고 직접 띄운 호스트 uvicorn 은 대상이 아니다.
- 한 요소가 실패해도 나머지는 계속 올린다. 종료 코드는 `0`(전부 정상)/`1`(부분 기동)/`2`(전제 미충족).
- `--no-web` / `--no-webhook` / `--no-ngrok` 으로 부분 기동·부분 정지가 가능하다.

세부 단계를 개별로 다루려면 아래 1~3단계를 그대로 따르면 된다(이 스크립트가 하는 일과 동일).

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
- `VERIFY_WORKDIR` (기본: 저장소 루트 — 워크스페이스 모드(`FLOWOPS_WORKSPACE`[+`_AUTOMAP`])
  활성 시 명시하지 않으면 건별로 해당 워크스페이스 경로가 기본값. 명시 설정이 항상 우선)
- `VERIFY_GATES_FILE` (기본: `.clickeye-gates.txt` — 워크스페이스에
  `.claude/harness-gates.txt`가 있으면 건별로 그것이 기본값. 명시 설정이 항상 우선, CE-339)
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

# 정본과 현재 crontab 대조 (정본에만 있는 줄 찾기)
comm -23 \
  <(grep -v '^#' /mnt/c/workspace/ClickEye/scripts/clickeye_cron.txt | grep -v '^$' | sort) \
  <(crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' | sort) \
  | head -5

# crontab 등록 (cron 정본 = scripts/clickeye_cron.txt)
(crontab -l 2>/dev/null; cat /mnt/c/workspace/ClickEye/scripts/clickeye_cron.txt) | crontab -

# 확인
crontab -l
```

> **cron 정본은 `scripts/clickeye_cron.txt` 하나입니다.** 파이프라인 폴링·야간 배치·confirmer·
> 인테이크 3배치와 watchdog 항목이 모두 이 파일에 정의돼 있으니, 개별 줄을 여기 문서에
> 중복 기재하지 않습니다. 등록 전 `SHELL`/`PATH` 지시와 로컬 `claude`/`ngrok` 설치 경로가
> 일치하는지(`command -v claude ngrok`) 파일 상단 체크리스트를 따르세요.
>
> 정본에는 러너 디스패처(`runner_dispatcher.sh`, CE-346) 줄도 포함돼 있습니다.
> `FLOWOPS_RUNNER_DISPATCH` 를 켜지 않으면 SKIP 후 즉시 종료하므로 등록만으로는 아무 일도
> 일어나지 않습니다. 켤 때의 전제(시트 배정·전용 러너와 단일 러너의 티켓 경합)는
> `docs/multiproject-delivery.md` §5-3 을 먼저 읽으세요.

watchdog 항목은 **호스트 워커**(`webhook_worker.py`)와 ngrok 을 감시합니다. webhook 수신부는
이제 compose 컨테이너이므로 호스트 `webhook_server.py` watchdog 은 더 이상 등록하지 않습니다.
정본의 watchdog 형태(자기매칭을 피하는 문자클래스 pgrep 패턴):

```cron
# 웹훅 실행 워커 watchdog (10분마다, 죽으면 재기동)
*/10 * * * * pgrep -f "[w]ebhook_worker.py" > /dev/null || (cd /mnt/c/workspace/ClickEye && nohup python3 scripts/webhook_worker.py >> logs/webhook-worker.log 2>&1 &)
# ngrok watchdog (10분마다, 죽으면 재기동 — 예약 도메인 고정)
*/10 * * * * pgrep -f "[n]grok http 9876" > /dev/null || (cd /mnt/c/workspace/ClickEye && nohup ngrok http 9876 --url="https://$NGROK_DOMAIN" --log=logs/ngrok.log --log-format=logfmt >> /dev/null 2>&1 &)
```

> **`--url` 은 생략하면 안 됩니다(CE-338).** 무료 플랜은 재기동마다 랜덤 URL 을 배정하므로,
> watchdog 이 `--url` 없이 되살리면 Linear 에 등록된 예약 도메인과 불일치해 이벤트가
> **조용히** 유실됩니다(에러 없음 — 폴링 cron 만 남아 최대 5분 지연, 업무시간 밖이면 더).
> 정본은 `NGROK_DOMAIN` 을 crontab 변수로 두고 이 줄에서 확장합니다(cron 은 crontab 변수를
> 커맨드 환경으로 export 하므로 `SHELL=/bin/bash` 아래에서 확장됩니다). 기본값 SSOT 는
> `scripts/webhook-doctor.sh:34` — 도메인을 바꾸면 두 곳을 함께 갱신하세요.

> **WSL2 영구 자동 시작**: `/etc/wsl.conf`에 아래 설정을 추가하면 WSL 부팅 시 cron이 자동 시작됩니다.
> ```ini
> [boot]
> command = service cron start
> ```

#### 3-5-1. 재부팅 후 복구는 아직 무인이 아니다 (CE-351)

WSL·도커를 재시작하면 **cron watchdog 만으로는 체인이 돌아오지 않습니다.** 실측(2026-08-04
마운트 장애 후 재진입):

| 구성요소 | 자동 복구 | 이유 |
|---|---|---|
| `docker.service` | ✅ | `systemctl is-enabled docker` = enabled |
| `clickeye-db` · `clickeye-redis` | ❌ | `RestartPolicy=no` |
| `clickeye-webhook` | ⚠️ 컨테이너만 살아남음 | `restart: unless-stopped` — 다만 redis 가 없으면 적재 불가 |
| 호스트 API(uvicorn :8000) | ❌ | 수동 기동만 |
| 호스트 워커 · ngrok | ⚠️ | cron watchdog 10분 — Redis 부재 시 접속 실패 경로 |

재시작 후 복구는 **0단계의 런처 한 줄**로 끝냅니다(기동 순서·healthy 대기·종단 검증 포함):

```bash
cd /mnt/c/workspace/ClickEye && bash scripts/fullstack_run.sh
```

런처를 쓰지 않고 손으로 할 때는 순서가 중요합니다(db·redis 가 healthy 여야 워커가 큐를 잡습니다):

```bash
cd /mnt/c/workspace/ClickEye/clickeye-infra/docker && docker compose --profile full up -d db redis webhook
cd /mnt/c/workspace/ClickEye && bash scripts/webhook-doctor.sh   # 워커 + ngrok(예약 도메인) 기동 + 종단 검증
```

`webhook-doctor.sh` 는 컨테이너 소유 PID 를 호스트 잔재로 오탐하지 않습니다(cgroup 판정,
CE-338). WSL 은 컨테이너 프로세스를 호스트 PID 네임스페이스에 노출하므로 `ps` 에 보이는
`webhook_server.py` 는 정상적인 컨테이너 수신부일 수 있습니다 — `--force` 로 죽이지 마세요.

부팅 자동 복구(compose restart 정책 + systemd 유닛)는 **CE-351** 에서 다룹니다.

---

### 3-6. 다프로젝트 체인 활성 절차 (CE-345/346/347/329)

다프로젝트 무인 딜리버리를 위한 4종 티켓(시트 풀·디스패처·리다이렉트·집행면)이 모두 main에 머지되었습니다.
여기서는 운영자가 순서대로 실행할 절차를 기술합니다. 이론 상세는 `docs/multiproject-delivery.md` §5-3 ~ §5-5를 참조하세요.

**1단계: 시트 풀 등록**

구독 계정마다 1회, **그 계정으로 로그인된 클린 셸에서** 수행합니다. 시트 인증은
`claude setup-token` 이 발급하는 **구독 OAuth 토큰**입니다 — API 키(크레딧 과금)를
넣지 마세요. 실행면은 구독형 전용입니다:

```bash
cd /mnt/c/workspace/ClickEye
mkdir -p .ralph/seats && umask 077        # 새 파일 권한 600

claude setup-token                        # 시트 계정 OAuth 토큰 발급 → 출력값 복사
read -rs TOKEN                            # 에코 없이 입력(Enter 로 종료) — 히스토리에 남지 않음
printf '%s' "$TOKEN" > .ralph/seats/seat-a.token && unset TOKEN
ls -l .ralph/seats/seat-a.token            # -rw------- (600) 확인

# 시트 등재
python3 scripts/seat_map.py register-seat \
  --id seat-a \
  --token-file .ralph/seats/seat-a.token \
  --label "계정 A (구독 시트)"

# 워크스페이스에 배정 (1 시트 : 1 워크스페이스 — 중복 배정은 --force 없이 거부)
python3 scripts/seat_map.py assign --workspace "3be49b62" --seat seat-a

# 해석 확인 (빈 출력이면 배정·상태·토큰 파일을 점검)
python3 scripts/seat_map.py resolve --resolve-key "3be49b62"
python3 scripts/seat_map.py list
```

한도 도달 계정은 `set-status --seat seat-a --status disabled` 로 내립니다. 그 워크스페이스는
기본 계정으로 폴백하지 않고 **단계를 건너뜁니다**(사용량 오귀속 금지).

상세 절차: `docs/multiproject-delivery.md` §5-3

**2단계: 워크스페이스 매핑**

**선행 조건: 머신 서비스 키 발급** (최초 1회, CE-350)

아래 폴링은 `CLICKEYE_SERVICE_KEY`(머신 서비스 키 평문)를 요구합니다. 없으면
`scripts/workspace_map.py` 가 `ERROR: CLICKEYE_SERVICE_KEY 환경변수가 필요합니다`(exit 2)로
끝납니다. 웹 로그인 없이 CLI 로 발급합니다:

```bash
cd /mnt/c/workspace/ClickEye/clickeye-api

# 발급 + .env 등재 (평문은 stdout 한 줄만 — 안내는 stderr 로 분리되어 있어 캡처가 안전하다)
( umask 077; uv run python -m scripts.service_key issue --name "로컬 러너" --print-env >> ../.env )
grep -c '^CLICKEYE_SERVICE_KEY=' ../.env      # 1 이어야 정상(중복 등재 확인)

# 등재한 키가 실제로 인증되는지 확인 (평문을 인자로 넘기지 않는다 — ps·히스토리 노출 방지)
CLICKEYE_SERVICE_KEY="$(grep '^CLICKEYE_SERVICE_KEY=' ../.env | tail -1 | cut -d= -f2-)" \
  uv run python -m scripts.service_key verify

# 목록 / 회수
uv run python -m scripts.service_key list
uv run python -m scripts.service_key deactivate --id <uuid>
```

> **평문은 발급 시점 1회만 노출**되고 DB 에는 sha256 해시만 남습니다 — 잃으면 복구가 아니라
> 재발급입니다. 이 키는 인테이크 접수·거버넌스 evaluate·머신 조회 **세 면의 공용 인증 채널**
> 이므로 발급은 곧 그 세 면의 접근 권한을 만드는 일입니다.
>
> **로테이션 순서**: 새 키 발급 → `.env` 교체 → 그 다음에 옛 키 `deactivate`. 먼저 내리면
> 그 사이 배치가 401 로 실패합니다.

> **⚠ 컨테이너 이미지 신선도** — 머신 조회 라우트(`/api/v1/intake/machine/projects`)는
> 소스에 있어도 **낡은 `api` 이미지에는 없습니다**(실측 2026-08-04: HTTP 404. `migrate`
> 이미지도 같은 이유로 리비전을 몰라 실패했다). compose 경로로 API 를 띄운다면 pull 후
> 한 번은 재빌드하세요:
> ```bash
> (cd clickeye-infra/docker && docker compose --profile full build migrate api)
> ```

고객 프로젝트 목록을 머신 API에서 폴링하여 `.ralph/workspaces.json` 원장을 갱신합니다:

```bash
# API 정보 확인 (머신 제어 서버) — 없으면 위 선행 조건 참조
grep CLICKEYE_SERVICE_KEY /mnt/c/workspace/ClickEye/.env

# 원장 폴링 (머신 API 조회 + pending_source 마킹)
CLICKEYE_SERVICE_KEY="..." python3 scripts/workspace_map.py

# 상태 조회
python3 scripts/workspace_map.py --list

# 각 pending_source 항목에 repo 수동 등재
python3 scripts/workspace_map.py --set-source "3be49b62" "git@github.com:customer/repo.git"

# 재확인
python3 scripts/workspace_map.py --list
```

상세 절차: `docs/multiproject-delivery.md` §5-3

**3단계: 워크스페이스 조달**

고객 저장소를 clone하고 Tier 0 코어 + 집행면 훅을 배치합니다:

```bash
# 조달 (멱등 — 이미 있으면 clone 을 건너뛰고 코어 배치만 검증한다)
# FLOWOPS_ENFORCEMENT=true 를 함께 주면 집행면 훅(gitguard-gate.cjs)까지 배선된다.
FLOWOPS_ENFORCEMENT=true bash scripts/workspace_provision.sh \
  --key "3be49b62" \
  --source "git@github.com:customer/repo.git"

# 조달 완료 확인 — 훅 번들과 settings 엔트리
ls -l workspaces/3be49b62/.claude/hooks/gitguard-gate.cjs
grep -c gitguard-gate workspaces/3be49b62/.claude/settings.json
```

고객 저장소에 이미 `.claude/settings.json` 이 있으면 **원본을 보존**하고 집행면 훅
엔트리만 가산 병합합니다(다른 키·기존 훅 불변, 재실행 멱등). 병합이 불가능한 경우
(주석 포함 JSON 등)에는 경고만 남기고 조달은 계속되며 **그 워크스페이스는 집행면 없이
동작**하므로, 위 `grep -c` 가 0이면 수동 병합이 필요합니다.

상세 절차: `docs/multiproject-delivery.md` §5-4

**4단계: 단일 러너 티켓 경합 차단 (선행 필수)**

> **⚠ 이 단계는 시트를 등록한 뒤에만 하세요(실측 2026-08-04).** 디스패처는 워크스페이스마다
> **배정 시트를 무조건 요구**합니다 — `scripts/runner_dispatcher.sh:186` 이 `seats.json` 에
> 배정이 없으면 `no_seat` 로 영구 스킵하며, 이 판정은 `FLOWOPS_SEAT_POOL` 토글과 **무관**합니다
> (그 토글은 `auto_dev_pipeline.sh` 의 시트 주입만 좌우합니다).
>
> 따라서 시트 없이 제외만 걸면 그 티켓은 **단일 러너에서 빠지고 디스패처도 스킵해 아무도
> 처리하지 않는 죽은 조합**이 됩니다(실측: `후보=1 스폰=0 스킵=1`).
>
> **시트가 없다면 이 단계와 5단계의 `FLOWOPS_RUNNER_DISPATCH` 를 건너뛰세요.** 단일 러너가
> `FLOWOPS_WORKSPACE_AUTOMAP` 으로 `[수주:<key>]` 티켓을 직접 집어 워크스페이스 모드로
> 처리합니다(구독 계정 1개·워크스페이스 소수면 이 구성이 정상입니다). 디스패처는 여러 계정으로
> **병렬** 실행할 때 필요한 층입니다.

디스패처를 켜기 전에 단일 러너(cron)가 디스패처가 관리할 티켓을 건드리지 않도록 제외 목록을 등록합니다:

```bash
# 운영 중인 전용 러너의 workspace_key 확인
python3 scripts/workspace_map.py --list | grep "status=mapped"

# crontab에서 해당 커맨드 라인을 찾고 WATCHER_EXCLUDE_PREFIXES 인자 추가
# 구분자는 탭 문자입니다 (공백 불가):
crontab -e

# 예시 (기존 라인):
# */5 9-18 * * 1-5 cd /mnt/c/workspace/ClickEye && bash scripts/auto_dev_pipeline.sh --once

# 수정된 라인 (2개 러너 제외):
# */5 9-18 * * 1-5 cd /mnt/c/workspace/ClickEye && \
#   WATCHER_EXCLUDE_PREFIXES="$(printf '[수주:ws1] \t[수주:ws2] ')" \
#   bash scripts/auto_dev_pipeline.sh --once

# 검증 — 제외를 준 상태로 조회해서 해당 접두사 티켓이 목록에서 빠지는지 본다
WATCHER_EXCLUDE_PREFIXES="$(printf '[수주:ws1] \t[수주:ws2] ')" \
  python3 scripts/linear_watcher.py --dry-run
# (--dry-run 은 조회만 하고 원장·Linear 상태를 바꾸지 않는다)
```

상세 절차: `docs/multiproject-delivery.md` §5-5

**5단계: 토글 순차 활성화**

`/mnt/c/workspace/ClickEye/.env`에서 다음 토글을 순서대로 활성화합니다:

```bash
# .env 편집
nano /mnt/c/workspace/ClickEye/.env

# 순서대로 추가(또는 기존 값을 true로 변경):
# 1. 워크스페이스 모드 필수 조건:
#    FLOWOPS_WORKSPACE=true
#    FLOWOPS_WORKSPACE_AUTOMAP=true (선택)
#    FLOWOPS_SEAT_POOL=true
#    FLOWOPS_SEAT_POOL_STRICT=true (선택, 기본 경고 후 폴백)

# 2. 다프로젝트 기능 활성화 (순서 지키기):
#    FLOWOPS_WORKSPACE_DELIVERY=true    # 고객 리다이렉트
#    FLOWOPS_RUNNER_DISPATCH=true       # 전용 러너 디스패처
#    FLOWOPS_ENFORCEMENT=true (선택)   # 집행면 훅

# 켜기 전 검증 — 실행 없이 판정만 보는 경로를 쓴다.
# ⚠ auto_dev_pipeline.sh 에는 --dry-run 이 없다(--once / --max-iterations / --max-turns 뿐).
#   즉 파이프라인을 실행하면 실제로 티켓을 처리한다. 먼저 조회 단계만 확인한다:
python3 scripts/linear_watcher.py --dry-run

# 디스패처는 반드시 DRYRUN 과 함께 — 이 변수를 빼면 실제로 러너를 스폰한다:
FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true \
  bash scripts/runner_dispatcher.sh    # 스폰 대상 목록만 출력, 스폰·clone 없음

# 시트 해석·워크스페이스 원장은 오프라인 조회로 확인(부작용 없음):
python3 scripts/seat_map.py resolve --resolve-key "3be49b62"
python3 scripts/workspace_map.py --list
```

**6단계: 종단 검증**

전 체인이 정상 동작하는지 확인합니다:

```bash
# 단일 러너 폴링 (Queued 이슈 감지)
python3 scripts/linear_watcher.py --dry-run

# 디스패처 시뮬레이션
FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true bash scripts/runner_dispatcher.sh

# 실제 1건 통과 — Linear 에서 테스트 이슈(제목이 대상 워크스페이스 접두사로 시작)를
# Queued 로 바꾸고, 아래 순서로 로그를 따라가며 각 단계가 실제로 일어났는지 확인한다.
tail -20 logs/dispatcher.log                        # ① 후보 산정 → 스폰
tail -20 "$(ls -t logs/runner_*.log | head -1)"     # ② 전용 러너(시트 주입 로그 확인)
tail -20 "$(ls -t logs/ws_delivery_*.log | head -1)" # ③ 고객 clone git stderr(실패 시 사유)
tail -20 "$(ls -t logs/delivery_*.log | head -1)"   # ④ 고객 push 결과

# ⑤ 최종 확인 — 고객 저장소에 인테이크 브랜치가 도달했는지(고객 기본 브랜치는 불변)
git -C workspaces/3be49b62 ls-remote --heads origin "clickeye/intake-*"
```

성공 기준: ①에 스폰 1건, ②에 `시트 주입: seat=...`, ④에 push 성공, ⑤에
`clickeye/intake-<워크스페이스키>` 브랜치 존재, Linear 티켓이 Done. **push 가 실패하면
티켓은 Done 이 되지 않고 재시도 경로로 되돌아가며 로컬 브랜치는 보존**됩니다(작업 유실 없음).

**브랜치는 인테이크당 1개다(CE-369).** 티켓마다 새로 만들지 않고
`clickeye/intake-<워크스페이스키>` 하나에 커밋을 쌓는다 — 원격에 이미 있으면 그것을
이어받고, 없으면 고객 기본 브랜치에서 뗀다. 이래야 뒤 티켓이 앞 티켓의 산출물을 본다
(전에는 티켓마다 기본 브랜치에서 떠서 의존 티켓이 앞 결과를 못 봤다).

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
| 파이프라인 실행 이력 | GET | `/api/v1/pipeline-runs` |

### 웹 UI (http://localhost:3000)

- **딜리버리 콘솔** — 인게이지먼트 설계·실행·추적 (/delivery/[engagementId])
  - **파이프라인 실행 축**(CE-364) — 무인 체인이 통과한 5단계(정제·구현·QA·게이트·종료)와
    런 이벤트 타임라인, 그 티켓의 소비 토큰. 세션이 없는 프로젝트에서도 이 패널이 채워진다.
    읽는 법: **소요시간에 `~` 가 붙으면 유도값**(연속 이벤트 시각 차 — 실측은 구현 단계뿐),
    **"진행 추정"** 은 시작 이벤트가 없어 추론한 상태, **"기록 없음"** 은 런이 끝났는데 그
    단계 이벤트만 없는 경우(예: 거버넌스 비활성 경로의 게이트)로 **실행 여부를 뜻하지 않는다.**
    토큰은 **캐시읽기를 함께** 본다 — 실측에서 출력의 150배 이상이라 입출력만 보면 크게
    과소평가한다. 집계는 구현 스텝만이므로 총량이 아니다(CE-353).
- **AI Team** — 프로필 추천·구성·평가
- **Ops 패널** — 컨테이너·환경·테이블 모니터링
- **Settings** — Linear, Anthropic, 멤버 관리

---

## 5단계: DB 직접 접속 및 확인

### 소비 토큰 관측 (CE-362)

**"이 프로젝트에 토큰을 얼마나 썼나"** — 프로젝트별 합계:

```bash
docker exec clickeye-db psql -U clickeye -d clickeye -c "
select left(project_id::text,8) as project, count(*) as runs,
       sum(input_tokens) as in_tok, sum(output_tokens) as out_tok,
       sum((meta->>'cache_read_input_tokens')::bigint) as cache_read,
       round(sum((meta->>'total_cost_usd')::numeric),4) as ref_usd
from llm_usage_ledger where project_id is not null group by project_id;"
```

티켓 단위로 보려면 `task_id` 로 묶는다(`where task_id = 'CE-366'`).

실행 이력(단계별 소요·판정)은 **호스트 로컬 파일과 서버 원장 두 곳**에 쌓인다(CE-363).
로컬 jsonl 을 먼저 쓰고 그다음 서버로 보내므로, 서버가 죽어 있어도 이력은 남는다
(전송 실패는 전부 삼키고 파이프라인을 죽이지 않는다).

```bash
# ① 호스트 로컬 (항상 기록)
python3 -c "
import json
for l in open('logs/metrics/pipeline_runs.jsonl'):
    d=json.loads(l); print(d.get('event'), d.get('data'))"

# ② 서버 원장 — run 단위로 묶어서 조회(이벤트 스레드 + 그 티켓 소비 토큰 동반)
#    admin/superadmin JWT 필요. issue_key·project_id 로 좁힐 수 있다.
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/pipeline-runs?limit=5" | python3 -m json.tool

# ③ 원장 직접 확인
docker exec clickeye-db psql -U clickeye -d clickeye -c \
  "select run_id, issue_key, event, occurred_at from pipeline_run_events
   order by created_at desc limit 10;"
```

서버 원장은 `(run_id, event)` 유일 제약으로 멱등하다 — 재전송·재시도가 행을 늘리지 않는다.
**토큰은 이 테이블에 복제하지 않는다**(`llm_usage_ledger` 가 유일한 출처이고, 조회 시점에
`task_id` = 티켓 키로 조인해 채운다).

읽는 법 — 반드시 알아둘 것:

- **소비량이다. 잔여 한도가 아니다.** 실행면은 구독형 전용이라 잔량·청구 개념이 없다.
  `total_cost_usd` 는 **참고 환산값**이며 청구액이 아니다. `key_source` 는 `subscription_seat`
  로 기록된다.
- **캐시 읽기가 대부분을 차지한다.** 실측(CE-366): 입력 15 / 출력 2,836 인데 캐시 읽기가
  294,037 이다. 입출력만 보면 소비 규모를 크게 과소평가한다.
- **지금 집계는 구현 스텝만이다.** 정제·분해 지점 토큰은 아직 미배선(CE-353)이므로
  **총량이 아니다.** 정제가 40초 돌아도 그 소비량은 원장에 없다.
- 원장이 비어 있으면 토글 4개를 확인한다 — `FLOWOPS_METRICS` · `FLOWOPS_USAGE_INGEST` ·
  `FLOWOPS_GOVERNANCE_SERVICE_URL`(`.env`) + **서버 `FEATURE_LLM_USAGE_INGEST`**(compose api).
  마지막 것이 꺼져 있으면 엔드포인트가 `{status: disabled}` 로 **조용히 무시한다**.
- `project_id` 가 NULL 이면 워크스페이스 원장에 `project_id` 가 없다는 뜻이다
  (`python3 scripts/workspace_map.py --resolve-project <key>` 로 확인).

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

#### 워커 로그에 `STOP-CHAIN` 이 찍히고 티켓이 처리되지 않는다

**정상 동작입니다(CE-349).** 재트리거 체인을 의도적으로 끊은 신호입니다.

```
STOP-CHAIN: 파이프라인 파일락 보유 PID 158709 생존 — 직전 실행이 SKIP(진척 0)으로 종료.
            재트리거 중단(폴링 cron 이 복구)
```

의미: Queued 이슈가 남아 있는데 파이프라인이 `.ralph/.pipeline_lock` 에 걸려 아무 일도
하지 못하고 끝났다는 뜻입니다. 이때 재트리거하면 락 보유자가 끝날 때까지 **6초 주기로
무한 스핀**하므로(수정 전 실측: 25초에 5회, 스핀마다 쓰레기 로그 1개) 체인을 끊습니다.

```bash
# 누가 락을 잡고 있는지 확인
cat /mnt/c/workspace/ClickEye/.ralph/.pipeline_lock
ps -o pid,etime,cmd -p "$(cat /mnt/c/workspace/ClickEye/.ralph/.pipeline_lock)"
```

- **다른 파이프라인/러너가 정상 실행 중** → 그대로 두면 됩니다. 그 실행이 끝난 뒤 폴링
  cron(평일 09~18시 `*/5`)이 잔여 Queued 를 집어갑니다.
- **인터랙티브 작업을 위해 사람이 선점한 락** → 작업이 끝나면 보유 프로세스를 종료하세요.
  잔류 락은 다음 실행이 `WARN: 잔류 lock 파일 제거` 로 스스로 치웁니다.

`STOP-CHAIN: 연속 재트리거 상한 5회 도달` 형태로 찍힌 경우는 락 외의 원인(배정 시트가
`disabled`, `WATCHER_EXCLUDE_PREFIXES` 와 watcher 조회 범위 불일치 등)으로 진척이 없다는
신호입니다. 시트 상태(`python3 scripts/seat_map.py list`)와 제외 접두사를 확인하세요.

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

# 다프로젝트 (CE-339, CE-345, CE-346, CE-347, CE-329)
# FLOWOPS_WORKSPACE=true        — 워크스페이스 모드 (+WORKSPACE_KEY, 기본 off)
# FLOWOPS_WORKSPACE_AUTOMAP=true — 이슈 제목 접두사 → 워크스페이스 자동 해석 (기본 off)
# FLOWOPS_SEAT_POOL=true        — 워크스페이스 배정 시트(.ralph/seats.json)의 OAuth 토큰 주입
#                                 (기본 off). 원장 관리 CLI: scripts/seat_map.py,
#                                 부트스트랩 절차: docs/multiproject-delivery.md §5-3
# FLOWOPS_SEAT_POOL_STRICT=true — 시트 미배정/점유 시 단계 미실행 + 이슈를 실패 경로
#                                 (재시도 복귀/Backlog)로 되돌림 (기본 off = 경고 후 폴백).
#                                 disabled 시트·토큰 미판독은 이 토글과 무관하게 차단
# FLOWOPS_RUNNER_DISPATCH=true   — 워크스페이스별 전용 러너 스폰(디스패처, 기본 off).
#                                 FLOWOPS_RUNNER_DISPATCH_DRYRUN 도 참조.
#                                 단일 러너와 전용 러너 간 티켓 경합 차단: multiproject-delivery.md §5-5
# FLOWOPS_WORKSPACE_DELIVERY=true — 고객 clone 에 태스크 브랜치 생성·push (기본 off).
#                                   3중 게이트(조건 만족 시만 실행). 상세: multiproject-delivery.md §5-5
# FLOWOPS_ENFORCEMENT=true       — 조달 시 집행면 PreToolUse 훅 배선(기본 off).
#                                 workspace_provision.sh 에서 호출자 env 우선(FLOWOPS_ENV_KEEP_EXISTING).
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
| `logs/dispatcher.log` | 워크스페이스별 전용 러너 디스패처 틱 로그 (CE-346) |
| `logs/runner_<key>_*.log` | 워크스페이스별 전용 러너 개별 실행 로그 (CE-346) |
| `logs/ws_delivery_<KEY>_*.log` | 고객 clone git 조작 stderr (태스크 브랜치 생성·push, CE-347) |
| `logs/delivery_<KEY>_*.log` | 고객 clone 푸시 결과 로그 (CE-347) |

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
