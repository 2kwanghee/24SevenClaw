#!/usr/bin/env python3
"""워크플로 주입 검사기 테스트 (CE-375).

**이 테스트가 없어서 첫 구현이 통과했다.** 적대적 검토에서 주입 7건 중 1건만 잡히는
것이 드러났고(치명), 원인은 차단목록 방식 + 줄 기반 `run:` 추적이었다. 그래서
검사기를 허용목록 + YAML 파싱으로 바꿨고, 그때 놓쳤던 형태를 여기서 전부 고정한다.

핵심 요구는 두 방향이다:
  ① 주입은 **반드시 잡힌다** — 못 잡는 가드는 없는 것보다 나쁘다(거짓 안심).
  ② 안전한 치환은 **오탐하지 않는다** — 오탐이 잦으면 검사를 끄게 된다.

실행: `python3 scripts/tests/test_check_workflow_injection.py`
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "cwi", _ROOT / "scripts" / "check_workflow_injection.py"
)
assert _SPEC and _SPEC.loader
cwi = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cwi)

PASS = 0
FAIL = 0


def check(label: str, expected: object, actual: object) -> None:
    global PASS, FAIL
    if expected == actual:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}\n      기대={expected!r}\n      실제={actual!r}")


def count(body: str) -> int:
    """워크플로 조각을 임시 파일로 써서 위반 건수를 센다."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "wf.yml"
        p.write_text(body, encoding="utf-8")
        return len(cwi.violations(str(p)))


def job(steps: str) -> str:
    return f"name: T\non: [push]\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n{steps}"


print("[1/3] 주입은 반드시 잡힌다 (첫 구현이 놓쳤던 형태 포함)")

# 치명: 한 줄 대시 형태. 첫 구현은 RUN_START 의 `$` 앵커와 선행 `- ` 때문에 통째로 놓쳤다.
check(
    "한 줄 `- run:` 형태",
    1,
    count(job("      - run: echo ${{ github.event.pull_request.body }}\n")),
)
check(
    "블록 스칼라 run 안",
    1,
    count(job('      - run: |\n          echo "${{ github.event.pull_request.title }}"\n')),
)
# 높음: 첫 구현의 차단목록에 없던 컨텍스트들.
for label, expr in [
    ("workflow_dispatch inputs", "inputs.t"),
    ("github.event.inputs", "github.event.inputs.t"),
    ("push 커밋 메시지", "github.event.head_commit.message"),
    ("커밋 배열 메시지", "github.event.commits[0].message"),
    ("3단 이상 .ref", "github.event.pull_request.head.ref"),
    ("head.label", "github.event.pull_request.head.label"),
    ("브랜치명 head_ref", "github.head_ref"),
    ("브랜치명 ref_name", "github.ref_name"),
    ("스텝 출력 파생값", "steps.x.outputs.y"),
    ("잡 출력 파생값", "needs.b.outputs.y"),
    ("이슈 본문", "github.event.issue.body"),
    ("코멘트 본문", "github.event.comment.body"),
]:
    check(label, 1, count(job(f"      - run: echo ${{{{ {expr} }}}}\n")))

# 높음: with.script 는 run 이 아니지만 값이 JS 소스가 된다(동일 RCE).
check(
    "actions/github-script 의 with.script",
    1,
    count(
        job(
            "      - uses: actions/github-script@v7\n"
            "        with:\n"
            '          script: console.log("${{ github.event.pull_request.body }}")\n'
        )
    ),
)

# 높음: env 로 넘겨도 run 이 다시 소스화하면 방어가 무의미하다.
check(
    "env → eval 재소스화",
    1,
    count(
        job(
            "      - env:\n"
            "          B: ${{ github.event.pull_request.body }}\n"
            '        run: eval "$B"\n'
        )
    ),
)
check(
    "env → bash -c 재소스화",
    1,
    count(
        job(
            "      - env:\n"
            "          B: ${{ github.event.pull_request.body }}\n"
            '        run: bash -c "$B"\n'
        )
    ),
)

# composite action 의 run 도 같은 위험을 갖는다.
check(
    "composite action runs.steps",
    1,
    count(
        "name: A\nruns:\n  using: composite\n  steps:\n"
        "    - run: echo ${{ github.event.pull_request.body }}\n      shell: bash\n"
    ),
)

print("[2/3] 안전한 치환은 오탐하지 않는다")

check(
    "github 생성값(sha/repository/run_id)",
    0,
    count(
        job('      - run: echo "${{ github.sha }} ${{ github.repository }} ${{ github.run_id }}"\n')
    ),
)
check(
    "secrets / vars / matrix / runner / actor",
    0,
    count(
        job(
            "      - env:\n          K: ${{ secrets.API_KEY }}\n"
            '        run: echo "${{ matrix.node }} ${{ runner.os }} ${{ github.actor }}"\n'
        )
    ),
)
check(
    '신뢰불가 값을 env 로 넘겨 "$VAR" 로만 읽는 정상 패턴',
    0,
    count(
        job(
            "      - env:\n"
            "          B: ${{ github.event.pull_request.body }}\n"
            "        run: printf '%s' \"$B\" | grep -oP 'X-\\d+'\n"
        )
    ),
)
# python3 -c 안에서 os.environ 으로 읽는 것은 소스에 스플라이스되지 않아 안전하다.
# 이 구분이 없으면 post-merge.yml 의 Linear 스텝을 오탐한다(실측).
check(
    "python3 -c + os.environ 는 안전",
    0,
    count(
        job(
            "      - env:\n"
            "          ISSUE_ID: ${{ steps.linear.outputs.issue_id }}\n"
            '        run: |\n          python3 -c "\n'
            "          import os\n          print(os.environ['ISSUE_ID'])\n"
            '          "\n'
        )
    ),
)

print("[3/3] 실제 레포 워크플로는 위반이 없다")

import glob  # noqa: E402  — 위 테스트가 통과한 뒤에만 의미가 있다

real = sorted(glob.glob(str(_ROOT / ".github" / "workflows" / "*.yml")))
check("워크플로 파일이 존재한다", True, len(real) > 0)
total = sum(len(cwi.violations(p)) for p in real)
check("실제 워크플로 위반 0건", 0, total)

print()
if FAIL:
    print(f"실패 {FAIL}건 / 통과 {PASS}건")
    sys.exit(1)
print(f"전체 통과: {PASS}건")
