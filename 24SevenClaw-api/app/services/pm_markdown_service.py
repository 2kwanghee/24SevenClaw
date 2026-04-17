"""PM 프로필 ↔ Markdown 직렬화/파싱 서비스.

Markdown 형식:
    ---
    name: "이름"
    slug: "slug"
    title: "직함"
    domain: "도메인"
    years_experience: 5
    language: "ko"
    is_active: true
    specialties: ["spec1", "spec2"]
    tech_stack_tags: ["tag1"]
    industry_tags: ["ind1"]
    preferred_solution_types: ["saas"]
    ---

    한 줄 설명(description)

    ---bio---
    상세 소개(bio_long)
"""

import contextlib
import re
from typing import Any

import yaml

from app.models.pm_profile import PMProfile


def serialize_pm_to_markdown(profile: PMProfile) -> str:
    """PM 프로필 모델을 Markdown 문자열로 직렬화한다."""
    raw: Any = profile

    frontmatter: dict[str, Any] = {
        "name": str(raw.name or ""),
        "slug": str(raw.slug or ""),
        "title": str(raw.title or "") or None,
        "domain": str(raw.domain or "") or None,
        "years_experience": int(raw.years_experience) if raw.years_experience else None,
        "language": str(raw.language or "ko"),
        "is_active": bool(raw.is_active),
        "specialties": list(raw.specialties or []),
        "tech_stack_tags": list(raw.tech_stack_tags or []),
        "industry_tags": list(raw.industry_tags or []),
        "preferred_solution_types": list(raw.preferred_solution_types or []),
    }
    # None 값 제거 (선택 필드)
    frontmatter = {k: v for k, v in frontmatter.items() if v is not None}

    yaml_block = yaml.dump(
        frontmatter,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).rstrip()

    description = str(raw.description or "").strip()
    bio_long = str(raw.bio_long or "").strip()

    parts = [f"---\n{yaml_block}\n---"]
    if description:
        parts.append(description)
    if bio_long:
        parts.append("---bio---")
        parts.append(bio_long)

    return "\n\n".join(parts) + "\n"


def parse_markdown_to_pm_dict(markdown: str) -> dict[str, Any]:
    """Markdown 문자열을 PMProfileUpdate 호환 딕셔너리로 파싱한다.

    Returns:
        dict: PMProfileUpdate 필드와 호환되는 딕셔너리.
              파싱에 실패한 필드는 포함하지 않는다.
    """
    result: dict[str, Any] = {}

    # YAML frontmatter 추출
    fm_match = re.match(r"^---\n(.*?)\n---", markdown, re.DOTALL)
    if fm_match:
        try:
            fm = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            fm = {}

        str_fields = ("name", "title", "domain", "language", "slug")
        for field in str_fields:
            if field in fm:
                result[field] = str(fm[field]) if fm[field] is not None else None

        if "is_active" in fm:
            result["is_active"] = bool(fm["is_active"])

        if "years_experience" in fm and fm["years_experience"] is not None:
            with contextlib.suppress(TypeError, ValueError):
                result["years_experience"] = int(fm["years_experience"])

        list_fields = (
            "specialties",
            "tech_stack_tags",
            "industry_tags",
            "preferred_solution_types",
        )
        for field in list_fields:
            if field in fm and isinstance(fm[field], list):
                result[field] = [str(x) for x in fm[field]]

    # frontmatter 이후 body 파싱
    after_fm = re.sub(r"^---\n.*?\n---\n?", "", markdown, flags=re.DOTALL).strip()

    # ---bio--- 구분자로 description / bio_long 분리
    if "---bio---" in after_fm:
        desc_part, bio_part = after_fm.split("---bio---", 1)
        result["description"] = desc_part.strip() or None
        result["bio_long"] = bio_part.strip() or None
    else:
        result["description"] = after_fm.strip() or None

    return result
