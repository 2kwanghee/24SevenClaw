# ClickEye - License Model

## 1. 현재 라이센스 정책 (v1)

### 1.1 기본 원칙
- **프로젝트 단위** 라이센스
- 에이전트/스킬/MCP는 프로젝트 라이센스에 포함
- 세부 라이센스 정책은 추후 별도 수립

### 1.2 라이센스 구조

```
프로젝트 라이센스
├── 프로젝트 1개 사용 권한
├── 에이전트 선택/사용 (포함)
├── 스킬 선택/사용 (포함)
├── MCP 서버 선택/사용 (포함)
├── Agent 연결 1개
├── 클라우드 UI 접근
└── 기술 지원 (플랜별 차등)
```

---

## 2. 플랜 구성 (초안)

| 항목 | Free (체험) | Pro | Enterprise |
|------|------------|-----|------------|
| 프로젝트 수 | 1 | 5 | Unlimited |
| Agent 연결 | 1 | 3 | Unlimited |
| 에이전트/스킬/MCP | 기본 세트 | 전체 | 전체 + 커스텀 |
| 동시 티켓 | 1 | 10 | Unlimited |
| 환경 템플릿 | 기본 | 전체 | 전체 + 커스텀 |
| 기술 지원 | 커뮤니티 | 이메일 | 전담 |
| 가격 | 무료 | TBD/월 | TBD/월 |

※ 가격은 시장 검증 후 결정

---

## 3. 라이센스 검증 흐름

### 3.1 발급

```
1. 사용자가 Cloud UI에서 플랜 선택 + 결제
2. Cloud API: 라이센스 키 생성 (license_key)
3. DB에 라이센스 레코드 저장:
   {
     license_id: "lic_xxx",
     user_id: "usr_xxx",
     plan: "pro",
     projects_limit: 5,
     agents_limit: 3,
     valid_from: "2026-03-23",
     valid_until: "2027-03-23",
     status: "active"
   }
4. 사용자에게 license_key 전달
5. Agent 설치 시 license_key 입력
```

### 3.2 검증 흐름

```
[Agent 시작]
     │
     ▼
[Cloud에 WebSocket 연결]
     │
     ▼
[agent.register / 연결 시 라이센스 확인]
     │
     ├── 유효 → 정상 동작
     │
     ├── 만료 → 읽기 전용 모드
     │         (새 환경 생성 불가, 기존 환경 유지)
     │
     └── 없음/비활성 → 연결 거부
```

### 3.3 주기적 검증
- **온라인**: 24시간마다 Cloud에 라이센스 유효성 확인
- **오프라인 허용**: 마지막 검증 후 **72시간** grace period
- **강제 검증**: Cloud에서 push로 즉시 재검증 가능 (플랜 변경, 결제 실패 시)

### 3.4 라이센스 한도 적용

```
프로젝트 생성 시:
  → Cloud API가 현재 프로젝트 수 확인
  → 한도 초과 시 거부 + 업그레이드 안내

Agent 등록 시:
  → Cloud API가 현재 Agent 수 확인
  → 한도 초과 시 거부

티켓 발행 시:
  → 동시 진행 티켓 수 확인
  → 한도 초과 시 큐잉 또는 거부
```

---

## 4. 향후 세부 라이센스 방향 (v2 계획)

### 4.1 가능한 확장 방향

```
옵션 A: 에이전트/스킬 개별 과금
  - 기본 세트는 포함
  - 프리미엄 에이전트/스킬은 별도 과금
  - 마켓플레이스 모델 (수수료)

옵션 B: 사용량 기반 과금
  - 에이전트 실행 시간 기반
  - Claude API 토큰 사용량 기반 (패스스루)
  - 티켓 처리 건수 기반

옵션 C: 기능 기반 과금 (현재 방향)
  - 프로젝트 수 + Agent 수 기반
  - 단순하고 예측 가능한 비용
  - 고객이 선호하는 모델
```

### 4.2 결정 시기
- MVP 출시 후 고객 피드백 기반으로 결정
- Phase 5 (상용화) 단계에서 구체화

---

## 5. 라이센스 키 형식

```
형식: CLK-{plan}-{random}-{checksum}
예시: CLK-PRO-a1b2c3d4e5f6-x9y8

구성:
  - CLK: ClickEye 접두사
  - PRO: 플랜 코드 (FREE, PRO, ENT)
  - a1b2c3d4e5f6: 랜덤 12자리 hex
  - x9y8: CRC16 체크섬 4자리
```

---

## 6. DB 스키마

```sql
CREATE TABLE licenses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    license_key     VARCHAR(50) UNIQUE NOT NULL,
    plan            VARCHAR(20) NOT NULL,          -- free | pro | enterprise
    projects_limit  INTEGER DEFAULT 1,
    agents_limit    INTEGER DEFAULT 1,
    concurrent_tickets_limit INTEGER DEFAULT 1,
    valid_from      TIMESTAMPTZ NOT NULL,
    valid_until     TIMESTAMPTZ,                   -- NULL = 무기한
    status          VARCHAR(20) DEFAULT 'active',  -- active | expired | suspended | cancelled
    stripe_subscription_id VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        VARCHAR(100) UNIQUE NOT NULL,
    license_id      UUID NOT NULL REFERENCES licenses(id),
    agent_secret_hash VARCHAR(255) NOT NULL,
    hostname        VARCHAR(255),
    os_info         VARCHAR(100),
    agent_version   VARCHAR(50),
    capabilities    JSONB DEFAULT '[]',
    status          VARCHAR(20) DEFAULT 'offline', -- online | offline | error
    last_heartbeat  TIMESTAMPTZ,
    registered_at   TIMESTAMPTZ DEFAULT NOW()
);
```
