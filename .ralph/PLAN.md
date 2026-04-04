# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [ ] **[api] ProjectConfig 모델 확장 (JSONB 위저드 결과)**
  > 요청사항: ## 목표

위저드 전체 결과를 저장하는 ProjectConfig 모델 확장

## 작업 내용

* ProjectConfig에 wizard_data JSONB 컬럼 추가
* POST /api/v1/projects/{id}/config — 위저드 설정 저장
* GET /api/v1/projects/{id}/config — 위저드 설정 조회
* wizard_data 스키마: { organization, solution, agents, skills, pipelines, platform }

## 사이즈: S

## 일정: 04-07 \~ 04-08

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|