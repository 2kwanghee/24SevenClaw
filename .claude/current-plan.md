## 목표
i18n 작업에서 발생한 Alembic 마이그레이션 충돌(중복 revision `040` + 미적용)을 해소하여 `users.language` 등 누락 컬럼을 DB에 반영하고, 로그인/카탈로그/PM 엔드포인트 500 에러를 복구한다.

## 근본 원인
- `040_user_language.py`와 `040_i18n_catalog_pm.py`가 **동일한 `revision="040"`** → Alembic이 충돌로 거부 → DB가 `039`에 멈춤 → `users.language` 및 `*_en` 컬럼 미생성 → `UndefinedColumnError`
- DB는 이미 `039` + `9f0519f73fcf` 두 head에 적용된 선행 멀티헤드 상태 (서로 다른 테이블이라 공존). 새 040들이 `039`에만 연결되어 적용 시 head 3개 발생.
- `039`, `9f0519f73fcf`는 **이미 적용된** revision → 절대 ID 수정 금지. 두 `040` 파일은 **미적용** → 안전하게 rename 가능.

## 변경 파일 목록
- `clickeye-api/alembic/versions/040_user_language.py` → `041_user_language.py`로 파일명 변경, `revision="041"`, `down_revision="040"`으로 수정
- (`040_i18n_catalog_pm.py`는 `revision="040"` 유지 — 변경 없음)
- `clickeye-api/alembic/versions/0XX_merge_*.py` (신규) — `alembic merge`로 자동 생성. 두 head(`041`, `9f0519f73fcf`)를 단일 head로 병합 (up/down 비어있음, 안전)

## 구현 단계
1. `040_user_language.py`를 `041_user_language.py`로 rename, revision/down_revision을 `041`/`040`으로 수정 (두 040은 서로 다른 테이블이라 순서 무관, 결정적으로 i18n_catalog_pm을 040 유지)
2. `alembic heads`로 head가 `041` + `9f0519f73fcf` 두 개임을 확인
3. `alembic merge -m "i18n 및 organizations 브랜치 통합" heads`로 병합 revision 생성
4. `alembic upgrade head` 실행
5. 검증 (아래 영향 범위 참조)

## 예상 영향 범위
- **DB 스키마 추가만** (컬럼 add). 기존 데이터/컬럼 변경·삭제 없음 → 비파괴적
- 복구 대상: `auth.py`(로그인), `registry`/`catalog`(`*_en` 컬럼), `pm_profile`(`*_en`), `generator.py`(`body_md_en`)
- 검증 항목:
  - `alembic heads` → head 정확히 1개
  - `alembic upgrade head` → 성공 (`heads` 아닌 단수형)
  - `information_schema.columns` 재조회 → `users.language` + `*_en` 컬럼 존재
  - 로그인 동작 + 기존 테스트 스위트 통과
