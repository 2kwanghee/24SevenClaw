import json
import urllib.request
import os
import sys

# .env 수동 로드
base = os.path.dirname(os.path.abspath(__file__))
for env_path in [os.path.join(base, ".env"), os.path.join(base, "..", ".env")]:
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

key = os.getenv("LINEAR_API_KEY", "")
if not key:
    print("ERROR: LINEAR_API_KEY not found in .env")
    sys.exit(1)

query = {
    "query": """
query {
  issues(
    filter: { identifier: { in: ["FLO-76", "FLO-77"] } }
    first: 10
  ) {
    nodes {
      identifier
      state { name }
    }
  }
}
"""
}

body = json.dumps(query).encode()
req = urllib.request.Request("https://api.linear.app/graphql", data=body, method="POST")
req.add_header("Authorization", key)
req.add_header("Content-Type", "application/json")

try:
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"ERROR: {e}")
