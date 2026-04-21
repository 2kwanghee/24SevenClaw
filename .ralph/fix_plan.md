# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[rebrand] Phase 5 — 디렉토리 리네임 + CI 업데이트 (HIGH RISK)**
  > 요청사항: 6개 서브모듈 디렉토리 리네임 및 CI/스크립트 경로 전면 갱신. 가장 높은 리스크 단계.

범위: 24SevenClaw-{api,web,agent,cli,contracts,infra} → clickeye-{api,web,agent,cli,contracts,infra}.

대상:

* git mv 6개 디렉토리
* .github/workflows/ci.yml (working-directory 6곳, paths-filter 3곳, cache-dependency-path 1곳)
* Dockerfile.\* 빌드 컨텍스트 경로
* scripts/ 7개 하드코딩 경로 (daily_docs.sh, create_detail_page.py, generate_spec_docs.py, run_codex_review.sh, [ralph-stop-hook.sh](<http://ralph-stop-hook.sh>), auto_dev_pipeline.sh, generate_plan_with_gemini.sh)
* .idea/modules.xml + 24SevenClaw.iml 리네임
* engine 템플릿 파일명 24seven-start.md.j2 → clickeye-start.md.j2

의존: CLK-4(24S-183) 완료 후 진행.

⚠️ 완료 후 WSL 세션 재시작 필요 (경로 캐시 제거).

검증: npm run build(web), uv run pytest(api), CI dry-run, 모든 스크립트 경로 해결.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | Phase 5 디렉토리 리네임 | ✅ | 6개 dir 리네임, CI/scripts/infra 경로 갱신. .claude/hooks·settings.json은 sensitive 파일로 수동 업데이트 필요. WSL 재시작 후 clickeye-api/web 접근 정상화 예상 |