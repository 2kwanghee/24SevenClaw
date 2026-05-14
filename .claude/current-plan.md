## 목표
Resume Dialog의 각 세션 카드에 삭제 버튼을 추가하여, 진행 중인 세션을 개별 삭제할 수 있도록 한다.

## 변경 파일 목록
- `clickeye-web/src/app/(dashboard)/solutions/new/page.tsx`:
  1. lucide-react import에 `Trash2` 추가
  2. `handleDeleteSession` 함수 추가 (API 호출 → 목록 업데이트 → 목록이 비면 다이얼로그 닫기)
  3. Resume Dialog의 각 세션 카드를 외부 `<div>` + 내부 resume `<button>` + 삭제 `<button>` 구조로 변경

## 구현 단계
1. `Trash2` 아이콘 import 추가 (6번 줄)
2. `handleResumeSession` 직후에 `handleDeleteSession` async 함수 추가
3. 각 세션 카드를 `<div group>` → 내부 resume button + 호버 시 나타나는 trash button 구조로 재작성

## 예상 영향 범위
- Resume Dialog UI만 변경, 위저드 로직 및 다른 기능에 영향 없음
- 삭제 성공 시 목록에서 즉시 제거, 목록 비면 다이얼로그 자동 닫힘
- 삭제 실패 시 toast 에러 표시
