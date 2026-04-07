# Ralph Loop — 구현 결과

## [engine] Gemini CLI 플랫폼 템플릿

### 변경 파일

**24SevenClaw-web** (5파일):
- `src/lib/engine/platforms/gemini-cli.ts` — GeminiCliAdapter 구현 (PlatformAdapter 인터페이스)
- `src/lib/engine/platforms/index.ts` — GeminiCliAdapter 등록
- `src/lib/engine/generators/gemini-md.ts` — GEMINI.md 루트 가이드 생성기
- `src/lib/engine/generators/gemini-settings.ts` — .gemini/settings.json 생성기
- `src/lib/engine/templates/gemini.md.hbs` — GEMINI.md Handlebars 템플릿

**24SevenClaw-api** (2파일):
- `app/engine/generator.py` — 플랫폼별 루트 가이드 템플릿 라우팅 + settings.json 분기
- `app/engine/templates/gemini.md.j2` — GEMINI.md Jinja2 템플릿

### 구현 내용

1. **GeminiCliAdapter**: `.gemini/` 디렉토리 구조 (agents/, skills/, settings.json, GEMINI.md)
2. **템플릿 재활용**: 기존 에이전트/스킬 Handlebars 템플릿을 그대로 재활용, 경로만 `.gemini/`로 변경
3. **Gemini settings.json**: Claude Code의 permissions/hooks 대신 coreTools/safetySettings 구조
4. **API 분기**: `_get_root_guide_template()` 함수로 플랫폼별 j2 템플릿 선택, `_build_gemini_settings()`로 설정 분기

### 테스트 결과

- Web: typecheck 통과, build 성공
- API: ruff check 통과, pytest 78개 전부 통과

### 남은 이슈

- 없음 (Cursor/Codex 어댑터는 별도 태스크)
