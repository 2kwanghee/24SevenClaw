## 목표

`.claude/MODEL-ROUTING.md` 가이드가 실제 시스템에 wiring되지 않아 ralph 헤드리스 루프가 전부 opus로 동작하는 문제를 해결한다. 진입점·서브에이전트·스킬 3개 레이어에 모델 라우팅을 실제로 적용한다.

## 변경 파일 목록

### 1단계: ralph 헤드리스 진입점 (2개)

- `scripts/auto_dev_pipeline.sh` — `claude -p` 호출(L248)에 `--model sonnet` 추가
- `scripts/ralph-loop.sh` — `claude -p` 호출(L99)에 `--model sonnet` 추가

근거: MODEL-ROUTING.md L92 `ralph-loop = T2 sonnet`.

### 2단계: T3 서브에이전트 프론트매터 (3개)

- `.claude/agents/docs.md` — frontmatter에 `model: haiku` 추가
- `.claude/agents/lint-frontend.md` — frontmatter에 `model: haiku` 추가
- `.claude/agents/lint-python.md` — frontmatter에 `model: haiku` 추가

근거: MODEL-ROUTING.md L42-44.

### 3단계: 스킬 SKILL.md (18개)

MODEL-ROUTING.md L52-100 표 기준으로 매핑:

| 스킬 | 모델 | 근거 라인 |
|------|------|-----------|
| ai-critique | sonnet | L90 |
| daily-close | haiku | L96 |
| endwork | haiku | L96 |
| fullstack | sonnet | L88 |
| harness-context | haiku | L71 |
| harness-loop | sonnet | L72 |
| harness-router | sonnet | L70 |
| harness-worker | sonnet | L73 (역할별 차등이지만 기본 T2) |
| log-work | haiku | L95 |
| manage-skills | haiku | L99 |
| merge-worktree | haiku | L98 |
| prd-to-linear | sonnet | L97 |
| ralph-loop | sonnet | L92 |
| run-pipeline | haiku | L93 |
| setup | haiku | L100 |
| tdd-smart-coding | sonnet | L91 |
| uiux | sonnet | L89 |
| verify-implementation | sonnet | L94 |

총 sonnet 9개 / haiku 9개.

## 구현 단계

1. 1단계: `auto_dev_pipeline.sh`, `ralph-loop.sh` 의 claude 호출 라인 수정
2. 2단계: 3개 에이전트 파일 frontmatter에 `model: haiku` 추가 (frontmatter가 없는 경우 새로 작성)
3. 3단계: 18개 SKILL.md 의 frontmatter에 `model:` 필드 일괄 추가
4. 검증: bash 문법 체크 + frontmatter 형식 확인

## 예상 영향 범위

- **ralph 헤드리스 루프 비용 대폭 감소**: 메인 자율 루프가 opus → sonnet으로 강등, 그 안의 모든 Agent 호출도 부모 모델(sonnet) 상속
- **T3 작업(린트/문서/로그) 추가 절감**: haiku로 강등되어 비용·지연 감소
- **품질 변화 가능성**: opus → sonnet/haiku 강등으로 일부 복잡한 판단의 정확도가 떨어질 수 있음. MODEL-ROUTING.md L195-203의 격상 규칙으로 보안/아키텍처 작업은 자동 격상되도록 설계되어 있어 영향 제한적.
- **부모(메인) Claude Code 세션은 변화 없음**: 변경은 자식 headless ralph와 그 서브에이전트만 영향.
- **롤백 쉬움**: 모든 변경이 추가형(--model 옵션, frontmatter 필드)이라 git revert만으로 원복.

## 검증 방법

1. `bash -n scripts/auto_dev_pipeline.sh scripts/ralph-loop.sh` 문법 통과
2. 변경된 frontmatter들이 `---` 블록 안에 올바른 YAML 형태로 들어갔는지 grep 검증
3. 다음 DayQueued 트리거 시 `logs/claude_*.log` 의 init 라인 `"model"` 필드가 `claude-sonnet-*`인지 확인

## STATUS: APPROVED
