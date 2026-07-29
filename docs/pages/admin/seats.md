---
title: 구독 시트 풀 (운영 패널)
category: page
status: draft
version: 0.1.0
last_updated: 2026-07-29
route: /admin/ops/seats
pages:
  - src/app/(dashboard)/admin/ops/seats/page.tsx      # 후보 — 미생성
components:
  - src/components/admin/ops/seat-table.tsx           # 후보 — 미생성
  - src/components/admin/ops/seat-state-badge.tsx     # 후보 — 미생성
  - src/components/admin/ops/seat-headroom-gauge.tsx  # 후보 — 미생성
related:
  - migration.md
  - docs/multiproject-delivery.md
  - docs/wireframes/multiproject-delivery.html
  - clickeye-api/app/schemas/seat.py
  - clickeye-api/app/services/seat_service.py
---

> **구현 금지.** `migration.md` Stage 0.5 산출물. 단, 시트 등록·배정 백엔드는 **이미 존재한다**
> (P4 완료, `schemas/seat.py`·`services/seat_service.py`). 이 화면은 그 위의 **모니터링 뷰**이며
> 신규 시트 모델을 만들지 않는다 (§3.0 · §9).

## 목적

운영자가 조직의 AI 구독 시트가 지금 배정 가능한지, 왜 불가능한지를 **근거와 함께** 판단한다.
정확한 잔여 토큰을 아는 척하지 않는 것이 이 화면의 설계 전제다.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠ 정확한 잔여 토큰 미표시 안내 (§6.2 · I-05)                 │
├─────────────────────────────────────────────────────────────┤
│ 상태별 요약 (READY / BUSY / COOLING_DOWN / AUTH_REQ / DISABLED)│
├─────────────────────────────────────────────────────────────┤
│ 시트 표                                                      │
│ 시트 │파생상태│파생근거│추정여유도│배정│heartbeat│capability│조치│
├──────────────────────────┬──────────────────────────────────┤
│ 재인증 안내 (Runner에서만) │ 상태 전이 감사 로그 (append-only) │
└──────────────────────────┴──────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 배정 가능 시트 확인**
1. 운영자 진입 → 상태별 요약에서 `READY 2` 확인
2. 표에서 근거 칩(`seat_status=active`, `lease 없음`, `heartbeat 유효`) 확인
3. Runner capability(OS/arch/docker/DB)가 작업 요구를 만족하는지 확인

**시나리오 2: 인증 만료**
1. `AUTH_REQUIRED` 시트 발견 → 근거 칩 `probe 실패 · 인증`
2. 재인증 안내 카드에 **Runner에서 사람이 1회 수행** 절차 표시
3. 웹에서 토큰을 입력하는 UI는 제공하지 않음

**시나리오 3: rate limit**
1. `COOLING_DOWN` + `reset 15:00 (공급자 통보)` 표시
2. 배정 버튼 비활성, reset 경과 + probe 성공 시 `READY` 자동 복귀

---

## 기능 요구사항

### 필수 기능
- [ ] **파생 5상태 표시** — 현행 `seat_status(active·exhausted·blocked)` + lease + probe에서 파생 (§6.2 매핑표)
- [ ] **파생 근거 병기** — 어떤 관측값 때문에 그 상태인지 칩으로 노출. 근거 없는 상태 표시 금지
- [ ] 추정 여유도를 **3단계(상·중·하) + 관측 없음**으로만 표시. 숫자·퍼센트 금지
      (**I-05 확정 2026-07-29** — 상/중/하 + 근거로 운영 가능하다고 확정)
- [ ] 목표 시트 보유량 **3~4개** 대비 현재 등록 수를 노출 (I-12 `C=2` 기준 산정)
- [ ] heartbeat 최신성, 마지막 사용 후 경과 시간
- [ ] Runner capability(OS·arch·docker·DB) 표시 — 배정 hard filter의 근거
- [ ] 상태 전이 감사 로그 (전이 시각·사유·전/후 상태)
- [ ] 평문 토큰·마스킹 토큰 모두 **미표시**
- [ ] superadmin 권한 가드

### 선택/개선 사항
- [ ] 시트별 최근 실패율 추이
- [ ] `DISABLED` 복구 시 사유 입력 요구
- [ ] 시트별 레이트 카운터 — **선행 과제 있음**: 로컬 claude 사용량의 원장 인제스트 배관 이후

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `seats` | `SeatView[]` | `GET /ops/seats` | 시트 표 |
| `transitions` | `SeatTransition[]` | `GET /ops/seats/transitions` | 감사 로그 |

`SeatView`는 DB 컬럼이 아니라 **파생 뷰**다. `seat_status` + 활성 lease + 최근 probe + heartbeat를
서비스 레이어에서 합성한다. 신규 컬럼을 추가하지 않는다.

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/ops/seats` | 진입 | 파생 시트 뷰 (후보) |
| `GET` | `/api/v1/ops/seats/transitions` | 진입 | 상태 전이 이력 (후보) |
| `POST` | `/api/v1/ops/seats/{id}/disable` | 운영자 조치 | 비활성화 (후보) |

기존 시트 등록(`POST /seats`)과 머신 수령(토큰 반환)은 **이 화면의 API가 아니다.** 웹에서
평문 토큰을 다루지 않는다는 경계를 유지한다 (§12.1).

---

## 접근성 / 반응형

- [ ] WCAG 2.1 AA — 상태는 색 + 텍스트(`READY` 등) + 근거 칩 3중 표현
- [ ] 여유도 게이지에 `title`/`aria-label`로 등급 텍스트 제공 (색만으로 전달 금지)
- [ ] 표 `overflow-x: auto`
- [ ] 비활성 버튼에 사유를 텍스트로 제공 (`reset 대기` 등)

---

## 구현 노트

- 이 화면이 §24.1의 금지 표현("잔여 token API가 있으므로 정확히 배정할 수 있다")을 시각적으로
  위반하지 않는지가 리뷰 포인트다.
- 시트는 **사용자당 1개(ToS 방어)** 원칙이므로 한 사용자에게 여러 시트를 만들 수 있는 UI를 두지 않는다.
- `credential_ref`는 불투명 문자열로만 노출한다. fingerprint 외의 유도 가능 정보를 붙이지 않는다.
