---
title: API 모듈 MOC
category: moc
module: clickeye-api
---

# 🛠️ clickeye-api (FastAPI · :8000)

백엔드 API — 카탈로그 + ZIP 생성 엔진.

## 진입점
- [[clickeye-api/CLAUDE|🧭 모듈 CLAUDE.md]]
- [[.claude/agents/api-agent|백엔드 API 개발 가이드]]

## 관련 문서
- [[docs/architecture-overview|아키텍처 개요]]
- [[docs/agent-protocol|에이전트 통신 프로토콜]]
- [[docs/aws-deployment-guide-ec2|AWS EC2 배포 가이드]]

## 이 모듈을 추적하는 문서 (related 역링크)
```dataview
TABLE status, category, last_updated
FROM "docs"
WHERE length(filter(related, (r) => startswith(r, "clickeye-api"))) > 0
SORT status ASC, last_updated DESC
```

[[🏠 ClickEye Home|← Home]]
