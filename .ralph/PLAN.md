# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[24S-142/P4] 통합 Composition & Registry Admin UI**
  > 요청사항: ## 작업 내용

* `src/components/admin/pm/composition-panel.tsx` 신규 — 타입별(agent/skill/hook/mcp_server/plugin) composition CRUD + body_md_override markdown-editor
* `src/app/(dashboard)/admin/pm/[id]/composition/page.tsx` 삭제 + redirect → `/admin/pm/[id]`
* `src/hooks/use-pm-admin.ts`: `useUpsertComposition` 뮤테이션 추가
* `src/hooks/use-registry-admin.ts` 신규 — Agent/Skill/MCP CRUD 훅
* `src/components/admin/registry/registry-editor-drawer.tsx` 신규
* `src/components/admin/registry/registry-list-table.tsx` 신규
* `src/app/(dashboard)/admin/registry/agents/page.tsx`, `…/skills/page.tsx`, `…/mcps/page.tsx` 신규
* `src/app/(dashboard)/layout.tsx`: Admin 사이드바에 "Agent 레지스트리", "Skill 레지스트리", "MCP 레지스트리" 링크 추가
* `src/lib/api-client.ts`: registryAdmin + useUpsertComposition 메서드

## 완료 기준

`pnpm lint && pnpm typecheck` 통과 + composition add/edit/delete + registry CRUD 동작 확인

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|