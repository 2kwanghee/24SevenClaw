# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **워크스페이스 조달 settings.json 병합 정책 v1 (보수적 보존)**
  > 요청사항: ## 배경

`scripts/workspace_provision.sh:64-68`가 Tier 0 코어 복사 시 대상 레포의 기존 `.claude/settings.json`을 **무조건 덮어쓴다**. `CLAUDE.md`는 존재 시 보존하는 것과 비대칭. 지금까지는 조달 대상이 신규 clone이라 문제가 없었지만, 자체 `.claude/settings.json`(훅·권한·env)을 가진 실 고객 레포 투입 전 반드시 해소해야 한다(고객 설정 무단 파괴 + 고객 훅 소실).

## v1 정책 (보수적 보존 — CLAUDE.md와 대칭)

* 대상 레포에 `.claude/settings.json`이 **없으면**: 현행과 동일하게 코어 settings 복사(회귀 0).
* **있으면**: 기존 파일을 건드리지 않고 보존. 코어 버전을 `.claude/settings.core.json`으로 병치 + 경고 로그(수동 병합 안내). 코어 훅 미설치 가능성을 조달 출력에 명시.
* 키 단위 자동 병합(고객 설정 + 코어 훅 주입, 충돌 규칙)은 v2 — 정책 판단(고객 훅 vs 게이트 훅 우선순위) 필요.

## 변경 파일

* `scripts/workspace_provision.sh`
* 조달 테스트(기존 스크립트 테스트 위치 준수)
* `docs/multiproject-delivery.md` 해당 절(조달 동작 설명) 갱신

## 수용 기준

* 기존 settings.json 없는 신규 조달 → 현행과 동일 결과(바이트 수준)
* 기존 settings.json 있는 조달 → 원본 바이트 보존 + `settings.core.json` 생성 + 경고 출력
* 멱등: 동일 조달 2회 = 동일 결과

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-08-03 | 워크스페이스 조달 settings.json 병합 정책 v1 (보수적 보존) | `[x]` 완료 | `workspace_provision.sh` Tier 0 복사에 존재 여부 분기 추가 — 없으면 현행대로 복사, 있으면 원본 보존 + `settings.core.json` 병치 + 경고 로그(`SETTINGS_PRESERVED` 요약 안내 포함). `test_workspace_provision.py` 신규 pytest 3개(신규조달/보존/멱등) 전부 통과. |