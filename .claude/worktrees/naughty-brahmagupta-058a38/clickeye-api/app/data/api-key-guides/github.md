# GitHub Personal Access Token 설정 가이드

## 1. Token 발급

1. GitHub 접속 → 우측 상단 프로필 → **Settings**
2. 좌측 하단 **Developer settings** → **Personal access tokens → Tokens (classic)**
3. **Generate new token (classic)** 클릭
4. Note 입력 (예: `clickeye-agent`)
5. Expiration 설정
6. **Scopes 선택**:
   - `repo` — 코드 읽기/쓰기, PR, Issues
   - `workflow` — GitHub Actions 트리거 (CI/CD 연동 시)
7. **Generate token** → 토큰 복사 — **다시 확인 불가**

## 2. 리포지토리 주소 확인

리포지토리 URL에서 `owner/repo` 형식으로 입력:
```
https://github.com/myorg/my-project
→ GITHUB_REPO=myorg/my-project
```

## 3. .env 설정

```
GITHUB_TOKEN=ghp_여기에토큰
GITHUB_REPO=owner/repository-name
```

## 문제 해결

- `401`: 토큰 만료 또는 scope 부족 → 재발급
- `403`: 해당 리포지토리 접근 권한 없음
- PR 생성 실패: `repo` scope 포함 여부 확인
