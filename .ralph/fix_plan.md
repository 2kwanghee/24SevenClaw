# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] 프로토타입 세션/프로토타입 모델 구현**
  > 요청사항: SQLAlchemy 모델 신규 작성.

* app/models/prototype_session.py: id, user_id(FK), organization_id(FK), solution_prompt, parsed_requirements(JSON), status, selected_prototype_id, selected_pm_id, current_step, metadata, created_at, updated_at
* app/models/prototype.py: id, session_id(FK CASCADE), variant_index, title, description, design_pattern, menu_structure(JSON), ui_structure(JSON), color_palette(JSON), thumbnail_url, figma_file_key, figma_embed_url, status, created_at, updated_at

models/**init**.py에 등록.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] 프로토타입 세션/프로토타입 모델 구현 | ✅ 완료 | 모델·스키마·서비스·테스트 일괄 업데이트, 337 passed |