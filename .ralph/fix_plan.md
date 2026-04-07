# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[engine] CLI 생성 엔진 웹 이식 (generators + templates)**
  > 요청사항: ## 목표

CLI의 생성 엔진을 웹 서버용으로 이식 (파일시스템 → 메모리 버퍼)

## 작업 내용

* lib/engine/generators/ 디렉토리 생성
* CLI generators/\*.ts → 웹용 이식:
  * agent.ts — 에이전트 .md 생성 (문자열 반환)
  * skill.ts — 스킬 .md 생성 (문자열 반환)
  * hook.ts — Hook .sh 생성 (문자열 반환)
  * settings.ts — settings.json 생성 (객체 반환)
  * claude-md.ts — [CLAUDE.md](<http://CLAUDE.md>) 생성 (문자열 반환)
* 파일시스템 출력 → Map<string, string> 반환으로 변환
* templates/\*.hbs 복사
* lib/engine/catalog/ — JSON 파일 배치

## 핵심 변경: fs.writeFile() → Map.set(path, content)

## 사이즈: L

## 일정: 04-12 \~ 04-13

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-07 | [engine] CLI 생성 엔진 웹 이식 | ✅ | generators 6개 + templates 13개 + catalog 3개 이식, Map<string,string> 반환 |