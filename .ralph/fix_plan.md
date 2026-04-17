# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[24S-142/P5] ZIP 엔진 PM 통합 (4개 플랫폼)**
  > 요청사항: ## 작업 내용

* `app/engine/platforms.py`: `PlatformDirs`에 `pm_dir` 추가, `_build_codex_settings` 분기
* `app/engine/generator.py`: `_generate_pm_files` 신규 writer, composition 우선 병합, codex 분기
* `app/engine/templates/pm/pm-{claude,gemini,cursor}.md.j2`, `pm-codex.py.j2` 신규
* `app/engine/templates/codex.md.j2` 신규(누락분)
* `app/schemas/generate.py`: `pm_profile_id: UUID | None` 추가
* `app/services/generate_service.py`: PM + compositions DB 로드 후 엔진 전달
* `app/api/v1/projects.py`: `wizard_data`에 `pm_profile_id` 영속화
* `tests/test_generate_pm.py` 신규 — 4개 플랫폼별 ZIP 내 파일 존재+내용 검증

## 완료 기준

pytest 통과 + Claude/Gemini/Cursor/Codex 각 ZIP에 PM 파일 주입 확인

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-17 | [24S-142/P5] ZIP 엔진 PM 통합 (4개 플랫폼) | ✅ 완료 | pytest 415/415 통과, ruff+mypy 통과 |