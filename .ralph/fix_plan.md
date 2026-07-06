# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] Phase 5 — 작업 전 사전검토(Pre-flight) 게이트 구현**
  > 요청사항: ## 목표

실행(Phase 6) 직전 **사전검토 게이트**를 신설한다. 계획 전체를 영향도·위험 관점에서 점검하고 사용자 승인을 받아야만 실행 팩(ZIP) 발급이 가능하다.

## As-Is 근거

* 현재 사전검토는 위저드 Step 3 권장안 체크박스 + Step 4 요약 확인이 전부
* `breaking_changes`는 텍스트 배열로만 존재, 영향도 분석/시뮬레이션 없음
* 프로젝트 Plan Gate·Governance Gate(HIGH 리스크 강등) 철학과 동일한 패턴을 modernize에도 적용

## 작업 내용

1. Pre-flight 체크리스트 자동 생성:
   * breaking change 목록 (major 업그레이드/EOL/DB 전환별)
   * 롤백 전략 유무 (특히 DB 마이그레이션: 백업·리허설·롤백 스크립트)
   * 테스트 커버리지 현황 (as-is 스캔에서 테스트 파일 비율 감지 추가)
   * HIGH 리스크 태스크 식별 (auth/보안/데이터 이관) → 수동 확인 필수 플래그
2. `preflight-review.md` 산출물 + 항목별 pass/warn/block 판정
3. 승인 API: block 항목 존재 시 승인 불가, 승인 시 `approved_at` 기록 → 이후에만 실행 팩 다운로드 허용
4. 위저드 confirm 스텝과 CLI 양쪽에서 사용 가능한 공용 엔드포인트

## 완료 조건

* block 판정 시 ZIP 발급 403, 승인 후 정상 발급 (통합 테스트)
* preflight 산출물이 ZIP에 포함되어 로컬 오케스트레이터가 재확인 가능

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-07-06 | [api] Phase 5 Pre-flight 게이트 | 완료 | `app/services/modernize/preflight.py` 신설(체크리스트 생성/렌더/승인 판정), `modernize_phase_artifacts`(phase=preflight) 재사용으로 마이그레이션 불요. `POST/GET /sessions/{id}/preflight`, `POST .../preflight/approve` 3개 엔드포인트 추가. `GET .../zip` 에 승인 게이트(403) 추가 + ZIP에 `docs/preflight-review.md` 동봉. scan.py에 test_file_ratio 감지 추가(framework_signals에 병합). contracts(TS+Python) PreflightReviewContent 동기화 + openapi.json 재생성(기존 드리프트 포함 전체 갱신). 단위 11 + 통합 5 신규 테스트 통과, 기존 modernize 테스트 35건 회귀 0. |