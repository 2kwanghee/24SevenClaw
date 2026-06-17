---
route: /solutions/new (Step 3)
title: PM 추천 생성 (로딩 → 결과 확인)
category: page
status: implemented
version: 1.3.0
components:
  - src/components/solutions/wizard/steps/step-pm-recommendation.tsx
store: useSolutionWizardStore → setRecommendedPMItems, setStep3Done
last_updated: 2026-06-15
---

## 목적
선택한 프로토타입을 기반으로 Claude + Rule 하이브리드 엔진(70/30 가중)이 최적 PM을 분석. 로딩 중 스켈레톤 UI 표시, 완료 시 추천 PM 카드를 표시한 뒤 사용자가 "다음"을 클릭해 Step 4로 진행.

---

## 레이아웃

**추천 중 (skeleton)**
```
┌─────────────────────────────────────────┐
│                                         │
│  [스켈레톤 PM 카드 × 3]                  │
│  [아바타 + 이름 + 메타 정보 로딩중]      │
│  [매치 점수 + 이유 칩 로딩중]             │
│  [정량 지표(4개) 로딩중]                 │
│  [태그들 로딩중]                        │
│                                         │
│  "PM 프로필 분석 중..."                 │
│                                         │
└─────────────────────────────────────────┘
```

**추천 완료 (ready)**
```
┌─────────────────────────────────────────┐
│  ✅ "PM 추천이 완료되었습니다"            │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ [아바타] PM 이름 / 역할          │   │
│  │ "추천 이유 1줄"                 │   │
│  │ [매치점수 칩] [이유들...]       │   │
│  │ 📊 정량 지표: 예상기간 / 팀 / 비용 │
│  │ [태그들...]                     │   │
│  │ (프로토타입 매칭 배경색)        │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ [아바타] PM 이름 / 역할          │   │
│  │ ...                             │   │
│  └─────────────────────────────────┘   │
│                                         │
│  "아래 다음 버튼을 클릭해               │
│   PM을 선택하세요"                     │
│                                         │
└─────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 정상 추천 (신규)**
1. Step 3 진입 직후 `prototypeSessions.recommendPMs` 호출
2. 스켈레톤 로딩 UI 표시 (EXPECTED_COUNT=3개 카드)
3. 응답 수신 → PM 데이터 파싱: 이름, 제목, 매치스코어, 이유, 정량 지표 추출
4. `setRecommendedPMItems` + `setStep3Done(true)` → ready 카드 표시 (animate-in)
5. "아래 다음 버튼을 클릭해 PM을 선택하세요" 안내 메시지 표시
6. 사용자 "다음" 클릭 → Step 4로 이동

**시나리오 2: 이전 버튼으로 Step 3 재진입**
1. 스토어에 이미 `recommendedPMItems` 데이터 있음을 감지
2. API 재호출 없이 기존 PM 카드를 즉시 ready 상태로 표시
3. `setStep3Done(true)` → 다음 버튼 활성화
4. 사용자 "다음" 클릭 → Step 4로 이동

**시나리오 3: 실패 (미구현 - 재시도 추가 예정)**
- 응답 오류 → 향후 에러 UI + 재시도 버튼 추가

---

## 기능 요구사항

- [x] 진입 직후 PM 추천 API 호출 (기존 결과 없을 때만)
- [x] 스켈레톤 로딩 UI (EXPECTED_COUNT=3)
- [x] 완료 시 추천 결과 저장 + `step3Done=true` → 카드 목록 표시
- [x] PM 카드에 다음 정보 표시:
  - PM 이름 + 역할/직급
  - 추천 이유 (reasoning) 1줄
  - 매치 점수 (matchScore) + 근거 칩들 (matchReasons 최대 3개)
  - 정량 지표 (4칸 격자): 예상기간 / 팀크기 / 월비용 / 유지보수난이도
  - 태그들
- [x] 완료 후 "다음 버튼 클릭" 안내 메시지
- [x] `canProceed = step3Done` (추천 완료 시 다음 버튼 활성화)
- [x] 이전 버튼 재진입 시 기존 카드 즉시 복원 (API 재호출 금지)
- [ ] 실패 시 에러 UI + 재시도 버튼

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `POST` | `prototypeSessions.recommendPMs` | 스텝 진입 | PM 추천 요청 |

---

## 추천 엔진 동작 방식 (Claude + Rule 하이브리드)

### 점수 계산 (70 / 30 가중)

| 점수 | 가중치 | 설명 |
|------|--------|------|
| Claude 점수 | 70% | 프로토타입 메타(스택·아키텍처·산업)와 PM 프로필 전문성 매칭을 Claude에 위임 |
| Rule 점수 | 30% | `domain × 0.4 + specialty × 0.3 + 메트릭(사용횟수·성공률) × 0.3` |

**최종 점수**: `final = claude_score × 0.7 + rule_score × 0.3`

### 자동 폴백 정책

Claude API 키 미설정·응답 오류·파싱 실패 시:
- 자동으로 Rule 점수 단독(100%)으로 폴백
- `pm_recommendation_logs.is_fallback` 컬럼에 기록
- `/admin/recommendations` 대시보드에서 폴백 발생 현황 확인 가능

### Prompt Caching

PM 카탈로그(모든 활성 PM 프로필 목록)와 시스템 프롬프트 블록에 `cache_control: ephemeral` 적용:
- 동일 카탈로그 기준 5분 내 재호출 시 Claude API 비용 약 90% 절감

### 품질 로그

각 추천 호출마다 `pm_recommendation_logs` 테이블 기록:
- 입력 스냅샷
- Claude 원문 응답
- 최종 순위
- 레이턴시
- 사용자가 Step 4에서 PM 선택 시 `selected_pm_id` 역기록

---

## PM → ZIP 배포 흐름

이 단계에서 추천된 PM을 Step 4에서 선택하면 최종 ZIP에 **플랫폼별 PM 파일**이 자동 주입된다.

### 전체 데이터 흐름

```
Step 3 (PM 추천)  →  Step 4 (PM 선택)  →  Step 9 (최종 확인)  →  프로젝트 생성
                                                               ↓
                                          POST /api/v1/projects/
                                          {
                                            pm_slug: "alex-pm",
                                            pm_markdown: "# Alex PM\n...",
                                            pm_compositions: [...],
                                            platform_id: "claude-code",
                                            ...
                                          }
                                                               ↓
                                          generate_all()
                                          ├── 에이전트 파일
                                          ├── 스킬 파일
                                          ├── settings.json
                                          └── PM 파일 주입
                                              └── .claude/pm/alex-pm.md
```

### PM 파일이 ZIP에 포함되는 조건

| 조건 | 결과 |
|------|------|
| PM 선택됨 + `pm_markdown` 있음 | ✅ 플랫폼별 PM 파일 생성 |
| PM 선택됨 + `pm_markdown` 비어있음 | ⚠️ PM 파일 생략 (경고 배지) |
| PM 미선택 | ❌ PM 파일 없음 |

### 플랫폼별 PM 파일 경로

| 플랫폼 | PM 파일 경로 예시 |
|--------|------------------|
| Claude Code | `.claude/pm/{slug}.md` |
| Gemini CLI | `.gemini/pm/{slug}.md` |
| Cursor | `.cursor/rules/pm-{slug}.md` |
| Codex | `.codex/pm/{slug}.py` |

자세한 파일 매핑은 `docs/pages/download/pm-environment.md` 참조.

### PM Composition 병합 규칙

PM에 연결된 Composition(에이전트·스킬)이 있으면 Step 5~6에서 사용자가 수동으로 선택한 항목과 **병합**:
- Composition 항목이 우선 순위를 가짐
- 중복은 제거됨

```
최종 에이전트 목록 = PM composition 에이전트 + 사용자 추가 에이전트 (중복 제외)
최종 스킬 목록    = PM composition 스킬 + 사용자 추가 스킬 (중복 제외)
```

---

## 상태 관리

| 상태 | 타입 | 출처 | 설명 |
|------|------|------|------|
| `recommendedPMItems` | `PMRecommendedItem[]` | `useSolutionWizardStore` | 추천된 PM 목록 |
| `step3Done` | `boolean` | `useSolutionWizardStore` | 추천 완료 여부 |

### PMRecommendedItem 구조

```typescript
{
  id: string;
  name: string;
  title?: string;              // 역할/직급
  reasoning: string;           // 추천 이유 (1줄)
  matchScore: number;          // 매치 점수 (0-100)
  matchReasons: string[];      // 매칭 근거 칩들 (최대 3개)
  estimatedWeeks?: string;     // 예상 기간
  teamSize?: string;           // 팀 규모
  monthlyCost?: string;        // 월 비용
  maintenanceDifficulty?: string; // 유지보수 난이도
  tags?: string[];             // 태그들
}
```

---

## 구현 노트

- **[v1.3]** Claude 하이브리드 추천 (70/30): `recommend_pms_for_session()` 호출, Claude API 실패 시 rule 폴백, `pm_recommendation_logs` INSERT
- **[v1.3]** Prompt caching: `cache_control: ephemeral` 적용 → 5분 내 재호출 시 약 90% 비용 절감
- **[v1.3]** PM 선택 역기록: Step 4에서 PM 선택 시 PATCH 호출 → `pm_recommendation_logs.selected_pm_id` 자동 업데이트
- **[v1.1]** 자동 이동 제거: 응답 수신 시 `nextStep()` 자동 호출 대신 `step3Done=true`로 설정하여 다음 버튼 활성화
- **[v1.1]** 이전 버튼 지원: `recommendedPMItems.length > 0` 감지 시 API 재호출 금지 + 기존 카드 즉시 표시
- 세션 없으면 Step 0으로 리다이렉트
- PM `pm_markdown` 필드 비어있으면 Step 4(선택 화면)에 경고 배지 표시 → 관리자에게 MD 편집 요청 메시지 포함
