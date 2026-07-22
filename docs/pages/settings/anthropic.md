---
title: Anthropic 자격증명 설정
category: page
status: implemented
version: 1.0.0
route: /settings/anthropic
pages:
  - src/app/(dashboard)/settings/anthropic/page.tsx
components:
  - src/components/credentials/credential-card.tsx
  - src/components/credentials/post-key-change-guide.tsx
store: 없음 (로컬 상태 + API 호출)
last_updated: 2026-07-22
related:
  - src/app/(dashboard)/settings/anthropic/page.tsx
---

## 목적

사용자가 자신의 Anthropic API 키를 등록/수정/삭제하는 설정 페이지. 키 변경 시 stale 프로젝트 목록을 제시하고 재인증 안내.

---

## 레이아웃

```
┌────────────────────────────────────────────────────┐
│ Anthropic 자격증명 설정                            │
│ API 키 및 계정 정보를 관리합니다                    │
├────────────────────────────────────────────────────┤
│                                                    │
│ ## API 키 섹션                                     │
│ ┌────────────────────────────────────────────────┐ │
│ │ Anthropic API 키                               │ │
│ │ 설명: Claude API 호출에 필요한 키              │ │
│ │ [입력 필드] → sk-ant-api03-...                 │ │
│ │ [? Anthropic Console 링크]                    │ │
│ │                                                 │ │
│ │ 도움말: 키는 안전하게 저장되며 암호화됩니다    │ │
│ └────────────────────────────────────────────────┘ │
│                                                    │
│ ## OAuth 브라우저 섹션 (정보 전용)                │
│ ┌────────────────────────────────────────────────┐ │
│ │ OAuth 앱 등록 불필요                           │ │
│ │ • 이 서비스는 API 키 방식만 지원합니다         │ │
│ │ • OAuth는 향후 지원 예정입니다                 │ │
│ └────────────────────────────────────────────────┘ │
│                                                    │
│ [저장]  [성공/에러 메시지]                         │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 새 API 키 저장**
1. `/settings/anthropic` 진입
2. API 키 입력 필드에 `sk-ant-api03-...` 입력
3. [저장] 클릭 → API 요청
4. 저장 완료 메시지 표시
5. stale 프로젝트 조회 후 가이드 모달 열기

**시나리오 2: API 키 변경**
1. 새 키 입력 후 [저장] 클릭
2. 기존 프로젝트 중 anthropic_key_status="stale" 인 항목 조회
3. "다음 프로젝트에서 키를 재인증해주세요" 가이드 모달 표시
4. 프로젝트 링크 제공

**시나리오 3: 유효성 검사**
1. 유효하지 않은 키 입력 (길이 <20 또는 sk-ant- 접두사 없음)
2. "유효한 API 키를 입력하세요" 에러 메시지
3. [저장] 버튼 disabled

---

## 기능 요구사항

- [x] API 키 입력 필드
- [x] 키 유효성 검사 (sk-ant- 접두사, 최소 길이)
- [x] 저장 (API)
- [x] 에러 메시지
- [x] 성공 메시지
- [x] Anthropic Console 링크
- [x] OAuth 정보 표시 (등록 불필요 안내)
- [x] Stale 프로젝트 감지 + 가이드 모달
- [ ] 키 삭제 (선택사항)
- [ ] 키 마스킹 표시

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `guideOpen` | `boolean` | 로컬 (useState) | 가이드 모달 열림 상태 |
| `staleProjects` | `ProjectResponse[]` | 조회 결과 | 키 변경 후 stale 프로젝트 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `POST` | `/api/v1/settings/anthropic-credentials` | [저장] 클릭 | API 키 저장 |
| `GET` | `/api/v1/projects?limit=100` | 키 저장 후 | 전체 프로젝트 조회 (stale 필터링) |

---

## 접근성 / 반응형

- [x] 입력 필드 라벨 + 설명
- [x] 링크 `aria-label` 제공
- [x] 에러 메시지 색상 + 아이콘
- [x] 성공 메시지 색상 + 아이콘
- [x] 모바일 반응형

---

## 구현 노트

- **키 마스킹**: 저장 후 화면에 원본 표시 안 함. "저장되었습니다" 메시지만 표시.
- **Stale 감지**: `anthropic_key_status === "stale"` 프로젝트 필터링.
- **유효성**: `startsWith("sk-ant-") && length >= 20`.
- **가이드 모달**: `PostKeyChangeGuide` 컴포넌트 (`channel="anthropic"`).
