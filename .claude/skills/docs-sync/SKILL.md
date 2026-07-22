---
name: docs-sync
description: 코드 변경 후 영향받는 docs/ 문서를 현행화한다. 유의미한 코드 변경(기능 구현, API/스키마 변경, 위저드/페이지 수정, 파이프라인 변경) 완료 시 자율적으로 호출하여 관련 문서의 프론트매터와 본문을 동기화한다.
---

# docs-sync — 문서 지속 현행화

코드가 바뀌면 관련 `docs/` 문서가 낡는다. 이 스킬은 **변경된 코드 → 영향 문서**를 역매핑해, 해당 문서의 프론트매터(`last_updated`/`status`)와 결정적 본문 구간을 현행화한다.

`log-work`(Linear 작업로그 + LoadMap 체크박스)와 **역할이 다르다**: 이 스킬은 `docs/` 본문·프론트매터 현행화만 담당하며 상호 호출하지 않는다.

## 언제 호출하나 (훅 강제 + 배치)

**강제 트리거**: `PostToolUse(Edit|Write)` 훅 `.claude/hooks/docs-sync-reminder.sh`가 코드 편집마다 자동 실행된다(LLM 0토큰, 순수 스크립트). 편집 파일이 어떤 문서의 `related:`와 매칭되면 그 문서를 `status: needs-revision`으로 플립하고 stderr로 리마인더를 띄운다.

```
[코드 편집]→훅(bash,0토큰): related 매칭 문서 needs-revision 표시 + 리마인더
   ↓ (편집 여러 번 — 매번 bash만)
[커밋 직전] 리마인더를 보고 이 스킬을 1회 호출 → 영향 문서 본문 현행화 + status: current 복귀
```

**호출 시점**: 리마인더가 떠 있으면(=needs-revision 문서가 있으면) **커밋 전에 1회** 호출한다. 편집마다가 아니라 **배치로 1회** — 토큰을 아끼는 핵심.

대상 영역(참고): clickeye-api→`agent-protocol.md`/페이지스펙, clickeye-web→`docs/pages/**`·`architecture-overview.md`·`product-guide.md`, scripts/→`pipeline-guide.md`·`clickeye-development-pipeline.md`, clickeye-infra→`aws-deployment-guide-ec2.md`.

스킬을 직접 호출하지 않아도, **현재 needs-revision 문서 목록**은 다음으로 확인한다:
```bash
grep -rl "^status: needs-revision" /mnt/c/workspace/ClickEye/docs --include=*.md
```
토글: `FLOWOPS_DOCS_SYNC=off`로 훅 비활성화 가능(회귀 0).

## 정규화 프론트매터 규약

모든 `docs/` 문서는 아래 프론트매터를 갖는다(상세: `docs/README.md`). 이 스킬은 이 규약을 강제한다.

```yaml
---
title: 문서 제목
category: architecture | guide | product | reference | page | presentation
status: current | needs-revision | draft | implemented
last_updated: YYYY-MM-DD
related: [추적 대상 코드/문서 경로]
route: ...     # 페이지 문서만(선택)
version: ...   # 선택
---
```

> Marp 덱(`clickeye-presentation-slides.md`)은 프론트매터 미적용(렌더 깨짐). 매니페스트에만 등재.

## 워크플로우

### 1. 변경 코드 수집
```bash
# 미커밋 변경 + 최근 커밋의 변경 파일
git -C /mnt/c/workspace/ClickEye status --porcelain
git -C /mnt/c/workspace/ClickEye diff --name-only HEAD~1 2>/dev/null
```

### 2. 영향 문서 역매핑
변경된 코드 경로를 각 문서의 `related` 프론트매터 및 `docs/pages/README.md`의 연결 파일 맵과 대조해 영향 문서를 추린다.
```bash
# related에 특정 경로를 추적하는 문서 찾기 (예: clickeye-api)
grep -rl "clickeye-api" /mnt/c/workspace/ClickEye/docs --include=*.md -l | xargs grep -l "^related:" 2>/dev/null
```
판단이 필요하면 변경 diff와 문서 본문을 읽어 실제 영향 여부를 확인한다(거짓 매칭 배제).

### 3. 현행화
영향 문서마다:
- **본문이 결정적으로 낡은 경우**(명령어/단계수/경로/스키마 등): 해당 구간을 정확히 수정하고 `status: current`, `last_updated: <오늘>` 갱신.
- **본문 갱신에 사람 판단이 필요한 경우**: `status: needs-revision`로만 표시하고 `last_updated`는 유지. 무엇을 고쳐야 하는지 한 줄 메모를 본문 상단 `> TODO(docs-sync):`로 남긴다.
- `related`에 새 추적 경로가 생겼으면 추가.

> 오늘 날짜는 환경/대화의 현재 날짜를 사용한다(예: 세션 컨텍스트의 currentDate). 임의 날짜 생성 금지.

### 4. 매니페스트 정합성
신규 문서를 만들었다면 `docs/README.md` 레지스트리 표에 한 줄 등재한다. 삭제했다면 제거한다.
"매니페스트에 없는 docs/ 문서 = 아카이브 후보" 규칙을 유지한다(`WeeklyWorkReport/`, `daily/` 자동 아카이브 제외).

### 5. 간결 보고
```
> docs-sync: N개 문서 현행화 (현행 M / needs-revision K)
> - <경로>: <한 줄 변경 요약>
```

## 규칙
- 한국어로 작성한다.
- 본문은 **변경된 부분만** 정확히 수정한다. 무관한 내용 재작성 금지.
- 프론트매터는 **필드 병합**(기존 값 임의 삭제 금지).
- 확신이 없으면 덮어쓰지 말고 `needs-revision` + TODO 메모로 남긴다.
