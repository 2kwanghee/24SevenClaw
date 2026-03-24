# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **4. Users 테이블 마이그레이션 (api)**
  > 요청사항: ```
`app/models/user.py` — User 모델 확인/보강 (id, email, password_hash, is_active, created_at, updated_at)
`alembic revision --autogenerate -m "create_users_table"` 실행
`alembic upgrade head` 실행
DB에 users 테이블 생성 확인 (psql 또는 SQLAlchemy inspect)
```

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|