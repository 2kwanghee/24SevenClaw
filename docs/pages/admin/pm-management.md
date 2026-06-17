---
route: /admin/pm
title: PM 관리
category: page
status: implemented
version: 1.0.0
roles: superadmin, admin
last_updated: 2026-04-17
---

## 목적

관리자가 AI-팀 PM 프로필과 그 구성 컴포넌트(Agent/Skill/Hook/MCP Server/Plugin)를 GUI로 CRUD할 수 있는 전용 화면이다. 이전에는 DB에 직접 접근해야 했으나, 이 UI로 대체된다.

---

## 접근 권한

`superadmin` 또는 `admin` 역할만 메뉴가 표시되고 접근 가능하다. 하위 페이지는 모두 `RoleGuard`와 백엔드 `require_permission("pm:manage")` 이중으로 보호된다.

---

## 페이지 구성

### PM 목록 (`/admin/pm`)

- 전체 PM 프로필 테이블 (이름·도메인·슬러그·활성 여부·생성일)
- 오른쪽 상단 **"새 PM 생성"** 버튼 → 인라인 다이얼로그 (이름·슬러그 입력)
- 행 클릭 → PM 편집 페이지로 이동
- 행 삭제 버튼 → confirm 후 삭제 (연결된 Composition도 CASCADE 삭제)

### PM 편집 (`/admin/pm/[id]`)

PM 프로필의 상세 정보를 수정한다.

| 섹션 | 필드 |
|------|------|
| 기본 정보 | 이름, 아바타 URL, 직함, 도메인, 연차, 언어, 활성 여부 |
| 태그 | 선호 솔루션 타입, 기술 스택 태그, 산업 태그 |
| 상세 소개 | 짧은 설명(description), 긴 소개(bio_long, 마크다운 허용) |
| 성격/특성 | specialties (배열), personality (JSON) |

오른쪽 상단 **"구성 관리"** 링크로 `/admin/pm/[id]/composition`으로 이동.

### Composition 관리 (`/admin/pm/[id]/composition`)

PM에 연결된 컴포넌트(에이전트·스킬 등)를 관리한다.

| 컬럼 | 설명 |
|------|------|
| 순서 (`display_order`) | 낮을수록 먼저 표시 |
| 타입 | agent / skill / hook / mcp_server / plugin |
| Slug | 컴포넌트 고유 식별자 |
| 이름 | 화면 표시용 이름 |
| 필수 | 필수 컴포넌트 여부 |

**"컴포넌트 추가"** 버튼으로 폼 패널을 열고 타입·Slug·이름·순서·필수 여부를 입력 후 저장. 삭제 버튼은 confirm 후 실행.

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/v1/pm-profiles/` | PM 목록 (일반 사용자도 접근 가능) |
| `POST` | `/api/v1/pm-profiles/` | PM 생성 (`pm:manage` 필요) |
| `PUT` | `/api/v1/pm-profiles/{id}` | PM 수정 (`pm:manage` 필요) |
| `DELETE` | `/api/v1/pm-profiles/{id}` | PM 삭제 (`pm:manage` 필요) |
| `POST` | `/api/v1/pm-profiles/{id}/composition` | Composition 추가 |
| `PUT` | `/api/v1/pm-profiles/{id}/composition/{cid}` | Composition 수정 |
| `DELETE` | `/api/v1/pm-profiles/{id}/composition/{cid}` | Composition 삭제 |

---

## MD 직접 편집 (`/admin/pm/[id]` → "PM 마크다운 편집" 탭)

PM의 `pm_markdown` 필드는 ZIP에 그대로 주입되는 핵심 파일이다. 관리자는 GUI 폼 외에도 **마크다운 에디터** 탭에서 원문을 직접 수정할 수 있다.

```
┌─────────────────────────────────────────────────────────┐
│  [기본 정보]  [PM 마크다운 편집]  [구성 관리]            │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────┐  │
│  │  # PM 이름                                        │  │
│  │  ## 역할 & 전문 분야                               │  │
│  │  - nextjs, fastapi, postgres                      │  │
│  │  ## 작업 스타일                                    │  │
│  │  ...                                              │  │
│  └───────────────────────────────────────────────────┘  │
│  [미리보기] [저장]                                       │
└─────────────────────────────────────────────────────────┘
```

- **라이브 미리보기**: 에디터 좌측 작성 / 우측 렌더링 분할 뷰 (Split Mode)
- **자동 저장**: 3초 debounce 후 `PATCH /api/v1/pm-profiles/{id}` 호출 (`pm_markdown` 필드만)
- **변경 감지**: 편집 중 다른 탭 이동 시 "저장되지 않은 변경사항" confirm 다이얼로그 표시
- ZIP 생성 시 이 마크다운 원문이 플랫폼별 경로에 주입된다 (`docs/pages/download/pm-environment.md` 참조)

---

## Composition → Registry 연동

Composition 관리 화면에서 컴포넌트를 추가할 때 **Registry에서 직접 검색**하여 선택할 수 있다.

```
[컴포넌트 추가] 클릭
  → 타입 선택 (agent / skill / mcp_server)
  → 검색창: 이름 또는 Slug 입력
      → Registry API 조회: /admin/registry/{type}s?q={keyword}
      → 결과 목록에서 선택 (Slug 자동 입력)
  → 순서·필수 여부 입력 후 저장
```

- **Registry 미등록 컴포넌트**: Slug를 직접 입력하는 수동 모드도 지원
- **Registry 연결 배지**: 검색으로 연결된 컴포넌트는 "Registry 연결됨" 배지 표시
- **일관성 보장**: Registry에서 컴포넌트 삭제 시 연결된 Composition 항목에 경고 표시 (CASCADE 삭제 아님)

---

## Claude 추천 품질을 높이기 위한 권장 작업

PM 프로필의 `bio_long`, `tech_stack_tags`, `industry_tags`, `preferred_solution_types` 값이 풍부할수록 Claude의 추천 정확도가 높아진다. 신규 PM 등록 시 다음 항목을 채울 것을 권장한다.

- **bio_long**: 100자 이상의 상세 소개 (마크다운 허용)
- **pm_markdown**: ZIP에 주입될 실제 PM 지침 파일 원문 (MD 직접 편집 탭에서 관리)
- **tech_stack_tags**: `["nextjs","fastapi","postgres"]` 형태
- **industry_tags**: `["fintech","ecommerce","saas"]` 형태
- **preferred_solution_types**: `["rest-api","fullstack","saas"]` 형태
- **specialties**: PM이 특히 잘 다루는 역량 항목
