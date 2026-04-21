# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[rebrand] Phase 4 — 패키지명 + lockfile 재생성**
  > 요청사항: npm/Python 패키지명 변경 및 lockfile 재생성.

범위: @24sevenclaw/cli → @clickeye/cli, @24sevenclaw/contracts → @clickeye/contracts, sevenclaw-api → clickeye-api, sevenclaw-agent → clickeye-agent.

대상: package.json 3개, pyproject.toml 2개, package-lock.json 3개 재생성, uv.lock 2개 재생성.

의존: CLK-3(24S-182) 완료 후 진행(env/db 안정화 확인).

검증: npm install, uv sync 무오류, 임포트 체인 이상 없음.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | Phase 4 패키지명 + lockfile 재생성 | ✅ 완료 | @clickeye/cli, @clickeye/contracts, clickeye-web, clickeye-api, clickeye-agent |