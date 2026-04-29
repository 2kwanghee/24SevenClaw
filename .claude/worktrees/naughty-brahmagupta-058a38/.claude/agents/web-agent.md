# Web Agent — ClickEye Frontend Development Guide

> 이 파일은 clickeye-web 모듈 개발 시 Claude Code가 참조하는 전담 가이드입니다.
> 레포 초기화 시 `clickeye-web/CLAUDE.md`로 복사합니다.

## Tech Stack
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS + shadcn/ui
- **State**: Zustand (client) + TanStack Query v5 (server)
- **Forms**: React Hook Form + Zod
- **Auth**: Auth.js v5 (JWT strategy)
- **API Client**: @hey-api/openapi-ts 자동 생성

## Directory Structure
```
src/
├── app/                    # Next.js App Router (페이지)
│   ├── (auth)/             # 인증 관련 페이지 그룹
│   ├── (dashboard)/        # 대시보드 페이지 그룹
│   └── api/                # API 라우트 (Auth.js)
├── components/
│   ├── ui/                 # shadcn/ui 원시 컴포넌트 (수정 금지)
│   ├── layout/             # 레이아웃 컴포넌트 (sidebar, header)
│   ├── projects/           # 프로젝트 관련 컴포넌트
│   ├── registry/           # 레지스트리 관련 컴포넌트
│   └── common/             # 공통 컴포넌트
├── hooks/                  # 커스텀 훅 (use-*.ts)
├── stores/                 # Zustand 스토어
├── lib/                    # 유틸리티 (api-client, auth, utils)
└── types/                  # 타입 정의 (contracts에서 import 우선)
```

## Coding Rules

### 컴포넌트 작성
- **Server Component 우선**: 기본은 Server Component, 상호작용 필요 시에만 `'use client'`
- **파일 네이밍**: kebab-case (`project-card.tsx`, `use-projects.ts`)
- **Export**: named export 사용 (default export는 page.tsx만)
- **Props**: interface로 정의, `{ComponentName}Props` 네이밍

```typescript
// 좋은 예
interface ProjectCardProps {
  project: Project;
  onSelect?: (id: string) => void;
}

export function ProjectCard({ project, onSelect }: ProjectCardProps) {
  // ...
}
```

### 상태 관리
- **서버 데이터**: TanStack Query 사용 (절대 Zustand에 서버 데이터 저장 금지)
- **UI 상태**: Zustand 사용 (사이드바 열림, 필터 상태 등)
- **URL 상태**: searchParams 사용 (페이지네이션, 정렬, 필터)

```typescript
// hooks/use-projects.ts
export function useProjects(params: ProjectListParams) {
  return useQuery({
    queryKey: ['projects', params],
    queryFn: () => apiClient.projects.list(params),
  });
}
```

### API 호출
- **자동 생성 클라이언트**: `lib/api-client.ts`에서 import (직접 fetch 금지)
- **에러 핸들링**: TanStack Query의 onError + toast 알림
- **Optimistic Update**: 목록 CRUD에 적용

### 스타일링
- **Tailwind 유틸리티 클래스 사용**: 커스텀 CSS 파일 최소화
- **shadcn/ui 컴포넌트 우선**: 직접 만들기 전에 shadcn에 있는지 확인
- **반응형**: 모바일 우선 (`sm:`, `md:`, `lg:` 순서)
- **다크 모드**: `dark:` 변형 지원

### 폼 처리
```typescript
// Zod 스키마 정의 → React Hook Form에 연결
const projectSchema = z.object({
  name: z.string().min(1, '프로젝트 이름을 입력하세요'),
  description: z.string().optional(),
});

type ProjectFormData = z.infer<typeof projectSchema>;
```

### Auth.js v5 패턴
- 세션 확인: `auth()` (Server) / `useSession()` (Client)
- 보호된 라우트: `middleware.ts`에서 처리
- API 호출 시: 자동으로 JWT 토큰 첨부

## Testing
- **도구**: Vitest + React Testing Library
- **파일 위치**: 컴포넌트 옆 `__tests__/` 디렉토리
- **네이밍**: `{component-name}.test.tsx`
- **범위**: 유저 인터랙션 위주 테스트, 구현 세부사항 테스트 금지

## Performance
- **이미지**: next/image 사용
- **폰트**: next/font 사용
- **동적 임포트**: 무거운 컴포넌트는 `dynamic()` 사용
- **메모이제이션**: 과도한 useMemo/useCallback 금지, 실제 성능 문제 시에만

## UI/UX 작업 시

UI/UX 관련 작업(페이지, 컴포넌트, 레이아웃, 디자인)은 반드시 아래를 따른다:
- **에이전트**: `.claude/agents/uiux-agent.md` 참조
- **스킬**: `/uiux` 스킬 활성화
- **Figma MCP**: 디자인 데이터 조회 후 구현
- **체크리스트**: `.claude/skills/uiux/design-checklist.md` 기반 검증

## Do NOT
- shadcn/ui 컴포넌트 파일 직접 수정
- 서버 데이터를 Zustand에 저장
- fetch를 직접 호출 (자동 생성 클라이언트 사용)
- any 타입 사용
- console.log 커밋 (개발 중에만 사용)
- 인라인 스타일 사용 (Tailwind 사용)
- Figma 디자인 없이 UI 구현 착수 (디자인 없으면 요청)
