# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] 산출물 상태 머신 구현 (Draft→Released 6단계)**
  > 요청사항: ## 개요

보고서 §5 산출물 상태 관리 체계를 구현한다.

## 상태 흐름

```
Draft → Reviewed → Revised → Approved → In Development → Validated → Released
```

## 작업 내용

* contracts에 ArtifactStatus enum 정의
* ProjectConfig 또는 별도 Artifact 모델에 상태 필드 추가
* 상태 전이 API 엔드포인트 구현 (PUT /artifacts/{id}/transition)
* 전이 규칙 검증 (예: Draft→Reviewed만 허용, Draft→Approved 불가)
* 메타정보 자동 기록 (작성 AI, 리뷰 AI, 타임스탬프, 변경 이력)

## 대상 파일

* `24SevenClaw-api/app/models/`
* `24SevenClaw-contracts/protocol/`
* `24SevenClaw-api/app/api/v1/`

## 순서

2번 (Issue 1 이후) → 다른 기능의 기반 인프라

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-10 | 산출물 상태 머신 구현 | ✅ 완료 | contracts TS/Py + API 모델/스키마/서비스/라우터 + 테스트 11개 통과 |