# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[rebrand] Phase 1 — 저위험 텍스트 치환 (24SevenClaw → ClickEye)**
  > 요청사항: 문서·UI 텍스트에서 'ClickEye' 표기로 치환. 디렉토리·DB·패키지명은 손대지 않음.

범위: [CLAUDE.md](<http://CLAUDE.md>) 6개, LoadMap_v3.md, [TODO.md](<http://TODO.md>), docs/ 17파일, .claude/agents·skills 11파일, web layout.tsx(title metadata), page.tsx(로고/푸터), auth/dashboard/solutions layout 4파일, engine 템플릿 gemini.md.hbs/claude.md.hbs/env.ts.

변경 패턴: '24SevenClaw' → 'ClickEye' (단, 디렉토리명·패키지명·DB명·컨테이너명 등 고유식별자는 제외).

검증: npm run build 성공, 기존 기능 무영향.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | [rebrand] Phase 1 텍스트 치환 | ✅ 완료 | 문서/UI 36개 파일. 디렉토리명 보존. build 성공 |