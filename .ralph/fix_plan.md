# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] Step 8 API Key 실시간 유효성 검증 UI 구현**
  > 요청사항: ## 작업 목적

Step 8 환경변수 입력 UI에서 Linear/Notion API Key 입력 필드에 **실시간 유효성 검증** 피드백을 추가한다. 사용자가 잘못된 키를 입력한 채로 다음 단계로 진행하는 것을 사전에 차단한다.

## UX 흐름

```
사용자가 API Key + Team ID/DB ID 입력
  → [검증하기] 버튼 클릭 (또는 두 필드 모두 입력 완료 시 자동 트리거)
  → 로딩 스피너 표시
  → 성공: ✅ 초록 뱃지 + "Linear 연결 완료: {team_name}"
  → 실패: ❌ 빨간 뱃지 + 에러 메시지
  → 다음 버튼: 검증 성공 시에만 활성화
```

## 구현 명세

### 검증 상태 타입

```typescript
type ValidationState = "idle" | "loading" | "success" | "error";

interface ValidationResult {
  state: ValidationState;
  message?: string;  // 성공: "팀명" or "DB명", 실패: 에러 설명
}
```

### 검증 트리거 조건

* Linear: `LINEAR_API_KEY` AND `LINEAR_TEAM_ID` 모두 입력 완료 시 자동 트리거 (debounce 1초)
* Notion: `NOTION_API_KEY` AND `NOTION_DATABASE_ID` 모두 입력 완료 시 자동 트리거 (debounce 1초)

### API 호출

```typescript
// lib/api-client.ts에 추가
const validateLinear = async (apiKey: string, teamId: string) =>
  POST("/api/v1/integrations/linear/validate", { api_key: apiKey, team_id: teamId });

const validateNotion = async (apiKey: string, databaseId: string) =>
  POST("/api/v1/integrations/notion/validate", { api_key: apiKey, database_id: databaseId });
```

### canProceed 변경

기존: 빈 문자열만 체크
변경: 빈 문자열 + **검증 상태가 "success"** 인 경우에만 true

```typescript
case 8: {
  const ev = data.env.envVars;
  if (!ev["ANTHROPIC_API_KEY"]?.trim()) return false;

  if (data.agents.selectedSkills.includes("linear")) {
    if (!ev["LINEAR_API_KEY"]?.trim() || !ev["LINEAR_TEAM_ID"]?.trim()) return false;
    if (linearValidation.state !== "success") return false;  // 추가
  }

  if (data.agents.selectedSkills.includes("notion")) {
    if (!ev["NOTION_API_KEY"]?.trim() || !ev["NOTION_DATABASE_ID"]?.trim()) return false;
    if (notionValidation.state !== "success") return false;  // 추가
  }

  return true;
}
```

### UI 컴포넌트 구조

각 통합 섹션(Linear/Notion) 하단에 검증 상태 표시 영역 추가:

```tsx
{/* 검증 중 */}
<div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
  <Loader2 className="h-4 w-4 animate-spin" />
  <span>연결 확인 중...</span>
</div>

{/* 성공 */}
<div className="flex items-center gap-2 text-sm text-emerald-400">
  <CheckCircle2 className="h-4 w-4" />
  <span>Linear 연결 완료: {teamName}</span>
</div>

{/* 실패 */}
<div className="flex items-center gap-2 text-sm text-red-400">
  <AlertCircle className="h-4 w-4" />
  <span>{errorMessage}</span>
</div>
```

## 참조 파일

* `src/components/solutions/wizard/steps/step-solution-env.tsx` — 수정 대상
* `src/app/(dashboard)/solutions/new/page.tsx` — canProceed Step 8 로직 수정
* `src/app/(dashboard)/solutions/[sessionId]/page.tsx` — 동일하게 수정

## 완료 기준

- Linear 필드 입력 완료 시 자동 검증 실행 (debounce 1초)
- Notion 필드 입력 완료 시 자동 검증 실행
- 검증 중 로딩 스피너 표시
- 검증 성공 시 ✅ + 팀명/DB명 표시
- 검증 실패 시 ❌ + 구체적 에러 메시지 표시
- 검증 미완료/실패 시 다음 버튼 비활성화
- API Key 변경 시 검증 상태 초기화 (idle로 리셋)

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|