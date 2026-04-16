# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] prototype_sessions 라우터 구현**
  > 요청사항: app/api/v1/prototype_sessions.py 신규 작성. 8개 엔드포인트.

* POST /prototype-sessions (세션 생성)
* GET /prototype-sessions/{id} (세션 조회)
* PATCH /prototype-sessions/{id} (선택/스텝 업데이트)
* GET /prototype-sessions/{id}/status (생성 진행률)
* GET /prototype-sessions/{id}/prototypes (프로토타입 목록)
* POST /prototype-sessions/{id}/prototypes/generate (생성 트리거)
* POST /prototype-sessions/{id}/recommend-pms (PM 추천)
* POST /prototype-sessions/{id}/finalize (최종 프로젝트 생성)

router.py에 등록.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] prototype_sessions 라우터 구현 | ✅ 완료 | 8개 엔드포인트 구현, 356 tests pass |