---
title: Modernize 회귀 검증 체크리스트 (MVP-2-A)
category: reference
status: current
last_updated: 2026-05-18
related:
  - clickeye-api
  - clickeye-web
---

# ClickEye Modernize 회귀 검증 체크리스트 (MVP-2-A)

> Modernize 파이프라인(M1~M7) PR 머지 전 매번 확인해야 할 비침습성 회귀 검증.
> 핵심 원칙: **기존 코드 무영향, 신규 기능은 옵트인 분기로만 추가.**

## 한눈에 요약 — 매 PR 머지 전

| # | 항목 | 자동화 | 명령 / 위치 |
|---|---|---|---|
| **R-1** | 기존 `/solutions/new` 위저드 E2E | 수동 (또는 Playwright) | 브라우저로 12-step 진행 → ZIP 다운로드 |
| **R-2** | ZIP 골든파일 (Modernize) | ✅ vitest/pytest | `pytest tests/services/modernize/test_zip_builder.py` |
| **R-3** | OpenAPI diff | 수동 + 가이드 | `openapi-diff` 또는 git diff `openapi.json` |
| **R-4** | 카탈로그 변경 0 건 | ✅ shell 스크립트 | `bash scripts/modernize-check-catalog-unchanged.sh` |
| **R-5** | wizard-store snapshot | ✅ vitest | `cd clickeye-web && npx vitest run` |
| **R-6** | Feature flag OFF | ✅ shell + vitest | `bash scripts/modernize-check-flag-off.sh` |
| **R-7** | Alembic downgrade | ✅ python -m alembic | `uv run python -m alembic downgrade 038` → 재 `upgrade 039` |

---

## R-1 — 기존 `/solutions/new` 위저드 E2E

**왜 중요**: Modernize 신규 기능이 기존 12-step 위저드 흐름을 깨면 안 됨.

**자동 검증** (가능한 부분):
```bash
# dev 서버 살아있는 상태에서
curl -s -o /dev/null -w "/solutions/new HTTP %{http_code}\n" http://localhost:3000/solutions/new
```
HTTP 200 이면 페이지 컴파일 OK.

**수동 검증** (필요 시):
1. `npm run dev` (clickeye-web)
2. 브라우저 → `/solutions/new`
3. Step 0~11 차례로 진행 (회사정보 → 솔루션 → 프로토타입 → PM → 에이전트 → 플랫폼 → OS → 환경변수 → ROI → 확인)
4. "이대로 진행" → ZIP 다운로드
5. ZIP 트리가 기존 산출물과 동일한지 확인

**실패 신호**: 어떤 step 에서 에러 / canProceed 가 의도와 다르게 동작 / 산출 ZIP 누락 파일.

---

## R-2 — ZIP 골든파일 (Modernize)

**왜 중요**: ZIP 생성기 시그니처 변경 시 다운스트림 (사용자 로컬 `auto_dev_pipeline.sh`) 이 깨질 수 있음.

**자동 검증**:
```bash
cd clickeye-api
uv run python -m pytest tests/services/modernize/test_zip_builder.py -v
```

`test_zip_deterministic_for_same_input` 가 동일 입력 → 동일 파일명 set 보장.

**기존 ZIP** (`generator.generate_all()`): 별도 테스트 없음 — 미변경 보장은 코드 리뷰로 확인.

---

## R-3 — OpenAPI diff (기존 endpoint 미변경)

**왜 중요**: 기존 endpoint 의 path / method / response schema 변경은 frontend / SDK 호환성 깨뜨림.

**자동 검증**:
```bash
# 1. 베이스 (main) 의 openapi.json 추출
git checkout main
uv run python scripts/openapi_export.py > /tmp/openapi-base.json
git checkout -

# 2. 현재 브랜치의 openapi.json
uv run python scripts/openapi_export.py > /tmp/openapi-head.json

# 3. diff
npx @openapitools/openapi-diff /tmp/openapi-base.json /tmp/openapi-head.json
```

**기대 결과**: `Breaking changes: 0`. 신규 path 추가만 허용.

`openapi_export.py` 가 없다면 `curl http://localhost:8000/openapi.json | jq` 로 직접 비교.

---

## R-4 — 카탈로그 변경 0 건

**왜 중요**: `app/data/catalog/*.json` 의 기존 항목 id/category/필드 변경은 위저드 게이트 회귀 (M4 의 ticket_source 검증) 를 일으킬 수 있음.

**자동 검증**:
```bash
bash scripts/modernize-check-catalog-unchanged.sh main
```

신규 항목 추가는 허용. 기존 라인 삭제/수정 감지 시 exit 1.

---

## R-5 — wizard-store snapshot

**왜 중요**: 기존 setter 시그니처가 변하면 모든 step 컴포넌트 회귀.

**자동 검증**:
```bash
cd clickeye-web
npx vitest run src/stores/__tests__/solution-wizard-store.test.ts
```

기대 결과: 모든 케이스 통과. M1 + M4 의 modernize 케이스도 함께 통과.

전체 회귀:
```bash
cd clickeye-web
npx vitest run
```

77/77 통과 — MVP-2-A 출시 시점 기준.

---

## R-6 — Feature flag OFF 동작

**왜 중요**: 베타 사용자 외에는 신규 라우트/endpoint 가 절대 노출되지 않아야 함.

**자동 검증** (dev 서버 + `FEATURE_MODERNIZE_ENABLED=false` 로 기동):
```bash
bash scripts/modernize-check-flag-off.sh http://localhost:8000 http://localhost:3000
```

기대 결과: backend `/api/v1/integrations/github/app/*` + `/api/v1/modernize/*` 모두 404.

**프론트엔드 검증** (브라우저):
- `NEXT_PUBLIC_FEATURE_MODERNIZE_ENABLED=false` 로 dev 서버 재기동
- `/projects` → "기존 코드 현대화 BETA" 카드 **미노출** 확인
- `/solutions/modernize/new` 직접 진입 → `/projects` 로 즉시 redirect 확인

---

## R-7 — Alembic downgrade (M2 무영향 검증)

**왜 중요**: 신규 migration 039 적용 후 즉시 downgrade 했을 때 기존 스키마 (038) 와 완전히 동일해야 함.

**자동 검증**:
```bash
cd clickeye-api

# 신규 테이블 부재 → 적용 → 존재 → downgrade → 부재 확인
uv run python -m alembic upgrade 039
uv run python -m alembic downgrade 038

# 기존 핵심 테이블 컬럼 개수가 변하지 않았는지 확인
uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import engine
async def check():
    async with engine.connect() as c:
        r = await c.execute(text(\"\"\"
            SELECT table_name, COUNT(*) AS cols
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name IN ('projects','users','organizations','pm_profiles','prototype_sessions')
            GROUP BY table_name ORDER BY table_name
        \"\"\"))
        for row in r.fetchall():
            print(f'  {row[0]:25s}: {row[1]} columns')
asyncio.run(check())
"

# 최종 상태 복원
uv run python -m alembic upgrade 039
```

**기대 결과** (M2 시점 실측):
```
organizations            : 14 columns
pm_profiles              : 20 columns
projects                 : 21 columns
prototype_sessions       : 12 columns
users                    : 13 columns
```

downgrade 전후 동일.

---

## CI 통합 (권장)

`.github/workflows/regression.yml` (예시):
```yaml
- name: R-4 catalog check
  run: bash scripts/modernize-check-catalog-unchanged.sh ${{ github.base_ref }}

- name: R-5 wizard-store regression
  run: |
    cd clickeye-web
    npx vitest run src/stores/__tests__/solution-wizard-store.test.ts

- name: R-2 ZIP golden
  run: |
    cd clickeye-api
    uv run python -m pytest tests/services/modernize/test_zip_builder.py

# R-1 / R-3 / R-6 / R-7 은 dev 서버 또는 DB 가 필요 — 별도 integration job 또는 nightly
```

---

## 환경 의존성 (검증 자동화 실행 전 확인)

| 항목 | 확인 |
|---|---|
| `tests/conftest.py` 의 SQLite/Uuid 호환성 | M3 시점 conftest 가 SQLite + Uuid 매핑 부서져 있음. `structlog` 미설치도. CI 환경 정비 필요. |
| `uv run python -m alembic` | OK (M2 실측) |
| `npm test` / `npx vitest` | OK (M1~M7 매 세션 77/77 통과) |
| Anthropic API key | M5/M6 의 LLM 요약/권장안 생성 통합 테스트는 별도 환경에서. 단위 테스트는 placeholder fallback 으로 검증 가능. |
| GitHub App 등록 | M3 인프라 통합 테스트용. `docs/modernize-github-app-setup.md` 참조. |

---

## 마일스톤 진행 (참조)

```
[✓] M1 — Feature flag + wizard-store mode 분기
[✓] M2 — 백엔드 모델 5종 + Alembic 039
[✓] M3 — GitHub App 인프라 + install/callback/webhook
[✓] M4 — 진입 카드 + repo-connect/select step + repo 목록 API
[✓] M5 — 코드 분석 엔진 7-step + diagnose UI
[✓] M6 — VersionUp 권장안 LLM + diagnosis-review UI
[✓] M7 — Linear 자동 등록 + ZIP 생성 + finalize 흐름
[✓] M8 — 회귀 R-1~R-7 자동화 + 본 체크리스트 + 단위 테스트
```

MVP-2-A 출시 완료. 후속:
- M7-B: 공유 step (PM/agents/env) 재사용, ZIP 안 기존 자산 (`auto_dev_pipeline.sh`) 통합, finalize idempotency 강화
- MVP-2-B: Refactor 시나리오 LLM 프롬프트 정교화
- MVP-2-C: LanguageMigrate 시나리오 + target_stack UI
- MVP-3: ClickEye 클라우드에서 자동 PR 작성 (M3 GitHub App write scope 승격)
