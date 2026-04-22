# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] 프로젝트 finalize 시 Linear/Notion 초기 태스크 자동 등록**
  > 요청사항: ## 작업 목적

`POST /prototype-sessions/{session_id}/finalize` 호출로 프로젝트가 최초 생성되면, 위저드에서 선택한 Linear 또는 Notion에 **"프로젝트 생성 완료"** 태스크를 자동으로 등록한다. 이 태스크는 AI Team이 첫 연동이 정상 동작함을 사용자가 확인할 수 있는 기준점이 된다.

## 구현 명세

### finalize 엔드포인트 수정 위치

`app/api/v1/prototype_sessions.py` → `finalize_session` 함수 마지막 단계에서 실행

### 처리 순서 (finalize 기존 로직 이후 추가)

```
1. 기존: 세션 검증 + Project DB 생성
2. [신규] 위저드 데이터에서 선택된 스킬 목록 확인
3. [신규] Linear 선택 시:
   - wizard_data에서 LINEAR_API_KEY, LINEAR_TEAM_ID 추출
   - linear_service.create_issue() 호출 → 이슈 생성
4. [신규] Notion 선택 시:
   - wizard_data에서 NOTION_API_KEY, NOTION_DATABASE_ID 추출
   - notion_service.create_page() 호출 → 페이지 생성
5. [신규] 생성된 이슈/페이지 URL을 project에 저장 (initial_task_url 컬럼)
6. 기존: project_id 반환 (실패해도 프로젝트 생성은 성공으로 처리)
```

### Linear 초기 이슈 내용

```
제목: 🚀 ClickEye 프로젝트 생성 완료 — {project_name}
설명:
  ClickEye 위저드를 통해 AI 개발 자동화 솔루션이 성공적으로 구성되었습니다.

  ## 다음 단계
  1. ZIP 파일 다운로드
  2. 압축 해제 후 디렉토리 진입
  3. Claude Code에서 /ClickEyeStart 실행

  ## 연동 정보
  - 생성 일시: {created_at}
  - 플랫폼: {platform}
  - 에이전트: {agent_list}
```

### Notion 초기 페이지 내용

동일한 내용으로 Notion Page 생성 (Title 프로퍼티 + 본문 블록)

### 실패 처리

* Linear/Notion 초기 이슈 생성 실패는 **경고 로그만 남기고 finalize 전체를 실패시키지 않는다**
* failure-safe: 프로젝트 생성 자체는 무조건 성공으로 응답

### DB 스키마 변경

`projects` 테이블에 컬럼 추가:

```sql
ALTER TABLE projects ADD COLUMN initial_task_url VARCHAR(500);
```

→ Alembic 마이그레이션 필요 (019_add_initial_task_url.py)

## 참조 파일

* `app/api/v1/prototype_sessions.py` — finalize_session 함수
* `app/services/linear_service.py` — create_issues 함수
* `app/services/notion_service.py` — 신규 생성 필요 ([24S-211](https://linear.app/flow-ops/issue/24S-211/api-notion-api-key-유효성-검증-엔드포인트-구현)과 연계)
* `app/models/project.py` — initial_task_url 컬럼 추가

## 완료 기준

- finalize 완료 후 Linear에 이슈 자동 생성 확인 (실제 Linear 워크스페이스에서 확인)
- finalize 완료 후 Notion에 페이지 자동 생성 확인
- Linear/Notion 생성 실패 시에도 프로젝트 생성은 정상 완료
- initial_task_url이 DB에 저장됨
- Alembic 마이그레이션 019 적용 완료

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-22 | [api] finalize 시 Linear/Notion 초기 태스크 자동 등록 | ✅ 완료 | 019 마이그레이션, FinalizeRequest 확장, _register_initial_tasks 메서드, 테스트 5개 |