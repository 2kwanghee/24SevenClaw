---
title: Agent 모듈 MOC
category: moc
module: clickeye-agent
---

# 🤖 clickeye-agent (Python)

고객 서버 에이전트 데몬.

## 진입점
- [[clickeye-agent/CLAUDE|🧭 모듈 CLAUDE.md]]
- [[.claude/agents/agent-agent|고객 서버 에이전트 개발 가이드]]

## 관련 문서
- [[docs/agent-protocol|에이전트 통신 프로토콜]]
- [[docs/architecture-overview|아키텍처 개요]]

## 이 모듈을 추적하는 문서 (related 역링크)
```dataview
TABLE status, category, last_updated
FROM "docs"
WHERE length(filter(related, (r) => startswith(r, "clickeye-agent"))) > 0
SORT status ASC, last_updated DESC
```

[[🏠 ClickEye Home|← Home]]
