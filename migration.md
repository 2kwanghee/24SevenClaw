# ClickEye 다프로젝트 딜리버리 전환 전략 가이드

> 문서 성격: 미래 마이그레이션을 준비하기 위한 **기획·전략·Agent 인수인계 문서**
>
> 현재 상태: **설계 대기(IMPLEMENTATION FORBIDDEN)**
>
> 작성 기준일: 2026-07-29
>
> 기준 문서: `docs/multiproject-delivery.md`의 P4·P5

---

## 0. 이 문서를 읽는 Agent에게

이 문서는 지금 코드를 수정하라는 구현 명세가 아니다.

ClickEye의 현재 구조가 완성되고, 외부 CMS에서 전달된 첫 번째 프로덕트가 기존 ClickEye
흐름으로 1차 생성된 뒤에 마이그레이션 계획을 수립하기 위한 전략 가이드다.

다음 조건을 모두 만족하기 전에는 코드, DB, API 계약, WebSocket 계약, 인프라 설정을
변경해서는 안 된다.

1. ClickEye 현행 구조의 완료 범위를 사용자가 확인했다.
2. CMS → Intake → Project → 티켓 → 구현 → 검증의 첫 프로덕트 기준선이 확보되었다.
3. 이 문서의 필수 사용자 인터뷰가 완료되었다.
4. 인터뷰 답변을 반영한 별도의 실행용 마이그레이션 계획을 작성했다.
5. 사용자가 그 실행 계획을 명시적으로 승인했다.

특히 이 문서에 등장하는 모델명, 상태값, API 경로, 파일명은 **미래 설계 후보**다.
현재 코드에 구현되어 있다고 표현하거나, 사용자 승인 없이 생성해서는 안 된다.

### 0.1 금지 범위에서 제외되는 작업 (2026-07-29 추가)

위 금지는 **런타임 동작을 바꾸는 산출물**에 적용된다. 다음은 금지 대상이 아니다.

- 와이어프레임(정적 HTML·이미지·ASCII 목업)
- `docs/pages/`의 페이지 스펙(`status: draft`)
- 이 문서 자체의 실측 정정과 인터뷰 답변 기록

제외 조건은 셋 다 만족해야 한다.

1. `clickeye-api` / `clickeye-web` / `clickeye-agent` / `clickeye-contracts` / `clickeye-infra`의
   소스를 변경하지 않는다.
2. DB migration, API 계약, WebSocket 계약, 인프라 설정을 변경하지 않는다.
3. 산출물이 "구현 완료"로 읽히지 않도록 `status: draft` 또는 구현 금지 표기를 유지한다.

이유: 화면 없이 백엔드 실행 계층만 설계하면 §16 인터뷰 질문(특히 I-05·I-09·I-10)의 답을
사용자가 판단할 근거가 없다. 화면은 인터뷰의 **입력**이지 구현의 시작이 아니다.
상세 순서는 §17의 `Stage 0.5`를 따른다.

---

## 1. 사용자의 의도

ClickEye는 경영·인사·CRM 제품이 아니라 **딜리버리 서비스 구현 플랫폼**이다.

외부 CMS는 개발할 프로덕트를 탐색하고 요구사항을 만든다. ClickEye는 CMS가 전달한
프로덕트를 받아 프로젝트를 생성하고, 연결된 AI 구독 좌석과 실행 Runner를 배정하고,
구현·검증·Docker 테스트 배포·사용자 인수 테스트까지 추적해야 한다.

똑빌더 전체를 복제하는 것이 목적이 아니다. 다음 운영 패턴만 참고한다.

1. 외부 이벤트를 통한 프로젝트 시작
2. 현재 가용 자원을 기준으로 한 배정
3. 프로젝트 온보딩 자동화
4. 사람이 처리해야 하는 외부 작업의 명시적 blocker 관리
5. 프로젝트 진행 상황 모니터링

똑빌더에서 사람이 프로젝트를 수주하고 담당자를 배정하는 자리에, ClickEye에서는
연결된 AI 구독 좌석과 Runner가 들어간다.

### 1.1 절대 추가하지 않을 범위

- 계약·견적·매출·회계
- 직원 인사정보, 평가, 휴가, 근태
- 사람 개발자 배정 및 외주 인력 관리
- 영업 CRM
- 똑빌더 전체 기능 또는 UI 복제
- 외부 CMS 기능의 중복 구현
- 기존 ClickEye 전면 리팩터링
- 기존 데이터의 대규모 재작성

---

## 2. 서비스 경계

### 2.1 외부 CMS의 책임

- 개발 대상 프로덕트 탐색
- 요구사항 작성과 정제
- 기술 스택 및 배포 환경 지정
- 필요한 외부 연동 항목 지정
- ClickEye Intake API 호출
- 프로젝트 소유자에게 외부 연동 준비 요청
- ClickEye가 발급한 테스트 환경과 결과 수신

CMS는 ClickEye의 실행 스케줄러, 작업공간, AI 좌석 인증, Docker 실행기를 구현하지 않는다.

### 2.2 ClickEye의 책임

- Intake 검증과 기존 Project 생성
- 프로젝트별 CONTROL YAML 연결
- DeliveryManifest 검증과 버전 관리
- 구독 좌석과 Runner의 가용성 판단 및 배정
- 프로젝트 작업공간 준비
- 기존 하네스 파일 주입
- 구현 작업 실행과 진행 상태 수집
- 외부 연동 blocker 관리
- 승인된 Docker 빌드·배포·헬스체크
- 사용자 인수 테스트 URL 제공

### 2.3 프로젝트 소유자 또는 사용자의 책임

- 카카오·지도·결제·DNS·SSL·앱스토어 등 외부 계정 개설
- 법적·비즈니스 승인
- Secret Manager에 실제 비밀값 등록
- 테스트 환경 로그인과 인수 테스트
- 최종 승인 또는 보완 요청

---

## 3. 현재 코드 실측 기준선

아래 내용은 마이그레이션 방향을 정하기 위해 현재 저장소에서 확인한 기준선이다.
미래 Agent는 실제 계획 수립 직전에 다시 실측하고, 달라진 내용은 이 문서보다 최신 코드를
우선해야 한다.

| 영역 | 현재 확인된 구조 | 전략적 판단 |
|---|---|---|
| Intake | `clickeye-api/app/models/intake.py`에 요청, idempotency, target, project 연결, 티켓 상태가 존재 | CMS 연계 기반을 재사용한다 |
| Intake 스키마 | `clickeye-api/app/schemas/intake.py`의 `target`은 범용 dict | 기존 요청을 깨지 않고 Manifest envelope를 선택적으로 추가할 수 있다 |
| Project 생성 | `clickeye-api/app/services/intake_service.py`가 승인 시 기존 Project를 생성 | 생성 흐름은 유지하되 Manifest 승격 지점만 후속 검토한다 |
| Project | `clickeye-api/app/models/project.py`에 기존 lifecycle과 `settings` JSON이 존재 | lifecycle은 유지한다. 배포 명세 전체를 settings에 영구 저장하는 것은 피한다 |
| CONTROL YAML | `governance/control.py`, `control_plane_service.py`, `DeliveryProfile`이 정책·게이트·재시도·동시성을 제어 | 정책 제어면으로 유지하고 런타임 명세와 분리한다 |
| 하네스 생성 | `clickeye-api/app/engine/generator.py`가 Agent·Skill·Guide 파일을 생성 | 새 생성 엔진을 만들지 않고 작업공간 주입에 재사용한다 |
| 사용량 원장 | `LlmUsageLedger`에 프로젝트·task·provider·model·token·cost 등이 존재 | `seat_id` 축을 가산하는 방향을 검토한다 |
| Agent 연결 | `AgentConnection`이 현재 project와 license에 묶여 있다 | 다프로젝트 공용 Runner에 바로 사용할 수 없는 핵심 격차다 |
| WebSocket | Agent register·heartbeat·status·log·result 계약이 존재 | 계약을 교체하지 않고 선택 필드를 가산한다 |
| 결과 영속화 | 현재 status·log·result 처리 일부가 로그 중심이며 job 결과 연결은 미완성 | 실행 원장과 이벤트 저장이 필요하다 |
| Agent 실행 | `runner_handler.py`가 `claude -p` 실행과 로그 전송을 담당 | provider 추상화, 작업공간 준비, 승인 명령 집행이 부족하다 |
| Agent heartbeat | 계약에는 system·environment·active task가 가능하지만 reporter는 idle 중심 | 좌석·Runner 가용성 판단을 위한 실제 telemetry가 부족하다 |
| 환경 구성 | Agent의 environment handler는 완전한 provisioning이 아니다 | 온보딩과 배포 실행을 구현 완료로 간주하면 안 된다 |
| Docker 실행 | build/run 경로가 있으나 stop/destroy와 격리가 완결되지 않았다 | 제품 배포 Runner로 사용하기 전에 lifecycle 보강이 필요하다 |
| 기존 파이프라인 | `scripts/auto_dev_pipeline.sh`와 관련 파일이 저장소 전역 lock·전역 상태를 사용 | 기존 ClickEye 루트에서 병렬화하지 말고 프로젝트별 작업공간에서 실행해야 한다 |
| ClickEye 인프라 | API용 docker proxy는 임의 제품 배포 용도가 아니다 | 제품 배포는 전용 Runner host에서 수행한다 |
| Web | 기존 Intake 콘솔과 Delivery 콘솔이 존재 | 별도 경영 제품을 만들지 않고 실행·연동·배포 패널을 확장한다 |
| Delivery 이벤트 | `DeliveryEvent`가 Intake 체인의 고수준 전이를 기록 | 고빈도 실행 로그는 별도 Job Event에 두고 요약 이벤트만 연결한다 |

### 3.0 초판 이후 실측 정정 (2026-07-29)

초판 작성 시 §3 표와 §9 후보 목록은 실행 계층이 전부 미구현이라는 전제로 작성되었다.
같은 날 실측한 결과 **일부는 이미 구현되어 있다.** 미래 Agent가 중복 모델을 만들지 않도록
아래를 §3 표보다 우선한다.

| 항목 | 초판 서술 | 실측 결과 | 근거 |
|---|---|---|---|
| 구독 시트 | 전부 신규 필요 | **등록형 시트 구현됨** — 사용자당 1개(ToS 방어), 머신 수령, Fernet 암호화 저장. 평문은 등록 요청과 머신 수령 응답에만 존재 | `clickeye-api/app/schemas/seat.py`, `clickeye-api/app/services/seat_service.py` |
| 시트 저장 위치 | 신규 `SubscriptionSeat` table | 신규 table 아님 — 기존 `user_anthropic_credentials`의 `credential_type` 확장으로 수용 | `clickeye-api/app/models/user_anthropic_credentials.py` |
| 프로젝트↔시트 배정 | 미구현 | 배정/해제 API 계약 존재 (`ProjectSeatAssignRequest/Response`) | `clickeye-api/app/schemas/seat.py` |
| 다프로젝트 실행 | 미구현 | **v1 구현됨(순차)** — watcher 프로젝트 필터 + 시트×범위×파이프라인 합성 러너 | `scripts/project_runner.sh`, `scripts/linear_watcher.py` |
| P4 / P5 진행상태 | 설계 대기 | `docs/multiproject-delivery.md`에서 **P4·P5 모두 ✅ 완료(2026-07-29)** 로 표기 | `docs/multiproject-delivery.md` P4·P5 행 |

따라서 미구현으로 남은 실제 격차는 §3.1의 6개 중 다음으로 좁혀진다.

- **병렬** 다프로젝트 실행 (현재 v1은 순차, 병렬은 러너 수평 확장 필요)
- 시트별 레이트 카운터 (선행 과제: 로컬 claude 사용량의 원장 인제스트 배관)
- DeliveryJob·JobEvent 실행 원장 (API 계층)
- Human Integration Gate
- 제품별 Docker 테스트 배포와 인수 테스트

### 3.1 현재 가장 중요한 결론

현재 ClickEye의 핵심 제어·프로젝트·티켓 흐름은 버릴 대상이 아니다. 부족한 것은 다음의
실행 계층이다.

1. 런타임·배포 명세
2. 구독 좌석 가용성 원장과 보수적 배정
3. 프로젝트별 작업공간과 lease
4. 실행 상태·로그·결과의 영속화
5. 외부 연동 blocker
6. 제품별 Docker 테스트 배포

따라서 향후 마이그레이션은 전면 개편이 아니라 **기존 흐름 옆에 실행 계층을 가산하는
방식**이어야 한다.

---

## 4. 반드시 보존할 기존 구조

다음 항목은 재설계하거나 교체하지 않는다.

- `IntakeRequest`와 CMS 연계 API
- `Project` 모델과 기존 lifecycle
- `DeliveryProfile`과 CONTROL YAML 제어면
- 거버넌스 `Policy`와 fail-closed 검증
- 기존 하네스·Agent·Skill 파일 생성 엔진
- `RunnerTaskPayload`의 기존 필수 계약
- `docs/multiproject-delivery.md`의 P0~P3, P6~P9
- 기존 티켓 발급·완주·정합성 검증 흐름
- 기존 프로젝트에 종속된 Agent 연결 동작
- 기존 Web의 Intake 및 Delivery 콘솔

새 기능은 기존 프로젝트가 아무 설정 변경 없이 계속 동작하도록 Feature Flag 뒤에서
도입한다.

---

## 5. 목표 구조

```text
외부 CMS
  │
  │ 기존 Intake + 선택적 DeliveryManifest
  ▼
ClickEye API
  ├─ 기존 Project / Ticket / CONTROL YAML / Governance
  ├─ DeliveryManifest Registry
  ├─ Human Integration Gate
  ├─ Seat Scheduler
  ├─ DeliveryJob Ledger
  └─ Deployment Ledger
         │
         │ 기존 WebSocket 계약 + 선택 필드
         ▼
신뢰된 Runner
  ├─ 좌석별 인증 홈
  ├─ 프로젝트별 작업공간
  ├─ Claude/Codex CLI 실행
  ├─ Git checkpoint
  ├─ Docker build/compose
  └─ 상태·로그·결과·사용량 보고
         │
         ▼
테스트 URL → 사용자 로그인 인수 테스트
```

### 5.1 핵심 원칙

- CONTROL YAML은 **무엇을 허용하고 어떤 품질 게이트를 통과할지** 결정한다.
- DeliveryManifest는 **무엇을 어떤 환경에서 빌드·실행·검증할지** 기술한다.
- Secret은 **어디에서도 명세 값으로 전달하지 않고 참조만 전달**한다.
- Scheduler는 정확한 잔여 토큰이 아니라 관측된 상태를 근거로 보수적으로 배정한다.
- 좌석 변경은 실행 세션을 순간 이동시키는 것이 아니라 Git checkpoint 경계에서 이어받는다.
- README는 참고 자료이며 실행 권한이 아니다.

---

## 6. 제한적으로 도입할 다섯 가지 기능

### 6.1 DeliveryManifest

DeliveryManifest는 CONTROL YAML과 분리된 프로젝트 런타임·배포 명세다.

포함할 정보:

- 소스 저장소 URL, ref, subdirectory
- 기술 스택
- 개발 대상 OS와 아키텍처
- 배포 OS와 아키텍처
- Dockerfile 또는 Compose 경로
- DB 종류와 버전
- 환경변수의 이름·필수 여부·Secret 여부
- 외부 연동 요구사항
- bootstrap·build·test·migration·healthcheck 명령
- 사용자 인수 테스트 경로와 인증 방식
- CPU·memory·disk 등 Runner 적합성 판단에 필요한 최소 요구
- CMS 작성 주체·버전·서명 또는 hash 등 provenance

포함하지 않을 정보:

- API key, OAuth token, 비밀번호
- `.env` 실제 값
- 좌석 인증 파일
- CONTROL YAML의 정책·재시도·게이트 정의
- README에서 자동 추출한 미승인 shell 명령

#### 명령 표현 원칙

가능하면 shell 문자열 대신 `argv` 배열과 작업 디렉터리를 사용한다.

```yaml
commands:
  build:
    argv: ["npm", "run", "build"]
    working_dir: "."
    shell: false
```

`shell: true`, privilege escalation, host mount, 임의 network 설정 등은 기본 거부한다.
필요하다면 CONTROL 정책 또는 별도 승인 단계가 있어야 한다.

#### 저장 전략 후보

향후 실행 계획에서는 버전·감사·fail-closed를 위해 별도 `DeliveryManifest` 레코드를 우선
검토한다. `Project.settings`는 활성 Manifest 참조나 요약값만 갖도록 하는 편이 안전하다.
다만 이 선택은 데이터 모델 인터뷰와 첫 프로덕트의 실제 payload를 확인한 뒤 확정한다.

### 6.2 Seat Scheduler

Seat는 사람이 아니라 AI 구독 계정의 **실행 가능 단위**다. MVP에서는 하나의 Seat가 하나의
격리된 Runner 프로세스 또는 인증 홈에 대응하고, 동시에 한 개의 작업만 수행한다.

필수 상태:

```text
READY
  └─ 배정 성공 → BUSY

BUSY
  ├─ 정상 종료·checkpoint 성공 → READY
  ├─ rate limit → COOLING_DOWN
  ├─ 인증 만료 → AUTH_REQUIRED
  └─ 운영자 비활성화 → DISABLED

COOLING_DOWN
  ├─ reset 시각 경과 + probe 성공 → READY
  └─ probe 인증 실패 → AUTH_REQUIRED

AUTH_REQUIRED
  └─ 신뢰된 Runner에서 재인증 + probe 성공 → READY

READY / BUSY / COOLING_DOWN / AUTH_REQUIRED
  └─ 운영자 조치 → DISABLED
```

#### 현행 어휘와의 충돌 (2026-07-29 정정)

위 5상태는 **목표 어휘**다. 현재 구현된 시트는 3상태(`active | exhausted | blocked`)를 쓴다
(`clickeye-api/app/schemas/seat.py`). 화면과 API는 임의로 한쪽을 택하지 말고 아래 매핑을 따른다.

| 현행 `seat_status` | 목표 상태 | 판별에 추가로 필요한 관측값 |
|---|---|---|
| `active` (미배정) | `READY` | heartbeat 최신성, 활성 lease 없음 |
| `active` (배정 중) | `BUSY` | 활성 lease 1건 |
| `exhausted` | `COOLING_DOWN` | provider reset 시각 |
| `blocked` (인증 만료) | `AUTH_REQUIRED` | probe 실패 원인 = 인증 |
| `blocked` (운영자 조치) | `DISABLED` | 비활성화 주체·사유 |

즉 목표 5상태는 **신규 column이 아니라 `seat_status` + lease + probe 결과의 파생값**으로
표현할 수 있다. 화면은 파생된 5상태를 보여주되, 그 근거(어느 관측값 때문인지)를 함께
노출해야 한다. 근거 없이 파생 상태만 보여주면 §1.1의 "정확한 잔여량을 아는 척"과 같은
문제가 된다.

Scheduler가 사용하면 안 되는 가정:

- 공급자가 정확한 구독 잔여 토큰 API를 제공한다는 가정
- “토큰이 충분하므로 이 프로젝트는 끝까지 완료된다”는 보장
- 개인 계정 비밀번호를 API DB에 저장해야 한다는 가정
- 하나의 인증 파일을 여러 동시 프로세스가 안전하게 공유한다는 가정

Scheduler가 사용할 관측값:

- 최근 성공·실패 시각
- 실행별 input/output token 관측값
- 최근 rate-limit 오류
- 공급자가 알려준 reset 시각
- heartbeat 최신성
- Runner의 OS·architecture·Docker·DB capability
- 최근 실패율과 cooldown 상태
- 마지막 사용 후 경과 시간

배정은 다음 순서로 한다.

1. provider와 Runner capability가 작업 요구를 만족하는지 hard filter
2. Seat 상태가 `READY`이고 heartbeat가 유효한지 확인
3. cooldown과 기존 lease가 없는지 확인
4. 프로젝트 조직과 Seat 사용 권한 확인
5. 우선순위와 대기 시간으로 Job 정렬
6. 최근 rate limit·실패율·관측 사용량을 반영한 보수적 score 계산
7. DB transaction과 row lock으로 Seat 1개를 lease
8. Seat와 Job 상태를 함께 변경

동시 선택 경쟁은 `SELECT ... FOR UPDATE SKIP LOCKED` 또는 동등한 원자적 lease 방식으로
막는다. 구체 SQL은 실행 계획 단계에서 DB 버전과 ORM 패턴을 확인한 뒤 결정한다.

### 6.3 Workspace Runner

Runner는 프로젝트별로 완전히 구분된 디렉터리를 준비한다.

예시 구조:

```text
/data/clickeye/
  seats/
    <seat_id>/
      auth/                       # 0700, 프로젝트 작업공간 밖
      runtime/
  workspaces/
    <project_id>/
      repo/
      .clickeye/
        manifest/<version>.json
        control/CONTROL.yaml
        jobs/<job_id>/
        locks/project.lock
        runtime/ports.json
      logs/<job_id>/
      artifacts/<job_id>/
      deploy/<deployment_run_id>/
```

Runner의 책임:

- 경로 traversal과 symlink escape를 차단한 디렉터리 생성
- 저장소 clone 또는 CMS 산출물 전개
- 기존 ClickEye 생성 엔진을 통한 하네스 파일 주입
- 프로젝트·branch·lock·log·artifact 격리
- Manifest가 승인한 명령만 실행
- Claude 또는 Codex CLI 실행
- 상태·진행률·로그·결과·관측 사용량 전송
- 실패 시 checkpoint 후 재시도
- Seat 변경 시 Git 기준으로 이어받기
- README 분석 결과를 제안으로만 기록

#### Seat 변경 규칙

살아 있는 CLI 세션을 다른 Seat로 이전하려고 해서는 안 된다.

1. 현재 실행을 중단 가능한 ticket 또는 attempt 경계까지 정리한다.
2. Secret과 인증 파일을 제외하고 Git checkpoint를 만든다.
3. checkpoint commit과 base commit을 Job 원장에 기록한다.
4. 기존 Seat를 cooldown 또는 auth-required로 전환한다.
5. 새 Seat가 같은 branch와 checkpoint에서 새 attempt를 시작한다.

checkpoint에 실패한 dirty workspace는 자동 재배정하지 않고 blocker로 남긴다.

### 6.4 Human Integration Gate

> **정의 (I-08, 2026-07-29 확정).** 여기서 말하는 외부 연동은 **만들어주는 프로덕트에 녹여야
> 하는 연동**이다. ClickEye 자체가 쓰려는 연동이 아니다.
>
> 예: 회사 홈페이지를 만들어준다고 하면 회사 위치를 표시하고 길찾기를 제공해야 한다. AI는 그
> 지도 API 계정을 만들 수 없으므로, **고객(사용자)이 직접 발급해 API KEY를 입력하는 별도
> 작업**이 필요하다. Gate는 그 사람 작업을 추적하는 장치다.
>
> 따라서 담당은 고객(프로젝트 소유자)이고, 1차 알림 채널은 고객이 키를 입력하는 화면과 같은
> 곳(ClickEye Web)이다. 이 기능을 ClickEye의 연동 관리 기능으로 확장해석하지 않는다.

다음은 AI가 계정을 임의로 만들거나 승인할 수 없는 대표 작업이다.

- 카카오 API
- 지도 API
- 결제 모듈과 가맹 심사
- DNS·SSL
- 앱스토어 계정
- 운영용 외부 서비스 계정
- 법적·비즈니스 승인

상태:

```text
REQUIRED
  → AWAITING_OWNER
  → CREDENTIAL_SAVED
  → VALIDATING
  → VERIFIED

VALIDATING → FAILED → AWAITING_OWNER
모든 활성 상태 → BLOCKED
```

Gate마다 구현, 검증, 배포 중 어느 phase를 막는지 기록한다. 예를 들어 결제 운영 key가 없어도
mock으로 구현은 진행할 수 있지만, 실제 결제 검증과 배포는 막을 수 있다.

`CREDENTIAL_SAVED`는 비밀값이 ClickEye DB에 저장되었다는 뜻이 아니다. Secret Manager 또는
Runner 전용 보안 저장소에 저장되었고 ClickEye가 불투명한 `secret_ref`와 fingerprint만
받았다는 뜻이어야 한다.

### 6.5 Deploy Runner

MVP 지원 범위:

- Linux/amd64
- Dockerfile 또는 Docker Compose
- PostgreSQL
- SQLite
- ClickHouse
- HTTP healthcheck
- 테스트 URL 발급
- 사용자의 로그인 인수 테스트

후속 Runner Profile:

- Windows native application
- Windows Container
- RedHat 전용 환경
- 특수 MSSQL 기능
- GPU 또는 특수 하드웨어

개발을 처음부터 Docker 안에서 수행할 필요는 없다. 구현 작업공간과 배포 검증 환경을
분리할 수 있다. 다만 배포 전에는 Manifest로 선언된 환경에서 재현 가능한 build와
healthcheck를 통과해야 한다.

---

## 7. CONTROL YAML과 DeliveryManifest의 책임 분리

| 질문 | CONTROL YAML | DeliveryManifest |
|---|---|---|
| 누가 어떤 방식으로 작업할 수 있는가 | 담당 | 비담당 |
| 자동 정지 조건은 무엇인가 | 담당 | 비담당 |
| 재시도와 동시성 한도는 무엇인가 | 담당 | 비담당 |
| compile·test·check gate는 무엇인가 | 담당 | 명령 참조만 |
| Git 정책과 blocker 정책은 무엇인가 | 담당 | 비담당 |
| 어떤 저장소를 빌드하는가 | 비담당 | 담당 |
| OS·architecture·Docker 방식은 무엇인가 | 비담당 | 담당 |
| DB 종류와 버전은 무엇인가 | 비담당 | 담당 |
| 환경변수 스키마는 무엇인가 | 비담당 | 담당 |
| 외부 연동이 무엇인가 | 허용·차단 정책 | 요구 항목 |
| 실제 Secret 값은 무엇인가 | 절대 저장 금지 | 절대 저장 금지 |
| healthcheck와 인수 테스트 경로는 무엇인가 | 통과 정책 | 실행 명세 |

두 문서가 충돌하면 더 제한적인 결과를 적용하고 fail-closed한다. 예를 들어 Manifest가
shell 실행을 요구하지만 CONTROL 정책이 금지하면 실행하지 않는다.

---

## 8. CMS → ClickEye 계약 전략

기존 Intake 계약을 깨지 않는다. 새 필드는 선택적 envelope로 시작한다.

개념 예시:

```json
{
  "service_key": "기존 방식 유지",
  "idempotency_key": "cms-product-001",
  "requirements": "기존 요구사항",
  "target": {
    "schema_version": "1.0",
    "delivery_manifest": {
      "source": {},
      "stack": {},
      "development": {},
      "deploy": {},
      "databases": [],
      "env_schema": [],
      "integrations": [],
      "commands": {},
      "acceptance": {}
    }
  }
}
```

전략:

1. `delivery_manifest`가 없는 기존 Intake는 지금처럼 처리한다.
2. Feature Flag가 꺼져 있으면 새 실행 기능을 시작하지 않는다.
3. Manifest가 있으면 JSON Schema와 Secret 포함 여부를 검증한다.
4. 기존 Project 생성 lifecycle은 유지한다.
5. Project가 생성되면 Manifest를 별도 버전 레코드로 승격하는 방식을 우선 검토한다.
6. CONTROL YAML 제출은 기존 governance 경로를 유지한다.
7. Scheduler는 Project, 활성 CONTROL, 활성 Manifest, 필요한 Integration Gate가 모두 준비된
   경우에만 Job을 만든다.
8. CMS callback에는 기존 필드를 유지하고 선택적으로 manifest 상태, blocker 요약,
   acceptance URL을 가산한다.

초기 Manifest를 Intake payload에 포함할지, Project 생성 후 별도 PUT으로 제출할지는 첫
CMS 실제 payload와 재전송 전략을 인터뷰한 뒤 확정한다.

---

## 9. 미래 데이터 모델 후보

이 절은 DDL이나 확정 모델이 아니다. 첫 프로덕트 관측 후 실행용 마이그레이션 계획에서
최소 모델로 축소하거나 확정한다.

| 후보 모델 | 목적 | 기존 모델 변경 여부 |
|---|---|---|
| `DeliveryManifest` | 프로젝트별 버전·hash·검증 상태·effective spec | 신규 |
| ~~`SubscriptionSeat`~~ | provider·Runner·credential ref·상태·cooldown | **신규 금지 (§3.0 정정)** — 기존 `user_anthropic_credentials`(`credential_type`)가 이미 등록형 시트를 수용한다. 부족한 축(Runner 연결, cooldown 근거)만 가산 검토 |
| `SeatUsageSample` | 실행별 token 관측·rate limit·reset·confidence | 신규 — 단 선행 과제가 있다. 로컬 claude 사용량의 원장 인제스트 배관 전에는 카운터를 세우지 않는다 |
| `DeliveryJob` | ticket/프로젝트 실행과 lease·attempt·checkpoint | 신규 |
| `DeliveryJobEvent` | 실행 상태·정제 로그·결과의 append-only 이력 | 신규 |
| `HumanIntegrationGate` | 외부 연동 blocker와 검증 상태 | 신규 |
| `DeploymentRun` | Docker build·start·health·URL·rollback 이력 | 신규 |
| `LlmUsageLedger.seat_id` | 기존 비용·token 원장과 Seat 연결 | nullable 가산 후보 |
| `AgentConnection.scope` | 기존 project 전용과 공용 Runner 구분 | default=`project` 가산 후보 |
| `AgentConnection.project_id` | 공용 Runner 허용 | nullable 전환 검토 필요 |
| `AgentConnection.organization_id` | 공용 Runner의 권한 경계 | nullable 가산 후보 |

### 9.1 AgentConnection 변경의 주의점

현재 Agent 연결은 project와 license에 묶여 있어 공용 Runner로 바로 사용할 수 없다.
이를 해결하는 선택지는 두 가지다.

1. 기존 `AgentConnection`에 `scope=project|runner`를 가산하고 runner scope에서
   project/license nullable을 허용한다.
2. 별도 Runner 연결 모델과 endpoint를 만든다.

전면 중복을 피하려면 1번이 우선 후보지만, 인증·라이선스 의미가 바뀌므로 자동 결정해서는
안 된다. 반드시 사용자 인터뷰와 보안 리뷰를 거쳐야 한다. 기존 행은 모두
`scope=project`로 유지되어야 한다.

### 9.2 데이터 원칙

- 모든 DB 변경은 nullable column 또는 신규 table 중심의 가산형이다.
- 기존 행의 대규모 backfill을 요구하지 않는다.
- Secret 값은 어떤 신규 모델에도 넣지 않는다.
- 고빈도 원문 로그는 DB 무제한 적재를 피하고 retention 또는 artifact 저장소를 사용한다.
- 기존 `DeliveryEvent`에는 Job 시작·완료·배포 준비 같은 고수준 요약만 남긴다.

---

## 10. DeliveryJob 상태 머신

```text
QUEUED
  ├─ 선결조건 미충족 → BLOCKED
  └─ 배정 시도 → SCHEDULING

BLOCKED
  └─ Manifest·CONTROL·Integration 해소 → QUEUED

SCHEDULING
  ├─ Seat lease 성공 → LEASED
  └─ 가용 Seat 없음 → QUEUED

LEASED
  → PROVISIONING
  → RUNNING
  → CHECKPOINTING
  → VERIFYING
  → COMPLETED

PROVISIONING / RUNNING / CHECKPOINTING / VERIFYING
  ├─ 재시도 가능 실패 → RETRY_WAIT → QUEUED
  ├─ 재시도 한도 소진 → FAILED
  ├─ 정책 위반 → HALTED
  └─ 명시적 취소 → CANCELLED
```

원칙:

- `FAILED`를 성공 또는 완료로 집계하지 않는다.
- lease에는 만료 시각이 있고 heartbeat로 갱신한다.
- lease 만료 시 즉시 Seat를 READY로 만들지 않고 Runner probe를 거친다.
- 한 프로젝트에 동시에 하나의 변경 Job을 기본값으로 한다.
- read-only 검증 Job의 병렬화는 CONTROL 정책이 명시할 때만 후속 허용한다.
- `task_id`는 기존 Runner 계약과 호환되도록 `DeliveryJob.id`로 사용할 수 있다.

---

## 11. Agent·API·Web 메시지 흐름

```text
1. CMS → API
   기존 Intake 생성 + 선택적 DeliveryManifest

2. API 내부
   Intake 검증 → 기존 Project 생성 → Manifest 검증/활성 후보

3. CMS 또는 제어 서비스 → API
   기존 CONTROL YAML 제출

4. API Scheduler
   선결조건 확인 → DeliveryJob QUEUED → Seat/Runner lease

5. API → Agent WebSocket
   기존 setup_env/build/run/run_task 계약을 우선 재사용
   task_id = DeliveryJob.id

6. Agent
   workspace 준비 → 하네스 주입 → 승인 명령/CLI 실행

7. Agent → API WebSocket
   status / log / result / heartbeat / 사용량 관측

8. API
   JobEvent 저장 → lease 갱신 → Seat 상태/usage 갱신

9. API 기존 흐름
   티켓 완주 → P7 정합성 검증 → 고수준 DeliveryEvent

10. API → Agent
    Integration Gate가 충족된 경우 Docker build/run

11. Agent → API → Web/CMS
    healthcheck 결과 + 테스트 URL + 인수 테스트 대기 상태

12. 사용자 → Web
    로그인 테스트 → 승인 또는 보완 요청
```

### 11.1 계약 호환 원칙

- `RunnerTaskPayload`의 기존 필드를 삭제·변경하지 않는다.
- 새로운 데이터는 처음에는 모두 optional로 가산한다.
- 기존 Agent가 보내지 않는 heartbeat 필드는 정상으로 처리한다.
- 다만 capability가 확인되지 않은 기존 Agent는 신규 Scheduler 후보가 될 수 없다.
- TypeScript와 Python 계약은 항상 contract-first로 함께 변경한다.
- status·log·result의 영속화가 끝나기 전에는 다프로젝트 실행을 활성화하지 않는다.

---

## 12. Secret과 인증 구조

### 12.1 구독 좌석 인증

- 개발자 비밀번호, OAuth token, API key를 ClickEye DB에 저장하지 않는다.
- Seat 인증은 신뢰된 Runner에서 사람이 1회 수행한다.
- ClickEye에는 `seat_id`, provider, Runner 연결, 불투명한 `credential_ref`만 저장한다.
- provider별 인증 홈은 Seat마다 격리한다.
- 인증 파일은 프로젝트 작업공간, Git, 로그, artifact에 포함하지 않는다.
- 인증 만료는 `AUTH_REQUIRED`로 전환하고 사용자 또는 운영자에게 알린다.

### 12.2 프로젝트 외부 연동 Secret

- 중앙 Secret Manager를 우선 사용한다.
- Runner-local 저장소는 이동이 불필요한 제한된 Secret에만 사용한다.
- API는 Secret의 실제 값을 읽거나 응답하지 않는다.
- Runner는 실행 직전에 참조를 resolve하고 child process 또는 Docker secret으로 주입한다.
- 로그 redaction과 환경 dump 금지를 적용한다.
- `.env` 파일이 불가피하면 0600 권한, 작업 종료 후 안전한 폐기, artifact 제외가 필요하다.

### 12.3 반드시 분리할 두 인증

1. Runner가 ClickEye API에 연결하는 Agent 인증
2. Runner가 Claude/Codex 구독을 사용하는 provider 인증

둘을 같은 token이나 같은 저장소로 합치지 않는다.

---

## 13. Docker 배포 lifecycle

```text
REQUESTED
  → PREFLIGHT
  → BUILDING
  → BUILT
  → STARTING
  → HEALTHCHECKING
  → READY_FOR_ACCEPTANCE
  → ACCEPTED
  → STOPPED

오류:
BUILDING / STARTING / HEALTHCHECKING
  → FAILED
  → ROLLING_BACK
  → ROLLED_BACK
```

실행 순서:

1. 활성 Manifest와 CONTROL 정책 재검증
2. 필요한 Integration Gate가 `VERIFIED`인지 확인
3. workspace checkpoint와 clean 상태 확인
4. 프로젝트 전용 Compose namespace, network, volume, port 할당
5. Secret 참조를 resolve
6. image build와 digest 기록
7. 명시된 migration command 실행
8. container 시작
9. HTTP healthcheck와 제한된 smoke test 수행
10. 테스트 URL 발급
11. 사용자 인수 테스트 대기
12. 승인 시 결과 고정, 거부 시 보완 Job 생성

격리 명명 예:

```text
compose project: ce-<project_short_id>-<deployment_short_id>
network/volume/container label: clickeye.project_id, clickeye.deployment_id
```

rollback은 새 container와 network를 정리하되, volume은 Manifest가 disposable로 명시하지
않는 한 자동 삭제하지 않는다. 현재 Agent의 stop/destroy가 완결된 것으로 가정해서는 안 된다.

---

## 14. 가능성 판단

| 기능 | 판단 | 전제 또는 이유 |
|---|---|---|
| CMS 이벤트로 Project 생성 | 가능 | 기존 Intake와 Project 생성 흐름 재사용 |
| CONTROL YAML 연결 | 가능 | 기존 governance 구조 재사용 |
| Manifest 수신과 검증 | 가능 | 선택 필드와 신규 버전 레코드 가산 |
| 프로젝트별 workspace | 가능 | Agent provisioning 보강 필요 |
| Claude/Codex 좌석 배정 | 조건부 가능 | provider 인증 격리와 이용약관·운영정책 확인 필요 |
| 정확한 구독 잔여 token 조회 | 보장 불가능 | 공식 provider API 확인 전 가정 금지 |
| 관측 사용량 기반 보수적 배정 | 가능 | run 결과, rate limit, reset, heartbeat 수집 필요 |
| 실행 중 Seat의 무중단 교체 | 불가능 | checkpoint 경계의 재시작만 가능 |
| 여러 프로젝트 동시 실행 | 가능 | Seat 1개당 1작업, workspace·lock·lease 격리 필요 |
| README 자동 분석 | 가능 | 실행이 아니라 제안·Manifest 보조 용도 |
| README 명령 무검증 실행 | 금지 | 공급망·명령 주입 위험 |
| 카카오·지도·결제 자동 구성 | 조건부 가능 | 계정 발급·심사·동의는 사람 blocker |
| Linux Docker 배포 | 가능 | 전용 Runner host와 lifecycle 보강 필요 |
| PostgreSQL·SQLite·ClickHouse | MVP 가능 | 제품별 버전·backup·migration 명세 필요 |
| MSSQL 일반 지원 | 조건부 | Linux container 기본 기능만 별도 검증 |
| 특수 MSSQL·Windows·RedHat | MVP 불가 | 별도 Runner Profile 필요 |
| GPU·특수 하드웨어 | MVP 불가 | 자원 예약과 전용 host 필요 |
| 사용자 테스트 URL | 가능 | DNS, TLS, port allocation, 접근 정책 결정 필요 |
| 사용자 로그인 인수 테스트 | 가능 | 테스트 계정과 Secret 처리 정책 필요 |

---

## 15. 미래 마이그레이션 착수 조건

다음은 마이그레이션 계획을 쓰기 위한 선행 게이트다.

### Gate A — 현행 ClickEye 기준선 고정

- [ ] 사용자가 “현재 구조 완료”를 선언
- [ ] P0~P3, P6~P9의 실제 구현 상태 재측정
- [ ] 기존 API·DB schema·WebSocket 계약 snapshot 확보
- [ ] 기존 회귀 테스트 결과 확보
- [ ] 미완성 기능과 알려진 결함 목록 확정

### Gate B — 첫 프로덕트 관측

- [ ] CMS가 실제 Intake payload 1건 이상 전송
- [ ] 기존 Project가 생성됨
- [ ] CONTROL YAML이 연결됨
- [ ] 티켓 발급·실행·완주·검증 흐름이 기록됨
- [ ] 실제 repository와 README 구조를 확인
- [ ] 실제 기술 스택·DB·외부 연동·배포 환경을 확인
- [ ] 어디에서 사람이 개입했는지 기록
- [ ] 사용량과 실행 시간의 기준값 확보

### Gate C — 사용자 인터뷰

- [ ] 이 문서의 I-01~I-12 질문에 답변
- [ ] 답변마다 `확정 / 실험 필요 / 보류` 상태 기록
- [ ] 미답변 항목에 Agent가 임의 기본값을 넣지 않음

### Gate D — 실행 계획 승인

- [ ] 정확한 변경 파일 목록
- [ ] migration revision과 down/rollback 정책
- [ ] Feature Flag 도입 순서
- [ ] 단계별 수용 기준
- [ ] 예상 작업량과 담당 범위
- [ ] 사용자 명시 승인

---

## 16. 필수 사용자 인터뷰

미래 Agent는 아래 질문의 답이 코드와 기존 문서에서 명백히 확인되지 않으면 반드시
사용자에게 질문해야 한다. 질문 없이 일반적인 업계 관행으로 대신 결정하지 않는다.

한 번에 모든 질문을 던지기보다, 현재 설계 단계에 필요한 1~3개를 묶어 질문한다. 답변은
이 문서의 “인터뷰 답변 기록”에 반영하거나 별도 승인된 의사결정 문서에 기록한다.

### I-01. 첫 프로덕트 기준선

**질문:** 마이그레이션 설계의 기준으로 삼을 첫 프로덕트는 무엇이며, “1차 생성 완료”를
어떤 상태로 판단합니까?

필요한 이유: Project 생성만 의미하는지, 티켓·코드·검증·배포까지 의미하는지에 따라
착수 시점이 달라진다.

### I-02. CMS 계약 소유권

**질문:** DeliveryManifest를 CMS가 Intake와 함께 완성해서 보낼지, Project 생성 후
ClickEye와 협의해 별도 제출할지 어느 쪽을 원합니까?

필요한 이유: idempotency, validation 실패 callback, Manifest 수정 권한이 달라진다.

### I-03. Seat 범위와 소유권

**질문:** Seat는 회사 공용 계정, 내부 개발자 개인 구독, 외부 개발자 개인 구독 중 무엇을
허용하며 프로젝트별 사용 권한은 누가 정합니까?

필요한 이유: 개인정보, 이용약관, 조직 권한, 퇴사·계정 회수 정책이 달라진다.

### I-04. Provider 우선순위

**질문:** MVP에서 반드시 지원할 provider와 CLI는 무엇이며, Claude와 Codex 중 어느 쪽을
기본 실행기로 삼습니까?

필요한 이유: 인증 홈, usage telemetry, 명령 옵션, 결과 형식이 provider마다 다르다.

### I-05. 정확한 사용량에 대한 기대

**질문:** 대시보드에서 정확한 잔여 token 숫자가 아니라
`사용 가능 / cooldown / 인증 필요 / 추정 여유도`만 제공해도 운영상 충분합니까?

필요한 이유: 공식적으로 제공되지 않는 잔량을 구현한다고 약속해서는 안 된다.

### I-06. Runner 운영 위치

**질문:** 초기 Runner는 별도 AWS 서버, 사내 로컬 서버, 개발자 PC 중 어디에서 운영하며
둘 이상을 동시에 지원해야 합니까?

필요한 이유: network, secret manager, filesystem, Docker 권한, test URL 방식이 달라진다.

### I-07. Secret Manager

**질문:** AWS Secrets Manager, Vault, 클라우드별 Secret Manager, Runner-local 보안 저장소
중 어떤 체계를 운영 표준으로 선택합니까?

필요한 이유: Secret 참조 형식과 Runner 이동 가능성이 달라진다.

### I-08. 외부 연동 책임자와 알림

**질문:** Human Integration Gate가 생기면 누가 owner가 되며, CMS·ClickEye Web·이메일·메신저
중 어디로 blocker 알림을 보내야 합니까?

필요한 이유: blocker가 기록만 되고 해결되지 않는 상태를 방지해야 한다.

### I-09. 테스트 URL 접근 정책

**질문:** 테스트 URL은 인터넷 공개, IP allowlist, VPN, 일회성 token, ClickEye 로그인
프록시 중 어떤 접근 정책을 사용합니까?

필요한 이유: port, DNS, TLS, 인증 구조와 운영 비용이 달라진다.

### I-10. 인수 테스트 완료 정의

**질문:** 사용자의 승인 한 번으로 완료할지, 체크리스트·결함 등록·재검증까지 ClickEye에서
관리할지 어느 범위가 MVP입니까?

필요한 이유: ClickEye가 별도 QA/CRM 제품으로 확장되는 것을 막으면서 필요한 기록은
남겨야 한다.

### I-11. 프로젝트 삭제와 보존

**질문:** 작업공간, build artifact, container, volume, 실행 로그를 프로젝트 완료 후 얼마나
보존하며 누가 삭제를 승인합니까?

필요한 이유: 자동 정리와 rollback 가능성, 저장 비용, 개인정보 보존이 충돌한다.

### I-12. 운영 동시성 목표

**질문:** MVP에서 동시에 실행할 프로젝트 수, Seat 수, 프로젝트당 허용 Job 수의 목표는
얼마입니까?

필요한 이유: Scheduler·DB lease·Runner host 규모를 과도하거나 부족하게 설계하지 않기
위함이다.

> **이 답변이 막고 있는 계산이 있다.** `docs/hybrid-runner-headless-poc.md` §4-3의
> `필요 시트 수 ≈ C + cooldown 여유분`에서 `C`(목표 동시 실행 수)가 유일한 미지수다.
> 동시 실행 목표는 프로젝트 총량(20~50)이 아니라 **동시성 요구**이며, 둘을 혼동하면 시트 수가
> 과대 산정된다. 같은 문서 §4-2가 확정한 대로 현행 병목은 시트가 아니라 러너 호스트와
> git main 머지 경로다.

### I-13. 신규 패널의 IA 위치

**질문:** Manifest·실행·외부연동·배포 패널을 프로젝트 하위 탭, 딜리버리 콘솔 내부 섹션,
신규 최상위 메뉴 중 어디에 붙입니까?

필요한 이유: 프로젝트 경계와 운영자 경계가 달라진다. 시트 풀은 조직 전역이고 Job은
프로젝트별이므로 한 화면에 섞으면 권한 경계가 흐려진다.

> 2026-07-29 답변 완료 — §25 참조.

### I-14. 딜리버리와 프로젝트의 관계

**질문:** `딜리버리`와 `프로젝트`를 사이드바 1뎁스에 나란히 두는 현재 구조가 맞습니까?

필요한 이유: 실측 결과 두 메뉴는 **같은 엔티티의 같은 목록**을 노출한다.

- `engagement`는 API에 모델이 없다 — `grep -rlni "engagement" clickeye-api/app` → 0건
- `clickeye-web/src/app/(dashboard)/delivery/[engagementId]/page.tsx:75` —
  `const projectId = engagementId;` (`engagementId`가 곧 `projectId`)
- `clickeye-web/src/app/(dashboard)/delivery/page.tsx:20` — `useProjects()`.
  즉 딜리버리 목록 = 프로젝트 목록
- 같은 파일 `:260` — 딜리버리 상세가 이미 `/projects/[id]/ai-team`을 자식처럼 링크

사용자가 "어느 메뉴로 들어가야 하나"를 매번 판단해야 하는 구조이며, 실행 계층 4개 탭을
어디에 붙일지도 이 결정에 종속된다.

> 2026-07-29 답변 완료 — §25 참조.

### 16.1 인터뷰 답변 기록 양식

```markdown
#### I-XX — 질문 제목
- 인터뷰 일시:
- 답변자:
- 답변:
- 상태: 확정 | 실험 필요 | 보류
- 근거 또는 제약:
- 설계 영향:
- 재확인 시점:
```

Agent는 `보류` 답변을 구현 기본값으로 바꾸지 않는다. 해당 기능을 Feature Flag off 또는
명시적 blocker 상태로 유지하는 계획을 작성한다.

---

## 17. 단계별 전환 전략

아래 순서는 미래 실행 계획을 작성할 때의 전략적 순서다. 지금 실행하지 않는다.

### Stage 0 — 관측과 계약 고정

- 첫 프로덕트 E2E 관측
- 사용자 인터뷰
- API·DB·WebSocket baseline snapshot
- DeliveryManifest v1 초안과 CMS 예제 payload 합의
- provider 공식 문서와 이용 정책 재검증

완료 조건: 미확정 의사결정이 blocker로 목록화되고 사용자가 범위를 승인한다.

### Stage 0.5 — 화면 기준선 (와이어프레임)

> 초판 누락 항목. 2026-07-29 추가.
> **이 단계만은 Gate A~D의 선행 없이 진행할 수 있다** (§0.1 제외 조건 충족 시).

초판은 Stage 0(관측)에서 Stage 1(백엔드)로 곧장 넘어갔다. 그 결과 §20의 Web은
"Execution·Integrations·Deployment 패널 후보" 한 줄로만 남아 있었다. 이는 두 가지 문제를
만든다.

1. 사용자가 §16의 I-05·I-09·I-10을 답할 근거가 없다. 잔여량을 숫자로 볼지, 테스트 URL을
   어떻게 열지, 인수 테스트를 어디까지 기록할지는 **화면을 봐야 판단할 수 있는 질문**이다.
2. 설계 문서만 늘어나고 제품이 완성되지 않는다.

산출물:

- 클릭 가능한 와이어프레임 — `docs/wireframes/multiproject-delivery.html`
- 페이지 스펙 6종 (`docs/pages/`, 전부 `status: draft`)
  - `projects/manifest.md` · `projects/execution.md` · `projects/integrations.md` ·
    `projects/deployment.md` · `admin/seats.md` · `admin/execution-overview.md`

IA 결정 (I-13 · I-14, 2026-07-29 확정):

```text
사이드바 1뎁스   딜리버리(단일 진입) · 가이드 · 운영(superadmin)
                 └ `프로젝트` 1뎁스 제거 — 같은 목록 중복 노출이었다 (I-14)

딜리버리 목록    /delivery
                 리스트(행) → 클릭 시 우측 슬라이드 패널에 요약 → `진입하기`로만 진입
                 요약 5종: 단계+진행률 · 티켓(완주·검증) · 마지막 활동 · blocker · 구독 시트

프로젝트 상세    /projects/[id]/...
                 기존 4탭 콘솔·개요·AI팀·계약
                 신규 4탭 {manifest,execution,integrations,deployment}

운영 패널        /admin/ops/{seats,execution}
```

기존 딜리버리 콘솔·프로젝트 탭·라우트를 **교체하지 않고 탭만 가산**한다. `/projects/*` 라우트는
유지하고 사이드바 노출만 정리한다. 신규 최상위 메뉴나 별도 제품 화면을 만들지 않는다(§1.1).

와이어프레임이 반드시 지켜야 할 제약:

- 정확한 잔여 token 숫자를 표시하지 않는다. `사용 가능 / cooldown / 인증 필요 / 추정 여유도`만
  쓴다 (I-05가 `확정`되기 전까지). 추정값에는 근거를 병기한다.
- 시트 상태는 §6.2의 매핑표를 따라 파생 5상태 + 근거를 함께 보여준다.
- Secret 실제 값을 표시하는 UI 요소를 두지 않는다. `secret_ref`와 fingerprint만 노출한다.
- `FAILED`를 완료·성공 집계에 섞지 않는다 (§10).
- Feature Flag off 상태의 화면(패널 미표시)도 와이어프레임에 포함한다 (§19).
- 미확정 인터뷰 항목에 의존하는 요소는 `미확정` 배지로 표시하고 임의 확정하지 않는다.

완료 조건: 사용자가 6화면을 보고 I-05·I-09·I-10·I-12에 답할 수 있다. 화면이 §1.1의 금지
범위(계약·인사·CRM)를 끌어들이지 않았음을 확인한다.

### Stage 1 — Manifest와 Human Gate

- 기존 Intake에 선택적 Manifest를 받아 검증
- Project lifecycle은 그대로 유지
- 외부 연동 요구를 blocker로 표시
- 실행은 아직 기존 단일 프로젝트 흐름 사용

목적: Scheduler와 Docker보다 먼저 “무엇을 실행할지”와 “사람이 무엇을 해야 하는지”를
정확히 만든다.

### Stage 2 — P4 Seat Pool

- Seat registry와 Runner 연결
- heartbeat·usage·rate-limit 관측
- 1 Seat = 1 active Job 원칙
- 수동 배정 또는 shadow scheduling으로 판단 정확도 검증

목적: 자동 배정 전에 관측값과 상태 전이가 신뢰 가능한지 확인한다.

### Stage 3 — P5 Workspace와 DeliveryJob

- 프로젝트별 workspace·branch·lock·artifact 격리
- Job lease와 상태 이벤트 영속화
- 기존 RunnerTaskPayload 호환 실행
- 두 프로젝트·두 Seat로 제한된 동시 실행
- rate-limit 발생 시 checkpoint 기반 이어받기 검증

목적: 기존 전역 파이프라인을 무리하게 병렬화하지 않고 프로젝트 단위로 격리한다.

### Stage 4 — Deploy Runner MVP

- Linux/amd64 전용 profile
- Dockerfile/Compose build·run·healthcheck·rollback
- PostgreSQL·SQLite·ClickHouse profile
- 테스트 URL과 사용자 인수 상태

목적: 첫 프로덕트와 유사한 환경부터 지원하고 범용 OS 플랫폼을 약속하지 않는다.

### Stage 5 — 운영 안정화

- Web 실행·연동·배포 모니터링
- alert, retention, 장애 runbook
- Seat score 보정
- 실패 재현과 rollback 리허설
- 지원 profile 확대 여부 재평가

---

## 18. 가산형 DB 마이그레이션 전략 후보

실제 revision 번호는 마이그레이션 착수 시 최신 Alembic head를 확인한 뒤 정한다.
현재 번호를 예약하거나 파일을 만들지 않는다.

1. Manifest와 Human Integration Gate 신규 table
2. Seat registry, usage sample, 기존 usage ledger의 nullable seat 연결
3. AgentConnection의 호환 필드와 Runner scope
4. DeliveryJob과 JobEvent, active lease unique 제약
5. DeploymentRun

원칙:

- migration 적용 직후에도 Feature Flag는 off다.
- 기존 project scope Agent는 동일하게 동작한다.
- 기존 Intake는 Manifest 없이 성공한다.
- 신규 column에는 기존 행을 위한 안전한 default 또는 nullable을 사용한다.
- 운영 rollback은 먼저 flag off와 Job drain으로 수행한다.
- 신규 데이터가 쌓인 뒤 자동 downgrade로 table을 삭제하지 않는다.
- schema downgrade가 필요하면 별도 사용자 승인과 backup이 있어야 한다.

---

## 19. 기존 API 호환과 Feature Flag

미래 후보 flag:

```text
FEATURE_DELIVERY_EXECUTION
FLOWOPS_DELIVERY_MANIFEST
FLOWOPS_HUMAN_INTEGRATION_GATE
FLOWOPS_SEAT_SCHEDULER
FLOWOPS_WORKSPACE_RUNNER
FLOWOPS_DEPLOY_RUNNER
```

이름은 현재 설정 규칙을 재실측한 뒤 확정한다.

도입 원칙:

- master flag는 기본 off
- component flag도 각각 기본 off
- legacy Project와 legacy Agent는 flag 영향을 받지 않음
- API response의 신규 필드는 optional
- 신규 endpoint는 flag off에서 기존 convention에 맞춰 숨김 또는 404
- Web 패널은 API capability와 flag가 모두 확인될 때만 표시
- 자동 스케줄링 전 shadow mode로 추천 결과만 기록
- Seat와 Deploy 기능을 동시에 처음 켜지 않음

---

## 20. 향후 영향 파일 지도

다음은 미래 실행 계획에서 재실측할 후보이며 지금 생성하거나 수정하지 않는다.

### API

- `clickeye-api/app/models/intake.py`
- `clickeye-api/app/schemas/intake.py`
- `clickeye-api/app/services/intake_service.py`
- `clickeye-api/app/models/project.py`
- `clickeye-api/app/models/agent_connection.py`
- `clickeye-api/app/models/llm_usage_ledger.py`
- `clickeye-api/app/services/control_plane_service.py`
- `clickeye-api/app/engine/generator.py`
- `clickeye-api/app/ws/router.py`
- `clickeye-api/app/ws/hub.py`
- `clickeye-api/app/ws/handlers.py`
- `clickeye-api/app/core/config.py`
- `clickeye-api/app/services/project_service.py`
- `clickeye-api/app/api/v1/router.py`
- `clickeye-api/app/models/__init__.py`
- 신규 Manifest·Seat·Job·Gate·Deployment 모델/서비스/스키마 후보

### Contracts

- `clickeye-contracts/protocol/messages.ts`
- `clickeye-contracts/protocol/commands.ts`
- 해당 Python mirror

필수 필드를 바꾸지 않고 heartbeat·result의 optional telemetry만 우선 검토한다.

### Agent

- `clickeye-agent/clickeye_agent/config.py`
- `clickeye-agent/clickeye_agent/storage/local_store.py`
- `clickeye-agent/clickeye_agent/main.py`
- `clickeye-agent/clickeye_agent/reporter.py`
- `clickeye-agent/clickeye_agent/handlers/runner_handler.py`
- `clickeye-agent/clickeye_agent/handlers/docker_handler.py`
- `clickeye-agent/clickeye_agent/handlers/environment_handler.py`
- 신규 workspace manager·command policy·seat probe·secret resolver·deploy manager 후보

### Web

- `clickeye-web/src/lib/api-client.ts` 및 공식 생성 흐름
- 기존 Intake 콘솔
- 기존 Delivery 콘솔
- 신규 독립 제품이 아닌 Execution·Integrations·Deployment 패널 후보

### Infra

- ClickEye API용 Docker proxy는 제품 배포기로 확장하지 않는다.
- 별도 Runner host profile과 최소 권한 Docker 정책을 후속 검토한다.

---

## 21. 테스트와 rollback 전략

### 21.1 테스트

- Manifest JSON Schema의 정상·거부·알 수 없는 필드·Secret 값 검출
- CMS Intake idempotency와 legacy payload 회귀
- CONTROL과 Manifest 충돌 시 fail-closed
- 동시에 여러 Scheduler가 같은 Seat를 선택하는 경쟁 조건
- lease 만료, heartbeat 지연, Runner 재접속
- Seat별 인증 홈과 프로젝트 Secret 격리
- 경로 traversal, symlink escape, repo URL 검증
- 승인되지 않은 shell, host mount, privilege 실행 거부
- status·log·result의 Job 연결과 순서 보장
- 두 프로젝트·두 Seat 동시 실행
- rate-limit → checkpoint → 다른 Seat 재시작
- Human Gate phase별 차단과 재개
- Docker build 실패·healthcheck 실패·rollback
- 테스트 URL 접근 제어와 만료
- 로그·DB·Git·artifact에 Secret이 남지 않는지 검사
- 기존 P0~P3, P6~P9 회귀

### 21.2 운영 rollback

1. 신규 Intake scheduling 중지
2. 활성 Job drain 또는 안전 checkpoint
3. component flag off
4. 기존 단일 프로젝트 실행 흐름으로 복귀
5. workspace와 artifact는 보존
6. 신규 deployment namespace만 중지
7. volume 삭제는 별도 승인
8. 원장 데이터는 감사 목적으로 보존

rollback이 schema downgrade를 의미해서는 안 된다.

---

## 22. 예상 작업량

첫 프로덕트와 인터뷰가 완료되기 전의 거친 범위 추정이다.

| 단계 | 예상 인력 작업량 |
|---|---:|
| 관측·인터뷰·계약 확정 | 1~1.5 인주 |
| Manifest·CMS bridge | 1~1.5 인주 |
| Human Integration Gate | 1.5~2 인주 |
| Seat registry·telemetry·scheduler | 2~3 인주 |
| DeliveryJob·workspace·lease·monitoring | 3~4 인주 |
| Deploy Runner MVP | 2.5~4 인주 |
| Web 패널·E2E·보안·운영 안정화 | 1.5~2.5 인주 |
| 합계 | 약 12.5~18.5 인주 |

한 명이 순차 수행하면 약 13~19주가 필요할 수 있다. 두 명 이상이 계약 확정 후 안전하게
병렬 작업하더라도 8~12주 수준을 가정하는 편이 보수적이다.

이 숫자는 확정 견적이 아니다. 첫 프로덕트의 stack, 외부 연동, Runner 위치, provider 수가
확인되면 다시 산정한다.

---

## 23. MVP 수용 기준

미래 MVP는 최소한 다음을 충족해야 한다.

- [ ] 기존 Intake payload가 변경 없이 동작한다.
- [ ] Manifest가 없는 기존 Project는 기존 lifecycle을 유지한다.
- [ ] Manifest와 CONTROL의 검증 실패는 실행 전에 차단된다.
- [ ] Secret 실제 값이 CMS payload, CONTROL, Manifest, ClickEye DB, Git에 없다.
- [ ] Seat 상태 5종의 전이가 감사 가능하다.
- [ ] 정확한 잔여 token을 표시한다고 주장하지 않는다.
- [ ] 한 Seat에 active Job이 1개만 존재한다.
- [ ] 두 프로젝트가 서로 다른 workspace에서 동시에 실행된다.
- [ ] 프로젝트 lock과 branch, log, artifact가 섞이지 않는다.
- [ ] Agent 연결이 끊겨도 lease 만료와 재시도가 기록된다.
- [ ] rate-limit 발생 시 checkpoint를 기준으로 다른 Seat가 이어받을 수 있다.
- [ ] checkpoint 실패 시 자동 재배정하지 않는다.
- [ ] Human Integration Gate가 phase별로 작업을 차단·재개한다.
- [ ] README 임의 명령이 실행되지 않는다.
- [ ] Linux/amd64 Dockerfile 또는 Compose build가 재현된다.
- [ ] PostgreSQL, SQLite, ClickHouse 중 실제 첫 제품에 필요한 profile이 검증된다.
- [ ] HTTP healthcheck 실패 시 acceptance URL을 발급하지 않는다.
- [ ] 사용자가 테스트 URL에서 로그인 인수 테스트를 수행할 수 있다.
- [ ] 실패 deployment를 프로젝트 namespace 단위로 rollback할 수 있다.
- [ ] Feature Flag off 시 기존 ClickEye 동작으로 즉시 복귀한다.
- [ ] 기존 P0~P3, P6~P9 회귀 테스트가 통과한다.

---

## 24. Agent 작업 규칙

이 문서를 인수한 Agent는 다음 순서를 지킨다.

1. 먼저 사용자에게 현재 단계가 “현행 구조 완성 전”, “첫 프로덕트 생성 중”,
   “마이그레이션 계획 수립 가능” 중 어디인지 확인한다.
2. 앞의 두 단계라면 구현 계획을 만들지 말고 관측 항목과 인터뷰 질문만 관리한다.
3. 코드 실측 결과와 이 문서가 다르면 차이를 사용자에게 보고한다.
4. 미확정 인터뷰 질문을 사용자에게 묻는다.
5. 답을 받은 뒤 별도의 실행용 계획을 작성한다.
6. 계획에는 정확한 파일, DB revision, 계약 변경, flag, 테스트, rollback을 포함한다.
7. 사용자 승인 전에는 어떤 구현도 시작하지 않는다.

### 24.1 금지되는 Agent 표현

- “구독 잔여 token API가 있으므로 정확히 배정할 수 있다.”
- “Runner는 이미 다프로젝트 workspace를 지원한다.”
- “Docker stop/destroy가 완성되어 있다.”
- “README를 읽고 자동으로 안전하게 실행한다.”
- “Windows·RedHat·MSSQL까지 Docker로 모두 지원한다.”
- “기존 코드를 전면 리팩터링해야 한다.”
- “똑빌더 기능을 ClickEye 안에 모두 구현한다.”
- “사용자 답변이 없으므로 일반적인 기본값으로 결정했다.”

### 24.2 이 전략의 성공 기준

이 전략은 많은 기능을 새로 만드는 것이 성공이 아니다.

기존 ClickEye의 프로젝트·제어면·티켓·검증 흐름을 유지하면서, 첫 프로덕트를 기준으로
필요한 실행 계층만 가산하고, 사용자가 결정해야 할 사안을 인터뷰 없이 넘기지 않는 것이
성공이다.

---

## 25. 인터뷰 답변 기록

답변을 추정해 기록하지 않는다. **미답변: I-01·I-02·I-03·I-04·I-06·I-07·I-11**
(첫 프로덕트 관측 이후 진행).

#### I-05 — 정확한 사용량에 대한 기대
- 인터뷰 일시: 2026-07-29
- 답변자: 사용자(khee@tscorp.ai)
- 답변: `사용 가능 / cooldown / 인증 필요 / 추정 여유도`만으로 충분하다.
- 상태: 확정
- 근거 또는 제약: 공급자가 공식 잔량 API를 제공하지 않는다. 없는 것을 있는 것처럼 만들지 않는다.
- 설계 영향: 시트 화면은 상/중/하 + 관측 근거만 노출한다. 숫자·퍼센트 잔량 요소를 만들지 않는다.
  파생 5상태는 §6.2 매핑표를 따르고 근거를 병기한다.
- 재확인 시점: 공급자가 공식 잔량 API를 제공하면 재검토.

#### I-08 — 외부 연동 책임자와 알림
- 인터뷰 일시: 2026-07-29
- 답변자: 사용자
- 답변: **질문의 전제를 교정.** 외부 연동은 ClickEye가 쓰려는 연동이 아니라
  **만들어주는 프로덕트에 녹여야 하는 연동**이다. 예: 회사 홈페이지를 만들면 회사 위치 표시와
  길찾기가 필요한데, AI가 그 API 연동 계정을 만들 수 없으므로 **고객(사용자)이 직접 발급해
  API KEY를 입력**하는 별도 작업이 필요하다. 그 작업을 추적하는 기능이다.
- 상태: 확정(정의) · 부분 보류(채널 확장)
- 근거 또는 제약: 담당은 고객(프로젝트 소유자)이다. 1차 채널은 고객이 키를 입력하는 화면과
  같은 곳이어야 하므로 ClickEye Web. 이메일·메신저 확장은 보류.
- 설계 영향: 게이트 카드는 "무엇을 발급해 어디에 넣어야 하는지"가 고객에게 자족적으로 읽혀야
  한다. ClickEye 자체 연동 관리 기능으로 해석해 확장하지 않는다. `CREDENTIAL_SAVED`는
  Secret Manager 저장을 의미하며 ClickEye는 `secret_ref` + fingerprint만 받는다.
- 재확인 시점: 첫 프로덕트에서 실제 필요한 연동 목록이 확인된 뒤 채널 확장 여부 판단.

#### I-09 — 테스트 URL 접근 정책
- 인터뷰 일시: 2026-07-29
- 답변자: 사용자
- 답변: 사내 **`아이피:포트`** 형식. 도메인·DNS·TLS를 쓰지 않는다. 프로덕트의 주체는 고객이고
  코드 전체를 고객이 가져가므로, 완료 시 **배포 테스트는 우리가 직접** 수행한다.
- 상태: 확정
- 근거 또는 제약: 외부 공개 테스트에는 사내 방화벽 정책과 도메인 설정이 필요해 MVP 범위를
  넘는다.
- 설계 영향: §14의 "테스트 URL — DNS·TLS·port allocation 필요"에서 **port allocation만
  남는다.** MVP 난이도가 내려간다. 남는 실무 항목은 포트 충돌 방지와 프로젝트별 포트 회수.
  화면은 도메인 URL 대신 `http://<host-ip>:<port>`를 표시하고 접근 범위를 "사내망"으로 명시한다.
- 재확인 시점: 고객이 원격 인수 테스트를 요구하는 사례가 생기면 재검토.

#### I-10 — 인수 테스트 완료 정의
- 인터뷰 일시: 2026-07-29
- 답변자: 사용자
- 답변: 사람이 개입한다. **이 부분은 아직 AI 자동화로 대체하지 않는다.**
- 상태: 확정
- 근거 또는 제약: 인수 판단은 자동화 대상이 아니다.
- 설계 영향: 화면은 사람의 판단을 **기록**하는 역할만 한다. 통과 여부를 추론하거나 자동 승인하지
  않는다. 결함 등록·재검증 워크플로를 ClickEye 안에 만들지 않는다(§1.1 — 별도 QA 제품으로
  번지는 것 방지). 보완 요청은 실행 탭의 보완 Job으로만 연결한다.
- 재확인 시점: 인수 테스트 반복 횟수가 운영 부담이 될 때.

#### I-12 — 운영 동시성 목표
- 인터뷰 일시: 2026-07-29
- 답변자: 사용자
- 답변: 가능하면 많이 하고 싶지만 그것은 아직 목표다. **우선 최대 2개, 기본은 1개씩 순차 진행.**
- 상태: 확정(MVP) · 상향은 목표
- 근거 또는 제약: 현행 유효 동시성은 1이다(러너 호스트 1대 · 단일 체크아웃 병렬 배제).
- 설계 영향: `C = 2` → **필요 시트 3~4개**(활성 2 + cooldown·인증 예비 1~2). 산정은
  `docs/hybrid-runner-headless-poc.md` §4-3. 최대 2를 실제로 쓰려면 러너 수평 확장과
  main 머지 직렬화가 선행된다 — 시트를 늘려서 해결되지 않는다.
- 재확인 시점: 러너 수평 확장 착수 시점.

#### I-14 — 딜리버리와 프로젝트의 관계
- 인터뷰 일시: 2026-07-29
- 답변자: 사용자
- 답변: 딜리버리를 단일 진입점으로 한다. 딜리버리에 진입하면 진행 중 프로젝트가 목록으로
  노출되고 진척도가 요약되며, 선택하면 상세로 들어간다. **1뎁스의 `프로젝트` 메뉴는 제거**한다.
  목록은 카드가 아니라 **리스트**이고, 행을 클릭하면 즉시 진입하지 않고 **우측 슬라이드 패널**에
  요약이 열린다. 진입은 패널의 `진입하기`로만 한다. 디자인은 최대한 심플한 컨설팅 스타일.
- 상태: 확정
- 근거 또는 제약: "일반 품목 파는 사이트처럼 상품을 클릭하면 바로 진입하는 구조"를 원하지
  않는다 — 솔루션다운 표현과 향후 확장을 위한 선택이다.
- 설계 영향: `/projects/*` **라우트는 삭제하지 않는다**(기존 URL·북마크 유지). 사이드바 1뎁스
  노출만 제거한다. 프로젝트 상세는 기존 4탭(콘솔·개요·AI팀·계약) + 신규 4탭(매니페스트·실행·
  외부연동·배포)이다. 슬라이드 패널 요약 항목 5종: 현재 단계+진행률 / 티켓 진행(완주·검증) /
  마지막 활동 시각 / 현재 막힌 것 / **어떤 구독 시트로 진행 중인지**.
  `엔게이지먼트`↔`프로젝트` 용어 이원화는 부채로 남기고 이번에 개명하지 않는다
  (i18n 키·라우트명·문서 경로가 함께 바뀌고 기존 링크가 깨진다).
- 재확인 시점: 용어 통일을 별도 과제로 착수할 때.

#### I-13 — 신규 패널의 IA 위치
- 인터뷰 일시: 2026-07-29
- 답변자: 사용자(khee@tscorp.ai)
- 답변: 프로젝트 하위 탭 + 시트는 운영 패널.
  `/projects/[id]/{manifest,execution,integrations,deployment}` 및
  `/admin/ops/{seats,execution}`
- 상태: 확정
- 근거 또는 제약: 프로젝트별 격리가 자연스럽고 기존 `projects` 탭 구조를 그대로 재사용한다.
  시트 풀은 조직 전역 자원이므로 프로젝트 하위에 두지 않고 superadmin 운영 패널에 둔다.
- 설계 영향: 기존 사이드바 최상위 메뉴를 변경하지 않는다. 신규 최상위 메뉴를 만들지 않는다.
  Stage 0.5 와이어프레임과 페이지 스펙 6종이 이 배치를 따른다.
- 재확인 시점: Stage 3(DeliveryJob) 착수 전. 다프로젝트 동시 실행 수가 I-12에서
  확정되면 `/admin/ops/execution`의 정보 밀도를 재검토한다.

```markdown
#### I-XX — 질문 제목
- 인터뷰 일시:
- 답변자:
- 답변:
- 상태: 확정 | 실험 필요 | 보류
- 근거 또는 제약:
- 설계 영향:
- 재확인 시점:
```

---

## 26. 변경 이력

| 일자 | 변경 | 비고 |
|---|---|---|
| 2026-07-29 | 초판 작성 | 구현 금지, 첫 프로덕트 이후 계획 수립, 필수 인터뷰 게이트 명시 |
| 2026-07-29 | 인터뷰 6건 확정 반영 | I-05(여유도 표기 확정) · **I-08 정의 교정**(프로덕트에 녹일 연동 — 고객이 키 발급·입력. ClickEye 자체 연동 아님, §6.4 전제 추가) · I-09(사내 `아이피:포트` — DNS·TLS가 MVP에서 제외되어 난이도 하락) · I-10(사람 개입 유지, AI 자동화 대체 안 함) · I-12(최대 2·기본 1 순차 → 필요 시트 3~4) · **I-14 신설·확정**(딜리버리 단일 진입 · `프로젝트` 1뎁스 제거 · 리스트+슬라이드 패널). 근거: `engagementId === projectId`, 두 메뉴가 동일 `useProjects()` 목록 |
| 2026-07-29 | 실측 정정 + 화면 단계 신설 | ①§0.1 금지범위 예외(와이어프레임·페이지 스펙) ②§3.0 실측 정정 — 등록형 시트·프로젝트 러너는 이미 구현(P4·P5 완료), 남은 격차 5개로 축소 ③§6.2 시트 상태 어휘 충돌 매핑(현행 3상태 ↔ 목표 5상태 파생) ④§9 `SubscriptionSeat` 신규 생성 금지로 정정 ⑤§17 `Stage 0.5 화면 기준선` 신설 ⑥I-13 신설·확정 |
