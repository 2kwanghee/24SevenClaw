#!/usr/bin/env python3
"""공통 .env 파일 로더.

모든 파이프라인 스크립트가 이 모듈을 사용하여 환경변수를 로딩한다.
.env 파일 우선, os.environ 폴백.

사용법:
    from env_loader import load_env, get_var

    env = load_env()
    api_key = get_var("LINEAR_API_KEY", required=True)
"""

import os
import sys

_PROJECT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_env_cache: dict[str, str] | None = None


def load_env() -> dict[str, str]:
    """Load all key-value pairs from .env file. Cached after first call."""
    global _env_cache
    if _env_cache is not None:
        return _env_cache

    env_vars: dict[str, str] = {}
    env_path = os.path.join(_PROJECT_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip("\"'")
    _env_cache = env_vars
    return env_vars


def get_var(key: str, required: bool = False) -> str | None:
    """Get env var: .env file first, os.environ fallback."""
    env = load_env()
    value = env.get(key) or os.getenv(key)
    if required and not value:
        print(f"Error: {key} is required. Set it in .env or environment.", file=sys.stderr)
        sys.exit(1)
    return value
