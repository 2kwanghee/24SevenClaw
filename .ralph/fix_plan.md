# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[rebrand] Phase 2 — 환경변수 prefix 변경 (SEVENCLAW_* → CLICKEYE_*)**
  > 요청사항: 환경변수 prefix 및 데이터 경로 변경.

범위: SEVENCLAW\_\* → CLICKEYE\_*, /data/sevenclaw → /data/clickeye, 라이센스 키 포맷 24SC-* → CLK-\*.

대상 파일: 24SevenClaw-agent/agent/config.py, .env.example 5개, .env, 에이전트 런타임 코드(SEVENCLAW_AGENT_ID, SEVENCLAW_AGENT_SECRET, SEVENCLAW_LICENSE_KEY, SEVENCLAW_CLOUD_WS_URL 등).

의존: CLK-1(24S-180) 완료 후 진행.

검증: 에이전트 부팅 테스트, .env 샘플 로드 확인.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | [rebrand] Phase 2 환경변수 prefix 변경 | ✅ 완료 | config.py + .env.example 2개 + docker-compose + license-model. .env는 안전규칙 준수 미변경 |