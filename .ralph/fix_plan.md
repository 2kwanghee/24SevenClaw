# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] /registry 데드 링크 + 중복 admin/registry 탭 페이지 제거**
  > 요청사항: ## 목적

사이드바의 에이전트/스킬/MCP 3개 메뉴가 현재 404 데드 링크. UX 신뢰도 저하 방지를 위해 제거하고 중복 레거시 탭 페이지도 함께 정리.

## 작업 범위

* `src/app/(dashboard)/layout.tsx` navItems에서 `/registry/agents`, `/registry/skills`, `/registry/mcps` 3개 엔트리 제거
* 빈 디렉토리 `src/app/(dashboard)/registry/{agents,skills,mcps}/` 삭제
* 중복 레거시 페이지 `src/app/(dashboard)/admin/registry/page.tsx` 삭제 (사이드바에서 링크 없고 개별 페이지와 기능 동일)
* 관리자 `/admin/registry/agents|skills|mcps` 3개 메뉴는 그대로 유지

## 완료 기준

* 사이드바 클릭 시 404 발생 없음
* `npm run typecheck && npm run build` 통과

## 선행 조건

없음 (독립적으로 배포 가능)

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | /registry 데드 링크 제거 + admin/registry/page.tsx 삭제 | ✅ 완료 | pre-existing KPI 타입 누락도 함께 수정 |