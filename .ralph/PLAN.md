# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [ ] **[api] Organization 모델 + API 구현**
  > 요청사항: ## 목표

Organization 모델 생성 및 API 구현

## 작업 내용

* Organization 모델 생성 (company_name, size, industry, tech_stack)
* POST /api/v1/organizations — 회사 정보 등록/수정
* GET /api/v1/organizations/me — 내 회사 정보 조회
* User ↔ Organization 1:1 관계 설정
* Pydantic 스키마 정의

## 사이즈: M

## 일정: 04-07 \~ 04-08

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|