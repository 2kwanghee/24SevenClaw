# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] PrototypeService 구현 (세션/프로토타입 관리)**
  > 요청사항: app/services/prototype_service.py 신규 작성.

* create_session(user_id, org_id, prompt) → 세션 생성 + status=pending
* analyze_requirements(session_id) → ClaudeService.analyze_solution 호출 → parsed_requirements 저장
* generate_prototypes(session_id) → 3\~4개 비동기 생성 (BackgroundTasks)
* get_session(session_id) → 세션 + 프로토타입 목록 조회
* select_prototype(session_id, prototype_id) → 선택 저장
* get_generation_status(session_id) → 생성 진행률 반환

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] PrototypeService 구현 | ✅ 완료 | 기존 구현 검증 + 테스트 11개 통과 |