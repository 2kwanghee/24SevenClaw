"""FastAPI OpenAPI 스펙을 JSON 파일로 내보내는 스크립트.

Usage:
    python -m scripts.export_openapi [output_path]

기본 출력: ../clickeye-contracts/openapi/openapi.json
"""

import json
import sys
from pathlib import Path

from app.main import create_app


def export_openapi(output_path: str | None = None) -> None:
    app = create_app()
    spec = app.openapi()

    if output_path is None:
        # 기본값: contracts 레포의 openapi 디렉토리
        contracts_dir = Path(__file__).resolve().parent.parent.parent / "clickeye-contracts"
        output_path = str(contracts_dir / "openapi" / "openapi.json")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    print(f"OpenAPI 스펙 내보내기 완료: {output}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    export_openapi(path)
