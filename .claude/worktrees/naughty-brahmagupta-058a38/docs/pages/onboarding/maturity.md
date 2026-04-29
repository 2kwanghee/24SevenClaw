---
route: /onboarding/maturity
title: 성숙도 진단
status: implemented
version: 1.0.0
pages:
  - src/app/(dashboard)/onboarding/maturity/page.tsx
components:
  - src/components/onboarding/maturity-questionnaire.tsx
  - src/components/onboarding/maturity-result.tsx
store: 없음 (TanStack Query)
last_updated: 2026-04-16
---

## 목적
팀의 AI 개발 성숙도를 설문으로 진단하고 수준(Starter/Intermediate/Advanced)에 맞는 프리셋을 추천.

---

## 레이아웃

**진단 중:**
```
┌──────────────────────────────────────────────┐
│ 질문 N / 전체   [프로그레스바]                │
│                                              │
│ [질문 텍스트]                                │
│                                              │
│ ○ 선택지 1 (점수 1)                          │
│ ○ 선택지 2 (점수 2)                          │
│ ○ 선택지 3 (점수 3)                          │
│ ● 선택지 4 (점수 4) ← 선택됨                 │
│                                              │
│ [이전]                          [다음]       │
└──────────────────────────────────────────────┘
```

**진단 완료:**
```
┌──────────────────────────────────────────────┐
│ 진단 결과: Intermediate (점수 67/100)         │
│                                              │
│ [레이더 차트: 팀/프로세스/툴링/CI/AI 영역]    │
│                                              │
│ [추천 프리셋] → [프리셋 선택으로 이동]        │
└──────────────────────────────────────────────┘
```

---

## 기능 요구사항

- [x] 카테고리별 설문 (team / process / tooling / ci / ai)
- [x] 가중치 기반 점수 계산
- [x] 결과: starter(0~40) / intermediate(40~70) / advanced(70~100)
- [x] 결과 레이더 차트 (5개 카테고리)
- [x] 추천 프리셋 이동 버튼
- [ ] 결과 공유 (URL)
- [ ] 히스토리 (이전 진단 결과 비교)
- [ ] 영역별 개선 팁 표시

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `GET` | `presets.getQuestions` | 진입 | 질문 목록 조회 |
| `POST` | `presets.assess` | 제출 | 점수 계산 + 추천 |
