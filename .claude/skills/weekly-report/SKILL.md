---
name: weekly-report
model: sonnet
description: 금주(이번 주 월요일~오늘)에 작업한 git 커밋을 모아 주간보고 마크다운을 docs/WeeklyWorkReport/<주월요일날짜>/weekly-report.md 로 생성한다. "주간보고", "금주 작업 내역", "이번 주 작업 정리", "주간 업무 보고", "weekly report" 등을 요청하면 반드시 이 스킬을 사용한다. 사용자가 명시적으로 "주간보고"라는 단어를 쓰지 않아도 한 주간 작업을 요약/정리해 달라는 맥락이면 이 스킬을 떠올릴 것.
user-invocable: true
---

이번 주에 한 작업을 git 커밋에서 모아 주간보고 문서를 만드는 스킬이다.

핵심 아이디어: **무엇을 했는지의 1차 기록은 git 커밋**이다. 커밋 제목이 보고서의 항목이 되고,
커밋 본문이 그 항목의 세부 내용이 된다. 날짜·주차 계산·수집은 스크립트가 결정론적으로 처리하니,
너는 그 결과를 사람이 읽기 좋게 **큐레이션**하는 데 집중하면 된다.

## Workflow

### Step 1: 데이터 수집

스크립트를 실행해 이번 주 범위·제목·출력 경로·커밋 목록을 한 번에 받는다.

```bash
bash .claude/skills/weekly-report/scripts/collect_week.sh
```

지난 주를 만들려면 `--week-offset 1`(1주 전), `--week-offset 2`(2주 전)처럼 전달한다.
사용자가 "지난주 주간보고"라고 하면 `--week-offset 1`로 실행한다.

스크립트 출력에서 다음을 읽는다:
- `TITLE=` → 보고서 제목 (예: `6월 둘째주 주간보고`). 주차는 주 월요일 기준으로 계산된다.
- `OUTPUT_PATH=` → 보고서를 쓸 경로. **이 경로를 그대로 사용**한다(임의로 바꾸지 말 것).
- `RANGE=` → 집계 기간(월요일 ~ 끝일).
- `COMMIT_COUNT=` → 커밋 수.
- `=== COMMITS ===` 이후 각 커밋 레코드: `DATE`, `SUBJECT_CLEAN`(prefix 정리된 제목),
  `BODY`(본문 불릿), `FILES`(변경 파일).

`COMMIT_COUNT=0`이면 해당 기간 커밋이 없는 것이다. 파일을 만들지 말고
"이번 주(<RANGE>) 커밋이 없어 주간보고를 생성하지 않았습니다"라고 사용자에게 알리고 멈춘다.

### Step 2: 큐레이션

커밋을 보고서 항목으로 다듬는다. 기계적 나열이 아니라, **읽는 사람이 한 주의 성과를
빠르게 파악**할 수 있게 만드는 것이 목적이다.

- **항목 제목**: `SUBJECT_CLEAN`을 사용한다(이미 `WIP(root):`, `[api]`, `feat:` 등 prefix가 제거됨).
  어색하면 자연스럽게 다듬어도 된다.
- **세부 불릿**: `BODY`에서 핵심 1~3개를 고른다. 본문이 길면 가장 의미 있는 변경만 남기고,
  사소한 문서 동기화·포맷팅 같은 줄은 생략한다. 본문이 비어 있으면 `FILES`를 보고
  무엇을 건드렸는지 한 줄로 요약한다.
- **제외**: `update N files`, 단순 오타/포맷 수정처럼 보고 가치가 낮은 기계적 커밋은 건너뛴다.
  같은 작업이 여러 커밋으로 쪼개져 있으면 하나의 항목으로 합쳐도 좋다.
- **순서**: 최신 → 과거 순(스크립트가 주는 순서)을 유지한다.

### Step 3: 보고서 작성

`OUTPUT_PATH`에 아래 템플릿으로 파일을 쓴다(Write 도구가 상위 디렉토리를 자동 생성한다).

ALWAYS 아래 구조를 따른다:

```markdown
제목: {TITLE}

## ClickEye

1. {항목 제목} ({DATE})
- {세부 불릿}
- {세부 불릿}

2. {항목 제목} ({DATE})
- {세부 불릿}
```

규칙:
- 모든 작업을 단일 `## ClickEye` 섹션 아래 번호 리스트로 둔다(모듈별로 쪼개지 않는다).
- 각 항목 제목 끝에 해당 커밋 `DATE`를 `(YYYY-MM-DD)` 형식으로 붙인다.
- 항목 사이에는 빈 줄을 하나 둔다.

### Step 4: 결과 보고

파일을 쓴 뒤 사용자에게 생성 경로와 포함된 항목 수를 한 줄로 알린다.
예: `docs/WeeklyWorkReport/2026-06-08/weekly-report.md 생성 (항목 2개)`

## 완성 예시

스크립트가 준 커밋(메타프롬프트 도입 / linear 게이트)을 다듬으면 이런 결과가 된다:

```markdown
제목: 6월 둘째주 주간보고

## ClickEye

1. 메타프롬프트 관측형 사전 정제를 파이프라인 기획 단계로 도입 (2026-06-11)
- metaprompt 스킬 신규 추가 (.claude/skills/metaprompt/SKILL.md)
- auto_dev_pipeline.sh STEP A: Gemini 기획을 Claude 메타프롬프트 정제로 대체 (멱등성·failsafe·Linear 코멘트·구현 프롬프트 prepend)

2. linear 스킬 선택 시 이슈 기반 개발 게이트 emit (2026-06-11)
- generator.py: linear 선택 시 clickeye-linear-gate.sh(PreToolUse hook)
```
