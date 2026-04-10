#!/usr/bin/env python3
"""REVIEW.md에서 구조화된 verdict를 파싱하여 JSON으로 출력.

사용법:
    python3 scripts/parse_review_verdict.py [--file .ralph/REVIEW.md]

출력 (stdout):
    {"verdict": "PASS", "reason": ""}
    {"verdict": "FAIL", "reason": "보안 취약점 발견: SQL injection 위험"}

종료 코드:
    0 — PASS
    1 — FAIL
    2 — verdict를 파싱할 수 없음 (수동 리뷰 필요)
"""

import argparse
import json
import os
import re
import sys


def parse_verdict(content: str) -> dict:
    """REVIEW.md 내용에서 VERDICT 라인을 파싱."""

    # 패턴 1: "VERDICT: PASS" 또는 "VERDICT: FAIL (reason)" — 라인 시작 앵커
    m = re.search(
        r"^VERDICT:\s*(PASS|FAIL)(?:\s*[:\-—]\s*(.+))?",
        content,
        re.IGNORECASE | re.MULTILINE,
    )
    if m:
        verdict = m.group(1).upper()
        reason = (m.group(2) or "").strip()
        return {"verdict": verdict, "reason": reason}

    # 패턴 2: "## Verdict" 섹션 아래의 PASS/FAIL
    m = re.search(
        r"##\s*Verdict[:\s]*[\r\n]+\s*(PASS|FAIL)(?:\s*[:\-—]\s*(.+))?",
        content,
        re.IGNORECASE,
    )
    if m:
        verdict = m.group(1).upper()
        reason = (m.group(2) or "").strip()
        return {"verdict": verdict, "reason": reason}

    # 패턴 3: Codex CLI 실행 실패 fallback 마커
    if "자동 생성 실패" in content or "수동 리뷰가 필요" in content:
        return {"verdict": "UNKNOWN", "reason": "Codex CLI 실행 실패 — 수동 리뷰 필요"}

    return {"verdict": "UNKNOWN", "reason": "verdict를 파싱할 수 없음"}


def main():
    parser = argparse.ArgumentParser(description="REVIEW.md verdict 파서")
    parser.add_argument(
        "--file",
        default=os.path.join(
            os.path.dirname(__file__), "..", ".ralph", "REVIEW.md"
        ),
        help="REVIEW.md 경로 (기본: .ralph/REVIEW.md)",
    )
    args = parser.parse_args()

    filepath = os.path.abspath(args.file)
    if not os.path.exists(filepath):
        result = {"verdict": "UNKNOWN", "reason": "REVIEW.md 파일 없음"}
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(2)

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    result = parse_verdict(content)
    print(json.dumps(result, ensure_ascii=False))

    if result["verdict"] == "PASS":
        sys.exit(0)
    elif result["verdict"] == "FAIL":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
