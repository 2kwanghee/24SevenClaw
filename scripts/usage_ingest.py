#!/usr/bin/env python3
# usage_ingest.py — 로컬 배치(claude -p) 사용량 → 서버 원장 인제스트 (CE-328).
#
# `claude -p --output-format stream-json` 로그를 사후 파싱하여 마지막 result 이벤트의
# modelUsage(모델별 누적 토큰)를 추출, seat_id 축으로 서버 원장에 POST 한다.
# 순수 가산(additive) — 어떤 실패(파싱/네트워크/403 등)도 stderr 경고 한 줄 후 exit 0 으로
# 삼켜 절대 호출측 파이프라인을 죽이지 않는다.
#
# stdlib 전용(requests 금지 — urllib.request 사용).
#
# env:
#   FLOWOPS_GOVERNANCE_SERVICE_URL (→ API_URL 폴백)  — 인제스트 베이스 URL
#   GOVERNANCE_SERVICE_TOKEN                         — X-Governance-Token 헤더(있을 때)
#   FLOWOPS_GOVERNANCE_SERVICE_TIMEOUT               — 전송 타임아웃(초, 기본 10)
#   CLICKEYE_SEAT_ID / CLICKEYE_PROJECT_ID           — 상관관계 축(없으면 null)
#
# 사용:
#   python3 scripts/usage_ingest.py --log logs/claude_CE-328_*.log \
#     --request-kind local_batch_implement --task-id CE-328

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

INGEST_PATH = "/api/v1/llm/ingest/usage"
DEFAULT_TIMEOUT = 10.0


def _warn(msg: str) -> None:
    """비차단 경고 — 조용한 손실 방지용 로그만 남긴다."""
    sys.stderr.write("[usage-ingest] " + msg + "\n")


def _pick(d: dict, *keys):
    """camelCase/snake_case 혼재 대응 — 존재하는 첫 키의 값을 반환."""
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return None


def _int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


# ── 파싱 ─────────────────────────────────────────────────────────────────────


def parse_log(text: str):
    """stream-json 로그(문자열)를 줄 단위로 파싱.

    stderr 혼입 등 json.loads 실패 줄은 스킵한다. 반환:
      (last_result_event | None, api_key_source | None)
    api_key_source 는 system/init 이벤트의 apiKeySource(예: 'none').
    """
    last_result = None
    api_key_source = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue  # stderr 혼입/비-JSON 줄 스킵
        if not isinstance(evt, dict):
            continue
        etype = evt.get("type")
        if etype == "result":
            last_result = evt
        elif etype == "system" and evt.get("subtype") == "init":
            aks = evt.get("apiKeySource")
            if aks is not None:
                api_key_source = aks
    return last_result, api_key_source


def models_from_result(result_event: dict):
    """result 이벤트 → 모델별 토큰 항목 리스트.

    modelUsage(모델ID→토큰 dict)를 우선 사용, 부재 시 top-level usage 로 폴백(단일 모델).
    """
    entries = []
    model_usage = result_event.get("modelUsage")
    if isinstance(model_usage, dict) and model_usage:
        for model_id, u in model_usage.items():
            if not isinstance(u, dict):
                continue
            entries.append(
                {
                    "model": model_id,
                    "input_tokens": _int(_pick(u, "inputTokens", "input_tokens")),
                    "output_tokens": _int(_pick(u, "outputTokens", "output_tokens")),
                    "cache_read_input_tokens": _int(
                        _pick(u, "cacheReadInputTokens", "cache_read_input_tokens")
                    ),
                    "cache_creation_input_tokens": _int(
                        _pick(u, "cacheCreationInputTokens", "cache_creation_input_tokens")
                    ),
                }
            )
        return entries

    # 폴백: top-level usage(단일 모델). 모델명 미상이면 result.model 또는 'unknown'.
    usage = result_event.get("usage")
    if isinstance(usage, dict) and usage:
        entries.append(
            {
                "model": result_event.get("model") or "unknown",
                "input_tokens": _int(_pick(usage, "inputTokens", "input_tokens")),
                "output_tokens": _int(_pick(usage, "outputTokens", "output_tokens")),
                "cache_read_input_tokens": _int(
                    _pick(usage, "cacheReadInputTokens", "cache_read_input_tokens")
                ),
                "cache_creation_input_tokens": _int(
                    _pick(usage, "cacheCreationInputTokens", "cache_creation_input_tokens")
                ),
            }
        )
    return entries


def _key_source(api_key_source):
    """init 이벤트 apiKeySource → 인제스트 계약의 key_source.

    'none'(=API 키 미사용, 구독 세션) → subscription_seat, 그 외/미확인 → 규칙상
    'none' 이 아니면 org_api_key, 미확인 시 안전 기본값 subscription_seat.
    """
    if api_key_source is None:
        return "subscription_seat"
    return "subscription_seat" if api_key_source == "none" else "org_api_key"


def build_payload(result_event, api_key_source, *, request_kind, task_id):
    """파싱 결과 → 인제스트 JSON 계약 payload. seat/project 는 env 에서 읽는다."""
    models = models_from_result(result_event)
    payload = {
        "session_id": result_event.get("session_id"),
        "request_kind": request_kind,
        "key_source": _key_source(api_key_source),
        "seat_id": os.environ.get("CLICKEYE_SEAT_ID") or None,
        "project_id": os.environ.get("CLICKEYE_PROJECT_ID") or None,
        "task_id": task_id or None,
        "models": models,
        "meta": {
            "total_cost_usd": result_event.get("total_cost_usd"),
            "num_turns": result_event.get("num_turns"),
            "duration_ms": result_event.get("duration_ms"),
            "api_key_source": api_key_source,
        },
    }
    return payload


# ── 전송 ─────────────────────────────────────────────────────────────────────


def _base_url(api_url_arg):
    """베이스 URL 폴백: --api-url → FLOWOPS_GOVERNANCE_SERVICE_URL → API_URL."""
    base = (
        api_url_arg
        or os.environ.get("FLOWOPS_GOVERNANCE_SERVICE_URL")
        or os.environ.get("API_URL")
    )
    return base.rstrip("/") if base else None


def post_usage(payload, base_url, *, token=None, timeout=DEFAULT_TIMEOUT):
    """서버 인제스트 엔드포인트로 POST. 응답 본문(문자열)을 반환.

    네트워크/HTTP 오류는 호출자(main)가 삼키도록 예외를 그대로 전파한다.
    """
    url = base_url + INGEST_PATH
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Governance-Token", token)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _timeout():
    raw = os.environ.get("FLOWOPS_GOVERNANCE_SERVICE_TIMEOUT")
    try:
        return float(raw) if raw else DEFAULT_TIMEOUT
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


# ── 엔트리포인트 ──────────────────────────────────────────────────────────────


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(description="로컬 claude 배치 사용량 서버 인제스트")
    parser.add_argument("--log", required=True, help="claude stream-json 로그 파일 경로")
    parser.add_argument(
        "--request-kind",
        default="local_batch_implement",
        help="출처 구분(기본 local_batch_implement)",
    )
    parser.add_argument("--task-id", default=None, help="상관관계 태스크 키(예: CE-328)")
    parser.add_argument("--api-url", default=None, help="인제스트 베이스 URL(최우선 폴백)")
    args = parser.parse_args(argv)

    # 로그 읽기
    try:
        with open(args.log, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as e:
        _warn("로그 파일 읽기 실패 — 인제스트 스킵: %s" % e)
        return 0

    result_event, api_key_source = parse_log(text)
    if result_event is None:
        _warn("result 이벤트 없음 — 인제스트 스킵")
        return 0

    payload = build_payload(
        result_event,
        api_key_source,
        request_kind=args.request_kind,
        task_id=args.task_id,
    )
    if not payload["models"]:
        _warn("모델 사용량 없음 — 인제스트 스킵")
        return 0

    base = _base_url(args.api_url)
    if not base:
        _warn("베이스 URL 미설정(FLOWOPS_GOVERNANCE_SERVICE_URL/API_URL) — 인제스트 스킵")
        return 0

    token = os.environ.get("GOVERNANCE_SERVICE_TOKEN") or None
    try:
        body = post_usage(payload, base, token=token, timeout=_timeout())
        _warn("전송 완료: %s" % (body or "").strip()[:200])
    except HTTPError as e:
        _warn("전송 HTTP 오류(비차단) %s: %s" % (e.code, getattr(e, "reason", "")))
    except (URLError, OSError, ValueError) as e:
        _warn("전송 실패(비차단): %s" % e)
    return 0


def main(argv=None) -> int:
    # 최후 방어선 — 예기치 못한 예외까지 삼켜 항상 exit 0.
    try:
        return run(argv)
    except Exception as e:  # noqa: BLE001 — 파이프라인 보호가 최우선
        _warn("예기치 못한 오류(비차단): %s" % e)
        return 0


if __name__ == "__main__":
    sys.exit(main())
