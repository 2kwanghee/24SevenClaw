# NVIDIA NeMo Agent Monitoring — ClickEye 접목 검토

> 작성일: 2026-03-24
> 목적: NeMo Agent Toolkit의 모니터링 기능을 ClickEye에 적용할 수 있는 부분 분석

---

## NVIDIA NeMo Agent Monitoring이란

NeMo Agent Toolkit은 AI 에이전트 워크플로의 **전체 실행 과정을 추적/프로파일링/최적화**하는 오픈소스 라이브러리.

- **OpenTelemetry 기반 트레이싱** — 에이전트의 모든 단계(LLM 호출, 도구 사용, 중간 결과)를 span으로 추적
- **이벤트 드리븐 아키텍처** — `IntermediateStepManager`가 워크플로 이벤트를 발행, 비동기로 텔레메트리 수집
- **프로파일러** — 에이전트 → 도구 → 개별 토큰 레벨까지 성능 병목 분석
- **플러그인 기반** — Phoenix, Langfuse, Weave, 또는 OTel 호환 서비스로 내보내기

---

## ClickEye 접목 가능 영역

### 1. Agent 데몬의 Claude 인스턴스 모니터링 (Phase 3)

**가장 직접적인 접목 포인트.**

현재 설계에서 고객 서버의 Agent가 Claude 인스턴스에 작업을 지시하고 결과를 수집하는데, 이 과정이 블랙박스.

NeMo 적용 시:
- Claude가 **어떤 도구를 호출**했는지, **각 단계에 얼마나 걸렸는지** 트레이싱
- **input/output 토큰 사용량** 실시간 추적 → 비용 산정 근거
- 작업 실패 시 **어느 단계에서 실패**했는지 span 단위로 디버깅
- 이 데이터를 Agent → Cloud로 보고하면 **클라우드 대시보드에서 실시간 확인**

**해당 모듈**: `24SevenClaw-agent`의 `claude_handler` + Cloud의 모니터링 대시보드

---

### 2. 티켓 → Claude 작업의 End-to-End 트레이싱 (Phase 3)

현재 설계:
```
클라우드 티켓 발행 → Agent 전달 → Claude 작업 → 결과 수집 → 클라우드 보고
```

이 전체 파이프라인을 **하나의 OTel trace**로 묶을 수 있음:
- **Trace ID**: 티켓 ID와 연결
- **Span 계층**: 티켓 전달 → Claude 계획 수립 → 코드 생성 → 테스트 실행 → Git 커밋
- 각 span에 **소요 시간, 토큰 수, 성공/실패** 메타데이터 부착

→ 클라우드 UI에서 "이 티켓이 왜 30분 걸렸는지"를 **단계별로 드릴다운** 가능

---

### 3. 파이프라인 실행 모니터링 (Phase 4)

Phase 4의 DAG 기반 파이프라인 실행 엔진에 NeMo 프로파일러를 붙이면:
- 파이프라인의 **각 노드(빌드, 테스트, 배포)별 실행 시간** 프로파일링
- 병렬 실행 시 **병목 노드** 자동 식별
- 노드 간 **데이터 흐름**과 대기 시간 시각화
- **빌드 로그 스트리밍**과 함께 성능 메트릭도 동시 전송

---

### 4. 멀티 에이전트 협업 모니터링 (장기)

고객이 여러 Docker 컨테이너에서 **다수의 Claude 인스턴스**를 동시에 돌리는 시나리오:
- NeMo의 **cross-agent coordination 메트릭** 활용
- 에이전트 간 **작업 분배 효율성** 추적
- 전체 팀(에이전트 그룹)의 **총 토큰 소비, 비용, 처리량** 집계
- 어떤 에이전트가 병목인지 식별

---

### 5. 클라우드 대시보드 연동 (Phase 3-4)

NeMo가 **OpenTelemetry 표준**을 사용하므로, 클라우드 쪽에서:
- Agent가 보내는 OTel 데이터를 **수신하는 Collector** 배치
- 기존 설계의 `ticket_events` 테이블과 **OTel span 데이터를 연계**
- 대시보드에서 **트레이스 뷰어** 제공 (Jaeger/Grafana Tempo 스타일)
- 라이센스별 **토큰 사용량 집계** → 과금 근거

---

## 접목 구조

```
┌─ 클라우드 ──────────────────────────────────┐
│  OTel Collector ← Agent가 보내는 텔레메트리    │
│       │                                      │
│  Trace Storage (Tempo/Jaeger)                │
│       │                                      │
│  대시보드 UI: 트레이스 뷰어 + 비용 분석         │
└──────────────────────────────────────────────┘
        ▲ WebSocket + OTel (OTLP)
        │
┌─ 고객 서버 ─────────────────────────────────┐
│  Agent 데몬                                  │
│    └─ NeMo Agent Toolkit 통합               │
│         ├─ IntermediateStepManager           │
│         ├─ Claude 호출 트레이싱               │
│         ├─ 도구 사용 추적                     │
│         └─ 토큰/비용 프로파일링               │
│                                              │
│  [Container A]     [Container B]             │
│   Claude + NeMo     Claude + NeMo            │
└──────────────────────────────────────────────┘
```

---

## 현실적 판단

| 관점 | 평가 |
|------|------|
| **기술적 적합성** | 높음 — OTel 표준 기반이라 기존 설계에 자연스럽게 끼워넣기 가능 |
| **도입 시점** | Phase 3 (Claude 연동) 시작할 때 함께 설계하는 게 이상적 |
| **비용** | 오픈소스이므로 라이센스 비용 없음, GPU 의존성도 모니터링 기능에선 불필요 |
| **리스크** | NVIDIA 에코시스템 의존성 증가, Agent가 Python 기반이라 통합은 수월 |
| **대안** | Langfuse나 LangSmith 같은 LLM 전용 옵서버빌리티도 비교 검토 가치 있음 |

**핵심**: ClickEye의 **"블랙박스인 Claude 작업 과정을 투명하게 만드는 것"**이 고객에게 큰 가치이고, NeMo의 모니터링이 정확히 이 문제를 풀어줌. Phase 3 설계 시 본격적으로 검토 권장.

---

## 참고 자료

- [NeMo Agent Toolkit | NVIDIA Developer](https://developer.nvidia.com/nemo-agent-toolkit)
- [NeMo | Build, monitor, and optimize AI agents | NVIDIA](https://www.nvidia.com/en-us/ai-data-science/products/nemo/)
- [NVIDIA NeMo Agent Toolkit Overview (1.5)](https://docs.nvidia.com/nemo/agent-toolkit/latest/)
- [Observe Workflows — NeMo Agent Toolkit (1.4)](https://docs.nvidia.com/nemo/agent-toolkit/latest/run-workflows/observe/observe.html)
- [NVIDIA AgentIQ Observability](https://docs.nvidia.com/agentiq/latest/concepts/observability.html)
- [GitHub - NVIDIA/NeMo-Agent-Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit)
