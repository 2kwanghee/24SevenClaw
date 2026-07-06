# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api/zip] 요구사항→에이전트 매핑 레지스트리 + DB 마이그레이션 에이전트 팩**
  > 요청사항: ## 목표

요구사항 태그(Phase 2 산출)에 따라 **필요한 에이전트·스킬·태스크 템플릿을 자동 선택**하는 레지스트리를 구축한다. 1호 수직 팩으로 **DB 마이그레이션 팩**을 구현한다. (R4)

## As-Is 근거

* 현재 시나리오 분기는 시스템 프롬프트 차이뿐, DB/인프라 등 요구사항 유형별 전용 처리 없음
* outdated 감지도 python/node 레지스트리만 지원

## 작업 내용

1. **매핑 레지스트리** (YAML/JSON, 카탈로그 DB 연동):
   * `요구사항 태그 → {agents[], skills[], task_templates[], preflight_checks[]}`
   * 예: `db_migrate(mariadb→postgresql)` → db-migrator 에이전트 + 스키마변환/데이터이관/검증 태스크 템플릿 + 백업·롤백 preflight 항목
2. **DB 마이그레이션 팩** (MariaDB / MySQL / MSSQL / Oracle / PostgreSQL 조합):
   * 소스→타깃 조합별 태스크 시퀀스: ①스키마 덤프·타입 매핑 변환 → ②DDL 생성·적용 → ③데이터 이관(배치/검증 쿼리) → ④앱 코드의 SQL/드라이버/ORM 설정 수정 → ⑤정합성 검증(행수/체크섬) → ⑥롤백 스크립트
   * 조합별 주의사항(예: MSSQL T-SQL→PostgreSQL 함수 차이, AUTO_INCREMENT→IDENTITY) 지식을 에이전트 프롬프트에 내장
3. as-is 스캔에 DB 감지 추가 (드라이버 의존성·connection string·ORM 설정 기반)
4. Phase 4 계획 생성이 레지스트리를 참조해 태스크에 `assigned_agent` 자동 지정
5. 이후 수직 팩(프레임워크 업그레이드, 컨테이너 리플랫폼)을 같은 레지스트리 형식으로 추가 가능한 구조

## 완료 조건

* mariadb→postgresql 샘플 요구사항으로 계획~ZIP까지 db-migrator 팩이 선택·베이크되는 E2E 테스트
* 레지스트리 스키마 검증 테스트

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-07-06 | [api/zip] 요구사항→에이전트 매핑 레지스트리 + DB 마이그레이션 팩 | 완료(범위 축소) | Phase 2/3/4(CE-285~288)가 형제 브랜치에 미병합 상태라, 살아있는 7-step 파이프라인 위에 자기완결적으로 구현. `agent_registry.py`(레지스트리 로더+태그도출+팩조회) + `agent_pack_registry.json`(5개 태그, db_migrate는 mariadb/mysql/mssql/oracle→postgresql 4개 콤보+generic) 신규. `manifest.py`에 DB 드라이버 키워드 감지(`framework_signals["db_type"]`) 추가 — connection string/ORM 설정 스캔은 별도 소스 스캔 인프라가 필요해 이번 범위에서 제외(후속 과제). `plan_builder.build_plan()`에 `requirement_tags`/`source_db`/`target_db` optional 인자 + `assigned_agent`(migrate 카테고리만) 추가 — DB 컬럼이 아닌 plan.json 필드로만 저장(Alembic 마이그레이션 없음, CE-287 DAG/wave 병합 전 임시). `zip_builder.py`에 태그 기반 `.claude/agents/*.md`/`.claude/skills/*.md` 번들 + README에 preflight 체크리스트 섹션 추가. 신규 테스트 3개 파일 + 기존 3개 파일 보강, 전체 75+ 테스트 통과, ruff/mypy 클린(내 변경 파일 기준). **후속 과제**: CE-285(Phase2 tags)/CE-286(Phase3 tobe)/CE-287(Phase4 DAG+assigned_agent 컬럼)/CE-288(preflight)/CE-289(zip 로컬실행팩) 병합 시 `derive_requirement_tags()`를 StackDescriptor 기반 Phase2 로직과 재조정하고 `assigned_agent` 저장 위치(plan.json vs DB 컬럼)를 통합 필요. |