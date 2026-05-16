## 목표
Linear 관련 두 영역(별도 카드 'Linear 연동 상태' + ZIP 다운로드 카드 안의 Linear 키 입력/검증)을 한 카드로 통합한다. 사용자에게는 한 곳에서 "서버 자동화용 저장 자격증명 + ZIP 다운로드용 키 입력/라이브 검증"이 모두 보여야 한다.

## 변경 파일 목록
- `clickeye-web/src/app/(dashboard)/projects/[projectId]/page.tsx`:
  - `LinearPreflightCard` 별도 호출 위치(line 683~689) 제거
  - ZIP 다운로드 카드(IIFE) 첫 안내 문구 다음에 `hasLinear` 분기로 동일 컴포넌트를 카드 내부에 임베드
  - `LinearPreflightCard` 컴포넌트에 `compact?: boolean` prop 추가 — true면 외부 박스/그림자 제거 + 패딩·간격 축소(안쪽 sub-card 스타일)

## 구현 단계
1. `LinearPreflightCard`에 compact 모드 분기 추가 (className 토글)
2. 메인 페이지의 별도 호출 제거
3. ZIP 카드 안 hasLinear 영역에 임베드 호출 추가 (compact)
4. typecheck + lint

## 예상 영향 범위
- review_pipeline·setup_bootstrap의 서버 자동화 자격증명 흐름은 그대로 — 표시 위치만 변경
- 사용자 혼란 감소: Linear 관련 정보가 한 카드로 통합
- LinearPreflightCard의 새로고침 버튼·"AI Team 시작하기" 액션 모두 유지
- 시각적 통일감 — outer 카드 + inner sub-card(compact) 계층 명확

## STATUS: APPROVED
