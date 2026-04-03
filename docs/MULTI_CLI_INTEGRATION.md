# Multi-CLI 워크플로우 통합 가이드 (v2)

> 기존 자동화 파이프라인(Claude 기반)에
> **Gemini CLI (기획) + Codex CLI (QA)** 를 통합하는 가이드

기존 문서:

---

## 1. 통합 목표

기존 파이프라인은 **Claude 단일 에이전트 중심 구조**였다.

이를 아래 구조로 확장한다:

```text
Gemini (기획)
    ↓
Claude (구현)
    ↓
Codex (QA)
```

핵심:

> 기존 구조는 유지하고, **Step 사이에 Agent를 삽입**한다.

---

## 2. 변경 포인트 요약

| 구간     | 기존            | 변경                   |
| ------ | ------------- | -------------------- |
| Step 1 | fix_plan 생성   | Gemini PLAN 생성       |
| Step 2 | Claude 구현     | 동일                   |
| Step 3 | Linear report | Codex QA 추가          |
| PR     | fix_plan 기반   | PLAN + TASK + REVIEW |

---

## 3. 전체 아키텍처 (확장)

```text
PRD
 ↓
/prd-to-linear (Claude)
 ↓
Linear (Queued)
 ↓
auto_dev_pipeline.sh
 ↓
[NEW] Gemini → PLAN.md 생성
 ↓
linear_watcher.py
 ↓
Claude → TASK.md 생성
 ↓
[NEW] Codex → REVIEW.md 생성
 ↓
linear_reporter.py
 ↓
PR / Merge
 ↓
CI + AI Review
```

---

## 4. 문서 기반 상태 관리 (핵심)

기존:

```
fix_plan.md
```

변경:

```text
docs/
├─ PLAN.md     (Gemini)
├─ TASK.md     (Claude)
└─ REVIEW.md   (Codex)
```

---

## 5. Step 1 확장 — Gemini PLAN 생성

📍 위치: `linear_watcher.py` 실행 전

---

### scripts/generate_plan_with_gemini.sh

```bash
#!/bin/bash

FEATURE="$1"

mkdir -p docs

gemini <<EOF > docs/PLAN.md
당신은 시니어 PM이다.

요구사항:
$FEATURE

다음을 작성하라:

## 1. 요구사항 요약
## 2. 범위 / 비범위
## 3. 작업 단계
## 4. 수용 기준
## 5. 리스크
## 6. 변경 파일 후보
## 7. 테스트 전략

코드는 작성하지 마라.
EOF
```

---

### linear_watcher.py 변경

기존:

```python
fix_plan 생성
```

변경:

```python
if not exists("docs/PLAN.md"):
    run("generate_plan_with_gemini.sh")

create TASK.md
```

---

## 6. Step 2 — Claude 실행 (강화)

기존 로직 유지:

* 브랜치 생성
* Claude 실행
* 테스트

---

### 추가 규칙

`.ralph/PROMPT.md` 수정:

```md
Read docs/PLAN.md.

Rules:
- PLAN 기준으로만 구현
- TASK.md 반드시 업데이트
- 테스트 수행 필수
```

---

### TASK.md 형식

```md
# TASK

## 변경 파일
## 구현 내용
## 테스트 결과
## 남은 이슈
```

---

## 7. Step 3 확장 — Codex QA (핵심 추가)

📍 위치: Claude 실행 이후 / reporter 이전

---

### scripts/run_codex_review.sh

```bash
#!/bin/bash

codex <<EOF > docs/REVIEW.md
Read docs/PLAN.md and docs/TASK.md.

Review current implementation.

Focus:
- 요구사항 충족 여부
- 회귀 위험
- 테스트 누락
- 보안 문제

코드 수정하지 말 것.

출력:

## 1. 주요 발견
## 2. 요구사항 불일치
## 3. 리스크
## 4. 테스트 부족
## 5. PR 코멘트
EOF
```

---

### auto_dev_pipeline.sh 수정

기존:

```bash
Claude 실행
→ linear_reporter
```

변경:

```bash
Claude 실행
→ TASK.md 생성
→ Codex 실행
→ REVIEW.md 생성
→ linear_reporter
```

---

## 8. Step 4 — PR 생성 개선

📍 auto_pr_creator.py

---

### PR Body 구조 변경

```md
## 📌 PLAN
(PLAN.md)

## ⚙️ 구현 내용
(TASK.md)

## 🧪 QA 결과
(REVIEW.md)
```

---

## 9. CI / AI Review 관계

기존:

* GPT 기반 PR 리뷰

변경:

* Codex → 1차 QA
* GPT → 2차 리뷰

👉 이중 검증 구조

---

## 10. 권한 전략

| 도구     | 권한           |
| ------ | ------------ |
| Gemini | Read-only    |
| Claude | 코드 수정        |
| Codex  | 기본 Read-only |

---

## 11. 실행 흐름 (실제)

### 1. PRD 등록

```
/prd-to-linear
```

---

### 2. 자동 실행

```
Webhook → auto_dev_pipeline.sh
```

---

### 3. 내부 흐름

```text
Gemini → PLAN.md
Claude → TASK.md
Codex → REVIEW.md
```

---

### 4. 결과

* PR 생성
* CI 실행
* Merge
* Linear Done

---

## 12. 기존 기능과의 충돌 없음

| 기능                | 영향    |
| ----------------- | ----- |
| linear_watcher    | 유지    |
| auto_dev_pipeline | 확장    |
| GPT fix_plan      | 대체 가능 |
| AI Review         | 유지    |

---

## 13. 확장 로드맵

* Gemini MCP 연결 (Linear / Notion)
* Codex PR 자동 리뷰
* Claude SubAgent 분리

---

## 14. 핵심 설계 원칙

1. 기존 파이프라인 유지
2. Agent는 단계 사이에 삽입
3. 상태는 문서로 전달

---

## 15. 한 줄 요약

> Claude 혼자 개발하던 구조를
> **Gemini(기획) + Claude(구현) + Codex(QA)** 로 확장한 것

---

## END
