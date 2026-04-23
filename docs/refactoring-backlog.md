# 리팩토링 백로그 (Phase 2 + 3)

Phase 1에서 공통 인프라를 구축했습니다. 아래는 남은 전체 마이그레이션과 추가 개선 항목입니다.

---

## Phase 2 — Full Migration (Phase 1 인프라 전체 적용)

| 항목 | 내용 | 영향 파일 수 |
|------|------|-------------|
| `useAccessToken` 잔여 치환 | 13개 훅 + 12개 인라인 `session?.accessToken` 모두 `useAccessToken` import로 교체 | 25 |
| `useWizardAsyncStep` 마이그레이션 | `step-pm-recommendation.tsx`, `step-solution-agents.tsx`, `step-pm-composition.tsx` 3개 step 전환 | 3 |
| `BaseModal` 전환 | 10+ 모달 파일을 `BaseModal` 기반으로 재작성 | 10+ |
| Mixin 전체 적용 | 나머지 20개 모델에 `UUIDPKMixin + TimestampMixin` 적용 (alembic diff 매번 검증) | 20 |
| `get_or_404` 전체 적용 | 나머지 14개 서비스에 `get_or_404` 적용 | 14 |
| `paginate` 전체 적용 | `page/page_size` 스타일 엔드포인트에 `PageParams + paginate` 적용 | 신규 엔드포인트부터 |
| `BaseService` 상속 확대 | 나머지 7개 서비스에 `BaseService` 상속 + `apply_update` 적용 | 7 |

---

## Phase 3 — 추가 공통화 항목

### 프론트엔드

| 항목 | 현황 | 목표 |
|------|------|------|
| `api-client.ts` URLSearchParams 빌더 | 12곳에서 수동 빌드 | `buildQuery(params)` 헬퍼 |
| Blob fetch 공통화 | 5곳에서 `response.blob()` + URL.createObjectURL 수동 처리 | `downloadBlob(url, filename)` 헬퍼 |
| SummaryCard 컴포넌트 | `step-confirmation.tsx` ↔ `step-solution-confirm.tsx` 중복 | `SummaryCard` 공통 컴포넌트 |
| FormField/TextInput 스타일 | 4+ 파일, 20+ 필드에서 인라인 스타일 반복 | `FormField` 공통 컴포넌트 |
| Empty/Error/Loading UI | 6개 step에서 각각 구현 | `StepEmpty`, `StepError`, `StepLoader` 컴포넌트 |
| Zustand nested setter | `solution-wizard-store.ts`에서 7번 spread 패턴 반복 | `mergeSection(section, partial)` 헬퍼 |
| Skeleton/reveal 로직 | 3개 파일에서 `useState + setTimeout stagger` 반복 | `useStaggerReveal(items, delay)` 훅 |

### 백엔드

| 항목 | 현황 | 목표 |
|------|------|------|
| `SchemaMixin(from_attributes)` | 38곳에서 `model_config = {"from_attributes": True}` 반복 | `BaseSchema(BaseModel)` 기반 클래스 |
| Router DI boilerplate | 21개 라우터에서 `service = XxxService(db)` 143회 반복 | `Depends(get_xxx_service)` 패턴 표준화 |
| Jinja 렌더 헬퍼 | `generator.py`에 `_env.get_template().render()` 8회 반복 | `render(template, **ctx)` 헬퍼 |
| `_slugify` 공통화 | `project_service.py`, `prototype_service.py` 중복 정의 | `app/utils/text.py`로 이동 |
| 테스트 `auth_headers` fixture | 7개 테스트 파일에서 수동 register/login | `conftest.py`에 `auth_headers` fixture 추가 |
| 상태 전이 가드 | 5개 서비스에서 유효하지 않은 상태 전이 체크 로직 반복 | `assert_valid_transition(current, target, allowed)` 헬퍼 |

---

## 우선순위 가이드

1. **즉시**: `useAccessToken` 치환 (단순 import 교체, 부작용 없음)
2. **이번 스프린트**: `BaseModal` 전환 + Mixin 전체 모델 적용
3. **다음 스프린트**: `get_or_404`, `BaseService` 전체 서비스 적용
4. **이후**: Phase 3 항목 (티켓 단위로 분리)
