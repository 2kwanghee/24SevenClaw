# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] 위저드 티켓 소스(Linear/Notion) XOR 필수 선택 구현**
  > 요청사항: ## 배경

모든 솔루션은 단일 티켓 소스를 가져야 하므로 위저드에서 Linear/Notion 중 정확히 하나를 강제 선택하게 변경.

## 선행 조건

[24S-195](https://linear.app/flow-ops/issue/24S-195/api-카탈로그-notion-스킬-추가-및-zip-템플릿-구현) **완료 후 착수** (카탈로그 API에서 notion + category 응답 필요)

## 작업 내용

### UI (`step-solution-agents.tsx:126-157`)

- "연동 스킬" 섹션을 2개 서브섹션으로 분리
  - 상단: "티켓 소스 (필수, 1개 선택)" — Linear/Notion 라디오 그룹
  - 하단: "추가 스킬 (선택)" — 나머지 카탈로그 스킬 기존 토글 유지
- 카탈로그 `category === "ticket_source"` 항목만 라디오에 노출 (하드코딩 금지)
- 라디오 선택 시 Zustand `selectedSkills`에서 반대편 자동 제거 (XOR 강제)
- 라벨 `(선택)` → `(필수)` 변경 및 안내 문구 추가

### 검증 로직 (`solutions/new/page.tsx:86`)

- agents 케이스 `canProceed`에 조건 추가:
  `selectedSkills.some(s => TICKET_SOURCE_IDS.includes(s))`
- `TICKET_SOURCE_IDS`는 카탈로그 응답에서 동적 도출 (하드코딩 금지)
- 미선택 시 안내 메시지: "티켓 소스(Linear 또는 Notion)를 1개 선택해야 합니다"

### 환경변수 스텝 (`step-solution-env.tsx:31`)

- `NOTION_REQUIRED = ["NOTION_API_KEY", "NOTION_DATABASE_ID"]` 추가
- `getRequiredKeys(selectedSkills)` (`:48-54`)에 notion 분기 추가 — linear와 동일 패턴
- `solutions/new/page.tsx:93-97` env 검증 블록에 notion 분기 추가

### 테스트

- Linear만 선택 → 통과
- Notion만 선택 → 통과
- 미선택 → 다음 스텝 차단
- 둘 다 선택 시도 → 반대편 자동 해제(XOR)
- env 스텝에서 선택 소스에 맞는 키만 필수 표시

## 재사용 가능 코드

* `RequiredKeyRow` (`step-solution-env.tsx:66-171`) — Notion 키 입력 그대로 사용
* `useCatalogSkills` 훅 — 카탈로그에서 자동 로드
* 기존 Zustand `setSkills` 액션

## 관련 파일

* `clickeye-web/src/app/(dashboard)/solutions/new/page.tsx:26-102,172`
* `clickeye-web/src/components/solutions/wizard/steps/step-solution-agents.tsx:126-157`
* `clickeye-web/src/components/solutions/wizard/steps/step-solution-env.tsx:21-54`
* `clickeye-web/src/stores/solution-wizard-store.ts`
* `clickeye-web/src/types/solution-wizard.ts`
* `clickeye-web/src/hooks/use-catalog.ts:17-23`

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | [web] 위저드 티켓 소스 XOR 필수 선택 | ✅ 완료 | 4개 파일 수정, 빌드 통과 |