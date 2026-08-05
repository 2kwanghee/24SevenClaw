#!/usr/bin/env python3
"""PR 에서 Linear 이슈 키를 뽑는다 (CE-376).

`post-merge.yml` 이 머지된 PR 을 어떤 이슈에 연결할지 정하는 데 쓴다.

## 왜 브랜치가 1순위인가

전 구현은 **PR 본문만** 보고 `grep -oP '[A-Z0-9]+-\\d+' | head -1` 했다. 실측(PR #108):
본문에 정규식 리터럴을 백틱으로 적었더니 그 문자열 자체에서 **`Z0-9`** 가 첫 매치로
잡혔다. 존재하지 않는 이슈라 Linear 조회가 빈손이었고, 스텝은 에러 없이 끝나
**성공처럼 보였다** — 자동 Done 처리가 조용히 멈춘 것이다.

브랜치명은 규약(`{type}/{module}/{TICKET-KEY}-{desc}`)이 강제돼 있고, 거버넌스 게이트의
`ticket-ref` 가 **이미 브랜치명에서 키를 뽑아 머지를 차단**한다. 같은 근거를 쓰면 두 경로의
판정이 어긋나지 않는다. 그래서 추출도 `governance.core.extract_issue_key()` 라는 같은
SSOT 를 쓴다(정책 `issue_key_search` 를 따르므로 다프로젝트 키 형태도 함께 간다).

## 본문 폴백에서 코드 영역을 지우는 이유

브랜치에 키가 없을 때만 본문을 본다. 이때도 **코드 펜스와 인라인 코드를 먼저 제거**한다 —
위 사고의 `Z0-9` 가 정확히 백틱 안에 있었다. 코드 예시·정규식·로그를 본문에 붙이는 것은
정상적인 PR 작성 습관이므로, 그것 때문에 자동화가 틀리면 안 된다.

출력: stdout 에 키 한 줄(없으면 빈 줄), 진단은 stderr. **항상 exit 0** — 이 스크립트가
죽으면 호출 스텝이 죽고, 그러면 `if: … != ''` 인 뒤 스텝들이 조용히 스킵된다
(CE-375 에서 실제로 겪은 경로).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# 코드 펜스(``` … ```) → 인라인 코드(` … `) 순으로 제거한다. 순서가 중요하다:
# 인라인부터 지우면 펜스의 여는/닫는 백틱이 서로 짝지어져 본문을 잘못 먹는다.
_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE = re.compile(r"`[^`]*`")


def strip_code(text: str) -> str:
    """마크다운 코드 영역을 제거한다(키 탐색 대상에서 뺀다)."""
    return _INLINE.sub(" ", _FENCE.sub(" ", text or ""))


def extract(head_ref: str, body: str) -> str:
    """브랜치 우선, 없으면 코드 제거한 본문에서 키를 뽑는다. 못 찾으면 빈 문자열."""
    from governance.core import Policy, extract_issue_key

    pol = Policy.default()

    # ① 브랜치 — 규약이 강제되고 거버넌스가 이미 이 근거로 판정한다.
    #    extract_issue_key 는 키가 없으면 마지막 세그먼트를 돌려주므로(형식 불량 신호),
    #    엄격한 키 형태(`issue_key_re`)로 한 번 더 거른다.
    key = extract_issue_key(head_ref or "")
    if key and pol.issue_key_re.match(key):
        return key

    # ② 본문 폴백 — 코드 스팬/펜스를 지운 뒤에 찾는다.
    m = pol.issue_key_search_re.search(strip_code(body or ""))
    return m.group(0) if m else ""


def main() -> int:
    key = extract(os.environ.get("HEAD_REF", ""), os.environ.get("PR_BODY", ""))
    print(key)
    # 진단은 stderr 로 — 값(stdout)과 섞이면 호출부가 오염된다.
    print(f"[extract_issue_key] key={key or '(없음)'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # 죽으면 뒤 스텝이 조용히 스킵된다 — 빈 값으로 계속 간다.
        print("")
        print(f"[extract_issue_key] 실패({exc}) — 빈 값으로 진행", file=sys.stderr)
        sys.exit(0)
