# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [ ] **[수주:71e00c25] 리허설 저장소에 docs/INSTALL.md 신규 작성 + README 링크 1줄**
  > 요청사항: [CE-362](https://linear.app/flow-ops/issue/CE-362/관측-1단계-소비량실행-원장이-한-건도-안-쌓인다-인제스트메트릭-배선-점화)(관측 원장 점화) 라이브 검증 겸 딜리버리 티켓입니다. 대상은 고객 레포 `24seven-delivery-rehearsal`(워크스페이스 `71e00c25`, 조달 완료).

## 요구사항

**1.** `docs/INSTALL.md` **신규 작성** (한국어). 아래 3개 섹션을 이 순서로:

* `## 사전 요구사항` — `git` 만 기재(`git --version` 확인 명령 포함). 원문 근거가 없는 런타임(Node/Python 등)은 쓰지 않는다.
* `## 클론 방법` — `git clone https://github.com/2kwanghee/24seven-delivery-rehearsal.git` + `cd 24seven-delivery-rehearsal`
* `## 브랜치 규약` — 형식 `{type}/{module}/{TICKET-KEY}-{description}` 과 예시 1~2개. 단일 저장소이므로 `{module}` 생략 가능함을 1줄 명시.

**2.** `README.md` **에 링크 1줄 추가** — `- [설치 안내](docs/INSTALL.md)`. 기존 라인은 수정·삭제하지 않는다(순수 추가).

## 제외 범위

빌드·배포·환경변수·의존성 설치 안내, README 재구성, CI·템플릿 신설. 프론트매터는 대상 저장소에 그 관례가 없으므로 만들지 않는다.

## 수용 기준

* `docs/INSTALL.md` 가 존재하고 3개 섹션이 순서대로 있다
* `README.md` 변경이 순수 추가다(`git diff --numstat` 에서 삭제 0)
* 추가된 상대경로가 실제 파일을 가리킨다
* 전부 한국어

## 관측 검증 (운영자 확인용, 에이전트 작업 아님)

완주 후 `llm_usage_ledger` 에 이 티켓의 레코드가 `project_id=76e9af30-196f-4694-8f63-36b6e053f25c` 와 함께 들어와야 한다.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|