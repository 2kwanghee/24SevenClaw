# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P3: 기능 요구사항

- [ ] **[infra] Docker 헬스체크 + 프로덕션 Compose 작성**
  > 요청사항: ## 목표

Docker 컨테이너의 프로덕션 준비 수준을 높인다.

## 현황

* Dockerfile.api/web/agent에 HEALTHCHECK 미설정
* docker-compose.prod.yml 부재
* Dockerfile.web이 pnpm-lock.yaml 기대하지만 실제는 npm 사용

## 작업 내용

* Dockerfile.api: HEALTHCHECK /api/v1/health
* [Dockerfile.web](<http://Dockerfile.web>): HEALTHCHECK localhost:3000
* [Dockerfile.web](<http://Dockerfile.web>): pnpm → npm 정합성 수정
* docker-compose.prod.yml 작성 (환경변수 외부 주입, 리소스 제한)

## 사이즈: S

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|