# MODEL-ROUTING.md - 모델 라우팅 가이드

> 에이전트/스킬별 최적 모델을 지정하여 토큰 비용을 최소화한다.
> 원칙: **복잡도에 맞는 모델을 사용하고, 과도한 모델 사용을 피한다.**

---

## 모델 티어 정의

| 티어 | 모델 | 토큰 비용 | 적합한 작업 |
|------|------|-----------|-------------|
| **T1** | `opus` | 최고 | 아키텍처 설계, 복잡한 디버깅, 보안 감사, 시스템 리팩토링 |
| **T2** | `sonnet` | 중간 | 기능 구현, 코드 리뷰, 테스트 작성, 일반 개발 작업 |
| **T3** | `haiku` | 최저 | 린트, 포맷팅, 단순 검색, 로그 기록, 반복 작업 |

### 선택 기준
```
복잡도 높음 (설계 판단, 다중 모듈, 보안) → T1 opus
복잡도 중간 (단일 기능 구현, 리뷰, 테스트) → T2 sonnet
복잡도 낮음 (기계적 반복, 검색, 검증)     → T3 haiku
```

---

## 에이전트별 모델 배정

### 개발 에이전트

| 에이전트 | 기본 모델 | 격상 조건 | 근거 |
|----------|-----------|-----------|------|
| `web-agent` | **T2** sonnet | 아키텍처 변경 시 → T1 | 대부분 컴포넌트/페이지 구현 |
| `api-agent` | **T2** sonnet | 인증/보안 로직 → T1 | API 엔드포인트 구현 |
| `agent-agent` | **T1** opus | — | 프로토콜 설계, 분산 시스템 로직 |
| `infra-agent` | **T2** sonnet | 프로덕션 배포 → T1 | Docker/CI 설정 |
| `contracts-agent` | **T2** sonnet | 브레이킹 체인지 → T1 | 스키마/타입 정의 |
| `uiux-agent` | **T2** sonnet | — | Figma → 코드 변환 |

### 품질/도구 에이전트

| 에이전트 | 기본 모델 | 근거 |
|----------|-----------|------|
| `docs` | **T3** haiku | 문서 작성은 기계적 작업 |
| `lint-frontend` | **T3** haiku | ESLint/tsc 실행 + 결과 정리 |
| `lint-python` | **T3** haiku | ruff/mypy 실행 + 결과 정리 |
| `code-reviewer` | **T2** sonnet | 코드 품질 판단 필요 |

---

## 스킬별 모델 배정

### 개발 워크플로 스킬 (dev-skills.md)

| # | 스킬 | 모델 | 근거 |
|---|------|------|------|
| 1 | `setup-module` | **T3** haiku | scaffolding 템플릿 실행 |
| 2 | `api-endpoint` | **T2** sonnet | 비즈니스 로직 구현 포함 |
| 3 | `ui-page` | **T2** sonnet | 컴포넌트 구현 포함 |
| 4 | `agent-handler` | **T1** opus | 프로토콜 + 분산 로직 |
| 5 | `db-migration` | **T2** sonnet | 스키마 설계 판단 필요 |
| 6 | `contract-sync` | **T3** haiku | 기계적 동기화 작업 |
| 7 | `run-tests` | **T3** haiku | 테스트 명령 실행 + 결과 수집 |
| 8 | `docker-env` | **T3** haiku | Docker 명령 실행 |
| 9 | `pre-commit-check` | **T3** haiku | 린트/타입체크 실행 |
| 10 | `kickoff-day` | **T3** haiku | 상태 확인 + 태스크 정리 |

### 하네스 엔지니어링 스킬

| 스킬 | 모델 | 근거 |
|------|------|------|
| `harness-router` (H1) | **T2** sonnet | 의도 분석 + 라우팅 판단 |
| `harness-context` (H2) | **T3** haiku | 파일 필터링 + 컨텍스트 조립 |
| `harness-loop` (H3) | **T2** sonnet | 오류 진단 + 수정 방향 판단 |
| `harness-worker` (H4) | 역할별 차등 | 아래 참조 |

#### harness-worker 역할별 모델

| 역할 | 모델 | 근거 |
|------|------|------|
| `WRITE_CODE` | **T2** sonnet | 기능 구현 (복잡하면 T1 격상) |
| `TEST_WRITER` | **T2** sonnet | 테스트 설계 판단 필요 |
| `CODE_REVIEW` | **T2** sonnet | 코드 품질 분석 |
| `SECURITY_REVIEW` | **T1** opus | 보안 취약점 분석은 최고 정확도 필요 |

### Flow-Ops 스킬

| 스킬 | 모델 | 근거 |
|------|------|------|
| `fullstack` | **T2** sonnet | 풀스택 구현 (설계 포함 시 T1) |
| `uiux` | **T2** sonnet | 디자인 → 코드 변환 |
| `ai-critique` | **T2** sonnet | 코드 비평 + 개선안 |
| `tdd-smart-coding` | **T2** sonnet | Red-Green-Refactor 사이클 |
| `ralph-loop` | **T2** sonnet | 반복 작업 오케스트레이션 |
| `run-pipeline` | **T3** haiku | 파이프라인 실행 + 결과 수집 |
| `verify-implementation` | **T2** sonnet | 구현 검증 판단 |
| `log-work` | **T3** haiku | Linear에 로그 기록 |
| `endwork` / `daily-close` | **T3** haiku | TODO 아카이브 + 초기화 |
| `prd-to-linear` | **T2** sonnet | PRD 분석 + 태스크 분리 |
| `merge-worktree` | **T3** haiku | git 워크트리 병합 |
| `manage-skills` | **T3** haiku | 스킬 메타 관리 |
| `setup` | **T3** haiku | 환경 설정 |

---

## SuperClaude 페르소나별 모델 배정

| 페르소나 | 기본 모델 | 격상 조건 |
|----------|-----------|-----------|
| `architect` | **T1** opus | — (항상 T1) |
| `security` | **T1** opus | — (항상 T1) |
| `analyzer` | **T2** sonnet | `--ultrathink` 시 → T1 |
| `backend` | **T2** sonnet | 아키텍처 설계 → T1 |
| `frontend` | **T2** sonnet | — |
| `performance` | **T2** sonnet | 시스템 전체 최적화 → T1 |
| `qa` | **T2** sonnet | — |
| `refactorer` | **T2** sonnet | 대규모 리팩토링 → T1 |
| `devops` | **T2** sonnet | 프로덕션 인프라 → T1 |
| `mentor` | **T2** sonnet | — |
| `scribe` | **T3** haiku | 기술 문서 작성 → T2 |

---

## SuperClaude 명령별 모델 배정

| 명령 | 기본 모델 | 격상 조건 |
|------|-----------|-----------|
| `/analyze` | **T2** sonnet | `--think-hard`, `--ultrathink` → T1 |
| `/build` | **T2** sonnet | 신규 아키텍처 → T1 |
| `/implement` | **T2** sonnet | 복잡도 >0.8 → T1 |
| `/improve` | **T2** sonnet | 시스템 전체 → T1 |
| `/design` | **T1** opus | — (설계는 항상 T1) |
| `/task` | **T2** sonnet | — |
| `/test` | **T2** sonnet | — |
| `/troubleshoot` | **T2** sonnet | `--think-hard` → T1 |
| `/explain` | **T2** sonnet | — |
| `/cleanup` | **T2** sonnet | — |
| `/document` | **T3** haiku | 기술 심화 문서 → T2 |
| `/estimate` | **T2** sonnet | — |
| `/git` | **T3** haiku | — |
| `/index` | **T3** haiku | — |
| `/load` | **T3** haiku | — |
| `/spawn` | **T2** sonnet | 하위 에이전트는 각자 모델 적용 |

---

## PM + Deep Thinker 파이프라인

> **핵심 원칙**: Opus는 계획/설계에만 — 구현은 Sonnet이 담당

```
개발 요청
  → [pm-agent / Opus]   : 복잡도 판단 + 구현 스펙 생성
      → [deep-thinker / Opus] : 복잡도 ≥ 0.7 시에만 호출 (트레이드오프 분석)
  → [harness-router / Sonnet] : 구현 스펙 기반 라우팅
  → [harness-loop / Sonnet]   : 실제 코드 작성
  → [lint / Haiku]            : 자동 검증
```

| 에이전트 | 모델 | 호출 시점 | 출력 |
|----------|------|----------|------|
| `pm-agent` | **T1** opus | 세션 시작, `--think` 플래그, 블로킹 이슈 | 구현 스펙 |
| `deep-thinker` | **T1** opus | pm-agent에서 복잡도 ≥ 0.7 감지 시 | 트레이드오프 분석 + 결정 |

### 비용 절감 메커니즘

```
Before (opus로 전체 처리):
  설계(opus) + 구현(opus) + 테스트(opus) + 린트(opus)
  → opus 4회

After (PM 파이프라인):
  pm-agent(opus 1회) → harness-loop(sonnet) → lint(haiku)
  → opus 1회 / sonnet N회 / haiku M회
  예상 비용 절감: ~50-70%
```

---

## 서브에이전트(Agent tool) 모델 배정

| subagent_type | 기본 모델 | 근거 |
|---------------|-----------|------|
| `pm-agent` | **T1** opus | 개발 세션 기획 + 복잡도 판단 |
| `deep-thinker` | **T1** opus | 아키텍처/트레이드오프 심층 분석 |
| `Explore` | **T3** haiku | 파일 탐색 + 코드 검색 |
| `Plan` | **T2** sonnet | 구현 계획 수립 |
| `code-reviewer` | **T2** sonnet | 코드 품질 판단 |
| `docs` | **T3** haiku | 문서 작업 |
| `lint-frontend` | **T3** haiku | 린트 실행 |
| `lint-python` | **T3** haiku | 린트 실행 |
| `general-purpose` | **T2** sonnet | 복잡도에 따라 T1 격상 |
| `codex:codex-rescue` | **T2** sonnet | 진단 + 구현 |

---

## 격상/격하 규칙

### T2 → T1 격상 조건 (하나라도 해당 시)
- 보안 관련 로직 (인증, 권한, 암호화)
- 아키텍처 설계 또는 변경
- 3개 이상 모듈에 걸친 변경
- `--think-hard` 또는 `--ultrathink` 플래그
- 프로덕션 배포/인프라 변경
- 프로토콜/계약 브레이킹 체인지

### T2 → T3 격하 조건 (모두 해당 시)
- 단일 파일 변경
- 패턴이 명확한 반복 작업
- 판단이 필요 없는 기계적 실행
- 이전 작업의 결과를 그대로 적용

### T3 → T2 격상 조건 (하나라도 해당 시)
- 실행 결과에서 예상 외 오류 발생
- 사용자가 판단/분석을 요청
- 결과물에 대한 품질 판단 필요

---

## 비용 최적화 예시

### Before (모든 작업에 opus 사용)
```
API 엔드포인트 추가 작업:
  harness-router  → opus  (과잉)
  harness-context → opus  (과잉)
  harness-loop    → opus  (적정)
  WRITE_CODE      → opus  (적정~과잉)
  TEST_WRITER     → opus  (과잉)
  CODE_REVIEW     → opus  (과잉)
  lint-python     → opus  (과잉)
  log-work        → opus  (과잉)
  ─────────────────────────
  총 8회 opus 호출
```

### After (모델 라우팅 적용)
```
API 엔드포인트 추가 작업:
  harness-router  → sonnet (T2) 의도 분석
  harness-context → haiku  (T3) 파일 필터링
  harness-loop    → sonnet (T2) 오류 진단
  WRITE_CODE      → sonnet (T2) 구현
  TEST_WRITER     → sonnet (T2) 테스트
  CODE_REVIEW     → sonnet (T2) 리뷰
  lint-python     → haiku  (T3) 린트 실행
  log-work        → haiku  (T3) 로그 기록
  ─────────────────────────
  opus 0회 / sonnet 4회 / haiku 3회
  예상 비용 절감: ~60-70%
```

---

## 적용 방법

### 에이전트 파일에 model 프론트매터 추가
```yaml
# .claude/agents/docs.md
---
name: docs
model: haiku
description: 문서 작성 및 업데이트 전문 에이전트
---
```

### Agent tool 호출 시 model 파라미터 지정
```
Agent(subagent_type="Explore", model="haiku", ...)
Agent(subagent_type="code-reviewer", model="sonnet", ...)
Agent(subagent_type="general-purpose", model="opus", ...)  # 복잡한 설계
```

### 스킬 내부에서 서브에이전트 호출 시
```
# harness-loop에서 lint 서브에이전트 호출
Agent(subagent_type="lint-python", model="haiku", ...)

# harness-worker에서 보안 리뷰 호출  
Agent(subagent_type="code-reviewer", model="opus", ...)  # SECURITY_REVIEW
```

---

## 참고

- 이 가이드는 **권장 사항**이며, 사용자가 명시적으로 모델을 지정하면 그것을 우선한다
- 격상/격하는 자동 판단하되, 불확실하면 한 단계 높은 모델을 사용한다
- 비용 절감보다 **품질 유지가 우선** — 의심스러우면 격상한다
