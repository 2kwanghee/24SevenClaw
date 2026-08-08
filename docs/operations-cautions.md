---
title: 운영 시 주의사항
category: guide
status: current
last_updated: 2026-08-08
related:
  - scripts/webhook_server.py
  - clickeye-api/app/services/ops/webhook_env_service.py
  - scripts/auto_dev_pipeline.sh
  - clickeye-infra/managed/api.env
  - clickeye-api/CLAUDE.md
---

# 운영 시 주의사항

ClickEye 플랫폼 운영 중 발생한 사고와 반복 가능한 함정을 집대성한 문서입니다. 각 항목은 **무엇을 하면 안 되는가 / 왜 / 어떻게 확인하는가**를 명확히 합니다.

## A. Linear Webhook 시크릿 관리 (CE-417, CE-421)

### A1. 설정 저장 후 "활성화 추가 작업" 필요

**문제**: 프로젝트 설정 카드에서 webhook 시크릿을 저장해도 수신이 즉시 시작되지 않습니다.

**원인**: 운영 패널의 webhook env 렌더링과 webhook 컨테이너 재기동이 별도의 명시적 작업입니다.

**해결 방법**:
1. 프로젝트 설정(`/projects/{projectId}/settings`)의 Linear 카드에서 webhook 시크릿 저장 (DB 에 저장됨)
2. 운영 패널 `/admin/ops/env` → **Webhook 시크릿 배선** 카드 → **[webhook.env 렌더]** 버튼
3. 화면에 표시된 재기동 명령을 호스트에서 실행:
   ```
   cd clickeye-infra && docker compose -f docker/docker-compose.yml up -d --no-build --force-recreate webhook
   ```
4. 수신부 기동 로그에서 `팀 바인딩: 시크릿 N개 / 팀 M개` 라인 확인

**근거**: `clickeye-api/app/services/ops/webhook_env_service.py:338` `_restart_command()` — 렌더 서비스는 docker 를 실행하지 않고 명령 문자열만 반환한다(무 DB·무 docker 원칙).

---

### A2. 멀티 테넌트 보안: 레거시 시크릿 제거 필수

**문제**: 멀티 테넌트 격리를 완성하려면 `WEBHOOK_SECRET` / `WEBHOOK_SECRETS` 를 반드시 비워야 합니다.

**원인**: 레거시 변수는 팀 바인딩 검사를 면제받습니다 (= 임의 팀 사칭 가능).

**확인 및 해결**:
- 운영 패널에서 webhook env 렌더 결과를 봅니다.
- 수신부 기동 배너에 `WARN: WEBHOOK_SECRET 또는 WEBHOOK_SECRETS 이 설정되었습니다` 출력되면 제거 필요
- `.env` 또는 `clickeye-infra/managed/webhook.env` 에서 아래 두 라인을 비우거나 주석 처리:
  ```bash
  # WEBHOOK_SECRET=
  # WEBHOOK_SECRETS=
  ```

**근거**: `scripts/webhook_server.py:18-60` — 크로스테넌트 바인딩(WEBHOOK_SECRET_MAP) 설명

---

### A3. 세 변수의 의미 차이와 운영 흐름

| 변수 | 용도 | 팀 검사 | 운영자 개입 |
|------|------|--------|-----------|
| `WEBHOOK_SECRET` | 레거시 단일 시크릿 | 없음 | 수기 설정 (제거 권장) |
| `WEBHOOK_SECRETS` | 콤마 목록(단일 조직용) | 없음 | 수기 설정 (제거 권장) |
| `WEBHOOK_SECRET_MAP` | 프로젝트별 팀 바인딩 | **있음** | 운영 패널 자동 렌더 |

**운영 흐름**:
1. 사용자가 프로젝트 설정 카드에서 webhook 시크릿 입력 및 저장 (DB)
2. 운영 패널이 DB → `WEBHOOK_SECRET_MAP` 렌더 (자동)
3. 관리자가 `/admin/ops/env` 에서 **[webhook.env 렌더]** 실행 후 컨테이너 재기동
4. webhook 수신부가 파일을 읽어 팀별 바인딩 검증 시작

---

### A4. 제외 항목 확인 (fail-closed 정책)

**문제**: 시크릿 또는 team_id 에 특수문자가 있으면 렌더에서 제외됩니다.

**이유**: 콤마, 개행, `=`, 앞뒤 공백이 있으면 수신부 파서가 항목을 제대로 분해할 수 없어 전체 안전성을 깨뜨립니다. fail-closed 설계상 그 항목만 **제외** 처리합니다.

**확인 방법**:
- 운영 패널의 webhook env 렌더 결과 `skipped` 섹션 확인
- 제외된 항목이 있으면 그 프로젝트의 webhook은 인증 불통 상태

**수정**:
- 시크릿 재생성 (특수문자 없는 무작위 문자열)
- team_id 정정 (Linear 대시보드에서 확인)
- 다시 저장 → 렌더 → 배포

**근거**: `clickeye-api/app/services/ops/webhook_env_service.py:147-180` — `_is_single_physical_line()`, `_has_control_char()`

---

### A5. 항목 0개면 라인 삭제 (기동 거부 방지)

**문제**: 시크릿을 모두 삭제했는데 `WEBHOOK_SECRET_MAP=` 라인이 빈 상태로 남으면 수신부가 기동을 거부합니다.

**원인**: 수신부는 MAP 라인이 명시되어 있으면 "설정됐는데 값이 0개" 를 fail-closed 로 해석합니다.

**해결**:
- 운영 패널에서 렌더하면 항목이 0개일 때 **라인 자체를 삭제** (자동)
- webhook 수신부 재기동 전 확인: 파일에 `WEBHOOK_SECRET_MAP=` 라인이 없어야 함

**확인 명령**:
```bash
grep "WEBHOOK_SECRET_MAP" clickeye-infra/managed/webhook.env
# 결과 없으면 정상
```

**근거**: `clickeye-api/app/services/ops/webhook_env_service.py:13-15`

---

### A6. 수신부 파일은 DB 변경을 동기화하지 않음

**문제**: 시크릿을 삭제해도 재렌더 전까지 폐기된 시크릿이 수신부에서 계속 유효합니다 (드리프트).

**해결**:
1. 운영 패널에서 변경사항 확인 (드리프트 표시)
2. 반드시 `/admin/ops/env` 의 **[webhook.env 렌더]** 재실행 후 재기동
3. webhook 수신부 로그에서 새 `WEBHOOK_SECRET_MAP` 라인 확인

**참고**: 스냅샷 파일 없이 파일의 현재 MAP 항목 집합과 DB 산출 집합을 직접 비교해 드리프트를 보고합니다.

**근거**: `clickeye-api/app/services/ops/webhook_env_service.py:16-17` — "드리프트는 파일이 진실"

---

### A7. 동일 team_id, 다른 프로젝트 시크릿 충돌

**주의**: 같은 `team_id` 를 쓰는 서로 다른 프로젝트는 **서로의 시크릿으로 인증됩니다**.

**의미**: Linear 워크스페이스가 1개면 모든 프로젝트의 webhook이 같은 team_id + 같은 시크릿을 쓰므로 문제없습니다. 그러나 멀티 워크스페이스 모드에서는 각 프로젝트가 고유 team_id를 가져야 합니다.

**확인**:
```bash
grep "=" clickeye-infra/managed/webhook.env | grep WEBHOOK_SECRET_MAP
# 각 team_id가 1회만 나타나는지 확인
```

---

### A8. 자동 등록 레이블과 수동 정리

**문제**: 프로젝트별 webhook은 자동으로 등록되지만, **옛 공용 레이블("ClickEye")로 등록된 훅은 자동 정리되지 않습니다**.

**해결**:
- 사용하지 않는 webhook은 Linear 콘솔에서 수동 삭제
- 프로젝트별 webhook은 프로젝트 설정 저장 시 자동으로 `ClickEye:<project_id>` 레이블이 붙습니다.

**근거**: `clickeye-api/app/services/ops/webhook_env_service.py` 구현체에서 자동 등록 로직

---

## B. 파이프라인 및 자동화 운영

### B1. cron 틱이 main을 checkout — 락 선점 필수

**사고 이력**: 2026-08-03 파이프라인 락 미보유 상태에서 인터랙티브 작업 중 cron 틱이 기동되어 checkout main 을 시도해 git 충돌 발생.

**문제**: webhook_server의 재트리거는 cron 폴링과 병행됩니다. cron이 빈 큐를 감지해도 `checkout main` 을 시도합니다.

**해결**:
- 인터랙티브 작업(브랜치 전환, 커밋) 전에 파이프라인 락을 선점:
  ```bash
  mkdir -p .ralph
  echo $$ > .ralph/.pipeline_lock
  # 작업 수행
  rm .ralph/.pipeline_lock
  ```

**확인**:
```bash
ls -la .ralph/.pipeline_lock
```

**근거**: `scripts/webhook_server.py:32, 88-89` — `LOCK_FILE`, `PIPELINE_LOCK_FILE`; `scripts/auto_dev_pipeline.sh:32` — `LOCK_FILE=".ralph/.pipeline_lock"`

---

### B2. 거버넌스 게이트: 브랜치 키 검증

**문제**: 브랜치명에 Linear 티켓 키가 없으면 auto_dev_pipeline.sh의 거버넌스 게이트를 통과하지 못합니다.

**요구사항**:
- 브랜치: `{type}/{module}/{TICKET-KEY}-{description}` 형식
- 예시: `feature/web/CE-302-delivery-console`, `fix/api/24S-142-auth-bug`
- 정규식: 브랜치 어디든 `^[A-Z0-9]+-\d+$` 패턴의 키 존재 필수

**실패 시 조치**:
1. 기존 PR이 있으면 닫기 (거버넌스가 차단함)
2. 올바른 키를 포함한 새 브랜치 생성
3. 새 PR 생성

**참고**: 자동 파이프라인은 선택한 이슈의 키를 자동으로 브랜치명에 포함합니다.

**근거**: `CLAUDE.md` — "브랜치: `{type}/{module}/{TICKET-KEY}...` (Linear 키 병기 필수)"; `scripts/pre_merge_gate.py` (ticket-ref 검증)

---

### B3. HIGH 위험 경로는 자동머지 불가

**규칙**: `clickeye-contracts/**`, `clickeye-infra/**`, `*auth*`, 보안 경로는 `AUTO_MERGE=on` 이어도 자동머지 금지입니다 (직접 PR 경로로 강등).

**해결**:
- 고위험 경로 변경 시 자동 파이프라인 시행 금지
- 수동으로 PR 생성 후 코드 리뷰 거쳐 머지

**위험 판단 기준**: `docs/pipeline-guide.md` Step 5.5, `scripts/pre_merge_gate.py:_risk_demote()`

---

### B4. `FLOWOPS_*` 토글: 명시적 false 주입 필수

**문제**: 테스트/스크립트에서 토글 변수를 "제거"로는 off 상태를 재현할 수 없습니다.

**원인**: `.env` 로더가 **미설정 변수를 .env 값으로 채워서** 실행 시 변수가 존재합니다 (존재하지만 빈 값일 수 있음). pipeline_config.sh의 is_enabled 함수가 빈 값을 true로 해석할 수 있습니다.

**해결**:
```bash
# ❌ 틀린 방법 (변수 제거해도 안 됨)
unset FLOWOPS_AUTO_COMMIT

# ✓ 옳은 방법 (명시적 false)
export FLOWOPS_AUTO_COMMIT=false
```

**실제 사고**: CE-419 실측 — 테스트에서 토글 비활성화 재현 실패

**근거**: `scripts/pipeline_config.sh:20-40` — `_load_flowops_env()` 함수가 .env 파일의 값으로 export 실행

---

### B5. 모델 별칭 금지, 정식 모델명만 사용

**사고 이력**: CE-367, 2026-08-04 — `--model sonnet` 별칭이 `claude-opus-4-8` 로 해석되어 비용 2.5배 증가.

**규칙**:
- ❌ `--model sonnet`, `--model opus` (별칭)
- ✓ `--model claude-sonnet-5`, `--model claude-opus-5` (정식명)

**영향**: 캐시 읽기 오류 및 환산액 오류 누적.

**모델 지정 위치**: `scripts/auto_dev_pipeline.sh:44-46` 에서 관리
```bash
PIPELINE_MODEL_REFINE="${PIPELINE_MODEL_REFINE:-claude-sonnet-5}"
PIPELINE_MODEL_IMPL="${PIPELINE_MODEL_IMPL:-claude-sonnet-5}"
PIPELINE_MODEL_REVIEW="${PIPELINE_MODEL_REVIEW:-claude-sonnet-5}"
```

**근거**: `scripts/auto_dev_pipeline.sh:35-46` — CE-367 주석 상세 설명

---

## C. 개발 환경 이슈

### C1. WSL drvfs 마운트 간헐적 끊김

**증상**: "Input/output error" 메시지와 함께 git, npm 명령이 실패합니다.

**원인**: Windows WSL2 의 drvfs 마운트 불안정성 (실측: 빈번한 재발).

**복구 방법**:
1. Windows PowerShell (관리자) 에서:
   ```powershell
   wsl --shutdown
   ```
2. WSL 세션 재시작
3. Claude Code 세션과 dev 서버 재시작

**확인**:
```bash
ls /mnt/c/workspace/ClickEye  # I/O error 가 나오면 shutdown 필요
```

**메모**: 마운트 복구 후 항상 개발 서버(web, api 등)를 재시작해야 합니다. 그렇지 않으면 파일 변경 감지가 깨질 수 있습니다.

---

### C2. 머지 후 dev 서버 재시작 필수

**증상**: 머지된 코드가 웹 화면에 반영되지 않음 (옛 버전 유지).

**원인**: WSL 환경에서 `next dev` 의 파일 변경 감지가 간헐적으로 깨집니다.

**해결**: 머지 후 dev 서버 재시작:
```bash
# killall node   # 기존 프로세스 종료
npm run dev       # dev 서버 재시작
```

**확인**: 브라우저에서 localhost:3000 새로고침 후 변경사항 반영 확인.

---

### C3. Alembic autogenerate 위험: drop_table/drop_index 확인

**문제**: `alembic revision --autogenerate` 가 `drop_table()`, `drop_index()` 를 생성할 수 있으며, 그대로 적용하면 **실데이터가 삭제**됩니다.

**원인**:
- 모델이 `clickeye-api/app/models/__init__.py` 에 등록되지 않음 (누락)
- 모델 선언이 실제 DB 스키마와 불일치 (JSON↔JSONB, 부분 유니크 인덱스 미선언 등)

**실제 사고**: CE-370 실측 — `roi_standards`, `pm_recommendation_logs`, CE-328 멱등 인덱스가 삭제 대상 됨.

**해결**:
1. `alembic revision --autogenerate -m "description"` 실행
2. 생성된 마이그레이션 파일 **반드시 검토** (drop 문 확인)
3. drop 문이 있으면:
   - 대신 **모델을 실제 스키마에 맞춘다** (DB 를 모델에 맞추는 새 마이그레이션 금지)
   - 누락 모델을 `__init__.py` 에 등록
   - 부분 유니크 인덱스는 모델 `__table_args__` 에 `postgresql_where` 로 선언
4. 정정 후 마이그레이션 재생성

**검증**:
```bash
cd clickeye-api
grep -E "drop_table|drop_index" alembic/versions/HEAD.py  # 있으면 위험
```

**근거**: `clickeye-api/CLAUDE.md` — DB 마이그레이션 섹션 상세 경고 + `tests/test_model_registration.py` (회귀 방지)

---

## D. 운영 패널 일반

### D1. 관리형 env 파일 권한: 0600, API 컨테이너 소유

**문제**: 운영 패널이 렌더한 관리형 env 파일(`clickeye-infra/managed/api.env` 등)은 **파일 권한 0600 + API 컨테이너 사용자 소유** 입니다. 호스트의 비root 운영자가 읽지 못할 수 있습니다.

**확인**:
```bash
ls -la clickeye-infra/managed/api.env
# 결과: -rw------- 1 appuser appgroup ...
```

**해결**: root 권한으로만 읽기 가능하거나, docker exec로 컨테이너 내부에서 확인:
```bash
docker exec clickeye-api cat /app/.env
```

**참고**: 이는 보안 정책에 따른 의도된 동작입니다 (평문 시크릿 노출 방지).

---

### D2. ✅ **해소됨**: clickeye-infra/managed/api.env git 추적 해제 (2026-08-08)

**있었던 문제**: `clickeye-infra/managed/api.env` 가 `clickeye-infra/.gitignore` 의 `managed/*.env` 규칙에도 불구하고 **git 에 추적**되고 있었다(한 번 추적된 파일은 이후 gitignore 규칙이 적용되지 않는다). 커밋 내용은 주석 2줄로 시크릿은 없었으나, 운영 패널이 이 경로에 실제 시크릿을 렌더한 뒤 `git add -A` 하는 순간 평문이 커밋될 수 있었다.

**조치 완료**: `git rm --cached clickeye-infra/managed/api.env`(파일은 존치, 인덱스에서만 제거). 이후 `managed/*.env` 규칙이 정상 적용됨을 `git check-ignore` 로 확인. 커밋 내용에 시크릿이 없었으므로 히스토리 재작성은 불필요했다.

**재발 방지 — 신규 관리형 env 파일을 만들 때**: 실제 값 파일(`*.env`)은 절대 `git add` 하지 말 것. 예시(`*.env.example`)만 추적한다. 추적 여부는 아래로 확인:
```bash
git ls-files clickeye-infra/managed/   # *.env(예시 제외)가 나오면 안 됨
```
만약 시크릿이 이미 커밋·푸시된 것을 발견하면, 히스토리 정정보다 **해당 키 전량 폐기·재발급이 우선**이다(원격에 올라간 값은 회수 불가로 간주).

---

## 체크리스트

운영 담당자가 정기적으로 확인할 사항:

- [ ] **주 1회**: webhook 렌더 결과 검토 (skipped 항목 없는지)
- [ ] **변경 후**: 거버넌스 게이트 통과 확인 (브랜치 키 검증)
- [ ] **월 1회**: 레거시 webhook 시크릿 제거 (WEBHOOK_SECRET/WEBHOOK_SECRETS 비어 있는지)
- [ ] **머지 후**: dev 서버 재시작 (파일 변경 감지 확인)
- [ ] **마이그레이션 전**: drop 문 검토 (`alembic revision --autogenerate` 출력)
- [ ] **git 작업 전**: 파이프라인 락 확인 (`.ralph/.pipeline_lock` 없는지)
- [ ] **긴급**: WSL drvfs 에러 발생 시 `wsl --shutdown` 실행
