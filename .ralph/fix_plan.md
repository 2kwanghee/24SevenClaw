# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[PM Admin] MD↔UI 양방향 편집 + 통합 Composition/Registry 관리 + 환경 배포 자동화**
  > 요청사항: ## 목표

PM 관리 시스템(Phase 1-6 완료) 위에 **서비스 자산 수준의 PM Admin**을 구축한다.

### 핵심 기능

1. **MD ↔ UI 양방향 편집** — 설정 폼 값이 하단 Markdown(YAML frontmatter + 본문)으로 실시간 렌더링. 반대로 MD 직접 수정 시 폼 + DB 반영.
2. **통합 SubAgent/Skill 관리** — PM 편집 화면 하단 SKILL·AGENT 토글 패널에서 composition CRUD + 각 구성요소 Markdown body 인라인 편집.
3. **환경 배포 자동화** — PM 선택 시 ZIP 생성에서 플랫폼별 `.claude/pm/{slug}.md`, `.gemini/pm/{slug}.md`, `.cursor/rules/pm-{slug}.md`, `.codex/pm/{slug}.py` 자동 주입.
4. **Registry Admin CRUD** — Agent/Skill/MCPServer 모델에 `body_md` 추가 + Admin UI 제공.

### 구현 Phase (각 Phase별 하위 이슈 참조)

* Phase 1: DB migration 013 + Registry Admin API
* Phase 2: PM Markdown 직렬화/파싱 API
* Phase 3: Web MD 편집 UI (react-markdown 도입)
* Phase 4: 통합 Composition & Registry Admin UI
* Phase 5: ZIP 엔진 PM 통합 (4개 플랫폼)
* Phase 6: 문서 + E2E 검증

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-17 | PM Admin MD↔UI 편집 + Registry Admin + ZIP PM 통합 (Phase 1-6) | ✅ | 367/367 테스트 통과 |