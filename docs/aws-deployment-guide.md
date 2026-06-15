# ClickEye AWS 배포 가이드 (ECS Fargate)

> ClickEye 클라우드(`clickeye-api` + `clickeye-web`)를 AWS ECS Fargate 위에 올리는 단계별 가이드.
> 데이터 저장소는 관리형(RDS PostgreSQL + ElastiCache Redis)을 사용한다.
> 리전 예시는 서울(`ap-northeast-2`) 기준이며, `<...>` 표기는 환경에 맞게 치환한다.
>
> 🟢 **AWS가 처음이거나 데모/소규모로 빠르게 띄우고 싶다면** 이 Fargate 가이드보다
> [EC2 1대 초보자 가이드](./aws-deployment-guide-ec2.md)가 훨씬 쉽다. 본 문서는 본격 운영용이다.

---

## 0. 범위 & 아키텍처

### 배포 대상
| 서비스 | 기술 | 포트 | 헬스체크 | 클라우드 배포 |
|--------|------|------|----------|---------------|
| `clickeye-api` | FastAPI (uvicorn) | 8000 | `/api/v1/health` | ✅ Fargate |
| `clickeye-web` | Next.js 15 (standalone) | 3000 | `/` | ✅ Fargate |
| `clickeye-agent` | Python 데몬 | — (outbound WSS only) | — | ❌ **고객 서버에서 실행** |

> **`clickeye-agent`는 본 가이드 범위에서 제외한다.** Agent는 고객 인프라에서 실행되며
> 클라우드 API로 **outbound `wss://` 연결만** 맺는다(인바운드 포트 없음). 클라우드에는 Agent가
> 접속할 WebSocket 엔드포인트(`/ws/agent`)만 노출하면 된다(아래 ALB 라우팅 참조).

### 타깃 아키텍처

```
                          Internet
                              │
                       Route53 (A alias)
                              │
                   ┌──────────▼───────────┐
                   │   ALB (HTTPS:443)     │  ACM 인증서
                   │   HTTP:80 → 443 리다이렉트 │
                   └──────────┬───────────┘
            ┌─────────────────┼──────────────────┐
   리스너 규칙:  /api/*, /ws/*           기본(/)
            │                                    │
   ┌────────▼─────────┐              ┌──────────▼────────┐
   │ TG: api (8000)   │              │ TG: web (3000)    │
   │ ECS Service api  │              │ ECS Service web   │
   │ (Fargate, priv)  │              │ (Fargate, priv)   │
   └───┬─────────┬────┘              └───────────────────┘
       │         │
 ┌─────▼───┐ ┌───▼──────────┐
 │  RDS    │ │ ElastiCache  │
 │ Postgres│ │   Redis      │
 │ (priv)  │ │  (priv)      │
 └─────────┘ └──────────────┘

이미지: ECR  ·  시크릿: Secrets Manager  ·  로그: CloudWatch Logs
```

핵심 원칙: **api와 web을 같은 도메인**에 둔다(`/api/*`, `/ws/*` → api / 나머지 → web).
CORS·인증 설정이 단순해지고, Next.js의 빌드타임 API URL 문제(아래 4-3)도 완화된다.

---

## 1. 사전 준비

### 1-1. 계정/도구
- AWS 계정 + 관리자급 IAM 사용자(또는 배포용 권한 Role)
- 로컬에 설치: **AWS CLI v2**, **Docker**, (선택) `jq`
- `aws configure` 로 자격증명/기본 리전(`ap-northeast-2`) 설정

```bash
aws sts get-caller-identity   # 계정/권한 확인
export AWS_REGION=ap-northeast-2
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR=${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
```

### 1-2. 도메인 & 인증서(ACM)
- 도메인 예시: `app.clickeye.io`(web+api 단일 도메인). Agent는 `wss://app.clickeye.io/ws/agent`로 접속.
- Route53에 호스팅 영역이 있다고 가정.
- **ACM에서 ALB와 같은 리전(`ap-northeast-2`)에 인증서 발급** (CloudFront를 쓸 경우만 us-east-1 필요 — 본 가이드는 ALB 직결이라 서울 리전).

```bash
aws acm request-certificate \
  --domain-name app.clickeye.io \
  --validation-method DNS \
  --region $AWS_REGION
# 콘솔/CLI로 DNS 검증 CNAME을 Route53에 추가 → 상태 ISSUED 확인
```

---

## 2. 네트워킹 (VPC)

ECS Fargate·RDS·Redis는 **private 서브넷**, ALB는 **public 서브넷**에 둔다.

권장 구성(2 AZ):
- VPC 1개 (예: `10.0.0.0/16`)
- public 서브넷 ×2 (ALB, NAT GW)
- private 서브넷 ×2 (Fargate tasks, RDS, ElastiCache)
- **NAT Gateway** ×1+ : private 서브넷의 Fargate가 ECR/Secrets Manager로 아웃바운드 풀링하기 위해 필요
  - 비용을 줄이려면 NAT 대신 **VPC 인터페이스 엔드포인트**(`ecr.api`, `ecr.dkr`, `secretsmanager`, `logs`) + **S3 게이트웨이 엔드포인트**(ECR 레이어용) 구성 가능

> 빠르게 시작하려면 콘솔 **VPC → Create VPC → "VPC and more"** 마법사로 2 AZ + NAT 포함 구성을 한 번에 생성하는 것이 가장 간단하다.

### 2-1. 보안 그룹 (체인)
| SG | 인바운드 | 비고 |
|----|----------|------|
| `sg-alb` | 80, 443 ← 0.0.0.0/0 | 인터넷 → ALB |
| `sg-web` | 3000 ← `sg-alb` | ALB → web task |
| `sg-api` | 8000 ← `sg-alb` | ALB → api task (HTTP + WS 동일 포트) |
| `sg-rds` | 5432 ← `sg-api` | api → PostgreSQL |
| `sg-redis` | 6379 ← `sg-api` | api → Redis |

아웃바운드는 기본(전체 허용) 유지 — Fargate가 ECR/Secrets/외부 API(Anthropic 등)에 접근.

---

## 3. ECR 이미지 빌드 & 푸시

### 3-1. 레포지토리 생성
```bash
aws ecr create-repository --repository-name clickeye-api  --region $AWS_REGION
aws ecr create-repository --repository-name clickeye-web  --region $AWS_REGION
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR
```

> ⚠️ **CPU 아키텍처 고정**: Fargate 기본은 `X86_64`다. 로컬 빌드 호스트(특히 Apple Silicon/arm)에서
> arm64 이미지가 만들어지면 태스크가 `exec format error`로 죽는다. 아래 빌드 명령에 모두
> `--platform linux/amd64`를 명시하고, task definition에도 `runtimePlatform`을 맞춘다(§6-2).

### 3-2. API 이미지
빌드 컨텍스트는 `clickeye-api`, Dockerfile은 infra의 `Dockerfile.api`를 사용한다.
```bash
cd /path/to/ClickEye
docker build \
  --platform linux/amd64 \
  -f clickeye-infra/docker/Dockerfile.api \
  -t $ECR/clickeye-api:latest \
  clickeye-api
docker push $ECR/clickeye-api:latest
```

### 3-3. Web 이미지 — ⚠️ 빌드타임 환경변수 주의 (중요)

Next.js의 `NEXT_PUBLIC_*`와 `AUTH_URL`은 **`npm run build` 시점에 번들에 인라인**된다.
**런타임 env 주입은 효과가 없다.** (현재 `docker-compose.prod.yml`이 web에 `NEXT_PUBLIC_API_URL`을
런타임 env로 넣고 있으나, 이 값은 클라이언트 번들에 반영되지 않는다.)

현재 `clickeye-infra/docker/Dockerfile.web`에는 빌드 ARG가 없으므로, **아래처럼 ARG를 추가**해야
운영 도메인을 주입할 수 있다(가이드 적용 시 1회 수정 필요):

```dockerfile
# Dockerfile.web (builder 스테이지의 npm run build 앞에 추가)
ARG NEXT_PUBLIC_API_URL
ARG AUTH_URL
ARG NEXT_PUBLIC_FEATURE_MODERNIZE_ENABLED=false
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    AUTH_URL=$AUTH_URL \
    NEXT_PUBLIC_FEATURE_MODERNIZE_ENABLED=$NEXT_PUBLIC_FEATURE_MODERNIZE_ENABLED
RUN npm run build
```

그 후 운영 도메인으로 빌드(단일 도메인 권장):
```bash
docker build \
  --platform linux/amd64 \
  -f clickeye-infra/docker/Dockerfile.web \
  --build-arg NEXT_PUBLIC_API_URL=https://app.clickeye.io \
  --build-arg AUTH_URL=https://app.clickeye.io \
  -t $ECR/clickeye-web:latest \
  clickeye-web
docker push $ECR/clickeye-web:latest
```

> 단일 도메인(`/api/*` → api)으로 라우팅하므로 `NEXT_PUBLIC_API_URL`을 web과 같은 도메인으로 두면
> CORS가 사실상 same-origin이 되어 단순해진다.

---

## 4. 데이터 저장소 (관리형)

### 4-1. RDS PostgreSQL 16
- 엔진: PostgreSQL 16, 인스턴스: 시작은 `db.t4g.micro`~`small`
- **Multi-AZ**(운영) 권장, 자동 백업 활성화
- private 서브넷 그룹 + `sg-rds`
- DB 이름 `clickeye`, 마스터 사용자 `clickeye`

연결 문자열(asyncpg 드라이버 필수):
```
DATABASE_URL=postgresql+asyncpg://clickeye:<PASSWORD>@<rds-endpoint>:5432/clickeye
```
> RDS는 SSL을 권장한다. SQLAlchemy+asyncpg의 SSL 파라미터 형식은 `?ssl=require`(libpq) 표기와
> 다를 수 있으니, 적용 전 SQLAlchemy create_async_engine의 `connect_args={"ssl": ...}` 또는
> URL 쿼리 형식을 실제 버전 기준으로 확인한다.

### 4-2. ElastiCache Redis 7
- 엔진: Redis 7, 노드 `cache.t4g.micro`부터
- private 서브넷 그룹 + `sg-redis`
- (간단히 시작하려면 클러스터 모드 비활성화)

```
REDIS_URL=redis://<elasticache-primary-endpoint>:6379
```
> 전송 중 암호화(in-transit) 활성화 시 `rediss://` 스킴을 사용한다.

---

## 5. Secrets Manager (환경변수 주입)

민감값은 Secrets Manager에 저장하고 ECS task definition의 `secrets`로 주입한다.

```bash
aws secretsmanager create-secret --name clickeye/api \
  --secret-string '{
    "DATABASE_URL":"postgresql+asyncpg://clickeye:<PW>@<rds>:5432/clickeye",
    "REDIS_URL":"redis://<redis>:6379",
    "JWT_SECRET_KEY":"<랜덤-강한-시크릿>",
    "ANTHROPIC_API_KEY":"<선택>"
  }' --region $AWS_REGION

aws secretsmanager create-secret --name clickeye/web \
  --secret-string '{ "AUTH_SECRET":"<랜덤-강한-시크릿>" }' --region $AWS_REGION
```

> **태스크 실행 역할(execution role)**에 해당 시크릿 읽기 권한(`secretsmanager:GetSecretValue`)과
> ECR/CloudWatch 권한(`AmazonECSTaskExecutionRolePolicy`)을 부여해야 한다.

### 환경변수·시크릿 매핑표

**clickeye-api** (`clickeye-api/.env.example`, `app/config.py` 기준)
| 변수 | 필수 | 출처 | 값/주의 |
|------|------|------|---------|
| `DATABASE_URL` | ✅ | Secret | RDS 엔드포인트, `postgresql+asyncpg://…` |
| `REDIS_URL` | ✅ | Secret | ElastiCache 엔드포인트 |
| `JWT_SECRET_KEY` | ✅ | Secret | 운영용 강한 랜덤값 |
| `CORS_ORIGINS` | ✅ | env | `["https://app.clickeye.io"]` (web 오리진) |
| `PUBLIC_API_URL` | ✅ | env | `https://app.clickeye.io` — **생성 ZIP에 각인**되므로 운영 URL 필수 |
| `DEBUG` | — | env | `false` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | — | env | 기본 30 |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | — | env | 기본 7 |
| `ANTHROPIC_API_KEY` | 선택 | Secret | AI 코드생성 사용 시 |
| `FEATURE_MODERNIZE_ENABLED` | 선택 | env | 기본 false |
| `GITHUB_APP_*` | 선택 | Secret | Modernize/GitHub 연동 시 |
| `FRONTEND_URL` | 선택 | env | OAuth 리다이렉트용, `https://app.clickeye.io` |

**clickeye-web** (`clickeye-web/.env.example` 기준)
| 변수 | 필수 | 출처 | 값/주의 |
|------|------|------|---------|
| `NEXT_PUBLIC_API_URL` | ✅ | **빌드 ARG** | `https://app.clickeye.io` (빌드타임 인라인) |
| `AUTH_URL` | ✅ | **빌드 ARG**(+런타임 env 권장) | `https://app.clickeye.io` |
| `AUTH_SECRET` | ✅ | Secret(런타임) | 세션 암호화 키 |
| `AUTH_TRUST_HOST` | ✅ | env(런타임) | **`true` 필수** — ALB에서 TLS가 종료되어 컨테이너는 평문 HTTP를 본다. 없으면 Auth.js v5가 forwarded host를 신뢰하지 않아 로그인/콜백 URL이 깨진다(로그인 시도 전까지 조용히 잠복) |
| `NEXT_PUBLIC_FEATURE_MODERNIZE_ENABLED` | 선택 | 빌드 ARG | 기본 false |

---

## 6. ECS Fargate 배포

### 6-1. 클러스터 & 로그 그룹
```bash
aws ecs create-cluster --cluster-name clickeye --region $AWS_REGION
aws logs create-log-group --log-group-name /ecs/clickeye-api --region $AWS_REGION
aws logs create-log-group --log-group-name /ecs/clickeye-web --region $AWS_REGION
```

### 6-2. Task Definition (예시 — api)
`requiresCompatibilities: FARGATE`, `networkMode: awsvpc`. 컨테이너 헬스체크/로그/시크릿 포함.

```jsonc
{
  "family": "clickeye-api",
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "512", "memory": "1024",
  "runtimePlatform": { "cpuArchitecture": "X86_64", "operatingSystemFamily": "LINUX" },
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "containerDefinitions": [{
    "name": "api",
    "image": "<ECR>/clickeye-api:latest",
    "portMappings": [{ "containerPort": 8000 }],
    "environment": [
      { "name": "DEBUG", "value": "false" },
      { "name": "CORS_ORIGINS", "value": "[\"https://app.clickeye.io\"]" },
      { "name": "PUBLIC_API_URL", "value": "https://app.clickeye.io" }
    ],
    "secrets": [
      { "name": "DATABASE_URL",   "valueFrom": "arn:aws:secretsmanager:...:clickeye/api:DATABASE_URL::" },
      { "name": "REDIS_URL",      "valueFrom": "arn:aws:secretsmanager:...:clickeye/api:REDIS_URL::" },
      { "name": "JWT_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:...:clickeye/api:JWT_SECRET_KEY::" }
    ],
    "healthCheck": {
      "command": ["CMD-SHELL", "python -c \"import urllib.request;urllib.request.urlopen('http://localhost:8000/api/v1/health')\""],
      "interval": 30, "timeout": 5, "retries": 3, "startPeriod": 15
    },
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/clickeye-api",
        "awslogs-region": "<REGION>",
        "awslogs-stream-prefix": "api"
      }
    }
  }]
}
```
web용 task definition도 동일 패턴(`image: clickeye-web`, `containerPort: 3000`,
`runtimePlatform` 동일, 헬스체크 `wget --spider http://localhost:3000/`,
환경변수 `AUTH_TRUST_HOST=true`, 시크릿 `AUTH_SECRET`).

```bash
aws ecs register-task-definition --cli-input-json file://taskdef-api.json --region $AWS_REGION
aws ecs register-task-definition --cli-input-json file://taskdef-web.json --region $AWS_REGION
```

### 6-3. ALB + 타깃 그룹 + 리스너 규칙
- 타깃 그룹 2개 (`target-type: ip`, Fargate awsvpc이므로 IP 타깃)
  - `tg-api`: 포트 8000, 헬스체크 경로 `/api/v1/health`
  - `tg-web`: 포트 3000, 헬스체크 경로 `/`
    - 현재 web의 `/`는 리다이렉트 없는 랜딩 페이지로 **200**을 반환한다(미들웨어/locale 경로 프리픽스 없음) → 기본 매처(200)로 정상. 추후 `/`가 리다이렉트로 바뀌면 ALB 타깃이 healthy가 안 되니, 그 경우 매처를 `200-399`로 두거나 200 보장 경로로 변경한다.
- HTTPS:443 리스너(ACM 인증서) — **기본 액션 = `tg-web`**
- 리스너 규칙(우선순위 순):
  - 경로 `/api/*` → `tg-api`
  - 경로 `/ws/*` → `tg-api`  ← **Agent WebSocket(`/ws/agent`) 경로. 필수.**
- HTTP:80 리스너 → 443으로 리다이렉트

> ALB는 HTTP/HTTPS 리스너에서 WebSocket을 기본 지원한다(별도 설정 불필요).
> 단, WS 연결 유지를 위해 ALB **idle timeout**을 충분히(예: 300s+) 늘리는 것을 권장한다.

### 6-4. ECS 서비스 생성
각 서비스를 private 서브넷 + 해당 SG로 생성하고 타깃 그룹에 연결한다.
```bash
aws ecs create-service --cluster clickeye --service-name api \
  --task-definition clickeye-api --desired-count 2 --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<priv-a>,<priv-b>],securityGroups=[<sg-api>],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=<tg-api-arn>,containerName=api,containerPort=8000" \
  --health-check-grace-period-seconds 60 --region $AWS_REGION

aws ecs create-service --cluster clickeye --service-name web \
  --task-definition clickeye-web --desired-count 2 --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<priv-a>,<priv-b>],securityGroups=[<sg-web>],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=<tg-web-arn>,containerName=web,containerPort=3000" \
  --health-check-grace-period-seconds 60 --region $AWS_REGION
```

---

## 7. DB 마이그레이션 (1회성 run-task)

api 이미지에 alembic이 포함되어 있으므로, 동일 이미지로 **명령만 덮어써** 1회 실행한다.
```bash
aws ecs run-task --cluster clickeye \
  --task-definition clickeye-api --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<priv-a>,<priv-b>],securityGroups=[<sg-api>],assignPublicIp=DISABLED}" \
  --overrides '{"containerOverrides":[{"name":"api","command":["/app/.venv/bin/alembic","upgrade","head"]}]}' \
  --region $AWS_REGION
```
> 마이그레이션은 api 서비스 첫 배포 **전** 또는 직후 1회 실행한다. 시드 프리셋은 앱 기동 시
> 자동(멱등)으로 삽입된다.

---

## 8. 도메인 & TLS 연결

- Route53에서 `app.clickeye.io` **A 레코드(Alias)** → ALB DNS 이름으로 연결
- ALB 443 리스너에 ACM 인증서가 붙어 있는지 확인
- `https://app.clickeye.io` 접속 → web 표시, `https://app.clickeye.io/api/v1/health` → `{"status":"healthy"}`

---

## 9. 배포·검증·롤백

### 검증 체크리스트
```bash
# 헬스
curl -s https://app.clickeye.io/api/v1/health        # {"status":"healthy", db/redis ok}
curl -sI https://app.clickeye.io/                    # 200 (web)
# 서비스 상태
aws ecs describe-services --cluster clickeye --services api web \
  --query 'services[].{name:serviceName,running:runningCount,desired:desiredCount}' --region $AWS_REGION
```
- ALB 타깃 그룹에서 api/web 타깃이 **healthy** 인지 확인
- Agent 연결 테스트: 고객 측 `CLICKEYE_CLOUD_WS_URL=wss://app.clickeye.io` 로 설정 후 `/ws/agent` 연결 확인

### 새 버전 배포(롤링)
```bash
# 새 이미지 push (예: :v2) → 새 task def 리비전 등록 → 서비스 업데이트
aws ecs update-service --cluster clickeye --service api \
  --task-definition clickeye-api:<NEW_REV> --region $AWS_REGION
```
ECS는 기본 롤링 업데이트(헬스체크 통과 후 교체)로 무중단 배포한다.

### 롤백
```bash
aws ecs update-service --cluster clickeye --service api \
  --task-definition clickeye-api:<PREV_REV> --region $AWS_REGION
```
이전 task definition 리비전으로 되돌리면 즉시 롤백된다.

---

## 10. 비용 개략 & 후속 과제

### 대략 비용(서울, 최소 구성 기준 — 변동 가능)
| 항목 | 메모 |
|------|------|
| Fargate api×2 + web×2 | vCPU/메모리 사용량 비례. 초기엔 desired-count 1로 절감 가능 |
| ALB | 시간당 + LCU |
| RDS `db.t4g.micro` Multi-AZ | 단일 AZ로 시작하면 절반 |
| ElastiCache `cache.t4g.micro` | |
| NAT Gateway | 시간당 + 데이터 처리. VPC 엔드포인트로 대체 시 절감 |

> 비용 최적화: 초기엔 단일 AZ·desired-count 1·NAT 대신 VPC 엔드포인트 조합으로 시작하고,
> 트래픽 증가 시 Multi-AZ/오토스케일링으로 확장.

### 후속 과제(본 가이드 범위 밖)
- **CI 자동 배포**: GitHub Actions에서 ECR 빌드&푸시 → `ecs update-service` (OIDC 역할 사용). 현재 `.github/workflows/ci.yml`에는 이미지 빌드/푸시 단계가 없음.
- **IaC**: Terraform으로 VPC/ALB/ECS/RDS/Redis 코드화(반복 배포·재현성).
- **오토스케일링**: ECS Service Auto Scaling(CPU/요청 수 기준).
- **`Dockerfile.web` 빌드 ARG 반영**(4-3) — 운영 도메인 주입을 위해 필요.
- **관측성**: CloudWatch 대시보드/알람, (선택) X-Ray.

---

## 부록: 자주 막히는 지점
- **web에서 API 호출이 localhost로 감** → `NEXT_PUBLIC_API_URL`을 빌드타임에 안 넣음(4-3 참조).
- **Fargate 태스크가 ECR 이미지 못 받음** → private 서브넷에 NAT/VPC 엔드포인트 누락, 또는 실행 역할 권한 부족.
- **api가 DB 연결 실패** → `sg-rds` 인바운드에 `sg-api` 누락, 또는 `DATABASE_URL` 드라이버가 `+asyncpg` 아님.
- **Agent 연결 안 됨** → ALB 리스너에 `/ws/*` → api 규칙 누락, 또는 ALB idle timeout 짧음.
- **CORS 차단** → api `CORS_ORIGINS`에 web 오리진 미포함(단일 도메인이면 same-origin이라 무관).
- **로그인/콜백 URL이 깨짐** → web에 `AUTH_TRUST_HOST=true` 누락(ALB TLS 종료로 컨테이너가 평문 HTTP를 봄).
- **태스크가 `exec format error`로 죽음** → 이미지가 arm64로 빌드됨. `--platform linux/amd64` + task def `runtimePlatform` 확인.
