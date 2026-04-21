# Solution Wizard v2 — PRD (Product Requirements Document)

> **문서 버전**: 1.0  
> **작성일**: 2026-04-16  
> **상태**: Draft  
> **Linear Epic**: 24S-89 ~ 24S-124  

---

## 1. 개요

### 1.1 배경
현재 ClickEye 플랫폼은 7-Step 수동 위저드로 솔루션을 설계한다. 사용자가 직접 에이전트, 스킬, 파이프라인, 플랫폼을 선택해야 하며, 이 과정은 AI 자동화 플랫폼의 비전과 괴리가 있다.

### 1.2 목표
**AI 주도 프로토타입 생성 + AI PM 매칭** 기반의 새 위저드로 전환한다.

- 사용자는 회사 정보와 원하는 솔루션을 **자연어로 설명**하면 된다
- AI가 자동으로 **프로토타입 3개를 생성**하고 사용자가 선택한다
- AI가 적합한 **PM(Project Manager) 에이전트를 추천**하고 사용자가 확인한다
- 최종 확인 후 프로젝트가 생성된다

### 1.3 핵심 지표
| 지표 | 현재 (v1) | 목표 (v2) |
|------|-----------|-----------|
| 위저드 완료율 | - | ≥70% |
| 위저드 소요 시간 | 10~15분 | ≤5분 |
| 프로토타입 만족도 | N/A | ≥4.0/5.0 |
| PM 매칭 정확도 | N/A | ≥80% |

---

## 2. 사용자 플로우

### 2.1 위저드 v2 — 7 Step

```
Step 1: 회사 정보 + 자연어 입력
  ↓
Step 2: 프로토타입 생성 (로딩)
  ↓
Step 3: 프로토타입 선택
  ↓
Step 4: PM 추천
  ↓
Step 5: PM 선택
  ↓
Step 6: PM 구성 확인
  ↓
Step 7: 최종 확인 + 프로젝트 생성
```

### 2.2 Step 상세

#### Step 1: 회사 정보 + 자연어 입력
- **입력 필드**:
  - 회사명 (필수)
  - 회사 규모: solo / small / medium / enterprise
  - 업종: IT / 금융 / 커머스 / 헬스케어 / 교육 / 기타
  - 주요 제품/서비스 (텍스트)
  - 사업 유형: B2B / B2C / Internal
  - **자연어 설명** (필수, textarea): "어떤 솔루션을 만들고 싶으신가요?"
  - 기술 스택 (태그 입력, 선택)
- **제출 시**: API 호출 → prototype_session 생성 → Step 2로 이동

#### Step 2: 프로토타입 생성 (로딩 UI)
- Claude API를 통해 자연어 분석 → 프로토타입 3개 생성
- **로딩 UI**: 진행 상태 표시 (분석 중 → 구조 설계 중 → 프로토타입 생성 중)
- 예상 소요 시간: 15~30초
- 실패 시: 재시도 버튼 + 에러 메시지

#### Step 3: 프로토타입 선택
- 3개 프로토타입 카드 표시
- 각 카드에 포함되는 정보:
  - 프로토타입 이름
  - 솔루션 유형 (SaaS, REST API, 풀스택 등)
  - 기술 스택 구성
  - 에이전트 구성 (추천 에이전트 목록)
  - 스킬 구성 (추천 스킬 목록)
  - 파이프라인 구성
  - AI 추천 사유 (reasoning)
- 사용자가 하나를 선택하면 Step 4로 이동

#### Step 4: PM 추천
- 선택한 프로토타입 기반으로 적합한 PM 에이전트 추천
- PM 프로필 카드 3~5개 표시:
  - PM 이름 + 아바타
  - 전문 분야 (백엔드, 프론트엔드, DevOps 등)
  - 경력 요약
  - 매칭 점수 (0~100)
  - 추천 사유
- 추천 순서: 매칭 점수 내림차순

#### Step 5: PM 선택
- PM 프로필 상세 보기 지원
- 단일 PM 또는 복수 PM 선택 가능
- 선택 후 Step 6으로 이동

#### Step 6: PM 구성 확인
- 선택한 PM의 역할 배정 확인
- PM별 담당 영역 표시:
  - 담당 에이전트
  - 담당 스킬/파이프라인
  - 실행 순서
- 수정 가능 (PM 재배정, 역할 변경)

#### Step 7: 최종 확인 + 프로젝트 생성
- 전체 설정 요약:
  - 회사 정보
  - 선택한 프로토타입
  - PM 구성
  - 예상 산출물
- "프로젝트 생성" 버튼 → 프로젝트 생성 + ZIP 다운로드 준비
- 생성 완료 후 프로젝트 대시보드로 이동

---

## 3. 백엔드 아키텍처

### 3.1 신규 DB 모델

#### prototype_sessions
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| organization_id | UUID | FK → organizations |
| user_id | UUID | FK → users |
| user_input | JSONB | 사용자 입력 (자연어 포함) |
| status | VARCHAR | pending / generating / completed / failed |
| created_at | TIMESTAMP | 생성 시각 |

#### prototypes
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| session_id | UUID | FK → prototype_sessions |
| name | VARCHAR | 프로토타입 이름 |
| solution_type | VARCHAR | saas / rest-api / fullstack / internal-tool / mvp / custom |
| config | JSONB | 에이전트/스킬/파이프라인/플랫폼 구성 |
| reasoning | TEXT | AI 추천 사유 |
| is_selected | BOOLEAN | 사용자 선택 여부 |
| created_at | TIMESTAMP | 생성 시각 |

#### pm_profiles
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| name | VARCHAR | PM 이름 |
| slug | VARCHAR | URL-safe 식별자 |
| specialty | VARCHAR | 전문 분야 |
| description | TEXT | 프로필 설명 |
| avatar_url | VARCHAR | 아바타 이미지 |
| skills | JSONB | 보유 스킬 목록 |
| experience_areas | JSONB | 경험 영역 |
| personality_traits | JSONB | 성격 특성 |
| is_active | BOOLEAN | 활성 여부 |
| created_at | TIMESTAMP | 생성 시각 |

#### pm_compositions
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| prototype_id | UUID | FK → prototypes |
| pm_profile_id | UUID | FK → pm_profiles |
| role | VARCHAR | 담당 역할 |
| assigned_agents | JSONB | 담당 에이전트 목록 |
| assigned_skills | JSONB | 담당 스킬 목록 |
| match_score | INTEGER | 매칭 점수 (0~100) |
| reasoning | TEXT | 매칭 사유 |

#### pm_metrics
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| pm_profile_id | UUID | FK → pm_profiles |
| total_projects | INTEGER | 총 프로젝트 수 |
| success_rate | FLOAT | 성공률 |
| avg_rating | FLOAT | 평균 평점 |
| updated_at | TIMESTAMP | 갱신 시각 |

#### pm_ratings
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| pm_profile_id | UUID | FK → pm_profiles |
| project_id | UUID | FK → projects |
| user_id | UUID | FK → users |
| score | INTEGER | 평점 (1~5) |
| comment | TEXT | 코멘트 |
| created_at | TIMESTAMP | 생성 시각 |

### 3.2 기존 모델 확장

#### organizations (추가 컬럼)
- `main_product` (VARCHAR): 주요 제품/서비스
- `business_type` (VARCHAR): B2B / B2C / Internal
- `company_description` (TEXT): 회사 설명

#### projects (추가 컬럼)
- `prototype_session_id` (UUID, FK): 프로토타입 세션 참조
- `pm_profile_id` (UUID, FK): 담당 PM 참조
- `project_type` (VARCHAR): 프로젝트 유형

### 3.3 신규 서비스

#### ClaudeService
- `analyze_user_input()`: 자연어 입력 분석 → 구조화된 요구사항 추출
- `generate_ui_structure()`: 요구사항 → UI 구조 JSON 생성
- `recommend_pm()`: 프로토타입 + PM 풀 → PM 추천 (매칭 점수 포함)

#### PrototypeService
- `create_session()`: 프로토타입 세션 생성
- `generate_prototypes()`: AI 기반 프로토타입 3개 생성 (BackgroundTasks)
- `get_session_status()`: 생성 상태 조회 (polling)
- `select_prototype()`: 프로토타입 선택

#### PMService
- `recommend()`: 프로토타입 기반 PM 추천
- `get_composition()`: PM 구성 조회
- `update_composition()`: PM 구성 수정
- `rate()`: PM 평가

### 3.4 API 엔드포인트

#### prototype_sessions 라우터
| Method | Path | 설명 |
|--------|------|------|
| POST | /api/v1/prototype-sessions | 세션 생성 + 프로토타입 생성 시작 |
| GET | /api/v1/prototype-sessions/{id} | 세션 상태 조회 |
| GET | /api/v1/prototype-sessions/{id}/prototypes | 프로토타입 목록 조회 |
| POST | /api/v1/prototype-sessions/{id}/prototypes/{pid}/select | 프로토타입 선택 |
| POST | /api/v1/prototype-sessions/{id}/retry | 재생성 |
| GET | /api/v1/prototype-sessions/{id}/status | 생성 상태 polling |
| DELETE | /api/v1/prototype-sessions/{id} | 세션 삭제 |
| POST | /api/v1/prototype-sessions/{id}/finalize | 최종 확정 + 프로젝트 생성 |

#### pm_profiles 라우터
| Method | Path | 설명 |
|--------|------|------|
| GET | /api/v1/pm-profiles | PM 목록 조회 |
| GET | /api/v1/pm-profiles/{id} | PM 상세 조회 |
| POST | /api/v1/pm-profiles/recommend | PM 추천 요청 |
| GET | /api/v1/pm-profiles/{id}/metrics | PM 성과 메트릭 |
| POST | /api/v1/pm-profiles/{id}/rate | PM 평가 |

---

## 4. 프론트엔드 구조

### 4.1 라우트
| 경로 | 설명 |
|------|------|
| /solutions/new | 위저드 시작 (Step 1) |
| /solutions/[sessionId] | 위저드 진행 (Step 2~7) |
| /solutions/[sessionId]/complete | 완료 페이지 |

### 4.2 상태 관리
- `solution-wizard-store.ts` (Zustand): 위저드 UI 상태, 현재 Step, 세션 ID
- TanStack Query: 프로토타입/PM 데이터 서버 상태 관리

### 4.3 주요 컴포넌트
- `SolutionWizardLayout`: 위저드 레이아웃 + 스테퍼
- `StepCompanyInfo`: Step 1 회사 정보 + 자연어 입력
- `StepPrototypeLoading`: Step 2 프로토타입 생성 로딩
- `StepPrototypeSelect`: Step 3 프로토타입 선택
- `StepPMRecommend`: Step 4 PM 추천
- `StepPMSelect`: Step 5 PM 선택
- `StepPMConfig`: Step 6 PM 구성 확인
- `StepFinalConfirm`: Step 7 최종 확인

---

## 5. 기술 의존성

### 5.1 외부 서비스
- **Anthropic Claude API**: 자연어 분석, 프로토타입 생성, PM 추천
  - 모델: claude-sonnet-4-20250514 (기본) / claude-opus-4-20250514 (복잡한 분석)
  - Rate limit 고려: 프로토타입 생성 시 3회 API 호출

### 5.2 신규 패키지
- `anthropic` (Python): Claude API 클라이언트
- 프론트엔드 추가 패키지 없음 (기존 스택 활용)

### 5.3 환경 변수
- `ANTHROPIC_API_KEY`: Claude API 키 (필수)
- `ANTHROPIC_MODEL_DEFAULT`: 기본 모델 ID (선택, 기본값: claude-sonnet-4-20250514)
- `ANTHROPIC_MODEL_ADVANCED`: 고급 분석 모델 ID (선택, 기본값: claude-opus-4-20250514)
- `PROTOTYPE_GENERATION_TIMEOUT`: 프로토타입 생성 타임아웃 초 (선택, 기본값: 60)

---

## 6. 구현 페이즈

| Phase | Linear | 내용 | 의존성 |
|-------|--------|------|--------|
| Phase 0 | 24S-89 | 준비 (PRD, 시드 데이터, 스키마, 환경 변수) | 없음 |
| Phase 1 | 24S-90 | DB 모델 + Alembic 마이그레이션 + Pydantic 스키마 | Phase 0 |
| Phase 2 | 24S-91 | 백엔드 서비스 (Claude/Prototype/PM) + API 라우터 | Phase 1 |
| Phase 3 | 24S-92 | 프론트엔드 기반 (타입, 스토어, 레이아웃, Step 1/7) | Phase 2 |
| Phase 4 | 24S-93 | 프로토타입 UI (Step 2/3) + 비동기 생성 구조 | Phase 3 |
| Phase 5 | 24S-94 | PM 시스템 UI (Step 4/5/6) | Phase 4 |
| Phase 6 | 24S-95 | E2E 테스트 + 에러 핸들링 + 반응형 + 접근성 | Phase 5 |

---

## 7. 수용 기준

### Phase 0 완료 조건
- [ ] PRD 문서가 `docs/spec/`에 존재하고 전체 플로우를 기술
- [ ] PM 시드 데이터 JSON이 `clickeye-api/data/`에 존재 (최소 6개 PM 프로필)
- [ ] UI 구조 JSON 스키마가 `clickeye-api/data/`에 존재 (7 Step 정의)
- [ ] `config.py`에 `anthropic_api_key` 환경 변수가 추가됨
- [ ] 기존 테스트가 깨지지 않음

### 전체 v2 완료 조건
- [ ] 위저드 v2로 프로젝트 생성 E2E 플로우 동작
- [ ] 프로토타입 3개 자동 생성 (30초 이내)
- [ ] PM 추천 및 매칭 동작
- [ ] 반응형 (모바일/태블릿/데스크톱)
- [ ] WCAG AA 접근성 준수
- [ ] 기존 v1 위저드와 병행 운영 가능 (feature flag)
