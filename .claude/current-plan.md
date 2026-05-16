## 목표
docs/pipeline-guide.md에 `webhook-doctor.sh` 사용법을 추가한다.

## 변경 파일 목록
- `docs/pipeline-guide.md`:
  - "1. Webhook — 실시간 자동 트리거" 섹션 상단에 빠른 시작 박스로 webhook-doctor.sh 안내 추가
  - 기존 수동 nohup 명령은 "수동 기동(레거시)"로 강등
  - "스크립트 참조" 표에 `webhook-doctor.sh`, `webhook_doctor_linear_check.py` 추가

## 구현 단계
1. pipeline-guide.md의 webhook 시작 방법 섹션을 doctor 중심으로 재구성
2. 스크립트 참조 표에 신규 스크립트 2개 행 추가

## 예상 영향 범위
- 문서만 수정 — 동작/스크립트 영향 없음

## STATUS: APPROVED
