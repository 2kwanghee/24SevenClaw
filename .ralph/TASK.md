# Ralph Loop — 구현 결과

## [api] ZIP 생성 API (스트리밍 + .env 포함)

### 변경 파일
| 파일 | 변경 | 설명 |
|------|------|------|
| `app/schemas/generate.py` | 신규 | GenerateRequest 스키마 (PreviewRequest + env_vars) |
| `app/services/generate_service.py` | 신규 | ZIP 생성 서비스 (generate_zip) |
| `app/api/v1/projects.py` | 수정 | POST /{id}/generate 엔드포인트 추가 |
| `tests/test_generate.py` | 신규 | 단위 4개 + API 3개 = 7개 테스트 |

### 구현 내용
- `POST /api/v1/projects/{id}/generate` — 위저드 설정 + envVars 기반 ZIP 스트리밍 다운로드
- 기존 `generate_all` 엔진 재사용, .env/.env.example 파일 추가 패키징
- API 키는 메모리에서만 처리 (DB/로그 기록 없음)
- Content-Type: application/zip, Content-Disposition: attachment

### 테스트 결과
- 전체 78개 테스트 통과 (기존 71 + 신규 7)
- ruff check 통과

### 남은 이슈
- 없음
