# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[agent] 에이전트 프리셋 동적 수신 핸들러**
  > 요청사항: ## 개요

에이전트가 Cloud로부터 config.update 메시지를 수신하여 프리셋 설정을 동적으로 적용하는 핸들러를 구현한다.

## 선행 조건

* \[api\] 프리셋 카탈로그 API 완료 필수

## 범위

* handlers/config_handler.py 신규: config.update 메시지 처리, 로컬 SQLite 저장, 리로드 시그널
* [dispatcher.py](<http://dispatcher.py>) 수정: config_handler 등

## 완료 조건

- config.update 메시지 수신 및 파싱
- 로컬 설정 저장 및 리로드
- 기존 핸들러와 충돌 없음

## 크기: S

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|