# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[24S-142/P3] Web MD 편집 UI (react-markdown 도입)**
  > 요청사항: ## 작업 내용

* `package.json`: `react-markdown ^9`, `remark-gfm ^4`, `gray-matter ^4` 추가
* `src/components/admin/markdown/markdown-editor.tsx` 신규 — split pane (textarea ↔ react-markdown preview)
* `src/components/admin/markdown/collapsible-section.tsx` 신규 — useState+Chevron 핸드롤 패턴 재사용 컴포넌트
* `src/lib/validations/pm.ts` 신규 — RHF + Zod 스키마
* `src/app/(dashboard)/admin/pm/[id]/page.tsx` 전면 리팩터 — raw useState → RHF, 7블록 레이아웃(기본정보/태그/자유서술/MD전체/SKILL/AGENT/기타)
* `src/components/admin/pm/pm-edit-form.tsx` 신규 — 추출 폼 컴포넌트
* `src/components/admin/pm/pm-markdown-pane.tsx` 신규 — 전체 MD 토글 패널
* `src/components/admin/pm/tag-input.tsx` — 기존 inline 추출

## 완료 기준

`pnpm lint && pnpm typecheck` 통과 + PM 편집 화면에서 폼 수정 → MD 실시간 반영 확인

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-17 | 24S-142/P3 Web MD 편집 UI | ✅ 완료 | react-markdown split pane, RHF+Zod, 7블록 레이아웃 |