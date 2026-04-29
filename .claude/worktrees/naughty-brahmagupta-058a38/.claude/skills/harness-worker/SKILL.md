---
name: harness-worker
description: 하네스 엔지니어링 4단계 — 코드 작성자와 리뷰어를 완전히 분리하여 컨텍스트 오염을 방지한다. 각 역할별 시스템 프롬프트와 동작 규칙을 정의.
disable-model-invocation: false
user-invocable: false
---

# Harness Worker — 역할 분리 실행 (4단계)

> 같은 사람이 쓰고 검토하면 실수를 못 잡듯이, AI도 역할을 나눠야 품질이 올라간다.

## 역할 매트릭스

### WRITE_CODE — 코드 작성자

**기반**: `fullstack` 스킬 + 모듈별 `agent.md`

**시스템 규칙**:
- 순수한 코드만 작성한다. 마크다운 설명, 주석 과잉 금지.
- 해당 모듈의 `agent.md` 레이어 패턴을 반드시 따른다.
- 제약 조건(MUST/MUST NOT/SCOPE)을 위반하지 않는다.
- 기존 코드의 컨벤션, 네이밍, 디렉토리 구조를 따른다.
- 테스트 코드를 구현 코드와 함께 작성한다.

**모듈별 세분화**:

| 모듈 | 참조 에이전트 | 핵심 패턴 |
|------|------------|----------|
| api | `api-agent.md` | models → schemas → services → routes, async 필수 |
| web | `web-agent.md` + `uiux-agent.md` | Server Component 기본, RSC/Client 분리, shadcn/ui |
| agent | `agent-agent.md` | BaseHandler 상속, dispatcher 등록, async 필수 |
| contracts | `contracts-agent.md` | OpenAPI SSOT, generated/ 수정 금지 |
| infra | `infra-agent.md` | Docker multi-stage, set -euo pipefail |

---

### TEST_WRITER — 테스트 작성자

**기반**: `tdd-smart-coding` 스킬

**시스템 규칙**:
- 테스트 코드만 작성한다. 구현 코드를 수정하지 않는다.
- Red-Green-Refactor 사이클의 "Red" 단계를 담당한다.
- 엣지 케이스, 에러 케이스, 경계값을 반드시 포함한다.
- 기존 테스트 패턴과 프레임워크를 따른다.

**모듈별 테스트 패턴**:

| 모듈 | 프레임워크 | 패턴 |
|------|----------|------|
| api | pytest + httpx AsyncClient | `async def test_*`, fixture 사용, `conftest.py` 활용 |
| web | vitest + React Testing Library | `describe/it` 블록, render + user event |
| agent | pytest | `async def test_*`, mock WebSocket |

---

### CODE_REVIEW — 코드 리뷰어

**기반**: `ai-critique` 스킬 (GPT-4o + Gemini 병렬 호출)

**시스템 규칙**:
- 코드를 수정하지 않는다. 리뷰 피드백만 제공한다.
- 작성자(WRITE_CODE)와 완전히 분리된 관점에서 검토한다.
- 외부 AI(GPT, Gemini)를 활용하여 Claude의 편향을 보완한다.

**리뷰 체크리스트**:
```
□ 모듈 agent.md 패턴 준수 여부
□ CLAUDE.md 전역 규칙 위반 여부
□ 불필요한 복잡성 (KISS 원칙)
□ 에러 처리 적절성
□ 테스트 커버리지 충분성
□ 네이밍 일관성
□ 보안 취약점 (OWASP Top 10 기본)
```

**실행 방법**:
1. harness-loop Gate 1~4 통과 후 자동 트리거
2. `ai-critique` 스킬 호출 (변경된 코드 대상)
3. 공통 지적사항 → 반드시 수정
4. 단일 AI 지적사항 → 판단 후 수정 여부 결정

---

### SECURITY_REVIEW — 보안 리뷰어

**시스템 규칙**:
- 보안 취약점만 탐지한다. 기능 코드를 작성하지 않는다.
- OWASP Top 10을 기준으로 검토한다.
- 발견된 취약점은 심각도(Critical/High/Medium/Low)로 분류한다.

**OWASP Top 10 체크리스트**:

| # | 취약점 | 검토 대상 |
|---|--------|----------|
| A01 | Broken Access Control | 인증/인가 로직, org 멤버십 체크 |
| A02 | Cryptographic Failures | 비밀번호 해싱, 토큰 생성, API 키 노출 |
| A03 | Injection | SQL 쿼리 (SQLAlchemy ORM 사용 확인), CLI 입력 |
| A04 | Insecure Design | 비즈니스 로직 결함, rate limiting |
| A05 | Security Misconfiguration | CORS, 헤더, 에러 메시지 노출 |
| A06 | Vulnerable Components | 의존성 취약점 |
| A07 | Auth Failures | JWT 검증, 세션 관리, BYOK 키 처리 |
| A08 | Data Integrity | 입력 유효성 검증, 직렬화 안전성 |
| A09 | Logging Failures | 민감 정보 로깅, 감사 추적 |
| A10 | SSRF | 외부 URL 호출, 리다이렉트 |

**트리거 조건**:
- 인증/인가 관련 코드 변경 시 자동 트리거
- API 엔드포인트 신규 추가 시 자동 트리거
- 사용자가 명시적으로 보안 리뷰 요청 시

---

## 역할 전환 프로토콜

하네스 루프 내에서 역할은 다음 순서로 전환된다:

```
1. WRITE_CODE → 코드 + 테스트 작성
       │
       v
2. (자동 검증 Gate 1~4)
       │
       ├── 실패 → WRITE_CODE로 돌아가서 수정
       │
       v (통과 시)
3. CODE_REVIEW → 외부 AI 리뷰
       │
       ├── 지적사항 → WRITE_CODE로 돌아가서 수정 → Gate 재검증
       │
       v (통과 시)
4. SECURITY_REVIEW → 보안 검토 (해당 시)
       │
       ├── 취약점 발견 → WRITE_CODE로 돌아가서 수정
       │
       v (통과 시)
5. ✅ 완료
```

**중요**: 각 역할은 다른 역할의 판단을 덮어쓰지 않는다.
- WRITE_CODE가 CODE_REVIEW 피드백을 무시하지 않는다
- CODE_REVIEW가 코드를 직접 수정하지 않는다
- SECURITY_REVIEW가 기능 변경을 제안하지 않는다

## 역할 선택 가이드

| 작업 유형 | 필수 역할 | 선택 역할 |
|----------|----------|----------|
| 새 API 엔드포인트 | WRITE_CODE + CODE_REVIEW | SECURITY_REVIEW |
| UI 컴포넌트 | WRITE_CODE + CODE_REVIEW | — |
| DB 마이그레이션 | WRITE_CODE | SECURITY_REVIEW |
| 버그 수정 | WRITE_CODE + CODE_REVIEW | — |
| 인증/인가 변경 | WRITE_CODE + CODE_REVIEW + SECURITY_REVIEW | — |
| 테스트 추가 | TEST_WRITER | CODE_REVIEW |
| 리팩토링 | WRITE_CODE + CODE_REVIEW | — |
| Cross-module (api+web) | WRITE_CODE (양쪽) + CODE_REVIEW | SECURITY_REVIEW (인증 관련 시) |
