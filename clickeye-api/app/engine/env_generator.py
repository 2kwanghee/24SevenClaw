"""환경 변수 파일 생성기 — 스킬별 API 키를 .env / .env.example로 생성."""

import re
from typing import Any


def generate_env_files(
    *,
    env_var_definitions: list[dict[str, Any]],
    env_vars: dict[str, str],
) -> dict[str, str]:
    """.env 및 .env.example 파일 내용을 생성.

    Args:
        env_var_definitions: 카탈로그에서 수집된 환경 변수 정의 목록.
        env_vars: 사용자가 입력한 {변수명: 값} 맵.

    Returns:
        {".env": content, ".env.example": content} 딕셔너리.
        정의가 없고 env_vars도 비어있으면 빈 딕셔너리 반환.
    """
    # 카탈로그 정의 기반 변수 + 사용자가 직접 추가한 변수 수집
    all_var_names: list[str] = []
    var_meta: dict[str, dict[str, Any]] = {}

    # 1) 카탈로그 정의된 변수
    for defn in env_var_definitions:
        name = defn["name"]
        all_var_names.append(name)
        var_meta[name] = defn

    # 2) 사용자가 직접 추가한 변수 (카탈로그에 없는 것)
    for name in env_vars:
        if name not in var_meta:
            all_var_names.append(name)
            var_meta[name] = {"name": name, "description": "", "pattern": "", "required": False}

    if not all_var_names:
        return {}

    # .env 생성 (실제 값 포함)
    env_lines: list[str] = [
        "# 환경 변수 — 이 파일을 .gitignore에 추가하세요",
        "# 자동 생성됨 (ClickEye)",
        "",
    ]

    # .env.example 생성 (값 없이 변수명만)
    example_lines: list[str] = [
        "# 환경 변수 템플릿 — 복사하여 .env로 사용",
        "# cp .env.example .env",
        "",
    ]

    for name in all_var_names:
        meta = var_meta[name]
        value = env_vars.get(name, "")
        description = meta.get("description", "")
        skill_name = meta.get("skill_name", "")

        # 주석 추가
        comment_parts: list[str] = []
        if skill_name:
            comment_parts.append(skill_name)
        if description:
            comment_parts.append(description)

        if comment_parts:
            comment = " — ".join(comment_parts)
            env_lines.append(f"# {comment}")
            example_lines.append(f"# {comment}")

        # 값 검증 + 특수문자 포함 시 따옴표 처리
        validated_value = _validate_env_value(name, value, meta)

        env_lines.append(f"{name}={_quote_env_value(validated_value)}")
        example_lines.append(f"{name}=")
        env_lines.append("")
        example_lines.append("")

    files: dict[str, str] = {
        ".env": "\n".join(env_lines),
        ".env.example": "\n".join(example_lines),
    }

    return files


def _validate_env_value(name: str, value: str, meta: dict[str, Any]) -> str:
    """환경 변수 값의 기본 유효성 검증.

    값이 비어있거나 패턴에 맞지 않으면 빈 문자열 반환 (안전하게 실패).
    """
    if not value or not value.strip():
        return ""

    value = value.strip()
    pattern = meta.get("pattern", "")
    if pattern and not re.match(pattern, value) and _is_dangerous_value(value):
        return ""

    return value


def _quote_env_value(value: str) -> str:
    """#, 공백 등 특수문자가 포함된 값을 따옴표로 감싼다.

    bash .env 로더에서 # 이후가 주석으로 잘리는 현상을 방지한다.
    """
    if not value:
        return value
    needs_quote = any(c in value for c in " \t#$\\`!")
    if not needs_quote:
        return value
    if '"' not in value:
        return f'"{value}"'
    if "'" not in value:
        return f"'{value}'"
    # 큰따옴표와 작은따옴표 모두 포함된 경우 — 큰따옴표 이스케이프
    return '"' + value.replace('"', '\\"') + '"'


def _is_dangerous_value(value: str) -> bool:
    """명백히 위험한 값 감지 (셸 인젝션 등)."""
    dangerous_patterns = [";", "&&", "||", "`", "$(", "${"]
    return any(p in value for p in dangerous_patterns)
