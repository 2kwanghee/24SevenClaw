---
name: log-work
description: 코드 작업 완료 후 즉시 Linear에 작업 로그를 기록한다. 유의미한 코드 변경(기능 구현, 버그 수정, 리팩토링, 테스트 추가, 인프라 변경) 완료 시 자율적으로 호출한다.
disable-model-invocation: false
user-invocable: true
---

완료된 작업을 즉시 Linear에 기록하는 실시간 작업 로거이다.

이 스킬은 유의미한 작업 완료 후 자율적으로 호출해야 한다 — 사용자가 요청할 때까지 기다리지 않는다. 다음 상황에서 자동 호출한다:
- 코드 파일이 생성되거나 크게 수정됨
- 버그가 수정됨
- 기능이 구현됨
- 설정 또는 인프라 변경이 이루어짐
- 리팩토링이 완료됨
- 테스트가 추가되거나 업데이트됨

## Notion DB 속성

이슈 필드 매핑 및 라벨 가이드는 이 스킬 디렉토리의 `linear-reference.md`를 참조한다.

## Workflow

### Step 1: 방금 완료한 작업 요약

현재 대화에서 수행한 작업을 분석한다:
- 어떤 파일을 생성/수정/삭제했는가
- 어떤 문제를 해결했는가
- 어떤 기능을 구현했는가

$ARGUMENTS가 있으면 해당 내용을 포함한다.

### Step 2: 기존 태스크 확인

```bash
python3 scripts/linear_tracker.py list --status "Todo"
python3 scripts/linear_tracker.py list --status "In progress"
```

방금 완료한 작업이 기존 Todo/In progress 태스크에 해당하면 해당 태스크를 Done으로 업데이트한다:

```bash
python3 scripts/linear_tracker.py update \
  --issue-id "이슈ID" \
  --status "Done"
```

### Step 2.5: LoadMap.md 체크리스트 동기화

완료한 작업이 LoadMap.md의 `- [ ]` 항목에 해당하면 `- [x]`로 변경한다.

1. LoadMap.md를 읽고 현재 Phase/Week 섹션에서 관련 항목을 찾는다
2. 완료한 작업과 매칭되는 `- [ ]` 항목을 `- [x]`로 변경한다
3. 매칭 기준: 파일명, 기능명, 또는 태스크 설명이 일치하는 항목
4. LoadMap.md가 없으면 이 단계를 건너뛴다
5. 변경이 있으면 커밋에 포함한다

```
예시:
  완료 작업: "src/commands/init.ts 구현"
  LoadMap.md 매칭: "- [ ] `src/commands/init.ts` — init 명령어 메인 로직"
  변경 후:         "- [x] `src/commands/init.ts` — init 명령어 메인 로직"
```

### Step 3: 작업 로그 등록

Linear만 보더라도 어떤 작업을 왜 수행했고, 무엇이 변경되었으며, 결과가 어떤지 파악할 수 있도록 상세하게 작성한다.
현재 완료한 작업 한 건에 대해서만 기록한다 — 후속 과제나 미래 계획은 포함하지 않는다.

**summary 작성 포맷**:

```markdown
## 배경
왜 이 작업을 수행했는지 (이슈, 요구사항, 문제 상황 등)

## 변경 내역
• 파일명 — 구체적으로 무엇을 변경/생성/삭제했는지
• 파일명 — 변경 내용과 의도
(주요 파일 위주로 나열, 설정 파일 등 부수적 변경도 포함)

## 주요 결정 사항
구현 과정에서 내린 기술적 판단이나 설계 선택 (해당 시)

## 결과
작업 완료 후 상태 (동작 확인 결과, 테스트 통과 여부 등)
```

```bash
python3 scripts/linear_tracker.py log \
  --title "작업 요약 (간결하게)" \
  --summary "## 배경
왜 이 작업을 수행했는지

## 변경 내역
• file1.ts — 변경 내용과 의도
• file2.ts — 변경 내용과 의도

## 주요 결정 사항
기술적 판단/설계 선택 (해당 시, 없으면 생략)

## 결과
동작 확인 결과, 테스트 통과 여부 등" \
  --tags "적절한태그" \
  --date "$(date +%Y-%m-%d)"
```

### Step 4: Telegram 알림 전송

Linear 기록이 완료되면 Telegram으로 결과를 알린다.
메시지는 작업의 출처(프롬프트 or Linear 티켓)와 마크다운 업데이트 내역을 기반으로 구성한다.

**메시지 구성 규칙**:
1. **출처 표시**: 프롬프트 요청인지, Linear 이슈 처리인지 명시
2. **작업 요약**: 무엇을 했는지 1~3줄로 핵심만
3. **마크다운 업데이트**: LoadMap.md 또는 fix_plan.md에서 체크한 항목을 인용
4. **Linear 링크**: 상세 내역 확인용

```bash
# Case 1: 프롬프트 요청으로 작업한 경우
python3 scripts/telegram_notify.py \
  --message "✅ *작업 완료*

📌 *요청*: 사용자가 요청한 내용 요약
🔨 *처리*:
• 핵심 변경사항 1
• 핵심 변경사항 2

📋 *로드맵 업데이트*:
\`LoadMap.md\` ☑ 체크된 항목 내용
또는
\`fix_plan.md\` ☑ 체크된 항목 내용
(업데이트한 마크다운이 없으면 이 섹션 생략)

🔗 Linear: URL"

# Case 2: Linear 이슈를 처리한 경우
python3 scripts/telegram_notify.py \
  --message "✅ *이슈 완료*

🎫 *이슈*: 이슈제목 (이슈ID)
🔨 *처리*:
• 핵심 변경사항 1
• 핵심 변경사항 2

📋 *로드맵 업데이트*:
\`LoadMap.md\` ☑ 체크된 항목 내용
또는
\`fix_plan.md\` ☑ 체크된 항목 내용
(업데이트한 마크다운이 없으면 이 섹션 생략)

🔗 Linear: URL"
```

### Step 5: 간결한 결과 보고

```
> Linear 기록 완료: [작업 제목] | [Linear URL]
> Telegram 알림 전송 완료
```

기존 태스크를 업데이트한 경우:
```
> 태스크 완료 처리: [태스크 제목]
```

## Rules

- 한국어로 작성한다
- 간결하게 — 사용자의 작업 흐름을 방해하지 않는다
- 사소한 변경(오타 수정, 포맷팅)은 기록하지 않는다
- 여러 작업을 한 번에 수행한 경우 하나의 로그로 통합한다
- 커밋 메시지 스타일로 제목을 작성한다 (동사로 시작: 구현, 수정, 추가, 리팩토링 등)

$ARGUMENTS
