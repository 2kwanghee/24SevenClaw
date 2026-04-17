---
route: /admin/pm
title: PM 관리
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

## Claude 추천 품질을 높이기 위한 권장 작업

PM 프로필의 `bio_long`, `tech_stack_tags`, `industry_tags`, `preferred_solution_types` 값이 풍부할수록 Claude의 추천 정확도가 높아진다. 신규 PM 등록 시 다음 항목을 채울 것을 권장한다.

- **bio_long**: 100자 이상의 상세 소개 (마크다운 허용)
- **tech_stack_tags**: `["nextjs","fastapi","postgres"]` 형태
- **industry_tags**: `["fintech","ecommerce","saas"]` 형태
- **preferred_solution_types**: `["rest-api","fullstack","saas"]` 형태
- **specialties**: PM이 특히 잘 다루는 역량 항목
