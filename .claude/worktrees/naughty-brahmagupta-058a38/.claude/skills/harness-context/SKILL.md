---
name: harness-context
description: 하네스 엔지니어링 2단계 — 현재 작업에 필요한 정보만 AI에게 선별 제공한다. 전체 코드베이스를 읽고 정작 중요한 제약을 잊는 것을 방지하는 가림막 역할.
disable-model-invocation: false
user-invocable: false
---

# Harness Context Manager — 컨텍스트 선별 제공 (2단계)

> AI에게 밭 전체가 아니라, **지금 갈아야 할 이랑만** 보여준다.

## 컨텍스트 3계층

### Layer 1: 전역 제약 조건 (항상 고정)

어떤 작업이든 반드시 인지해야 하는 규칙. 컨텍스트에서 절대 제거하지 않는다.

| 소스 | 내용 |
|------|------|
| `CLAUDE.md` | Development Rules, Conventions |
| `LoadMap.md` → 현재 Phase | 핵심 원칙 (예: "기존 코드 보존", "마이그레이션 분리") |
| 금지 사항 | "Cloud에 코드 저장 금지", "contracts 먼저", "sync 코드 금지(api/agent)" |

### Layer 2: 작업별 컨텍스트 (동적 로딩)

현재 작업과 직접 관련된 파일만 로딩한다.

**로딩 프로토콜**:
```
1. 대상 모듈의 agent.md 로딩
   - api 작업 → api-agent.md (레이어 패턴, async 규칙, 테스트 패턴)
   - web 작업 → web-agent.md (컴포넌트 패턴, 상태관리, 스타일링)
   - 프론트 UI 작업 → uiux-agent.md 추가 (접근성, 반응형, 디자인 체크리스트)

2. 작업 대상 파일 + 직접 의존 파일
   - 수정할 파일 읽기
   - 해당 파일이 import하는 모듈 중 핵심만 (1-depth)
   - 관련 테스트 파일

3. 기존 패턴 참조 (유사 코드)
   - 같은 레이어의 기존 구현 1개 참조
   - 예: 새 router 작성 시 → 기존 router 1개를 패턴 참조로 로딩
```

**로딩하지 않는 것**:
- 다른 모듈의 코드 (api 작업 시 web 코드 불필요)
- 완료된 이전 작업의 상세 코드
- 인프라/배포 설정 (인프라 작업이 아닌 경우)
- 문서 전체 (필요한 섹션만)

### Layer 3: 가비지 컬렉션 (자동 정리)

컨텍스트 윈도우가 커지면 자동으로 정리한다.

```
정리 우선순위 (먼저 정리):
1. 이미 커밋된 완료 코드의 상세 내용 → 한 줄 요약으로 대체
2. 탐색용으로 읽었지만 수정하지 않은 파일
3. 에러 메시지 중 이미 해결된 것
4. 이전 하네스 루프의 중간 시도 코드

절대 정리하지 않는 것:
- Layer 1 전역 제약 조건
- 현재 작업의 대상 파일
- 현재 하네스 루프의 에러 트레이스 (미해결)
```

## 모듈별 컨텍스트 매핑

### API 모듈 작업 시

```
필수 로딩 (존재하는 경우):
  - .claude/agents/api-agent.md
  - app/models/ → 관련 모델 (없으면 생성 예정으로 스킵)
  - app/schemas/ → 관련 스키마 (없으면 생성 예정으로 스킵)
  - app/services/ → 관련 서비스 (없으면 생성 예정으로 스킵)
  - app/api/v1/ → 관련 라우터
  - tests/ → 관련 테스트
  - 기존 유사 구현 1개 (패턴 참조, 없으면 agent.md의 예시 참조)

참조 로딩 (필요 시):
  - alembic/versions/ → 마이그레이션 변경 시
  - app/core/deps.py → 의존성 주입 확인 시
  - app/core/auth.py → 인증 관련 작업 시
```

### Web 모듈 작업 시

```
필수 로딩:
  - .claude/agents/web-agent.md
  - .claude/agents/uiux-agent.md (UI 작업 시)
  - src/app/{route}/ → 관련 페이지
  - src/components/{domain}/ → 관련 컴포넌트
  - src/hooks/ → 관련 훅
  - src/types/ → 관련 타입
  - 기존 유사 구현 1개 (패턴 참조)

참조 로딩 (필요 시):
  - src/stores/ → 상태관리 변경 시
  - src/lib/ → 유틸리티 사용 시
```

### Cross-Module 작업 시

```
필수 로딩:
  - .claude/agents/contracts-agent.md
  - contracts 관련 타입 정의
  - API 측 엔드포인트 + Web 측 API 호출 코드
  - CLAUDE.md → "contracts 먼저 업데이트" 규칙 강조
```

## 세션 시작 시 자동 컨텍스트

기존 `.claude/hooks/load-recent-changes.sh`가 주입하는 내용:
- 최근 CHANGELOG 20줄
- 최근 git commit 10개

하네스 추가 컨텍스트:
- TODO.md에서 오늘의 작업 목록
- LoadMap.md에서 현재 Week의 목표

## 컨텍스트 크기 가이드

| 작업 규모 | 목표 컨텍스트 | 포함 범위 |
|----------|-------------|----------|
| 단일 파일 수정 | ~2K 토큰 | 대상 파일 + agent.md |
| 단일 기능 구현 | ~5K 토큰 | 레이어 파일들 + 테스트 + 패턴 참조 |
| Cross-module | ~8K 토큰 | 양쪽 관련 파일 + contracts |
| 대규모 리팩토링 | ~12K 토큰 | 영향 범위 전체 + 의존 관계 |
