# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[api] 성숙도 질문지 + 스코어링 엔진**
  > 요청사항: ## 개요

성숙도 평가 질문지와 스코어링 엔진을 확장 구현한다. 7개 질문(팀규모, CI/CD, 테스트, 배포빈도, AI도구 등) 카테고리별 가중치 적용.

## 선행 조건

* [24S-76](https://linear.app/flow-ops/issue/24S-76/api-프리셋-카탈로그-db-서비스-api) (프리셋 카탈로그 API) 완료 필수

## 범위

* services/maturity_service.py 확장: 질문지 데이터, 가중평균 스코어링 (0-100 -> starter/intermediate/advanced)
* GET /api/v1/maturity/questions (인증 불요)
* POST /api/v1/maturity/assess (응답 제출 -> 스코어 + 프리셋 추천)
* GET /api/v1/maturity/me (최근 평가 조회)
* auth_service.py: 회원가입 시 maturity_required 플래그 반환

## 완료 조건

- 질문지 반환 엔드포인트
- 스코어링 알고리즘 정확성 테스트
- 프리셋 추천 연동
- 회원가입 플래그 동작

## 크기: M

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|