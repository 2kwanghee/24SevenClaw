# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [ ] **[24S-142/P6] 문서 + E2E 검증**
  > 요청사항: ## 작업 내용

* `docs/pages/admin/pm-management.md`: MD 편집·composition·registry 연동 섹션 추가
* `docs/pages/admin/registry.md` 신규 — Agent/Skill/MCP 관리 가이드
* `docs/pages/solutions/wizard/step-04-pm-recommend.md`: PM → ZIP 배포 흐름 보강
* `docs/pages/download/pm-environment.md` 신규 — 플랫폼별 배포 파일 매핑
* E2E 시나리오: 관리자 로그인 → PM 생성 → composition 편집 → MD 직접편집 저장 → 위저드 PM 선택 → ZIP 다운 → 파일 내용 일치 검증
* 권한 회귀: 일반 user로 `/admin/registry/*`·`/admin/pm/*` 접근 시 AccessDenied

## 완료 기준

4개 문서 업데이트 완료 + E2E 시나리오 수동 통과

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|