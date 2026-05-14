"""`.claude/skills/*/SKILL.md` frontmatter를 파싱하여 스킬 카탈로그 JSON을 생성한다.

Usage:
    uv run python scripts/build_skills_catalog.py
    uv run python scripts/build_skills_catalog.py --output app/data/catalog/skills.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml  # pyyaml

# 이 스크립트 위치 기준으로 `.claude/skills/` 탐색
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SKILLS_DIR = _REPO_ROOT / ".claude" / "skills"
_CATALOG_DIR = Path(__file__).resolve().parent.parent / "app" / "data" / "catalog"
_DEFAULT_OUTPUT = _CATALOG_DIR / "skills.json"

# 공개 여부 — 워크플로 자동화 내부 스킬은 제외
_PUBLIC_SLUGS: set[str] = {
    "fullstack",
    "uiux",
    "tdd-smart-coding",
    "ai-critique",
    "verify-implementation",
    "ralph-loop",
    "run-pipeline",
    "log-work",
    "prd-to-linear",
    "setup",
}

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)

# 슬러그 → 표시명 수동 매핑 (H1 없는 파일 처리)
_DISPLAY_NAMES: dict[str, str] = {
    "fullstack": "풀스택 엔지니어",
    "uiux": "UI/UX 엔지니어",
    "log-work": "작업 로그 기록",
    "tdd-smart-coding": "TDD 스마트 코딩",
    "ai-critique": "AI 코드 리뷰",
    "verify-implementation": "구현 검증",
    "ralph-loop": "Ralph 자율 개발 루프",
    "run-pipeline": "자동 개발 파이프라인",
    "prd-to-linear": "PRD → Linear 자동 등록",
    "setup": "워크플로 환경 셋업",
}


def _extract_display_name(slug: str, body: str) -> str:
    """수동 매핑 → H1 → slug 순으로 표시 이름을 결정한다."""
    if slug in _DISPLAY_NAMES:
        return _DISPLAY_NAMES[slug]
    m = _H1_RE.search(body)
    if m:
        return m.group(1).strip()
    print(f"[WARN] 표시 이름 없음, 슬러그를 이름으로 사용: {slug}", file=sys.stderr)
    return slug


def _parse_skill_md(path: Path) -> dict[str, object] | None:
    """SKILL.md를 파싱하여 스킬 정보 dict를 반환한다. 실패 시 None."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"[WARN] 읽기 실패, 건너뜀: {path} ({e})", file=sys.stderr)
        return None

    m = _FRONTMATTER_RE.match(raw)
    if not m:
        print(f"[WARN] frontmatter 없음, 건너뜀: {path}", file=sys.stderr)
        return None

    try:
        front: dict[str, object] = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        print(f"[WARN] YAML 파싱 오류, 건너뜀: {path} ({e})", file=sys.stderr)
        return None

    body = raw[m.end():]
    slug = path.parent.name

    description = str(front.get("description") or "")
    name = _extract_display_name(slug, body)

    return {
        "slug": slug,
        "name": name,
        "description": description,
        "category": "workflow",
        "is_public": slug in _PUBLIC_SLUGS,
        "output_file": f"{slug}.md",
        "body_md": body.strip(),
    }


def build_catalog() -> list[dict[str, object]]:
    """`.claude/skills/` 디렉토리를 스캔하여 카탈로그 목록 반환."""
    if not _SKILLS_DIR.exists():
        print(f"[ERROR] skills directory not found: {_SKILLS_DIR}", file=sys.stderr)
        sys.exit(1)

    catalog: list[dict[str, object]] = []
    for skill_dir in sorted(_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        entry = _parse_skill_md(skill_md)
        if entry:
            catalog.append(entry)

    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="스킬 카탈로그 JSON 생성기")
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help="출력 JSON 파일 경로",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="파일 저장 없이 stdout 출력",
    )
    args = parser.parse_args()

    catalog = build_catalog()
    print(f"[INFO] 스킬 {len(catalog)}개 파싱 완료", file=sys.stderr)

    output_data = json.dumps(catalog, ensure_ascii=False, indent=2)

    if args.stdout:
        print(output_data)
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output_data + "\n", encoding="utf-8")
    print(f"[INFO] 저장 완료: {args.output}", file=sys.stderr)
    public_count = sum(1 for e in catalog if e["is_public"])
    private_count = len(catalog) - public_count
    print(f"[INFO]   공개 스킬: {public_count}, 내부 스킬: {private_count}", file=sys.stderr)


if __name__ == "__main__":
    main()
