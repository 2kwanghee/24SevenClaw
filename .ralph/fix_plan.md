# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[Phase 2] Solution Wizard v2 — 백엔드 서비스 + API**
  > 요청사항: ## 백엔드 서비스 레이어 + API 라우터 구현

### 신규 서비스

* ClaudeService (자연어 분석, UI 구조 생성, PM 추천)
* PrototypeService (세션 생성, 프로토타입 생성, 선택)
* PMService (추천, 구성 조회, 평가)

### 신규 API 라우터

* prototype_sessions.py (8개 엔드포인트)
* pm_profiles.py (5개 엔드포인트)
* [router.py](<http://router.py>) 등록

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | Phase 2: 백엔드 서비스 + API | ✅ | 3 서비스 + 2 라우터(13 엔드포인트) + 22 테스트 |