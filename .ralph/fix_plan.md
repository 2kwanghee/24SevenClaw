# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[guide] 첫 방문 인터랙티브 투어 (react-joyride)**
  > 요청사항: react-joyride 설치 및 첫 방문 시 자동 실행되는 온보딩 투어 구현.

신규 패키지: react-joyride (Next.js 15 app router 호환).

신규 파일:

* 24SevenClaw-web/src/stores/onboarding-store.ts (zustand persist, tourCompleted 플래그, theme-store.ts 패턴 복제)
* 24SevenClaw-web/src/components/onboarding/tour.tsx (react-joyride 래퍼 컴포넌트)
* 24SevenClaw-web/src/components/onboarding/tour-steps.ts (투어 단계 정의)

수정 파일:

* src/app/(dashboard)/layout.tsx — 첫 방문 감지 시 투어 자동 실행
* src/components/layout/header.tsx — Help 아이콘 드롭다운 확장 ('가이드 보기' / '튜토리얼 다시 시작')

투어 단계 (4-5단계):

1. 대시보드 개요 (사이드바 네비게이션)
2. 새 솔루션 만들기 → 위저드 진입
3. Settings → Linear 연동
4. Projects → AI Team 화면
5. Help 아이콘 → /guide 안내

의존: CLK-6(24S-185) 완료 후 진행.

검증: localStorage.clear() → 대시보드 진입 → 투어 자동 시작, 완료 후 tourCompleted:true 저장, Help에서 재실행.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | [guide] 첫 방문 인터랙티브 투어 | 완료 | react-joyride v3, onboarding-store, TourWrapper, HelpDropdown |