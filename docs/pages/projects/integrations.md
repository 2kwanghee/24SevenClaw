---
title: 외부 연동 게이트 (프로젝트 탭)
category: page
status: draft
version: 0.1.0
last_updated: 2026-07-29
route: /projects/[projectId]/integrations
pages:
  - src/app/(dashboard)/projects/[projectId]/integrations/page.tsx  # 후보 — 미생성
components:
  - src/components/projects/integrations/gate-table.tsx             # 후보 — 미생성
  - src/components/projects/integrations/phase-block-matrix.tsx      # 후보 — 미생성
  - src/components/projects/integrations/secret-ref-cell.tsx         # 후보 — 미생성
related:
  - migration.md
  - docs/wireframes/multiproject-delivery.html
---

> **구현 금지.** `migration.md` Stage 0.5 산출물. Stage 1(Manifest·Human Gate) 승인 전 코드 생성 금지.

## 목적

**만들어주는 프로덕트에 녹여야 하는 외부 연동**을 명시적 blocker로 관리한다.
ClickEye 자체가 쓰려는 연동이 아니다 (I-08 정의 확정, 2026-07-29).

> 예: 회사 홈페이지를 만들면 회사 위치 표시와 길찾기가 필요하다. AI는 그 지도 API 계정을 만들
> 수 없으므로 **고객(사용자)이 직접 발급해 API KEY를 입력하는 별도 작업**이 필요하다.
> 이 화면은 그 사람 작업을 추적한다.

blocker가 기록만 되고 아무도 해결하지 않는 상태를 막는 것이 이 화면의 존재 이유다.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ 상태별 요약 (VERIFIED / VALIDATING / AWAITING_OWNER / REQUIRED)│
├─────────────────────────────────────────────────────────────┤
│ 게이트 표                                                    │
│ 연동 │ 상태 │ 차단 phase │ 담당 │ 비밀값 참조 │ 조치           │
│ 카카오 로그인 │VERIFIED│차단없음│소유자│secret_ref+fp│재검증    │
│ 결제 모듈     │AWAITING│검증·배포│소유자│미등록      │요청재발송 │
├──────────────────────────┬──────────────────────────────────┤
│ phase 별 차단 효과        │ CREDENTIAL_SAVED 경고 (§12.2)     │
│ 구현 가능 / 검증 차단 /   │ 알림 채널 (I-08 미확정)           │
│ 배포 차단                 │                                  │
└──────────────────────────┴──────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: blocker 확인**
1. 진입 → `AWAITING_OWNER` 게이트와 그것이 막는 phase 확인
2. 담당자와 요청 발송 이력 확인

**시나리오 2: phase별 부분 진행**
1. 결제 운영 키가 없어도 **구현은 mock으로 진행 가능**
2. 검증·배포만 차단 — "전부 막기"가 기본값이 아님 (§6.4)

**시나리오 3: 비밀값 등록**
1. 소유자가 Secret Manager에 실제 값을 등록
2. ClickEye는 `secret_ref` + fingerprint만 수신 → `CREDENTIAL_SAVED`
3. `VALIDATING` → 성공 시 `VERIFIED`, 실패 시 `FAILED` → `AWAITING_OWNER`

---

## 기능 요구사항

### 필수 기능
- [ ] 게이트 상태 — `REQUIRED / AWAITING_OWNER / CREDENTIAL_SAVED / VALIDATING / VERIFIED / FAILED / BLOCKED`
- [ ] **게이트별 차단 phase 표시** (구현·검증·배포 중 무엇을 막는지)
- [ ] phase별 차단 효과 요약 — 구현 가능/검증 차단/배포 차단을 사유와 함께
- [ ] 담당(owner) 표시 및 미지정 상태 노출
- [ ] `secret_ref` + fingerprint만 표시. **실제 값·마스킹 값 모두 금지** (§12.2)
- [ ] 요청 재발송 이력 (누구에게·언제)
- [ ] 게이트 해소 시 관련 Job이 `BLOCKED → QUEUED`로 복귀함을 안내

### 확정 사항 (I-08, 2026-07-29)

- [ ] 담당 = **고객(프로젝트 소유자)**. 사람 개발자 배정 개념을 도입하지 않는다
- [ ] 1차 알림 채널 = **ClickEye Web** — 고객이 키를 입력하는 화면과 알림 지점을 일치시킨다
- [ ] 게이트 카드는 "무엇을 발급해 어디에 넣어야 하는지"가 고객에게 **자족적으로** 읽혀야 한다
- [ ] 이메일·메신저 확장은 **보류** — 위 자족성이 확인된 뒤 판단

### 선택/개선 사항
- [ ] 게이트 템플릿 (카카오·지도·결제·DNS/SSL·앱스토어) 프리셋
- [ ] 검증 실패 사유 상세

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `gates` | `HumanIntegrationGate[]` | `GET .../integrations` | 게이트 표 |
| `phaseBlocks` | `PhaseBlockSummary` | 동일 응답 파생 | 차단 효과 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/projects/{id}/integrations` | 진입 | 게이트 목록 (후보) |
| `POST` | `/api/v1/projects/{id}/integrations/{gateId}/notify` | 요청 재발송 | 담당자 알림 (후보, I-08 확정 후) |
| `POST` | `/api/v1/projects/{id}/integrations/{gateId}/validate` | 재검증 | 검증 트리거 (후보) |

API는 Secret의 실제 값을 읽거나 응답하지 않는다 (§12.2).

---

## 접근성 / 반응형

- [ ] 상태는 색 + 텍스트 병기
- [ ] 차단 phase는 칩으로 나열해 스크린리더가 개별 인식 가능하게
- [ ] 표 `overflow-x: auto`
- [ ] 비활성 버튼에 사유 텍스트 제공 (`검증 중` 등)
- [ ] 긴 `secret_ref` `overflow-wrap: anywhere`

---

## 구현 노트

- `CREDENTIAL_SAVED`가 "ClickEye DB에 비밀값이 저장됨"으로 읽히면 안 된다. 화면에 경고 문구를
  상시 노출한다 (§6.4).
- 담당자 지정 UI는 사람 개발자 배정이 아니다 — §1.1의 금지 범위(인력 관리)로 번지지 않게
  **프로젝트 소유자/사용자 역할만** 다룬다.
- 게이트 해소를 AI가 자동 처리하는 액션을 만들지 않는다 (계정 발급·심사·동의는 사람 작업).
