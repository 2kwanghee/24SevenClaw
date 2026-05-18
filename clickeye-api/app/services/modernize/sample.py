"""Step 5 — entry-point 코드 샘플링.

LLM 입력 컨텍스트로 사용할 텍스트 스니펫을 80k tokens 이내로 자른다.
워크스페이스가 비어있거나 크기 0 인 파일만 있는 경우 빈 list 반환.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_MAX_TOTAL_CHARS = 80_000 * 4  # 80k tokens ≈ 320k chars
_MAX_FILE_CHARS = 8_000

# entry-point 후보 — 흔한 파일명/패턴
_ENTRY_FILE_NAMES = frozenset(
    [
        "main.py",
        "app.py",
        "__init__.py",
        "settings.py",
        "config.py",
        "index.js",
        "index.ts",
        "app.js",
        "app.ts",
        "main.js",
        "main.ts",
        "server.js",
        "server.ts",
        "main.go",
        "main.rs",
        "Cargo.toml",
        "pyproject.toml",
        "package.json",
        "go.mod",
        "Dockerfile",
    ]
)


def sample_workspace(root: Path) -> list[dict[str, Any]]:
    """워크스페이스에서 entry-point + 큰 모듈 N개 텍스트 슬라이스.

    Returns:
        [{"path": "src/main.py", "lang": "python", "text": "..."}, ...]
    """
    if not root.exists() or not root.is_dir():
        return []

    candidates: list[Path] = []
    # 1) entry-point 파일 우선
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(p in (".git", "node_modules", "vendor", ".venv") for p in path.parts):
            continue
        if path.name in _ENTRY_FILE_NAMES:
            candidates.append(path)

    # 2) 큰 .py / .ts / .js 파일 추가 (entry 안 잡혔을 때 보강)
    size_ranked: list[tuple[int, Path]] = []
    if len(candidates) < 5:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(p in (".git", "node_modules", "vendor", ".venv") for p in path.parts):
                continue
            ext = path.suffix.lower()
            if ext not in (".py", ".ts", ".tsx", ".js", ".go", ".rs"):
                continue
            try:
                size_ranked.append((path.stat().st_size, path))
            except OSError:
                continue
        size_ranked.sort(reverse=True)
        for _, path in size_ranked[: 10 - len(candidates)]:
            if path not in candidates:
                candidates.append(path)

    snippets: list[dict[str, Any]] = []
    total_chars = 0
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if not text.strip():
            continue
        clipped = text[:_MAX_FILE_CHARS]
        snippets.append(
            {
                "path": str(path.relative_to(root)),
                "lang": _lang_from_ext(path.suffix.lower()),
                "text": clipped,
            }
        )
        total_chars += len(clipped)
        if total_chars >= _MAX_TOTAL_CHARS:
            break

    return snippets


def _lang_from_ext(ext: str) -> str:
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".toml": "toml",
        ".json": "json",
    }.get(ext, "text")
