"""Step 6.5 — 시나리오별 권장안 생성.

VersionUp 우선 (MVP-2-A). Refactor / LanguageMigrate 는 placeholder + 동일 schema.
JSON strict validation + 1 회 재시도 + Anthropic key 미설정 시 deterministic fallback.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.config import settings
from app.services.claude_service import ClaudeService

_VERSIONUP_SYSTEM = """You are a senior dependency upgrade planner.

Input (JSON): scenario, goals_text, lang_distribution, framework_signals,
outdated_packages, manifests, llm_summary.

Your task: produce STRICT JSON only — no prose, no markdown fences.
Each recommendation upgrades EXACTLY ONE package or runtime version.
Group breaking changes inside the 'after.breaking_changes' array.

Output schema:
{
  "recommendations": [
    {
      "category": "upgrade",
      "target_path": "<manifest path, e.g. pyproject.toml>",
      "before": {"pkg": "<name>", "version": "<current>"},
      "after": {
        "version": "<latest>",
        "migration_notes": "<plain text>",
        "breaking_changes": ["<change 1>", "<change 2>"]
      },
      "title": "<one-line title, Korean OK>",
      "rationale_md": "<short markdown rationale>",
      "effort": "S" | "M" | "L",
      "risk": "low" | "med" | "high",
      "priority": <int 1..100, lower = sooner>,
      "prompt_md": "<auto_dev_pipeline.sh task prompt, markdown>"
    },
    ...
  ]
}

Rules:
- 6 ~ 20 recommendations total.
- Priority: EOL runtime first, then major version jumps, then minor.
- 'prompt_md' must be a ready-to-use task description for an AI coding agent.
- Korean is preferred for title/rationale_md/prompt_md when the user goals_text is Korean.
"""

_REFACTOR_SYSTEM = """You are a senior code reviewer. Identify code smells, layering
violations, dead code, missing tests. Do NOT suggest dependency upgrades or language changes.
Output STRICT JSON in the same schema as the VersionUp planner, with category='refactor'."""

_LANGUAGE_MIGRATE_SYSTEM = """You are a migration architect. Produce a phased plan
to migrate FROM the detected primary stack TO the user-provided target_stack.
First recommendation is always 'scaffolding', last is 'cutover'. Output STRICT JSON
in the same schema, with category='migrate'."""

_SYSTEM_PROMPTS = {
    "versionup": _VERSIONUP_SYSTEM,
    "refactor": _REFACTOR_SYSTEM,
    "language_migrate": _LANGUAGE_MIGRATE_SYSTEM,
}


async def generate_recommendations(
    *,
    scenario: str,
    goals_text: str,
    lang_distribution: dict[str, float],
    framework_signals: dict[str, str],
    outdated_packages: list[dict[str, Any]],
    manifests: list[dict[str, Any]],
    llm_summary: str,
) -> list[dict[str, Any]]:
    """시나리오별 권장안 list 반환. 실패 시 빈 list (분석 자체는 ready 처리됨)."""

    if not settings.anthropic_api_key:
        return _deterministic_versionup_fallback(outdated_packages, framework_signals)

    system = _SYSTEM_PROMPTS.get(scenario, _VERSIONUP_SYSTEM)
    context = {
        "scenario": scenario,
        "goals_text": goals_text,
        "lang_distribution": lang_distribution,
        "framework_signals": framework_signals,
        "outdated_packages": outdated_packages[:50],
        "manifests": manifests[:10],
        "llm_summary": llm_summary[:6000],
    }

    parsed = await _call_claude(system=system, context=context)
    if parsed is None:
        # 1회 재시도 — 동일 context, 다른 random seed (max_tokens 약간 줄임)
        parsed = await _call_claude(system=system, context=context, retry=True)

    if parsed is None:
        # 모든 시도 실패 → deterministic fallback (분석은 보존)
        return _deterministic_versionup_fallback(outdated_packages, framework_signals)

    return parsed


async def _call_claude(
    *, system: str, context: dict[str, Any], retry: bool = False
) -> list[dict[str, Any]] | None:
    """Claude messages.create + strict JSON validation."""
    service = ClaudeService()
    client = service._get_client()  # noqa: SLF001
    try:
        response = await client.messages.create(
            model=settings.anthropic_model_default,
            max_tokens=4000 if not retry else 3000,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False, indent=2),
                }
            ],
        )
    except Exception:
        return None

    raw = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw += block.text

    return _parse_strict_recommendations(raw)


def _parse_strict_recommendations(raw: str) -> list[dict[str, Any]] | None:
    """LLM 응답에서 JSON 추출 + recommendations[] 정합성 검증.

    응답이 markdown fence 로 감싸인 경우도 허용.
    """
    if not raw.strip():
        return None
    # markdown ```json ... ``` 제거
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", raw.strip(), flags=re.MULTILINE)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    recs = data.get("recommendations")
    if not isinstance(recs, list):
        return None

    valid: list[dict[str, Any]] = []
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        title = rec.get("title")
        category = rec.get("category")
        if not isinstance(title, str) or not isinstance(category, str):
            continue
        # 필수 필드는 title + category 만. 나머지는 default 채움.
        valid.append(
            {
                "category": category,
                "target_path": _safe_str(rec.get("target_path")),
                "before": rec.get("before") if isinstance(rec.get("before"), dict) else None,
                "after": rec.get("after") if isinstance(rec.get("after"), dict) else None,
                "title": title,
                "rationale_md": _safe_str(rec.get("rationale_md")),
                "effort": _normalize_effort(rec.get("effort")),
                "risk": _normalize_risk(rec.get("risk")),
                "priority": _normalize_priority(rec.get("priority")),
                "prompt_md": _safe_str(rec.get("prompt_md")),
            }
        )
    return valid if valid else None


def _safe_str(v: object) -> str:
    return str(v) if isinstance(v, str | int | float) else ""


def _normalize_effort(v: object) -> str:
    if isinstance(v, str) and v.upper() in ("S", "M", "L"):
        return v.upper()
    return "M"


def _normalize_risk(v: object) -> str:
    if isinstance(v, str) and v.lower() in ("low", "med", "high"):
        return v.lower()
    return "med"


def _normalize_priority(v: object) -> int:
    if isinstance(v, int):
        return max(1, min(100, v))
    if isinstance(v, float):
        return max(1, min(100, int(v)))
    return 50


def _deterministic_versionup_fallback(
    outdated_packages: list[dict[str, Any]],
    framework_signals: dict[str, str],
) -> list[dict[str, Any]]:
    """Anthropic 미설정 시 outdated_packages 를 기계적으로 권장안으로 변환.

    추가 안전망: outdated 가 비어있어도 framework_signals 의 EOL 항목만으로 권장안 1건 생성.
    """
    recs: list[dict[str, Any]] = []
    for idx, pkg in enumerate(outdated_packages[:20], start=1):
        name = pkg.get("name") or "package"
        current = pkg.get("current") or ""
        latest = pkg.get("latest") or ""
        severity = pkg.get("severity") or "low"
        kind = pkg.get("kind") or "python"
        target_path = "pyproject.toml" if kind == "python" else "package.json"

        risk = "high" if severity == "high" else "med" if severity == "med" else "low"
        effort = "L" if risk == "high" else "M" if risk == "med" else "S"
        priority = 10 + idx if risk == "high" else 30 + idx if risk == "med" else 50 + idx

        recs.append(
            {
                "category": "upgrade",
                "target_path": target_path,
                "before": {"pkg": name, "version": current},
                "after": {"version": latest, "migration_notes": "", "breaking_changes": []},
                "title": f"{name} {current} → {latest} 업그레이드",
                "rationale_md": (
                    f"{name} 의 현재 버전(`{current}`)이 최신(`{latest}`) 보다 낮습니다."
                    f" severity: **{severity}**."
                ),
                "effort": effort,
                "risk": risk,
                "priority": priority,
                "prompt_md": (
                    f"# {name} {current} → {latest}\n\n"
                    f"## Files in scope\n- `{target_path}`\n\n"
                    f"## Acceptance criteria\n"
                    f"- [ ] {target_path} 의 {name} 버전을 {latest} 로 갱신\n"
                    f"- [ ] 빌드/테스트 통과\n"
                ),
            }
        )

    # framework EOL 단독 권장안 추가 (outdated 0 인 케이스)
    for fw, ver in framework_signals.items():
        if fw == "python" and any(v in ver for v in ("3.6", "3.7", "3.8")):
            recs.append(
                {
                    "category": "upgrade",
                    "target_path": "pyproject.toml",
                    "before": {"pkg": "python", "version": ver},
                    "after": {"version": "3.12", "migration_notes": "", "breaking_changes": []},
                    "title": f"Python {ver} → 3.12 (EOL 대응)",
                    "rationale_md": f"Python {ver} 는 EOL 이거나 곧 EOL 입니다.",
                    "effort": "L",
                    "risk": "high",
                    "priority": 1,
                    "prompt_md": (
                        "# Python runtime upgrade\n\n## Files in scope\n"
                        "- pyproject.toml\n- Dockerfile\n- .python-version\n\n"
                        "## Acceptance criteria\n- [ ] Python 3.12 환경에서 빌드/테스트 통과\n"
                    ),
                }
            )
    return recs
