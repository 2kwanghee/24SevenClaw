# 구현 플랜

## 목표
1. Linear 자격증명을 유저 단위 → 프로젝트 단위로 전환
2. ZIP에 `/ClickEyeRemove` 명령어 및 `remove.sh` 추가
3. ZIP에 `log/` 폴더 + 로깅 프로세스 추가

---

## 변경 파일 목록

### Issue 1 — Linear 자격증명 프로젝트별 관리

**현재 구조 (문제)**
- `user_linear_credentials` 테이블: user_id UNIQUE → 유저당 1개
- 위저드에서 `linearCredentials.save()` → 기존 값 덮어씀
- 프로젝트 삭제 시 자격증명 그대로 유지
- 새 프로젝트 생성 시 이전 자격증명 재사용

**변경 구조**
- `project_linear_credentials` 테이블 신규 생성 (project_id FK + CASCADE DELETE)
- `user_linear_credentials` 는 글로벌 설정용으로 유지 (settings/linear 페이지)
- `push_to_linear` → 프로젝트 자격증명 우선, 없으면 유저 자격증명 폴백
- 위저드 finalize → 프로젝트 자격증명에 저장

**변경 파일:**
- `clickeye-api/app/models/project_linear_credentials.py` (신규)
- `clickeye-api/app/models/__init__.py` (임포트 추가)
- `clickeye-api/alembic/versions/024_project_linear_credentials.py` (신규 마이그레이션)
- `clickeye-api/app/api/v1/integrations.py` (register_initial_tasks → 프로젝트 자격증명 저장)
- `clickeye-api/app/api/v1/review_pipeline.py` (push_to_linear → 프로젝트 자격증명 우선 조회)
- `clickeye-api/app/schemas/integrations.py` (project_id 필드 추가)
- `clickeye-web/src/app/(dashboard)/solutions/new/page.tsx` (finalize 시 project_id 포함 저장)

### Issue 2 — /ClickEyeRemove 명령어 + remove.sh

**변경 파일:**
- `clickeye-api/app/engine/templates/commands/clickeye-remove.md.j2` (신규)
- `clickeye-api/app/engine/templates/remove.sh.j2` (신규)
- `clickeye-api/app/engine/generator.py` (remove.sh, clickeye-remove.md 파일 목록 추가)

**remove.sh 동작:**
1. 실행 중인 webhook_server, linear_watcher 프로세스 종료
2. .env 초기화 (key 값 비움)
3. Linear webhook 등록 해제 (API 호출)
4. log/ 폴더 내용 보존 여부 확인 후 처리
5. 완료 메시지 출력

### Issue 3 — log/ 폴더 + 로깅

**변경 파일:**
- `clickeye-api/app/engine/templates/scripts/webhook_server.py.j2` (로깅 추가)
- `clickeye-api/app/engine/templates/scripts/linear_watcher.py.j2` (로깅 추가)
- `clickeye-api/app/engine/generator.py` (log/ 디렉토리 + .gitkeep 추가)

**로그 구조:**
```
log/
├── webhook.log      # Linear webhook 수신 이벤트
├── watcher.log      # linear_watcher 폴링 로그
└── pipeline.log     # 파이프라인 실행 전체 로그
```

---

## 구현 단계

1. [모델] `project_linear_credentials.py` 생성
2. [마이그레이션] Alembic 마이그레이션 파일 생성
3. [API] `integrations.py` — register_initial_tasks에서 프로젝트 자격증명 저장
4. [API] `review_pipeline.py` — push_to_linear에서 프로젝트 자격증명 우선 사용
5. [템플릿] `remove.sh.j2` 생성
6. [템플릿] `clickeye-remove.md.j2` 생성
7. [템플릿] `webhook_server.py.j2` 로깅 추가
8. [템플릿] `linear_watcher.py.j2` 로깅 추가
9. [엔진] `generator.py` — 신규 파일 목록 등록

## 예상 영향 범위

- `push_to_linear` 동작 변경: 프로젝트 자격증명 우선 → 호환성 유지됨 (폴백 있음)
- 기존 유저 자격증명(`/settings/linear`) 동작 변경 없음
- ZIP 생성 구조 변경: 파일 2개 추가, 기존 파일 수정
