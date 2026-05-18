## 목표
M6 — VersionUp 권장안 생성 LLM + step-modernize-diagnosis-review UI.
M5 의 분석 결과를 입력으로 시나리오별 권장안(`ModernizeRecommendation`)을 생성하고, 사용자가 검토·취사선택(selected=true/false)할 수 있는 UI 추가.

## 비침습성 보장
- 신규 endpoint 2개만 추가 (`GET/PATCH /sessions/{id}/recommendations`)
- pipeline.py 의 기존 step 흐름은 유지, 권장안 생성만 새로 끼워넣음
- Anthropic API key 미설정 시 outdated 패키지를 기반으로 한 deterministic fallback (M5 의 placeholder 패턴 재사용)
- 신규 step UI 만 추가, 기존 step 미변경

## 변경 파일 목록

### Backend (신규)
- `app/services/modernize/recommendations.py` — 시나리오별 LLM 프롬프트 + JSON strict + DB insert
- `tests/services/modernize/test_recommendations.py` — placeholder 모드 + JSON 스키마 검증

### Backend (수정)
- `app/schemas/modernize.py` — `ModernizeRecommendationResponse`, `ModernizeRecommendationUpdate` 추가
- `app/services/modernize/pipeline.py` — Step 6.5 권장안 생성 단계 추가 (status='recommending' 후)
- `app/api/v1/modernize.py` — `GET /sessions/{id}/recommendations`, `PATCH /sessions/{id}/recommendations/{rec_id}` 추가

### Frontend (신규)
- `src/components/solutions/wizard/steps/step-modernize-diagnosis-review.tsx` — 진단 요약 + 시나리오 라디오 + 권장 카드 체크리스트

### Frontend (수정)
- `src/lib/api-client.ts` — `listRecommendations`, `updateRecommendation` 추가
- `src/app/(dashboard)/solutions/modernize/new/page.tsx` — STEP_COMPONENTS 에 diagnosis-review 추가 (4 step)

## VersionUp 권장안 LLM 시나리오

**System prompt 핵심**:
"You are a dependency upgrade planner. Each recommendation upgrades EXACTLY ONE package or runtime. Group breaking changes per package. Output STRICT JSON only."

**Input**: outdated_packages + manifests + framework_signals + scenario + goals_text
**Output JSON schema**:
```
{ "recommendations": [{
  "category": "upgrade",
  "target_path": "pyproject.toml",
  "before": {"pkg": "django", "version": "3.2.18"},
  "after": {"version": "5.0.6", "migration_notes": "...", "breaking_changes": [...]},
  "title": "Django 3.2 → 5.0 업그레이드",
  "rationale_md": "...",
  "effort": "S|M|L",
  "risk": "low|med|high",
  "priority": 1..100,
  "prompt_md": "..."
}]}
```

**Fallback (API key 미설정)**: outdated_packages 각각을 기계적으로 category='upgrade' 권장안으로 변환.

## Endpoint 시그니처

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/modernize/sessions/{id}/recommendations` | user + flag + ownership | `ModernizeRecommendationResponse[]` |
| PATCH | `/modernize/sessions/{id}/recommendations/{rec_id}` | user + flag + ownership | `ModernizeRecommendationResponse` |

PATCH body: `{ selected?, priority?, prompt_md? }`

## 구현 단계
1. schemas 확장
2. recommendations.py 서비스 (VersionUp 우선, refactor/language_migrate placeholder)
3. pipeline.py 에 권장안 생성 단계 추가
4. endpoint 2 개 추가
5. 단위 테스트 (placeholder fallback JSON 스키마 검증)
6. api-client 확장
7. step-modernize-diagnosis-review UI
8. modernize/new/page.tsx 확장
9. ruff + mypy + tsc + vitest

## STATUS: APPROVED
