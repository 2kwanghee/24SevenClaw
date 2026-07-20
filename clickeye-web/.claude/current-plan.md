## 목표
Next 16에서 제거된 `next lint`로 인한 CI "Web (lint)" 실패를 복구한다. flat config에 `@typescript-eslint` 플러그인을 올바르게 등록하고 lint 스크립트를 `eslint .`로 전환한다.

## 변경 파일 목록
- eslint.config.mjs: 커스텀 룰 config object에 `@typescript-eslint` 플러그인 등록(typescript-eslint 임포트)
- package.json: `"lint": "next lint"` → `"eslint ."`, devDep에 `typescript-eslint` 명시 추가

## 구현 단계
1. eslint.config.mjs를 Next 16 flat config 정석으로 수정 (플러그인 등록 후 no-unused-vars warn 룰 적용)
2. package.json lint 스크립트 교체
3. typescript-eslint를 명시적 devDep로 설치(hoisting 의존 제거)
4. npm run lint exit 0까지 교정
5. npm run typecheck / build 회귀 확인

## 예상 영향 범위
lint 설정과 package.json 스크립트만 변경. 소스 로직 무변경. 백엔드 무관.

## STATUS: APPROVED
