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

# DB 마이그레이션 적용
uv run python -m alembic upgrade head

# 시드 데이터 로딩 (PM 프로필 초기 데이터, 최초 1회)
uv run python scripts/seed_pm_data.py

# API 서버 실행 (--host 0.0.0.0: WSL2에서 Windows 브라우저 접근 허용)
uv run python -m uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

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

---

## 3단계: 자동화 파이프라인 기동

### 3-1. webhook 서버 시작 (Linear 이벤트 수신)

```bash
cd /mnt/c/workspace/ClickEye

# 백그라운드 실행
nohup python3 scripts/webhook_server.py >> logs/webhook.log 2>&1 &

# 정상 기동 확인
curl -s http://127.0.0.1:9876/health
# 응답: {"status":"ok"} 이면 정상
```

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

### 3-4. crontab 등록 (영구 자동 기동)

WSL 재시작 후에도 파이프라인이 자동 복구되려면 crontab이 등록돼 있어야 합니다.

등록 여부 확인:

```bash
crontab -l | grep auto_dev_pipeline
```

등록이 안 된 경우:

```bash
# cron 서비스 상태 확인
service cron status

# 꺼져 있으면 시작
sudo service cron start

# crontab 등록
(crontab -l 2>/dev/null; cat /tmp/clickeye_cron.txt) | crontab -

# 확인
crontab -l
```

`/tmp/clickeye_cron.txt`가 없으면 아래 내용으로 직접 `crontab -e` 편집:

```cron
# 평일 9-18시 매 5분 큐 폴링 (webhook 죽어도 백업)
*/5 9-18 * * 1-5 cd /mnt/c/workspace/ClickEye && bash scripts/auto_dev_pipeline.sh --once >> logs/pipeline-cron.log 2>&1
# 자정 야간 배치 (NightQueued 연속 처리)
0 0 * * * cd /mnt/c/workspace/ClickEye && bash scripts/auto_dev_pipeline.sh --max-iterations 50 >> logs/pipeline-night.log 2>&1
# 평일 정오 Confirm → Done 정리
0 12 * * 1-5 cd /mnt/c/workspace/ClickEye && python3 scripts/linear_confirmer.py >> logs/confirmer.log 2>&1
# webhook_server watchdog (10분마다 살아있는지 확인, 죽으면 재기동)
*/10 * * * * pgrep -f "webhook_server.py" > /dev/null || (cd /mnt/c/workspace/ClickEye && nohup python3 scripts/webhook_server.py >> logs/webhook.log 2>&1 &)
# ngrok watchdog (10분마다 살아있는지 확인, 죽으면 재기동)
*/10 * * * * pgrep -f "ngrok http 9876" > /dev/null || (cd /mnt/c/workspace/ClickEye && nohup ngrok http 9876 --log=logs/ngrok.log --log-format=logfmt >> /dev/null 2>&1 &)
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
| PM 평가 등록 | POST | `/api/v1/pm-profiles/{id}/rate` |
| PM 메트릭 조회 | GET | `/api/v1/pm-profiles/{id}/metrics` |
| 프로토타입 세션 생성 | POST | `/api/v1/prototype-sessions/` |
| 프로토타입 세션 목록 | GET | `/api/v1/prototype-sessions/` |

### 웹 UI (http://localhost:3000)

- Solution Wizard v2 — 7단계 위저드 흐름
- PM 시스템 UI (추천 · 구성 · 평가)
- 프로토타입 UI
- AI Team 3계층 운영 대시보드
- 가치 대시보드 KPI 시각화
- 성숙도 온보딩 흐름

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
SELECT * FROM prototype_sessions ORDER BY created_at DESC LIMIT 5;

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

# 1. 프로세스 생존 여부
pgrep -af webhook_server.py        # PID가 출력되면 실행 중
pgrep -af "ngrok http 9876"        # PID가 출력되면 실행 중
service cron status                # cron 서비스 상태
crontab -l | grep pipeline         # crontab 등록 확인

# 2. 포트 바인딩 확인
ss -tlnp | grep 9876               # webhook 서버 포트
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

#### DayQueued로 옮겨도 파이프라인이 실행되지 않는다

**원인 확인 순서**:

1. **webhook_server가 죽어 있는 경우** (가장 흔함)
   ```bash
   pgrep -f webhook_server.py || echo "프로세스 없음"
   # → 없으면 재기동
   cd /mnt/c/workspace/ClickEye
   nohup python3 scripts/webhook_server.py >> logs/webhook.log 2>&1 &
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
- 실패가 지속되면 `.env`에서 `FLOWOPS_GEMINI_PLAN=false`로 일시 비활성화 (fix_plan.md를 PLAN.md로 그대로 사용)

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
# FLOWOPS_LINEAR_WATCHER=true   — Linear 이슈 감지 활성화 (false면 파이프라인 전체 스킵)
# FLOWOPS_GEMINI_PLAN=true      — Gemini 기획 단계
# FLOWOPS_CODEX_REVIEW=true     — Codex QA 리뷰 단계
# FLOWOPS_AUTO_MERGE=true       — PR 없이 main 직접 머지
# FLOWOPS_TELEGRAM=true         — Telegram 완료 알림
```

---

#### 파이프라인 로그 위치

| 로그 파일 | 내용 |
|---|---|
| `logs/webhook.log` | Linear webhook 이벤트 수신 + 파이프라인 트리거 기록 |
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

# webhook 이벤트 수신 이력
grep "EVENT\|TRIGGER\|IDLE" logs/webhook.log | tail -20

# 에러만 필터
grep -i "error\|warn\|fail" logs/pipeline-cron.log | tail -20
```

---

#### E2E 정상 동작 검증 시나리오

파이프라인이 전체적으로 잘 동작하는지 확인하려면:

1. 프로세스 생존 확인
   ```bash
   pgrep -af webhook_server.py && curl -s http://127.0.0.1:9876/health
   pgrep -af "ngrok http 9876"
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
   Gemini PLAN 생성 완료
   Claude 구현 완료
   Codex QA 리뷰 완료
   ```

6. 완료 시 Linear 이슈 상태 **Done** 전이 + Telegram 알림 수신

7. `logs/webhook.log` 마지막 줄:
   ```
   IDLE: 잔여 DayQueued/NightQueued 이슈 없음
   ```
