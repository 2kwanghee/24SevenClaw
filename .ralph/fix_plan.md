# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **3. Alembic 마이그레이션 설정 (api)**
  > 요청사항: ```
`alembic.ini` — sqlalchemy.url을 env에서 읽도록 수정
`alembic/env.py` — async 마이그레이션 설정 (run_migrations_online async)
`alembic/env.py` — target_metadata에 Base.metadata 연결
`app/models/__init__.py` — 모든 모델 import 집중 (autogenerate용)
```

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|