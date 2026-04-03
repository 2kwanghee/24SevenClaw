# Multi-Agent 파이프라인 통합 가이드

> 자동화 파이프라인에 **Gemini CLI (기획) + Codex CLI (QA)** 를 통합한 멀티 Agent 워크플로우
> 구현 완료: v6 (2026-04-03)

---

## 1. 아키텍처

```text
Linear (Queued 이슈)
    ↓
linear_watcher.py → fix_plan.md
    ↓
[Gemini CLI] → PLAN.md     (기획: 범위/수용기준/리스크/테스트전략)
    ↓
[Claude CLI] → TASK.md     (구현: 변경파일/구현내용/테스트결과)
    ↓
[Codex CLI]  → REVIEW.md   (QA: 요구충족/리스크/테스트부족/PR코멘트)
    ↓
linear_reporter.py + auto_pr_creator.py
    ↓
PR (PLAN + TASK + REVIEW 포함) → CI → Merge
```

## 2. 문서 기반 상태 관리

각 Agent는 파일을 통해 상태를 전달한다 (API 연동 없음):

```
.ralph/
├─ fix_plan.md    (linear_watcher — 이슈에서 생성)
├─ PLAN.md        (Gemini — 기획서)
├─ TASK.md        (Claude — 구현 결과)
└─ REVIEW.md      (Codex — QA 리뷰)
```

## 3. Agent 권한

| Agent  | 역할 | 코드 수정 | 파일 생성 |
|--------|------|----------|----------|
| Gemini | 기획 | 불가 | PLAN.md |
| Claude | 구현 | 가능 | TASK.md + 소스코드 |
| Codex  | QA   | 불가 | REVIEW.md |

## 4. 모듈 토글

`.env`에서 개별 Agent ON/OFF:

```env
FLOWOPS_GEMINI_PLAN=true     # Gemini 기획 (false: fix_plan을 PLAN.md로 사용)
FLOWOPS_CODEX_REVIEW=true    # Codex QA (false: QA 건너뜀)
```

## 5. 스크립트

| 스크립트 | Agent | 입력 | 출력 |
|----------|-------|------|------|
| `generate_plan_with_gemini.sh` | Gemini | 이슈 제목+설명+fix_plan | `.ralph/PLAN.md` |
| `auto_dev_pipeline.sh` (Claude 단계) | Claude | PROMPT.md (PLAN.md 참조) | `.ralph/TASK.md` + 코드 |
| `run_codex_review.sh` | Codex | PLAN.md + TASK.md + diff | `.ralph/REVIEW.md` |

## 6. PR Body 구조

```markdown
## Linear Issue
- [24S-XX](URL)

## 📌 PLAN (Gemini)
<details> ... PLAN.md 내용 ... </details>

## ⚙️ TASK (Claude)
변경 파일, 구현 내용, 테스트 결과

## 🧪 QA Review (Codex)
<details> ... REVIEW.md 내용 ... </details>

## Fix Plan Result
- [x] 완료 항목들

## Changes / Commits
```

## 7. 폴백 전략

| 실패 상황 | 대응 |
|----------|------|
| Gemini CLI 실패 | fix_plan.md를 PLAN.md로 복사 |
| Codex CLI 실패 | 기본 REVIEW.md 생성 (수동 리뷰 권고) |
| 둘 다 비활성화 | 기존 Claude 단일 파이프라인과 동일하게 동작 |

## 8. 기존 파이프라인과의 호환

- `FLOWOPS_GEMINI_PLAN=false` + `FLOWOPS_CODEX_REVIEW=false` → 기존 v5 동작과 동일
- 기존 스크립트 (linear_watcher, linear_reporter, auto_pr_creator) 모두 유지
- GPT fix_plan (`--use-gpt-plan`)과 Gemini PLAN은 병행 가능 (Gemini가 fix_plan을 입력으로 받음)
