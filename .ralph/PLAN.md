# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [ ] **[24S-142/P2] PM Markdown 직렬화/파싱 API**
  > 요청사항: ## 작업 내용

* `app/services/pm_markdown.py` 신규
  * `serialize_pm_to_markdown(pm, compositions) -> str`: YAML frontmatter + 섹션(소개/운영가이드/구성)
  * `parse_markdown_to_pm(md) -> (PMProfileUpdate, list[PMCompositionUpsert])`: frontmatter + 섹션 파싱
* `app/schemas/pm_profile.py`: `markdown_body`, `PMMarkdownUpsertRequest` 추가
* `app/api/v1/pm_profiles.py`: `GET/PUT /pm-profiles/{id}/markdown` 추가
* `app/services/pm_service.py`: `markdown_body` 저장 경로
* `tests/test_pm_markdown.py` 신규 — 라운드트립 `serialize(parse(serialize(pm))) == serialize(pm)` 포함

## 완료 기준

pytest 통과 + mypy strict 통과

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|