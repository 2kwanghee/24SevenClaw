---
title: 인테이크 검토 콘솔
category: page
status: implemented
version: 1.0.0
last_updated: 2026-07-23
route: /admin/intake
pages:
  - src/app/(dashboard)/admin/intake/page.tsx
components:
  - src/hooks/use-intake.ts
store: 없음 (TanStack Query 사용)
related:
  - src/app/(dashboard)/admin/intake/page.tsx
  - src/hooks/use-intake.ts
  - clickeye-api/app/api/v1/intake.py
  - clickeye-api/app/schemas/intake.py
---

## 목적
외부 서비스가 발송한 요구사항 정의서(수주 인테이크)를 검토하고 승인/반려하는 관리자 게이트. 승인 시 딜리버리 프로젝트를 자동 생성하고, 반려 시 사유를 기록한다.

---

## 레이아웃

```
┌────────────────────────────────────────────────────────────────┐
│ 헤더 (Inbox 아이콘) "인테이크 검토 콘솔"                          │
├────────────────────────────────────────────────────────────────┤
│ 상태 탭: [Pending Review] [Accepted] [Rejected] [서비스 키...   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ 타이틀         | Input Type | 우선순위 | 수신일시 | 작업  │   │
│ ├─────────────────────────────────────────────────────────┤   │
│ │ [수주1]        | structured | high    | 2026-07-21 | [승인][반려] │
│ │ (클릭 시 상세 전개)                                      │   │
│ │  └─ 정규화 본문 미리보기                                  │   │
│ │  └─ 원본 URL (있을 시)                                   │   │
│ │  └─ 타깃 요약 (target 필드)                              │   │
│ │  └─ 생성된 프로젝트 링크 (수용 시)                         │   │
│ │                                                         │   │
│ │ [수주2]        | url        | —       | 2026-07-20 | [승인][반려] │
│ │ ...                                                     │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                │
│ (accepted/rejected 탭에서는 목록만 표시, 작업 버튼 없음)         │
│                                                                │
│ [모달: 승인 확인 다이얼로그]                                    │
│ "'{title}' 요구사항을 승인하시겠습니까?"                         │
│ [취소] [승인]                                                  │
│                                                                │
│ [모달: 반려 사유 입력]                                          │
│ "'{title}' 요구사항을 반려합니다."                              │
│ [반려 사유 (선택):] [텍스트 에어리어]                            │
│ [취소] [반려]                                                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

> **서비스 키 관리 탭** (superadmin만 표시):
```
┌────────────────────────────────────────────────────────────────┐
│ "외부 서비스가 이 키를 이용해 /api/v1/intake로 수주를 발송합니다." │
│                                                                │
│ [키 이름] [__________] [발급]                                   │
│                                                                │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ 이름    | 조직 ID     | 상태    | 발급일   | 작업         │   │
│ ├─────────────────────────────────────────────────────────┤   │
│ │ key-1   | org-abc123  | Active  | 2026-01-01 | [비활성화] │   │
│ │ key-2   | —           | Inactive| 2026-01-15 | —         │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                │
│ [모달: 키 발급 직후 1회 평문 노출]                               │
│ "⚠️ 평문 키는 이 화면에서만 볼 수 있습니다. 안전히 저장하세요."  │
│ [xxxxxxxxxxxxxxxxxxxxxxxx] [복사]                              │
│ [확인]                                                         │
│                                                                │
│ [확인: Type-to-Confirm로 '키 이름' 입력 후 비활성화]             │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 수주 검토 → 승인**
1. Admin이 /admin/intake 진입 → "Pending Review" 탭 기본 표시
2. 목록에서 수주 항목을 클릭 → 행 전개, 정규화 본문 미리보기
3. [승인] 버튼 클릭 → 확인 모달 표시
4. "승인" 버튼 클릭 → `POST /api/v1/intake/{id}/accept` 호출
5. 성공 시 `toast.success("승인했습니다")` + 프로젝트 링크 버튼 표시
6. 목록에서 해당 항목 제거 (또는 상태 변경), "Accepted" 탭에 이동

**시나리오 2: 수주 검토 → 반려**
1. [반려] 버튼 클릭 → 사유 입력 모달 표시
2. 사유 입력 (선택) → [반려] 버튼 클릭
3. `POST /api/v1/intake/{id}/reject` + 사유 payload 호출
4. 성공 시 `toast.success("반려했습니다")` → "Rejected" 탭 표시

**시나리오 3: 서비스 키 발급 (Superadmin)**
1. "서비스 키" 탭 클릭 → 발급 폼 + 키 목록 표시
2. 키 이름 입력 → [발급] 버튼 클릭
3. `POST /api/v1/intake/service-keys` 호출
4. 응답에서 평문 키 1회 노출 → 모달로 "안내 배너 + 평문 표시 + 복사 버튼"
5. [확인] 클릭 → 모달 닫힘 (이후 평문은 미노출, 목록에서 해시만 표시)
6. 목록 자동 갱신

**시나리오 4: FEATURE_INTAKE 토글 OFF**
1. 백엔드 설정 `FEATURE_INTAKE=false` (기본값)
2. 페이지 진입 시 `GET /api/v1/intake` → 404 응답
3. `isFeatureDisabled` 함수 감지 → "Pending Review" 탭에 위치에 "기능 사용 안 함" 배너 표시

---

## 기능 요구사항

### 필수 기능 ✓ (구현됨)
- [x] 상태 탭 (Pending Review / Accepted / Rejected) 렌더링
- [x] 상태별 인테이크 목록 조회 (`GET /api/v1/intake?status_filter=pending_review` 등)
- [x] 인테이크 행 클릭 시 상세 정보 전개 (정규화 본문, 원본 URL, target, 프로젝트 링크)
- [x] 승인 다이얼로그 → `POST /api/v1/intake/{id}/accept` 호출 → Project 생성
- [x] 반려 다이얼로그 (사유 입력, 선택) → `POST /api/v1/intake/{id}/reject` 호출
- [x] Toast 알림 (성공/실패)
- [x] 서비스 키 탭 (superadmin만 표시) → `GET /api/v1/intake/service-keys`
- [x] 키 발급 폼 → `POST /api/v1/intake/service-keys` → 평문 1회 표시 + 복사 버튼
- [x] 키 목록 렌더링 (이름, 조직 ID, 활성/비활성, 생성일)
- [x] 키 비활성화 → `DELETE /api/v1/intake/service-keys/{key_id}` → type-to-confirm
- [x] FEATURE_INTAKE 토글 감지 → 404 시 "기능 사용 안 함" 배너 표시
- [x] Admin+ 권한 검증 (`RoleGuard roles={["superadmin", "admin"]}`)
- [x] 정제 스펙 섹션 (CE-310): `refine_status` 뱃지(정제 대기/정제됨/건너뜀) + 원문↔정제 스펙 2컬럼 비교, 승인 다이얼로그에 "정제 스펙으로 프로젝트 생성" 안내. 정제 실행은 로컬 배치 `scripts/intake_refine.sh`(FLOWOPS_INTAKE_REFINE, claude -p + metaprompt) — 서버는 머신 엔드포인트(`GET /intake/refine/pending`, `POST /intake/{id}/refined`)로 조율만

### 선택/개선 사항
- [ ] 검색/필터 (타이틀, 우선순위, 입력 타입)
- [ ] 페이지네이션
- [ ] 다중 선택 후 일괄 승인/반려

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `data` (목록) | `IntakeResponse[]` | `useIntakeList(status)` | 상태별 인테이크 목록 |
| `acceptTarget` | `IntakeResponse\|null` | Local state | 승인 확인 다이얼로그 표시 여부 |
| `rejectTarget` | `IntakeResponse\|null` | Local state | 반려 사유 입력 다이얼로그 표시 여부 |
| `rejectReason` | `string` | Local state | 반려 사유 텍스트 |
| `createdKey` | `string\|null` | Local state | 발급된 평문 키 (1회 표시) |
| `tab` | `"pending_review"\|"accepted"\|"rejected"\|"service-keys"` | Local state | 현재 활성 탭 |
| `expanded` | `boolean` (per row) | Local state | 각 행의 상세 전개 여부 |
| `isSuperadmin` | `boolean` | `useRBACStore` | 서비스 키 탭 표시 여부 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/intake?status_filter=pending_review\|accepted\|rejected` | 탭 변경 | 상태별 인테이크 목록 |
| `POST` | `/api/v1/intake/{id}/accept` | "승인" 확인 | 수주 승인 → Project 생성 |
| `POST` | `/api/v1/intake/{id}/reject` | "반려" 확인 | 수주 반려 + 사유 기록 |
| `GET` | `/api/v1/intake/service-keys` | 서비스 키 탭 진입 | 키 목록 조회 (superadmin) |
| `POST` | `/api/v1/intake/service-keys` | "발급" 버튼 클릭 | 키 생성 (평문 1회 반환) |
| `DELETE` | `/api/v1/intake/service-keys/{key_id}` | "비활성화" 확인 | 키 비활성화 |

**인증 방식**:
- 수주 접수 (`POST /intake`): `X-ClickEye-Service-Key` 헤더 (머신 인증)
- 검토/관리 (`GET`, `POST`, `DELETE`): JWT (Admin+)

**응답 스키마**:
```typescript
// IntakeResponse
{
  id: UUID;
  service_key_id: UUID;
  input_type: "structured" | "document" | "url";
  title: string;
  payload: Record<string, any>;
  normalized_text?: string;
  source_url?: string;
  target?: Record<string, any>;
  priority?: string;
  status: "pending_review" | "accepted" | "rejected";
  project_id?: UUID;
  created_at: ISO8601;
}

// ServiceKeyResponse
{
  id: UUID;
  name: string;
  organization_id?: UUID;
  is_active: boolean;
  created_at: ISO8601;
}

// ServiceKeyCreatedResponse (발급 직후만, 평문 포함)
{
  ...ServiceKeyResponse,
  key: string; // 평문 키, 1회만 노출
}
```

---

## 접근성 / 반응형

- [x] WCAG 2.1 AA — 색상 대비: 승인(emerald-600), 반려(red-700), 상태 배지 모두 4.5:1 이상
- [x] 키보드 네비게이션: Tab/Enter로 탭 전환, 행 클릭/Escape로 전개 해제
- [x] `aria-label` 적용: 버튼(승인/반려/복사), 탭, 모달 제목(`titleId`)
- [x] 모바일 (sm 미만): 테이블 → 단일 열(카드 스타일)로 변환, 탭 스크롤 가능
- [x] 태블릿 (md): 테이블 3~4 열로 축소
- [x] 데스크톱 (lg+): 전체 테이블 (5 열)
- [x] 로딩 상태: 텍스트 "로드 중..." 표시
- [x] 에러 상태: 적색 배너 + 에러 메시지 (404는 "기능 사용 안 함" 배너로 분류)
- [x] 다크모드: CSS 변수 `--bg-surface`, `--border-subtle`, `--text-primary` 등 사용

---

## 권한 및 접근 제어

| 엔드포인트/기능 | Superadmin | Admin | Others |
|-----------------|-----------|-------|--------|
| 목록 조회 (`GET /intake`) | 전체 | 자기 조직 키 접수분만 | ❌ |
| 승인/반려 (`POST /{id}/accept\|reject`) | ✓ | ✓ | ❌ |
| 서비스 키 관리 (발급/조회/비활성화) | ✓ | ❌ | ❌ |
| 페이지 진입 (`/admin/intake`) | ✓ | ✓ | ❌ (RoleGuard) |

**구현**:
- `<RoleGuard roles={["superadmin", "admin"]}>` — 페이지 전체 보호
- `useRBACStore().isSuperadmin()` — 서비스 키 탭 조건부 렌더링
- 백엔드 `require_permission("control_tower:read|write")` + `require_superadmin` 의존성

---

## FEATURE_INTAKE 토글

**기본값**: `false` (기능 사용 안 함)

**동작**:
1. 설정에서 `FEATURE_INTAKE=true`로 활성화
2. `/admin/intake` 진입 시 `GET /api/v1/intake` 호출
   - `FEATURE_INTAKE=true`: 200 + 목록 반환
   - `FEATURE_INTAKE=false`: 404 반환 (존재 자체를 은닉)
3. 프론트엔드 `isFeatureDisabled()` 함수:
   ```typescript
   function isFeatureDisabled(error: unknown): boolean {
     return error instanceof ApiClientError && error.status === 404;
   }
   ```
4. 404 감지 시 → 모든 탭에 위치에 **주황색 안내 배너** 표시:
   ```
   ⓘ "인테이크 검토 기능이 비활성화되어 있습니다."
   ```

---

## 연결 파일

| 파일 | 역할 | 주요 내용 |
|------|------|----------|
| `src/app/(dashboard)/admin/intake/page.tsx` | 페이지 (Client Component) | 상태 관리, UI 렌더링, 다이얼로그 |
| `src/hooks/use-intake.ts` | TanStack Query 훅 | `useIntakeList()`, `useAcceptIntake()`, `useRejectIntake()`, `useIntakeServiceKeys()` 등 |
| `clickeye-api/app/api/v1/intake.py` | FastAPI 라우터 | 엔드포인트 정의, 머신/JWT 인증, 기능 토글 |
| `clickeye-api/app/schemas/intake.py` | Pydantic 스키마 | `IntakeCreate`, `IntakeResponse`, `ServiceKeyResponse` 등 |
| `clickeye-api/app/services/intake_service.py` | 비즈니스 로직 | 수주 수용/반려, 프로젝트 생성, 서비스 키 관리 |
| `clickeye-api/app/models/intake.py` | SQLAlchemy 모델 | `Intake`, `IntakeServiceKey` 테이블 |

---

## 구현 노트

### 주요 기능 특이사항
1. **Idempotency-Key**: 외부 서비스의 중복 접수 방지 (POST /intake 헤더 지원)
2. **Input Type 분기**: `structured`/`document`/`url` 타입별로 필수 필드가 다름 (스키마 validator 처리)
3. **정규화 본문**: 접수 시 NLP 파이프라인이 정규화되어 저장 (백엔드 구현)
4. **프로젝트 자동 생성**: 승인 시 `accept_intake()` 함수가 Project 레코드를 생성하고 project_id 저장
5. **평문 키 1회 노출**: 발급 직후만 평문 반환, DB는 SHA256 해시 저장 (이후 조회 불가)
6. **Type-to-Confirm**: 키 비활성화 시 사용자가 키 이름을 입력하도록 강제 (실수 방지)

### 에러 처리
- 404 (FEATURE_INTAKE=false): 안내 배너
- 401/403 (권한 부족): RoleGuard가 페이지 자체 차단
- 네트워크/서버 에러: 적색 배너 + 에러 메시지

### 번역 (i18n)
- 모든 텍스트는 `useTranslations("intake")` / `useTranslations("toast.intake")` 로 외부화
- 키: `pageTitle`, `tabs.*`, `col.*`, `actions.*`, `detail.*`, `acceptDialog.*` 등

### 토스트 알림
- 성공: `toast.success(tT("acceptSuccess"))` 또는 `toast.success(tT("rejectSuccess"))`
- 실패: `toast.error(err.message || tT("acceptFail"))`
- 복사: `toast.success(tT("copySuccess"))`

### 다크모드
- 모든 색상을 CSS 변수 사용 (`--bg-surface`, `--border-subtle`, `--text-primary` 등)
- 상태 배지/버튼은 고정 색상 (emerald, red, amber) 사용하나 배경은 tone-adjust 필요 시 dark: 변형 추가

---

## 파일 구조

```
clickeye-web/src/
├── app/(dashboard)/admin/intake/
│   └── page.tsx                ← 이 페이지 (본문)
├── hooks/
│   └── use-intake.ts           ← TanStack Query 훅 (API 호출 로직)
├── lib/
│   └── api-client.ts           ← 자동 생성 API 클라이언트 (POST, GET, DELETE)

clickeye-api/app/
├── api/v1/
│   └── intake.py               ← FastAPI 라우터
├── schemas/
│   └── intake.py               ← Pydantic 스키마
├── services/
│   └── intake_service.py       ← 비즈니스 로직
└── models/
    └── intake.py               ← SQLAlchemy 모델 (Intake, IntakeServiceKey)
```
