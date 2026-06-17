---
title: 발표 인덱스 (Quick Reference)
category: presentation
status: current
last_updated: 2026-06-15
related:
  - docs/clickeye-presentation-slides.md
  - docs/clickeye-product-guide.md
---

# ClickEye 발표 인덱스 (Quick Reference)

> 내일 발표 시 빠르게 참조할 수 있는 한 페이지 요약.
> 상세 자료는 `clickeye-product-guide.md` 와 `clickeye-development-pipeline.md` 에.

---

## 발표 자료 두 묶음

| 묶음 | 파일 | 용도 |
|---|---|---|
| **① 제품 자체** | `docs/clickeye-product-guide.md` | "이 제품이 뭐고 어떻게 쓰는가" |
| **② 개발 파이프라인** | `docs/clickeye-development-pipeline.md` | "우리는 이 제품을 어떻게 만드는가" |

---

## 발표 흐름 추천 (45 분 기준)

| 시간 | 섹션 | 자료 |
|---|---|---|
| 0:00~0:05 | 인사 + 한 줄 핵심 메시지 | Product Guide §12 부록 B |
| 0:05~0:15 | 제품 소개 (사용 안내) | Product Guide §3~5 |
| 0:15~0:25 | 라이브 데모 (신규 위저드 + Modernize) | Product Guide §11 |
| 0:25~0:35 | 동작 원리 + 차별점 | Product Guide §6~9 |
| 0:35~0:42 | 개발 파이프라인 소개 (우리도 우리 도구 씁니다) | Development Pipeline §1~3 + §12 |
| 0:42~0:45 | Q&A | Product Guide §12 |

---

## 한 줄 핵심 (어떤 청중이라도)

> **"ClickEye 는 5 분 위저드 → ZIP 다운로드 → 사용자 로컬에서 AI 가 코드를 자율적으로 작성하는 자동화 솔루션입니다.**
> **우리는 이 시스템을 우리 자신을 만들기 위해 매일 사용합니다."**

---

## 3 가지 차별점 (어떤 슬라이드에도 들어가야)

1. **ZIP-first 보안** — 코드가 ClickEye 클라우드에 영구 저장되지 않음
2. **한국 시장 친화** — Linear · Notion · Telegram · 한국어 PM/Agent
3. **자율 진화** — Linear → 멀티 Agent (Claude 메타프롬프트 → Claude → Codex) → 거버넌스 게이트 → PR

---

## 라이브 데모 사전 체크리스트

```bash
□ dev 서버 두 개 기동
  cd clickeye-web && npm run dev          # http://localhost:3000
  cd clickeye-api && uv run uvicorn app.main:app --reload --port 8000

□ webhook + ngrok (선택, Modernize 데모용)
  bash scripts/webhook-doctor.sh

□ 환경 변수 확인
  echo $ANTHROPIC_API_KEY | head -c 20    # 적어도 sk-ant- 시작 확인
  echo $LINEAR_API_KEY    | head -c 20    # lin_api_ 시작 확인

□ 화이트리스트 GitHub repo 준비 (Modernize 데모용)
  - 사전 설치된 demo App 으로 접근 가능한 small Django 또는 Express repo

□ 브라우저 캐시 미리 청소 (Ctrl+Shift+R)

□ 화면 녹화 백업 (라이브 실패 대비)
  - 신규 위저드 12-step 완주 영상
  - Modernize 진단 → finalize 영상
```

---

## 자주 받는 질문 5 가지 (즉답용)

### Q1. 코드를 외부로 보내지 않는다는 게 확실한가?
> Modernize 의 분석 워크스페이스는 `/tmp/modernize/<session>/` 에 임시 생성되고 Step 7 종료 직후 `shutil.rmtree` 로 즉시 삭제됩니다. DB 에는 분석 메타(언어 비중, 의존성 목록, AI 요약 markdown)만 영속. 원본 코드는 어떤 곳에도 보관되지 않습니다.

### Q2. AI 가 작성한 코드의 품질은 어떻게 보장되나요?
> 매 커밋마다 `harness-gate.sh` 가 모듈별 **lint + type + test** 를 자동 실행. 통과 못 하면 커밋 자체가 차단됩니다. 추가로 Claude 메타프롬프트(기획·정제) + Claude(구현) + Codex(QA) 교차 검토 후 **머지 직전 거버넌스 게이트**(정합성·위험)로 단일 AI 환각·계약 드리프트를 방지. (Gemini 기획은 폴백)

### Q3. AI 토큰 비용이 얼마나 드나요?
> 사용량 의존. 평균:
> - 신규 위저드 1 회 = $0.5 ~ $2
> - Modernize 분석 1 회 = $1 ~ $5
> - 자동 개발 작업 1 건 = $0.5 ~ $10
> BYOK 라 토큰 비용은 사용자가 직접 관리 + 정확히 추적 가능.

### Q4. Claude Code / Gemini CLI 와 ClickEye 의 차이는?
> 개별 AI 도구는 도구만. ClickEye 는 **도구 + 멀티 Agent 오케스트레이션 + Linear 자동 등록 + 자동 PR 생성 + 진단 + 멀티 플랫폼 ZIP** 까지 통합 패키지. 또한 위저드 UX 로 비개발자도 설계 가능.

### Q5. 우리 사내 Jenkins / GitLab CI 와 충돌하나?
> 충돌 없음. ClickEye 는 **코드 작성과 PR 생성까지** 만 담당. 빌드/배포는 기존 CI 그대로 사용. GitHub Actions 통합은 ZIP 안 `.github/workflows/` 로 옵트인.

---

## 비즈니스 청중용 추가 강조

| 메시지 | 효과 |
|---|---|
| "5 분 만에 설계, 즉시 ZIP 다운로드" | 도입 진입장벽 최소화 강조 |
| "한국 시장 친화 (Linear · Notion · Telegram · 한국어 PM)" | 글로벌 도구 대비 차별점 |
| "ZIP-first — 코드 외부 유출 0" | 보안 / 컴플라이언스 안심 |
| "BYOK — 토큰 투명, 마진 0" | 비용 신뢰 |
| "MVP-2-A 가 자기 자신의 자동화로 만들어짐" | 제품 신뢰성 증거 |

---

## 기술 청중용 추가 강조

| 메시지 | 슬라이드 키워드 |
|---|---|
| 비침습성 회귀 R-1~R-7 자동화 | "기존 코드 무영향 + R-7 Alembic downgrade 실측" |
| Plan-first + 사용자 승인 마커 | "AI 즉흥 코드 차단" |
| 모델 라우팅 Opus/Sonnet/Haiku | "토큰 80% 절감" |
| Hook 시점 4 단계 자동 검증 | "PreToolUse + PostToolUse + Stop" |
| 멀티 Agent + 거버넌스 | "Claude 메타프롬프트 → Claude → Codex + 머지 직전 거버넌스 게이트" |

---

## 시연 실패 시 백업 전략

| 실패 시나리오 | 대응 |
|---|---|
| Dev 서버가 안 켜짐 | 사전 녹화 영상 재생 + 코드 직접 보여주기 |
| Modernize 진단이 30 초 넘어감 | 진행률 화면 보여주면서 다음 슬라이드 진행 |
| Linear API 키 만료 | 사전 검증 화면 (M6 의 라이브 검증) 로 키 만료 감지 UX 시연 |
| Anthropic API 한도 초과 | `_placeholder_summary` fallback 시연 (M5 의 안전망) — 사전 시나리오로 등록 |
| GitHub App 미설치 | 503 응답 후 `docs/modernize-github-app-setup.md` 설치 가이드 보여주기 |

---

## 청중별 강조점 (1 줄 정리)

- **CTO / 기술 리더**: 멀티 Agent 합의 + Hook 자동 검증 + 비침습성 R-1~R-7
- **PM / 기획**: 12단계 위저드 + AI PM 추천 + Linear 자동 등록
- **DevOps / SRE**: Webhook 진단 자동화 + harness-gate + ZIP-first 보안
- **시니어 개발자**: Plan-first + 모델 라우팅 + Modernize 의 deterministic fallback
- **C-level / 영업**: BYOK 비용 투명 + 한국 시장 친화 + 5 분 도입

---

## 발표 후 후속 자료 안내

발표 후 청중에게 공유할 자료:

```
ClickEye 자료 패키지
├── docs/clickeye-product-guide.md           # 제품 사용 가이드
├── docs/clickeye-development-pipeline.md    # 개발 파이프라인 동작 원리
├── docs/architecture-overview.md            # 아키텍처 상세
├── docs/comparison.md                       # 경쟁사 비교
├── docs/license-model.md                    # 라이센스 / 가격
├── docs/pipeline-guide.md                   # 자동화 파이프라인 사용 가이드
├── docs/modernize-github-app-setup.md       # Modernize 설정 가이드
└── docs/modernize-regression-checklist.md   # 회귀 검증 체크리스트
```

베타 가입 / 문의: TBD
