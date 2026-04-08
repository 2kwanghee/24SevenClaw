# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [ ] **[infra] CI 파이프라인에 테스트 실행 + 보안 스캔 추가**
  > 요청사항: ## 목표

CI에서 테스트 실행과 의존성 보안 스캔을 자동화한다.

## 현황

* ci.yml에 lint/typecheck/build만 있고 pytest/npm test 실행 없음
* 보안 스캔 (npm audit, pip-audit) 없음
* PR #15 CI 실패 원인: Detect Changes 토큰 권한 부족 + OPENAI_API_KEY 누락

## 작업 내용

* ci.yml API Job에 `uv run pytest --cov=app` 추가
* ci.yml에 `npm audit --audit-level=high` 스텝 추가
* ci.yml permissions에 `pull-requests: read` 추가 (Detect Changes 수정)
* GPT Code Review의 OPENAI_API_KEY 시크릿 등록 또는 옵션 처리

## 사이즈: S

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|