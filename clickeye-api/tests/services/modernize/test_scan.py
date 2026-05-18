"""scan.scan_workspace 단위 테스트 — 확장자 분포 / 50k 파일 cap.

tmp_path 픽스처로 격리. DB / 외부 API 의존 X.
"""

from __future__ import annotations

from pathlib import Path

from app.services.modernize.scan import scan_workspace


def test_scan_empty_dir(tmp_path: Path) -> None:
    result = scan_workspace(tmp_path)
    assert result["file_count"] == 0
    assert result["loc_total"] == 0
    assert result["lang_distribution"] == {}
    assert result["truncated"] is False


def test_scan_nonexistent_dir(tmp_path: Path) -> None:
    result = scan_workspace(tmp_path / "missing")
    assert result["file_count"] == 0


def test_scan_python_only(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print('hello')\n" * 10)
    (tmp_path / "b.py").write_text("x = 1\n" * 5)
    result = scan_workspace(tmp_path)
    assert result["file_count"] == 2
    assert "python" in result["lang_distribution"]  # type: ignore[operator]
    assert result["lang_distribution"]["python"] == 1.0  # type: ignore[index]


def test_scan_mixed_languages(tmp_path: Path) -> None:
    # 정확히 byte 단위로 비율 검증
    (tmp_path / "main.py").write_text("x" * 600)  # python 60%
    (tmp_path / "app.ts").write_text("y" * 400)  # typescript 40%
    result = scan_workspace(tmp_path)
    dist = result["lang_distribution"]
    assert isinstance(dist, dict)
    assert dist["python"] == 0.6
    assert dist["typescript"] == 0.4


def test_scan_skips_node_modules(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.ts").write_text("x" * 100)
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("y" * 999_999)
    result = scan_workspace(tmp_path)
    # node_modules 가 skip 되므로 ts 100%
    assert result["file_count"] == 1
    assert result["lang_distribution"] == {"typescript": 1.0}


def test_scan_skips_dotgit_and_pycache(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("x" * 100)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("y" * 500)
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "a.pyc").write_text("z" * 200)
    result = scan_workspace(tmp_path)
    assert result["file_count"] == 1


def test_scan_ignores_unknown_extensions(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("x" * 100)
    (tmp_path / "bin.exe").write_text("y" * 999)
    (tmp_path / "data.bin").write_text("z" * 999)
    result = scan_workspace(tmp_path)
    assert result["file_count"] == 1  # 알 수 없는 확장자는 카운트 안 됨
    assert result["lang_distribution"] == {"python": 1.0}


def test_scan_ignores_large_files(tmp_path: Path) -> None:
    """5MB 초과 파일은 lock/minified 로 간주해 skip."""
    (tmp_path / "small.py").write_text("x" * 100)
    (tmp_path / "huge.js").write_text("y" * (6 * 1024 * 1024))
    result = scan_workspace(tmp_path)
    assert result["file_count"] == 1
    assert result["lang_distribution"] == {"python": 1.0}
