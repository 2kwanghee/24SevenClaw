# Queue-Driven 자동화 워크플로우 설계

> Linear 상태값(DayQueued / NightQueued)에 따라 브랜치 전략을 자동 결정하는 시스템

---

## 1. Linear 상태 흐름

```
                   ┌─────────────┐
                   │    Wait     │  ← 기획 완료, 작업 대기
                   └──────┬──────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
   ┌──────────────────┐    ┌──────────────────┐
   │   DayQueued      │    │   NightQueued     │
   │ (주간 자동화 큐)   │    │ (야간 자동화 큐)   │
   └────────┬─────────┘    └────────┬─────────┘
            │                       │
            ▼                       ▼
   ┌──────────────────┐    ┌──────────────────┐
   │   In Progress    │    │   In Progress    │
   │  (주간 모드 실행)  │    │  (야간 모드 실행)  │
   │  전략 A: 순차 분기 │    │  전략 B: 체이닝    │
   └────────┬─────────┘    └────────┬─────────┘
            │                       │
            └───────────┬───────────┘
                        ▼
               ┌──────────────┐
               │   Confirm    │  ← PR 생성 완료, 머지 대기
               └──────┬───────┘
                      ▼
               ┌──────────────┐
               │     Done     │  ← 머지 완료 (post-merge 자동)
               └──────────────┘
```

---

## 2. 상태별 자동 동작

### DayQueued → 주간 모드 (전략 A)

| 단계 | Claude 동작 |
|------|------------|
| 감지 | Linear에서 DayQueued 이슈를 우선순위 순으로 조회 |
| 분기 | `main`에서 최신 pull 후 `ralph/{ticket-id}` 생성 |
| 개발 | 코드 작성 + harness gate 통과 + 커밋 |
| PR | push + PR 생성 |
| 상태 | DayQueued → In Progress → Confirm |
| 대기 | **사람이 PR 머지 확인할 때까지 다음 태스크 진행하지 않음** |
| 반복 | 사람이 "다음" 지시 또는 머지 확인 후 다음 DayQueued 이슈 처리 |

**핵심:** 한 번에 하나. 머지 확인 후 다음 이슈.

### NightQueued → 야간 모드 (전략 B)

| 단계 | Claude 동작 |
|------|------------|
| 감지 | Linear에서 NightQueued 이슈를 우선순위 순으로 전부 조회 |
| 그룹핑 | 같은 모듈 → 체이닝 그룹, 다른 모듈 → 독립 그룹 |
| 첫 분기 | `main`에서 최신 pull 후 첫 브랜치 생성 |
| 개발 | 코드 작성 + harness gate 통과 + 커밋 + push + PR |
| 체이닝 | 다음 이슈를 **현재 브랜치 위에서** 분기 (같은 모듈일 때) |
| 반복 | NightQueued 이슈가 소진될 때까지 연속 처리 |
| 상태 | 각 이슈: NightQueued → In Progress → Confirm |
| 종료 | 모든 이슈 Confirm 상태. 사람이 아침에 순차 머지 |

**핵심:** 멈추지 않고 연속 처리. PR은 각각 생성. 아침에 순차 머지.

---

## 3. 모듈 그룹핑 (야간 모드)

NightQueued 이슈가 여러 모듈에 걸쳐 있을 때:

```
NightQueued 이슈 목록:
  24S-73 [api] RBAC         ← api 모듈
  24S-76 [api] 프리셋        ← api 모듈 (같은 모듈 → 체이닝)
  24S-77 [web] 프리셋 UI     ← web 모듈
  24S-78 [agent] 핸들러      ← agent 모듈

자동 그룹핑 결과:
  체인 1 (api):   24S-73 → 24S-76  (73 위에서 76 분기)
  독립 (web):     24S-77           (main에서 분기)
  독립 (agent):   24S-78           (main에서 분기)

실행 순서:
  1. main에서 ralph/24S-73 분기 → 작업 → PR
  2. ralph/24S-73 위에서 ralph/24S-76 분기 → 작업 → PR
  3. main에서 ralph/24S-77 분기 → 작업 → PR
  4. main에서 ralph/24S-78 분기 → 작업 → PR
```

**그룹핑 규칙:**
- 이슈 제목의 `[module]` 접두사로 모듈 판별
- 같은 모듈 이슈: 우선순위 순으로 체이닝
- 다른 모듈 이슈: main에서 독립 분기
- `[contracts]` 이슈: 항상 최우선 처리 (SSOT)

---

## 4. 아침 머지 순서 (야간 모드 후)

사람이 아침에 처리할 순서:

```
1. contracts PR 먼저 (있으면)
2. 각 체인의 선행 PR부터 순서대로
   - api 체인: 24S-73 → 24S-76
3. 독립 PR은 순서 무관
   - web: 24S-77 (언제든)
   - agent: 24S-78 (언제든)
```

충돌 발생 시:
```bash
git checkout ralph/24S-76
git pull origin main          # 선행 PR(24S-73) 반영
# 충돌 해결 → commit → push
# GitHub에서 PR 머지
```

---

## 5. 상태 전이 규칙

| 현재 상태 | 트리거 | 다음 상태 | 수행자 |
|-----------|--------|-----------|--------|
| Wait | 사람이 큐 배정 | DayQueued 또는 NightQueued | 사람 |
| DayQueued | Claude가 작업 시작 | In Progress | Claude |
| NightQueued | Claude가 작업 시작 | In Progress | Claude |
| In Progress | PR 생성 완료 | Confirm | Claude |
| Confirm | GitHub에서 PR 머지 | Done | post-merge 자동 |
| (어떤 상태든) | 이슈 취소 | Canceled | 사람 |

---

## 6. Claude 감지 로직 (의사코드)

```python
# 주간 모드: 사람이 지시할 때 실행
def process_day_queue():
    issues = linear.list_issues(team="24Seven", state="DayQueued", orderBy="priority")
    
    for issue in issues:
        # 한 번에 하나만
        linear.update(issue.id, state="In Progress")
        
        git.checkout("main")
        git.pull("origin", "main")
        git.checkout_new(f"ralph/{issue.identifier}")
        
        execute_task(issue)
        
        git.commit_and_push()
        gh.pr_create(issue)
        
        linear.update(issue.id, state="Confirm")
        
        # 사람 머지 대기 — 다음 이슈로 넘어가지 않음
        break


# 야간 모드: overnight 지시 시 실행
def process_night_queue():
    issues = linear.list_issues(team="24Seven", state="NightQueued", orderBy="priority")
    
    # 모듈별 그룹핑
    groups = group_by_module(issues)
    
    for module, chain in groups.items():
        is_first = True
        
        for issue in chain:
            linear.update(issue.id, state="In Progress")
            
            if is_first:
                git.checkout("main")
                git.pull("origin", "main")
                is_first = False
            # else: 이전 브랜치 위에서 분기 (체이닝)
            
            git.checkout_new(f"ralph/{issue.identifier}")
            
            execute_task(issue)
            
            git.commit_and_push()
            gh.pr_create(issue)
            
            linear.update(issue.id, state="Confirm")
    
    # 모든 이슈 처리 완료 — 사람이 아침에 머지


def group_by_module(issues):
    """[module] 접두사 기반 그룹핑. contracts 최우선."""
    groups = {}
    for issue in issues:
        module = extract_module(issue.title)  # "[api]" → "api"
        groups.setdefault(module, []).append(issue)
    
    # contracts를 첫 번째로 정렬
    if "contracts" in groups:
        sorted_groups = {"contracts": groups.pop("contracts")}
        sorted_groups.update(groups)
        return sorted_groups
    return groups
```

---

## 7. 적용 범위

이 시스템은 **Linear + Git + Claude Code** 조합을 사용하는 모든 프로젝트에 적용 가능.

### 적용 조건
- Linear 팀에 `DayQueued`, `NightQueued` 상태 추가
- 이슈 제목에 `[module]` 접두사 사용
- Claude Code 또는 호환 AI 에이전트 사용
- GitHub PR 기반 머지 플로우

### 다른 레포 적용 시
- 이 문서를 레포의 `docs/` 또는 `.claude/` 에 복사
- 모듈명을 해당 프로젝트 구조에 맞게 수정
- 아래 "공통 자동화 프롬프트"를 CLAUDE.md 또는 에이전트 파일에 추가
