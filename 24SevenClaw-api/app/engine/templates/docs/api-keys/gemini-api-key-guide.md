# Gemini API 키 발급 가이드

## 1. Google AI Studio 접속

1. [aistudio.google.com](https://aistudio.google.com) 접속
2. Google 계정으로 로그인

## 2. API 키 발급

1. 좌측 상단 **Get API key** 클릭
2. **Create API key** 클릭
3. 프로젝트 선택 또는 새 프로젝트 생성
4. 생성된 키 복사

발급된 키 형식: `AIza...`

## 3. .env 설정

```
GEMINI_API_KEY=AIza여기에붙여넣기
```

## 4. Gemini CLI 설치

```bash
npm install -g @google/gemini-cli
```

## 5. Gemini CLI 인증

### API 키 방식 (추천)

```bash
export GEMINI_API_KEY=AIza...
gemini
```

### OAuth 방식

```bash
gemini  # 처음 실행 시 브라우저 로그인 진행
```

## 6. 24SevenClaw와 함께 사용

ZIP 압축 해제 후:

```bash
cd 프로젝트-폴더
gemini  # Gemini CLI 실행
```

Gemini CLI 실행 후:
```
/24SeventStart
```

## 요금 안내

- **무료 티어**: 분당 15회 요청, 일 1,500회 (개발 테스트 충분)
- **유료**: 월 $20부터 (고성능 작업 시)
- Google AI Studio 무료 사용으로 시작 권장

## 지원 모델

| 모델 | 특징 |
|------|------|
| `gemini-2.5-pro` | 최고 성능, 복잡한 코딩 |
| `gemini-2.0-flash` | 빠른 응답, 일반 작업 |

## 문제 해결

- `API_KEY_INVALID`: 키 형식 확인 (AIza로 시작)
- `QUOTA_EXCEEDED`: 무료 티어 한도 초과 → 잠시 후 재시도
- `gemini: command not found`: npm 전역 설치 확인
