#!/usr/bin/env python3
"""GitHub Actions 셸 주입 정적 검사 (CE-375).

`run:` 블록 안에서 신뢰할 수 없는 입력을 `${{ }}` 로 치환하면 **그 값이 곧 셸 소스가
된다.** Actions 는 bash 가 파싱하기 전에 스크립트 텍스트를 치환하므로, 큰따옴표로 감싸도
백틱(명령 치환)·`$(...)`·`"`(인용 탈출)이 그대로 동작한다.

실측 2026-08-05(PR #106): `post-merge.yml` 이 PR 본문을 `BODY="${{ ... }}"` 로 받아
본문의 백틱 코드 스팬이 CI 에서 실행됐다 — `npm test`·`npx next build` 가 돌고 스텝이
죽었으며, 뒤 스텝(Linear Done 처리·텔레그램)이 조용히 스킵됐다.

올바른 방법은 `env:` 로 넘기는 것이다. env 값은 스크립트에 스플라이스되지 않고 환경변수로
주입되므로 셸이 파싱하지 않는다:

    env:
      PR_BODY: ${{ github.event.pull_request.body }}
    run: |
      ISSUE_ID=$(printf '%s' "$PR_BODY" | grep -oP '[A-Z0-9]+-\\d+' | head -1)

종료 코드: 0 = 위반 없음, 1 = 위반 발견.
"""

from __future__ import annotations

import glob
import re
import sys

# 공격자가 값을 정할 수 있는 컨텍스트.
# - body/title: PR·이슈 작성자가 자유 입력. 사후 수정도 가능하다.
# - head_ref/ref_name: git 레퍼런스는 백틱·`$`·괄호를 허용하므로 브랜치명만으로 성립한다.
# - steps.*.outputs: 위 입력에서 파생될 수 있다(문자셋이 제한돼도 예외를 두지 않는다).
UNTRUSTED = re.compile(
    r"\$\{\{\s*(?:"
    r"github\.event\.[A-Za-z_]+\.(?:body|title)"
    r"|github\.event\.[A-Za-z_]+\.[A-Za-z_]+\.(?:name|login|email)"
    r"|github\.head_ref"
    r"|github\.ref_name"
    r"|steps\.[A-Za-z0-9_-]+\.outputs\.[A-Za-z0-9_-]+"
    r"|needs\.[A-Za-z0-9_-]+\.outputs\.[A-Za-z0-9_-]+"
    r")"
)

RUN_START = re.compile(r"^-?\s*run:\s*(\|.*)?$")


def violations(path: str) -> list[tuple[int, str]]:
    """`run:` 블록 안의 신뢰불가 치환을 (행번호, 원문)으로 반환한다.

    YAML 파서 대신 들여쓰기로 블록을 추적한다 — 검사 대상이 "원문 텍스트에 값이
    스플라이스되는가" 이므로 구조화된 값보다 소스 라인이 정확한 기준이다.
    """
    found: list[tuple[int, str]] = []
    in_run = False
    run_indent = 0
    for lineno, line in enumerate(open(path, encoding="utf-8").read().split("\n"), 1):
        stripped = line.strip()
        if RUN_START.match(stripped) or stripped.startswith("run: "):
            in_run = True
            run_indent = len(line) - len(line.lstrip())
            # `run: echo ${{ ... }}` 한 줄 형태도 검사 대상이다.
            if stripped.startswith("run: ") and UNTRUSTED.search(line):
                found.append((lineno, stripped))
            continue
        if not in_run:
            continue
        indent = len(line) - len(line.lstrip())
        # 블록 종료: 내용이 있고 들여쓰기가 run 이하로 돌아온 줄(주석은 무시).
        if stripped and indent <= run_indent and not stripped.startswith("#"):
            in_run = False
            continue
        if UNTRUSTED.search(line):
            found.append((lineno, stripped))
    return found


def main() -> int:
    targets = sorted(glob.glob(".github/workflows/*.yml")) + sorted(
        glob.glob(".github/workflows/*.yaml")
    )
    if not targets:
        print("검사 대상 워크플로 없음")
        return 0

    total = 0
    for path in targets:
        for lineno, text in violations(path):
            total += 1
            print(f"❌ {path}:{lineno}: run 블록에서 신뢰불가 입력 치환")
            print(f"     {text[:120]}")

    if total:
        print()
        print(f"위반 {total}건 — `env:` 로 넘기고 run 안에서는 \"$VAR\" 로 읽으세요(CE-375).")
        print("이 치환은 값이 셸 소스가 되어 임의 명령 실행으로 이어집니다.")
        return 1

    print(f"✅ run 블록 내 신뢰불가 입력 치환 없음 ({len(targets)}개 워크플로)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
