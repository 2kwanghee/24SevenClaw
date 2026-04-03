# 작업 정리 — 2026-03-24

## 1. 파이프라인 문제 진단 및 수정

### 문제
- `auto_dev_pipeline.sh` (v4)가 Linear Queued 이슈를 **전부 한꺼번에 In Progress로 변경** 후 tmux 병렬 실행 시도
- 실제로 tmux 세션이 정상 동작하지 않아 **상태만 바뀌고 작업은 안 됨**
- 태스크 간 의존성이 있어 병렬보다 **순차 실행이 적합**

### 해결: v4 → v5 순차 실행 전환
- **`auto_dev_pipeline.sh`**: tmux 병렬 → 동기 순차 실행으로 전면 재작성
  - Queued 이슈 1개 감지 → In Progress → Claude 실행 → 완료 → 결과 보고 → PR → 다음 이슈
  - `--once` 옵션 추가 (1개만 처리 후 종료)
- **`linear_watcher.py`**: `--limit N` 옵션 추가 (기본 0=전체, 1=순차 실행용)

### 정렬 순서 수정
- 기존: priority(긴급도) 기준 정렬
- 변경: **identifier 번호순** (24S-1 → 24S-2 → ... → 24S-10), 동일 번호 내 priority 2차 정렬

---

## 2. 반복 롤백 원인 분석

### 증상
- v5로 수정해도 계속 v4로 되돌아감

### 원인
- v4 파이프라인이 `ralph/24S-*` 브랜치들을 **main 이전 커밋에서 분기**시킴
- 각 브랜치에는 v4만 존재
- `commit-session.sh` Stop Hook이 해당 브랜치에서 `git add -A && commit` → v4 상태 고정
- Claude 세션이 `ralph/24S-*` 브랜치에서 돌고 있었으므로 main의 v5가 적용되지 않음

### 해결
- main으로 체크아웃 후 v5 커밋 확인
- 모든 ralph 브랜치 삭제 (로컬 + 리모트)

---

## 3. commit-session.sh Hook 개선

### 문제
- 기존: 루트 레포에서만 `git add -A` + 커밋
- 하위 모듈(api, web, agent, infra, contracts)은 독립 git → 변경사항이 **어디에도 커밋되지 않고 방치**

### 해결
- 하위 5개 모듈 각각 `git add -A` + 커밋 후 루트 커밋
- 모듈별 scope 자동 설정 (`WIP(api):`, `WIP(infra):` 등)
- 실행 순서: web → api → agent → infra → contracts → 루트

---

## 4. GitHub 레포 구성

### 하위 모듈 독립 레포 생성 (전부 private)
| 레포 | URL |
|---|---|
| 루트 | https://github.com/2kwanghee/24SevenClaw |
| web | https://github.com/2kwanghee/24SevenClaw-web |
| api | https://github.com/2kwanghee/24SevenClaw-api |
| agent | https://github.com/2kwanghee/24SevenClaw-agent |
| infra | https://github.com/2kwanghee/24SevenClaw-infra |
| contracts | https://github.com/2kwanghee/24SevenClaw-contracts |

- 각 하위 폴더에 remote 연결 + initial push 완료
- 루트 remote URL: `24Seven` → `24SevenClaw`로 변경

---

## 5. fix_plan.md PR 충돌 해결

### 문제
- `.ralph/fix_plan.md`가 모든 브랜치에서 수정 → PR 머지 시 충돌
- `.gitignore`에 있지만 **이미 git에 추적 중**이라 무시되지 않음

### 해결
- `git rm --cached .ralph/fix_plan.md` → git 추적 제거
- 이후 `.gitignore`에 의해 자동 무시 → PR 충돌 방지

---

## 6. 브랜치 정리 및 머지

### 머지된 브랜치 (main으로)
| 브랜치 | 내용 |
|---|---|
| ralph/24S-3 | Docker 환경 확인 완료 |
| ralph/24S-5 | Alembic 마이그레이션 설정 |
| ralph/24S-6 | Users 테이블 마이그레이션 |
| ralph/24S-9 | Day 2 마무리 문서 |
| ralph/24S-10 | TODO.md 전 항목 완료 체크 |

### 삭제된 브랜치 (커밋 없음)
- ralph/24S-4, 24S-7, 24S-8

- 로컬 + 리모트 전부 삭제 완료

---

## 변경된 파일 목록

| 파일 | 변경 내용 |
|---|---|
| `scripts/auto_dev_pipeline.sh` | v4 병렬 → v5 순차 실행 |
| `scripts/linear_watcher.py` | `--limit` 옵션 + identifier 번호순 정렬 |
| `.claude/hooks/commit-session.sh` | 하위 모듈 독립 커밋 지원 |
| `.gitignore` | (변경 없음, 이미 fix_plan.md 포함) |
| `.ralph/fix_plan.md` | git 추적 제거 |
