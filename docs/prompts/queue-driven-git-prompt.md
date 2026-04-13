# Queue-Driven Git 자동화 프롬프트

> 이 프롬프트를 프로젝트의 CLAUDE.md 또는 에이전트 파일에 추가하면
> Linear 상태값 기반 자동 브랜치 전략이 적용된다.
> 프로젝트별 모듈명만 수정하여 재사용 가능.

---

## 프롬프트 (CLAUDE.md 또는 에이전트 파일에 추가)

```markdown
## Queue-Driven Git 자동화 규칙

### Linear 상태 기반 브랜치 전략

이 프로젝트는 Linear 이슈의 상태값에 따라 git 브랜치 전략을 자동으로 결정한다.

#### DayQueued (주간 모드)
- **브랜치 전략:** main에서 분기 → 작업 → PR → 사람 머지 확인 후 다음
- **분기 기준:** 항상 `main` (최신 pull 후)
- **진행 방식:** 한 번에 하나의 이슈만 처리
- **상태 전이:** DayQueued → In Progress → Confirm (PR 생성 후)
- **다음 이슈:** 사람이 PR 머지를 확인하고 지시할 때까지 대기

실행 절차:
1. Linear에서 DayQueued 이슈를 우선순위 순으로 조회
2. 첫 번째 이슈를 In Progress로 변경
3. `git checkout main && git pull origin main`
4. `git checkout -b ralph/{ticket-id}`
5. 코드 작성 + 커밋
6. `git push -u origin ralph/{ticket-id}`
7. `gh pr create` 로 PR 생성
8. 이슈를 Confirm으로 변경
9. 다음 이슈로 넘어가지 않음 — 사람의 머지 확인 대기

#### NightQueued (야간 모드)
- **브랜치 전략:** 체이닝 (같은 모듈은 이전 브랜치에서 분기)
- **분기 기준:** 같은 모듈 → 이전 브랜치, 다른 모듈 → main
- **진행 방식:** 모든 NightQueued 이슈를 연속 처리
- **상태 전이:** NightQueued → In Progress → Confirm (각 이슈마다)
- **다음 이슈:** 멈추지 않고 연속 진행

실행 절차:
1. Linear에서 NightQueued 이슈를 우선순위 순으로 전부 조회
2. 이슈 제목의 [module] 접두사로 모듈별 그룹핑
3. contracts 모듈이 있으면 최우선 처리
4. 각 그룹 내 첫 이슈: `git checkout main && git pull origin main` 후 분기
5. 같은 그룹 후속 이슈: 이전 브랜치 위에서 분기 (체이닝)
6. 각 이슈마다: 코드 작성 → 커밋 → push → PR 생성 → Confirm
7. 모든 이슈 처리 완료까지 연속 실행

#### 모듈 그룹핑 규칙
- 이슈 제목 형식: `[module] 작업 설명`
- 같은 [module] 이슈: 우선순위 순으로 체이닝 (이전 브랜치에서 분기)
- 다른 [module] 이슈: main에서 독립 분기
- [contracts] 이슈: 항상 최우선 처리 (공유 타입의 SSOT)

#### 공통 규칙
- 브랜치명: `ralph/{ticket-id}` (예: ralph/24S-73)
- 커밋 메시지: `[module] 작업 내용 (ticket-id)`
- PR 타겟: 항상 main
- force push 금지
- 사람의 명시적 요청 없이 main에 직접 push 금지
```

---

## 커스텀 가이드

### 다른 프로젝트에 적용할 때 수정할 부분

| 항목 | 현재 값 | 수정 대상 |
|------|---------|----------|
| Linear 팀명 | `24Seven` | 프로젝트 팀명 |
| 브랜치 접두사 | `ralph/` | 프로젝트 관례에 맞게 |
| 모듈 목록 | `api`, `web`, `agent`, `contracts`, `infra` | 프로젝트 모듈 구조 |
| SSOT 모듈 | `contracts` | 공유 타입/스키마 레포 |
| 커밋 메시지 형식 | `[module] 한국어 설명` | 프로젝트 관례 |
| 티켓 접두사 | `24S-` | Linear 팀 접두사 |

### 적용 예시 — 다른 프로젝트

```markdown
## Queue-Driven Git 자동화 규칙

(위 프롬프트 전문을 복사한 뒤 아래 값만 교체)

- Linear 팀: `MyProject`
- 브랜치 접두사: `auto/`
- 모듈: `backend`, `frontend`, `shared`
- SSOT 모듈: `shared`
- 커밋 형식: `[module] description (MP-XX)`
- 티켓 접두사: `MP-`
```

---

## 사람의 아침 루틴 (야간 모드 후)

NightQueued 작업이 완료된 아침에 수행하는 절차:

```bash
# 1. 처리된 이슈 확인
# Linear에서 Confirm 상태 이슈 목록 확인

# 2. PR 목록 확인
gh pr list --state open

# 3. 머지 순서 결정
#    contracts PR → 각 체인의 선행 PR → 독립 PR
#    (GitHub에서 순서대로 Merge 버튼 클릭)

# 4. 충돌 발생 시
git checkout ralph/{충돌-브랜치}
git pull origin main
# 충돌 해결 → git add → git commit → git push
# GitHub에서 PR 재머지

# 5. 전부 머지 후 정리
git checkout main && git pull origin main
git branch --merged main | grep 'ralph/' | xargs git branch -d
git fetch --prune
```

---

## 주간/야간 모드 전환 명령

사람이 Linear에서 이슈 상태를 변경하는 것만으로 모드가 결정된다:

| 사람의 행동 | 결과 |
|------------|------|
| 이슈를 `DayQueued`로 이동 | Claude가 주간 모드로 처리 (순차, 머지 대기) |
| 이슈를 `NightQueued`로 이동 | Claude가 야간 모드로 처리 (체이닝, 연속) |
| 이슈를 `Wait`로 유지 | 아직 큐에 올리지 않은 상태 |

프롬프트 입력 없이 Linear 상태만으로 작업 모드가 결정된다.
