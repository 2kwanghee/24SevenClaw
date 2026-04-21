# ClickEye Retouch — 상세 개발 플랜

> 작성일: 2026-04-13
> 기반 문서: `docs/spec/retouch.md`
> 상태: 컨펌 완료 → Linear 등록 → 개발 진행 중

## Context

현재 플랫폼은 7-Step 위저드, 오케스트레이터(10단계), 리뷰 파이프라인, 산출물 상태머신, 대시보드 등 핵심 백엔드가 구현되어 있으나, **RBAC / 프리셋 / 중앙 계약 관리 / 성숙도 평가 / 밸류 시각화**가 부재한 상태.

---

## 1. 변경 요구사항 → Linear 이슈 매핑

### Feature 1: 기본 프리셋 + 자연어 설정

| 이슈 ID | 제목 | 모듈 | 크기 | 의존성 |
|---------|------|------|------|--------|
| 24S-101 | 프리셋/성숙도 타입 스키마 정의 | contracts | S | — |
| 24S-102 | 프리셋 카탈로그 DB + 서비스 + API | api | M | 24S-101 |
| 24S-103 | 프리셋 선택 + 자연어 설정 UI | web | M | 24S-102 |
| 24S-104 | 에이전트 프리셋 동적 수신 핸들러 | agent | S | 24S-102 |

### Feature 2: RBAC (역할 기반 접근 제어)

| 이슈 ID | 제목 | 모듈 | 크기 | 의존성 |
|---------|------|------|------|--------|
| 24S-201 | RBAC 타입 스키마 정의 | contracts | S | — |
| 24S-202 | RBAC 모델 + 서비스 + 권한 미들웨어 | api | L | 24S-201 |
| 24S-203 | RBAC 관리 UI (사용자/조직/감사로그) | web | M | 24S-202 |

### Feature 3: 중앙 실행 계약 관리

| 이슈 ID | 제목 | 모듈 | 크기 | 의존성 |
|---------|------|------|------|--------|
| 24S-301 | 중앙 계약 타입 스키마 정의 | contracts | M | — |
| 24S-302 | 중앙 계약 관리 모델 + 서비스 + API | api | L | 24S-301, 24S-202 |
| 24S-303 | contract.sync 에이전트 핸들러 | agent | S | 24S-301 |
| 24S-304 | 중앙 계약 관리 UI | web | M | 24S-302, 24S-203 |

### Feature 4: 성숙도 평가지표

| 이슈 ID | 제목 | 모듈 | 크기 | 의존성 |
|---------|------|------|------|--------|
| 24S-401 | 성숙도 질문지 + 스코어링 엔진 | api | M | 24S-102 |
| 24S-402 | 성숙도 온보딩 흐름 UI | web | M | 24S-401, 24S-103 |

### Feature 5: 키밸류 (가치 시각화)

| 이슈 ID | 제목 | 모듈 | 크기 | 의존성 |
|---------|------|------|------|--------|
| 24S-501 | KPI 메트릭 집계 엔드포인트 확장 | api | M | — |
| 24S-502 | 가치 대시보드 KPI 시각화 | web | L | 24S-501 |

### Feature 6: AI Team 운영 대시보드

| 이슈 ID | 제목 | 모듈 | 크기 | 의존성 |
|---------|------|------|------|--------|
| 24S-601 | AI Team 3계층 운영 대시보드 UI | web | L | 24S-502 |
| 24S-602 | 산출물 상태머신 자동 전이 트리거 | api | M | — |

**총 17개 이슈** (S×4, M×9, L×4)

---

## 2. 모듈별 상세 구현 명세

### 2.1 Contracts (24S-101 + 24S-201 + 24S-301) — 단일 PR

**새 파일:**
- `protocol/presets.ts` — MaturityLevel, PresetProfile 타입
- `protocol/rbac.ts` — SystemRole, OrgRole, Permission 타입
- `protocol/central_contract.ts` — ContractSource, ContractType, CentralContract 타입
- `messages.ts`에 `'contract.sync'` 추가
- `python/protocol.py`에 Pydantic 미러링

### 2.2 API — 프리셋 (24S-102)

**DB:** `Preset`, `MaturityAssessment` 모델
**서비스:** `preset_service.py`, `maturity_service.py`
**엔드포인트:** `GET/POST /presets`, `POST /projects/{id}/configure-natural`
**마이그레이션:** 005

### 2.3 API — RBAC (24S-202)

**DB:** `users.system_role` 추가, `OrganizationMembership`, `RoleAuditLog`
**서비스:** `rbac_service.py` (check_permission, assign_role, org member CRUD)
**의존성:** `require_permission()` 팩토리
**마이그레이션:** 006

### 2.4 API — 중앙 계약 (24S-302)

**DB:** `CentralContract`, `CustomerContractOverride`, `ContractAuditLog`
**서비스:** `contract_service.py` (CRUD + allowed_overrides 검증 + WebSocket sync)
**마이그레이션:** 007

### 2.5 API — 성숙도 확장 (24S-401)

7개 질문 가중평균 스코어링, 회원가입 시 maturity_required 플래그

### 2.6 API — KPI 확장 (24S-501)

phase_duration, throughput, automation_rate, review_acceptance_rate

### 2.7 API — 자동 전이 (24S-602)

오케스트레이터 단계 전이 시 Artifact 상태 자동 갱신

### 2.8~2.13 Web — UI 구현

프리셋 UI, RBAC 관리, 중앙 계약 관리, 성숙도 온보딩, KPI 대시보드, AI Team 대시보드

### 2.14 Agent — 핸들러 (24S-104 + 24S-303)

config_handler.py, contract_handler.py 추가

---

## 3. DB 마이그레이션 전략

```
기존: 001 → 002 → 003 → 004 → 7ed6d815b022
추가:
  005_add_presets_and_maturity_tables
  006_add_rbac_tables
  007_add_central_contracts_tables
```

모든 마이그레이션 additive, server_default 사용, JSONB 적용

---

## 4. 병렬 작업 가이드

```
Phase 0 — Foundation
  [contracts] 24S-101+201+301 단일 PR → [api] 24S-202 RBAC + 24S-602 자동전이

Phase 1 — Core (3개 트랙 병렬)
  Track A: 24S-102→103→104 (프리셋)
  Track B: 24S-203 (RBAC UI)
  Track C: 24S-501 (KPI)

Phase 2 — Extended (2개 트랙 병렬)
  Track A: 24S-302→303→304 (중앙 계약)
  Track B: 24S-401→402→502 (성숙도+밸류)

Phase 3 — AI Team
  24S-601 (AI Team 대시보드)
```

**에이전트 배정:**
- Agent A: contracts → api RBAC → api 중앙 계약
- Agent B: web 프리셋 → web RBAC → web 중앙 계약
- Agent C: api 프리셋 → api KPI → api 성숙도
- Agent D: agent 핸들러 → web 가치 대시보드

---

## 5. 검증 계획

- 단위: 서비스 메서드별 3건+, RBAC 전체 역할×권한 매트릭스
- 통합: 회원가입→성숙도→프리셋→위저드 E2E, 계약 생성→sync→에이전트
- UI: 개발 서버 실행 후 브라우저 검증
