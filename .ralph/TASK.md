# 구현 결과 — [engine] CLI 생성 엔진 웹 이식

## 변경 파일 (27개, 24SevenClaw-web)

### 신규 생성
| 파일 | 역할 |
|------|------|
| `src/lib/engine/types.ts` | 공유 타입 (CLI types.ts 이식) |
| `src/lib/engine/template-loader.ts` | Handlebars 템플릿 로딩 + 캐시 (server-only) |
| `src/lib/engine/index.ts` | 진입점: `generateAll()` → `Map<string, string>` |
| `src/lib/engine/generators/agent.ts` | 에이전트 .md 생성기 |
| `src/lib/engine/generators/skill.ts` | 스킬 .md 생성기 |
| `src/lib/engine/generators/hook.ts` | Hook .sh 생성기 |
| `src/lib/engine/generators/settings.ts` | settings.json 생성기 |
| `src/lib/engine/generators/claude-md.ts` | CLAUDE.md 생성기 |
| `src/lib/engine/generators/scripts.ts` | 자동화 스크립트 생성기 |
| `src/lib/engine/catalog/agents.json` | 에이전트 카탈로그 (CLI에서 복사) |
| `src/lib/engine/catalog/skills.json` | 스킬 카탈로그 (CLI에서 복사) |
| `src/lib/engine/catalog/stacks.json` | 스택 카탈로그 (CLI에서 복사) |
| `src/lib/engine/templates/**/*.hbs` | Handlebars 템플릿 13개 (CLI에서 복사) |

### 수정
| 파일 | 변경 |
|------|------|
| `package.json` | handlebars, server-only 의존성 추가 |

## 핵심 변경: fs.writeFile() → Map.set(path, content)

- CLI: `writeFiles(targetDir, files)` → 파일시스템에 직접 기록
- Web: `generateAll(options)` → `Map<string, string>` 메모리 버퍼 반환
- 비동기 생성기 4개 `Promise.all()`로 병렬 실행
- 템플릿 로딩에 캐시 적용 (`templateCache`)
- `server-only` import로 클라이언트 번들 포함 방지

## 테스트 결과

- `tsc --noEmit`: ✅ 통과
- `eslint src/lib/engine/`: ✅ 통과
- `npm run build`: ✅ 통과 (16.9s 컴파일, 정적 페이지 7개 생성)

## 남은 이슈

- `next lint` (npm run lint)이 "Invalid project directory" 에러 — Next.js 16 + flat config 호환 이슈 (기존 문제, 이번 작업과 무관)
- 멀티플랫폼 지원 기초 (platforms/) — 별도 티켓 (LoadMap #12)
