# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[engine] 멀티플랫폼 지원 기초 (Claude Code 완전 구현)**
  > 요청사항: ## 목표

멀티플랫폼 지원 아키텍처 설계 + Claude Code 플랫폼 완전 구현

## 작업 내용

* lib/engine/platforms/ 디렉토리 구조 설계
* 플랫폼 인터페이스 정의 (PlatformAdapter)
  * getConfigDir(): 설정 디렉토리 경로
  * getAgentDir(): 에이전트 파일 경로
  * getSettingsFile(): 설정 파일 경로
  * generateFiles(): 플랫폼별 파일 생성
* Claude Code 어댑터 완전 구현 (기존 CLI 로직 재활용)
  * .claude/ 구조, settings.json, agents/\*.md
* 플랫폼별 디렉토리 매핑 정의

## 사이즈: M

## 일정: 04-12 \~ 04-13

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|