# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web+api] Linear/Notion API Key 유효성 검증 및 초기 태스크 자동 등록**
  > 요청사항: ## 배경

위저드 Step 8에서 사용자가 Linear/Notion API Key를 입력하지만, 현재는 **빈 문자열 여부만 체크**한다. 잘못된 Key를 입력해도 다음 단계로 넘어갈 수 있고, AI Team이 실제 이슈를 생성하려 할 때 비로소 오류가 발생하는 구조다.

또한 프로젝트가 최초 생성될 때 연동된 Linear/Notion에 **성공 확인 태스크**가 자동으로 등록되어야 하지만 해당 프로세스가 없다.

## 목표

1. **API Key 유효성 실시간 검증** — 입력 즉시 백엔드를 통해 실제 API를 호출해 key가 유효한지 확인
2. **초기 태스크 자동 등록** — 프로젝트 finalize 완료 시 연동된 Linear/Notion에 "프로젝트 생성 완료" 태스크를 자동 등록

## 범위

* clickeye-api: 유효성 검증 엔드포인트 2개 + finalize 후 초기 태스크 등록 로직
* clickeye-web: Step 8 UI에 실시간 검증 피드백 (로딩 → 성공/실패 뱃지)

## 하위 티켓

* \[api\] Linear API Key 유효성 검증 엔드포인트
* \[api\] Notion API Key 유효성 검증 엔드포인트
* \[api\] 프로젝트 finalize 시 초기 태스크 자동 등록
* \[web\] Step 8 실시간 Key 유효성 검증 UI

## 완료 기준

- 잘못된 Linear API Key 입력 시 Step 8에서 즉시 에러 표시, 다음 버튼 비활성
- 잘못된 Notion API Key / DB ID 입력 시 동일하게 에러 표시
- 프로젝트 생성 완료 후 Linear에 "프로젝트 생성 완료" 이슈가 자동 등록됨을 확인
- 프로젝트 생성 완료 후 Notion에 동일한 페이지가 자동 등록됨을 확인

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-22 | Linear/Notion API Key 유효성 검증 + 초기 태스크 자동 등록 | ✅ 완료 | api: integrations.py, notion_service.py / web: step-solution-env.tsx, wizard-store |