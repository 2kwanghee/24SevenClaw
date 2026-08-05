#!/usr/bin/env python3
"""GitHub Actions 셸/스크립트 주입 정적 검사 (CE-375).

`run:` 안에서 `${{ }}` 로 값을 치환하면 **그 값이 곧 셸 소스가 된다.** Actions 는 bash 가
파싱하기 전에 스크립트 텍스트를 치환하므로, 큰따옴표로 감싸도 백틱(명령 치환)·`$(...)`·
`"`(인용 탈출)이 그대로 동작한다. `actions/github-script` 의 `with.script` 도 같다(JS 소스).

실측 2026-08-05(PR #106): `post-merge.yml` 이 PR 본문을 `BODY="${{ ... }}"` 로 받아
본문의 백틱 코드 스팬이 CI 에서 실행됐다 — `npm test`·`npx next build` 가 돌고 스텝이
죽었으며, 뒤 스텝(Linear Done 처리·텔레그램)이 조용히 스킵됐다.

## 판정 방식 — 허용목록이다(차단목록이 아니다)

첫 구현은 "신뢰할 수 없는 컨텍스트"를 열거했다. 그 방식은 **항상 뒤처진다** — 적대적
검토에서 주입 7건 중 1건만 잡았다(`inputs.*` · `github.event.head_commit.message` ·
`github.event.pull_request.head.ref` 등이 목록에 없어 통과). 그래서 뒤집었다:
**`run:` 에 치환해도 안전한 컨텍스트만 허용하고, 나머지는 전부 위반**으로 본다.
새 공격 표면이 생겨도 기본이 "차단"이다.

올바른 방법은 `env:` 로 넘겨 `"$VAR"` 로 읽는 것이다. env 값은 스크립트에 스플라이스되지
않고 환경변수로 주입되므로 셸이 파싱하지 않는다.

종료 코드: 0 = 위반 없음, 1 = 위반 발견, 2 = 검사 자체 실패(파싱 불가 등).
"""

from __future__ import annotations

import glob
import re
import sys
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - CI 에는 항상 있다
    print("❌ PyYAML 이 필요합니다: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

# ---------------------------------------------------------------------------
# 허용목록 — run/script 에 치환해도 셸 메타문자가 들어올 수 없는 컨텍스트
# ---------------------------------------------------------------------------
# 판단 기준: **값을 정하는 주체가 공격자가 될 수 있는가.**
# - secrets/vars/env/matrix/runner/job/strategy: 레포 관리자·워크플로 작성자가 정한다.
# - github.sha/run_id/run_number/run_attempt/job/workflow/event_name/api_url/server_url/
#   repository(_owner)/workspace/action*/ref_protected: GitHub 가 생성하거나 형태가 고정이다.
# - github.actor/triggering_actor: GitHub 사용자명은 영숫자·하이픈만 허용된다.
# 여기에 없는 것은 전부 위반이다. 특히 `github.event.**`(웹훅 페이로드 전체) ·
# `github.head_ref`/`ref_name`(git 레퍼런스는 백틱·$·괄호를 허용) · `inputs.**`
# (workflow_dispatch 는 자유 입력) · `steps.*.outputs.*`/`needs.*.outputs.*`(파생값).
SAFE_CONTEXT = re.compile(
    r"""^(?:
        secrets\.[A-Za-z0-9_]+
      | vars\.[A-Za-z0-9_]+
      | env\.[A-Za-z0-9_-]+
      | matrix\.[A-Za-z0-9_.-]+
      | runner\.[a-z_]+
      | job\.[a-z_.]+
      | strategy\.[a-z_-]+
      | github\.(?:
            sha | run_id | run_number | run_attempt | job | workflow | workflow_ref
          | event_name | api_url | graphql_url | server_url | workspace
          | repository | repository_owner | repository_id | repository_owner_id
          | actor | actor_id | triggering_actor | token | retention_days
          | action | action_path | action_ref | action_repository | action_status
          | ref_protected | ref_type | secret_source | path | env
        )
    )$""",
    re.VERBOSE,
)

EXPR = re.compile(r"\$\{\{(.+?)\}\}", re.DOTALL)

# run 블록에서 env 변수를 다시 셸/JS 소스로 만드는 형태. env: 로 넘겨도 이러면 무의미하다.
REEVAL = re.compile(
    r"""(?:^|[;&|(\s])(?:
          eval\s
        | (?:ba)?sh\s+-c\s
        | (?:ba)?sh\s+-\S*c\S*\s
        | python3?\s+-c\s
        | node\s+-e\s
    )""",
    re.VERBOSE | re.MULTILINE,
)

# ---------------------------------------------------------------------------


def unsafe_exprs(text: str) -> list[str]:
    """문자열 안의 `${{ }}` 중 허용목록에 없는 것들을 반환한다."""
    bad: list[str] = []
    for raw in EXPR.findall(text or ""):
        expr = raw.strip()
        if not SAFE_CONTEXT.match(expr):
            bad.append(expr)
    return bad


def _steps(doc: Any) -> list[tuple[str, dict[str, Any]]]:
    """워크플로/composite action 문서에서 (잡이름, 스텝) 목록을 뽑는다."""
    out: list[tuple[str, dict[str, Any]]] = []
    if not isinstance(doc, dict):
        return out
    # 워크플로: jobs.<id>.steps
    jobs = doc.get("jobs")
    if isinstance(jobs, dict):
        for job_id, job in jobs.items():
            if isinstance(job, dict):
                for st in job.get("steps") or []:
                    if isinstance(st, dict):
                        out.append((str(job_id), st))
    # composite action: runs.steps
    runs = doc.get("runs")
    if isinstance(runs, dict):
        for st in runs.get("steps") or []:
            if isinstance(st, dict):
                out.append(("runs", st))
    return out


def violations(path: str) -> list[str]:
    """파일 1개의 위반 설명 목록. 파싱 실패는 예외를 올린다(조용히 통과시키지 않는다)."""
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)

    found: list[str] = []
    for job_id, step in _steps(doc):
        label = step.get("name") or step.get("uses") or "(run)"
        where = f"{path} [{job_id} / {label}]"

        # ① run: 본문 — 치환값이 셸 소스가 된다.
        run = step.get("run")
        if isinstance(run, str):
            for expr in unsafe_exprs(run):
                found.append(f"{where}: run 안에서 `${{{{ {expr} }}}}` 치환 → 셸 소스")

        # ② with.script — actions/github-script 는 값이 JS 소스가 된다(run 과 동일 위험).
        with_ = step.get("with")
        if isinstance(with_, dict):
            script = with_.get("script")
            if isinstance(script, str):
                for expr in unsafe_exprs(script):
                    found.append(f"{where}: with.script 안에서 `${{{{ {expr} }}}}` 치환 → JS 소스")

        # ③ env: 로 넘긴 뒤 run 에서 eval/bash -c 로 다시 소스화하면 env 의 방어가 무의미하다.
        #
        # 단 **셸이 그 변수를 확장하는 경우만** 위반이다. `python3 -c "…"` 안에서
        # `os.environ['X']` 로 읽는 것은 값이 소스에 스플라이스되지 않으므로 안전하다
        # (실측: 이 구분이 없으면 post-merge.yml 의 Linear 스텝을 오탐한다).
        # 따라서 run 텍스트에 `$VAR`/`${VAR}` 형태의 셸 참조가 있어야 한다.
        env = step.get("env")
        if isinstance(env, dict) and isinstance(run, str) and REEVAL.search(run):
            tainted = [
                k
                for k, v in env.items()
                if isinstance(v, str)
                and unsafe_exprs(v)
                and re.search(r"\$\{?" + re.escape(str(k)) + r"\b", run)
            ]
            if tainted:
                found.append(
                    f"{where}: env {tainted} 가 신뢰불가인데 run 이 eval/-c 로 재소스화한다"
                )
    return found


def main() -> int:
    targets = sorted(
        set(
            glob.glob(".github/workflows/*.yml")
            + glob.glob(".github/workflows/*.yaml")
            # composite action 의 run: 도 같은 위험을 갖는다(재귀 탐색).
            + glob.glob(".github/actions/**/action.yml", recursive=True)
            + glob.glob(".github/actions/**/action.yaml", recursive=True)
        )
    )
    if not targets:
        print("검사 대상 워크플로 없음")
        return 0

    total = 0
    for path in targets:
        try:
            items = violations(path)
        except Exception as exc:  # 파싱 실패를 통과로 처리하면 검사가 무력해진다.
            print(f"❌ {path}: 파싱 실패 — {exc}")
            return 2
        for msg in items:
            total += 1
            print(f"❌ {msg}")

    if total:
        print()
        print(f'위반 {total}건 — `env:` 로 넘기고 run 안에서는 "$VAR" 로 읽으세요(CE-375).')
        print("치환값은 셸/JS 소스가 되어 임의 명령 실행으로 이어집니다.")
        return 1

    print(f"✅ run/script 치환 위반 없음 ({len(targets)}개 파일)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
