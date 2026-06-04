# 93 테스트 실패 정리 — 레거시 제거 + test-rot 수정 (승인됨)

전체 플랜: `~/.claude/plans/staged-tinkering-lecun.md`. 사용자 ExitPlanMode 승인 완료.

## 목표
초창기 레거시 `/recommend`(dead) 코드+테스트 제거 + test-rot 3종 수정. catalog 시드 픽스처는 deferred(별도 티켓).

## 변경 파일 목록
**W1 — 레거시 recommend 제거 (dead code, 웹·cli 미사용 확인)**
- 삭제: `clickeye-api/app/services/recommend_service.py`, `clickeye-api/app/api/v1/recommend.py`, `clickeye-api/tests/test_recommend.py`
- `clickeye-api/app/api/v1/router.py`: recommend_router import(L29)+include(L56) 제거
- `clickeye-web/src/lib/api-client.ts`: `recommend` export 객체 제거 (+ RecommendRequest/Response 타입 미사용 시)
- `clickeye-api/tests/test_integration.py`: recommend 체인 테스트만 제거

**W2 — test-rot**
- `tests/test_preview.py`: sync→async `generate_preview()` 호출에 await + no_db
- `tests/test_linear_validate.py`: mock `validate_credentials_v2` → `validate_credentials` (+ 반환 tuple[bool,str])
- `tests/test_prototype_sessions.py` + `tests/test_pm_profiles.py`: org 생성 시 `features={"live_preview_enabled": True}` set

## 예상 영향 범위
- 프로덕션 코드 변경 = W1 dead-code 삭제뿐(라이브 동작 불변). 나머지 테스트 전용.
- W1+W2 후 잔여 실패 = deferred catalog-seed 버킷(의도됨, 신규 회귀 0 확인).

## STATUS: APPROVED
