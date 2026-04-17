---
route: /solutions/new (Step 3)
title: PM 추천 생성 (로딩 → 결과 확인)
status: implemented
version: 1.2.0
components:
  - src/components/solutions/wizard/steps/step-pm-recommendation.tsx
store: useSolutionWizardStore → setRecommendedPMItems, step3Done
last_updated: 2026-04-17
---

## 목적
선택한 프로토타입 기반으로 AI가 최적 PM을 분석하는 동안 로딩 UI 표시, 완료 시 결과 카드를 보여준 뒤 사용자가 직접 "다음"을 클릭해 Step 4로 진행.

---

## 레이아웃

**추천 중 (skeleton)**
```
┌─────────────────────────────────────────┐
│                                         │
│    [스켈레톤 아바타]  [스켈레톤 텍스트] │
│    [스켈레톤 아바타]  [스켈레톤 텍스트] │
│    [스켈레톤 아바타]  [스켈레톤 텍스트] │
│                                         │
│    "PM 프로필 분석 중..."               │
│                                         │
└─────────────────────────────────────────┘
```

**추천 완료 (ready)**
```
┌─────────────────────────────────────────┐
│  ✅ "PM 추천이 완료되었습니다"           │
│                                         │
│    [아바타] PM 이름 / 역할              │
│    [아바타] PM 이름 / 역할              │
│    [아바타] PM 이름 / 역할              │
│                                         │
│    "아래 다음 버튼을 클릭해             │
│     PM을 선택하세요"                    │
└─────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 정상 추천 (신규)**
1. Step 3 진입 직후 `prototypeSessions.recommendPMs` 호출
2. 스켈레톤 카드 UI 표시 (예정 PM 수만큼)
3. 응답 수신 → `setRecommendedPMItems` + `step3Done=true` → PM 카드 목록 표시
4. "아래 다음 버튼을 클릭해 PM을 선택하세요" 안내 메시지 표시
5. 사용자가 "다음" 클릭 → Step 4 이동

**시나리오 2: 이전 버튼으로 Step 3 재진입**
1. 스토어에 이미 `recommendedPMItems` 데이터가 있음을 감지
2. API 재호출 없이 기존 PM 카드를 즉시 표시
3. `step3Done=true`로 다음 버튼 활성화
4. 사용자가 "다음" 클릭 → Step 4 이동

**시나리오 3: 실패**
- 응답 오류 → 에러 메시지 + 재시도 버튼

---

## 기능 요구사항

- [x] 진입 즉시 PM 추천 API 호출 (기존 결과 없을 때만)
- [x] 스켈레톤 로딩 UI (카드 형태)
- [x] 완료 시 추천 결과 스토어 저장 + `step3Done=true` → 카드 목록 표시
- [x] 완료 후 "다음 버튼 클릭" 안내 메시지 표시
- [x] `canProceed = step3Done` (추천 완료 시 다음 버튼 활성화)
- [x] 이전 버튼으로 재진입 시 기존 카드 즉시 복원 (API 재호출 없음)
- [ ] 예상 소요 시간 표시
- [ ] 실패 시 에러 UI + 재시도 버튼 (현재 미구현)

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `POST` | `prototypeSessions.recommendPMs` | 스텝 진입 | PM 추천 요청 |

---

## 추천 엔진 동작 방식 (v1.2)

### Claude + Rule 하이브리드 (70 / 30)

PM 추천은 두 점수를 가중 합산한다.

| 점수 | 가중치 | 설명 |
|------|--------|------|
| Claude 점수 (`claude_score`) | 70% | 프로토타입 메타(스택·아키텍처·산업)와 PM 프로필 전문성 매칭을 Claude에 위임 |
| Rule 점수 (`rule_score`) | 30% | `domain × 0.4 + specialty × 0.3 + 사용 횟수/성공률 메트릭 × 0.3` |

최종 점수: `final = claude_score × 0.7 + rule_score × 0.3`

### 자동 폴백 정책

Claude API 키 미설정·응답 오류·파싱 실패 시 자동으로 Rule 점수 단독(100%)으로 폴백한다. 폴백 발생 여부는 `pm_recommendation_logs.is_fallback` 컬럼에 기록되며 `/admin/recommendations` 대시보드에서 확인할 수 있다.

### Prompt Caching

PM 카탈로그(모든 활성 PM 프로필 목록)와 시스템 프롬프트 블록에 `cache_control: ephemeral`을 적용한다. 동일 카탈로그 기준으로 5분 내 재호출 시 Claude API 비용이 약 90% 절감된다.

### 품질 로그

각 추천 호출마다 `pm_recommendation_logs` 테이블에 입력 스냅샷, Claude 원문 응답, 최종 순위, 레이턴시를 기록한다. 사용자가 Step 4에서 PM을 최종 선택하면 해당 로그의 `selected_pm_id`도 업데이트된다.

---

## PM → ZIP 배포 흐름

이 단계에서 추천된 PM을 선택하면 최종 ZIP 안에 **플랫폼별 PM 파일**이 자동 주입된다.

### 전체 데이터 흐름

```
Step 3 (PM 추천)  →  Step 4 (PM 선택)  →  Step 9 (최종 확인)  →  프로젝트 생성
                                                                        │
                                                                        ▼
                                                              POST /api/v1/projects/
                                                              {
                                                                pm_slug: "alex-pm",
                                                                pm_markdown: "# Alex PM\n...",
                                                                pm_compositions: [...],
                                                                platform_id: "claude-code",
                                                                ...
                                                              }
                                                                        │
                                                                        ▼
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
| PM 선택됨 + `pm_markdown` 비어있음 | ❌ PM 파일 생략 (경고 표시) |
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

PM에 연결된 Composition(에이전트·스킬)이 있으면 위저드에서 수동 선택한 항목과 **병합**된다.
Composition 항목이 우선 순위를 가지며 중복은 제거된다.

```
최종 에이전트 목록 = PM composition 에이전트 + 사용자 추가 에이전트 (중복 제외)
최종 스킬 목록    = PM composition 스킬 + 사용자 추가 스킬 (중복 제외)
```

---

## 구현 노트

- **[v1.2]** Claude 하이브리드 추천 연결: `recommend_pms_for_session()` 재작성, Claude API 실패 시 rule 폴백, `pm_recommendation_logs` INSERT
- **[v1.2]** Prompt caching: 시스템·PM 카탈로그 블록에 `ephemeral` 적용
- **[v1.2]** 사용자 PM 선택 시 `selected_pm_id` 추천 로그에 역기록 (`PATCH /prototype-sessions/{id}` → `pm_recommendation_logs` 자동 업데이트)
- **[v1.1]** 자동 이동 제거: 응답 수신 시 `nextStep()` 자동 호출 대신 `step3Done=true`로 설정하여 다음 버튼 활성화
- **[v1.1]** 이전 버튼 지원: `recommendedPMItems.length > 0`이면 API 재호출 없이 기존 카드 즉시 표시 + `step3Done=true`
- 세션 없으면 Step 0으로 리다이렉트
- PM `pm_markdown` 필드가 비어있으면 Step 4(선택 화면)에 경고 배지 표시 — 관리자에게 MD 편집을 요청하는 메시지 포함
