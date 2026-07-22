---
title: Linear 자격증명 설정
category: page
status: implemented
version: 1.0.0
route: /settings/linear
pages:
  - src/app/(dashboard)/settings/linear/page.tsx
components:
  - src/components/credentials/post-key-change-guide.tsx
store: 없음 (로컬 상태 + API 호출)
last_updated: 2026-07-22
related:
  - src/app/(dashboard)/settings/linear/page.tsx
---

## 목적

사용자가 Linear 연동을 설정하는 페이지. API 키, 팀 ID, Webhook 설정(터널 URL + 시크릿)을 관리. Stale 프로젝트 안내 포함.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│ Linear 자격증명 설정                                    │
│ Linear API 키 및 팀 정보를 관리합니다                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 저장된 자격증명 (저장된 경우만 표시)                     │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ✓ 자격증명 저장됨                                   │ │
│ │ API 키: lin_api_****** | 팀 ID: xxxx-xxxx-...      │ │
│ │ Webhook: 설정됨 ✓ | 터널: https://xxxx.trycloudflare.com │
│ │ Webhook 등록됨 ✓                                   │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ 입력 폼 (신규 또는 수정)                                │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ API 키 * [입력 필드]     (빈 값 입력 시 기존 유지)  │ │
│ │ 팀 ID * [입력 필드]                                 │ │
│ │                                                     │ │
│ │ ─── Webhook 설정 (선택) ───                         │ │
│ │ 터널 URL [입력 필드]                                │ │
│ │ [? 터널 설정 가이드 열기/닫기]                      │ │
│ │ Webhook 시크릿 [입력 필드]                          │ │
│ │ [? Webhook 시크릿 생성 가이드]                      │ │
│ │                                                     │ │
│ │ [저장] [삭제]                                       │ │
│ │ [성공/에러 메시지]                                  │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: Linear API 키 첫 등록**
1. `/settings/linear` 진입 (저장된 자격증명 없음)
2. API 키 + 팀 ID 필수 입력
3. [저장] 클릭 → API 요청
4. 저장 완료 후 stale 프로젝트 조회 + 가이드 모달

**시나리오 2: Webhook 설정**
1. 터널 URL 입력 (선택사항)
2. Webhook 시크릿 생성 (`openssl rand -hex 32`)
3. 시크릿 입력 후 [저장]
4. Webhook 자동 등록 (Linear API 호출)

**시나리오 3: Webhook 시크릿 생성 가이드**
1. [? Webhook 시크릿 생성 가이드] 클릭
2. 아코디언 열림 → `openssl` 명령 표시
3. 명령 복사 버튼 제공
4. 아코디언 닫기

**시나리오 4: 자격증명 삭제**
1. 저장된 자격증명 있을 때 [삭제] 버튼 활성화
2. [삭제] 클릭 → confirm 다이얼로그
3. 확인 후 삭제 → 성공 메시지

---

## 기능 요구사항

- [x] API 키 입력 (신규 또는 유지)
- [x] 팀 ID 필수 입력
- [x] 터널 URL 입력 (선택)
- [x] Webhook 시크릿 입력 (선택)
- [x] 저장된 자격증명 요약 표시
- [x] API 키 마스킹
- [x] Webhook 등록 상태 표시
- [x] 터널 설정 가이드 (아코디언)
- [x] Webhook 시크릿 생성 가이드 (아코디언)
- [x] 자격증명 삭제 (confirm)
- [x] 로딩 상태
- [x] 에러/성공 메시지
- [x] Stale 프로젝트 감지 + 가이드 모달

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `loading` | `boolean` | 로컬 (useState) | 초기 로드 |
| `saving` | `boolean` | 로컬 (useState) | 저장 중 |
| `deleting` | `boolean` | 로컬 (useState) | 삭제 중 |
| `saved` | `LinearCredentialsResponse \| null` | API 응답 | 저장된 자격증명 |
| `apiKey` | `string` | 로컬 (useState) | API 키 입력 |
| `teamId` | `string` | 로컬 (useState) | 팀 ID 입력 |
| `webhookSecret` | `string` | 로컬 (useState) | Webhook 시크릿 입력 |
| `tunnelUrl` | `string` | 로컬 (useState) | 터널 URL 입력 |
| `guideOpen` | `boolean` | 로컬 (useState) | 가이드 모달 상태 |
| `staleProjects` | `ProjectResponse[]` | 조회 결과 | Stale 프로젝트 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/settings/linear-credentials` | 페이지 로드 | 저장된 자격증명 조회 |
| `POST/PUT` | `/api/v1/settings/linear-credentials` | [저장] 클릭 | 자격증명 저장/수정 |
| `DELETE` | `/api/v1/settings/linear-credentials` | [삭제] 확인 | 자격증명 삭제 |
| `GET` | `/api/v1/projects?limit=100` | 키 저장 후 | 프로젝트 조회 (stale 필터링) |

---

## 접근성 / 반응형

- [x] 필수 필드 `*` 표시 + `aria-required`
- [x] 입력 필드 라벨 + 설명
- [x] 아코디언 `aria-expanded` / 펼침/접힘 아이콘
- [x] 삭제 confirm 다이얼로그 focus trap
- [x] 에러/성공 메시지 색상 + 아이콘
- [x] 모바일 반응형

---

## 구현 노트

- **API 키 유지**: 저장된 자격증명 있을 때 API 키 필드는 선택사항. 빈 값 입력 시 기존 키 유지 (`payload.api_key = null`).
- **Webhook 자동 등록**: 시크릿 입력 후 저장 시 Linear API로 webhook 자동 등록. `linear_webhook_id` 반환 시 "Webhook 등록됨" 배지 표시.
- **Stale 감지**: `linear_key_status === "stale"` 프로젝트 필터링.
- **터널 URL**: Cloudflare Tunnel (`https://xxxx.trycloudflare.com` 형식).
- **가이드 컴포넌트**: `GuideBlock` 아코디언 컴포넌트로 터널/시크릿 가이드 구현.
- **로딩**: 초기 자격증명 로드 중 spinner 표시.
