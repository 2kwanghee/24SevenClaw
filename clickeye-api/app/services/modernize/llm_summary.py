"""Step 6 — Claude API 로 코드베이스 요약.

이 단계는 권장안 생성과는 분리 — 요약은 모든 시나리오에서 공통으로 필요한 컨텍스트.
M5 는 단순한 system prompt 로 시작, M6 에서 시나리오별 세분화 + 권장안 생성 단계 추가.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from app.config import settings
from app.services.claude_service import ClaudeService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

MODERNIZE_SUMMARY_SYSTEM = """You are a senior software architect analyzing an existing codebase.

You will receive:
- scenario: one of 'versionup', 'refactor', 'language_migrate'
- goals_text: user-provided modernization goals (may be empty)
- lang_distribution: language byte ratios
- framework_signals: detected framework versions
- outdated_packages: packages with newer versions available
- snippets: text slices of entry-point files

Your task: produce a concise Markdown summary (≤ 600 words) of:
1. **Stack overview** — primary language, frameworks, build system.
2. **Modernization priorities** — what is most outdated or at risk, given the scenario.
3. **Risk callouts** — EOL runtimes, deprecated frameworks, security flags.
4. **Suggested phasing** — high-level order of work (1~3 phases).
   Do NOT yet list per-package recommendations — that comes in a later step.

Be specific. Reference detected versions. Keep it Korean if the user goals are Korean."""


async def summarize_codebase(
    *,
    scenario: str,
    goals_text: str,
    lang_distribution: dict[str, float],
    framework_signals: dict[str, str],
    outdated_packages: list[dict[str, Any]],
    snippets: list[dict[str, Any]],
    db: AsyncSession | None = None,
    task_id: str | None = None,
) -> tuple[str, int]:
    """Claude API 호출. (summary_md, tokens_used) 반환.

    Anthropic API key 미설정 시 placeholder 요약 반환 (개발 환경 / 베타 안전 동작).

    계측 배선 (CE-299, 회귀 0): feature_llm_gateway 가 켜지고 db 세션이 주어지면
    호출을 LLM 게이트웨이 경유로 라우팅해 usage 를 원장에 기록한다. flag off 또는
    db 미제공 시 기존 경로를 그대로 사용한다(동작·반환 불변, 투명 계측).
    """
    if not settings.anthropic_api_key:
        return _placeholder_summary(
            scenario=scenario,
            lang_distribution=lang_distribution,
            framework_signals=framework_signals,
            outdated_packages=outdated_packages,
        ), 0

    # 컨텍스트 구성 — JSON 으로 직렬화해 모델에 전달
    context = {
        "scenario": scenario,
        "goals_text": goals_text or "",
        "lang_distribution": lang_distribution,
        "framework_signals": framework_signals,
        "outdated_packages": outdated_packages[:30],  # 길이 제한
        "snippets": snippets[:8],  # 길이 제한
    }
    user_text = json.dumps(context, ensure_ascii=False, indent=2)
    messages = [{"role": "user", "content": user_text}]

    # ── 게이트웨이 경유 (flag on + db 제공 시에만) ──────────────────────────────
    if settings.feature_llm_gateway and db is not None:
        from app.services import llm_gateway  # 지연 import (순환 방지)

        result = await llm_gateway.call(
            db,
            system=MODERNIZE_SUMMARY_SYSTEM,
            messages=messages,
            max_tokens=1500,
            request_kind="modernize_summary",
            task_id=task_id,
        )
        return result.text, result.input_tokens + result.output_tokens

    # ── 기존 경로 (flag off — 회귀 0) ─────────────────────────────────────────
    service = ClaudeService()
    client = service._get_client()  # noqa: SLF001 — claude_service 패턴 재사용
    response = await client.messages.create(
        model=settings.anthropic_model_default,
        max_tokens=1500,
        system=MODERNIZE_SUMMARY_SYSTEM,
        messages=messages,  # type: ignore[arg-type]  # TODO: 타입 정합
    )

    summary_md = ""
    for block in response.content:
        if hasattr(block, "text"):
            summary_md += block.text
    tokens_used = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)
    return summary_md, tokens_used

    # TODO(CE-299): claude_service 의 wizard/presets/recommendation 등 광범위한
    # in-API AI 호출도 게이트웨이 경유로 배선해야 한다(블라스트 반경 관리를 위해 이번
    # 스코프에서는 대표 지점 1곳만 계측). 후속 티켓에서 단계적으로 확대.


def _placeholder_summary(
    *,
    scenario: str,
    lang_distribution: dict[str, float],
    framework_signals: dict[str, str],
    outdated_packages: list[dict[str, Any]],
) -> str:
    """LLM 미사용 시 정적 요약 — 분석 데이터만으로 markdown 생성."""
    lines = [
        "# 코드베이스 진단 요약 (placeholder)",
        "",
        f"> 시나리오: **{scenario}**",
        "",
        "## 감지된 스택",
    ]
    if lang_distribution:
        for lang, ratio in lang_distribution.items():
            lines.append(f"- {lang}: {ratio * 100:.1f}%")
    else:
        lines.append("- (감지된 언어 없음)")

    if framework_signals:
        lines.extend(["", "## 프레임워크/런타임"])
        for fw, ver in framework_signals.items():
            lines.append(f"- {fw}: `{ver}`")

    if outdated_packages:
        lines.extend(["", f"## Outdated 패키지 ({len(outdated_packages)}건)"])
        for pkg in outdated_packages[:15]:
            lines.append(
                f"- {pkg.get('name')} (`{pkg.get('current')}` → `{pkg.get('latest')}`, "
                f"severity: {pkg.get('severity')})"
            )

    lines.extend(
        [
            "",
            "## 안내",
            "이 요약은 Anthropic API key 미설정 시 표시되는 정적 요약입니다.",
            "key 설정 후 재분석 시 AI 가 시나리오별 우선순위와 마이그레이션 단계를 제안합니다.",
        ]
    )
    return "\n".join(lines)
