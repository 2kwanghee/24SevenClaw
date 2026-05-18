"""Step 2 — 워크스페이스 스캔: 확장자 분포 → lang_distribution.

200MB / 50k 파일 제한. 초과 시 부분 분석으로 fallback.
"""

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

_MAX_FILES = 50_000
_MAX_TOTAL_BYTES = 200 * 1024 * 1024  # 200MB
_TEXT_EXTENSIONS_TO_LANG: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rs": "rust",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".vue": "vue",
    ".svelte": "svelte",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    ".less": "css",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
}

_SKIP_DIRS = frozenset(
    [
        "node_modules",
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "target",  # Rust/Java
        ".gradle",
        ".idea",
        ".vscode",
    ]
)


def _iter_files(root: Path) -> Iterator[Path]:
    """root 아래 분석 대상 파일을 순회. SKIP_DIRS 제외."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            yield Path(dirpath) / name


def scan_workspace(root: Path) -> dict[str, object]:
    """워크스페이스를 스캔해 통계 반환.

    Returns:
        {
            "loc_total": int,
            "file_count": int,
            "lang_distribution": {"python": 0.62, "typescript": 0.28, ...} (정렬 X, 모든 값 합 ≤ 1)
            "truncated": bool — limit 초과 시 True
        }
    """
    if not root.exists() or not root.is_dir():
        return {
            "loc_total": 0,
            "file_count": 0,
            "lang_distribution": {},
            "truncated": False,
        }

    byte_by_lang: Counter[str] = Counter()
    file_count = 0
    total_bytes = 0
    truncated = False

    for file_path in _iter_files(root):
        ext = file_path.suffix.lower()
        lang = _TEXT_EXTENSIONS_TO_LANG.get(ext)
        if lang is None:
            continue

        try:
            size = file_path.stat().st_size
        except OSError:
            continue

        if size > 5 * 1024 * 1024:  # 5MB 초과 파일은 데이터로 제외 (lock 파일, 미니파이 등)
            continue

        byte_by_lang[lang] += size
        file_count += 1
        total_bytes += size

        if file_count > _MAX_FILES or total_bytes > _MAX_TOTAL_BYTES:
            truncated = True
            break

    if not byte_by_lang:
        return {
            "loc_total": 0,
            "file_count": file_count,
            "lang_distribution": {},
            "truncated": truncated,
        }

    total = float(sum(byte_by_lang.values()))
    distribution = {lang: round(byte / total, 4) for lang, byte in byte_by_lang.most_common()}

    # loc 은 raw byte 의 추정 (line 평균 30 byte 가정 — 정밀 측정은 비용 큼)
    loc_total = int(sum(byte_by_lang.values()) / 30)

    return {
        "loc_total": loc_total,
        "file_count": file_count,
        "lang_distribution": distribution,
        "truncated": truncated,
    }
