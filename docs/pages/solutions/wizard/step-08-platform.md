---
route: /solutions/new (Step 7)
title: 플랫폼 선택
category: page
status: implemented
version: 2.0.0
components:
  - src/components/solutions/wizard/steps/step-solution-platform.tsx
store: useSolutionWizardStore → setPlatform
last_updated: 2026-06-15
---

## 목적
로컬에서 AI 개발을 실행할 에이전트 플랫폼 선택. 현재 Claude Code만 사용 가능(권장), 나머지는 Coming Soon. PM이 지원 플랫폼을 지정하면 자동 필터링 및 선택 제약.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────┐
│ 생성된 프로젝트를 실행할 AI 플랫폼을 선택하세요.   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │ ◉ Claude Code    │  │ ○ Gemini CLI     │        │
│  │    [권장]        │  │    [Coming Soon] │        │
│  │                  │  │    (비활성)       │        │
│  │ 설명 텍스트       │  │ 설명 텍스트      │        │
│  │  ✅ 선택됨        │  │  > 선택 (불가)   │        │
│  └──────────────────┘  └──────────────────┘        │
│                                                     │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │ ○ Cursor         │  │ ○ Codex          │        │
│  │    [Coming Soon] │  │    [Coming Soon] │        │
│  │    (비활성)       │  │    (비활성)       │        │
│  │ 설명 텍스트       │  │ 설명 텍스트      │        │
│  │  > 선택 (불가)   │  │  > 선택 (불가)   │        │
│  └──────────────────┘  └──────────────────┘        │
│                                                     │
│ ┌───────────────────────────────────────────────┐  │
│ │ 📁 폴더 구조 프리뷰 (Claude Code 기준)        │  │
│ │ my-project/                                   │  │
│ │ ├── .claude/                                  │  │
│ │ │   ├── CLAUDE.md                             │  │
│ │ │   ├── settings.json                         │  │
│ │ │   └── ...                                   │  │
│ │ ├── src/                                      │  │
│ │ └── ...                                       │  │
│ └───────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 스토리보드

1. 스텝 진입 → `pmSupportedPlatforms` 확인
2. useEffect 자동 선택 로직:
   - PM이 플랫폼을 지정했다면 (`hasPmFilter=true`):
     - 지원하는 사용 가능 플랫폼이 1개만 있으면 자동 선택
     - 현재 선택이 미지원이면 지원 플랫폼 중 첫 번째로 교체
   - PM 필터가 없다면 (`hasPmFilter=false`):
     - 현재 선택이 없으면 `claude-code` 기본값
3. UI 렌더링
   - 4개 플랫폼 카드 (2열 그리드)
   - Claude Code: 권장 배지 + 선택 가능
   - Gemini/Cursor/Codex: Coming Soon 배지 + 비활성 (또는 PM 미지원 시 PM 미지원 배지)
4. 사용자 클릭 → `setPlatform({ platformId })`
5. canProceed: `platformId` 존재 여부
6. "다음" 클릭 → Step 8(OS/환경) 이동

---

## 기능 요구사항

### 플랫폼 옵션
- [x] Claude Code (`claude-code`) — 사용 가능, 권장 배지
- [x] Gemini CLI (`gemini-cli`) — Coming Soon, 비활성
- [x] Cursor (`cursor`) — Coming Soon, 비활성
- [x] Codex (`codex`) — Coming Soon, 비활성

### PM 필터링
- [x] PM이 지원 플랫폼을 지정하면 (`pmSupportedPlatforms.length > 0`):
  - 미지원 플랫폼: "PM에서 지원하지 않음" 배지 + 비활성
  - 지원 플랫폼: 정상 선택 가능
- [x] PM 미지원 플랫폼이 현재 선택되면 자동 교체
- [x] PM이 단일 플랫폼만 지원하면 자동 선택

### 자동 선택
- [x] PM 필터 없을 때: `platformId` 미지정 시 `claude-code` 기본값
- [x] PM 필터 있을 때: 아래 순서대로 수행
  1. 지원·사용 가능 플랫폼이 1개면 자동 선택
  2. 현재 선택이 미지원이면 지원 플랫폼 중 첫 번째로 교체

### UI
- [x] 카드 레이아웃: 2열 그리드 (`grid gap-3 sm:grid-cols-2`)
- [x] 선택 표시: 라디오 버튼 스타일
- [x] 아이콘: 각 플랫폼별 unique 아이콘 (Terminal, Zap, Code2, Cpu)
- [x] 배지: 권장 / Coming Soon / PM 미지원 (조건부)
- [x] 설명: `platformDescriptions` 번역 키에서 로드

### 검증
- [x] canProceed: `platformId` 존재 여부

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `platformId` | `string` | store | 선택한 플랫폼 ID |
| `pmSupportedPlatforms` | `string[]` | store (Step 5에서 저장) | PM이 지원하는 플랫폼 목록 |
| `hasPmFilter` | `boolean` | 로컬 (computed) | PM 필터 활성화 여부 |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| (없음) | — | — | 로컬 상태만 사용 (API 연동 없음) |

---

## 접근성 / 반응형

- [x] 라디오 버튼: `type="button"` 시뮬레이션 (onClick → `setPlatform`)
- [x] 선택 상태: `isSelected` 조건부 스타일
- [x] 비활성 버튼: 클릭 불가 (`!isAvailable` 시 핸들러 불실행)
- [x] 배지: 조건부 색상 (`badgeClass`)
- [x] 반응형: sm: 2열 그리드

---

## 구현 노트

- **PLATFORM_OPTIONS**: id/label/icon/available 정의 (하드코딩, 확장 가능)
- **useEffect 자동 선택**: 의존성 `[hasPmFilter, pmSupportedPlatforms]`
  - `!hasPmFilter || !pmSupportedPlatforms.includes(platformId)` 시에만 변경
  - 중복 선택 방지 (if condition으로 이미 선택된 경우 return)
- **배지 로직**:
  1. PM 미지원: "PM에서 지원하지 않음" 배지
  2. Claude Code: "권장" 배지 (amber)
  3. 나머지: "Coming Soon" 배지 (zinc, disabled)
- 번역 키: `wizard.step5.platform` (note: step5 = wizard index 5)
- `platformDescriptions`: `claudeCodeDesc`, `geminiCliDesc`, `cursorDesc`, `codexDesc` 키 사용
- canProceed: `platformId` 존재 여부 검증
- **PM 자동 선택 트리거**: `pmSupportedPlatforms` 변경 시에만 (store 외부에서 Step 5에서 저장)
