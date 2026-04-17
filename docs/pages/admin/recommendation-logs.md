---
route: /admin/recommendations
title: PM 추천 로그 (품질 대시보드)
status: implemented
version: 1.0.0
roles: superadmin, admin
last_updated: 2026-04-17
---

## 목적

PM 추천 엔진의 품질을 모니터링하는 관리자 전용 대시보드다. 각 추천 호출의 결과·레이턴시·Claude/Fallback 비율을 조회하고, 추천한 PM과 사용자가 실제로 선택한 PM을 비교해 정확도를 파악할 수 있다.

---

## 접근 권한

`superadmin` 또는 `admin` 역할만 접근 가능 (`pm:manage` 권한 필요).

---

## 화면 구성

### 요약 카드

| 카드 | 설명 |
|------|------|
| 전체 추천 | 로그 조회 기준 총 추천 건수 |
| Claude 기반 | Claude API 응답이 사용된 추천 건수 |
| Fallback | Claude 실패로 Rule-only로 처리된 건수 |
| 평균 레이턴시 | 전체 추천 API 평균 응답 시간 (ms) |

### 필터

- **전체**: 필터 없음
- **Claude만**: `is_fallback = false`인 로그만 표시
- **Fallback만**: `is_fallback = true`인 로그만 표시

### 로그 테이블

| 컬럼 | 설명 |
|------|------|
| 세션 ID | 프로토타입 세션 UUID (앞 8자리) |
| 생성 시각 | 추천 호출 시각 (한국 시간) |
| 추천 방식 | `Claude` (초록) 또는 `Fallback` (주황) 배지 |
| 레이턴시 | Claude API 포함 총 응답 시간 (ms) |
| 1순위 PM | 최종 점수 1위 PM ID와 점수 |
| 선택된 PM | 사용자가 Step 4에서 실제 선택한 PM ID (없으면 "미선택") |

### 행 클릭 (상세 펼침)

행을 클릭하면 상세 패널이 펼쳐져 다음 정보를 표시한다.

- **입력 스냅샷**: 추천 당시의 프로토타입 메타데이터 (JSON)
- **최종 순위 (Top 5)**: PM ID, 최종 점수, Claude 점수, Rule 점수

---

## API 엔드포인트

| 메서드 | 경로 | 파라미터 |
|--------|------|---------|
| `GET` | `/api/v1/admin/pm-recommendations` | `session_id?`, `is_fallback?`, `offset`, `limit` |

---

## 주요 지표 해석

### Fallback 비율

- **5% 미만**: 정상. Claude API가 안정적으로 동작 중.
- **5~30%**: Claude API 간헐적 오류 발생. 로그를 확인해 원인 파악.
- **30% 초과**: Claude API 키 만료 또는 네트워크 이슈 가능성. 즉시 점검 필요.

### 1순위 PM ≠ 선택된 PM

추천 1순위와 실제 선택이 다를 경우 추천 품질 개선이 필요할 수 있다. 패턴이 반복되면 해당 PM의 프로필 데이터(`bio_long`, 태그)를 보강하거나 Claude 프롬프트를 조정하는 것을 권장한다.

### 평균 레이턴시

Claude 응답 포함 전체 추천 API 평균 레이턴시가 10초를 초과하면 타임아웃 설정 조정을 검토한다 (현재 Claude 호출 타임아웃: 10초).

---

## 관련 문서

- [PM 추천 엔진 동작 방식](../solutions/wizard/step-04-pm-recommend.md) — 70/30 하이브리드 점수 및 폴백 정책
- [PM 관리](./pm-management.md) — PM 프로필 CRUD 및 Claude 품질 향상 권장 작업
