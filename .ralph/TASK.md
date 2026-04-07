# Ralph Loop — 구현 결과

## [api] 프로젝트 설정 저장/조회 연동

### 변경 파일

**24SevenClaw-api:**
- `app/api/v1/projects.py` — generate 엔드포인트에 wizard_data 자동 저장 + redownload 엔드포인트 추가
- `app/schemas/generate.py` — RedownloadRequest 스키마 추가
- `app/schemas/project.py` — ProjectResponse에 wizard_data 필드 추가

**24SevenClaw-web:**
- `src/lib/api-client.ts` — WizardConfigData 타입, saveConfig/redownload 메서드 추가
- `src/app/(dashboard)/projects/[projectId]/page.tsx` — 설정 요약 카드 + 재다운로드 버튼
- `src/app/(dashboard)/projects/new/page.tsx` — 위저드 완료 시 config 저장 연동

### 구현 내용

1. **위저드 완료 시 설정 자동 저장**: generate 엔드포인트 호출 시 wizard_data가 프로젝트에 자동 저장 (env_vars 제외)
2. **프로젝트 상세에서 설정 조회**: ProjectResponse에 wizard_data 포함, 상세 페이지에서 에이전트/스킬/플랫폼 요약 표시
3. **재다운로드**: POST /projects/{id}/redownload — 저장된 wizard_data로 동일 ZIP 재생성 (env_vars만 새로 전달)
4. **위저드 완료 플로우**: 프로젝트 생성 → wizard config POST 저장 → 목록으로 이동

### 테스트 결과

- API: pytest 78건 통과, ruff 통과
- Web: TypeScript 타입체크 통과, 빌드 성공

### 남은 이슈

- mypy에서 organization_service.py의 기존 unused-ignore 경고 3건 (이번 변경과 무관)
