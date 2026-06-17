---
route: /solutions/[sessionId] (Step 11)
title: 최종 확인 및 프로젝트 생성
category: page
status: implemented
version: 1.1.0
components:
  - src/components/solutions/wizard/steps/step-confirmation.tsx
store: useSolutionWizardStore (read-only) + setEnv, setEnvValidation
last_updated: 2026-06-15
---

## 목적
위저드에서 설정한 전체 내용(회사, 솔루션, PM, 에이전트, 스킬, ROI 등)을 최종 리뷰하고 프로젝트 생성을 확정. 보류했던 API 키는 여기서 입력 가능하며, 생성 후 OS별 설치 가이드 모달을 표시하고 프로젝트 대시보드로 이동.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────┐
│ ✅ 솔루션 설계가 완료됐습니다!                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 🏢 회사 정보                                        │
│ 회사명: Acme Corp / 규모: 50-100명 / 업종: SaaS   │
│ 솔루션: "실시간 협업 플랫폼 구축"                   │
│ [🔄 수정하기] (Step 0)                            │
│                                                     │
│ 🎯 선택된 프로토타입                                │
│ [프로토타입 프리뷰 미니 카드]                       │
│ Full-stack Web App (3-tier, Auth 포함)             │
│ [🔄 수정하기] (Step 1)                            │
│                                                     │
│ 👤 선택된 PM 구성                                  │
│ [아바타] Alice Kim | 시니어 아키텍트| ⭐⭐⭐⭐⭐   │
│ 구성: 에이전트 3개 · 스킬 5개 · 훅 2개            │
│ [🔄 수정하기] (Step 4)                            │
│                                                     │
│ 🤖 에이전트 (3개)                                 │
│ [fullstack] [uiux] [security-review]              │
│                                                     │
│ 💻 플랫폼                                         │
│ [Claude Code 아이콘] Claude Code                  │
│ [🔄 수정하기] (Step 7)                            │
│                                                     │
│ 🖥️  실행 환경                                     │
│ WSL2 (Ubuntu) ⭐ 권장                             │
│ [🔄 수정하기] (Step 8)                            │
│                                                     │
│ 💰 ROI 요약                                       │
│ 절감액: ₩200,000,000 (80% 절감)                    │
│ 기간: 120일 → 30일 (75% 단축)                    │
│ [🔄 수정하기] (Step 10)                           │
│                                                     │
│ 🔑 API 키 설정                                    │
│                                                     │
│ ANTHROPIC_API_KEY (필수)                           │
│ ○ ✅ 이미 설정됨                                  │
│ ● 🕐 보류 → [입력 필드 표시]                      │
│                                                     │
│ LINEAR_API_TOKEN [✅ 유효]                        │
│ NOTION_API_TOKEN [❌ 유효하지 않음]               │
│                                                     │
├─────────────────────────────────────────────────────┤
│ [이대로 진행] 버튼                                 │
│                                                     │
│ ℹ️  "이대로 진행" 클릭 시 프로젝트가 생성되고       │
│     설정 파일이 준비됩니다. Linear/Notion이        │
│     활성화되면 초기 작업이 자동으로 등록됩니다.     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 최종 리뷰 및 확인**
1. 컴포넌트 로드 → wizardData 읽기 (read-only)
2. 전체 선택사항 요약 표시 (회사, 프로토타입, PM, 에이전트, 플랫폼, OS, ROI)
3. 각 섹션별 "[🔄 수정하기]" 버튼 → 해당 Step으로 goToStep() 호출
4. 사용자가 내용 검토

**시나리오 2: 보류 키 입력**
1. ANTHROPIC_API_KEY를 이전 단계에서 "보류" → 🕐 배지 표시
2. "[입력 필드]" 활성화 → 사용자가 sk-ant-... 입력
3. "이대로 진행" 전에 입력값 검증 (canProceed 조건)
4. Linear/Notion 토큰도 이곳에서 재입력/유효성 재검사 가능

**시나리오 3: 프로젝트 생성 및 설치 가이드**
1. 모든 필수값 입력 완료 + canProceed = true
2. "이대로 진행" 클릭 → POST `/api/solutions/{sessionId}/finalize`
   - Body:
     ```json
     {
       "project_name": "...",
       "description": "...",
       "wizard_data": {
         "organization": {...},
         "solution": {...},
         "agents": {...},
         "skills": [...],
         "hooks": [...],
         "mcps": [...],
         "platform": {...}
       }
     }
     ```
3. 응답: project_id 수신
4. 모달 표시: 설치 가이드 (OS 분기)
   - **WSL2**: Docker + CLI 설치, ZIP 다운로드→압축해제→cd→npm install→키 적용
   - **일반 (Windows/Mac/Linux)**: 네이티브 구성 가이드 (Coming Soon 텍스트)
5. 각 가이드 단계별:
   - [복사] 버튼으로 명령 복사
   - ZIP 다운로드 링크
   - 스킬별 추가 설정 링크
6. 모달 닫기 또는 "프로젝트로 이동" 클릭 → `/projects/{project_id}` 이동

**시나리오 4: Linear/Notion 초기 작업 등록**
1. POST `/api/solutions/{sessionId}/finalize` 성공 후
2. Linear/Notion 키가 valid → `integrations.registerInitialTasks` fire-and-forget 호출
3. 사용자 계정의 Linear/Notion 워크스페이스에 자동 작업 생성
4. UI는 응답 대기하지 않음 (백그라운드 처리)

---

## 기능 요구사항

### 전체 선택사항 요약
- [x] 회사명, 규모, 업종, 솔루션 요청 (회사)
- [x] 프로토타입 프리뷰 (미니 카드 형식)
- [x] 선택된 PM (아바타, 이름, 직책, 별점, 구성 정보)
- [x] 에이전트 목록 배지 (선택된 agents)
- [x] 플랫폼 (platform.platformId 표시)
- [x] 실행 환경 (OS)
- [x] ROI 요약 (절감액 + 절감률 + 기간 단축)

### 수정 기능
- [x] 각 섹션 "[🔄 수정하기]" 버튼
  - [x] 회사 정보 → Step 0
  - [x] 프로토타입 → Step 1
  - [x] PM 구성 → Step 4
  - [x] 플랫폼 → Step 7
  - [x] OS → Step 8
  - [x] ROI → Step 10

### 보류 키 게이트
- [x] ANTHROPIC_API_KEY 상태 표시
  - [x] ✅ 이미 설정됨 (이전 단계에서 입력)
  - [x] 🕐 보류 (이전 단계에서 보류 선택 → 입력 필드 표시)
- [x] Linear/Notion 검증 상태 표시
  - [x] ✅ 유효
  - [x] ❌ 유효하지 않음
  - [x] 유효하지 않으면 "이대로 진행" 버튼 비활성화

### 프로젝트 생성 및 설치 가이드
- [x] "이대로 진행" 버튼 → POST `/api/solutions/{sessionId}/finalize`
- [x] 설치 가이드 모달 (OS 분기)
  - [x] WSL2: 명령 3-5단계 + 복사 버튼
  - [x] 일반: Coming Soon 플레이스홀더
- [x] ZIP 다운로드 링크 (별도 버튼 또는 가이드 내 포함)
- [x] 스킬별 가이드 링크 (마크다운 문서 또는 외부 링크)
- [x] "프로젝트로 이동" 버튼 → `/projects/{project_id}`

### 상태 및 유효성
- [x] canProceed: Linear/Notion이 invalid 아님 + ANTHROPIC_API_KEY 입력 또는 보류
- [x] Linear/Notion 재검증: 800ms 디바운스

---

## 상태 관리

| 상태값 | 타입 | 설명 |
|--------|------|------|
| `submitting` | boolean | finalize 호출 중 |
| `error` | string \| null | 생성 실패 메시지 |
| `projectId` | string \| null | 생성된 프로젝트 ID |
| `showInstallGuide` | boolean | 설치 가이드 모달 표시 여부 |
| `deferredEnvVars` | Record<string, string> | 보류 키 입력값 (로컬만 유지) |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `POST` | `prototypeSessions.finalize` | "이대로 진행" 클릭 | 프로젝트 생성 + ZIP 생성 |
| `POST` | `integrations.registerInitialTasks` | finalize 성공 후 (fire-and-forget) | Linear/Notion 초기 작업 등록 |
| `GET` | `projects.download` (implicit) | 설치 가이드 모달의 ZIP 링크 | ZIP 파일 다운로드 |

---

## 접근성 / 반응형

- [x] 섹션 헤더는 semantic h3 태그
- [x] "수정하기" 링크는 aria-label with step 정보
- [x] 색상만으로 상태 표현 금지 (배지 + 텍스트)
- [x] 모달: 포커스 트래핑, ESC 키로 닫기
- [x] 모바일: 각 섹션을 풀 너비 카드로 스택
- [x] 설치 가이드: 명령 복사 시 시각적 피드백 (체크 아이콘 잠시 표시)
- [x] 다크 모드: 모달, 카드 배경색 적절한 대비 확보

---

## 구현 노트

- **컨테이너**: 부모 페이지 컴포넌트에서 handleSubmit 로직 처리
  - POST `/api/solutions/{sessionId}/finalize` 호출
  - 응답에서 project_id 추출
  - 설치 가이드 모달 표시 (OS별 분기)
  - 모달 닫기 후 `/projects/{project_id}` 라우팅

- **실제 컴포넌트**: step-confirmation.tsx는 read-only 요약 UI만 담당
  - 생성 로직은 부모에서 수행
  - 하위 컴포넌트: PrototypePreview (프로토타입 미니 카드), PMRatingStars (별점), IntegrationValidationBadge (토큰 상태)

- **보류 키 게이트**: 
  - 이전 단계에서 ANTHROPIC_API_KEY를 "보류" → deferredEnvVars 스토어에 저장
  - 여기서 입력 필드 활성화 → 입력값은 envVars에 합병
  - 또는 사용자가 건너뛰고 로컬에서 .env 직접 작성

- **Linear/Notion 검증 재시도**:
  - 토큰 상태가 invalid → "유효성 재검사" 버튼 제공
  - 800ms 디바운스 후 `integrations.validateLinear`/`validateNotion` 재호출

- **설치 가이드 모달 구성**:
  - 타이틀: "프로젝트 생성 완료! 설치하기"
  - 단계별 명령 + 복사 버튼
  - ZIP 다운로드 버튼
  - "프로젝트로 이동" 버튼 (클릭 후 `/projects/{id}`)
  - OS별 CSS class (wsl2 vs non-wsl2) 적용하여 가이드 분기

- **Linear/Notion fire-and-forget**: 
  - finalize 성공 후 UI에 영향 없이 백그라운드에서 registerInitialTasks 호출
  - 실패해도 사용자에게 알림 없음 (로그만 남김)
  - 사용자는 나중에 Linear/Notion에서 수동 생성 가능

- **마운트 시**: 이전 단계 선택값이 store에 저장되어 있다고 가정
  - wizardData 읽기
  - deferredEnvVars가 있으면 보류 키 입력 필드 활성화
