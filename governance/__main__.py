"""거버넌스 커널 CLI — `python -m governance`.

출력: --json 이면 결과 JSON(stdout). exit 0=pass, 2=fail(블로킹).
원래 scripts/pre_merge_gate.py 의 main() 을 이곳으로 이전했다. 신규 인자
--project-dir / --plan-text 를 추가하되 기본값은 각각 None 으로, 미지정 시 커널이
os.getcwd() 를 git 기준으로 사용한다(파이프라인·CI 는 루트 실행이라 기존과 동일).

사용법:
  python -m governance --base main --head ralph/CE-123 --json
  python -m governance --base origin/main --head HEAD --ci --json          # CI 미러
  python -m governance --diff-files "clickeye-api/app/api/x.py" --head ralph/CE-1  # 테스트용
  python -m governance --head ralph/TASK-GATE-001 --policy policy.json --json      # 정책 주입
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from governance.core import Policy, PolicyError, evaluate


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
    p.add_argument(
        "--usage-json",
        default=None,
        help="트리아지 예산/레이트 주입용 usage dict(JSON). 예: '{\"cost\":1.2,\"tokens\":5000}'",
    )
    p.add_argument(
        "--metrics-json",
        default=None,
        help="트리아지 risk_score 주입용 metrics dict(JSON). 예: '{\"coverage\":0.6,\"diff_lines\":500}'",
    )
    p.add_argument(
        "--policy",
        default=None,
        help=(
            "프로젝트 정책(JSON 문자열 또는 .json 파일 경로). 미지정 시 기본 ClickEye 정책"
            "(토글은 env 재독). 지정 시 env 를 조회하지 않으며, 파싱 실패는 차단(exit 2)."
        ),
    )
    args = p.parse_args()

    files = None
    if args.diff_files is not None:
        files = [f.strip() for f in re.split(r"[,\n]", args.diff_files) if f.strip()]

    usage = json.loads(args.usage_json) if args.usage_json else None
    metrics = json.loads(args.metrics_json) if args.metrics_json else None

    # ── 정책 로드 (fail-closed) ────────────────────────────────────────────
    # 명시된 정책이 깨졌으면 조용히 기본값으로 떨어지지 않는다 — 그러면 프로젝트가
    # 의도한 게이트가 사라진 채 통과한다. exit 2(차단)로 드러낸다.
    policy = None
    if args.policy is not None:
        raw = args.policy
        try:
            if os.path.isfile(raw):
                with open(raw, encoding="utf-8") as fh:
                    data = json.load(fh)
            else:
                data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[governance] 정책 로드 실패(차단): {e}", file=sys.stderr)
            return 2
        try:
            policy = Policy.from_dict(data)
        except PolicyError as e:
            print(f"[governance] 정책 형식 불량(차단): {e}", file=sys.stderr)
            return 2

    result = evaluate(
        args.base,
        args.head,
        files,
        project_dir=args.project_dir,
        plan_text=args.plan_text,
        usage=usage,
        metrics=metrics,
        policy=policy,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        triage_suffix = ""
        if "triage" in result:
            triage_suffix = f" triage={result['triage']} risk={result['risk_score']}"
        print(f"[governance:{result['governance']}] verdict={result['verdict']} "
              f"tier={result['tier']} merge={result['merge_decision']} "
              f"key={result['issue_key']}{triage_suffix}")
        for f in result["failures"]:
            print(f"  ❌ {f}", file=sys.stderr)
        for w in result["warnings"]:
            print(f"  ⚠️  {w}", file=sys.stderr)

    return 2 if result["verdict"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
