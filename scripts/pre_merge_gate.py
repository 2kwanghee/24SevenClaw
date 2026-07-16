#!/usr/bin/env python3
"""ClickEye 자율 워크플로우 — 머지 직전 거버넌스 SSOT(Single Source of Truth) 게이트.

⚠️ 이 스크립트는 이제 **얇은 shim** 이다. 실제 로직은 저장소 루트의 stdlib 전용 커널
패키지 `governance/`(governance.core)에 단일 존재한다. 여기서는 (1) 기존 CLI 계약
(JSON stdout, exit 0/2)과 (2) 레거시 `import pre_merge_gate` 를 보존하기 위해 커널을
재노출하고, CLI 호출은 저장소 루트를 --project-dir 로 못박아 커널 CLI 에 위임한다.
→ auto_dev_pipeline.sh / ci.yml 호출부는 파싱 계약(JSON 키·타입·exit code) 무변경.

검증(정합성)과 위험분류를 한 곳에 모은다. 두 곳에서 **동일하게** 호출된다:
  (a) auto_dev_pipeline.sh — git merge 직전, 권위(authoritative) 게이트.
      direct-merge + push origin main 이 유일한 비보호 경로이므로 여기가 진짜 관문이다.
  (b) .github/workflows/ci.yml — pull_request 미러. 같은 검증을 PR에서 재확인.

검증 항목(블로킹은 contract-drift / ticket-ref 둘뿐 — 수용기준 1):
  - contract-drift : API 계약면(app/api|schemas|models|ws, contracts/**)이 바뀌었는데
                     clickeye-contracts/openapi/openapi.json(또는 generated client)이 동반되지 않음 → 차단.
  - ticket-ref     : 브랜치 접미사 ralph/<KEY> 에서 이슈 키 추출, shape `^[A-Z0-9]+-\\d+$` 검증.
                     키 없으면(슬래시 없는 브랜치) skip→pass. 형태 불량이면 차단.
  - plan-trace     : .ralph/refined/<KEY>.md 또는 .ralph/PLAN.md 가 있으면 비자명성/연관성 점검(권고).
                     산출물이 없으면(CI 체크아웃 등) 자동 skip. 절대 블로킹하지 않음.

위험분류(머지경로 강등용 — 새 승인장치 없음):
  - HIGH : 변경 경로가 clickeye-contracts/** | clickeye-infra/** | **/*auth* | 보안키워드 → 직접머지 금지·PR 강등.
  - LOW  : 현행 유지.

토글(.env, pipeline_config.sh 와 동일 의미: 미설정=on, false/0/off/no=off):
  FLOWOPS_GOVERNANCE(마스터) / _CONTRACT / _TICKET / _TRACE / _RISK_DEMOTE

출력: --json 이면 결과 JSON. exit 0=pass, 2=fail(블로킹). 마스터 off면 항상 pass/LOW(회귀 0).

사용법:
  python3 scripts/pre_merge_gate.py --base main --head ralph/CE-123 --json
  python3 scripts/pre_merge_gate.py --base origin/main --head HEAD --ci --json   # CI 미러
  python3 scripts/pre_merge_gate.py --diff-files "clickeye-api/app/api/x.py" --head ralph/CE-1   # 테스트용
"""

from __future__ import annotations

import os
import sys

# 저장소 루트를 sys.path 에 추가하여 커널 패키지(governance)를 설치 없이 import.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# 커널 재노출: 레거시 `import pre_merge_gate as g; g.evaluate(...)` 등을 그대로 지원.
# (sys.path 조작 후 import 이므로 E402 는 의도적 — noqa 처리.)
from governance.core import *  # noqa: E402,F401,F403
from governance.core import (  # noqa: E402,F401
    CONTRACT_SURFACE_PREFIXES,
    CONTRACTS_PREFIX,
    GENERATED_CLIENT_PREFIX,
    HIGH_PATH_PATTERNS,
    HIGH_PREFIXES,
    ISSUE_KEY_RE,
    OPENAPI_SPEC,
    check_contract_drift,
    check_plan_trace,
    check_ticket_ref,
    classify_risk,
    evaluate,
    extract_issue_key,
    get_changed_files,
    is_enabled,
)


def main() -> int:
    """커널 CLI 에 위임. 저장소 루트를 --project-dir 로 못박아 기존 .ralph 접근을 보존한다.

    JSON stdout + exit 0/2 계약은 커널 CLI 가 그대로 유지한다(파싱 계약 무변경).
    """
    from governance.__main__ import main as _kernel_main

    argv = sys.argv[1:]
    has_project_dir = any(
        a == "--project-dir" or a.startswith("--project-dir=") for a in argv
    )
    if not has_project_dir:
        sys.argv = [sys.argv[0], *argv, "--project-dir", _REPO_ROOT]
    return _kernel_main()


if __name__ == "__main__":
    sys.exit(main())
