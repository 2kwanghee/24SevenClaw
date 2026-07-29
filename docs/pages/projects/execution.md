---
title: 실행 · DeliveryJob (프로젝트 탭)
category: page
status: draft
version: 0.1.0
last_updated: 2026-07-29
route: /projects/[projectId]/execution
pages:
  - src/app/(dashboard)/projects/[projectId]/execution/page.tsx  # 후보 — 미생성
components:
  - src/components/projects/execution/job-state-rail.tsx         # 후보 — 미생성
  - src/components/projects/execution/workspace-tree.tsx         # 후보 — 미생성
  - src/components/projects/execution/job-event-timeline.tsx     # 후보 — 미생성
  - src/components/projects/execution/job-log-tail.tsx           # 후보 — 미생성
related:
  - migration.md
  - docs/wireframes/multiproject-delivery.html
  - scripts/project_runner.sh
---

> **구현 금지.** `migration.md` Stage 0.5 산출물. Stage 3(Workspace·DeliveryJob) 승인 전 코드 생성 금지.
> 실행 원장(DeliveryJob·JobEvent)은 아직 없다 — 현재는 스크립트 계층에서 순차 실행된다(§3.0).

## 목적

이 프로젝트의 실행이 지금 어느 단계에 있고, 어느 시트가 붙어 있고, 실패하면 무엇이
이어받을 수 있는지를 보여준다. 시트 교체가 **checkpoint 경계의 재시작**임을 화면으로 드러낸다.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ Job 헤더 — job-7c1a · [RUNNING] · 시도 2/3                   │
│ 상태 레일 QUEUED→SCHEDULING→LEASED→PROVISIONING→RUNNING→     │
│           CHECKPOINTING→VERIFYING→COMPLETED                  │
│ 칩: 시트 · lease만료 · branch · base commit · checkpoint · 티켓│
├──────────────────────────────────┬──────────────────────────┤
│ 작업공간 (경로 트리 + 격리 체크)   │ Job 이벤트 (append-only)  │
│ 실행 로그 (tail · redaction)      │ 실패한 Job (자동 재배정 X) │
│                                  │ 시트 교체 규칙 주석 (§6.3) │
└──────────────────────────────────┴──────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 실행 중 추적**
1. 진입 → 활성 Job 상태 레일에서 현재 단계 강조
2. lease 만료 잔여시간이 heartbeat로 갱신
3. JobEvent 타임라인과 로그 tail이 append-only로 누적

**시나리오 2: 재시도**
1. `test exit=1` → `RETRY_WAIT` → `QUEUED` 전이가 타임라인에 남음
2. 시도 카운터 2/3으로 증가
3. 한도 소진 시 `FAILED` — 완료 집계에 반영하지 않음

**시나리오 3: rate limit → 다른 시트 이어받기**
1. 시트가 `COOLING_DOWN`으로 전환
2. 현재 attempt를 중단 가능 경계까지 정리 → Git checkpoint
3. checkpoint/base commit을 원장에 기록 → 새 시트가 **같은 branch·checkpoint에서 새 attempt**
4. 화면은 attempt별 시트를 구분해 표시

**시나리오 4: checkpoint 실패**
1. dirty workspace는 자동 재배정하지 않음
2. blocker로 남기고 작업공간·artifact를 보존

---

## 기능 요구사항

### 필수 기능
- [ ] Job 상태 레일 — §10 상태 머신 전체 노출(전이 시각 포함)
- [ ] lease 만료 잔여시간 + heartbeat 기반 갱신
- [ ] attempt 카운터와 attempt별 시트 이력
- [ ] base commit / checkpoint commit **상시 노출** (§6.3)
- [ ] 작업공간 경로 트리 + 격리 체크(traversal·symlink 차단, 인증 홈은 작업공간 밖)
- [ ] JobEvent 타임라인 — append-only, 실패 전이 포함
- [ ] 로그 tail — redaction 적용, 원문은 artifact 저장소 참조
- [ ] `FAILED` Job을 완료·성공률에 합산하지 않음
- [ ] 체크포인트 실패 시 "자동 재배정하지 않음"을 명시적으로 표시

### 선택/개선 사항
- [ ] Job 취소(`CANCELLED`) 액션 — CONTROL 정책 확인 후
- [ ] artifact 다운로드 (Secret 제외 검사 통과 시)
- [ ] 프로젝트당 동시 변경 Job 1개 초과 시도에 대한 안내

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `jobs` | `DeliveryJob[]` | `GET .../jobs` | Job 목록 |
| `job` | `DeliveryJobDetail` | `GET .../jobs/{id}` | 헤더·레일·칩 |
| `events` | `DeliveryJobEvent[]` | `GET .../jobs/{id}/events` | 타임라인 |
| `logTail` | `string[]` | WebSocket | 로그 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/projects/{id}/jobs` | 진입 | Job 목록 (후보) |
| `GET` | `/api/v1/projects/{id}/jobs/{jobId}` | 선택 | Job 상세 (후보) |
| `GET` | `/api/v1/projects/{id}/jobs/{jobId}/events` | 선택 | 이벤트 이력 (후보) |
| WS | 기존 Agent 채널 | 상시 | status / log / result / heartbeat |

`task_id`는 기존 Runner 계약 호환을 위해 `DeliveryJob.id`를 사용한다 (§10). 기존
`RunnerTaskPayload` 필수 필드는 변경하지 않는다 (§11.1).

---

## 접근성 / 반응형

- [ ] 상태 레일에 `role="img"` + 현재 단계를 포함한 `aria-label`
- [ ] 로그·작업공간 트리는 `overflow-x: auto`
- [ ] 상태는 색 + 텍스트 병기, 실패는 아이콘까지 3중 표현
- [ ] 잔여시간·시도 횟수 `tabular-nums`
- [ ] `prefers-reduced-motion`에서 진행 애니메이션 정지

---

## 구현 노트

- **금지 표현 주의**: 이 화면이 "Runner가 이미 다프로젝트 workspace를 지원한다"처럼 읽히면
  §24.1 위반이다. 현재 실행 모드(순차)를 표기한다.
- 로그를 DB에 무제한 적재하지 않는다. 화면은 tail + artifact 참조 구조를 전제한다 (§9.2).
- status·log·result의 영속화가 끝나기 전에는 이 화면을 다프로젝트 활성화 근거로 쓰지 않는다 (§11.1).
