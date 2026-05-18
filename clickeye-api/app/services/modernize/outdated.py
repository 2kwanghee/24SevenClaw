"""Step 4 — outdated 패키지 감지.

각 manifest 의 deps 를 pypi.org / registry.npmjs.org 에 조회해 최신 버전 비교.
간단한 process-local 24h 캐시. 동시성 30 으로 제한.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import httpx

_PYPI_URL = "https://pypi.org/pypi/{name}/json"
_NPM_URL = "https://registry.npmjs.org/{name}"
_CONCURRENCY = 30
_TTL_SECONDS = 24 * 60 * 60

# (kind, name) → (cached_at, latest_version)
_cache: dict[tuple[str, str], tuple[float, str | None]] = {}

# EOL Python / Node 기준 (단순 — major.minor 만 비교)
_PYTHON_EOL = {"2.7", "3.6", "3.7", "3.8"}
_NODE_EOL = {"14", "16", "17", "18"}


async def detect_outdated(
    manifests: list[dict[str, Any]],
    framework_signals: dict[str, str],
) -> dict[str, object]:
    """outdated 패키지 + risk flag 반환.

    Returns:
        {
            "outdated_packages": [{name, current, latest, kind, severity}],
            "risk_flags": ["python_eol_3_8", ...]
        }
    """
    outdated: list[dict[str, str]] = []
    semaphore = asyncio.Semaphore(_CONCURRENCY)

    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks: list[asyncio.Task[dict[str, str] | None]] = []
        for manifest in manifests:
            kind = manifest.get("kind")
            deps = manifest.get("raw_deps")
            if not isinstance(deps, dict) or kind not in ("python", "node"):
                continue
            for name, version in deps.items():
                if not isinstance(name, str) or not isinstance(version, str):
                    continue
                tasks.append(
                    asyncio.create_task(_check_one(client, semaphore, kind, name, version))
                )
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, dict):
                    outdated.append(r)

    risk_flags = _collect_risk_flags(framework_signals)
    return {"outdated_packages": outdated, "risk_flags": risk_flags}


async def _check_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    kind: str,
    name: str,
    current: str,
) -> dict[str, str] | None:
    async with semaphore:
        latest = await _get_latest_version(client, kind, name)
    if not latest:
        return None
    # current 에서 숫자만 추출 (>=, ~, ^ 등 제거)
    current_clean = re.sub(r"[^\d.a-zA-Z-]", "", current) or current
    if _same_version(current_clean, latest):
        return None
    return {
        "name": name,
        "current": current,
        "latest": latest,
        "kind": kind,
        "severity": _classify_severity(current_clean, latest),
    }


async def _get_latest_version(client: httpx.AsyncClient, kind: str, name: str) -> str | None:
    """packageregistry 에서 최신 버전 조회 + 24h 캐시."""
    cache_key = (kind, name)
    now = time.time()
    cached = _cache.get(cache_key)
    if cached and now - cached[0] < _TTL_SECONDS:
        return cached[1]

    try:
        if kind == "python":
            res = await client.get(_PYPI_URL.format(name=name))
            if res.status_code != 200:
                _cache[cache_key] = (now, None)
                return None
            body = res.json()
            latest = body.get("info", {}).get("version")
        elif kind == "node":
            res = await client.get(_NPM_URL.format(name=name))
            if res.status_code != 200:
                _cache[cache_key] = (now, None)
                return None
            body = res.json()
            tags = body.get("dist-tags") or {}
            latest = tags.get("latest")
        else:
            return None
    except (httpx.HTTPError, ValueError):
        return None

    if isinstance(latest, str):
        _cache[cache_key] = (now, latest)
        return latest
    _cache[cache_key] = (now, None)
    return None


def _same_version(current: str, latest: str) -> bool:
    """대략적 동일 버전 비교 — 수정 자릿수 같으면 same 로 간주."""
    c_parts = re.findall(r"\d+", current)[:3]
    l_parts = re.findall(r"\d+", latest)[:3]
    return c_parts == l_parts


def _classify_severity(current: str, latest: str) -> str:
    """버전 차이에 따른 severity. major gap → high, minor → med, patch → low."""
    c = re.findall(r"\d+", current)
    l_ = re.findall(r"\d+", latest)
    if not c or not l_:
        return "low"
    try:
        if int(l_[0]) > int(c[0]):
            return "high"
        if len(c) >= 2 and len(l_) >= 2 and int(l_[1]) > int(c[1]):
            return "med"
    except ValueError:
        pass
    return "low"


def _collect_risk_flags(framework_signals: dict[str, str]) -> list[str]:
    """프레임워크 버전에서 EOL/심각도 플래그 추출."""
    flags: list[str] = []
    python_v = framework_signals.get("python", "")
    for eol in _PYTHON_EOL:
        if eol in python_v:
            flags.append(f"python_eol_{eol.replace('.', '_')}")
            break
    node_v = framework_signals.get("node", "")
    for eol in _NODE_EOL:
        if node_v.startswith(eol) or f">={eol}" in node_v or f"^{eol}" in node_v:
            flags.append(f"node_eol_{eol}")
            break
    return flags
