# Git 워크플로우 가이드 — ClickEye

> 작성일: 2026-04-13
> 목적: 다수의 Linear 태스크를 순차 처리할 때 브랜치 충돌을 방지하고, 사람/Claude의 역할을 명확히 구분

---

## 관련 문서
- `docs/queue-driven-automation.md` — 상태 기반 자동화 설계 상세
- `docs/prompts/queue-driven-git-prompt.md` — 다른 레포 적용용 공통 프롬프트

---

## 1. 현재 워크플로우 요약

```
Linear 이슈 (Wait)
  → 사람이 DayQueued 또는 NightQueued로 이동
  → Claude가 상태에 따라 브랜치 전략 자동 결정
  → ralph/{ticket-id} 브랜치 생성
  → fix_plan.md 기반 자동 개발
  → harness-gate.sh (lint/type/test) 통과 시 커밋
  → 세션 종료 시 commit-session.sh 자동 커밋
  → PR 생성 요청
  → 사람이 머지
  → post-merge.yml이 Linear 이슈 Done 처리
```

---

## 2. 자동 커밋 범위 — 무엇이 어디까지 커밋되는가

### Claude가 자동으로 하는 것

| 시점 | 동작 | 커밋 메시지 형식 |
|------|------|-----------------|
| 코드 작성 완료 시 | 사용자 요청에 의한 명시적 커밋 | `[module] 작업 내용 (ticket-id)` |
| 세션 종료 시 | `commit-session.sh` 자동 커밋 | `WIP(module): 요약` |
| ralph 루프 중 | 반복 작업 중간 커밋 | `WIP(module): 요약` |

### Claude가 자동으로 하지 않는 것

| 동작 | 이유 |
|------|------|
| `git push` | 사용자 명시 요청 필요 |
| `git merge` / `git rebase` | 충돌 위험 — 사용자 확인 필요 |
| PR 머지 | GitHub에서 사람이 수행 |
| `git push --force` | 안전 규칙상 금지 |
| 브랜치 삭제 | 사용자 명시 요청 필요 |

---

## 3. 충돌이 발생하는 이유

### 순차 작업 시 브랜치 분기 문제

```
main ─────────────────────────────────────────────
  │
  ├── ralph/24S-71 (contracts 작업)
  │     └── 커밋 A, B, C
  │
  ├── ralph/24S-73 (api RBAC 작업)  ← main에서 분기 (71 미반영)
  │     └── 커밋 D, E, F
  │
  └── ralph/24S-76 (api 프리셋 작업) ← main에서 분기 (71, 73 미반영)
        └── 커밋 G, H, I
```

**문제:** 각 브랜치가 main에서 분기하므로, 이전 브랜치의 변경이 반영되지 않은 상태에서 작업. 동일 파일(예: `protocol.py`, `dependencies.py`)을 여러 브랜치에서 수정하면 머지 시 충돌 발생.

### 충돌 고위험 파일

| 파일 | 이유 |
|------|------|
| `contracts/python/protocol.py` | 모든 기능이 타입을 추가 |
| `contracts/protocol/index.ts` | 모든 기능이 export를 추가 |
| `api/app/dependencies.py` | RBAC + 계약 등 여러 기능이 수정 |
| `api/app/api/v1/router.py` | 새 라우터 등록 시 동시 수정 |
| `api/app/models/__init__.py` | 새 모델 등록 |
| `.ralph/fix_plan.md` | 매 태스크마다 덮어쓰기 |
| `CLAUDE.md`, `TODO.md` | 문서 업데이트 충돌 |

---

## 4. 듀얼 모드 브랜치 전략

상황에 따라 두 가지 모드를 전환하여 사용한다.

### 주간 모드 (Daytime) — 순차 머지 후 분기

> **사용 시점:** 사람이 컴퓨터 앞에 있을 때. 태스크 하나씩 작업 → 머지 → 다음 태스크.

```
main ──┬── ralph/24S-73 ──→ PR ──→ merge ──→ main 업데이트
       │                                        │
       └────────────────────────────────────────┤
                                                │
       main (73 반영) ──┬── ralph/24S-76 ──→ PR ──→ merge
                        │                             │
                        └─────────────────────────────┤
                                                      │
                        main (76 반영) ──── ralph/24S-77
```

**Claude 동작:**
1. `main`에서 최신 pull 후 `ralph/{ticket-id}` 브랜치 생성
2. 코드 작성 + 커밋 + push
3. PR 생성
4. **사람이 머지 확인 후** 다음 태스크로 진행

**핵심 규칙:**
- 다음 태스크 전 반드시 `git checkout main && git pull origin main`
- 충돌 위험: **제로**

---

### 야간 모드 (Overnight) — 체이닝 브랜치

> **사용 시점:** overnight work. Claude가 여러 태스크를 연속 처리하고, 아침에 사람이 순차 머지.

```
                    [Claude 야간 작업]
main ──┬── ralph/24S-73 ──┬── ralph/24S-76 ──┬── ralph/24S-77
       │                  │ (73 기반 분기)    │ (76 기반 분기)
       │                  │                  │
       │                  │                  └── PR #3 (→ main)
       │                  └── PR #2 (→ main)
       └── PR #1 (→ main)

                    [사람 아침 작업]
       PR #1 머지 → PR #2 머지 → PR #3 머지 (순서 필수!)
```

**Claude 동작:**
1. `main`에서 최신 pull 후 첫 브랜치 생성
2. 첫 태스크 완료 + 커밋 + push + PR 생성
3. **현재 브랜치 위에서** 다음 브랜치 분기 (main으로 돌아가지 않음)
4. 두 번째 태스크 완료 + 커밋 + push + PR 생성
5. 반복

**핵심 규칙:**
- 이전 브랜치에서 분기하므로 이전 작업 코드가 반영된 상태로 개발
- PR 타겟은 모두 `main`
- 야간 작업 시작 전 Claude에게 다음과 같이 지시:
  ```
  "overnight 모드로 24S-73, 24S-76, 24S-77 순서대로 작업해.
   체이닝 브랜치로 진행하고, 각 태스크마다 PR 생성해."
  ```

---

### 아침 머지 절차 (Overnight 후)

사람이 출근해서 수행하는 순차 머지 플로우:

```bash
# 1. PR 목록 확인
gh pr list --state open

# 2. 선행 PR부터 순서대로 머지 (순서 필수!)
# GitHub에서:
#   PR #1 (ralph/24S-73 → main) → Merge
#   PR #2 (ralph/24S-76 → main) → Merge  
#   PR #3 (ralph/24S-77 → main) → Merge

# 3. 만약 PR #2에서 충돌이 발생하면:
git checkout ralph/24S-76
git pull origin main          # PR #1 머지 반영
# 충돌 해결 후:
git add . && git commit -m "[module] 머지 충돌 해결"
git push
# → PR #2 다시 머지 가능

# 4. 전부 머지 후 로컬 동기화
git checkout main && git pull origin main

# 5. 머지 완료된 브랜치 정리
git branch --merged main | grep 'ralph/' | xargs git branch -d
git fetch --prune
```

**충돌 발생 확률:**
- 같은 모듈 내 순차 작업: **낮음** (체이닝으로 이전 코드 반영)
- 공유 파일(router.py, index.ts 등): **중간** (양쪽 추가 타입 충돌 → 대부분 단순 병합)
- 다른 모듈 작업: **거의 없음**

---

### 모드 선택 가이드

| 상황 | 모드 | 이유 |
|------|------|------|
| 낮에 컴퓨터 앞에서 작업 | **주간 모드** | 실시간 머지 → 충돌 제로 |
| 밤에 Claude에게 맡기고 퇴근 | **야간 모드 (체이닝)** | 연속 작업 가능, 아침에 순차 머지 |
| 서로 다른 모듈 태스크 동시 실행 | **야간 + 모듈 병렬** | 독립 모듈은 main에서 각각 분기 |
| contracts 포함 태스크 | **어느 모드든 contracts 선행** | SSOT — 반드시 첫 번째로 머지 |

### 야간 모드에서 모듈 병렬 결합

서로 다른 모듈을 수정하는 태스크가 섞여 있으면 **체이닝 + 병렬**을 결합할 수 있다:

```
main ──┬── ralph/24S-73 (api) ──┬── ralph/24S-76 (api)   ← api 체인
       │                        │
       └── ralph/24S-77 (web) ──┬── ralph/24S-84 (web)   ← web 체인 (main에서 독립 분기)
```

- 같은 모듈: 체이닝 (이전 브랜치에서 분기)
- 다른 모듈: main에서 독립 분기 (충돌 없음)
- `contracts/`는 반드시 먼저 머지 (SSOT)

---

## 5. 사람 vs Claude 역할 구분

### Claude가 하는 영역

| 단계 | Claude 동작 | 자동/수동 |
|------|------------|----------|
| 브랜치 생성 | `git checkout -b ralph/{ticket-id}` | 수동 (사용자 요청 시) |
| 코드 작성 | 파일 생성/수정 | 자동 |
| 커밋 | `git add` + `git commit` | 수동 (사용자 요청 시) |
| WIP 커밋 | 세션 종료 시 자동 커밋 | 자동 (commit-session.sh) |
| harness gate | lint/type/test 실행 | 자동 (pre-commit hook) |
| PR 생성 | `gh pr create` | 수동 (사용자 요청 시) |
| Linear 상태 업데이트 | In Progress → Done | 수동 (코드 내에서) |
| fix_plan.md 업데이트 | 항목 체크오프 | 자동 |

### 사람이 하는 영역

| 단계 | 사람 동작 | 이유 |
|------|----------|------|
| PR 리뷰 + 머지 | GitHub에서 Merge 버튼 | 최종 품질 확인은 사람 책임 |
| 충돌 해결 | 머지 충돌 시 수동 해결 | 의도 파악이 필요한 영역 |
| main 보호 | force push 방지 | 안전 규칙 |
| 브랜치 정리 | 머지 완료된 브랜치 삭제 | `git branch -d ralph/24S-XX` |
| 작업 순서 결정 | 어떤 태스크를 먼저 할지 | 비즈니스 우선순위 판단 |
| 머지 전략 선택 | squash / merge commit 선택 | 히스토리 관리 정책 |

### 공동 영역 (소통 필요)

| 상황 | 소통 내용 |
|------|----------|
| 다음 태스크 시작 전 | "main에 이전 PR 머지했어?" 확인 |
| 충돌 발생 시 | Claude가 충돌 파일 리포트 → 사람이 방향 결정 |
| push 전 | Claude가 변경 범위 요약 → 사람이 push 승인 |
| 브랜치 전략 결정 | Claude가 옵션 제시 → 사람이 선택 |

---

## 6. 실전 워크플로우

### 주간 모드 — 사람이 지시하며 작업

```
사람: "24S-73 RBAC API 작업 시작해"

  Claude:
    git checkout main && git pull origin main
    git checkout -b ralph/24S-73
    # ... 코드 작성 + 커밋 ...
    git push -u origin ralph/24S-73
    gh pr create --title "[api] RBAC 모델 + 서비스 + 권한 미들웨어"

사람: GitHub에서 PR 리뷰 → Merge 클릭

사람: "24S-76 프리셋 API 작업 시작해"

  Claude:
    git checkout main && git pull origin main  ← 머지 반영 확인
    git checkout -b ralph/24S-76
    # ... 다음 태스크 ...
```

### 야간 모드 — 퇴근 전 지시, 아침에 머지

**퇴근 전 (사람 → Claude):**
```
"overnight 체이닝 모드로 다음 태스크 순서대로 작업해:
 1. 24S-73 [api] RBAC 모델 + 서비스
 2. 24S-76 [api] 프리셋 카탈로그
 3. 24S-77 [web] 프리셋 UI
 각 태스크마다 커밋 + push + PR 생성해."
```

**Claude 야간 동작:**
```bash
# === 태스크 1 ===
git checkout main && git pull origin main
git checkout -b ralph/24S-73
# ... 작업 + 커밋 + push + PR 생성 ...

# === 태스크 2 (체이닝: 73 위에서 분기) ===
git checkout -b ralph/24S-76          # ← main이 아닌 73에서 분기
# ... 작업 + 커밋 + push + PR 생성 ...

# === 태스크 3 (체이닝: 76 위에서 분기) ===
git checkout -b ralph/24S-77          # ← 76에서 분기
# ... 작업 + 커밋 + push + PR 생성 ...
```

**아침 출근 (사람):**
```bash
# 1. PR 목록 확인
gh pr list --state open

# 2. 순서대로 머지 (선행 PR부터!)
#    PR #1: ralph/24S-73 → main  ← 먼저
#    PR #2: ralph/24S-76 → main  ← 그 다음
#    PR #3: ralph/24S-77 → main  ← 마지막

# 3. PR #2에서 충돌 발생 시:
git checkout ralph/24S-76
git pull origin main              # PR #1 반영
# 충돌 해결 → git add → git commit → git push
# → GitHub에서 PR #2 머지 가능

# 4. 전부 머지 후 정리
git checkout main && git pull origin main
git branch --merged main | grep 'ralph/' | xargs git branch -d
git fetch --prune
```

---

## 7. 충돌 발생 시 대응

### Claude가 할 수 있는 것
```bash
# 충돌 파일 확인
git diff --name-only --diff-filter=U

# 충돌 내용 표시
git diff

# 단순 충돌 (양쪽 추가) — Claude가 해결 가능
# 예: index.ts에 양쪽 모두 export 추가 → 둘 다 포함

# 복잡 충돌 — 사람에게 보고
# 예: 같은 함수의 로직을 양쪽에서 다르게 수정
```

### 사람이 해야 하는 것
```bash
# 1. 충돌 파일 열어서 직접 해결
# 2. 해결 후:
git add <resolved-files>
git commit -m "[module] 머지 충돌 해결"
```

---

## 8. 브랜치 정리 체크리스트

PR 머지 후 사용하는 정리 명령:

```bash
# 머지 완료된 로컬 브랜치 확인
git branch --merged main

# 개별 삭제
git branch -d ralph/24S-71

# 머지 완료된 전체 삭제 (main, HEAD 제외)
git branch --merged main | grep -v 'main\|HEAD\|\*' | xargs git branch -d

# 리모트 추적 브랜치 정리
git fetch --prune
```

---

## 9. 요약 — 한눈에 보기

```
┌──────────────────────────────────────────────────────────┐
│                    듀얼 모드 선택                           │
│                                                          │
│   주간 (Daytime)              야간 (Overnight)            │
│   ┌────────────────┐         ┌────────────────┐          │
│   │ main에서 분기    │         │ 이전 브랜치에서  │          │
│   │ → 작업 → PR     │         │ 체이닝 분기     │          │
│   │ → 머지 확인     │         │ → 각각 PR      │          │
│   │ → main pull    │         │ → 아침에 순차   │          │
│   │ → 다음 태스크    │         │   머지          │          │
│   └────────────────┘         └────────────────┘          │
│   충돌 위험: 제로              충돌 위험: 낮음~중간          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                    사람 영역                               │
│                                                          │
│   주간: 태스크 지시 → PR 리뷰/머지 → 다음 태스크 지시       │
│   야간: 퇴근 전 태스크 목록 지시 → 아침에 순차 머지          │
│   공통: 충돌 해결 (복잡), 브랜치 정리, push 승인             │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                   Claude 영역                             │
│                                                          │
│   주간: main pull → 브랜치 → 코드 → 커밋 → PR             │
│   야간: main pull → 체이닝 분기 → 코드 → 커밋 → PR (반복)  │
│   공통: harness gate, fix_plan, Linear 업데이트, 단순 충돌  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                  핵심 규칙                                 │
│                                                          │
│  1. contracts 변경은 항상 먼저 머지                         │
│  2. 주간: 다음 태스크 전 main pull 필수                     │
│  3. 야간: 같은 모듈은 체이닝, 다른 모듈은 main에서 독립 분기  │
│  4. 아침 머지: 반드시 선행 PR부터 순서대로                   │
│  5. push / merge는 사람 승인 후 실행                       │
└──────────────────────────────────────────────────────────┘
```
