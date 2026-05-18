## 목표
M2 — Modernize 파이프라인을 위한 신규 백엔드 모델 5종 + Alembic migration 039 추가.
plan 의 비침습성 원칙에 따라 **기존 테이블 컬럼·인덱스·제약 변경 0**, 모든 변경은 신규 테이블 추가에 한정.

## 변경 파일 목록

### 신규 모델 (5 파일 — 모두 신규)
- `clickeye-api/app/models/github_installation.py` — GitHub App 설치 정보 (installation token 비저장)
- `clickeye-api/app/models/github_repo.py` — 설치된 repo 캐시 (24h TTL)
- `clickeye-api/app/models/modernize_session.py` — 위저드 세션 + 분석 진행률
- `clickeye-api/app/models/codebase_analysis.py` — 정적 분석 + LLM 요약 영속
- `clickeye-api/app/models/modernize_recommendation.py` — 권장안 1:1 = 이슈 1건

### 수정 (모델 등록만)
- `clickeye-api/app/models/__init__.py` — 5 신규 모델 import 등록 (alembic autogenerate 인식)

### 신규 마이그레이션
- `clickeye-api/alembic/versions/039_modernize_tables.py` — 5 신규 테이블 create_table + index, downgrade 시 역순 drop_table

## 모델 시그니처 요약

| 모델 | 핵심 컬럼 | FK |
|---|---|---|
| GitHubInstallation | installation_id (BigInt unique), account_login, account_type, permissions JSON, repository_selection, suspended_at?, revoked_at? | user_id (CASCADE), organization_id (SET NULL) |
| GitHubRepo | gh_repo_id (BigInt), full_name, default_branch, private (Bool), language_primary, pushed_at, cached_at, unique(installation_id, gh_repo_id) | installation_id (CASCADE) |
| ModernizeSession | repo_full_name, repo_branch, commit_sha, scenario, goals_text, target_stack JSON, status, progress_pct, error JSON, extra JSON | user_id (CASCADE), organization_id (SET NULL), installation_id (SET NULL) |
| CodebaseAnalysis | loc_total, file_count, lang_distribution JSON, manifests JSON, outdated_packages JSON, framework_signals, risk_flags, llm_summary_md, tokens_used | session_id (CASCADE, UNIQUE 1:1) |
| ModernizeRecommendation | idx, category, target_path, before/after JSON, title, rationale_md, effort, risk, priority, prompt_md, linear_issue_id?, linear_identifier?, selected | session_id (CASCADE) + Index(session_id, idx) |

모든 모델: UUIDPKMixin + TimestampMixin + Base.

## 구현 단계
1. 5 신규 모델 파일 작성 (기존 패턴 일관 — Column(Uuid, ForeignKey(..., ondelete=...), ...))
2. `__init__.py` 에 import + __all__ 등록
3. Alembic 039 migration 직접 작성 (autogenerate 미사용 — DB 연결 의존 회피)
4. ruff + mypy 통과 확인
5. (가능하면) `alembic upgrade head` → `alembic downgrade -1` → 기존 테이블 변경 0 확인 (R-7)

## 예상 영향 범위
- 기존 테이블 모두 무변경 (R-2 ZIP 골든 미해당, R-5 위저드 store 미해당)
- 신규 테이블 5종만 추가
- `app/models/__init__.py` 의 import 추가만 — 기존 reader 영향 없음
- 신규 테이블은 어떤 기존 코드도 참조하지 않음 (M3 이후 사용)

## STATUS: APPROVED
