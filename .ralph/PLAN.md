# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[web] 중앙 계약 관리 UI**
  > 요청사항: ## 개요

중앙 계약 관리 어드민 + 프로젝트별 UI 구현.

## 선행 조건

* \[api\] 중앙 계약 API + \[web\] RBAC UI 완료 필수

## 범위

### 새 페이지

* (dashboard)/admin/contracts/page.tsx: 계약 목록
* (dashboard)/admin/contracts/\[id\]/page.tsx: 상세 + JSON 에디터 + 감사 로그
* (dashboard)/projects/\[projectId\]/contracts/page.tsx: 프로젝트별 뷰 (잠금=회색, 수정가능=파란색)

### 새 컴포넌트

* components/contracts/contract-viewer.tsx
* components/contracts/override-editor.tsx
* components/contracts/contract-audit-table.tsx

## 완료 조건

- 계약 CRUD UI 동작
- 오버라이드 편집 동작
- 잠금 필드 시각적 구분
- 동기화 버튼 동작

## 크기: M

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|