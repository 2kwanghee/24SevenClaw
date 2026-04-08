# Ralph Loop — 구현 결과

## 완료 항목

### [web+api] 추천 Reasoning — 각 추천 항목에 "왜 추천됨" 설명 추가

**상태**: 완료

### 변경 파일

#### API (24SevenClaw-api)
| 파일 | 변경 내용 |
|------|----------|
| `app/schemas/recommend.py` | `RecommendResponse`에 `summary: str` 필드 추가 |
| `app/services/recommend_service.py` | `AGENT_REASONING`, `SKILL_REASONING`, `PIPELINE_REASONING` 딕셔너리 추가. 각 추천 항목에 reasoning 주입 + summary 생성 |
| `tests/test_recommend.py` | SaaS 테스트에 reasoning/summary 필드 검증 추가 |

#### Web (24SevenClaw-web)
| 파일 | 변경 내용 |
|------|----------|
| `src/types/wizard.ts` | `Recommendations` 타입에 `skillReasonings`, `pipelineReasonings`, `summary` 추가 |
| `src/lib/api-client.ts` | `RecommendResponse`에 `reasoning?`, `summary` 필드 추가 |
| `src/hooks/use-recommend.ts` | API 응답에서 reasoning 파싱 + `AGENT_REASONING_MAP` 추가 (클라이언트측 역할 에이전트용) |
| `src/components/projects/wizard/steps/step-agents.tsx` | 추천 에이전트 카드에 reasoning 표시 (emerald 배경) |
| `src/components/projects/wizard/steps/step-skills.tsx` | 추천 스킬 카드에 reasoning 표시 |
| `src/components/projects/wizard/steps/step-pipelines.tsx` | 추천 파이프라인 카드에 reasoning 표시 |

### 설계 결정

- **에이전트 reasoning은 클라이언트 측 별도 관리**: API의 에이전트는 플랫폼(claude-code, cursor 등)이고 Step 3 UI의 에이전트는 역할(backend, frontend 등)이므로, `AGENT_REASONING_MAP`을 `use-recommend.ts`에 별도 정의
- **스킬/파이프라인 reasoning은 API에서 전달**: ID 매핑(github-mcp→github, ai-critique→ai-review) 시 reasoning도 함께 매핑

### 테스트 결과
- API: 183 tests passed (pytest)
- API: ruff check 통과
- Web: TypeScript 타입체크 통과
- Web: ESLint 0 errors (6 warnings — 기존)

### 남은 이슈
- 없음
