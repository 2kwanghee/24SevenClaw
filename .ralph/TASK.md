# 24S-76: 프리셋 카탈로그 DB + 서비스 + API 구현 결과

## 변경 파일 (16개)

### 신규 생성
| 파일 | 역할 |
|------|------|
| `app/models/preset.py` | Preset DB 모델 |
| `app/models/maturity_assessment.py` | MaturityAssessment DB 모델 |
| `app/schemas/preset.py` | Pydantic 요청/응답 스키마 |
| `app/services/preset_service.py` | 프리셋 CRUD + apply + seed 서비스 |
| `app/services/maturity_service.py` | 성숙도 평가 서비스 (가중평균 스코어링) |
| `app/api/v1/presets.py` | 프리셋 엔드포인트 (6개) |
| `alembic/versions/007_add_presets_and_maturity_tables.py` | DB 마이그레이션 |
| `data/presets/starter.json` | Starter 프리셋 시드 데이터 |
| `data/presets/intermediate.json` | Intermediate 프리셋 시드 데이터 |
| `data/presets/advanced.json` | Advanced 프리셋 시드 데이터 |
| `data/presets/maturity_questions.json` | 성숙도 평가 질문지 (10문항) |
| `tests/test_presets.py` | pytest 테스트 (12개 케이스) |

### 수정
| 파일 | 변경 내용 |
|------|----------|
| `app/models/__init__.py` | Preset, MaturityAssessment import 추가 |
| `app/api/v1/router.py` | presets_router include 추가 |

## 구현 내용

### API 엔드포인트
- `GET /api/v1/presets/` — 프리셋 목록 조회 (maturity_level, solution_type 필터)
- `GET /api/v1/presets/questions` — 성숙도 평가 질문지 조회
- `POST /api/v1/presets/assess` — 성숙도 평가 수행 → 점수 + 추천 프리셋
- `GET /api/v1/presets/{id}` — 프리셋 상세 조회
- `POST /api/v1/presets/{id}/apply?project_id=` — 프리셋을 프로젝트에 적용
- `POST /api/v1/presets/seed` — 시스템 프리셋 시드 로드 (관리자 전용)

### 성숙도 평가 로직
- 10개 질문 (team/process/tooling/ci/ai 5개 카테고리)
- 가중 평균 스코어링 (0-100)
- 0-39: starter / 40-69: intermediate / 70-100: advanced
- 평가 결과에 따라 해당 레벨의 시스템 프리셋 자동 추천

## 테스트 결과
- 신규 테스트: 12/12 통과
- 전체 테스트: 292/292 통과
- ruff check: 신규 파일 전체 통과

## 남은 이슈
- `POST /api/v1/projects/{id}/configure-natural` (자연어 → 설정 추천) 엔드포인트는 LLM 연동이 필요하여 이번 범위에서 제외. NaturalLanguageConfigRequest/Response 스키마는 준비됨.
