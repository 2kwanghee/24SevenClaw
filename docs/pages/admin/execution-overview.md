---
title: 다프로젝트 실행 현황 (운영 패널)
category: page
status: draft
version: 0.1.0
last_updated: 2026-07-29
route: /admin/ops/execution
pages:
  - src/app/(dashboard)/admin/ops/execution/page.tsx   # 후보 — 미생성
components:
  - src/components/admin/ops/execution-summary.tsx     # 후보 — 미생성
  - src/components/admin/ops/active-job-table.tsx      # 후보 — 미생성
  - src/components/admin/ops/job-queue-card.tsx        # 후보 — 미생성
related:
  - migration.md
  - docs/multiproject-delivery.md
  - docs/wireframes/multiproject-delivery.html
---

> **구현 금지.** `migration.md` Stage 0.5(화면 기준선) 산출물이다. Stage 3(DeliveryJob) 실행
> 계획이 사용자 승인을 받기 전에는 코드를 생성하지 않는다. `pages`/`components`는 후보 경로다.

## 목적

운영자(superadmin)가 조직 전체에서 지금 무엇이 돌고 있고 무엇이 막혀 있는지를 한 화면에서
판단한다. 프로젝트별 상세가 아니라 **자원 경합과 blocker의 전역 뷰**다.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ 요약 스트립 (6칸)                                            │
│ ┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐                        │
│ │실행││대기││차단││실패││완료││가용│                        │
│ │중 2││ 3  ││ 1  ││ 1  ││ 14 ││시트│  ← 실패는 완료와 분리   │
│ └────┘└────┘└────┘└────┘└────┘└────┘                        │
├─────────────────────────────────────────────────────────────┤
│ 프로젝트별 활성 Job (표)                                     │
│ 프로젝트 │ Job │ 상태 │ 시트 │ lease만료 │ 시도 │ 진행 │ 이벤트│
├──────────────────────────┬──────────────────────────────────┤
│ 대기 큐 (우선순위·대기시간) │ 동시성 한도 (I-12 미확정)        │
└──────────────────────────┴──────────────────────────────────┘
```

> 모바일 레이아웃 (sm 미만): 요약 스트립 2열 → 활성 Job은 표 대신 카드 목록.

---

## 스토리보드

**시나리오 1: 정상 로드**
1. superadmin이 `/admin/ops/execution` 진입
2. Feature Flag(`FEATURE_DELIVERY_EXECUTION`) + 권한 확인
3. 요약 집계 + 활성 Job + 대기 큐 렌더링
4. WebSocket으로 Job 상태·lease 잔여시간 갱신

**시나리오 2: Flag off**
1. 패널을 표시하지 않고 빈 상태 안내 + 기존 흐름 영향 없음 명시
2. 사이드바에서도 항목이 사라짐

**시나리오 3: 실패 Job 발생**
1. `FAILED` 카운터만 증가 — 완료율 분모/분자에 반영하지 않음
2. 행에 사유(체크포인트 실패 등) 표시, 자동 재배정 없음을 명시

---

## 기능 요구사항

### 필수 기능
- [ ] 상태별 집계 — `FAILED`를 완료·성공률과 **분리** 집계 (§10)
- [ ] 프로젝트별 활성 Job 표 — 상태·시트·lease 만료·시도 횟수·진행률
- [ ] 대기 큐 — 우선순위·대기시간 정렬, 선결조건 충족 여부
- [ ] 실행 모드 표기 — 현재 v1은 **순차**이므로 병렬로 오해되지 않게 배지 노출 (§3.0)
- [ ] Feature Flag off 상태 화면
- [ ] superadmin 권한 가드 (실경계는 백엔드가 강제)

### 확정 사항 (I-12, 2026-07-29)

- [ ] 동시성 한도 카드 값 — **동시 프로젝트 최대 2 · 기본 1 순차** · 프로젝트당 Job 1 ·
      시트당 Job 1 · 러너 호스트 1
- [ ] **필요 시트 3~4개** 표기 (활성 2 + cooldown·인증 예비 1~2)
- [ ] "최대 2를 쓰려면 러너 수평 확장 + main 머지 직렬화가 선행" 안내 —
      시트를 늘려 해결되지 않음을 화면에서 분명히 한다
      (근거: `docs/hybrid-runner-headless-poc.md` §4-2·§4-3)

### 선택/개선 사항
- [ ] lease 만료 임박(1분 미만) 행 강조
- [ ] 프로젝트 행 → 해당 프로젝트 실행 탭으로 이동

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `summary` | `ExecutionSummary` | API 폴링 | 요약 스트립 |
| `activeJobs` | `DeliveryJob[]` | API + WebSocket | 활성 Job 표 |
| `queue` | `QueuedJob[]` | API | 대기 큐 |
| `flags` | `FeatureFlags` | 기존 flag 조회 | 패널 표시 여부 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/ops/execution/summary` | 진입 | 상태별 집계 (후보) |
| `GET` | `/api/v1/ops/execution/jobs?status=active` | 진입 | 활성 Job (후보) |
| `GET` | `/api/v1/ops/execution/queue` | 진입 | 대기 큐 (후보) |
| WS | 기존 Agent 채널 | 상시 | status/heartbeat 기반 갱신 |

> 엔드포인트는 전부 **후보**다. Flag off 에서는 숨김 또는 404 (§19).

---

## 접근성 / 반응형

- [ ] WCAG 2.1 AA — 상태 배지는 색 외에 텍스트 라벨 병기
- [ ] 진행률 바에 `role="img"` + `aria-label`
- [ ] 표는 `overflow-x: auto` 컨테이너 안에서만 횡스크롤
- [ ] 숫자 열 `tabular-nums`
- [ ] 키보드 네비게이션 (Tab/Enter)
- [ ] 로딩 스켈레톤 / 빈 상태 / 권한 없음 상태

---

## 구현 노트

- **집계 규칙이 이 화면의 핵심**이다. `FAILED`를 완료에 섞으면 §23 MVP 수용 기준을 위반한다.
- 순차 실행(v1)을 병렬처럼 보이게 하는 시각화(동시 진행 레인 등)를 쓰지 않는다.
- 시트 상세는 이 화면에 넣지 않고 `/admin/ops/seats`로 분리한다 — 시트는 조직 전역 자원,
  Job은 프로젝트 자원으로 권한 경계가 다르다 (I-13).
