import type { InitOptions } from "../types.js";
import type { GeneratedFile } from "./agent.js";
import catalogStacks from "../catalog/stacks.json" with { type: "json" };

/** 선택된 워크플로우에 따른 자동화 스크립트 생성 */
export function generateScriptFiles(options: InitOptions): GeneratedFile[] {
  const workflows = options.workflows?.workflows ?? [];
  if (workflows.length === 0) return [];

  const stack = catalogStacks.find((s) => s.id === options.project.stack);
  const files: GeneratedFile[] = [];

  // ralph-loop 선택 시 fix_plan.md 템플릿 생성
  if (workflows.includes("ralph-loop")) {
    files.push({
      relativePath: ".ralph/fix_plan.md",
      content: `# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(\`- [ ]\`) 항목을 처리한다.
> 완료 시 \`- [x]\`로 표시하고 커밋한다.
> \`- [!]\`는 건너뛴 항목 (사유 기록 필수).

---

## P0: 긴급

## P1: 높음

## P2: 기능 요구사항

- [ ] **첫 번째 태스크를 여기에 작성하세요**
  > 상세 설명

---

## 진행 로그

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
`,
    });
  }

  // tdd 또는 harness-gate 선택 시 run-tests.sh 생성
  if (
    (workflows.includes("tdd") || workflows.includes("harness-gate")) &&
    stack &&
    stack.id !== "custom"
  ) {
    const lines = ["#!/usr/bin/env bash", "# 전체 테스트 실행 스크립트", 'set -euo pipefail', ""];

    if (stack.test.backend) {
      lines.push("echo '🧪 백엔드 테스트...'", stack.test.backend, "");
    }
    if (stack.test.frontend) {
      lines.push("echo '🧪 프론트엔드 테스트...'", stack.test.frontend, "");
    }

    lines.push('echo "✅ 모든 테스트 통과"');

    files.push({
      relativePath: "scripts/run-tests.sh",
      content: lines.join("\n") + "\n",
    });
  }

  return files;
}
