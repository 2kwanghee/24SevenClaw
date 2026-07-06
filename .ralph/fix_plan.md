# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [ ] **[api/zip] 요구사항→에이전트 매핑 레지스트리 + DB 마이그레이션 에이전트 팩**
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