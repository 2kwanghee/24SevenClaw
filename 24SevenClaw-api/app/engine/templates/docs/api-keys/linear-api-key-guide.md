# Linear API 키 및 팀 ID 발급 가이드

## 1. Linear 계정 생성

1. [linear.app](https://linear.app) 접속
2. **Sign Up** → 이메일 또는 Google 계정으로 가입
3. 워크스페이스(팀) 생성

## 2. Personal API Key 발급

1. 우측 상단 프로필 → **Settings** 클릭
2. 좌측 메뉴 **API** 섹션 클릭
3. **Personal API keys** → **Create key** 클릭
4. 이름 입력 (예: `24SevenClaw-agent`)
5. 생성된 키 복사 — **다시 확인 불가**

발급된 키 형식: `lin_api_...`

## 3. .env 설정

```
LINEAR_API_KEY=lin_api_여기에붙여넣기
LINEAR_TEAM_ID=여기에팀ID입력
```

## 4. 팀 ID 조회

### 방법 A: URL에서 확인
Linear 앱에서 팀으로 이동하면 URL이 다음과 같습니다:
```
https://linear.app/{워크스페이스}/team/{팀-ID}/issues
```
`{팀-ID}` 부분이 팀 식별자입니다 (예: `MYTEAM`).

### 방법 B: API로 조회
```bash
curl -H "Authorization: lin_api_여기에키" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ teams { nodes { id name key } } }"}' \
  https://api.linear.app/graphql
```
응답에서 `id` 값이 팀 UUID입니다.

## 5. AI Team 연동 설정

24SevenClaw AI Team 화면과 연동하면:
- 세션 생성 → Linear 이슈 자동 등록 (status: Queued)
- 서브태스크 완료 → Linear 이슈 상태 자동 업데이트
- Merge 완료 → Linear 이슈 Done 전환

## 문제 해결

- `401`: API 키 확인 (lin_api_ 접두사 포함 여부)
- `404`: 팀 ID 오류 — API로 팀 목록 재확인
- 권한 오류: 해당 팀의 멤버인지 확인
