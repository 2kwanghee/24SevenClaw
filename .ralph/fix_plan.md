# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[api] Rate Limiting 개선 + CORS 화이트리스트 + 입력값 검증 강화**
  > 요청사항: ## 목표

프로덕션 준비를 위한 보안 강화.

## 현황

* Rate Limit: IP 기반 100/60초 하드코딩, X-Forwarded-For 미지원
* CORS: allow_methods/headers가 와일드카드("\*")
* 입력값: agent/skill/pipeline ID 형식 검증 없음, PreviewRequest의 dict\[str, Any\] 미검증

## 작업 내용

* Rate Limit 설정을 config.py로 이동, 엔드포인트별 차등 (로그인 10/60초)
* X-Forwarded-For 헤더 검증 추가
* CORS allow_methods/headers 명시적 화이트리스트
* PreviewRequest/GenerateRequest에 agent_ids 형식 검증 추가

## 사이즈: S

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-08 | Rate Limiting + CORS + 입력값 검증 | ✅ 완료 | config 연동, X-Forwarded-For, 엔드포인트별 차등, CORS 화이트리스트, 카탈로그 ID 검증 |