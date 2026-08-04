# ClickEye - Daily TODO

> Claude가 이 파일을 참고하여 순차적으로 개발한다.
> 작업 완료 시 `[x]` 표시. 하루 마감 시 `/endwork` 명령으로 아카이브.
> Linear 프로젝트: "LoadMap v3 — 솔루션 빌더" (24S-18 ~ 24S-43)

---

## 2026-08-04

### 완료
- [x] **CE-338** 무인 체인 점화 종단 검증 — Linear→ngrok→수신 컨테이너→Redis 큐→호스트 워커→파이프라인 전 구간 실측 관통. crontab 을 정본과 완전 일치하게 재설치
- [x] **CE-349** 웹훅 재트리거 무한 루프 차단 (PR #89) — 락 보유자 생존 판정 + 체인 상한 5회. 부수 수정 2건: `webhook-doctor.sh` 컨테이너 PID 오탐, ngrok watchdog 예약 도메인 고정
- [x] 다음 스프린트 큐 리필 — CE-350~354 등재 (전부 `Wait`)
- [x] `/docs-sync` — `run_guide.md`(3-5-1 재부팅 복구 절·3-6 2단계 선행조건·STOP-CHAIN 트러블슈팅), `multiproject-delivery.md`(§6-1 주석·변경 이력)

### 차단 — 사용자 입력 필요 (다프로젝트 체인 활성, run_guide 3-6)
- [ ] **1단계 시트 풀 등록** — `claude setup-token` 을 구독 계정 셸에서 직접 실행해야 함 (원장 `.ralph/seats.json` 아직 없음)
- [ ] **2단계 워크스페이스 매핑** — `CLICKEYE_SERVICE_KEY` 미발급이라 머신 API 폴링 불가 → **CE-350** 선행
- [ ] **3단계 워크스페이스 조달** — 고객 repo URL 필요

> 무의존 검증은 통과: 디스패처 DRYRUN(`후보=0 active시트=0`), `linear_watcher --dry-run`,
> API 서버 기동(`/api/v1/health` healthy · 마이그레이션 058 head · 인테이크 API 활성).

### 다음 후보 (Linear `Wait`)
- [ ] CE-350 머신 서비스 키 발급 CLI (High — 활성 절차의 실제 블로커)
- [ ] CE-351 재부팅 내구성 (High — db·redis `RestartPolicy=no`, 2026-08-04 마운트 장애로 실증)
- [ ] CE-352 큐 신뢰성 BRPOPLPUSH + confirmer 지연 비대칭 (Medium)
- [ ] CE-353 F-1 후속 정제·분해 사용량 json 전환 (Medium)
- [ ] CE-354 F-4 잔여 제어면 YAML `gates` 직접 소비 (Low)
