# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[api] Phase 2 API 테스트 작성**
  > 요청사항: Phase 2 API 엔드포인트 pytest 테스트.

* tests/test_prototype_sessions.py: 세션 생성/조회/업데이트/프로토타입 목록 (최소 3개씩)
* tests/test_pm_profiles.py: PM 목록/상세/구성/평가 (최소 3개씩)
* ClaudeService mock 처리 (실제 API 호출 방지)

conftest.py에 PM 시드 데이터 fixture 추가.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] Phase 2 API 테스트 작성 | ✅ | test_prototype_sessions.py 11개, test_pm_profiles.py 12개 (총 23개 통과), conftest.py seeded_pm_profiles fixture 추가 |