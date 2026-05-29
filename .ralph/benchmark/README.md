# Prompt-Evolve 벤치마크 (동결 케이스)

APE/OPRO 프롬프트 진화의 **적합도(fitness) 평가용 동결 데이터셋**.
`scripts/prompt-evolve-eval.sh` 가 각 케이스를 git worktree에 풀고 후보 프롬프트로 실행한 뒤,
`scripts/ralph-stop-hook.sh` 게이트(테스트+린트+fix_plan 완료)로 PASS/FAIL과 반복 횟수를 측정한다.

## ⚠️ 현재 상태: PLACEHOLDER

`case-001.json` 은 **배관 검증용 자리표시자**다. 스키마/형식은 실제와 동일하지만 내용은 더미다.
**실제 진화 런 전에 반드시 과거 merged Linear 이슈/PR 로 교체**할 것.

### 왜 실제 동결 이슈여야 하나 (과적합 방지)
- 진화는 벤치마크에 맞춰 프롬프트를 최적화한다. 합성/장난감 케이스에 맞추면 실전 성능과 괴리가 생긴다.
- 이미 **머지 완료된 실제 이슈**(정답 PR 존재)를 동결하면, 후보 프롬프트가 그 작업을 얼마나 잘 재현하는지 객관 측정 가능.

## 실제 케이스 동결 방법
1. 난이도/모듈이 다양한 과거 merged Linear 이슈 1~3개 선정 (소형 단위 작업 권장).
2. 각 이슈에 대해 `case-XXX.json` 생성 (아래 스키마):
   - `fix_plan`: 그 이슈를 `.ralph/fix_plan.md` 형식(P1/P2/P3 + `- [ ]`)으로 표현
   - `reference_pr`: 실제 머지된 PR 번호/커밋 (품질 비교 기준)
   - `acceptance`: 통과 판정 기준(테스트/파일/동작)
3. 케이스는 **동결**(이후 변경 금지) — 진화가 케이스를 보고 자기조정하지 못하게.

## 케이스 스키마
```json
{
  "id": "case-001",
  "source_issue": "CE-XXX",
  "title": "이슈 제목",
  "description": "이슈 본문(거친 요구사항)",
  "modules": ["clickeye-api"],
  "fix_plan": "## P1: ...\n- [ ] 항목",
  "acceptance": "통과 판정 기준",
  "reference_pr": "#NN / commit-sha",
  "_placeholder": false
}
```

## 하드캡
- `prompt-evolve-loop.sh` 는 케이스를 최대 `B`개(기본 3) 사용한다. 케이스가 많아도 상한선 적용.
