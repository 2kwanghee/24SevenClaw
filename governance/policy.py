"""거버넌스 정책 값객체(Policy) — 다프로젝트 딜리버리의 정책 주입 지점.

## 왜 이 모듈이 있는가

`governance.core.evaluate()` 는 원래부터 순수함수였다 — `files`·`project_dir`·`plan_text`·
`usage`·`metrics` 가 모두 인자로 빠져 있다. 그러나 **정책**(계약면 경로·고위험 경로·이슈 키
형태·토글·임계값)만은 모듈 상수와 `os.environ` 에 묶여 있었다. 그래서 커널은
"어떤 저장소에 대해서도 판정할 수 있지만, ClickEye 저장소의 정책으로만 판정"할 수 있었다.

`Policy` 는 그 마지막 결합을 끊는다. 이후 `evaluate(..., policy=...)` 로 프로젝트별 정책을
주입할 수 있고, 정책 자체는 `DeliveryProfile`(DB)에서 온다.

## stdlib 전용 제약 (core.py 와 동일)

파이프라인·CI 가 시스템 python3 로 설치 없이 호출하므로 제3자 패키지를 import 하지 않는다.
`dataclasses`·`re`·`os` 만 쓴다.

## 토글 스냅샷 시점 — 회귀 0의 급소

현행 `check_*` 함수는 호출마다 `os.environ` 을 읽는다. 정책을 값객체로 옮기면 생성 시점에
동결되어 **장기 실행 API 서버에서 동작이 달라진다.** 그래서 두 모드를 구분한다:

| 모드 | 생성 | 토글·임계값 출처 |
|---|---|---|
| **live** (기본) | `Policy.default()` | **매 조회 시 `os.environ` 재독.** 캐시하지 않음 → 오늘의 동작과 동일 |
| **static** (명시) | `Policy.from_dict(...)` | 주어진 dict. 미지정 키는 **문서화된 기본 의미**로 폴백하며 **env 를 보지 않는다** |

static 이 env 를 보지 않는 것이 다프로젝트화의 핵심이다. 서버 프로세스 env 를 폴백으로 쓰면
한 프로젝트의 토글이 다른 프로젝트 판정에 새어 들어간다(`core.policy_summary()` 도크스트링이
지적한 바로 그 문제).

## fail-closed 범위 (P0)

`from_dict()` 는 형식 불량 입력에 `PolicyError` 를 던진다(fail-closed). 단 이는 **명시적으로
주어진 정책이 깨진 경우**에만 해당한다. 정책 미주입(=`default()`) 경로의 "미설정=on" 기본값은
P0 에서 변경하지 않는다 — 그것을 바꾸는 것 자체가 회귀이기 때문이다. 제어면을 DB 로 승격하는
단계(P4)에서 티어별로 전환한다.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

# ── 토글 원시 리더 ─────────────────────────────────────────────────────────
# core.py 에서 이곳으로 이전했다. core.py 는 이 심볼들을 다시 import 하여 재노출하므로
# `from governance.core import is_enabled` 및 `import *` 계약은 그대로 유지된다.

_FALSEY = {"false", "0", "off", "no"}
_TRUTHY = {"1", "true", "on", "yes"}


def is_enabled(key: str) -> bool:
    """pipeline_config.sh 의 is_enabled 과 동일 의미. 미설정/빈값은 on."""
    val = os.environ.get(key, "")
    if val == "":
        return True
    return val.strip().lower() not in _FALSEY


# ⚠️ is_opt_in 은 is_enabled 와 **의도적으로 반대(divergence)** 다.
#   is_enabled  → 미설정/빈값 = True  (기존 게이트 항목은 기본 on)
#   is_opt_in   → 미설정/그 외 = False, 명시적 opt-in 값만 True (신규 트리아지는 기본 off)
# 트리아지 토글에는 반드시 is_opt_in 을 써야 회귀 0(기본 off)이 보장된다.
def is_opt_in(key: str) -> bool:
    """명시적 opt-in 값(1/true/on/yes, 소문자)만 True. 미설정/그 외는 False."""
    return os.environ.get(key, "").strip().lower() in _TRUTHY


def _env_float(key: str, default: float) -> float:
    """FLOWOPS_GOVERNANCE_* float 임계값 읽기. 미설정/파싱불가면 default(결정적)."""
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# ── 기본 정책 상수 (ClickEye 저장소) ───────────────────────────────────────
# core.py 의 모듈 상수와 **값이 동일해야 한다.** 회귀 0 테스트가 이를 단언한다.

DEFAULT_CONTRACT_SURFACE_PREFIXES = (
    "clickeye-api/app/api/",
    "clickeye-api/app/schemas/",
    "clickeye-api/app/models/",
    "clickeye-api/app/ws/",
)
DEFAULT_OPENAPI_SPEC = "clickeye-contracts/openapi/openapi.json"
DEFAULT_GENERATED_CLIENT_PREFIX = "clickeye-contracts/generated/"
DEFAULT_CONTRACTS_PREFIX = "clickeye-contracts/"

DEFAULT_HIGH_PREFIXES = (
    "clickeye-contracts/",
    "clickeye-infra/",
)
DEFAULT_HIGH_PATH_PATTERN_SOURCES = (
    r"auth",
    r"(secur|secret|crypto|password|token|rbac|permission|credential)",
)

# 이슈 키 형태. **프로젝트마다 다르다** — 이것을 상수로 두면 다프로젝트가 성립하지 않는다.
# 예: ClickEye/Linear 는 `CE-313`·`24S-142` 이지만, infraeye3 는 `TASK-GATE-001`·
# `CYCLE-20260726-00` 을 쓴다. 후자는 아래 기본 shape 를 통과하지 못한다.
DEFAULT_ISSUE_KEY_SHAPE = r"^[A-Z0-9]+-\d+$"
# 브랜치 문자열 어디서든 키를 탐색(대문자/숫자 세그먼트-숫자). lowercase 세그먼트(web/api 등)는
# 매치하지 않고, 24S-142 처럼 숫자로 시작하는 키도 매치.
DEFAULT_ISSUE_KEY_SEARCH = r"[A-Z0-9]+-\d+"

# 트리아지 임계값의 env 키 → 기본값. static 정책은 이 기본값으로 폴백한다(env 미조회).
TRIAGE_THRESHOLD_DEFAULTS: dict[str, float] = {
    "FLOWOPS_GOVERNANCE_TRIAGE_SCORE_REVIEW": 0.40,
    "FLOWOPS_GOVERNANCE_TRIAGE_SCORE_BLOCK": 0.80,
    "FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_LIMIT": 0.0,
    "FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_WARN": 0.0,
    "FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_TOKEN_LIMIT": 0.0,
    "FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_TOKEN_WARN": 0.0,
    "FLOWOPS_GOVERNANCE_TRIAGE_RATE_RPM_LIMIT": 0.0,
    "FLOWOPS_GOVERNANCE_TRIAGE_RATE_TPM_LIMIT": 0.0,
}

# static 정책에서 토글 미지정 시의 폴백. is_enabled 계열은 True(기본 on),
# is_opt_in 계열은 False(기본 off) — env 리더의 의미를 그대로 승계한다.
_OPT_IN_TOGGLES = frozenset(
    {
        "FLOWOPS_GOVERNANCE_TRIAGE",
        "FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE",
        "FLOWOPS_GOVERNANCE_TRIAGE_BUDGET",
    }
)


class PolicyError(ValueError):
    """정책 입력이 형식 불량이다. 호출자는 이를 차단(fail-closed)으로 변환한다."""


def _as_str_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    """JSON 배열 → 문자열 튜플. 빈 문자열·비문자열 원소는 거부(fail-closed)."""
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise PolicyError(f"{field_name}: 문자열 배열이어야 함 (받은 값: {type(value).__name__})")
    out = []
    for i, v in enumerate(value):
        if not isinstance(v, str) or not v.strip():
            raise PolicyError(f"{field_name}[{i}]: 비어있지 않은 문자열이어야 함")
        out.append(v)
    return tuple(out)


def _as_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PolicyError(f"{field_name}: 비어있지 않은 문자열이어야 함")
    return value


def _compile(pattern: str, *, field_name: str, flags: int = 0) -> re.Pattern[str]:
    try:
        return re.compile(pattern, flags)
    except re.error as e:
        raise PolicyError(f"{field_name}: 정규식 컴파일 실패 ({pattern!r}): {e}") from e


@dataclass(frozen=True)
class Policy:
    """거버넌스 판정에 쓰이는 프로젝트별 정책.

    `live=True`(기본) 이면 토글·임계값을 조회 시점에 `os.environ` 에서 재독한다. `live=False`
    (`from_dict()` 산출물)이면 `toggles`/`triage_thresholds` dict 만 보고 env 를 조회하지 않는다.
    """

    contract_surface_prefixes: tuple[str, ...] = DEFAULT_CONTRACT_SURFACE_PREFIXES
    openapi_spec: str = DEFAULT_OPENAPI_SPEC
    generated_client_prefix: str = DEFAULT_GENERATED_CLIENT_PREFIX
    contracts_prefix: str = DEFAULT_CONTRACTS_PREFIX
    high_prefixes: tuple[str, ...] = DEFAULT_HIGH_PREFIXES
    high_path_patterns: tuple[re.Pattern[str], ...] = field(
        default_factory=lambda: tuple(
            re.compile(src, re.IGNORECASE) for src in DEFAULT_HIGH_PATH_PATTERN_SOURCES
        )
    )
    issue_key_re: re.Pattern[str] = field(
        default_factory=lambda: re.compile(DEFAULT_ISSUE_KEY_SHAPE)
    )
    issue_key_search_re: re.Pattern[str] = field(
        default_factory=lambda: re.compile(DEFAULT_ISSUE_KEY_SEARCH)
    )
    toggles: dict[str, bool] = field(default_factory=dict)
    triage_thresholds: dict[str, float] = field(default_factory=dict)
    live: bool = True

    # ── 토글·임계값 조회 ──────────────────────────────────────────────────
    def enabled(self, key: str) -> bool:
        """is_enabled 의미(미설정=on). live 면 env 재독, static 이면 dict→기본값."""
        if self.live:
            return is_enabled(key)
        return bool(self.toggles.get(key, True))

    def opt_in(self, key: str) -> bool:
        """is_opt_in 의미(미설정=off). live 면 env 재독, static 이면 dict→기본값."""
        if self.live:
            return is_opt_in(key)
        return bool(self.toggles.get(key, False))

    def threshold(self, key: str) -> float:
        """트리아지 임계값. live 면 env 재독, static 이면 dict→TRIAGE_THRESHOLD_DEFAULTS."""
        default = TRIAGE_THRESHOLD_DEFAULTS.get(key, 0.0)
        if self.live:
            return _env_float(key, default)
        raw = self.triage_thresholds.get(key, default)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    # ── 생성자 ────────────────────────────────────────────────────────────
    @classmethod
    def default(cls) -> Policy:
        """오늘의 ClickEye 정책. 토글·임계값은 **조회 시점에 env 재독**(live).

        캐시하지 않는다 — 캐시하면 장기 실행 API 서버에서 현행 동작과 달라진다.
        """
        return cls()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Policy:
        """DeliveryProfile.policy(JSON) → Policy. 미지정 필드는 기본 정책을 승계한다.

        산출물은 **static** 이다(`live=False`) — env 를 조회하지 않으므로 서버 프로세스의
        토글이 프로젝트 판정에 새어 들어가지 않는다. 형식 불량이면 `PolicyError`(fail-closed).
        """
        if data is None:
            return cls.default()
        if not isinstance(data, dict):
            raise PolicyError(f"policy: 객체(dict)여야 함 (받은 값: {type(data).__name__})")

        known = {
            "contract_surface_prefixes",
            "openapi_spec",
            "generated_client_prefix",
            "contracts_prefix",
            "high_prefixes",
            "high_path_patterns",
            "issue_key_shape",
            "issue_key_search",
            "toggles",
            "triage_thresholds",
        }
        unknown = sorted(set(data) - known)
        if unknown:
            # 오타로 정책이 조용히 무시되는 것을 막는다(fail-closed).
            raise PolicyError(f"policy: 알 수 없는 키 {unknown} (허용: {sorted(known)})")

        kwargs: dict[str, Any] = {"live": False}

        if "contract_surface_prefixes" in data:
            kwargs["contract_surface_prefixes"] = _as_str_tuple(
                data["contract_surface_prefixes"], field_name="contract_surface_prefixes"
            )
        if "openapi_spec" in data:
            kwargs["openapi_spec"] = _as_str(data["openapi_spec"], field_name="openapi_spec")
        if "generated_client_prefix" in data:
            kwargs["generated_client_prefix"] = _as_str(
                data["generated_client_prefix"], field_name="generated_client_prefix"
            )
        if "contracts_prefix" in data:
            kwargs["contracts_prefix"] = _as_str(
                data["contracts_prefix"], field_name="contracts_prefix"
            )
        if "high_prefixes" in data:
            kwargs["high_prefixes"] = _as_str_tuple(
                data["high_prefixes"], field_name="high_prefixes"
            )
        if "high_path_patterns" in data:
            sources = _as_str_tuple(data["high_path_patterns"], field_name="high_path_patterns")
            kwargs["high_path_patterns"] = tuple(
                _compile(s, field_name="high_path_patterns", flags=re.IGNORECASE) for s in sources
            )
        if "issue_key_shape" in data:
            kwargs["issue_key_re"] = _compile(
                _as_str(data["issue_key_shape"], field_name="issue_key_shape"),
                field_name="issue_key_shape",
            )
        if "issue_key_search" in data:
            kwargs["issue_key_search_re"] = _compile(
                _as_str(data["issue_key_search"], field_name="issue_key_search"),
                field_name="issue_key_search",
            )

        if "toggles" in data:
            raw_toggles = data["toggles"]
            if not isinstance(raw_toggles, dict):
                raise PolicyError("toggles: 객체(dict)여야 함")
            toggles: dict[str, bool] = {}
            for k, v in raw_toggles.items():
                if not isinstance(k, str) or not k.strip():
                    raise PolicyError("toggles: 키는 비어있지 않은 문자열이어야 함")
                if isinstance(v, bool):
                    toggles[k] = v
                elif isinstance(v, str):
                    lowered = v.strip().lower()
                    if lowered in _TRUTHY:
                        toggles[k] = True
                    elif lowered in _FALSEY:
                        toggles[k] = False
                    else:
                        raise PolicyError(f"toggles[{k}]: 불리언으로 해석 불가 ({v!r})")
                else:
                    raise PolicyError(f"toggles[{k}]: 불리언이어야 함 ({type(v).__name__})")
            kwargs["toggles"] = toggles

        if "triage_thresholds" in data:
            raw_th = data["triage_thresholds"]
            if not isinstance(raw_th, dict):
                raise PolicyError("triage_thresholds: 객체(dict)여야 함")
            thresholds: dict[str, float] = {}
            for k, v in raw_th.items():
                if not isinstance(k, str) or not k.strip():
                    raise PolicyError("triage_thresholds: 키는 비어있지 않은 문자열이어야 함")
                if isinstance(v, bool) or not isinstance(v, (int, float, str)):
                    raise PolicyError(f"triage_thresholds[{k}]: 숫자여야 함")
                try:
                    thresholds[k] = float(v)
                except ValueError as e:
                    raise PolicyError(f"triage_thresholds[{k}]: 숫자 변환 실패 ({v!r})") from e
            kwargs["triage_thresholds"] = thresholds

        return cls(**kwargs)

    # ── 직렬화(관측용) ────────────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        """정책을 JSON 직렬화 가능한 dict 로. `from_dict()` 의 역이며 round-trip 가능하다."""
        return {
            "contract_surface_prefixes": list(self.contract_surface_prefixes),
            "openapi_spec": self.openapi_spec,
            "generated_client_prefix": self.generated_client_prefix,
            "contracts_prefix": self.contracts_prefix,
            "high_prefixes": list(self.high_prefixes),
            "high_path_patterns": [p.pattern for p in self.high_path_patterns],
            "issue_key_shape": self.issue_key_re.pattern,
            "issue_key_search": self.issue_key_search_re.pattern,
            "toggles": dict(self.toggles),
            "triage_thresholds": dict(self.triage_thresholds),
        }
