## 판정
실패

## 근거

구현 자체(로직)는 스펙의 각 항목을 대체로 충족한다 — `summary()`/`usage()` 파라미터화, `daily_outcomes` 날짜 슬롯 채우기, `project_summary()` 집계, contract 동반 갱신까지 모두 diff에서 확인된다. 그러나 **테스트 계획**은 스펙에 명시된 수용 기준을 명백히 충족하지 못한다.

- 스펙 "대상 파일" 및 "테스트" 절에 "각 신규/변경 동작당 ≥3 테스트 추가", "신규/변경 엔드포인트별 ≥3 케이스(정상/빈 데이터/검증실패 또는 무회귀)"가 명시적 수용 기준으로 걸려 있다.
- `/usage` (project_id 필터): 신규 테스트가 `test_usage_filters_by_project_id` **1건**뿐. 스펙이 명시한 "기존 `task_id` 필터 회귀 없음" 테스트, "잘못된 값 422" 테스트가 **누락**됨(`test_observability.py:454` 부근).
- `/summary` (days/trend_days): `test_summary_with_days_query_returns_200`, `test_summary_empty_daily_outcomes_fills_trend_day_slots` **2건**뿐. "days 생략 시 기존과 동일 응답(무회귀)"을 직접 비교하는 테스트, 검증실패(`days=91` 등 422) 테스트가 **누락**됨.
- `/projects/{project_id}/summary`: 2개 테스트 함수로 정상/빈 데이터 케이스는 커버하나, seat NULL 그룹·검증실패 케이스가 별도 테스트로 분리되지 않음(정성적으로는 충족 근접하나 개수 기준 미달).
- Assumptions에 명시된 `trend_days > days`일 때 `min(trend_days, days)` 캡핑 로직이 **테스트로 검증되지 않음** — 이 케이스에 대한 회귀 방지책이 없다.

측정 가능한 수용 기준(테스트 개수)이 명시되어 있고 diff상 명백히 미달이므로 판정불가가 아니라 실패로 판정한다.

## 발견 사항
- [심각도: 중] [확신도: 상] `/usage` project_id 필터 회귀 테스트(기존 `task_id` 필터 정상 동작 유지 확인) 및 검증실패(422) 테스트 누락 — 스펙의 구현단계 10 요구사항 미충족 (clickeye-api/tests/test_observability.py:~440-460)
- [심각도: 중] [확신도: 상] `days`/`trend_days` 422 검증실패 테스트 부재 — `Query(ge=1, le=90)` 등 경계값이 실제로 422를 반환하는지 미검증 (clickeye-api/tests/test_observability.py)
- [심각도: 하] [확신도: 상] `trend_days > days` 캡핑(`effective_trend_days = min(trend_days, days)`) 동작에 대한 테스트 없음 — Assumptions에 명시된 보수적 설계 결정이 회귀 방지 없이 방치됨 (clickeye-api/app/services/observability_service.py:88, tests 미포함)
- [심각도: 하] [확신도: 중] `days` 생략 시 기존(하드코딩 7일) 응답과 동일함을 직접 비교하는 무회귀 테스트가 없음 — 기본값 상수가 우연히 동일한 것과 응답 내용이 실제로 무회귀인지 검증하는 것은 다름 (clickeye-api/tests/test_observability.py)
- [심각도: 하] [확신도: 하] `project_summary()`의 `seat_rows` 조회가 `LlmUsageLedger.seat_id`와 `UserAnthropicCredentials.id`를 outer join하는데, 두 컬럼의 타입(UUID vs 문자열 등) 일치 여부는 diff만으로 확인 불가 — 모델 정의를 직접 봐야 판단 가능 (clickeye-api/app/services/observability_service.py:206-213)
- [심각도: 하] [확신도: 하] `_daily_run_outcomes`가 `since`(days 기준) 전체 기간의 `PipelineRunEvent`를 조회한 뒤 `trend_days` 슬롯만 사용 — 기능상 버그는 아니나 `days=90, trend_days=1`처럼 큰 days 값일 때 불필요하게 넓은 범위를 스캔하는 비효율 (clickeye-api/app/services/observability_service.py:244-251)
