---
title: ClickEye Home
category: moc
---

# 🏠 ClickEye Home

AI 개발 자동화 솔루션 빌더 플랫폼. 이 노트가 전체 지식베이스의 진입점(MOC)이다.
그래프 뷰(`Ctrl/Cmd+G`)로 문서 간 관계를 시각적으로 탐색할 수 있다.

## 🧱 모듈 (6개 레포)
| 모듈 | 역할 | MOC |
|------|------|-----|
| 🎨 Web | Next.js 15 위저드 UI | [[모듈/web\|web]] |
| 🛠️ API | FastAPI 카탈로그+ZIP | [[모듈/api\|api]] |
| 🤖 Agent | 고객 서버 데몬 | [[모듈/agent\|agent]] |
| 📦 Infra | Docker/YAML 배포 | [[모듈/infra\|infra]] |
| 🧩 Contracts | 공유 타입/프로토콜 | [[모듈/contracts\|contracts]] |
| ⌨️ CLI | `@clickeye/cli` | [[모듈/cli\|cli]] |

## 🔭 허브
- [[🔄 프로세스맵|🔄 프로세스 맵]] — 위저드·하네스·PM라우팅·거버넌스·파이프라인 흐름
- [[📊 문서현황|📊 문서 현황 대시보드]] — status/category 실시간 집계

## 📑 핵심 문서
- [[docs/README|문서 매니페스트 (정식 레지스트리·SSoT)]]
- [[docs/architecture-overview|아키텍처 개요]]
- [[docs/agent-protocol|에이전트 통신 프로토콜]]
- [[docs/pipeline-guide|자동화 파이프라인 가이드]]
- [[docs/cli-guide|CLI 가이드]]
- [[docs/license-model|라이센스 모델]]
- [[docs/comparison|유사 플랫폼 비교]]
- [[LoadMap_v3|마스터 로드맵]]
- [[CLAUDE|루트 CLAUDE.md (개발 가이드)]]

## 🚨 지금 손봐야 할 문서
```dataview
LIST status
FROM "docs"
WHERE status = "needs-revision"
SORT file.name ASC
```

## 🗂️ 카테고리별 문서 한눈에
```dataview
TABLE rows.file.link AS 문서
FROM "docs"
WHERE category AND status != null
GROUP BY category
```

---
> ℹ️ 이 `obsidian/` 폴더와 `.obsidian/` 설정은 git에서 제외(개인용)된다. Dataview 블록이 코드로 보이면 커뮤니티 플러그인에서 **Dataview**를 설치하라.
