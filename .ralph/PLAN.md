# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] ZIP 생성 API (스트리밍 + .env 포함)**
  > 요청사항: ## 목표

위저드 설정 + API 키 기반 ZIP 파일 스트리밍 다운로드

## 작업 내용

* POST /api/v1/projects/{id}/generate
* 요청: 위저드 설정 + envVars (API 키 맵)
* 생성 엔진으로 파일 생성 → Python zipfile로 ZIP 패키징
* .env 파일: 클라이언트에서 전달된 키만 포함 (서버 미저장)
* .env.example: 변수명만 포함 (값 제외)
* Content-Type: application/zip 스트리밍 응답
* 파일명: {projectName}.zip

## 보안: API 키는 메모리에서만 처리, DB/로그에 기록하지 않음

## 사이즈: M

## 일정: 04-15 \~ 04-16

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|