---
title: AWS EC2 배포 가이드 (초보자용)
category: guide
status: current
last_updated: 2026-07-22
related:
  - clickeye-infra/docker-compose.prod.yml
  - clickeye-infra/managed/api.env
  - clickeye-api/app/services/ops/env_service.py
  - clickeye-api/app/services/ops/docker_client.py
---

# ClickEye AWS 배포 가이드 — EC2 1대 (초보자용)

> **이 문서는 AWS를 처음 다루는 사람을 위한 가장 쉬운 배포 경로다.**
> EC2 가상 컴퓨터 **1대**를 만들고, 그 안에서 `docker-compose.prod.yml` 하나로
> DB·Redis·API·Web을 **전부 한 번에** 실행한다.
> 운영 규모가 커지면 ECS Fargate(관리형 컨테이너) 기반 구성으로 넘어가는 것을 고려한다.
>
> - 적합: 데모, 내부 테스트, 소규모 운영, "일단 떠 있는 걸 보고 싶다"
> - 부적합: 고가용성/오토스케일이 필요한 본격 운영 → ECS Fargate 등 관리형 컨테이너 구성 고려
> - 리전 예시: 서울(`ap-northeast-2`). `<...>` 표기는 환경에 맞게 치환한다.

---

## 🧭 전체 그림

```
[내 노트북] ──SSH접속──> [EC2 서버 1대 (Ubuntu 리눅스)]
                              └─ docker compose up 한 줄
                                   ├─ web  (3000)  ← 브라우저가 보는 화면
                                   ├─ api  (8000)  ← 백엔드 API
                                   ├─ postgres     ← 데이터베이스
                                   └─ redis        ← 캐시
```

핵심: **EC2 = AWS가 빌려주는 빈 컴퓨터 한 대.** 우리가 할 일은 ①빌리고 ②들어가서
③Docker 깔고 ④코드 올리고 ⑤`docker compose` 한 줄로 실행. 그게 전부다.
관리형 컨테이너(ECS Fargate) 구성에서 쓰는 ECR·RDS·ElastiCache·ALB·Secrets Manager는 **하나도 필요 없다**
(DB·Redis도 컨테이너로 같은 서버에서 함께 돈다).

### 먼저 알아둘 AWS 용어 5개
| 용어 | 한 줄 뜻 | 일상 비유 |
|------|---------|----------|
| **EC2 인스턴스** | 빌리는 가상 컴퓨터 1대 | 월세 PC |
| **AMI** | 그 PC에 깔 운영체제(OS) 이미지 | "우분투 깔아주세요" |
| **인스턴스 타입** | PC 사양(CPU/RAM) | `t3.medium` = 2코어·4GB |
| **키 페어(.pem)** | SSH 접속용 열쇠 파일 | 그 PC의 디지털 열쇠 |
| **보안 그룹** | 방화벽 규칙 | "어떤 문(포트)을 열까" |

---

## 1단계: EC2 인스턴스 만들기 (콘솔 클릭)

1. AWS 콘솔 로그인 → 우측 상단 **리전을 `서울 (ap-northeast-2)`** 로 설정.
2. 검색창에 **EC2** → EC2 대시보드 → 주황색 **`Launch instance`(인스턴스 시작)**.
3. 위에서부터 채운다:
   - **Name(이름)**: `clickeye-server`
   - **AMI(OS)**: **Ubuntu Server 24.04 LTS** (Quick Start 탭)
   - **Instance type(사양)**: **`t3.medium`** 권장
     > ⚠️ 왜 medium? Next.js 빌드가 메모리를 많이 써서 `t3.micro`(1GB)·`small`(2GB)에선
     > 빌드 중 멈출(OOM) 수 있다. 4GB(medium)면 안전. 비용을 아끼려면 small로 시작하되,
     > 빌드가 실패하면 인스턴스를 끄고 타입만 medium으로 올리면 된다.
   - **Key pair(열쇠)**: **`Create new key pair`** → 이름 `clickeye-key`, RSA, `.pem`
     → **`Create`** → `clickeye-key.pem` 다운로드.
     > **이 파일은 다시 받을 수 없다. 잘 보관할 것.** (서버 접속 열쇠)
   - **Network settings(방화벽)**: 오른쪽 **`Edit`** → 2단계 참조
   - **Storage(디스크)**: 기본 8GB는 작다 → **30 GiB (gp3)** 로 변경
4. 우측 **`Launch instance`** → 완료.

---

## 2단계: 보안 그룹 = 방화벽 열기

위 Network settings에서 **`Create security group`** 선택하고 인바운드 규칙 4개를 추가:

| Type | Port | Source | 의미 |
|------|------|--------|------|
| SSH | 22 | **My IP** | 나만 서버에 접속(보안 권장) |
| HTTP | 80 | Anywhere (0.0.0.0/0) | 나중에 도메인 붙일 때 |
| Custom TCP | 3000 | Anywhere | 웹 화면 접속(테스트용) |
| Custom TCP | 8000 | Anywhere | API 접속(테스트용) |

> 처음엔 3000·8000을 열어 브라우저에서 바로 확인하고, 나중에 도메인+nginx로 정리할 때
> 닫으면 된다. SSH(22)는 **My IP**로 두는 게 안전하다(집/회사 IP가 바뀌면 이 규칙만 수정).

생성 후 인스턴스 목록에서 **Public IPv4 address**(예: `3.34.xxx.xxx`)를 확인한다. 이게 서버 주소다.

---

## 3단계: 서버에 접속 (SSH)

내 노트북 터미널에서 (`.pem` 파일이 있는 폴더에서):

```bash
chmod 400 clickeye-key.pem                       # 열쇠 권한 잠그기 (1회)
ssh -i clickeye-key.pem ubuntu@<서버_Public_IP>
```
> `ubuntu@`는 Ubuntu AMI의 기본 계정. 처음 접속 시 `yes` 한 번 입력.
> 접속되면 프롬프트가 `ubuntu@ip-...:~$` 로 바뀐다. 이제 그 안은 리눅스 컴퓨터다.

---

## 4단계: Docker 설치 (서버 안에서)

```bash
sudo apt-get update
curl -fsSL https://get.docker.com | sudo sh   # Docker 공식 설치 스크립트
sudo usermod -aG docker ubuntu                # sudo 없이 docker 사용
exit                                          # 그룹 권한 반영 위해 재접속
```
다시 `ssh -i clickeye-key.pem ubuntu@<IP>` 로 들어와 확인:
```bash
docker --version
docker compose version
```

---

## 5단계: 코드를 서버로 올리기

```bash
git clone <ClickEye 레포 주소>
cd ClickEye
```
> private 레포면 토큰/배포키가 필요하다. git 접근이 까다로우면 노트북에서 직접 복사도 가능:
> `scp -i clickeye-key.pem -r ./ClickEye ubuntu@<IP>:~/`
> (단 `node_modules`, `.next` 등 큰 폴더는 제외하고 보낼 것)

---

## 6단계: 환경변수(.env) 작성

compose 파일이 읽을 `.env`를 **compose 파일과 같은 폴더**에 만든다:

```bash
cd clickeye-infra/docker
nano .env       # 아래 내용 붙여넣고 값 채우기 → Ctrl+O, Enter, Ctrl+X
```

```bash
# --- DB ---
POSTGRES_DB=clickeye
POSTGRES_USER=clickeye
POSTGRES_PASSWORD=<강한_비밀번호_직접지정>

# --- 보안 키 (서버에서 `openssl rand -hex 32` 로 생성 추천) ---
JWT_SECRET_KEY=<랜덤_긴_문자열>
AUTH_SECRET=<랜덤_긴_문자열_또다른값>   # web 로그인 세션 암호화 키

# --- 주소 (서버 공인 IP!) ---
NEXT_PUBLIC_API_URL=http://<서버_Public_IP>:8000
AUTH_URL=http://<서버_Public_IP>:3000
CORS_ORIGINS=["http://<서버_Public_IP>:3000"]
```

`docker-compose.prod.yml`이 사용하는 변수: `POSTGRES_DB`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`,
`AUTH_URL`, `AUTH_SECRET` (포트는 기본값 5432/6379/8000/3000 사용).

---

## 7단계: ⚠️ 알아둘 함정 — web 주소 빌드타임 인라인 (이미 코드에 반영됨)

Next.js의 `NEXT_PUBLIC_API_URL`·`AUTH_URL`은 **"실행할 때"가 아니라 "빌드할 때" 코드에 박힌다.**
런타임 환경변수로만 넘기면 **브라우저 쪽 코드엔 반영되지 않는다.** (관리형 컨테이너 구성에서도 동일한 빌드타임 주입 이슈.)

> ✅ **이 함정은 이미 코드에 처리되어 있다.** `Dockerfile.web`에 빌드 ARG가 들어가 있고
> `docker-compose.prod.yml`이 `build.args`로 `NEXT_PUBLIC_API_URL`·`AUTH_URL`을 빌드타임에 주입한다.
> 또한 web 서비스에 `AUTH_SECRET`·`AUTH_URL`·`AUTH_TRUST_HOST=true`가 런타임 env로 설정되어 로그인도 동작한다.
>
> **그래서 당신이 따로 코드를 고칠 필요는 없다.** 6단계 `.env`에 `NEXT_PUBLIC_API_URL`·`AUTH_URL`·
> `AUTH_SECRET`을 **운영 주소/값으로 정확히 채우기만** 하면 된다. (값을 바꾸면 8단계 `--build`로 다시
> 빌드해야 번들에 반영된다 — 런타임 재시작만으론 클라이언트 코드가 안 바뀐다.)

---

## 8단계: 전부 실행

```bash
# clickeye-infra/docker 폴더에서
docker compose -f docker-compose.prod.yml up -d --build
```
- `--build`: 우리 코드로 이미지 직접 빌드 (첫 실행 5~10분, 정상)
- `-d`: 백그라운드 실행

확인:
```bash
docker compose -f docker-compose.prod.yml ps          # 5개 다 Up/healthy 인지
docker compose -f docker-compose.prod.yml logs -f api  # 로그 (Ctrl+C로 빠져나옴)
```

### ⚠️ DB 마이그레이션 — Migrate One-Shot 게이트 (CE-305)

**중요**: 8단계 `docker compose up`을 실행하면, `migrate` 서비스가 **자동으로** `alembic upgrade head`를 실행한다.
따라서 별도의 마이그레이션 명령어는 불필요하다. 

```bash
# 마이그레이션 상태 확인 (선택)
docker compose -f docker-compose.prod.yml logs migrate
```

> - `migrate`는 **one-shot 서비스**: DB 마이그레이션 완료 후 자동으로 Exit 0이 되며, 
>   API 서비스가 대기했다가 마이그레이션 성공을 확인한 후 부팅된다.
> - 로컬/배포 모두 동일한 게이트를 쓴다 (멱등성 보장).
> - 시드 프리셋은 API 앱 기동 시 멱등적으로 자동 삽입된다.

### 관리형 환경변수 (CE-305)

docker-compose 파일의 `.env`로는 부족한 경우, 운영 중 환경변수를 변경하고 싶을 수 있다.
**Superadmin 운영 패널**에서 관리형 env CRUD를 할 수 있다:

1. **조회**: `GET /api/v1/admin/ops/env` → Fernet 암호화된 변수들
2. **수정**: `PUT /api/v1/admin/ops/env/{key}` → 새 값 저장
3. **삭제**: `DELETE /api/v1/admin/ops/env/{key}`
4. **적용**: `POST /api/v1/admin/ops/env/render` → 수동 적용 명령 미리보기
   > **주의**: 명령어는 미리보기만 반환하며, docker 컨테이너는 **자동으로 재시작되지 않는다.**
   > 환경변수 변경 후 반영하려면 수동으로 `docker compose restart` 해야 한다.

### 내부망 Docker API (CE-305)

docker-compose에 `dockerproxy` 서비스가 포함되어 있다. 이는 기본적으로 **POST 요청을 차단**하는 read-only 프록시다.
Superadmin 패널의 "컨테이너 조회"(`GET /admin/ops/containers`) 기능이 이를 통해 컨테이너 상태를 조회한다.
외부망에서 접근 불가(내부망 전용).

---

## 9단계: 브라우저에서 확인

- `http://<서버_Public_IP>:8000/api/v1/health` → `{"status":"healthy"}` → 백엔드 OK
- `http://<서버_Public_IP>:3000` → 웹 화면 → 프론트 OK

여기까지면 **배포 성공.** 🎉

---

## 회사 기존 인스턴스 참고법

똑같이 따라 만들 필요는 없지만, **재사용하면 편한 것**:
1. **키 페어** — 기존 `.pem`이 있으면 1단계에서 그것을 선택(열쇠 일원화).
2. **VPC/서브넷** — 회사 VPC를 그대로 선택해도 되고, 모르면 `default` VPC로 둔다
   (인터넷 되는 public 서브넷 1개면 충분).

기존 인스턴스 설정 구경: EC2 목록 → 인스턴스 클릭 → 하단 **Security**(보안 그룹),
**Networking**(VPC/서브넷) 탭에서 회사 관례 확인 가능. 다만 ClickEye용 EC2는
독립적으로 새로 만드는 게 깔끔하니 참고만 하면 된다.

---

## 비용 개략 (서울, 변동 가능)

| 항목 | 메모 |
|------|------|
| EC2 `t3.medium` | 24시간 켜두면 월 수만 원대. 안 쓸 땐 **중지(stop)** 하면 과금 줄어듦 |
| EBS 디스크 30GB | 소액 |
| 데이터 전송(아웃바운드) | 트래픽 비례 |

> Fargate 구성(ALB+RDS+ElastiCache+NAT)보다 **훨씬 저렴**하다. 대신 가용성/오토스케일은 없다.

---

## 다음 단계 (지금은 몰라도 됨)

| 하고 싶어지면 | 방법 |
|--------------|------|
| `:3000` 없이 도메인 접속 | 80포트 + nginx 리버스 프록시, 도메인 A레코드 연결 |
| https 자물쇠 | Let's Encrypt(certbot) 무료 인증서 |
| 서버 재부팅돼도 자동 실행 | compose에 `restart: always` 이미 있음 → 자동 복구 |
| 본격 운영(고가용성) | ECS Fargate(관리형 컨테이너) + ALB + RDS/ElastiCache 구성으로 이전 |

---

## 부록: 자주 막히는 지점
- **SSH 접속 거부** → 보안 그룹 22번이 내 IP에 안 열림, 또는 `.pem` 권한이 `chmod 400` 안 됨.
- **빌드 중 서버가 멈춤/느림** → 메모리 부족(OOM). `t3.medium` 이상으로 올리거나 swap 추가.
- **web에서 API 호출이 localhost로 감** → 7단계 빌드 ARG 미적용.
- **브라우저에서 화면이 안 뜸** → 보안 그룹 3000/8000 미개방, 또는 컨테이너가 `healthy` 아님(`logs` 확인).
- **api가 DB 연결 실패** → `.env`의 `POSTGRES_*` 값 누락/오타, 또는 마이그레이션 미실행.
- **디스크 가득 참** → `docker system prune -a`로 미사용 이미지 정리, 또는 EBS 볼륨 확장.
