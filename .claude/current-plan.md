## 목표
최종 확인(case 11) 단계의 "이대로 진행" 버튼이 라이브 검증 결과 invalid 인 경우에도 활성화되는 문제 보강. step 9와 동일한 게이트 정책(invalid 만 차단)을 case 11 에도 적용한다.

## 변경 파일 목록
- `clickeye-web/src/app/(dashboard)/solutions/new/page.tsx`:
  - canProceed 의 case 11 추가 — Linear/Notion 검증이 invalid 면 false
- `clickeye-web/src/app/(dashboard)/solutions/[sessionId]/page.tsx`:
  - 동일 변경

## 구현 단계
1. new/page.tsx 의 case 10 다음에 case 11 추가
2. [sessionId]/page.tsx 의 동일 위치에 추가
3. typecheck + lint

## 예상 영향 범위
- step 11 의 "이대로 진행" 버튼이 invalid 일 때 비활성화됨.
- idle/loading/valid 는 통과 (step 9 정책과 일치).
- 검증 결과가 step 9 에서 valid 인 채 step 11 에 도달한 사용자에게는 영향 없음.

## STATUS: APPROVED
