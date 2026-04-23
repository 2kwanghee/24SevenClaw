# Jira API 설정 가이드

## 1. API Token 발급

1. [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens) 접속
2. **Create API token** 클릭
3. 레이블 입력 (예: `clickeye-agent`)
4. **Create** → 토큰 복사 — **다시 확인 불가**

## 2. Jira 인스턴스 URL 확인

Jira Cloud를 사용하면 URL 형식은 다음과 같습니다:
```
https://yourcompany.atlassian.net
```

## 3. 프로젝트 키 확인

Jira 프로젝트 목록에서 프로젝트 키 확인 (예: `PROJ`, `DEV`, `MYTEAM`).
이슈 번호 앞에 붙는 접두사입니다 (예: `PROJ-123`).

## 4. .env 설정

```
JIRA_URL=https://yourcompany.atlassian.net
JIRA_API_TOKEN=여기에API토큰
JIRA_EMAIL=your@email.com
JIRA_PROJECT_KEY=PROJ
```

## 문제 해결

- `401`: 이메일 + API 토큰 조합 오류 → Atlassian 계정 이메일 사용
- `403`: 해당 프로젝트 접근 권한 없음 → Jira 프로젝트 멤버 여부 확인
- `404`: URL 오류 → `https://yourcompany.atlassian.net` 형식 확인
