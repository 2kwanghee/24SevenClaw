#!/usr/bin/env python3
"""이슈 키 추출 테스트 (CE-376).

핵심은 **실측된 사고의 재현 방지**다: PR #108 본문에 정규식 리터럴을 백틱으로 적었더니
`Z0-9` 가 키로 뽑혀 Linear 자동 Done 이 조용히 멈췄다. 그 입력을 그대로 고정한다.

실행: `python3 scripts/tests/test_extract_issue_key.py`
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("eik", _ROOT / "scripts" / "extract_issue_key.py")
assert _SPEC and _SPEC.loader
eik = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(eik)

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


print("[1/4] 실측 사고 재현 방지 — 본문의 정규식 리터럴에 속지 않는다")

# PR #108 의 실제 상황: 본문에 백틱으로 정규식을 적었고 `Z0-9` 가 뽑혔다.
ACCIDENT_BODY = """## 수정

추출용 `grep -oP '[A-Z0-9]+-\\d+' | head -1` 이 첫 매치를 집는다.

```yaml
ISSUE_ID=$(printf '%s' "$PR_BODY" | grep -oP '[A-Z0-9]+-\\d+' | head -1)
```

회귀 방지를 CE-375 로 등재했다.
"""
check(
    "브랜치가 있으면 브랜치 키를 쓴다(사고 재현 X)",
    "CE-376",
    eik.extract("fix/root/CE-376-post-merge-automation", ACCIDENT_BODY),
)
check(
    "브랜치가 없어도 코드 영역은 무시한다",
    "CE-375",  # 본문 산문의 CE-375 — 코드 안 `Z0-9` 가 아니다
    eik.extract("", ACCIDENT_BODY),
)
check(
    "인라인 코드 안의 키는 뽑지 않는다",
    "",
    eik.extract("", "설명 `CE-999` 만 있는 본문"),
)
check(
    "코드 펜스 안의 키는 뽑지 않는다",
    "",
    eik.extract("", "설명\n\n```\nCE-999\n```\n"),
)

print("[2/4] 브랜치 우선 — 규약 형태를 정확히 뽑는다")

for branch, want in [
    ("fix/root/CE-376-post-merge-automation", "CE-376"),
    ("ralph/CE-123", "CE-123"),
    ("feature/api/24S-7-auth-bug", "24S-7"),
    ("fix/OPS-123", "OPS-123"),
    ("feature/web/CE-302-delivery-console", "CE-302"),
]:
    check(f"브랜치 {branch}", want, eik.extract(branch, ""))

print("[3/4] 브랜치에 키가 없으면 본문 폴백")

check("main 브랜치 + 본문 키", "CE-500", eik.extract("main", "CE-500 작업"))
check(
    "슬래시는 있으나 키 없음 → 본문 폴백",
    "CE-501",
    eik.extract("modarra9/some-desc-branch", "CE-501 작업"),
)
check("둘 다 없으면 빈 값", "", eik.extract("main", "키 없는 본문"))
check("빈 입력", "", eik.extract("", ""))
check("None 안전(빈 문자열로 처리)", "", eik.extract(None, None))  # type: ignore[arg-type]

print("[4/4] 브랜치 키가 본문 키보다 우선한다")

check(
    "브랜치 CE-376 vs 본문 CE-999 → 브랜치",
    "CE-376",
    eik.extract("fix/root/CE-376-x", "관련 이슈 CE-999"),
)
# 소문자 브랜치(Linear 자동 제안 형태)는 엄격한 키 형태가 아니므로 본문으로 넘어간다.
check(
    "소문자 브랜치는 키로 인정하지 않고 본문 폴백",
    "CE-374",
    eik.extract("modarra9/ce-374-fullstack", "CE-374 작업"),
)

print()
if FAIL:
    print(f"실패 {FAIL}건 / 통과 {PASS}건")
    sys.exit(1)
print(f"전체 통과: {PASS}건")
