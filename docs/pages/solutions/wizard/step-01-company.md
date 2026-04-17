---
route: /solutions/new (Step 0) / /solutions/[sessionId] (Step 0)
title: 회사 정보 + 솔루션 요청
status: implemented
version: 1.2.0
components:
  - src/components/solutions/wizard/steps/step-company-solution.tsx
store: useSolutionWizardStore → setCompany (getState()로 초기값 읽기)
last_updated: 2026-04-17
---

## 목적
회사 기본 정보와 원하는 솔루션 요구사항을 자연어로 입력받아 AI 설계의 입력값을 수집.

> **[v1.2]** `StepCompanySolution` 컴포넌트가 `/solutions/new`와 `/solutions/[sessionId]` 양쪽에서 공통으로 사용되는 단일 컴포넌트로 통합됨.

---

## 레이아웃

```
┌─────────────────────────────────────────┐
│ 회사명 *              [입력 필드]         │
├──────────────────────┬──────────────────┤
│ 회사 규모 *           │ 업종 *           │
│ [Select]             │ [Select]         │
├──────────────────────┴──────────────────┤
│ 주력 제품/서비스 *    [입력 필드]         │
├──────────────────────┬──────────────────┤
│ 비즈니스 유형 *       │ 기술 스택 (선택)   │
│ [Select]             │ [MultiTag]       │
├──────────────────────┴──────────────────┤
│ 회사 설명 (선택)      [Textarea]         │
├─────────────────────────────────────────┤
│ 원하는 솔루션 설명 *  [Textarea, 50자↑]  │
│ 현재 N자 / 최소 50자                     │
└─────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 정상 입력**
1. 회사명, 규모, 업종, 주력제품, 비즈니스 유형 선택
2. 기술 스택 태그 입력 (Enter로 추가)
3. 솔루션 설명 50자 이상 입력 → canProceed = true
4. "다음" 클릭 → Step 0 완료

**시나리오 2: 유효성 실패**
- 필수 필드 미입력 시 "다음" 버튼 비활성화
- 솔루션 설명 50자 미만 시 글자 수 카운터 빨간색 표시

---

## 기능 요구사항

- [x] 회사명 텍스트 입력 (필수)
- [x] 회사 규모 Select (startup / small / medium / mid-large / enterprise)
- [x] 업종 Select (it / fintech / ecommerce / healthcare / education / manufacturing / logistics / marketing / game / other)
- [x] 주력 제품/서비스 입력 (필수)
- [x] 비즈니스 유형 Select (b2b / b2c / b2b2c / internal)
- [x] 기술 스택 멀티 태그 입력 (선택 사항)
  - 입력하지 않으면: 백엔드가 최적 스택을 자유롭게 제안 (Variant 0~2 모두 백엔드 선택)
  - 입력하면: Variant 0(추천 프로토타입)이 해당 스택을 사용; Variant 1~2는 대안 스택으로 생성
- [x] 회사 설명 textarea (선택)
- [x] 솔루션 요청 textarea (필수, 50자 이상)
- [x] 글자 수 실시간 카운터 + 최소 기준 시각화
- [x] 필수 필드 미충족 시 다음 버튼 비활성화
- [ ] 회사명 기반 자동완성 (향후)
- [ ] 이전에 입력한 조직 정보 불러오기 (재방문 시)

---

## 상태 관리

| 상태 | 타입 | 출처 |
|------|------|------|
| `initialCompany` | `CompanyStep` | `useSolutionWizardStore.getState()` (구독 없이 1회 읽기) |
| `setCompany` | `fn` | `useSolutionWizardStore` |

---

## 접근성 / 반응형

- [x] 모든 입력 필드 `label` 연결
- [x] 필수 항목 `*` 표시
- [x] 에러 메시지 `aria-describedby` 연결
- [ ] 기술 스택 태그 입력 — 키보드로 태그 삭제 (Backspace)

---

## 구현 노트

- **[v1.1 버그 수정]** `company`를 reactive selector로 구독하면 `setCompany` → store 업데이트 → 리렌더 → `watch()` 재실행 → `techStack` 배열 참조 변경 → `useEffect` 재실행 → 무한 사이클 → "다음" 버튼 미활성화. `getState()`로 초기값 1회만 읽도록 수정.
- `watch()` 전체 객체 대신 개별 필드 watch 사용 (`watch("fieldName")`) — 배열 참조 변경 문제 회피
- `defaultValues`는 RHF 마운트 시에만 적용되므로 이후 store 변경이 폼을 덮어쓰지 않음
- **[v1.2]** `StepCompanySolution`은 `/solutions/new`와 `/solutions/[sessionId]` 라우트에서 공통으로 사용하는 통합 컴포넌트. 라우트별 분기 없이 store 값만으로 동작.
