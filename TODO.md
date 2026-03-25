# 24SevenClaw - Daily TODO

> Claude가 이 파일을 참고하여 순차적으로 개발한다.
> 작업 완료 시 `[x]` 표시. 하루 마감 시 `/endwork` 명령으로 아카이브.

---

## 오늘: 2026-03-25 (화) — Day 3: 인증 시스템 (회원가입/로그인/JWT)

### 1. 인증 코드 확인 (api)
- [x] `app/core/security.py` — JWT 생성/검증 (access + refresh) 구현 확인
- [x] `app/schemas/user.py` — UserCreate, UserLogin, TokenResponse 등 스키마 확인
- [x] `app/services/auth_service.py` — register, authenticate, refresh 로직 확인
- [x] `app/api/v1/auth.py` — POST /register, /login, /refresh, GET /me 엔드포인트 확인
- [x] `app/dependencies.py` — get_current_user 의존성 확인

### 2. 테스트 인프라 보강 (api)
- [ ] `tests/conftest.py` — 테이블 자동 생성 + auth_headers fixture 추가
- [ ] `tests/test_auth.py` — 인증 엔드포인트 테스트 작성

### 3. 테스트 항목
- [ ] 회원가입 성공
- [ ] 회원가입 이메일 중복 에러
- [ ] 회원가입 유효성 검사 실패 (비밀번호 짧음)
- [ ] 로그인 성공 (토큰 반환)
- [ ] 로그인 실패 (잘못된 비밀번호)
- [ ] 토큰 리프레시 성공
- [ ] 토큰 리프레시 실패 (잘못된 토큰)
- [ ] GET /me 인증 성공
- [ ] GET /me 인증 실패 (토큰 없음)

### 4. 린트/타입체크 (api)
- [ ] `uv run ruff check .` 통과
- [ ] `uv run mypy app/` 통과

### 5. 마무리
- [ ] 변경사항 커밋 (`[api] 인증 시스템 테스트 추가`)
- [ ] PjPlan.md Day 3 상태 업데이트 (✅)
