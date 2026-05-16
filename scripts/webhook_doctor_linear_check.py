#!/usr/bin/env python3
"""Linear webhook 등록 URL과 ngrok 도메인 매칭 확인 (webhook-doctor.sh 보조 헬퍼)."""
import json
import os
import sys
import urllib.request as r

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env_loader import get_var  # noqa: E402


def main(domain: str) -> int:
    key = get_var("LINEAR_API_KEY")
    if not key:
        print("    LINEAR_API_KEY 미설정 — Linear 등록 확인 건너뜀")
        return 0

    query = {"query": "query { webhooks { nodes { label url enabled team { key } } } }"}
    req = r.Request(
        "https://api.linear.app/graphql",
        data=json.dumps(query).encode(),
        headers={"Authorization": key, "Content-Type": "application/json"},
    )
    try:
        res = json.loads(r.urlopen(req, timeout=10).read())
    except Exception as e:
        print(f"    Linear API 호출 실패: {e}")
        return 1

    nodes = res.get("data", {}).get("webhooks", {}).get("nodes", []) or []
    matched, other = [], []
    for w in nodes:
        team = (w.get("team") or {}).get("key") or "ALL"
        label = w.get("label") or "-"
        flag = "ON " if w.get("enabled") else "OFF"
        line = f"      [{flag}] team={team:<6} label={label!r:<20} url={w['url']}"
        (matched if domain in (w.get("url") or "") else other).append(line)

    if matched:
        print(f"  ✓ Linear 등록 webhook {len(matched)}개가 ngrok 도메인({domain}) 사용 중")
        for m in matched:
            print(m)
    else:
        print(f"  ⚠ Linear에 ngrok 도메인({domain})을 쓰는 webhook 없음 — URL 갱신 필요할 수 있음")

    if other:
        print(f"    그 외 등록된 webhook {len(other)}개")
        for o in other:
            print(o)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: webhook_doctor_linear_check.py <ngrok-domain>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
