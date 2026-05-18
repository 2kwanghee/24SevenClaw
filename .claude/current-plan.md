## 목표
M7 — Modernize finalize 흐름: Linear 자동 등록 + ZIP 생성기 modernize 분기 + step-modernize-confirm UI.
사용자가 시나리오와 권장안을 검토 완료한 직후 한 번의 클릭으로 Linear 이슈 N+1 건 등록 + ZIP 다운로드까지.

## 비침습성 보장
- 기존 `linear_service.create_initial_task` / `create_issues` 미변경. 신규 함수 2 개 추가만.
- 기존 `generator.py.generate_all()` 미변경. 신규 `generate_modernize_zip()` 함수 추가.
- 신규 endpoint 2 개만 추가 (`POST /sessions/{id}/finalize`, `GET /sessions/{id}/zip`)
- 공유 step (PM/agents/env) 재사용은 M7-B 로 분리. M7-A 는 confirm step 만 추가하여 finalize 핵심 흐름 완성.

## 변경 파일 목록

### Backend (신규)
- `app/services/modernize/finalize.py` — Linear 등록 + ZIP 빌드 통합 흐름
- `app/services/modernize/zip_builder.py` — Modernize ZIP 트리 생성 (MODERNIZE_README, .ralph/tasks/, .clickeye/linear-issues.json, docs/diagnosis.*)

### Backend (수정)
- `app/services/linear_service.py` — `create_modernize_parent_issue`, `create_modernize_child_issues` 신규 함수 추가
- `app/schemas/modernize.py` — `FinalizeRequest`, `FinalizeResponse` 추가
- `app/api/v1/modernize.py` — `POST /sessions/{id}/finalize`, `GET /sessions/{id}/zip` 추가

### Frontend (신규)
- `src/components/solutions/wizard/steps/step-modernize-confirm.tsx` — 최종 요약 + finalize 트리거 + ZIP 다운로드 버튼

### Frontend (수정)
- `src/lib/api-client.ts` — `finalizeSession`, `downloadZip` 추가
- `src/app/(dashboard)/solutions/modernize/new/page.tsx` — STEP_COMPONENTS 에 confirm 추가 (5 step)

## Finalize 흐름

```
POST /modernize/sessions/{id}/finalize
  ├─ 0. 자격 검증: project_linear_credentials OR user_linear_credentials
  ├─ 1. selected=true 인 recommendations 정렬 (priority ASC)
  ├─ 2. Linear parent issue 생성 (옵션) — "Modernize: <repo> (<scenario>)"
  ├─ 3. 각 recommendation → child issue 일괄 생성
  │      → 응답의 identifier/id 를 ModernizeRecommendation.linear_issue_id/identifier 에 저장
  ├─ 4. ZIP 빌드 — generate_modernize_zip()
  ├─ 5. ModernizeSession.status = 'finalized'
  └─ 6. 응답: { linear_parent_url, linear_issues_count, zip_url }

GET /modernize/sessions/{id}/zip
  └─ ZIP streaming download
```

## ZIP 트리

```
project-root/
├── .clickeye/
│   └── linear-issues.json      # 등록된 이슈 매핑 (중복 등록 방지)
├── .ralph/
│   └── tasks/
│       └── <linear-identifier>.md  # rec.prompt_md
├── docs/
│   ├── diagnosis.md            # CodebaseAnalysis.llm_summary_md
│   └── diagnosis.json          # 분석 결과 머신리더블
├── MODERNIZE_README.md         # 1-pager 실행 가이드
└── .env.example                # LINEAR_API_KEY/TEAM_ID/REPO_URL 안내
```

기존 ZIP 자산 (auto_dev_pipeline.sh, harness-gate.sh, linear_tracker.py 등) 은 M7-B 에서 통합 — 일단 핵심 산출물만.

## 구현 단계
1. linear_service Modernize 헬퍼 2 개
2. zip_builder.py 작성
3. finalize.py 통합 흐름
4. schemas + endpoint 2 개
5. api-client + step-modernize-confirm UI
6. page.tsx STEP_COMPONENTS 확장
7. ruff + mypy + tsc + vitest

## 회귀 검증
- R-3 OpenAPI diff: 신규 2 path 추가
- R-5 wizard-store: 회귀 케이스 보존
- R-6 Feature flag OFF: 신규 endpoint 모두 404
- 기존 linear_service / generator.py 의 기존 export 미변경

## STATUS: APPROVED
