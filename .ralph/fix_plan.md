# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[api] PM 시드 데이터 로딩 스크립트**
  > 요청사항: pm_profiles.json + pm_compositions.json → DB 초기 로딩 스크립트.

* scripts/seed_pm_data.py
* 이미 존재하면 skip (멱등성)
* pm_metrics 초기값 함께 생성 (모두 0)
* pytest fixture로도 활용 가능하도록 구조화

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] PM 시드 데이터 로딩 스크립트 | ✅ 완료 | data/pm_compositions.json, scripts/seed_pm_data.py 생성 |