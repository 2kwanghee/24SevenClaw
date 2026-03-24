# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [!] **2. FastAPI 앱 완성 (api)** — 파이프라인 순차 실행 방식 개선 논의 중, 수동 진행 예정
  > 요청사항: ```
`app/main.py` — CORS, lifespan(startup/shutdown), 라우터 마운트 확인
`app/config.py` — Pydantic Settings에 DATABASE_URL, REDIS_URL, SECRET_KEY 등 환경변수 정의
`app/database.py` — async engine + async sessionmaker + get_db 의존성
`app/api/v1/health.py` — GET /health (DB ping + Redis ping 포함)
health 엔드포인트 수동 테스트 (curl 또는 httpx)

완료된 항목은 [x]로 체크할 것
```

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|