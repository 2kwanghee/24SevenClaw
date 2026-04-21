# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[guide] 사용자 가이드 콘텐츠 3종 작성**
  > 요청사항: 사용자가 선택한 3개 주제의 마크다운 가이드 문서 작성.

신규 파일:

1. docs/user-guide/wizard-7-step.md — 7-Step 솔루션 위저드 사용법 (각 스텝 입력 항목·예시·흔한 실수, 참조: src/components/solutions/wizard/steps/step-\*.tsx)
2. docs/user-guide/ai-team-management.md — AI Team 관리 (draft 자동 생성, Linear 동기화 힌트, 역할 할당, 참조: src/app/(dashboard)/projects/\[projectId\]/ai-team/page.tsx)
3. docs/user-guide/linear-integration-setup.md — Linear 연동 설정 (API 키 등록, webhook 설정, DayQueued 플로우, 기존 docs/user-guide/linear-realtime-tracking.md 재활용)

의존: CLK-6(24S-185) 완료 후 진행.

검증: /guide에서 3개 가이드 모두 조회 가능, 내부 링크가 실제 페이지로 연결.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | [guide] 사용자 가이드 콘텐츠 3종 작성 | ✅ 완료 | wizard-7-step.md, ai-team-management.md, linear-integration-setup.md 신규 작성 |