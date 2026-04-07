# Ralph Loop — 구현 결과

## 완료 항목

### [web] Step 7: 프리뷰 패널 + 다운로드 (PreviewPanel)

**변경 파일:**

| 파일 | 변경 내용 |
|------|-----------|
| `24SevenClaw-web/src/lib/api-client.ts` | `preview()`, `generateZip()` 엔드포인트 + 타입 추가 |
| `24SevenClaw-web/src/components/projects/wizard/steps/file-tree-preview.tsx` | 새 파일 — 재귀 폴더/파일 트리 (접기/펼치기) |
| `24SevenClaw-web/src/components/projects/wizard/steps/file-content-viewer.tsx` | 새 파일 — 파일 내용 뷰어 (라인넘버 + 복사) |
| `24SevenClaw-web/src/components/projects/wizard/steps/step-preview.tsx` | 새 파일 — 메인 프리뷰 패널 (2-column + 요약 + 다운로드) |
| `24SevenClaw-web/src/components/projects/wizard/steps/index.ts` | `StepReview` → `StepPreview` export 교체 |
| `24SevenClaw-web/src/app/(dashboard)/projects/new/page.tsx` | `StepReview` → `StepPreview` 참조 교체 |

**구현 내용:**
- 설정 요약 카드: 6개 스텝 데이터를 아이콘 + 라벨로 한 줄 요약
- 프리뷰 API 호출: `POST /api/v1/projects/{id}/preview` → 파일 트리 + 내용 수신
- FileTreePreview: 재귀 트리, depth < 2 자동 펼침, 폴더 클릭 접기/펼치기
- FileContentViewer: 라인넘버, 언어 감지, 클립보드 복사 기능
- DownloadButton: `POST /api/v1/projects/{id}/generate` → Blob → 파일 저장
- 2-column 레이아웃: 좌(240px 파일트리) / 우(파일 내용), 400px 높이

**테스트 결과:**
- TypeScript: `tsc --noEmit` ✅
- 빌드: `npm run build` ✅

**남은 이슈:**
- ESLint 설정이 비정상 (`next lint`가 동작하지 않음 — 기존 이슈)
- `step-review.tsx` 파일은 아직 삭제하지 않음 (사용처 없으므로 cleanup 대상)
- 프리뷰 API 호출 시 `project_id`에 "draft" 사용 — API 측에서 draft 처리 필요
