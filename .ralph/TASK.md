# 24S-80: [api] 중앙 계약 관리 모델 + 서비스 + API — 구현 결과

## 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `24SevenClaw-api/app/models/central_contract.py` | CentralContract, CustomerContractOverride, ContractAuditLog 모델 |
| `24SevenClaw-api/app/models/__init__.py` | 모델 등록 |
| `24SevenClaw-api/app/schemas/contract.py` | Pydantic 스키마 (CRUD + override + audit) |
| `24SevenClaw-api/app/services/contract_service.py` | CRUD, apply_contract_to_project, update_customer_override, sync_contracts_to_agent, 감사 로그 |
| `24SevenClaw-api/app/api/v1/contracts.py` | 엔드포인트 (contracts CRUD, overrides, sync, audit) |
| `24SevenClaw-api/app/api/v1/router.py` | 라우터 등록 |
| `24SevenClaw-api/alembic/versions/008_add_central_contracts_tables.py` | 마이그레이션 |
| `24SevenClaw-api/tests/test_contracts.py` | 16개 테스트 |

## 구현 내용

- **DB 모델**: CentralContract (slug unique, contract_type, source, version, content JSONB, is_locked, allowed_overrides), CustomerContractOverride (project FK, contract FK, override_content JSONB, approved_by, is_active), ContractAuditLog (contract FK, override FK, actor FK, change_type, diff_snapshot JSONB)
- **서비스**: superadmin 전용 CRUD + 감사 로그 자동 기록, allowed_overrides 검증 (허용 필드 외 수정 시 422), WebSocket contract.sync 전송
- **엔드포인트**: GET/POST/PUT/DELETE /api/v1/contracts, GET/POST/PATCH /api/v1/projects/{id}/contract-overrides, POST /api/v1/projects/{id}/contracts/sync, GET /api/v1/contracts/audit

## 테스트 결과

- 16 passed in 6.00s
- ruff check: All checks passed

## 남은 이슈

- 없음
