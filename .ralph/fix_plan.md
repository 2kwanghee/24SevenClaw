# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api/zip] 로컬 실행 팩 — 현대화 에이전트·스킬·룰 ZIP 생성**
  > 요청사항: ## 목표

ZIP 산출물을 "문서 6종"에서 **사용자 로컬에서 즉시 실행 가능한 현대화 팩**으로 격상: `.claude/` 에이전트·스킬·룰을 베이크한다. (R1)

## As-Is 근거

* `zip_builder.py` 산출물: `.clickeye/linear-issues.json`, `.ralph/tasks/*.md`, `docs/diagnosis.{md,json}`, `MODERNIZE_README.md`, `.env.example` 뿐
* `.claude/` 구조·에이전트·스킬·룰·실행 스크립트 전무. README가 안내하는 `auto_dev_pipeline.sh`도 미포함 (`zip_builder.py:13` 주석이 후속으로 미룸)

## 작업 내용

1. ZIP 트리 확장:

```
.claude/
├── agents/  modernize-pm.md, asis-analyzer.md, code-migrator.md,
│            db-migrator.md, test-guardian.md, work-recorder.md
├── skills/  modernize-phase-runner/, migration-verify/, record-work/
└── CLAUDE.md  (현대화 룰: 단계 게이트, 커밋 규칙, 기록지침, 롤백 원칙)
docs/modernize/  requirements.md, tobe-architecture.md,
                 modernization-plan.md, preflight-review.md, plan.json
```

2. 에이전트 파일은 카탈로그 템플릿 + 세션별 산출물(요구사항/계획) 컨텍스트를 렌더링해 생성 (기존 솔루션 ZIP 생성 엔진 패턴 재사용)
3. 멀티 플랫폼 대응: `.claude/` 우선, 기존 위저드의 platform 선택과 동일하게 `.gemini/`/`.cursor/` 변환 훅 자리만 마련
4. 결정성(같은 입력→같은 ZIP) 유지 — 기존 test_zip_builder R-2 원칙

## 완료 조건

* ZIP 압축 해제 → `claude` 실행 → 에이전트/스킬 인식 확인 (수동 E2E 1회 포함)
* zip_builder 단위 테스트 확장 (필수 트리/렌더링/빈 산출물 폴백)

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-07-06 | [api/zip] 로컬 실행 팩 | 완료 | `zip_builder.py`에 `.claude/CLAUDE.md`+6개 agents(YAML frontmatter 포함)+3개 skills(SKILL.md)+`docs/modernize/` 5개 산출물 추가. `phase_artifacts` 파라미터로 `modernize_phase_artifacts` 테이블 데이터를 승인 산출물로 렌더링, 없으면 플레이스홀더 폴백. `platform_id` 훅 자리(`_agent_dir_prefix`)만 마련(현재 `.claude/`만 구현). `/sessions/{id}/zip` 엔드포인트에서 ModernizePhaseArtifact 조회해 전달. 단위 테스트 8건 추가(트리/프론트매터/렌더링/폴백/결정성), 기존 8건 포함 총 37건 통과. 수동 E2E는 실제 `claude` 세션 대신 프로젝트 자체 `.claude/agents`·`.claude/skills` 컨벤션과의 구조 대조로 검증(YAML `name`/`description` 프론트매터 일치 확인) — API 비용 소모 회피. |