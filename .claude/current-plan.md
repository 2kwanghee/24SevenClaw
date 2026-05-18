## 목표
M5 — 코드 분석 엔진 7-step pipeline + step-modernize-diagnose UI.
사용자가 repo 를 선택한 직후 백그라운드 분석이 시작되어 진행률을 폴링으로 보여주고, 완료 시 step-modernize-diagnosis-review (M6) 로 자동 진행.

## 비침습성 보장
- 신규 endpoint 3 개만 추가 (`POST/GET /modernize/sessions`, `GET /sessions/{id}/analysis`)
- 분석은 FastAPI BackgroundTasks 로 비동기 — 기존 요청 흐름 영향 없음
- LLM 프롬프트는 M5 에서 placeholder, M6 에서 시나리오별 정교화
- 워크스페이스는 /tmp/modernize/<session_id>/ — Step 7 후 즉시 삭제 (시크릿/코드 비보관)

## 변경 파일 목록

### Backend (신규)
- `app/services/modernize/clone.py` — git clone (App JWT → installation token 사용)
- `app/services/modernize/scan.py` — 확장자 히스토그램 → lang_distribution
- `app/services/modernize/manifest.py` — pyproject.toml / package.json / requirements.txt / go.mod 파싱
- `app/services/modernize/outdated.py` — pypi/npm registry httpx 호출 (메모리 캐시)
- `app/services/modernize/sample.py` — entry-point 텍스트 슬라이스 (≤80k tokens)
- `app/services/modernize/llm_summary.py` — claude_service 재사용 + 시나리오 system prompt
- `app/services/modernize/pipeline.py` — 7-step orchestrator (asyncio Task)
- `tests/services/modernize/test_scan.py` — 확장자 카운팅 단위 테스트
- `tests/services/modernize/test_manifest.py` — manifest 파싱 단위 테스트

### Backend (수정)
- `app/schemas/modernize.py` — ModernizeSessionCreate/Response, CodebaseAnalysisResponse 추가
- `app/api/v1/modernize.py` — `POST /sessions`, `GET /sessions/{id}`, `GET /sessions/{id}/analysis` 추가

### Frontend (신규)
- `src/components/solutions/wizard/steps/step-modernize-diagnose.tsx` — 자동 진행 + 진행률 폴링

### Frontend (수정)
- `src/lib/api-client.ts` — modernize 도메인에 createSession / getSession / getAnalysis 추가
- `src/app/(dashboard)/solutions/modernize/new/page.tsx` — STEP_COMPONENTS 에 diagnose 추가 (3 step)

## 7-step pipeline 책임 분배

| Step | Sub-module | 입력 | 출력 (DB column) |
|---|---|---|---|
| 1 clone | clone.py | session.repo_full_name, branch | commit_sha + /tmp 경로 |
| 2 scan | scan.py | 워크스페이스 path | lang_distribution, loc_total, file_count |
| 3 manifest | manifest.py | 워크스페이스 path | manifests, framework_signals |
| 4 outdated | outdated.py | manifests | outdated_packages, risk_flags |
| 5 sample | sample.py | 워크스페이스 path | snippets (메모리, LLM 입력만) |
| 6 LLM summary | llm_summary.py | scenario + 모든 분석 결과 | llm_summary_md, tokens_used |
| 7 cleanup | pipeline.py | /tmp 경로 | (워크스페이스 삭제) |

## Endpoint 시그니처

| Method | Path | Body / Query | Response |
|---|---|---|---|
| POST | `/modernize/sessions` | `{installation_id, repo_full_name, branch?, scenario, goals_text?}` | `ModernizeSessionResponse` (status='pending', progress=0) |
| GET | `/modernize/sessions/{id}` | — | `ModernizeSessionResponse` (실시간 상태) |
| GET | `/modernize/sessions/{id}/analysis` | — | `CodebaseAnalysisResponse` (분석 완료 후) |

## 구현 단계
1. backend sub-service 6 종 (clone/scan/manifest/outdated/sample/llm_summary)
2. pipeline orchestrator (BackgroundTasks → asyncio.create_task 내부)
3. schemas + endpoint 3개
4. frontend api-client 확장
5. step-modernize-diagnose UI (3초 폴링)
6. modernize/new/page.tsx 확장 — STEP_COMPONENTS 에 diagnose 추가
7. 단위 테스트 (scan / manifest)
8. ruff + mypy + tsc + vitest

## 회귀 검증
- R-3 OpenAPI diff: 신규 3 path 추가, 기존 미변경
- R-5 wizard-store: 기존 케이스 동일 + diagnoseDone 회귀 무관 (이미 M4 modernize sub-state 에 포함됨)
- R-6 Feature flag OFF: 신규 endpoint 모두 404

## 다음 마일스톤 연결
- M6 에서 LLM 시나리오별 프롬프트 정교화 (VersionUp 우선) + step-modernize-diagnosis-review UI
- 본 M5 의 llm_summary 는 단순 system prompt + sample 컨텍스트로 시작, M6 에서 확장

## STATUS: APPROVED
