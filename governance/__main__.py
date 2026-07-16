"""거버넌스 커널 CLI — `python -m governance`.

출력: --json 이면 결과 JSON(stdout). exit 0=pass, 2=fail(블로킹).
원래 scripts/pre_merge_gate.py 의 main() 을 이곳으로 이전했다. 신규 인자
--project-dir / --plan-text 를 추가하되 기본값은 각각 None 으로, 미지정 시 커널이
os.getcwd() 를 git 기준으로 사용한다(파이프라인·CI 는 루트 실행이라 기존과 동일).

사용법:
  python -m governance --base main --head ralph/CE-123 --json
  python -m governance --base origin/main --head HEAD --ci --json          # CI 미러
  python -m governance --diff-files "clickeye-api/app/api/x.py" --head ralph/CE-1  # 테스트용
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from governance.core import evaluate


def main() -> int:
    p = argparse.ArgumentParser(description="ClickEye 머지 전 거버넌스 게이트(SSOT)")
    p.add_argument("--base", default="main", help="기준 ref (기본 main)")
    p.add_argument("--head", default="HEAD", help="대상 ref/브랜치 (기본 HEAD)")
    p.add_argument("--ci", action="store_true", help="CI 미러 모드(표기용)")
    p.add_argument("--json", action="store_true", help="결과 JSON 출력")
    p.add_argument(
        "--diff-files",
        default=None,
        help="git 대신 사용할 변경 파일 목록(콤마/줄바꿈 구분, 테스트용)",
    )
    p.add_argument(
        "--project-dir",
        default=None,
        help="git/.ralph 기준 경로(미지정 시 현재 작업 디렉토리)",
    )
    p.add_argument(
        "--plan-text",
        default=None,
        help="plan-trace 검사에 사용할 plan 본문(원격 호출용, 파일 대신)",
    )
    args = p.parse_args()

    files = None
    if args.diff_files is not None:
        files = [f.strip() for f in re.split(r"[,\n]", args.diff_files) if f.strip()]

    result = evaluate(
        args.base,
        args.head,
        files,
        project_dir=args.project_dir,
        plan_text=args.plan_text,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"[governance:{result['governance']}] verdict={result['verdict']} "
              f"tier={result['tier']} merge={result['merge_decision']} "
              f"key={result['issue_key']}")
        for f in result["failures"]:
            print(f"  ❌ {f}", file=sys.stderr)
        for w in result["warnings"]:
            print(f"  ⚠️  {w}", file=sys.stderr)

    return 2 if result["verdict"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
