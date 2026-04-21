# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[guide] 정적 /guide 페이지 + 사이드바/헤더 진입점 신설**
  > 요청사항: Next.js 15 app router 기준 /guide 라우트 신설. 좌측 TOC + 우측 마크다운 본문 레이아웃.

신규 파일:

* 24SevenClaw-web/src/app/(dashboard)/guide/page.tsx (가이드 목록 + TOC)
* 24SevenClaw-web/src/app/(dashboard)/guide/\[slug\]/page.tsx (세부 가이드)
* 24SevenClaw-web/public/user-guide/\*.md (마크다운 원본)
* 24SevenClaw-web/src/lib/guide-loader.ts (gray-matter frontmatter 파싱 유틸)

수정 파일:

* src/app/(dashboard)/layout.tsx — navItems에 BookOpen 아이콘 '가이드' 추가
* src/components/layout/header.tsx — Bell 옆에 Help(HelpCircle) 아이콘 추가, 클릭 시 /guide 이동

기술 스택: react-markdown@^9(설치됨), remark-gfm@^4(설치됨), gray-matter@^4(설치됨).

콘텐츠는 골격만 작성 — 상세 내용은 CLK-7(24S-186)에서 채움.

검증: /guide 접근, 사이드바/헤더 진입점 클릭 동작, TOC 네비게이션.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | [guide] /guide 페이지 + 사이드바/헤더 진입점 | ✅ 완료 | 빌드 통과, 4개 정적 페이지 생성 |