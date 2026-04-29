# Anthropic API 키 발급 가이드

## 1. Anthropic 계정 생성

1. [console.anthropic.com](https://console.anthropic.com) 접속
2. **Sign Up** 클릭 → 이메일 인증 완료

## 2. API 키 발급

1. 로그인 후 좌측 메뉴 **API Keys** 클릭
2. **Create Key** 버튼 클릭
3. 키 이름 입력 (예: `clickeye-dev`)
4. 생성된 키를 즉시 복사 — **다시 확인 불가**

발급된 키 형식: `sk-ant-api03-...`

## 3. .env 설정

```
ANTHROPIC_API_KEY=sk-ant-api03-여기에붙여넣기
```

## 4. 청구 설정 (필수)

API를 사용하려면 결제 수단을 등록해야 합니다.

1. 좌측 메뉴 **Billing** 클릭
2. **Add payment method** → 카드 등록
3. **Usage Limits** 탭에서 월 한도 설정 권장 (예: $20)

## 요금 안내

- Claude Sonnet 4: $3 / 1M input tokens, $15 / 1M output tokens
- Claude Haiku 4: $0.25 / 1M input tokens, $1.25 / 1M output tokens
- 개발 초기: 일반적으로 월 $5~20 수준

## 문제 해결

- `401 Unauthorized`: 키가 올바른지, 만료되지 않았는지 확인
- `429 Too Many Requests`: 요금제 한도 확인 또는 잠시 후 재시도
- `402 Payment Required`: 청구 설정 필요
