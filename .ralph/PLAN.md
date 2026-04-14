# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] 프리셋 카탈로그 DB + 서비스 + API**
  > 요청사항: ## 개요

프리셋 카탈로그 시스템을 API에 구현한다. DB 모델, 서비스, 엔드포인트, 시드 데이터 포함.

## 선행 조건

* [24S-75](https://linear.app/flow-ops/issue/24S-75/contracts-프리셋성숙도-타입-스키마-정의) (프리셋 타입 스키마) 완료 필수

## 범위

### DB 모델

* `models/preset.py`: Preset 테이블 (id, name, slug unique, maturity_level, solution_types JSON, default_agents/skills/pipelines JSON, description, is_system bool, is_active, created_at, updated_at)
* `models/maturity_assessment.py`: MaturityAssessment 테이블 (id, user_id FK, organization_id FK nullable, answers JSON, score int, level str, recommended_preset_id FK nullable, created_at)

### 서비스

* `services/preset_service.py`: CRUD + apply_preset(project_id, preset_id)
* `services/maturity_service.py`: 질문지 로드, 가중평균 스코어링 (0-100 -> 3단계), 프리셋 추천

### 엔드포인트

* GET /api/v1/presets (maturity_level, solution_type 필터)
* GET /api/v1/presets/{id}
* POST /api/v1/presets/{id}/apply (프로젝트에 적용)
* POST /api/v1/projects/{id}/configure-natural (자연어 -> 설정 추천)

### 시드 데이터

* data/presets/starter.json, intermediate.json, advanced.json

### 마이그레이션: 005_add_presets_and_maturity_tables.py

## 완료 조건

- [ ] DB 모델 + 마이그레이션 완료
- [ ] 서비스 로직 + pytest 테스트
- [ ] 엔드포인트 동작 확인
- [ ] 시드 데이터 적용 확인

## 크기: M

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|