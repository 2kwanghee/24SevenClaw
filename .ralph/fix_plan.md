# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] pm_profiles 라우터 구현**
  > 요청사항: app/api/v1/pm_profiles.py 신규 작성. 5개 엔드포인트.

* GET /pm-profiles (목록, domain/specialty 필터)
* GET /pm-profiles/{id} (상세 + metrics)
* GET /pm-profiles/{id}/composition (도구 구성)
* POST /pm-profiles/{id}/ratings (평가 등록)
* GET /pm-profiles/{id}/ratings (평가 목록)

router.py에 등록.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] pm_profiles 라우터 구현 | ✅ 완료 | 5개 엔드포인트 구현, router.py 등록 완료 |