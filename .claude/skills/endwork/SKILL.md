---
name: endwork
description: 하루 마감 시 TODO.md를 docs/daily/YYYYMMDD_Todo.md로 아카이브하고 TODO.md를 초기화한다.
user-invocable: true
---

하루 작업을 마감할 때 사용하는 스킬이다.
TODO.md의 현재 내용을 docs/daily/ 디렉토리에 날짜별로 아카이브하고, TODO.md를 다음 날 작업용으로 초기화한다.

## Workflow

### Step 1: 현재 TODO.md 읽기

TODO.md 파일을 읽어서 오늘의 작업 내용을 파악한다.

**파일 검증**:
- `TODO.md`가 존재하지 않으면: "TODO.md 파일이 없습니다. 먼저 생성해주세요." 안내 후 중단
- `LoadMap.md`가 존재하지 않으면: Step 4(LoadMap 업데이트)를 건너뛴다
- `docs/daily/` 디렉토리가 없으면: 자동 생성 (`mkdir -p docs/daily`)

### Step 2: 아카이브 파일 생성

TODO.md 내용을 `docs/daily/YYYYMMDD_Todo.md` 형식으로 복사한다.
- 날짜는 TODO.md 내에 기록된 날짜를 사용한다 (예: `2026-03-24` → `20260324_Todo.md`)
- TODO.md에 날짜가 없으면 오늘 날짜를 사용한다
- 파일 상단에 아카이브 시각을 추가한다:
  ```
  > 아카이브: YYYY-MM-DD HH:MM
  ```

### Step 3: TODO.md 초기화

TODO.md를 아래 템플릿으로 초기화한다:

```markdown
# 24SevenClaw - Daily TODO

> Claude가 이 파일을 참고하여 순차적으로 개발한다.
> 작업 완료 시 `[x]` 표시. 하루 마감 시 `/endwork` 명령으로 아카이브.

---

## 오늘: YYYY-MM-DD (요일) — Day N: 작업 제목

> LoadMap.md의 일자별 계획을 참고하여 작성할 것.

(다음 작업일의 TODO를 LoadMap.md에서 참조하여 여기에 작성)
```

- 다음 작업일 날짜와 Day 번호는 LoadMap.md의 Phase/Week 계획에서 참조한다
- LoadMap.md가 없으면 날짜만 채우고 작업 제목은 비워둔다

### Step 4: LoadMap.md 업데이트

LoadMap.md에서 오늘 날짜에 해당하는 행의 상태를 `✅`로 변경한다.

### Step 5: Git 커밋

```bash
git add TODO.md docs/daily/
# LoadMap.md가 변경된 경우에만 추가
git diff --quiet LoadMap.md 2>/dev/null || git add LoadMap.md
git commit -m "[docs] Day N 마감: TODO 아카이브 + 다음 작업일 준비"
```

### Step 6: 결과 보고

```
## 마감 완료
- 아카이브: docs/daily/YYYYMMDD_Todo.md
- TODO.md 초기화 완료
- 다음 작업: Day N+1 — {작업 제목}
```

## Rules

- TODO.md가 비어있으면 아카이브하지 않고 사용자에게 알린다
- 이미 같은 날짜의 아카이브가 있으면 `_v2`, `_v3` 접미사를 붙인다
- 한국어로 보고한다
- LoadMap.md의 계획 변경 이력에 기록하지 않는다 (상태 업데이트는 변경이 아님)

$ARGUMENTS
