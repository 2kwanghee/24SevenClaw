"""manifest.parse_manifests 단위 테스트 — pyproject/package.json/go.mod 파싱.

tmp_path 픽스처 사용. 외부 의존 X.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.modernize.manifest import parse_manifests


def test_parse_empty_dir(tmp_path: Path) -> None:
    result = parse_manifests(tmp_path)
    assert result["manifests"] == []
    assert result["framework_signals"] == {}


def test_parse_pyproject_pep621(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\n"
        'name = "demo"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["django>=5.0", "fastapi>=0.115"]\n'
    )
    result = parse_manifests(tmp_path)
    manifests: list[dict[str, Any]] = result["manifests"]  # type: ignore[assignment]
    assert len(manifests) == 1
    m = manifests[0]
    assert m["kind"] == "python"
    assert "django" in m["raw_deps"]
    assert "fastapi" in m["raw_deps"]
    signals: dict[str, str] = result["framework_signals"]  # type: ignore[assignment]
    assert signals["python"] == ">=3.12"
    assert "django" in signals
    assert "fastapi" in signals


def test_parse_pyproject_poetry(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "p"\nversion = "0.1.0"\n'
        "[tool.poetry.dependencies]\n"
        'python = "^3.11"\ndjango = "^4.2"\n'
    )
    result = parse_manifests(tmp_path)
    manifests: list[dict[str, Any]] = result["manifests"]  # type: ignore[assignment]
    assert len(manifests) == 1
    assert "django" in manifests[0]["raw_deps"]
    signals: dict[str, str] = result["framework_signals"]  # type: ignore[assignment]
    assert signals["python"] == "^3.11"


def test_parse_requirements_txt(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "django==3.2.18\n"
        "celery[redis]>=5.4\n"
        "# 주석은 무시\n"
        "-e .  # editable 도 무시\n"
        "psycopg[binary]==3.1.0; sys_platform == 'linux'\n"
    )
    result = parse_manifests(tmp_path)
    manifests: list[dict[str, Any]] = result["manifests"]  # type: ignore[assignment]
    deps = manifests[0]["raw_deps"]
    assert "django" in deps
    assert "celery" in deps
    assert "psycopg" in deps


def test_parse_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "engines": {"node": ">=18"},
                "dependencies": {"react": "^18.2", "next": "^14.0"},
                "devDependencies": {"typescript": "^5.0"},
            }
        )
    )
    result = parse_manifests(tmp_path)
    manifests: list[dict[str, Any]] = result["manifests"]  # type: ignore[assignment]
    deps = manifests[0]["raw_deps"]
    assert "react" in deps
    assert "next" in deps
    assert "typescript" in deps
    signals: dict[str, str] = result["framework_signals"]  # type: ignore[assignment]
    assert signals["node"] == ">=18"
    assert "react" in signals


def test_parse_dockerfile(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM python:3.8-slim\nWORKDIR /app\n")
    result = parse_manifests(tmp_path)
    manifests: list[dict[str, Any]] = result["manifests"]  # type: ignore[assignment]
    assert len(manifests) == 1
    assert manifests[0]["kind"] == "dockerfile"
    signals: dict[str, str] = result["framework_signals"]  # type: ignore[assignment]
    # Dockerfile FROM 에서 python:3.8 감지
    assert signals.get("python") == "3.8"


def test_parse_go_mod(tmp_path: Path) -> None:
    (tmp_path / "go.mod").write_text(
        "module example.com/app\n\ngo 1.21\n\n"
        "require (\n"
        "\tgithub.com/gin-gonic/gin v1.9.1\n"
        "\tgithub.com/lib/pq v1.10.9\n"
        ")\n"
    )
    result = parse_manifests(tmp_path)
    manifests: list[dict[str, Any]] = result["manifests"]  # type: ignore[assignment]
    assert manifests[0]["kind"] == "go"
    deps = manifests[0]["raw_deps"]
    assert "github.com/gin-gonic/gin" in deps
    signals: dict[str, str] = result["framework_signals"]  # type: ignore[assignment]
    assert signals.get("go") == "1.21"


def test_parse_skips_node_modules(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"app"}')
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "fake").mkdir()
    (tmp_path / "node_modules" / "fake" / "package.json").write_text('{"name":"fake"}')
    result = parse_manifests(tmp_path)
    # node_modules 의 package.json 은 skip — 루트만 카운트
    assert len(result["manifests"]) == 1  # type: ignore[arg-type]
