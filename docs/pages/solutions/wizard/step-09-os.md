---
route: /solutions/[sessionId] (Step 8)
title: 실행 환경 (OS) 선택
category: page
status: implemented
version: 1.0.0
components:
  - src/components/solutions/wizard/steps/step-solution-os.tsx
store: useSolutionWizardStore → setOs
last_updated: 2026-06-15
---

## 목적
솔루션을 실행할 운영체제(OS)를 선택. 현재 WSL2(Ubuntu)만 사용 가능하며, 해당 선택값은 최종 확인 단계의 설치 가이드 분기에 사용.

---

## 레이아웃

```
┌──────────────────────────────────────────┐
│ 실행 환경을 선택하세요.                   │
│                                          │
│  ┌─────────────────┐ ┌─────────────────┐ │
│  │ WSL2 (Ubuntu)  │ │Windows Native   │ │
│  │ ⭐ 권장          │ │Coming Soon       │ │
│  │ 설명 텍스트     │ │(비활성)          │ │
│  │ [✓ 선택됨]     │ │ > 선택           │ │
│  └─────────────────┘ └─────────────────┘ │
│                                          │
│  ┌─────────────────┐ ┌─────────────────┐ │
│  │    macOS        │ │ Linux Native    │ │
│  │Coming Soon       │ │Coming Soon       │ │
│  │(비활성)          │ │(비활성)          │ │
│  │ > 선택           │ │ > 선택           │ │
│  └─────────────────┘ └─────────────────┘ │
│                                          │
│  ┌──────────────────────────────────────┐ │
│  │ WSL2가 없으신가요?                    │ │
│  │ ▼ 설치 가이드 펼치기                  │ │
│  └──────────────────────────────────────┘ │
│    1. PowerShell 관리자 모드로 실행      │
│    2. wsl --install 명령 실행            │
│    3. 시스템 재부팅 후 Ubuntu 선택      │
│    📖 MS Learn: wsl 설치 공식 가이드    │
│                                          │
└──────────────────────────────────────────┘
```

---

## 기능 요구사항

- [x] 4개 OS 카드 (WSL2 / Windows / macOS / Linux)
- [x] WSL2 권장 배지 + 초록색 강조
- [x] Windows/macOS/Linux는 Coming Soon 배지로 비활성화
- [x] 단일 선택
- [x] WSL2 미설치 가이드: 접기/펼치기 패널
  - [x] 3단계 설치 안내
  - [x] MS Learn 공식 링크 (한국어)
- [x] `canProceed`: osId 존재 (자동으로 WSL2 선택됨)
- [ ] 설치 상태 자동 감지

---

## 스토리보드

**시나리오 1: 초기 로드**
1. 컴포넌트 마운트 시 `osId` 미설정 → 자동으로 `setOs({ osId: "wsl2" })` 호출
2. WSL2 카드가 기본 선택 상태로 표시
3. 사용자는 다른 OS를 시도할 수 없음 (비활성화됨)
4. canProceed = true (즉시 다음 단계 진행 가능)

**시나리오 2: WSL2 가이드 펼치기**
1. 사용자가 "WSL2가 없으신가요?" 버튼 클릭
2. 접힌 패널이 펼쳐지면서 3단계 설치 가이드 표시
3. MS Learn 링크(한국어) 제공
4. 사용자는 가이드를 보고 닫을 수 있음 (선택값 변경 없음)

**시나리오 3: 다른 OS 선택 시도**
- 사용자가 Windows/macOS/Linux 카드 클릭 → 비활성화되어 이벤트 무시

---

## 상태 관리

| 상태값 | 타입 | 설명 |
|--------|------|------|
| `osId` | string | 선택된 OS ID (`wsl2` \| `windows` \| `macos` \| `linux`) |
| `wslGuideOpen` | boolean | WSL2 설치 가이드 펼침 여부 |

---

## 구현 노트

- `OS_OPTIONS` 배열에서 `available: true/false` 속성으로 활성화/비활성화 제어
- WSL2는 기본으로 선택되어 사용자가 변경할 수 없음
- 설치 가이드 링크: `https://learn.microsoft.com/ko-kr/windows/wsl/install` (한국어 문서)
- 선택값 `osId`는 최종 확인 단계(Step 11)의 설치 가이드 모달에서 분기 처리 (WSL2 vs 일반)
