## 목표
M8 — 비침습성 회귀 검증 R-1~R-7 자동화 + Modernize 단위 테스트 + 회귀 체크리스트 문서화.
MVP-2-A 의 마지막 마일스톤. 신규 기능 추가 X, 검증 인프라 + 문서만 추가.

## 비침습성 보장
- 신규 테스트 파일 / 스크립트 / 문서만 추가
- 기존 vitest/pytest 회귀 케이스는 이미 매 마일스톤마다 통과 입증 (77/77)
- R-1 (브라우저 E2E) 와 R-7 (Alembic) 은 환경 의존이라 자동화 스크립트 + 수동 가이드 병행

## 변경 파일 목록

### Backend 단위 테스트 (신규)
- `tests/services/modernize/test_scan.py` — 확장자 분포 / 50k 파일 cap
- `tests/services/modernize/test_manifest.py` — pyproject/package.json/go.mod 파싱
- `tests/services/modernize/test_recommendations_fallback.py` — Anthropic 미설정 시 deterministic fallback
- `tests/services/modernize/test_zip_builder.py` — ZIP 트리 구조 / 파일 내용 검증
- `tests/services/modernize/__init__.py` — 패키지 초기화

### 자동화 스크립트 (신규)
- `scripts/modernize-check-catalog-unchanged.sh` — R-4 카탈로그 git diff 검사
- `scripts/modernize-check-flag-off.sh` — R-6 Feature flag OFF 동작 검증

### 문서 (신규)
- `docs/modernize-regression-checklist.md` — 매 PR 머지 전 R-1~R-7 체크리스트

## 검증 항목 매핑

| R# | 항목 | M8 자동화 |
|---|---|---|
| R-1 | 기존 위저드 E2E | 수동 가이드 (docs) + dev 서버 fetch 200 확인 스크립트 |
| R-2 | ZIP 골든파일 | pytest 픽스처 — Modernize ZIP 트리 구조 검증 (test_zip_builder) |
| R-3 | OpenAPI diff | 가이드 (openapi-diff 도구 사용법). 기존 endpoint 미변경은 코드 리뷰로 |
| R-4 | 카탈로그 변경 0 | `scripts/modernize-check-catalog-unchanged.sh` — git diff 검사 |
| R-5 | wizard-store snapshot | 이미 vitest 회귀 케이스 통과 (77/77) — 매 마일스톤 검증 완료 |
| R-6 | Feature flag OFF | `scripts/modernize-check-flag-off.sh` — env=false 시 라우트 404 |
| R-7 | Alembic downgrade | M2 실측 완료. 가이드 + 재실행 명령 문서화 |

## 구현 단계
1. Modernize 단위 테스트 4 종
2. R-4 catalog 검사 스크립트
3. R-6 Feature flag OFF 검증 스크립트
4. docs/modernize-regression-checklist.md
5. 모든 테스트 격리 실행 (격리: pytest --no-header tests/services/modernize/)
6. 최종 vitest 회귀 확인 + 마일스톤 마무리 보고

## STATUS: APPROVED
