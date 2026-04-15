# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [ ] **[api] 중앙 계약 관리 모델 + 서비스 + API**
  > 요청사항: ## 개요

중앙 실행 계약 관리 시스템을 API에 구현한다. 중앙 레포에서 관리하는 계약을 고객 프로젝트에 배포하고, 허용된 필드만 오버라이드 가능하도록 제어한다.

## 선행 조건

* [24S-72](https://linear.app/flow-ops/issue/24S-72/contracts-중앙-계약-타입-스키마-정의) (중앙 계약 타입) + [24S-73](https://linear.app/flow-ops/issue/24S-73/api-rbac-모델-서비스-권한-미들웨어) (RBAC) 완료 필수

## 범위

### DB 모델 (models/central_contract.py)

* CentralContract: slug unique, contract_type, source, version, content JSONB, is_locked default=True, allowed_overrides JSON=\[\]
* CustomerContractOverride: project_id FK, central_contract_id FK, override_content JSONB, approved_by FK nullable, is_active
* ContractAuditLog: contract_id FK, override_id FK, actor_id FK, change_type, diff_snapshot JSONB

### 서비스 (services/contract_service.py)

* CRUD (superadmin 전용, 감사로그 자동 기록)
* apply_contract_to_project() -> CustomerContractOverride 생성
* update_customer_override() -> allowed_overrides 필드만 수정 허용, 그 외 422
* sync_contracts_to_agent() -> WebSocket contract.sync 전송

### 엔드포인트

* GET/POST/PUT/DELETE /api/v1/contracts (admin+)
* GET/POST/PATCH /api/v1/projects/{id}/contract-overrides
* POST /api/v1/projects/{id}/contracts/sync
* GET /api/v1/contracts/audit

### 마이그레이션: 007_add_central_contracts_tables.py

## 완료 조건

- DB 모델 + 마이그레이션
- allowed_overrides 외 필드 수정 시 422 반환 테스트
- WebSocket sync 동작 확인
- 감사 로그 기록 확인

## 크기: L

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|