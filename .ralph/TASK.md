# Ralph Task — 구현 결과

## [web] 성숙도 온보딩 흐름 UI

### 변경 파일

**신규 생성:**
- `24SevenClaw-web/src/hooks/use-maturity-assessment.ts` — TanStack Query 기반 API 훅 (질문 조회 + 평가 제출)
- `24SevenClaw-web/src/components/onboarding/maturity-questionnaire.tsx` — 5카테고리 질문지 UI (진행률 바, 카테고리 인디케이터, 라디오 선택)
- `24SevenClaw-web/src/components/onboarding/maturity-result.tsx` — 결과 화면 (점수 카운트업 애니메이션, 성숙도 배지, 추천 프리셋 CTA)
- `24SevenClaw-web/src/app/(dashboard)/onboarding/maturity/page.tsx` — 온보딩 성숙도 평가 페이지

**수정:**
- `24SevenClaw-web/src/app/(auth)/register/page.tsx` — 회원가입 후 리다이렉트를 `/onboarding/maturity`로 변경 (이메일 + 소셜 로그인)

### 구현 내용

1. **질문지 UI**: API에서 질문 로드 → 5개 카테고리(팀/프로세스/도구/CI·CD/AI)별 스텝 진행 → 진행률 바 + 카테고리 아이콘 인디케이터
2. **결과 화면**: 점수 0→N 카운트업 애니메이션 (ease-out cubic) → 성숙도 배지 표시 → 분석 결과(reasoning) → "추천 프리셋 보기" / "설정 직접 선택하기" CTA
3. **리다이렉트 흐름**: 회원가입(이메일) → 로그인 → `/onboarding/maturity` | 회원가입(소셜) → `/onboarding/maturity`
4. **스킵 링크**: 헤더에 "건너뛰고 직접 설정하기" → `/projects/new` 위저드

### 테스트 결과

- TypeScript 타입체크: ✅ 통과 (기존 .next/types 캐시 에러 제외)
- Next.js 빌드: ✅ 통과 (`/onboarding/maturity` 라우트 정상 생성)
- ESLint: next lint 명령 이슈 (Next.js 16 호환성, 기존 이슈)

### 남은 이슈

- `next lint` 명령이 Next.js 16에서 인자 파싱 문제 (기존 이슈, 본 작업과 무관)
- 기존 사용자의 재접근 시 이미 평가 완료 여부 확인 로직 미구현 (향후 API에 maturity_required 플래그 추가 시 대응)
