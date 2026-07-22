---
title: 딜리버리 서비스 제품 안내
category: product
status: current
last_updated: 2026-07-22
related:
  - docs/architecture-overview.md
  - docs/pipeline-guide.md
---

# ClickEye — 딜리버리 서비스 제품 안내

> **AI 기반 인게이지먼트 딜리버리 플랫폼**
> 클라우드 콘솔에서 인게이지먼트(프로젝트)를 설계·실행·추적하면, AI가 로컬에서 자율적으로 코드를 작성합니다.
>
> 본 문서는 ClickEye 의 **딜리버리 서비스** 사용 방법과 기술 동작 원리를 설명합니다.

---

## 목차

1. [한눈에 보는 ClickEye 딜리버리](#1-한눈에-보는-clickeye-딜리버리)
2. [서비스 가치](#2-서비스-가치)
3. [딜리버리 콘솔 진입점](#3-딜리버리-콘솔-진입점)
4. [인게이지먼트 기반 딜리버리 흐름](#4-인게이지먼트-기반-딜리버리-흐름)
5. [AI Team 오케스트레이션](#5-ai-team-오케스트레이션)
6. [거버넌스 게이트](#6-거버넌스-게이트)
7. [운영 패널 (Ops)](#7-운영-패널-ops)
8. [클라우드 + 로컬 하이브리드 아키텍처](#8-클라우드--로컬-하이브리드-아키텍처)
9. [보안 보장](#9-보안-보장)
10. [FAQ](#10-faq)

---

## 1. 한눈에 보는 ClickEye 딜리버리

ClickEye 는 다음을 한 번에 해결합니다:

| 단계 | 담당 | 시간 |
|------|---|---|
| ① 설계 | 클라우드 콘솔(/delivery/[engagementId]) | **수 분** |
| ② 작업 요청 | AI Team (서브태스크 자동 생성 + 승인) | **수 분** |
| ③ 자동 실행 | 로컬 Claude Code 인스턴스 | **비실시간** |
| ④ 결과 | Linear 이슈 → In Progress → PR 생성 → Done | **자동 추적** |

### 핵심 가치

> **"클라우드 콘솔에서 인게이지먼트를 만드는 순간, AI가 로컬에서 코드 작성을 자율적으로 시작한다."**

기존: 환경 설정·도구 통합·프롬프트 작성에 **수시간 ~ 수일** 소요
ClickEye: 콘솔 설계 → AI Team 생성 → 자동 개발 → **즉시 결과 추적**

---

## 2. 서비스 가치

### 인게이지먼트 기반 딜리버리의 이점

| 기존 방식 | ClickEye 딜리버리 |
|---|---|
| 클라이언트가 직접 환경 설정 (ZIP 압축 해제, .env, 도구 설치) | 클라우드 콘솔에서 한 번에 인게이지먼트 설계 |
| 각 프로젝트마다 새로운 AI 프롬프트 작성 | AI Team 프로필 자동 매칭 + 구성 재사용 |
| 진행 상황 추적 어려움 (로컬 로그만 확인) | 딜리버리 콘솔에서 실시간 추적 + Linear 동기화 |
| AI 작업 결과가 산발적 | 거버넌스 게이트로 품질 검증 + 위험 분류 자동화 |
| 인프라/컨테이너 관리 사용자 책임 | 서버 측 컨테이너 오케스트레이션 (향후 MVP-3) |

### 핵심 가치

1. **클라우드 중심 설계** — 브라우저 콘솔에서 모든 의사결정 + AI Team 구성 자동 매칭
2. **자동 추적** — Linear ↔ GitHub ↔ 콘솔 실시간 동기화
3. **품질 보증** — 거버넌스 게이트 + 멀티 Agent 검토 자동화
4. **보안** — 코드는 로컬/서버에만 존재, 클라우드는 메타만 보관

---

## 3. 딜리버리 콘솔 진입점

대시보드 → **Projects** → 프로젝트 선택 → **Delivery** 탭:

```
┌────────────────────────────────────────────────────┐
│ /dashboard/projects/[projectId]/delivery           │
│                                                    │
│  📋 활성 인게이지먼트 목록                            │
│  ├─ Engagement ID + 상태 + AI Team 정보              │
│  ├─ 설계 / 실행 / 추적 단계 시각화                    │
│  └─ [새 인게이지먼트 시작] 버튼                       │
└────────────────────────────────────────────────────┘
```

인게이지먼트 생성 → 콘솔 내에서 다음 흐름 관리:
1. **설계** — 요구사항 + AI Team 프로필 선택
2. **실행** — 서브태스크 승인 + AI 작업 트리거
3. **추적** — Linear 상태 동기화 + PR 모니터링

---

## 4. 인게이지먼트 기반 딜리버리 흐름

### 진입 — 인게이지먼트 생성

콘솔 → **Projects → [projectId] → Delivery → [+ 새 인게이지먼트]**

| 입력 | 설명 |
|---|---|
| 인게이지먼트명 | 예: "사용자 인증 API 구현" |
| 요구사항 | 자유 텍스트 또는 마크다운 |
| 예상 규모 | S / M / L / XL |
| 우선순위 | P0 / P1 / P2 |
| AI Team 프로필 | (선택) 자동 추천 또는 수동 선택 |

### 설계 단계

인게이지먼트 상세 페이지:
- **요구사항 에디터** — 자유 입력 또는 Markdown
- **AI Team 구성 미리보기** — 프로필별 에이전트/스킬/MCP
- **Linear 이슈 매핑** (선택) — 기존 Linear 이슈와 연결

### 실행 단계

**[AI 초안 생성]** 버튼 클릭:
1. 콘솔이 요구사항을 분석해 **서브태스크 초안 생성**
2. 사용자가 초안 검토 + 승인/수정
3. **[작업 요청]** → Linear 이슈 자동 등록 (Queued 상태)
4. 로컬 Claude Code 인스턴스가 자동으로 감지 → 개발 시작

### 추적 단계

콘솔 내 **실시간 진행 상황**:
- **Linear 상태** — DayQueued → In Progress → Done
- **브랜치** — git 자동 생성 `feature/{TICKET}/*`
- **PR 링크** — 완료 시 자동 노출
- **AI Team 로그** — 각 단계별 결과 요약

---

## 5. AI Team 오케스트레이션

인게이지먼트 생성 시 콘솔이 자동으로 AI Team 을 구성합니다.

### AI Team 구성

| 역할 | 담당 | 입력 | 출력 |
|---|---|---|---|
| **기획 (메타프롬프트)** | Claude (Sonnet) | 요구사항 | 정제된 PLAN |
| **구현** | Claude (Sonnet) | PLAN | 코드 + 테스트 |
| **QA** | Codex (gpt-5) | PLAN + 코드 | 리뷰 피드백 |
| **거버넌스** | pre_merge_gate.py | 변경사항 | 정합성·위험 검증 |

### 멀티 Agent 기능

1. **메타프롬프트 기획** — 요구사항을 구현 가능한 스펙으로 자동 정제
   - 자동 범위 제한 + 수용 기준 추출
   - 위험 요인 자동 분류

2. **하네스 4단계** (로컬 Claude Code)
   - Router: 의도 분석
   - Context: 필요한 파일만 선별
   - Loop: 코드 작성 → 테스트 → 반복 (MAX 5회)
   - Worker: 역할 분리 (WRITE_CODE, TEST, REVIEW)

3. **거버넌스 게이트** — 머지 직전 자동 검증
   - 계약(Contract) 정합성
   - 티켓 참조(Ticket-ref) 확인
   - 위험 분류 (HIGH tier → PR 강등)

### 로컬 실행 환경

사용자 로컬에서 Claude Code 또는 동등 플랫폼이 실행:
- `.claude/` 또는 `.gemini/` 또는 `.cursor/` 설정 자동 주입
- `scripts/auto_dev_pipeline.sh` 자동 트리거
- Linear webhook 감지 또는 폴링 (30초 간격)

---

## 6. 거버넌스 게이트

모든 코드 변경이 머지 직전에 자동 검증되는 **단일 SSOT (Single Source of Truth)** 모듈:
`scripts/pre_merge_gate.py`

### 자동 검증 항목

| 검증 | 목적 | 실패 시 |
|---|---|---|
| **Contract Drift** | API 스키마 변경 감지 | 머지 차단 + Linear Backlog 이동 |
| **Ticket-ref** | 브랜치에 Linear 티켓 키 병기 | 머지 차단 |
| **Plan Trace** | 변경이 PLAN.md 와 부합 | 경고 (권고) |

### 위험 분류

| 위험도 | 변경 영역 | 처리 |
|---|---|---|
| **HIGH** | `contracts/`, `infra/`, `*auth*`, 보안 | PR 강등 (직접 머지 금지) |
| **MEDIUM** | API endpoint, 주요 서비스 | 거버넌스 검증 필수 |
| **LOW** | docs, scripts, 테스트 | 최소 검증 |

### 머지 정책

- **AUTO_MERGE=true** + LOW risk → 직접 머지 (`git push`)
- **HIGH risk** 또는 **검증 실패** → PR 경로로 강등 (기존 CI/CD 플로우)
- **거버넌스 거부** → Linear Backlog + Telegram 알림

---

## 7. 운영 패널 (Ops)

대시보드 → **Ops** → 인프라/데이터베이스 모니터링:

| 패널 | 기능 |
|---|---|
| **Containers** | 실행 중인 컨테이너 상태 (webhook, ngrok, DB) |
| **Environment** | 환경변수 + 토글 (`FLOWOPS_*`) |
| **Tables** | 데이터베이스 테이블 조회 (pm_profiles, engagements 등) |

### 관리자 기능

- 인게이지먼트 상태 수동 변경 (디버깅)
- 파이프라인 로그 조회
- Linear 동기화 상태 확인
- AI Team 프로필 카탈로그 관리

---

## 8. 클라우드 + 로컬 하이브리드 아키텍처

ClickEye 는 **두 레이어** 로 동작합니다:

```
┌──────────────────────────────────────────────────────┐
│  ☁  Cloud Plane (clickeye-web + clickeye-api)        │
│   ├─ 딜리버리 콘솔 (/delivery/[engagementId])         │
│   ├─ AI Team 프로필 카탈로그                           │
│   ├─ 인게이지먼트 메타 관리                             │
│   ├─ Linear ↔ GitHub 동기화                          │
│   └─ 거버넌스 게이트 (검증·위험분류)                    │
└────────────────┬─────────────────────────────────────┘
                 │  인게이지먼트 정보 전달 (JSON)
                 ▼
┌──────────────────────────────────────────────────────┐
│  💻 Local Execution Plane (사용자 로컬 / 서버)         │
│   ├─ Claude Code / Gemini / Codex / Cursor            │
│   ├─ .claude/ 또는 .gemini/ 설정                       │
│   ├─ auto_dev_pipeline.sh                            │
│   ├─ webhook 감지 또는 폴링                            │
│   └─ API 키는 .env 로컬만 (ClickEye 미수집)             │
└──────────────────────────────────────────────────────┘
```

### 기술 스택

**Cloud**:
- Frontend: Next.js 15 + TypeScript + Tailwind
- Backend: FastAPI 0.115 + PostgreSQL + Redis
- AI: Anthropic Claude + Google Gemini + OpenAI Codex

**Local**:
- Agent: Claude Code / Gemini CLI / Codex
- Scripts: bash + Python
- Webhook: ngrok 또는 Cloudflare Tunnel

---

## 9. 보안 보장

| 데이터 | 위치 | 비고 |
|---|---|---|
| **소스 코드** | 로컬 + 서버 | 클라우드 영구 저장 안 함 |
| **API 키** | 로컬 `.env` 만 | ClickEye 서버 미수집 |
| **인게이지먼트 메타** | 클라우드 DB | 요구사항·AI Team 구성만 |
| **Linear 자격증명** | 클라우드 (Fernet 암호화) | 선택적 저장 (사용자 동의) |
| **Webhook 서명** | HMAC-SHA256 검증 | Linear 신뢰성 보장 |

> **아키텍처 원칙**: 클라우드는 설계·조율·검증 담당 / 로컬은 실행 담당 / 코드는 사용자 권역에만 존재

---

## 10. FAQ

### Q1. 인게이지먼트 생성부터 결과까지 얼마나 걸리나요?
> 콘솔 설계 **수 분** + AI Team 승인 **수 분** + 자동 개발 **시간 단위** (작업 복잡도 의존).

### Q2. 결과를 모니터링하는 방법은?
> 콘솔 내 진행 상황 + Linear 상태 자동 동기화 + PR 링크 자동 노출.

### Q3. 우리 회사 사내 도구 (Jira, Slack) 연동도 가능한가요?
> 현재 **Linear 우선** 지원. Jira/Slack는 커스텀 통합으로 가능 (연락).

### Q4. AI 토큰 비용은?
> 사용량 의존 (BYOK). 평균 인게이지먼트 1건 = $0.5~$10 (규모 의존).

### Q5. 로컬 Claude Code 없이 클라우드만으로 실행 가능한가요?
> MVP-3 (향후)에서 클라우드 기반 Temporal 워커 지원 예정. 현재는 로컬 실행 필수.

### Q6. 코드 보안은?
> AI 생성 코드는 사용자 로컬에만 존재. ClickEye 클라우드는 메타만 보관. API 키는 `.env` 로컬만.

### Q7. 거버넌스 게이트가 머지를 거부하면?
> Linear Backlog로 이동 + Telegram 알림. 사용자가 수정 후 재요청.

### Q8. 다른 AI 도구 (Claude Code, Gemini) 와의 차이?
> 개별 도구 + 딜리버리 콘솔 + AI Team 자동 매칭 + 거버넌스 게이트 통합.

---

## 관련 문서

| 문서 | 위치 |
|---|---|
| 아키텍처 | `docs/architecture-overview.md` |
| 파이프라인 | `docs/pipeline-guide.md` |
| Linear 연동 | `docs/user-guide/linear-realtime-tracking.md` |
| 서비스 실행 | `docs/spec/run_guide.md` |

---

> **"클라우드 콘솔에서 인게이지먼트를 설계하면, AI가 로컬에서 자율적으로 코드를 작성하기 시작한다."**
