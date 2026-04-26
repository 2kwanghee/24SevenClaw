# Claude Code 구독 및 설정 가이드

## 요금제 비교

| 요금제 | 월 요금 | Claude Code 사용 | 특징 |
|--------|---------|-----------------|------|
| **Pro** | $20/월 | ✅ 포함 | 개인 개발자 추천 |
| **Max** | $100/월 | ✅ 포함 (5x 더 많이) | 대용량 작업 추천 |
| **API** | 사용량 과금 | ✅ API 키로 사용 | 팀/자동화 추천 |
| Free | $0 | ❌ 미포함 | Claude.ai 기본 사용만 |

> **추천**: 개발 초기에는 **Pro ($20/월)** 로 시작하세요.

## 1. 구독 방법

1. [claude.ai](https://claude.ai) 접속 → 로그인
2. 좌측 하단 **Upgrade** 클릭
3. Pro 또는 Max 선택 → 결제 정보 입력

## 2. Claude Code CLI 설치

```bash
npm install -g @anthropic-ai/claude-code
```

## 3. Claude Code 인증

```bash
claude
```

처음 실행 시 브라우저가 열려 로그인 요청이 나타납니다.
claude.ai 계정으로 로그인하면 자동으로 인증됩니다.

### API 키 방식 (팀/자동화 환경)

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
claude --api-key $ANTHROPIC_API_KEY
```

또는 `.env` 파일에 설정:
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

## 4. ClickEye와 함께 사용

ZIP 압축 해제 후:

```bash
cd 프로젝트-폴더
claude  # Claude Code 실행
```

Claude Code 실행 후 슬래시 커맨드 입력:
```
/ClickEyeStart
```

## 문제 해결

- `claude: command not found`: npm 전역 설치 확인 (`npm install -g @anthropic-ai/claude-code`)
- 인증 오류: `claude logout` 후 재로그인
- API 키 오류: `.env`의 `ANTHROPIC_API_KEY` 값 확인
