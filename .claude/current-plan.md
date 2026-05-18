## 목표
M4 — Modernize 위저드 진입점 + repo 연결/선택 step + repo 목록 API.
사용자가 M3 의 GitHub App 콜백을 통해 도착한 installation 정보를 바탕으로 repo 를 선택하고
ModernizeSession 시작 직전까지 도달하는 흐름.

## 비침습성 보장
- 기존 `/solutions/new` 위저드 라우트·UI·동작 절대 미변경
- 신규 라우트만 추가: `/solutions/modernize/new`, `/solutions/modernize/connected`
- 사이드바/대시보드 진입점은 `isModernizeEnabled()` flag 조건부 노출 — flag OFF 시 기존 UI 동일
- 기존 store setter / SOLUTION_WIZARD_STEPS export 시그니처 미변경 (M1 의 mode/MODERNIZE_WIZARD_STEPS 위에 modernize sub-state 만 추가)
- Backend: `require_modernize_feature` 가드로 신규 endpoint flag OFF 시 404

## 변경 파일 목록

### Backend (신규)
- `clickeye-api/app/api/v1/modernize.py` — installations / repos endpoint
- `clickeye-api/app/services/modernize/__init__.py` — modernize 서브패키지
- `clickeye-api/app/services/modernize/repo_service.py` — GitHub API 호출 + DB 캐시 (24h TTL)
- `clickeye-api/app/schemas/modernize.py` — InstallationListItem, RepoListItem

### Backend (수정)
- `clickeye-api/app/api/v1/router.py` — modernize_router include
- `clickeye-api/app/services/github_app_service.py` — installation token 으로 repo 목록 조회 helper 추가

### Frontend (신규)
- `clickeye-web/src/lib/api-client.ts` — `modernize` 도메인 export (listInstallations / listRepos / installUrl)
- `clickeye-web/src/components/solutions/wizard/steps/step-modernize-repo-connect.tsx` — install URL → popup
- `clickeye-web/src/components/solutions/wizard/steps/step-modernize-repo-select.tsx` — repo 목록 + 선택
- `clickeye-web/src/app/(dashboard)/solutions/modernize/new/page.tsx` — Modernize 위저드 entry
- `clickeye-web/src/app/(dashboard)/solutions/modernize/connected/page.tsx` — callback redirect 받는 페이지

### Frontend (수정 — 옵트인 분기)
- `clickeye-web/src/stores/solution-wizard-store.ts` — `modernize` sub-state 필드/setter 추가 (기존 미변경)
- `clickeye-web/src/types/solution-wizard.ts` — ModernizeData 타입 추가 (기존 SOLUTION_WIZARD_STEPS 미변경)
- `clickeye-web/src/app/(dashboard)/projects/page.tsx` 또는 사이드바 layout — `isModernizeEnabled()` 조건부 진입 카드/링크 1개 추가 (flag OFF 시 미노출 → 기존 동작)

### 테스트
- `clickeye-api/tests/services/test_modernize_repo_service.py` — repo 캐시 동작 단위 테스트
- `clickeye-web/src/lib/__tests__/api-client.modernize.test.ts` — modernize api client 단위 테스트

## API endpoint 시그니처

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/modernize/installations` | user + flag | `[{id, installation_id, account_login, account_type, repo_count}]` |
| GET | `/modernize/installations/{id}/repos?refresh=false` | user + flag + ownership | `[{full_name, default_branch, language_primary, private, pushed_at}]` |

## 구현 단계
1. backend schemas/modernize.py 작성
2. github_app_service 에 list_repos_with_installation_token helper 추가
3. services/modernize/repo_service.py — 캐시 + GitHub API 호출
4. api/v1/modernize.py — 2 endpoint
5. router 등록
6. backend 단위 테스트
7. frontend api-client modernize 도메인
8. wizard-store modernize sub-state
9. step-modernize-repo-connect.tsx
10. step-modernize-repo-select.tsx
11. solutions/modernize/new/page.tsx
12. solutions/modernize/connected/page.tsx
13. dashboard 진입 카드 (작은 변경)
14. ruff + mypy + vitest

## 회귀 검증
- R-3 OpenAPI diff: 기존 endpoint 미변경, 신규 2 path 만 추가
- R-5 wizard-store snapshot: 기존 setter 동작 동일 + modernize 신규 케이스 추가
- R-6 Feature flag OFF: 신규 라우트/endpoint 모두 404 (require_modernize_feature + frontend `isModernizeEnabled()` 가드)

## STATUS: APPROVED
