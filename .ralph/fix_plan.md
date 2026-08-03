# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **pending_source → repo 소스 등재 플로우 v1 (workspace_map CLI)**
  > 요청사항: ## 배경

[CE-339](https://linear.app/flow-ops/issue/CE-339/3-다프로젝트-워크스페이스-조달-남의-프로젝트를-무인-구현할-실행면-후속) v1의 `.ralph/workspaces.json` 원장은 repo_source 미상 항목을 `pending_source`로 표기만 한다(추측 clone 금지). 현재 `mapped`로 전환하는 유일한 방법이 운영자의 JSON 수동 편집 — 절차·검증·멱등 보장이 없다.

## v1 범위 (소형)

`scripts/workspace_map.py`에 등재 서브커맨드 추가:

* `--set-source <ticket_prefix|workspace_key> <repo_source>` — 항목 존재 검증 후 repo_source 기입 + `status: mapped` 전환. 멱등(동일 명령 2회 = 파일 바이트 동일). 미존재 키는 에러(exit ≠ 0)로 거부 — 항목 창작 금지.
* `--list` — 원장 상태 요약(prefix / key / status / repo_source 유무) 출력.
* 폴링(`build_ledger`)의 수동 값 보존 규칙은 불변 — set-source로 기입한 값을 폴링이 덮어쓰지 않음(기존 동작 유지 확인).

## 변경 파일

* `scripts/workspace_map.py`
* `scripts/tests/test_workspace_map.py` (set-source 성공/멱등/미존재 거부/폴링 보존 테스트)

## 수용 기준

* set-source 후 `--resolve-title "[수주:xxxxxxxx] ..."`가 workspace_key를 반환(mapped 해석 성립)
* 동일 set-source 2회 → 파일 내용 동일
* 미존재 prefix/key → 비0 종료 + 원장 무변경

## v2 (범위 외)

인테이크 접수 폼 repo URL 필드 / 관리자 화면 등재 / 접근 자격 증명(deploy key) 관리 — 시트 풀 설계와 연계 후 별도.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-08-03 | pending_source → repo 소스 등재 플로우 v1 | `[x]` 완료 | `workspace_map.py`에 `set_source()`/`format_list()` + `--set-source`/`--list` CLI 추가. pytest 17개 전부 통과(신규 12개). |