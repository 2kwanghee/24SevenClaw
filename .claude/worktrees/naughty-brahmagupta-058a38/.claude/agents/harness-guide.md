# 하네스 엔지니어링 가이드

> AI가 코드를 작성할 때 `라우팅 → 컨텍스트 제어 → 자동 교정 루프 → 역할 분리` 4단계로 통제하여 환각/오류를 사전 차단하는 개발 워크플로.

## 활성화 방법

하네스 워크플로는 **코드 작성을 수반하는 모든 개발 요청**에 자동 적용된다.
Claude Code가 이 가이드(`harness-guide.md`)를 CLAUDE.md 참조를 통해 인지하고, 개발 요청을 받으면 자동으로 Router 단계부터 시작한다.

- **자동 활성화**: 코드 구현/수정/버그 수정 요청 시
- **비활성화**: 설명/질문/상담 등 코드 작성이 불필요한 요청 시 (Router가 판단)

## 전체 흐름

```
사용자 요청
    │
    v
[0단계: PM Agent / Opus] ─── 세션 시작 & think 시점 호출
    │
    ├─ 복잡도 < 0.7 → 구현 스펙 직접 작성
    └─ 복잡도 ≥ 0.7 → [deep-thinker / Opus] 서브에이전트
            └─ 트레이드오프 분석 → 구현 스펙 확정
    │
    v
[1단계: Router / Sonnet] ─── 의도 분석
    │
    ├─ 모호한 요청 → 소크라테스식 인터뷰 (되물어보기)
    ├─ 명확한 작업 → 제약 조건 추출 → 하네스 루프 진입
    └─ 일반 대화 → 표준 응답 (설명, 질문 답변)
    │
    v
[2단계: Context Manager / Haiku] ─── 필요한 정보만 선별 제공
    │
    ├─ 전역 제약: CLAUDE.md + 현재 Phase 원칙
    ├─ 작업별 로딩: 해당 모듈 agent.md + 관련 파일만
    └─ 가비지 컬렉션: 완료된 작업 코드는 요약 압축
    │
    v
[3단계: Harness Loop / Sonnet] ─── 자동 교정 루프 (MAX 5회)
    │
    ├──→ Worker(WRITE_CODE)가 코드 작성
    ├──→ 자동 검증 (lint → typecheck → test)
    ├──→ 통과? → Worker(CODE_REVIEW) 최종 리뷰 → ✅ 완료
    └──→ 실패? → 에러 피드백 → 🔄 루프 재진입
              └──→ MAX 초과 → 🚨 PM Agent 재호출 (블로킹 이슈 판단)
    │
    v
[4단계: Worker / 역할별 모델] ─── 역할 분리
    │
    ├─ WRITE_CODE: fullstack + 모듈별 agent.md 규칙  [Sonnet]
    ├─ TEST_WRITER: tdd-smart-coding 방식             [Sonnet]
    ├─ CODE_REVIEW: ai-critique (GPT + Gemini 병렬)  [Sonnet]
    └─ SECURITY_REVIEW: OWASP Top 10 체크리스트      [Opus]
```

## 핵심 원칙

1. **출발 전에 방향 확인**: 모호한 요청은 코드 작성 전에 반드시 되물어본다
2. **가림막 원칙**: AI에게 전체 코드베이스가 아니라, 지금 작업에 필요한 파일만 보여준다
3. **자동 교정**: 테스트를 통과하기 전까지 코드를 사용자에게 전달하지 않는다
4. **역할 분리**: 코드를 쓰는 AI와 검토하는 AI를 분리하여 컨텍스트 오염을 방지한다

## 하네스 스킬 참조

| 단계 | 스킬/에이전트 | 모델 | 설명 |
|------|-------------|------|------|
| 0 | `pm-agent` | **opus** | 세션 기획 + 구현 스펙 생성 |
| 0↳ | `deep-thinker` | **opus** | 복잡한 설계/트레이드오프 분석 (pm-agent가 호출) |
| 1 | `/harness-router` | sonnet | 의도 분석 + 라우팅 |
| 2 | `/harness-context` | haiku | 컨텍스트 로딩 프로토콜 |
| 3 | `/harness-loop` | sonnet | 자동 교정 루프 |
| 4 | `/harness-worker` | 역할별 | 역할 분리 실행 |

## 기존 인프라 연동

- `ralph-loop` → 하네스 루프의 자율 반복 메커니즘 (fix_plan.md, stop-hook)
- `tdd-smart-coding` → TEST_WRITER 역할의 Red-Green-Refactor 사이클
- `ai-critique` → CODE_REVIEW 역할의 외부 AI 리뷰 (GPT + Gemini)
- `fullstack` → WRITE_CODE 역할의 시니어 엔지니어 페르소나
- `dev-skills.md/run-tests` → 모듈별 자동 검증 명령어
- `load-recent-changes.sh` → 세션 시작 시 컨텍스트 주입

## 언제 하네스를 적용하는가

| 상황 | 적용 여부 | 이유 |
|------|----------|------|
| 새 API 엔드포인트 구현 | ✅ | 명확한 작업 → 하네스 루프 |
| "성능 좀 개선해줘" | ⚠️ Router → 인터뷰 | 모호 → 구체화 후 루프 |
| "이 함수 설명해줘" | ❌ | 일반 대화 → 표준 응답 |
| DB 마이그레이션 | ✅ | 명확한 작업 → 하네스 루프 |
| 버그 수정 | ✅ | 명확한 작업 → 하네스 루프 |
| 아키텍처 상담 | ❌ | 일반 대화 → 표준 응답 |
| "로그인 만들어줘" | ⚠️ Router → 인터뷰 | 모호 → 어떤 인증? OAuth? JWT? |
