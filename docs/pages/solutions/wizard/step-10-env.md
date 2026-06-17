---
route: /solutions/[sessionId] (Step 9)
title: 환경변수 입력
category: page
status: implemented
version: 1.1.0
components:
  - src/components/solutions/wizard/steps/step-solution-env.tsx
store: useSolutionWizardStore → setEnv, setEnvValidation
last_updated: 2026-06-15
---

## 목적
로컬 실행에 필요한 API 키 및 환경변수를 입력. ANTHROPIC_API_KEY는 필수이며, Linear/Notion 등 선택한 스킬의 API 키는 실시간 유효성 검사 후 입력 또는 보류 가능. 입력값은 최종 ZIP 파일의 `.env`에 포함.

---

## 레이아웃

```
┌────────────────────────────────────────────────┐
│ 환경변수 설정                                   │
│ ℹ️  이 값들은 로컬 .env 파일에 저장됩니다.      │
├────────────────────────────────────────────────┤
│                                                │
│ 필수 API 키                                     │
│ ┌──────────────────────────────────────────────┐
│ │ ANTHROPIC_API_KEY                 [📖 가이드]│
│ │ 인증 키 | [✅ 설정됨] or [🕐 보류] or [❌필수] │
│ │ [입력 필드 or 보류 버튼]                     │
│ └──────────────────────────────────────────────┘
│
│ 스킬별 필수/선택 환경변수 그룹                 │
│ ┌──────────────────────────────────────────────┐
│ │ Linear (스킬: 6개 선택함)                    │
│ │                                              │
│ │ LINEAR_API_TOKEN [📖 가이드]                 │
│ │ [입력 필드]                [✅ 유효] [📖 도움]│
│ │                                              │
│ │ LINEAR_WEBHOOK_SECRET [📖 가이드]           │
│ │ [입력 필드]                [⏳ 검증 중...]   │
│ │                                              │
│ │ 웹훅 터널 설정 (선택)                        │
│ │ ○ Cloudflare Tunnel (기본)                  │
│ │ ○ ngrok                                      │
│ │ ○ Polling                                    │
│ └──────────────────────────────────────────────┘
│
│ ┌──────────────────────────────────────────────┐
│ │ Notion (스킬: 2개 선택함)                    │
│ │                                              │
│ │ NOTION_API_TOKEN [📖 가이드]                 │
│ │ [입력 필드]                [❌ 유효하지 않음]│
│ └──────────────────────────────────────────────┘
│
│ 추가 환경변수 (선택)                           │
│ ┌──────────────────────────────────────────────┐
│ │ KEY                 │ VALUE                  │
│ │ ┌─────────────────┐ ┌────────────────────┐  │
│ │ │ OPENAI_API_KEY  │ │ sk-...         [✕] │  │
│ │ └─────────────────┘ └────────────────────┘  │
│ │                                              │
│ │ [+ 환경변수 추가]                            │
│ └──────────────────────────────────────────────┘
│
│ ⚠️  API 키를 공유하거나 커밋하지 마세요.
│
└────────────────────────────────────────────────┘
```

---

## 기능 요구사항

### 필수 API 키
- [x] ANTHROPIC_API_KEY (항상 필수)
  - [x] 입력 필드 또는 "나중에" 보류 선택지
  - [x] console.anthropic.com 링크
  - [x] 상태 배지 (✅ 설정됨 / 🕐 보류 / ❌ 필수)

### 스킬별 필수 환경변수 그룹
- [x] 선택한 스킬별로 필수/선택 환경변수 자동 표시
- [x] Linear: LINEAR_API_TOKEN, LINEAR_WEBHOOK_SECRET
  - [x] LINEAR_API_TOKEN 실시간 유효성 검사 (`integrations.validateLinear`, 800ms 디바운스)
  - [x] 유효/무효 배지 표시
  - [x] 웹훅 터널 설정 (Cloudflare / ngrok / Polling)
  - [x] 각 옵션별 설정 가이드
- [x] Notion: NOTION_API_TOKEN
  - [x] NOTION_API_TOKEN 실시간 유효성 검사 (`integrations.validateNotion`, 800ms 디바운스)
  - [x] 유효/무효 배지 표시
- [x] 각 키별 외부 가이드 링크 (docs 또는 공식 페이지)

### 추가 환경변수 (선택)
- [x] 동적 키-값 쌍 추가 (OPENAI_API_KEY 등)
- [x] 행 삭제 버튼 (✕)
- [x] "환경변수 추가" 버튼
- [x] 입력 비ASCII 문자 새니타이즈 (sanitizeIntegrationInput)
- [x] KEY 형식 유효성 검사 (대문자 + 언더스코어)

### 상태 및 유효성
- [x] canProceed: ANTHROPIC_API_KEY 입력 또는 보류 + Linear/Notion이 모두 유효 (invalid 아님)
- [x] 보류 후 최종 확인 단계에서 입력 가능
- [x] 보안 경고 메시지 표시

---

## 스토리보드

**시나리오 1: 필수 키 입력**
1. ANTHROPIC_API_KEY 필수 항목 로드 (❌ 필수 상태)
2. 사용자가 입력 필드에 sk-ant-... 입력 → 실시간 상태 변경 (✅ 설정됨)
3. 또는 "나중에" 클릭 → 상태 변경 (🕐 보류)
4. canProceed 조건 확인: 입력 또는 보류 = 통과

**시나리오 2: 스킬별 필수 키 검증**
1. Linear 스킬 6개 선택 → Linear 그룹 표시
2. LINEAR_API_TOKEN 입력 → 800ms 디바운스 후 `integrations.validateLinear` 호출
3. 유효 → ✅ 배지, 무효 → ❌ 배지 + 에러 메시지
4. 웹훅 설정 선택 (3개 옵션 중 선택)
5. Notion도 동일하게 처리

**시나리오 3: Linear 웹훅 설정**
1. 웹훅 터널 선택 시 각 옵션별 가이드 텍스트 표시
2. Cloudflare (기본): 설정 명령 제시
3. ngrok: 토큰 입력 가이드
4. Polling: 주기 설정 가이드

**시나리오 4: 추가 환경변수**
1. "+ 환경변수 추가" 클릭 → 빈 키-값 행 추가
2. KEY 입력 (대문자 강제, 언더스코어만 허용)
3. VALUE 입력 (비ASCII 새니타이즈)
4. 행 삭제 가능

**시나리오 5: 보류 이후 최종 확인 단계**
1. ANTHROPIC_API_KEY를 "보류" → ZIP에 docs/api-keys.md 동봉
2. 최종 확인 단계에서 가이드를 보며 입력 가능
3. 또는 로컬에서 .env 직접 작성

---

## 상태 관리

| 상태값 | 타입 | 설명 |
|--------|------|------|
| `envVars` | Record<string, string> | 커스텀 환경변수 (OPENAI_API_KEY 등) |
| `requiredKeys` | Record<string, string> | 필수 키 입력값 (ANTHROPIC_API_KEY 등) |
| `deferredKeys` | Set<string> | 보류된 키 목록 |
| `linearValidation` | 'valid' \| 'invalid' \| 'pending' | Linear API 토큰 검증 상태 |
| `notionValidation` | 'valid' \| 'invalid' \| 'pending' | Notion API 토큰 검증 상태 |
| `linearWebhookTunnel` | 'cloudflare' \| 'ngrok' \| 'polling' | Linear 웹훅 터널 선택 |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 | 주기 |
|--------|------|--------|------|------|
| `POST` | `integrations.validateLinear` | LINEAR_API_TOKEN 입력 | Linear 토큰 유효성 검사 | 800ms 디바운스 |
| `POST` | `integrations.validateNotion` | NOTION_API_TOKEN 입력 | Notion 토큰 유효성 검사 | 800ms 디바운스 |

---

## 접근성 / 반응형

- [x] 키 필드는 readonly 표시 (포커스 없음)
- [x] 상태 배지는 aria-label로 설명
- [x] 외부 링크는 target="_blank" + rel="noopener noreferrer"
- [x] 모바일: 스택 레이아웃 (컬럼 1개)
- [x] 데스크톱: 필요시 2컬럼 그룹 분리

---

## 구현 노트

- **서버 키 사용**: 이 위저드는 사용자가 로컬 실행용 키를 입력하는 단계입니다. 위저드 설계 단계(프로토타입 생성, 프리뷰)에서의 LLM 호출은 **서버의 Anthropic API 키(환경변수 ANTHROPIC_API_KEY from .env.local)**를 사용하며, 사용자 키는 여기서 수집합니다. OpenAI 키는 이 위저드에서 받지 않으며, 사용자가 필요시 OPENAI_API_KEY를 커스텀 환경변수로 추가할 수 있습니다.
- `collectEnvVars` 유틸 함수로 선택한 에이전트/스킬의 필수 env_var 목록 추출
- 보류(Deferred) 키는 ZIP의 `docs/api-keys-guide.md`에 설정 방법 기록
- 입력 새니타이즈: 컨트롤 문자, 개행 제거 (보안)
- Linear 웹훅: fire-and-forget 방식으로 초기 등록은 최종 확인 단계(`registerInitialTasks`)에서 처리
