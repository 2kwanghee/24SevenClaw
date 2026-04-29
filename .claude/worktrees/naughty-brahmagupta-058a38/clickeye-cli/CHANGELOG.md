# Changelog

이 프로젝트의 모든 주요 변경사항을 기록합니다.
[Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따릅니다.

## [0.1.0] - 2026-04-03

### 추가

- **`24sc init`** — 인터랙티브 위자드로 AI 에이전트 워크플로우 구축
  - 프로젝트 타입 선택 (webapp, rest-api, fullstack, custom)
  - 6개 기술 스택 프리셋 (FastAPI+Next.js, Django+React 등)
  - 6개 에이전트 카탈로그 (backend, frontend, uiux, devops, fullstack, harness)
  - 5개 워크플로우 스킬 (TDD, AI 코드리뷰, Linear 연동, Ralph Loop, 하네스 게이트)
  - `--yes` (기본값 모드), `--dry-run` (미리보기) 옵션
- **`24sc add <category> <id>`** — 기존 프로젝트에 에이전트/스킬/Hook 추가
  - 기술 스택 자동 감지 (CLAUDE.md 파싱)
  - 파일 충돌 시 덮어쓰기 확인
  - Hook 자동 등록 (settings.json 업데이트)
- **`24sc doctor`** — 설정 상태 진단
  - 6개 체크 항목 (.claude/, CLAUDE.md, settings.json, Hook 권한, 에이전트 참조, .env)
  - 실패 항목별 수정 가이드 제공
- **하네스 엔지니어링** — 4단계 품질 게이트 프레임워크
  - Router → Context → Loop → Worker 파이프라인
  - harness-gate.sh 자동 생성 (lint + typecheck + test)
- **Handlebars 템플릿 시스템** — 카탈로그 기반 확장 가능한 코드 생성
