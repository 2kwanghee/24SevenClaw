---
route: /solutions/new (Step 0) / /solutions/[sessionId] (Step 0)
title: 회사 정보 + 솔루션 요청
category: page
status: implemented
version: 1.3.0
components:
  - src/components/solutions/wizard/steps/step-company-solution.tsx
store: useSolutionWizardStore → setCompany, setStep0Valid
last_updated: 2026-06-15
---

## 목적
회사 기본 정보, 기술 스택, 그리고 자연어 솔루션 요구사항을 수집하여 AI 설계의 입력값을 초기화. 우측 패널에서 솔루션 요청 분석(Claude NL 분석)을 실시간으로 표시.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────────────┐
│ [좌측 폼] (2/3)      │  [우측 라이브 프리뷰 패널] (1/3)        │
├──────────────────────┤                                         │
│ 회사명 *             │  회사 청사진 (Claude 분석)              │
│ [입력 필드]          │  solutionRequest 기반 NL 분석 결과:     │
│                      │                                         │
│ 회사 규모 *          │  - 추론 기반 산업(industry)            │
│ [버튼 그룹: 5개]     │  - 기술 스택 추천(techStack)            │
│                      │  - 타겟 사용자(target_users)           │
│ 업종 *               │  - 주요 기능(features)                 │
│ [태그 버튼 그룹]     │  - 근거(reasoning)                     │
│                      │                                         │
│ 기술 스택 (선택)     │  [스켈레톤 or 분석 결과]                │
│ [4개 카테고리 버튼]  │                                         │
│                      │                                         │
│ 주력 제품/서비스 *   │                                         │
│ [입력 필드]          │                                         │
│                      │                                         │
│ 비즈니스 유형 *      │                                         │
│ [4개 버튼]           │                                         │
│                      │                                         │
│ 회사 설명 (선택)     │                                         │
│ [Textarea]           │                                         │
│                      │                                         │
│ 솔루션 요청 * (≥50자) │                                         │
│ [Textarea]           │                                         │
│ N / 2000             │                                         │
│                      │                                         │
│ ☑ 자동 분해 활성화   │                                         │
│   ZIP에 bootstrap    │                                         │
│   모듈 포함          │                                         │
└──────────────────────┴─────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 정상 입력 + 라이브 프리뷰**
1. 필수 필드들 입력 (회사명, 규모, 업종, 주력제품, 비즈니스유형)
2. 기술 스택 선택 (선택 사항)
3. 솔루션 요청 textarea에 50자 이상 입력
4. (우측 패널) useWizardPreview 훅이 700ms 디바운스로 Claude 분석 호출
   - sessionStorage(NL_ANALYSIS_STORAGE_KEY)에 분석 결과 저장
   - industry, techStack, companyDescription 자동 프리필
5. canProceed = step0Valid (모든 필수 필드 유효) → "다음" 버튼 활성화
6. "다음" 클릭 → Step 1로 이동

**시나리오 2: 유효성 실패**
- 필수 필드 미입력 시 "다음" 버튼 비활성화
- 솔루션 설명 50자 미만 시 글자 수 카운터 빨간색 표시

**시나리오 3: 자동 분해 토글**
- `enableAutoDecompose=true` → ZIP 다운로드 시 `/bootstrap/` 모듈 포함

---

## 기능 요구사항

- [x] 회사명 텍스트 입력 (필수)
- [x] 회사 규모 Select (5개: startup / small / medium / mid-large / enterprise)
- [x] 업종 Select (10개: it / fintech / ecommerce / healthcare / education / manufacturing / logistics / marketing / game / other)
- [x] 주력 제품/서비스 입력 (필수, ≤500자)
- [x] 비즈니스 유형 Select (4개: b2b / b2c / b2b2c / internal, 아이콘 포함)
- [x] 기술 스택 멀티 선택 (4개 카테고리, 다중 선택 가능)
  - 미선택 시: 백엔드가 최적 스택 자유롭게 제안
  - 선택 시: Variant 0(추천)은 선택 스택 사용, Variant 1~2는 대안 스택 생성
- [x] 회사 설명 textarea (선택, ≤1000자)
- [x] 솔루션 요청 textarea (필수, 50~2000자)
- [x] 글자 수 실시간 카운터 + 최소 50자 기준 시각화
- [x] 자동 분해 토글 (`enableAutoDecompose`, 기본값: false)
- [x] 라이브 프리뷰 패널 (우측, Claude 분석 결과 표시)
  - solutionRequest 기반 디바운스 분석 호출
  - 결과: industry, techStack, companyDescription 자동 프리필
  - sessionStorage prefill → mount 시 1회 소비
- [x] 필수 필드 미충족 시 다음 버튼 비활성화

---

## 상태 관리

| 상태 | 타입 | 출처 | 설명 |
|------|------|------|------|
| `isValid` | `boolean` | React Hook Form | 폼 전체 유효성 |
| `setStep0Valid` | `fn` | `useSolutionWizardStore` | 다음 버튼 활성화 제어 |
| `setCompany` | `fn` | `useSolutionWizardStore` | 폼 값 → 스토어 동기화 |
| `NL_ANALYSIS_STORAGE_KEY` | `sessionStorage` | `useWizardPreview` hook | Claude 분석 결과 캐시 |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `POST` | `apiClient.wizardNL.analyze` | 700ms 디바운스 | Claude 자연어 분석 |

---

## 접근성 / 반응형

- [x] 모든 입력 필드 `label` 연결
- [x] 필수 항목 `*` 표시 (빨간색)
- [x] 에러 메시지 `aria-describedby` 연결
- [x] 모바일 우선 레이아웃: sm:grid-cols-1 → lg:grid-cols-2 (우측 패널)
- [x] Sparkles 아이콘으로 라이브 프리뷰 시각적 표시

---

## 구현 노트

- **[v1.3]** 라이브 프리뷰 패널 추가: `useWizardPreview('company', ...)` 훅이 solutionRequest 변경 시 700ms 디바운스로 Claude 분석 호출. 결과는 sessionStorage(NL_ANALYSIS_STORAGE_KEY)에 저장되고 mount 시 `consumeNlAnalysisPrefill()` 함수로 1회만 소비되어 form 기본값에 병합.
- `watch()` 대신 JSON.stringify 직렬화로 배열 참조 변경 문제 회피
- `getState()`로 초기값 1회만 읽음 (reactive 구독 금지 — 무한 루프 방지)
- `defaultValues`는 RHF mount 시에만 적용되므로 이후 store 변경이 폼을 덮어쓰지 않음
- **[v1.2]** 자동 분해 토글: `enableAutoDecompose` boolean 필드로 ZIP 다운로드 시 bootstrap 포함 여부 제어
- **[v1.2]** StepCompanySolution은 `/solutions/new`와 `/solutions/[sessionId]` 양쪽에서 공통 사용
