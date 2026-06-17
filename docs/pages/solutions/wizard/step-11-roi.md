---
route: /solutions/[sessionId] (Step 10)
title: ROI 비교 (도입 효율 가치)
category: page
status: implemented
version: 1.0.0
components:
  - src/components/solutions/wizard/steps/step-solution-roi.tsx
store: useSolutionWizardStore → setRoi
last_updated: 2026-06-15
---

## 목적
전통적인 팀 개발 방식과 ClickEye를 통한 AI 자동화 개발의 비용·기간을 비교. 솔루션 복잡도, 선택한 에이전트·스킬·훅 수를 바탕으로 자동 산출하며, 역할별 단가를 실시간 조정 가능.

---

## 레이아웃

```
┌────────────────────────────────────────────────────┐
│ ROI 비교: 도입 효율 가치                             │
│ 전통 팀 개발 vs ClickEye 자동화 효율을 비교합니다.   │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────────────┐  ┌──────────────────────┐
│  │ 👥 기존 인력 방식    │  │ ⚡ ClickEye 자동화   │
│  │ 비용: ₩250,000,000  │  │ 비용: ₩50,000,000   │
│  │ 기간: 120일          │  │ 기간: 30일          │
│  └──────────────────────┘  └──────────────────────┘
│
│  ┌────────────────────────────────────────────────┐
│  │ 💰 절감 효과                                    │
│  │ 절감액: ₩200,000,000                           │
│  │ 절감률: 80%                                    │
│  │                                                │
│  │ 진행도:                                        │
│  │ 기존:  |████████████████████| 100%             │
│  │ AI:    |████| 20%                             │
│  └────────────────────────────────────────────────┘
│
│  역할별 공수 명세 + 단가 조정                       │
│  ┌────────────────────────────────────────────────┐
│  │ 직군 │ 일당 (기본) │ 공수(일) │ 소계          │
│  ├─────┼────────────┼─────────┼──────────────┤
│  │ PM  │ ₩500,000  │ 10일    │ ₩5,000,000  │
│  │ (✎ 조정) [Adjusted 배지]                      │
│  │ BE  │ ₩400,000  │ 40일    │ ₩16,000,000 │
│  │ (✎ 수정 가능)                                 │
│  │ FE  │ ₩350,000  │ 30일    │ ₩10,500,000 │
│  │ QA  │ ₩300,000  │ 15일    │ ₩4,500,000  │
│  │ Designer│₩350,000│ 5일    │ ₩1,750,000  │
│  │                    합계: ₩250,000,000     │
│  │                                              │
│  │ [일당 수정] [전체 리셋]                       │
│  └────────────────────────────────────────────────┘
│
└────────────────────────────────────────────────────┘
```

---

## 기능 요구사항

### 자동 계산 및 표시
- [x] API `roi.calculate` 호출
  - [x] 입력: solution_type, complexity, selected_agents_count, selected_skills_count, selected_hooks_count, platform_id, overrides
  - [x] 출력: baseline_cost, clickeye_cost, savings, savings_ratio(KRW), baseline_days, clickeye_days, breakdown(역할별), rates_snapshot, formula_version
- [x] 마운트 시 자동 계산 (저장된 결과 없을 때)
- [x] 비교 카드 2개 (기존 인력 비용 vs ClickEye 비용)
- [x] 절감액 강조 카드 (절감액 + 절감률(%) + 진행도 막대그래프 2개)

### 역할별 명세표
- [x] 테이블: 직군(PM, BE, FE, QA, Designer) × 일당 × 공수 × 소계
- [x] 각 행의 일당은 인라인 편집 가능 (`contentEditable` 또는 입력 필드)
- [x] 편집 시 "Adjusted" 배지 표시
- [x] 400ms 디바운스 후 자동 재계산
- [x] "[전체 리셋]" 버튼 → 오버라이드 클리어 후 재계산

### 상태 및 에러 처리
- [x] 로딩 상태: 스피너 표시
- [x] 에러 발생 시: 에러 메시지 + 재시도 버튼
- [x] canProceed: roi.result 존재

---

## 스토리보드

**시나리오 1: 초기 로드 및 자동 계산**
1. 컴포넌트 마운트 → 저장된 roi.result 없음 → `roi.calculate` 호출
2. 입력:
   - `solution_type`: 선택한 프로토타입의 solution_type
   - `complexity`: 선택한 프로토타입의 complexity (low/medium/high)
   - `selected_agents_count`: agents.selectedAgents.length
   - `selected_skills_count`: agents.selectedSkills.length
   - `selected_hooks_count`: agents.selectedHooks.length
   - `platform_id`: platform.platformId
   - `overrides`: 없음 (첫 계산)
3. 응답 수신 후 비교 카드 + 명세표 + 막대그래프 렌더링
4. rates_snapshot에서 기본 일당값 표시

**시나리오 2: 역할별 단가 조정**
1. 사용자가 PM 일당(₩500,000) 편집 → ₩600,000으로 변경
2. 입력 필드는 `contentEditable` 또는 number input
3. 변경 감지 후 400ms 디바운스 → `roi.calculate` 재호출 (overrides 포함)
4. "PM [Adjusted 배지]" 표시 → 수정됨을 시각적으로 표현
5. 새로운 결과 렌더링 (합계 금액 업데이트)

**시나리오 3: 전체 리셋**
1. 사용자가 "[전체 리셋]" 버튼 클릭
2. overrideRates 전체 클리어
3. `roi.calculate` 호출 (overrides 없음)
4. rates_snapshot 기본값으로 복원
5. 모든 "Adjusted" 배지 제거

**시나리오 4: 에러 및 재시도**
1. API 호출 실패 → 에러 메시지 표시
2. 에러 옆 "재시도" 버튼 → 현재 설정으로 다시 계산

---

## 상태 관리

| 상태값 | 타입 | 설명 |
|--------|------|------|
| `result` | RoiCalculateResponse \| null | API 응답 스냅샷 (baseline_cost, clickeye_cost, savings 등) |
| `loading` | boolean | 계산 중 여부 |
| `error` | string \| null | 에러 메시지 |
| `overrideRates` | Record<string, string> | 역할별 단가 오버라이드 (편집 중) |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 | 주기 |
|--------|------|--------|------|------|
| `POST` | `roi.calculate` | 마운트 (저장된 결과 없음) | ROI 초기 계산 | 1회 |
| `POST` | `roi.calculate` | 역할별 단가 변경 | ROI 재계산 | 400ms 디바운스 |

---

## 접근성 / 반응형

- [x] 숫자 입력: `aria-label` with role description
- [x] 절감액 강조: 색상 + 텍스트로 의미 전달 (색상만 사용 금지)
- [x] 테이블: 헤더 행 명확 (th 태그)
- [x] 모바일: 막대그래프는 세로 방향 스택, 테이블은 스크롤 가능
- [x] 다크 모드: CSS 변수 적용 (--text-primary, --bg-surface 등)

---

## 구현 노트

- `formatKRW(value)`: 국내 통화 포맷 (₩ + 천 단위 쉼표)
- `formatDays(days, unit)`: 일단위 소수점 1자리 표시 + "일" 단위
- `buildOverrides(rates)`: 역할별 단가를 `role_rate.pm`, `role_rate.be` 형식으로 변환
- 저장된 ovrride는 roiState.overrides.roleRates 에서 복원
- formula_version: 계산 공식 버전 추적용 (향후 공식 변경 시 history 관리)
- rates_snapshot: API 응답에서 제공하는 당시 기본 일당 스냅샷 (audit trail)
