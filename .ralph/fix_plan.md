# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[api] Pydantic 스키마 구현 (prototype, pm_profile, solution)**
  > 요청사항: Pydantic v2 스키마 신규 작성.

* app/schemas/prototype.py: PrototypeSessionCreate, PrototypeSessionResponse, PrototypeResponse, PrototypeDetailResponse
* app/schemas/pm_profile.py: PMProfileResponse, PMProfileWithMetrics, PMCompositionResponse, PMRatingCreate, PMRatingResponse
* app/schemas/solution.py: SolutionAnalyzeRequest, SolutionAnalyzeResponse, UIStructureSchema

model_config = {"from_attributes": True} 패턴 준수.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | Pydantic 스키마 (prototype/pm_profile/solution) | ✅ 완료 | 신규 3종 + 기존 2종 보강, 337 tests passed |