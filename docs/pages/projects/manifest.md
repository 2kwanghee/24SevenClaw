---
title: DeliveryManifest (프로젝트 탭)
category: page
status: draft
version: 0.1.0
last_updated: 2026-07-29
route: /projects/[projectId]/manifest
pages:
  - src/app/(dashboard)/projects/[projectId]/manifest/page.tsx  # 후보 — 미생성
components:
  - src/components/projects/manifest/manifest-header.tsx        # 후보 — 미생성
  - src/components/projects/manifest/manifest-spec-panel.tsx    # 후보 — 미생성
  - src/components/projects/manifest/env-schema-table.tsx       # 후보 — 미생성
  - src/components/projects/manifest/validation-checklist.tsx   # 후보 — 미생성
related:
  - migration.md
  - docs/wireframes/multiproject-delivery.html
  - clickeye-api/app/schemas/intake.py
---

> **구현 금지.** `migration.md` Stage 0.5 산출물. Stage 1(Manifest·Human Gate) 승인 전 코드 생성 금지.

## 목적

CMS가 보낸 런타임·배포 명세를 **읽기 전용**으로 보여주고, 검증 결과와 CONTROL 충돌을
실행 전에 드러낸다. 무엇을 어떤 환경에서 빌드·실행·검증할지가 이 화면의 전부다.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ 헤더 — 프로젝트명 · [v3 활성] · 버전 칩(v3/v2/v1) · provenance │
├──────────────────────────────────┬──────────────────────────┤
│ 명세                              │ 검증 결과                 │
│  source (repo·ref·subdir)        │  ✓ JSON Schema           │
│  stack · 개발/배포 OS·arch        │  ✓ Secret 미포함          │
│  databases (종류·버전)            │  ✓ 저장소 URL 허용목록     │
│  commands (argv · shell:false)   │  ✗ CONTROL 충돌 1건       │
│                                  │  → fail-closed 안내       │
│ 환경변수 스키마                    ├──────────────────────────┤
│  이름│필수│Secret│참조             │ 인수 테스트 명세 (I-09)   │
│  (값 열은 존재하지 않음)           ├──────────────────────────┤
│                                  │ 책임 분리 주석 (§7)       │
└──────────────────────────────────┴──────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 활성 Manifest 확인**
1. `/projects/p-042/manifest` 진입
2. 활성 버전(v3)과 provenance(작성 주체·수신 시각·hash) 확인
3. 명세 섹션과 검증 체크리스트 렌더링

**시나리오 2: CONTROL 충돌**
1. Manifest가 `shell: true`를 요구하고 CONTROL이 금지
2. 해당 명령을 **거부**로 표시하고 실행 대상에서 제외
3. 해소 경로 안내 — CMS 재제출(argv 배열) 또는 별도 승인 단계

**시나리오 3: Manifest 없는 기존 프로젝트**
1. 탭 자체를 표시하지 않거나 "Manifest 미제출" 빈 상태
2. 기존 lifecycle은 그대로 동작 (§23 수용 기준)

---

## 기능 요구사항

### 필수 기능
- [ ] 버전 목록 + 활성 버전 표시 (v1 검증 실패 이력 포함)
- [ ] provenance — 작성 주체·schema_version·수신 시각·hash
- [ ] 명세 섹션 — source / stack / development / deploy / databases / commands / acceptance
- [ ] **commands는 argv 배열과 working_dir로 표시**. shell 문자열로 렌더링하지 않음 (§6.1)
- [ ] 환경변수 스키마 표 — 이름·필수·Secret·참조. **값 열을 만들지 않음**
- [ ] 검증 체크리스트 — Schema / Secret 미포함 / 저장소 URL / 알 수 없는 필드 / CONTROL 충돌 / Runner 적합성
- [ ] CONTROL 충돌 시 fail-closed 결과와 사유 표시 (§7)
- [ ] 읽기 전용 — 웹에서 Manifest를 편집하지 않음 (소유권은 CMS)

### 선택/개선 사항
- [ ] 버전 간 diff 뷰
- [ ] README 분석 결과를 **제안**으로만 표시 (실행 버튼 금지, §14)

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `versions` | `ManifestVersion[]` | `GET .../manifests` | 버전 칩 |
| `active` | `ManifestDetail` | `GET .../manifests/active` | 명세 섹션 |
| `validation` | `ValidationResult` | 동일 응답 | 체크리스트 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/projects/{id}/manifests` | 진입 | 버전 목록 (후보) |
| `GET` | `/api/v1/projects/{id}/manifests/active` | 진입 | 활성 명세 + 검증 (후보) |

Manifest 수신 경로(Intake payload의 `target.delivery_manifest` vs 별도 PUT)는 **I-02 미확정**이다.
이 화면은 두 경로 모두에서 동일하게 동작해야 한다.

---

## 접근성 / 반응형

- [ ] WCAG 2.1 AA
- [ ] 검증 결과는 아이콘(✓/✗) + 텍스트 병기
- [ ] `commands` 블록은 `overflow-x: auto`, `white-space: pre`
- [ ] 긴 참조 문자열 `overflow-wrap: anywhere`

---

## 구현 노트

- 이 화면과 CONTROL YAML 화면을 **합치지 않는다.** 정책(CONTROL)과 런타임 명세(Manifest)의
  책임 분리가 §7의 핵심이며, 한 화면에 섞으면 충돌 시 어느 쪽이 이겼는지 추적할 수 없다.
- `Project.settings`에 명세 전체를 저장하는 방식은 피한다 — 화면은 별도 Manifest 레코드 조회를
  전제한다 (§6.1 저장 전략).
- Secret 값을 표시하는 요소를 절대 추가하지 않는다. 리뷰 시 첫 확인 항목.
