---
title: ClickEye 문서 매니페스트
category: reference
status: current
last_updated: 2026-06-15
related:
  - .claude/skills/docs-sync/SKILL.md
  - .claude/agents/docs.md
---

# ClickEye 문서 매니페스트

`docs/` 전체의 **단일 정식 레지스트리**입니다. 모든 문서는 정규화 프론트매터(아래 규약)를 갖추고 이 표에 등재됩니다.

> **최소 필수 세트 규칙**: 이 표에 없는 `docs/` 문서는 *아카이브/삭제 후보*로 간주합니다. 새 문서를 추가하면 반드시 여기에 한 줄 등재하세요. (단 `WeeklyWorkReport/`, `daily/` 등 자동 생성 아카이브는 제외.)

## 정규화 프론트매터 규약

모든 문서 상단에 아래 YAML 프론트매터를 둡니다. 페이지 스펙(`docs/pages/`)은 기존 `_template.md` 필드를 포함한 **동일 슈퍼셋**을 사용합니다.

```yaml
---
title: 문서 제목
category: architecture | guide | product | reference | page | presentation
status: current | needs-revision | draft | implemented
last_updated: YYYY-MM-DD
related:            # 이 문서가 추적하는 코드/문서 경로 (변경 감지용)
  - 경로/...
route: ...         # 페이지 문서만(선택)
version: ...       # 선택
---
```

- `status: needs-revision` = 관련 코드가 바뀌었으나 문서 반영 전. `/docs-sync` 스킬이 자동 표시.
- `related` = `/docs-sync`가 "변경된 코드 → 영향 문서"를 매핑하는 키. 페이지 문서의 `pages/components/store` 역할을 통합.

## 지속 업데이트 워크플로우

- **`/docs-sync` 스킬**: 유의미한 코드 변경 후 호출 → 변경 경로를 `related`로 역매핑 → 영향 문서 `last_updated` 갱신 + `status: needs-revision` 표시 + 결정적 구간 본문 갱신. 상세: `.claude/skills/docs-sync/SKILL.md`.
- **`docs` 에이전트**: 문서 작성/구조 변경 전담. 이 매니페스트와 프론트매터 규약을 준수.
- **역할 경계**: `log-work`(Linear 작업로그 + LoadMap 체크박스) ≠ `/docs-sync`(`docs/` 본문·프론트매터 현행화).

---

## 문서 레지스트리

### architecture — 시스템 구조
| 문서 | 목적 | status |
|------|------|--------|
| [architecture-overview.md](architecture-overview.md) | 클라우드 SaaS + 로컬 에이전트 분리, 12단계 위저드 전체 구조 | current |
| [agent-protocol.md](agent-protocol.md) | 서버↔에이전트 통신 프로토콜 | current |
| [si-factory-transition.md](si-factory-transition.md) | SI 딜리버리 팩토리 전환 마스터 설계 기준 (P0~P4 티켓 CE-296~301 참조) | current |

### guide — 실행/사용 가이드
| 문서 | 목적 | status |
|------|------|--------|
| [cli-guide.md](cli-guide.md) | `@clickeye/cli`(`ce`) 명령·카탈로그·프리셋 | current |
| [pipeline-guide.md](pipeline-guide.md) | 자동화 파이프라인 v6 + 거버넌스 게이트 | current |
| [si-factory-operating-guide.md](si-factory-operating-guide.md) | SI 팩토리 전략적 실행 가이드 (배포·토글·통제·선결조건) | current |
| [aws-deployment-guide-ec2.md](aws-deployment-guide-ec2.md) | EC2 1대 docker-compose 배포(초보자용) | current |
| [modernize-github-app-setup.md](modernize-github-app-setup.md) | Modernize용 GitHub App 등록 런북 | current |
| [spec/run_guide.md](spec/run_guide.md) | 서비스 구동(API/web/webhook/ngrok/DB) | current |
| [user-guide/linear-realtime-tracking.md](user-guide/linear-realtime-tracking.md) | 엔드유저 ZIP 기반 Linear 실시간 연동 | current |

### product — 제품/내러티브
| 문서 | 목적 | status |
|------|------|--------|
| [clickeye-product-guide.md](clickeye-product-guide.md) | 제품 사용 안내 & 동작 원리(종합) | current |
| [clickeye-development-pipeline.md](clickeye-development-pipeline.md) | 도그푸딩 개발 파이프라인 동작 원리 | current |
| [comparison.md](comparison.md) | 유사 플랫폼 대비 아키텍처 비교 | current |

### presentation — 발표 자료
| 문서 | 목적 | status |
|------|------|--------|
| [clickeye-presentation-index.md](clickeye-presentation-index.md) | 발표 흐름 Quick Reference | current |
| [clickeye-presentation-slides.md](clickeye-presentation-slides.md) | Marp 슬라이드 덱(프론트매터 미적용 — Marp 지시자) | current |

### reference — 정책/체크리스트
| 문서 | 목적 | status |
|------|------|--------|
| [license-model.md](license-model.md) | 라이선스 정책(프로젝트 단위, 티어) | current |
| [modernize-regression-checklist.md](modernize-regression-checklist.md) | Modernize 비침습 회귀 검증 R-1~R-7 | current |
| [hybrid-runner-headless-poc.md](hybrid-runner-headless-poc.md) | CE-297 SPIKE — 컨테이너 헤드리스 PoC + 동시성 실측 결정 메모 | current |

### page — UI 페이지 스펙
| 문서 | 목적 | status |
|------|------|--------|
| [pages/README.md](pages/README.md) | 페이지 스펙 SSoT 인덱스 + 연결 파일 맵 | current |

> 개별 페이지 스펙(33종: landing/auth/solutions/wizard 12단계/projects/onboarding/admin/settings/download)은 [pages/README.md](pages/README.md) 참조.

### archive (자동 생성, 매니페스트 관리 제외)
- `WeeklyWorkReport/` — `weekly-report` 스킬 산출 주간 보고
- `daily/` — `endwork` 스킬 산출 일일 TODO 아카이브
