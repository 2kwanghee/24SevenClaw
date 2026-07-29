---
title: 배포 · DeploymentRun (프로젝트 탭)
category: page
status: draft
version: 0.1.0
last_updated: 2026-07-29
route: /projects/[projectId]/deployment
pages:
  - src/app/(dashboard)/projects/[projectId]/deployment/page.tsx   # 후보 — 미생성
components:
  - src/components/projects/deployment/deploy-state-rail.tsx       # 후보 — 미생성
  - src/components/projects/deployment/preflight-checklist.tsx     # 후보 — 미생성
  - src/components/projects/deployment/healthcheck-table.tsx       # 후보 — 미생성
  - src/components/projects/deployment/acceptance-card.tsx         # 후보 — 미생성
related:
  - migration.md
  - docs/wireframes/multiproject-delivery.html
---

> **구현 금지.** `migration.md` Stage 0.5 산출물. Stage 4(Deploy Runner MVP) 승인 전 코드 생성 금지.
> 현재 Agent의 Docker `stop/destroy`와 격리는 완결되지 않았다 — 완성으로 가정하지 않는다 (§13).

## 목적

Manifest가 선언한 환경에서 재현 가능한 build와 healthcheck를 통과했는지 보여주고,
사용자가 테스트 URL에서 인수 테스트를 수행할 수 있게 한다.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ 배포 헤더 — dep-7c1a · [HEALTHCHECKING] · linux/amd64        │
│ 레일 REQUESTED→PREFLIGHT→BUILDING→BUILT→STARTING→            │
│      HEALTHCHECKING→READY_FOR_ACCEPTANCE→ACCEPTED            │
│ 칩: compose namespace · image digest · network · label        │
├──────────────────────────────────┬──────────────────────────┤
│ preflight 체크리스트 (6항목)       │ 테스트 URL (I-09 미확정)  │
│ healthcheck 표                    │ 인수 테스트 (I-10 미확정) │
│                                  │ rollback (volume 보존)    │
└──────────────────────────────────┴──────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 정상 배포**
1. preflight 6항목 통과 → build → image digest 기록
2. migration 명령 실행 → container 시작
3. healthcheck 통과 → 테스트 URL 발급 → `READY_FOR_ACCEPTANCE`
4. 사용자 로그인 인수 테스트 → 승인 시 `ACCEPTED`

**시나리오 2: healthcheck 미통과**
1. 일부 검사가 진행 중/실패
2. **테스트 URL을 발급하지 않음** — 버튼 비활성 + 사유 표시
3. 실패 확정 시 `FAILED → ROLLING_BACK → ROLLED_BACK`

**시나리오 3: 게이트 미충족**
1. 배포를 막는 게이트가 `VERIFIED`가 아니면 preflight에서 중단
2. 외부 연동 탭으로 유도

**시나리오 4: 보완 요청**
1. 사용자가 인수 테스트에서 보완 요청
2. 보완 Job이 생성됨 (실행 탭으로 연결)

---

## 기능 요구사항

### 필수 기능
- [ ] 배포 lifecycle 레일 — §13 상태 전체(오류 경로 `FAILED/ROLLING_BACK/ROLLED_BACK` 포함)
- [ ] preflight 체크리스트 — 활성 Manifest·CONTROL 재검증 / 게이트 `VERIFIED` / workspace clean·checkpoint / namespace·network·volume·port 할당 / Secret 참조 resolve / migration 실행
- [ ] 격리 명명 노출 — `ce-<project_short_id>-<deployment_short_id>`, `clickeye.project_id` 라벨
- [ ] image digest 기록
- [ ] healthcheck 표 — 검사·결과·응답시간, 진행 중 상태 구분
- [ ] **healthcheck 통과 전 테스트 URL 발급 금지** (§23 수용 기준)
- [ ] 인수 테스트 승인 / 보완 요청 2액션
- [ ] rollback 결과 — container·network 정리 여부와 **volume은 자동 삭제하지 않음**을 명시

### 확정 사항 (2026-07-29 인터뷰)

- **I-09 확정 — 사내 `아이피:포트`.** 도메인·DNS·TLS를 쓰지 않는다.
  - [ ] 표시 형식 `http://<host-ip>:<port>`, 접근 범위 "사내망" 명시
  - [ ] 포트는 `runtime/ports.json` 기반 프로젝트별 할당, **충돌 방지와 회수**가 필수 구현 항목
  - [ ] 배포 테스트 주체는 우리(코드 소유는 고객) — 고객 원격 접근 UI를 만들지 않는다
  - MVP 난이도 하락: §14의 "DNS·TLS·port allocation" 중 **port allocation만 남는다**
- **I-10 확정 — 사람이 개입한다. AI 자동화로 대체하지 않는다.**
  - [ ] 화면은 사람의 판단을 **기록**만 한다. 통과 추론·자동 승인 금지
  - [ ] 결함 등록·재검증 워크플로를 만들지 않는다 (별도 QA 제품화 방지, §1.1)
  - [ ] 보완 요청은 실행 탭의 보완 Job으로만 연결

### 선택/개선 사항
- [ ] 배포 이력 목록 (이전 DeploymentRun)
- [ ] 보존 기간 표시 — **I-11 확정 후**

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `runs` | `DeploymentRun[]` | `GET .../deployments` | 이력 |
| `run` | `DeploymentRunDetail` | `GET .../deployments/{id}` | 레일·칩·preflight |
| `health` | `HealthcheckResult[]` | 동일 응답 + WS | healthcheck 표 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/projects/{id}/deployments` | 진입 | 배포 이력 (후보) |
| `POST` | `/api/v1/projects/{id}/deployments` | 배포 요청 | `REQUESTED` 생성 (후보) |
| `POST` | `/api/v1/projects/{id}/deployments/{depId}/accept` | 승인 | `ACCEPTED` (후보) |
| `POST` | `/api/v1/projects/{id}/deployments/{depId}/rollback` | 롤백 | namespace 정리 (후보) |
| WS | 기존 Agent 채널 | 상시 | build/start/health 진행 보고 |

MVP 지원 범위는 Linux/amd64 + Dockerfile/Compose + PostgreSQL·SQLite·ClickHouse + HTTP
healthcheck다. Windows·RedHat·특수 MSSQL·GPU를 지원한다고 표시하지 않는다 (§14 · §24.1).

---

## 접근성 / 반응형

- [ ] 레일에 `role="img"` + 현재 단계 `aria-label`
- [ ] 단계 이름이 길어 줄바꿈되므로 `<wbr>` 또는 `overflow-wrap` 적용
- [ ] 표 `overflow-x: auto`, 응답시간 `tabular-nums`
- [ ] 비활성 버튼에 사유 텍스트 (`healthcheck 미통과` 등)
- [ ] 성공/실패는 색 + 텍스트 + 아이콘 3중 표현

---

## 구현 노트

- 이 화면은 정리(stop/destroy)까지 끝났다고 표현하지 않는다. 정리 결과를 **별도 항목으로 보고**한다.
- rollback은 schema downgrade가 아니다 (§21.2). volume 삭제는 Manifest가 disposable로 명시하지
  않는 한 별도 승인이 필요하다.
- ClickEye API용 docker proxy를 제품 배포기로 쓰지 않는다 — 전용 Runner host를 전제한다 (§3 · §20).
