"""Step 3 — manifest 파싱: 패키지 매니페스트에서 의존성 추출.

지원: pyproject.toml, requirements.txt, package.json, go.mod, Cargo.toml, Dockerfile FROM.
다른 manifest 는 향후 추가. 파싱 실패는 silent skip.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

# Dockerfile FROM 라인 패턴
_DOCKERFILE_FROM = re.compile(r"^\s*FROM\s+([^\s]+)", re.MULTILINE | re.IGNORECASE)
# go.mod 의 go directive
_GO_DIRECTIVE = re.compile(r"^\s*go\s+([\d.]+)", re.MULTILINE)


def parse_manifests(root: Path) -> dict[str, object]:
    """워크스페이스 root 의 manifest 들을 파싱.

    Returns:
        {
            "manifests": [{path, kind, raw_deps: dict}],
            "framework_signals": {"python": "3.12", "django": "5.0", ...}
        }
    """
    manifests: list[dict[str, object]] = []
    framework_signals: dict[str, str] = {}

    if not root.exists() or not root.is_dir():
        return {"manifests": manifests, "framework_signals": framework_signals}

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        # node_modules / .git / vendor 디렉토리 skip
        if any(p in (".git", "node_modules", "vendor", ".venv") for p in rel.parts):
            continue

        name = path.name.lower()
        try:
            if name == "pyproject.toml":
                _parse_pyproject(path, rel, manifests, framework_signals)
            elif name == "requirements.txt":
                _parse_requirements_txt(path, rel, manifests)
            elif name == "package.json":
                _parse_package_json(path, rel, manifests, framework_signals)
            elif name == "go.mod":
                _parse_go_mod(path, rel, manifests, framework_signals)
            elif name == "cargo.toml":
                _parse_cargo_toml(path, rel, manifests)
            elif name == "dockerfile" or name.startswith("dockerfile."):
                _parse_dockerfile(path, rel, manifests, framework_signals)
        except (OSError, ValueError, tomllib.TOMLDecodeError, json.JSONDecodeError):
            # 파싱 실패는 silent skip — 분석 실패로 이어지지 않음
            continue

    return {"manifests": manifests, "framework_signals": framework_signals}


def _parse_pyproject(
    path: Path,
    rel: Path,
    manifests: list[dict[str, object]],
    framework_signals: dict[str, str],
) -> None:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    deps: dict[str, str] = {}

    # PEP 621
    project = data.get("project", {})
    if isinstance(project, dict):
        for dep in project.get("dependencies", []):
            name, version = _parse_dep_string(dep)
            if name:
                deps[name] = version
        # Python 버전
        py_req = project.get("requires-python")
        if isinstance(py_req, str):
            framework_signals["python"] = py_req

    # Poetry
    tool = data.get("tool", {})
    if isinstance(tool, dict):
        poetry = tool.get("poetry", {})
        if isinstance(poetry, dict):
            for k, v in poetry.get("dependencies", {}).items():
                if isinstance(v, str):
                    deps[k.lower()] = v
                elif isinstance(v, dict) and "version" in v:
                    deps[k.lower()] = str(v["version"])
                if k.lower() == "python" and isinstance(v, str):
                    framework_signals.setdefault("python", v)

    manifests.append({"path": str(rel), "kind": "python", "raw_deps": deps})
    _detect_python_frameworks(deps, framework_signals)


def _parse_requirements_txt(path: Path, rel: Path, manifests: list[dict[str, object]]) -> None:
    deps: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        name, version = _parse_dep_string(line)
        if name:
            deps[name] = version
    manifests.append({"path": str(rel), "kind": "python", "raw_deps": deps})


def _parse_package_json(
    path: Path,
    rel: Path,
    manifests: list[dict[str, object]],
    framework_signals: dict[str, str],
) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        section = data.get(key, {})
        if isinstance(section, dict):
            for name, version in section.items():
                if isinstance(name, str) and isinstance(version, str):
                    deps[name] = version

    engines = data.get("engines", {})
    if isinstance(engines, dict):
        node_v = engines.get("node")
        if isinstance(node_v, str):
            framework_signals["node"] = node_v

    manifests.append({"path": str(rel), "kind": "node", "raw_deps": deps})
    _detect_node_frameworks(deps, framework_signals)


def _parse_go_mod(
    path: Path,
    rel: Path,
    manifests: list[dict[str, object]],
    framework_signals: dict[str, str],
) -> None:
    text = path.read_text(encoding="utf-8")
    deps: dict[str, str] = {}
    # require 블록 파싱 (단순)
    in_require = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
            continue
        if stripped.startswith("require ") or in_require:
            parts = stripped.removeprefix("require ").strip().split()
            if len(parts) >= 2:
                deps[parts[0]] = parts[1]
    # go directive
    m = _GO_DIRECTIVE.search(text)
    if m:
        framework_signals["go"] = m.group(1)

    manifests.append({"path": str(rel), "kind": "go", "raw_deps": deps})


def _parse_cargo_toml(path: Path, rel: Path, manifests: list[dict[str, object]]) -> None:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    deps: dict[str, str] = {}
    deps_section = data.get("dependencies", {})
    if isinstance(deps_section, dict):
        for name, value in deps_section.items():
            if isinstance(value, str):
                deps[name] = value
            elif isinstance(value, dict) and "version" in value:
                deps[name] = str(value["version"])
    manifests.append({"path": str(rel), "kind": "rust", "raw_deps": deps})


def _parse_dockerfile(
    path: Path,
    rel: Path,
    manifests: list[dict[str, object]],
    framework_signals: dict[str, str],
) -> None:
    text = path.read_text(encoding="utf-8")
    bases: list[str] = []
    for m in _DOCKERFILE_FROM.finditer(text):
        base = m.group(1)
        bases.append(base)
        # python:3.8-slim 형식 감지
        if base.lower().startswith("python:"):
            framework_signals.setdefault("python", base.split(":", 1)[1].split("-", 1)[0])
        elif base.lower().startswith("node:"):
            framework_signals.setdefault("node", base.split(":", 1)[1].split("-", 1)[0])

    manifests.append({"path": str(rel), "kind": "dockerfile", "raw_deps": {"from": bases}})


def _detect_python_frameworks(deps: dict[str, str], framework_signals: dict[str, str]) -> None:
    """Python 의존성에서 주요 프레임워크 버전 추출."""
    for fw in ("django", "flask", "fastapi", "celery", "sqlalchemy", "pydantic"):
        if fw in deps:
            framework_signals[fw] = deps[fw]


def _detect_node_frameworks(deps: dict[str, str], framework_signals: dict[str, str]) -> None:
    """Node 의존성에서 주요 프레임워크 버전 추출."""
    for fw in (
        "react",
        "next",
        "vue",
        "nuxt",
        "svelte",
        "express",
        "@nestjs/core",
        "typescript",
    ):
        if fw in deps:
            framework_signals[fw] = deps[fw]


def _parse_dep_string(dep: str) -> tuple[str, str]:
    """예: 'django>=3.2,<4' → ('django', '>=3.2,<4'). extras 무시."""
    # extras 제거: 'celery[redis]>=5' → 'celery>=5'
    dep = re.sub(r"\[.*?\]", "", dep)
    # 환경 마커 제거
    dep = dep.split(";", 1)[0].strip()
    # operator 분리
    m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(.*)$", dep)
    if not m:
        return ("", "")
    name = m.group(1).lower()
    version = m.group(2).strip()
    return (name, version)
