# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] 프리뷰 API (파일 트리 + 내용 생성)**
  > 요청사항: ## 목표

위저드 설정 기반 파일 트리 + 내용 프리뷰 생성 API

## 작업 내용

* POST /api/v1/projects/{id}/preview
* 요청: 위저드 설정 전체 (organization, solution, agents, skills, pipelines, platform)
* 생성 엔진 호출 → 메모리에서 파일 생성
* 응답: { fileTree: \[...\], files: { "[CLAUDE.md](<http://CLAUDE.md>)": "내용...", ... } }
* 플랫폼별 구조 반영 (.claude/ vs .cursor/rules/ 등)

## 사이즈: M

## 일정: 04-15 \~ 04-16

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|