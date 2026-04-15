# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[agent] contract.sync 에이전트 핸들러**
  > 요청사항: ## 개요

에이전트가 contract.sync 메시지를 수신하여 중앙 계약 + 프로젝트 오버라이드를 머지하고 로컬에 저장하는 핸들러를 구현한다.

## 선행 조건

* [24S-72](https://linear.app/flow-ops/issue/24S-72/contracts-중앙-계약-타입-스키마-정의) (중앙 계약 타입) 완료 필수

## 범위

* handlers/contract_handler.py 신규: contract.sync 수신, CentralContract + Override 머지, $data_dir/contracts/{slug}.json 저장
* [dispatcher.py](<http://dispatcher.py>) 수정: ContractHandler 등록

## 완료 조건

- contract.sync 메시지 파싱 및 처리
- allowed_overrides 우선 적용 머지 로직
- 로컬 파일 저장 확인

## 크기: S

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|