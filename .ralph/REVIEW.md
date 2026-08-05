## 판정
실패

## 근거

- **엔드포인트 4종 구현**: `summary`/`usage`/`runs`/`runs/{issue_key}`/`seats` 모두 존재, 라우터 등록도 정상 (`router.py:21,84`) — 충족.
- **인증 가드**: `require_permission("settings:manage")` 라우터 레벨 적용, 형제 패턴과 일치 — 충족.
- **재사용 원칙**: `runs`는 `PipelineRunService.list_runs` 그대로 위임, `seats`는 `SeatQuotaService.latest()` 위에 `screen_view()`만 추가 — `latest()` 내부 쿼리 불변, 도메인 제약 충족.
- **model_mismatch 파생**: `scripts/auto_dev_pipeline.sh:1063`에서 실제로 `record_metric ... "model_mismatch" "{intended, actual}"` 이벤트를 남기는 것을 확인 — `"model_mismatch" in by_event`로 판정하는 구현이 실제 파이프라인 이벤트 스키마와 일치함(허구 아님). 충족.
- **빈 데이터 방어**: 4개 엔드포인트 모두 기본값(0/빈 리스트) 반환, 테스트에도 각 1개 이상 포함 — 충족.
- **Contract 우선 원칙 (미충족)**: 구현 스펙 8번 단계와 "준수할 컨벤션"에 "엔드포인트 구현 완료 후 반드시 `openapi.json` + 생성 TS 타입 동기화까지 포함"이 완료조건으로 명시되어 있으나, diff에 `clickeye-contracts/openapi/openapi.json`, `clickeye-contracts/generated/typescript/{types.gen.ts,sdk.gen.ts}` 변경이 전혀 없다. 신규 엔드포인트 4개 + `PipelineRunResponse.model_mismatch` 필드 추가가 있었음에도 contracts 미동기화 — 이 항목이 실패로 판정되는 핵심 근거.

## 발견 사항
- [심각도: 상] [확신도: 상] Contract 우선 원칙 위반 — 신규 라우터 4종 및 `PipelineRunResponse.model_mismatch` 필드 추가에도 `clickeye-contracts/openapi/openapi.json`, `generated/typescript/types.gen.ts`, `generated/typescript/sdk.gen.ts` 갱신이 diff에 없음 (스펙 "구현 단계 8", "준수할 컨벤션" 항목 직접 위반)
- [심각도: 하] [확신도: 상] 라우터 레벨 `dependencies=[Depends(require_permission(...))]`가 이미 내부에서 `get_current_user`를 의존하는데, 각 엔드포인트 함수 시그니처에서 다시 `_user: User = Depends(get_current_user)`를 선언해 요청당 인증 조회(JWT 디코드/DB 조회)가 중복 실행됨 (clickeye-api/app/api/v1/observability.py:29, 38, 55, 70, 85) — 기능상 오류는 아니고 형제 라우터(`llm_ledger.py`)도 동일 패턴을 쓸 가능성이 있어 컨벤션 일치일 수 있음, 참고용
- [심각도: 하] [확신도: 중] `ObservabilityService._count_group_by`가 `key is not None`인 행만 집계에 포함해 NULL 상태값이 있으면 집계에서 조용히 누락됨(clickeye-api/app/services/observability_service.py:126) — `projects.status`/`intake_requests.status`가 NOT NULL 기본값을 가져 실질적으로 발생 가능성은 낮음
