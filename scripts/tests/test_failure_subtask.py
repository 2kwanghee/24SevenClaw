"""파이프라인 실패 → Linear 하위 태스크 기능 테스트 (CE-376 4b).

검증 축:
  1. linear_tracker `task --parent` — 값이 있으면 input_data 에 parentId 가 들어가고,
     없으면 키 자체가 없다(None 을 넣으면 Linear 가 거부).
  2. auto_dev_pipeline handle_task_failure — 하위 태스크 생성이 FLOWOPS_FAILURE_SUBTASK
     토글 안에만 있고, 재시도 가능 경로(back_state 복귀)에는 생성 호출이 없다는 정적 검증.

네트워크·Linear 호출 없음(linear_request 목킹 + 소스 정적 검사).

Usage:
    cd ClickEye && python3 scripts/tests/test_failure_subtask.py
    cd ClickEye && pytest scripts/tests/test_failure_subtask.py -v
"""

from __future__ import annotations

import os
import sys
import types

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import linear_tracker as lt  # noqa: E402

_PIPELINE = os.path.join(_SCRIPTS_DIR, "auto_dev_pipeline.sh")


def _run_cmd_task(**overrides):
    """cmd_task 를 목킹된 linear_request/find_state_id 로 실행하고 전달된 input_data 반환."""
    captured = {}

    def fake_request(api_key, mutation, variables):
        captured["input"] = variables.get("input")
        return {"issueCreate": {"issue": {"id": "x", "identifier": "CE-999", "url": "http://x"}}}

    orig_request = lt.linear_request
    orig_find = lt.find_state_id
    lt.linear_request = fake_request
    lt.find_state_id = lambda *a, **k: "state-uuid"
    try:
        args = types.SimpleNamespace(
            title="[막힘] CE-123 — 거버넌스 차단",
            summary="본문",
            tags="",
            status="Wait",
            date="2026-08-05",
            parent="",
        )
        for k, v in overrides.items():
            setattr(args, k, v)
        lt.cmd_task(args, "api-key", "team-uuid")
    finally:
        lt.linear_request = orig_request
        lt.find_state_id = orig_find
    return captured["input"]


# ── 1. --parent 동작 ────────────────────────────────────────────────────────

def test_parent_sets_parent_id():
    inp = _run_cmd_task(parent="parent-uuid-1234")
    assert inp["parentId"] == "parent-uuid-1234"


def test_no_parent_omits_key():
    inp = _run_cmd_task(parent="")
    assert "parentId" not in inp, "부모 없으면 parentId 키 자체가 없어야 한다(None 금지)"


def test_parent_attr_absent_is_safe():
    # --parent 인자 없이 만들어진 args(getattr 기본값 경로)에서도 키가 없어야 한다.
    inp = _run_cmd_task()
    # SimpleNamespace 에 parent="" 이 있으므로 위와 동일. 별도로 속성 제거해 검증.
    args = types.SimpleNamespace(
        title="t", summary="s", tags="", status="Wait", date="2026-08-05"
    )
    captured = {}

    def fake_request(api_key, mutation, variables):
        captured["input"] = variables.get("input")
        return {"issueCreate": {"issue": {"id": "x", "identifier": "CE-1", "url": ""}}}

    orig_request, orig_find = lt.linear_request, lt.find_state_id
    lt.linear_request = fake_request
    lt.find_state_id = lambda *a, **k: "s"
    try:
        lt.cmd_task(args, "k", "team")
    finally:
        lt.linear_request, lt.find_state_id = orig_request, orig_find
    assert "parentId" not in captured["input"]


# ── 2. 파이프라인 정적 검증 ──────────────────────────────────────────────────

def _pipeline_src():
    with open(_PIPELINE, encoding="utf-8") as f:
        return f.read()


def _handle_task_failure_body():
    src = _pipeline_src()
    start = src.index("handle_task_failure()")
    # 다음 최상위 함수 or 파라미터 섹션 전까지
    end = src.index("\n# ── 파라미터", start)
    return src[start:end]


def test_subtask_creation_guarded_by_toggle():
    body = _handle_task_failure_body()
    assert 'is_enabled "FLOWOPS_FAILURE_SUBTASK"' in body, "토글 게이트 존재"
    # --parent 로 하위 태스크를 만드는 호출이 토글 블록 안에 있어야 한다.
    toggle_pos = body.index('is_enabled "FLOWOPS_FAILURE_SUBTASK"')
    parent_pos = body.index("--parent")
    assert parent_pos > toggle_pos, "하위 태스크 생성(--parent)은 토글 이후에 위치"


def test_subtask_status_is_wait_not_queued():
    body = _handle_task_failure_body()
    # 하위 태스크 생성 구간(--parent 근처)에서 상태가 Wait 이어야 하고 Queued 계열 금지.
    seg = body[body.index("FLOWOPS_FAILURE_SUBTASK"):]
    assert "--status Wait" in seg
    assert "DayQueued" not in seg and "NightQueued" not in seg, "하위 태스크는 Queued 계열 금지"


def test_retry_path_has_no_subtask_creation():
    body = _handle_task_failure_body()
    # 재시도 가능 경로 = rl_rc -eq 0 블록. 그 안에 --parent(하위 태스크 생성)가 없어야 한다.
    retry_start = body.index('if [ "$rl_rc" -eq 0 ]; then')
    retry_end = body.index("return 0", retry_start)
    retry_block = body[retry_start:retry_end]
    assert "--parent" not in retry_block, "재시도 가능 경로에는 하위 태스크 생성이 없어야 한다"
    assert "FLOWOPS_FAILURE_SUBTASK" not in retry_block


# ── 러너 ────────────────────────────────────────────────────────────────────

def _main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_main())
