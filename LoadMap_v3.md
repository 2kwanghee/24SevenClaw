# ClickEye - Development Roadmap v3

> AI 개발 자동화 SI 딜리버리 팩토리 — 딜리버리 콘솔에서 인게이지먼트 설계·실행·추적 → 하이브리드 러너로 자동 개발
> 로드맵 기간: 2026-04-07 ~ 2026-04-20 (2주)
> 업무 관리: Linear 티켓 기반

---

## 용어 정의

| 용어 | 의미 |
|------|------|
| **유저** | 서비스 이용자 (개발자, PM, 비개발자) |
| **관리자** | ClickEye 운영팀 (우리) |
| **웹** | ClickEye 웹 서비스 |
| **Agent 플랫폼** | Claude Code, Gemini CLI, Codex, Cursor 등 AI 코딩 도구 |
| **에이전트** | 웹에서 채용하는 가상 인력 (백엔드 엔지니어, 프론트엔드 등) |
| **스킬** | 에이전트가 사용하는 외부 도구 연동 (Notion, Linear, Teams, DB 등) |

---

## 서비스 비전

- **핵심 가치**: 딜리버리 콘솔에서 인게이지먼트를 설계·실행·추적하고 하이브리드 러너로 자동 개발
- **대상 유저**: 개발자, PM, 스타트업 — 터미널 경험 불문
- **비용 모델**: 1계정 1프로젝트 무료, 추가 프로젝트 유료 라이센스
- **Agent 토큰**: 유저 부담 (BYOK — Bring Your Own Key)

---

## 완료된 자산 (Phase 0)

### 웹 (clickeye-web)
- [x] 랜딩 페이지 (히어로 + CTA + 특징 + 가격)
- [x] 회원가입 / 로그인 (Auth.js v5 + JWT)
- [x] 대시보드 레이아웃
- [x] 프로젝트 목록 / 생성 / 상세 / 설정 페이지 (기본 CRUD)
- [x] 레지스트리 페이지 (기본 구조)

### API (clickeye-api)
- [x] 인증 엔드포인트 (JWT)
- [x] 프로젝트 CRUD API
- [x] User / Project / ProjectConfig / Registry / License / Ticket 모델
- [x] 헬스체크

---

## 에이전트 카탈로그

> CLI에서 계승 + 웹 UI 카드로 표시. 관리자가 지속 추가 가능.

| ID | 에이전트 | 역할 | 생성 파일 |
|----|---------|------|----------|
| `backend` | 시니어 백엔드 엔지니어 | API 설계, DB, 서버 로직 | `api-agent.md` |
| `frontend` | 프론트엔드 전문가 | 컴포넌트, 상태관리, 라우팅 | `web-agent.md` |
| `uiux` | UI/UX 디자이너 | 접근성, 반응형, 디자인 시스템 | `uiux-agent.md` |
| `devops` | DevOps 엔지니어 | Docker, CI/CD, 배포 | `infra-agent.md` |
| `fullstack` | 풀스택 시니어 | 백엔드+프론트 통합 | `fullstack-agent.md` |
| `harness` | 하네스 엔지니어 | 4단계 품질 통제 | `harness-guide.md` + 스킬 4종 |

## 스킬 카탈로그

> 두 종류: **워크플로우 스킬** (CLI 계승) + **외부 도구 스킬** (신규)

### 워크플로우 스킬 (CLI 계승)

| ID | 스킬 | API 키 | 설명 |
|----|------|--------|------|
| `tdd` | TDD 스마트 코딩 | 불필요 | 테스트 → 구현 → 리팩터링 |
| `ai-critique` | AI 코드 리뷰 | 불필요 | 자동 리뷰 + 개선 제안 |
| `ralph-loop` | Ralph 자율 루프 | 불필요 | 자율 개발 루프 |
| `harness-gate` | 하네스 Gate | 불필요 | lint+test 통과 후 커밋 허용 |

### 외부 도구 스킬 (신규 — 지속 업데이트)

| ID | 스킬 | API 키 | .env 변수 |
|----|------|--------|----------|
| `linear` | Linear 연동 | 필요 | `LINEAR_API_KEY` |
| `notion` | Notion 연동 | 필요 | `NOTION_API_KEY` |
| `slack` | Slack 알림 | 필요 | `SLACK_WEBHOOK_URL` |
| `telegram` | Telegram 알림 | 필요 | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |
| `github` | GitHub 연동 | 필요 | `GITHUB_TOKEN` |
| `teams` | Teams 알림 | 필요 | `TEAMS_WEBHOOK_URL` |
| `database` | DB 연결 | 필요 | `DATABASE_URL` |

## Agent 플랫폼

> 유저가 선택하는 AI 코딩 도구에 따라 폴더 구조가 달라짐

| ID | 플랫폼 | 설정 디렉토리 | 에이전트 파일 위치 | 설정 파일 |
|----|--------|-------------|-------------------|----------|
| `claude-code` | Claude Code | `.claude/` | `.claude/agents/` | `.claude/settings.json` |
| `gemini-cli` | Gemini CLI | `.gemini/` | `.gemini/agents/` | `.gemini/settings.json` |
| `codex` | Codex (OpenAI) | `.codex/` | `.codex/agents/` | `codex.json` |
| `cursor` | Cursor | `.cursor/rules/` | `.cursor/rules/` | `.cursorrules` |

---

## Linear 티켓 구조

### 프로젝트 라벨

| 라벨 | 용도 |
|------|------|
| `web` | 프론트엔드 (Next.js) |
| `api` | 백엔드 (FastAPI) |
| `engine` | 생성 엔진 (lib/engine) |
| `infra` | 인프라/배포 |

### 티켓 사이즈 기준

| 사이즈 | 예상 소요 | 예시 |
|--------|----------|------|
| `XS` | ~2시간 | API 응답 타입 추가, 상수 정의 |
| `S` | ~4시간 | 단일 API 엔드포인트, 단일 컴포넌트 |
| `M` | ~1일 | API + 프론트 엔드 통합, 거버넌스 룰 추가 |
| `L` | ~2일 | 다중 모듈 통합, 거버넌스 정책 시스템 |
| `XL` | ~3일+ | E2E 딜리버리 플로우, 메타프롬팅 엔진 |

---

## Phase 2 예고 (04-21 이후)

> Phase 1 (2주) 완료 후 확장

- **LLM 기반 추천**: 규칙 기반 → Claude/GPT 활용 지능형 추천
- **커뮤니티 에이전트**: 유저가 커스텀 에이전트 업로드/공유
- **에이전트 마켓플레이스**: 프리미엄 에이전트 유료 판매
- **사용 통계 대시보드**: 인기 에이전트/스킬/조합 분석
- **GitHub 연동**: 인게이지먼트 기반 레포 생성 및 배포
- **라이센스 시스템**: 1계정 1프로젝트 무료, 추가 유료

---

## 다프로젝트 딜리버리 전환 (2026-07 착수)

> 자기 저장소 전용 자동화 → **임의 프로젝트를 수주·실행하는 엔진**.
> 라이트한 프로젝트뿐 아니라 대형 레거시 현대화까지 같은 엔진으로 받는다.
> 설계 기준: `docs/multiproject-delivery.md` (5-Plane · Delivery Tier T1~T3 · 결정 D-1~D-9)

**Delivery Tier** — 기존 `Preset.maturity_level` 에 얹는다. 티어별로 코드 경로가
갈라지지 않고, 갈라지는 것은 `DeliveryProfile` 값뿐이다.

| Tier | 대상 | 집행 | 실행 |
|------|------|------|------|
| T1 Lite (`starter`) | 소규모 SI, PoC | 머지게이트 | 단일 순차 |
| T2 Standard (`intermediate`) | 일반 수주 | + 플랜·계약·비밀정보 | 단일 순차 |
| T3 Enterprise (`advanced`) | 대형 레거시 현대화 | + 소유권·금지git·기록선행 (PreToolUse 전량) | 샤드 N 병렬 + worktree |

| Phase | 내용 | 상태 |
|-------|------|------|
| **P0** | 거버넌스 정책 외부화(`Policy` 주입) + `DeliveryProfile` 미러·API | ✅ 완료 (CE-314, 2026-07-28) |
| **P1** | 완주 오케스트레이터 — 실패 무유실·재시도 한도·정지(HALT) 보고 | ✅ 완료 (2026-07-28) |
| P2 | YAML 제어면 계약 — 스키마·버전·서명·fail-closed·거부 콜백 | 대기 |
| P3 | 구독형 전용 강제 — 게이트웨이 강제 모드 + 종량 잔존 경로 감사 | 대기 |
| P4 | 시트 풀 + 계정별 토큰 모니터링 (`seat_id` 원장·시트별 레이트) | 대기 |
| P5 | 다프로젝트 동시 실행 — 락 세분화·작업 경로 격리 | P4 다음 |
| P6 | 티켓 전량 자동 발급 — 인테이크 → Linear, 사람 확인 제거 | 대기 |
| P7 | 정합성 테스트 게이트 — 전 티켓 완주 후 통합 검증 | P6 다음 |
| P8 | 집행면 게이트 엔진 + 룰 플러그인 | 대기 (선행조건 有) |
| P9 | 기록면 1급화 + 대시보드 | P4 다음 |

Phase 정의·순서 근거의 정본은 `docs/multiproject-delivery.md` §8.

---

## 핵심 원칙

1. **솔루션 중심**: 기술 스택이 아닌 "무엇을 만들 것인가"부터 시작
2. **프리뷰 우선**: 다운로드 전에 생성될 파일을 반드시 미리보기
3. **API 키 보안**: 모든 외부 도구 API 키는 Vault 암호화 저장 + RBAC 접근 통제
4. **멀티플랫폼**: Claude Code 외에도 Gemini, Codex, Cursor 지원
5. **지속 확장**: 에이전트/스킬/플랫폼은 관리자가 카탈로그 JSON 추가만으로 확장
6. **CLI 자산 재활용**: 생성 엔진, 템플릿, 카탈로그를 CLI와 웹이 공유
7. **Linear 기반 업무**: 모든 작업은 Linear 티켓으로 추적

---

## 계획 변경 이력

| 변경일 | 변경 내용 | 사유 |
|--------|----------|------|
| 2026-03-31 | 서비스 피벗: 고객 서버 에이전트 → 클라우드 SaaS | paperclip.ing 참고 |
| 2026-06-01 | 서비스 피벗: 위저드 기반 → 딜리버리 콘솔 기반 | 딜리버리 워크플로우 우선 |
| 2026-07-22 | LoadMap_v3 현행화: 위저드 구간 제거 | 딜리버리 서비스 모델로 전환 |
| 2026-07-27 | 다프로젝트 딜리버리 전환 착수 (P0~P5) | 대형 프로젝트 딜리버리 수용 — 전사 구동 목표 |

---

## 참조 문서

- `clickeye-web/` — 웹 프론트엔드 (딜리버리 콘솔)
- `clickeye-api/` — 백엔드 API (딜리버리/거버넌스 API)
- `docs/architecture-overview.md` — 시스템 아키텍처
- `.claude/agents/harness-guide.md` — 하네스 엔지니어링 가이드
- `.claude/skills/dev-skills.md` — 개발 스킬 레지스트리
