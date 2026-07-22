---
title: 가이드 뷰어
category: page
status: implemented
version: 1.0.0
route: /guide/[slug]
pages:
  - src/app/(dashboard)/guide/page.tsx
  - src/app/(dashboard)/guide/[slug]/page.tsx
components:
  - src/components/guide/guide-toc.tsx
  - src/components/guide/markdown-content.tsx
store: 없음
last_updated: 2026-07-22
related:
  - src/app/(dashboard)/guide/[slug]/page.tsx
  - src/lib/guide-loader.ts
---

## 목적

사용자가 ClickEye 플랫폼의 가이드·팁·튜토리얼을 계층적으로 탐색하고 읽을 수 있는 문서 뷰어. 목차 네비게이션 + 마크다운 렌더링.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│ 가이드                                                  │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│ 목차 (좌)    │ 콘텐츠 (우)                               │
│              │ ┌────────────────────────────────────┐  │
│ - 시작하기   │ │ # 가이드 제목                       │  │
│   - 설치     │ │ 설명: ...                          │  │
│   - 기본     │ │                                     │  │
│ - 고급       │ │ ## 섹션 1                          │  │
│   - API      │ │ 본문 마크다운 렌더링               │  │
│ - FAQ        │ │ - 리스트                           │  │
│              │ │ - 코드 블록                        │  │
│              │ │ `...`                              │  │
│              │ │                                     │  │
│              │ └────────────────────────────────────┘  │
│              │                                          │
└──────────────┴──────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 가이드 진입**
1. `/guide/getting-started` 진입 (정적 경로)
2. `getAllGuides()` → 목차 리스트 생성
3. `getGuide(slug, locale)` → 마크다운 콘텐츠 조회
4. 좌측 목차 + 우측 콘텐츠 렌더링

**시나리오 2: 목차 항목 클릭**
1. 목차에서 다른 가이드 클릭
2. `<a href="/guide/{slug}">` 네비게이션
3. Next.js 정적 경로로 사전 생성된 페이지 로드

**시나리오 3: 404 처리**
1. `/guide/invalid-slug` 진입
2. `getGuide(slug)` → null 반환
3. `notFound()` 호출 → 404 페이지 표시

---

## 기능 요구사항

- [x] 목차 네비게이션 (계층적 트리)
- [x] 마크다운 렌더링
- [x] 정적 경로 생성 (`generateStaticParams`)
- [x] 언어별 가이드 (locale 지원)
- [x] 제목 + 설명 표시
- [x] 404 처리
- [ ] 목차 검색 필터
- [ ] 다국어 콘텐츠 전환
- [ ] 마크다운 목차 생성 (Table of Contents in-page)

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `guides` | `Guide[]` | `getAllGuides(locale)` | 목차용 모든 가이드 |
| `guide` | `Guide` | `getGuide(slug, locale)` | 현재 페이지 콘텐츠 |

---

## 구현 노트

- **정적 생성**: SSG로 빌드 시 모든 가이드 사전 생성. `generateStaticParams` 필수.
- **목차 계층**: 가이드 메타데이터의 `category` / `order` 필드로 트리 구성.
- **마크다운 렌더**: `markdown-content` 컴포넌트에서 렌더링 (syntax highlight, 링크 등).
- **국제화**: `next-intl` 서버 API로 현재 locale 자동 감지.
- **색인**: `lib/guide-loader.ts`에서 문서 시스템과 인터페이스 (파일 기반 또는 DB).
