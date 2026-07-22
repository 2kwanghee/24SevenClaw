---
title: 운영 패널 (Superadmin)
category: page
status: implemented
version: 1.0.0
last_updated: 2026-07-22
route: /admin/ops
pages:
  - src/app/(dashboard)/admin/ops/page.tsx
components:
  - src/components/admin/ops/OpsContainer.tsx
  - src/components/admin/ops/OpsEnv.tsx
  - src/components/admin/ops/OpsTables.tsx
store: useRBACStore (superadmin만 접근)
related:
  - src/app/(dashboard)/admin/ops/page.tsx
  - clickeye-api/app/api/v1/ops_*.py
  - clickeye-api/app/services/ops/*
---

## 목적
Superadmin이 실행 중인 Docker 컨테이너, 환경변수, 화이트리스트 테이블을 관리하는 운영 대시보드.

---

## 레이아웃

```
┌─────────────────────────────────────────────────┐
│ 운영 패널 (Superadmin)                           │
├──────────────────────────────────────────────────┤
│ [탭] 컨테이너 | 포트 | 환경변수 | 테이블        │
├──────────────────────────────────────────────────┤
│                                                  │
│ ▶ 컨테이너 (read-only)                           │
│  ├─ clickeye-web (running) [3000]               │
│  ├─ clickeye-api (running) [8000]               │
│  ├─ postgres (running) [5432]                   │
│  └─ redis (running) [6379]                      │
│                                                  │
│ ▶ 포트 프로브 (read-only)                        │
│  └─ Open ports: 3000, 8000, 5432, 6379         │
│                                                  │
│ ▶ 환경변수 (CRUD)                               │
│  ├─ KEY: OPENAI_API_KEY   [***] [수정] [삭제]   │
│  └─ KEY: LINEAR_API_KEY   [***] [수정] [삭제]   │
│  [+ 추가]                                        │
│                                                  │
│ ▶ 화이트리스트 테이블 (CRUD)                     │
│  ├─ app_settings / key         [편집] [제거]    │
│  ├─ roi_standards / tier        [편집] [제거]   │
│  └─ presets / name             [편집] [제거]    │
│  [+ 추가]                                        │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 환경변수 수정**
1. Superadmin이 /admin/ops에 진입 (RoleGuard superadmin만)
2. "환경변수" 탭 선택
3. 환경변수 항목에서 [수정] 버튼 클릭
4. 입력 필드에 새 값 입력 후 저장
5. Fernet 암호화되어 서버에 저장됨
6. 명령 미리보기 제공 (docker 미실행, 수동 적용 필요)

**시나리오 2: 컨테이너 상태 모니터링**
1. "컨테이너" 탭 선택
2. 실행 중인 컨테이너 목록 조회 (docker API, read-only)
3. 각 컨테이너 상태/포트 확인

**시나리오 3: 화이트리스트 테이블 관리**
1. "테이블" 탭 선택
2. 편집 가능한 테이블(app_settings/roi_standards/presets) 확인
3. 필요 시 항목 추가/수정/삭제 (민감 테이블은 404)

---

## 기능 요구사항

### 필수 기능
- [x] Superadmin 역할 제한 (RoleGuard)
- [x] 컨테이너 목록 조회 (read-only, GET /admin/ops/containers)
- [x] 포트 프로브 결과 조회 (read-only, GET /admin/ops/ports)
- [x] 환경변수 조회 (GET /admin/ops/env, Fernet 암호화)
- [x] 환경변수 수정 (PUT /admin/ops/env/{key})
- [x] 환경변수 삭제 (DELETE /admin/ops/env/{key})
- [x] 환경변수 적용 명령 미리보기 (POST /admin/ops/env/render, docker 미실행)
- [x] 화이트리스트 테이블 조회 (GET /admin/ops/tables)
- [x] 화이트리스트 테이블 CRUD (POST/PUT/DELETE, 민감 테이블 제외)
- [x] 탭 인터페이스 (컨테이너/포트/환경변수/테이블)

### 선택/개선 사항
- [ ] 환경변수 변경 이력 조회
- [ ] 대량 업로드 (CSV)
- [ ] 환경변수 롤백
- [ ] 컨테이너 로그 조회

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `containers` | `Container[]` | `GET /admin/ops/containers` | 실행 중 컨테이너 목록 |
| `ports` | `number[]` | `GET /admin/ops/ports` | 열린 포트 목록 |
| `envVars` | `EnvVar[]` | `GET /admin/ops/env` | 환경변수 목록(암호화) |
| `tables` | `TableWhitelist[]` | `GET /admin/ops/tables` | 편집 가능 테이블 |
| `activeTab` | `'containers'\|'ports'\|'env'\|'tables'` | 로컬 | 현재 탭 |
| `renderCommand` | `string` | `POST /admin/ops/env/render` | 적용 명령 미리보기 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/admin/ops/containers` | 페이지 로드 | 실행 중 컨테이너(read-only) |
| `GET` | `/api/v1/admin/ops/ports` | 페이지 로드 | 포트 프로브 결과 |
| `GET` | `/api/v1/admin/ops/env` | 페이지 로드 | 환경변수 조회 |
| `PUT` | `/api/v1/admin/ops/env/{key}` | [저장] 클릭 | 환경변수 수정 |
| `DELETE` | `/api/v1/admin/ops/env/{key}` | [삭제] 클릭 | 환경변수 삭제 |
| `POST` | `/api/v1/admin/ops/env/render` | 환경변수 수정 후 | 적용 명령 미리보기 |
| `GET` | `/api/v1/admin/ops/tables` | 페이지 로드 | 화이트리스트 테이블 |
| `POST` | `/api/v1/admin/ops/tables` | [추가] 클릭 | 테이블 항목 생성 |
| `PUT` | `/api/v1/admin/ops/tables/{id}` | [편집] 저장 | 테이블 항목 수정 |
| `DELETE` | `/api/v1/admin/ops/tables/{id}` | [제거] 클릭 | 테이블 항목 삭제 |

---

## 접근성 / 반응형

- [x] Superadmin 역할 검증 (RoleGuard)
- [x] 색상 대비 4.5:1 이상 (WCAG AA)
- [x] 키보드 네비게이션 (Tab/Enter/Escape)
- [x] `aria-label`, `role` 적용
- [x] 모바일/태블릿/데스크톱 반응형
- [x] 환경변수 값은 마스킹 표시(*** 또는 숨김)
- [x] 환경변수 적용 명령은 미리보기만 (자동 실행 안 함)
- [x] 에러/성공 메시지 사용자 안내

---

## 구현 노트

- **환경변수 암호화**: Fernet 256-bit 키로 암호화하여 저장. `JWT_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`은 편집 불가(민감).
- **명령 미리보기**: `POST /admin/ops/env/render`은 docker를 실행하지 않고 명령만 반환. 실제 적용은 수동(로컬/서버에서 docker-compose restart).
- **화이트리스트 테이블**: `app_settings`, `roi_standards`, `presets`만 CRUD 가능. 민감 테이블(`users`, `projects` 등)은 404 반환.
- **Docker API**: 내부망 `dockerproxy` (tecnativa, POST 차단)를 통한 read-only 컨테이너 조회.
