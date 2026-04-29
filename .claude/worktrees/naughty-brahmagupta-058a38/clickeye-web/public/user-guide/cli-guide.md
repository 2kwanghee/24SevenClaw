---
title: CLI 사용법
description: ClickEye CLI 도구의 설치 및 주요 명령어를 안내합니다.
order: 4
---

# CLI 사용법

ClickEye CLI는 파워유저를 위한 커맨드라인 인터페이스입니다. 웹 대시보드와 동일한 생성 엔진을 공유합니다.

## 설치

```bash
npm install -g @clickeye/cli
```

## 기본 명령어

```bash
# 버전 확인
clickeye --version

# 도움말
clickeye --help

# 로그인
clickeye login

# 솔루션 생성
clickeye create

# 솔루션 목록
clickeye list
```

## 솔루션 생성

```bash
# 인터랙티브 모드로 솔루션 생성
clickeye create

# 옵션 지정
clickeye create --platform claude-code --stack nextjs
```

## 설정 파일

CLI 설정은 `~/.clickeye/config.json`에 저장됩니다.

```json
{
  "apiUrl": "https://api.clickeye.io",
  "token": "your-api-token"
}
```

> 상세 내용은 추후 업데이트 예정입니다 (24S-186).
