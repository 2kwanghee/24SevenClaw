## 목표
Phase 0 Step 2~3 — Helix 전용 PostgreSQL/Redis 컨테이너 격리 기동 + .env 템플릿 정비.

## 변경 파일 목록
- /mnt/c/workspace/helix/helix-infra/docker/docker-compose.yml: 호스트 포트 5432→5433, 6379→6380. 볼륨에 helix_ prefix.
- /mnt/c/workspace/helix/helix-api/.env: 신규 .env 작성 (예제 기반)
- /mnt/c/workspace/helix/helix-web/.env.local: 신규 작성
- /mnt/c/workspace/helix/helix-agent/.env: 신규 작성
- /mnt/c/workspace/helix/.env: 신규 작성 (root 공통)

## 구현 단계
1. docker-compose.yml port + volume edit
2. docker compose up -d db redis (full profile 제외)
3. healthcheck 통과 확인
4. 각 .env.example 검토 후 .env 신규 작성 (실제 API 키는 placeholder, 사용자가 채움)
5. .env에 HELIX_ prefix 변수 + 새 DB/Redis 포트 반영

## 예상 영향 범위
- 기존 ClickEye 운영 컨테이너와 포트 충돌 없음 (helix-* 컨테이너 이름 + 다른 포트)
- 호스트 5433/6380이 비어있어야 함 (충돌 시 다른 포트로 fallback)

## STATUS: APPROVED
