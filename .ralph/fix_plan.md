# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [ ] **[cli] `clickeye modernize` 명령 — run / status / resume / report**
  > 요청사항: ## 목표

CLI(`@clickeye/cli`)에서 현대화를 수행할 수 있는 `clickeye modernize` 서브커맨드를 추가한다. (R2 — CLI는 파워유저 경로, 웹과 동일 생성 엔진 공유)

## As-Is 근거

* clickeye-cli에 modernize 관련 명령 없음 (as-is 분석 확인)
* 위저드 5단계는 웹 전용, CLI 사용자는 실행 팩을 받을 방법이 없음

## 작업 내용

1. `clickeye modernize init` — API로 세션 생성(repo/branch/요구사항 입력, 대화형 프롬프트) 후 6단계 진행 상태 폴링
2. `clickeye modernize pull` — preflight 승인된 세션의 실행 팩 ZIP 다운로드·압축 해제
3. `clickeye modernize run [--resume|--dry-run|--wave n]` — 로컬 [orchestrator.py](<http://orchestrator.py>) 래핑 실행
4. `clickeye modernize status` — 세션 phase + 로컬 state.json 진행 현황 통합 표시
5. `clickeye modernize report` — 기록지침 로그를 요약 리포트로 출력 (CE-293 연동)
6. contracts의 Phase/산출물 타입 재사용 (openapi generated client)

## 완료 조건

* 명령별 단위 테스트 + `docs/cli-guide.md` 현행화
* 웹 위저드에서 만든 세션을 CLI로 이어받는(pull→run) 시나리오 검증

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|