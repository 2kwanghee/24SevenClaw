---
title: 하이브리드 러너 — 컨테이너 헤드리스 PoC + 동시성 실측 (CE-297)
category: reference
status: current
last_updated: 2026-07-15
related:
  - .ralph/fix_plan.md
  - .ralph/tasks/CE-297.md
  - clickeye-infra/docker
---

# 하이브리드 러너 — 컨테이너 헤드리스 PoC + 동시성 실측 (CE-297)

Phase 0 SPIKE 결과 메모. 하이브리드 실행 설계(데스크탑 러너=구독 시트 + 클라우드 컨테이너=조직 API 키)의 전제를 검증한다.

## 배경

현재 자동 개발 파이프라인은 `ANTHROPIC_API_KEY`를 unset하고 claude.ai 구독 시트(브라우저 로그인 세션)로 `claude` CLI를 실행한다. 하이브리드 구조의 "클라우드 팔"이 성립하려면 컨테이너 안에서 조직 API 키로 `claude -p`(헤드리스) 실행이 가능해야 한다.

## 1. 컨테이너 조직-키 헤드리스 실행 가능 여부 — **조건부 가능**

`node:20-slim` 이미지에 `npm install -g @anthropic-ai/claude-code`(설치 ~7초, CLI 버전 2.1.197 — 로컬 2.1.210 대비 약간 낮음, 버전 고정 검토 필요)로 구성 후, 브라우저 로그인 세션 없이 `ANTHROPIC_API_KEY` 환경변수만 주입한 상태로 `claude -p "..."`를 실행했다.

- **인증 메커니즘 자체는 검증됨**: `x-api-key` 인증만으로 CLI가 정상 기동해 Anthropic API까지 도달했다 (커스텀 Dockerfile 불필요, 글로벌 npm install만으로 충분).
- 단, 이번 PoC에 사용한 조직 API 키는 **크레딧 잔액 부족**(`Credit balance is too low`)으로 실제 응답까지는 받지 못했다. 이는 인증 실패가 아니라 별도의 계정 상태 문제다.
- **결론**: 헤드리스 컨테이너 실행 경로 자체는 기술적으로 유효. 실응답 검증은 크레딧 충전 후 재확인 필요.

## 2. API 동시성 상한(TPM/RPM) 실측 — **측정 불가 (크레딧 선행 필요)**

`/v1/messages`에 최소 토큰 요청을 보냈으나 크레딧 부족으로 HTTP 400(`invalid_request_error`)이 레이트리밋 판정 이전 단계에서 반환되어 `anthropic-ratelimit-*` 헤더(requests-limit, tokens-limit 등)가 전혀 내려오지 않았다. 확인된 것은 `anthropic-organization-id`(조직 식별 성공) 뿐.

- **후속 조치**: 해당 조직 API 키에 크레딧을 충전한 뒤 동일 curl 절차로 재실측 필요 (절차는 아래 재현 방법 참조).

## 3. 구독 시트(claude.ai Team/Enterprise 좌석) 수 — **실측 불가, API/CLI로 조회 불가능**

리포지토리 전체(`docs/`, `.env`, README 등) grep 결과 좌석/시트 수 기록 없음. 이 값은 API나 CLI로 조회할 방법이 없고 **Anthropic Console 조직 관리자 페이지에서 사람이 직접 확인**해야 한다.

## 완료 기준 대비 상태

| 완료 기준 | 상태 | 비고 |
|---|---|---|
| 컨테이너 조직-키 헤드리스 실행 가능 여부 | ✅ 확인 (조건부: 인증 O, 실응답은 크레딧 필요) | |
| 동시성 상한 실수치 (시트 수, TPM/RPM) | ❌ 미확정 | 크레딧 충전 + 콘솔 확인 선행 필요 (사람 액션) |
| 데스크탑 러너 앞당김 판단 (P2 vs P3) | ⏸ 보류 | 위 수치 없이는 "구독 시트가 초기 동시성의 몇 %를 담당하는지" 계산 불가 |

## 영향 / 후속 조치 (사람 액션 필요)

1. **조직 API 키에 크레딧 충전** (Anthropic Console billing) → 본 문서의 curl 절차로 TPM/RPM 헤더 재실측
2. **Anthropic Console에서 claude.ai 구독 시트 수 확인**
3. 위 두 수치 확보 후 데스크탑 러너(P2) vs 하이브리드 러너(P3) 배치 순서를 재판단하고 본 문서를 갱신

이 항목들이 채워지기 전까지 §3 리소스 거버넌스 설계와 데스크탑 러너 스케줄 확정은 블로킹 상태다.

## 재현 방법

```bash
# 1) 헤드리스 컨테이너 PoC
docker run --rm -e ANTHROPIC_API_KEY="$(grep '^ANTHROPIC_API_KEY=' .env | cut -d= -f2-)" \
  node:20-slim bash -c "npm install -g @anthropic-ai/claude-code >/dev/null 2>&1 && claude -p 'hello, respond with just OK'"

# 2) API 레이트리밋 헤더 실측 (응답 헤더만 출력 — 요청 헤더/키 값 노출 없음)
curl -sS -D - -o /dev/null https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-haiku-20241022","max_tokens":8,"messages":[{"role":"user","content":"hi"}]}'
```
