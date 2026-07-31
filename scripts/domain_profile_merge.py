#!/usr/bin/env python3
"""도메인 제약 병합기 (파생형 하네스 Tier 2) — 정제 산출물의 도메인 제약을 누적 물질화.

metaprompt 정제 결과(refined md)에서 `## 도메인 제약 (Domain Constraints)` 섹션을
추출해 워크스페이스 `<target>/.claude/CLAUDE.domain.md` 에 **티켓 키 마커 블록**으로
멱등 병합한다. 같은 키 재실행 시 해당 블록만 교체(중복 없음), 없으면 append.

LLM·네트워크 없음. Python 3 표준 라이브러리 전용. 결정론적.

exit 0 고정(파이프라인 비차단). stdout 에 결과 JSON 한 줄:
  - 병합: {"merged": true, "ticket": "...", "target": "..."}
  - 섹션 부재: {"merged": false, "reason": "no_section"}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Optional

DOMAIN_FILE = "CLAUDE.domain.md"
FILE_HEADER = "# 도메인 제약 프로파일 (자동 누적 — domain_profile_merge.py)"


def extract_domain_section(text: str) -> Optional[str]:
    """refined md 에서 도메인 제약 섹션(헤더 포함)을 추출. 부재 시 None.

    섹션 시작: `## ` 로 시작하고 '도메인 제약' 또는 'Domain Constraints' 를 포함하는 줄.
    섹션 끝: 다음 `## ` 헤더 직전 또는 EOF. 코드펜스 안의 `## ` 는 무시하지 않는다
    (정제 스펙의 도메인 섹션은 평문 리스트가 관례 — 보수적으로 헤더만 경계로 삼는다).
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("## ") and ("도메인 제약" in s or "Domain Constraints" in s):
            start = i
            break
    if start is None:
        return None

    body: list[str] = [lines[start]]
    for line in lines[start + 1:]:
        if line.strip().startswith("## "):
            break
        body.append(line)

    # 헤더만 있고 실질 내용이 없으면(공백/코드펜스 잔해뿐) 섹션 없음으로 취급(패딩 방지)
    section = "\n".join(body).rstrip()
    content_after_header = "\n".join(body[1:]).strip()
    content_after_header = content_after_header.strip("`").strip()
    if not content_after_header:
        return None
    return section


def _block(ticket: str, section: str) -> str:
    return (
        f"<!-- domain:{ticket} begin -->\n"
        f"{section}\n"
        f"<!-- domain:{ticket} end -->"
    )


def merge_block(existing: Optional[str], ticket: str, section: str) -> str:
    """티켓 키 마커 블록을 멱등 병합 — 같은 키 있으면 교체, 없으면 append."""
    block = _block(ticket, section)
    if not existing:
        return f"{FILE_HEADER}\n\n{block}\n"

    body = existing
    if FILE_HEADER not in body:
        body = f"{FILE_HEADER}\n\n{body.lstrip()}"

    pattern = re.compile(
        r"<!-- domain:" + re.escape(ticket) + r" begin -->.*?"
        r"<!-- domain:" + re.escape(ticket) + r" end -->",
        re.DOTALL,
    )
    if pattern.search(body):
        merged = pattern.sub(lambda _m: block, body)
    else:
        merged = body.rstrip() + "\n\n" + block + "\n"
    if not merged.endswith("\n"):
        merged += "\n"
    return merged


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="도메인 제약 병합기 (Harness Tier 2)")
    p.add_argument("--refined", required=True, help="정제 산출물 md 경로")
    p.add_argument("--target", required=True, help="구현 대상 워크디렉터리(.claude/ 상위)")
    p.add_argument("--ticket", required=True, help="이슈 키(마커 블록 키)")
    args = p.parse_args(argv)

    try:
        with open(args.refined, encoding="utf-8") as fh:
            refined_text = fh.read()
    except OSError as e:
        print(json.dumps({"merged": False, "reason": f"refined_read_error: {e}"},
                         ensure_ascii=False))
        return 0

    section = extract_domain_section(refined_text)
    if section is None:
        print(json.dumps({"merged": False, "reason": "no_section"}, ensure_ascii=False))
        return 0

    claude_dir = os.path.join(os.path.abspath(args.target), ".claude")
    os.makedirs(claude_dir, exist_ok=True)
    domain_path = os.path.join(claude_dir, DOMAIN_FILE)

    existing = None
    if os.path.exists(domain_path):
        with open(domain_path, encoding="utf-8") as fh:
            existing = fh.read()

    merged = merge_block(existing, args.ticket, section)
    with open(domain_path, "w", encoding="utf-8") as fh:
        fh.write(merged)

    print(json.dumps(
        {"merged": True, "ticket": args.ticket, "target": domain_path},
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
