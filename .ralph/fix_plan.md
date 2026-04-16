# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] 비동기 프로토타입 생성 구조 (BackgroundTasks)**
  > 요청사항: FastAPI BackgroundTasks로 프로토타입 비동기 생성 구현.

POST /prototype-sessions/{id}/prototypes/generate 호출 시:

1. session.status = "generating" 저장
2. BackgroundTasks에 generate_prototypes 등록
3. 즉시 { task_id, status: "generating" } 응답

백그라운드 태스크:

1. ClaudeService.generate_ui_structure(requirements, variant_index) × 3\~4회
2. 각 결과를 Prototype 레코드로 저장 (status: ready)
3. 모두 완료 시 session.status = "completed"
4. 실패 시 해당 prototype.status = "failed"

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|