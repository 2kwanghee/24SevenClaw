"""모델 등록 누락 회귀 방지 (CE-370).

`app/models/*.py` 에 모델(테이블 있는 클래스)을 정의한 모든 모듈은
`app/models/__init__.py` 에서 import 되어야 한다. 하나라도 빠지면
`alembic revision --autogenerate` 가 그 테이블을 메타데이터에서 보지 못해 **실 테이블을
drop 하는** 마이그레이션을 만든다(CE-370 실측: roi_standards 14행·pm_recommendation_logs
삭제문 생성).

**판정은 런타임 상태가 아니라 소스의 정적 대조(ast)로만 한다.** 두 가지 이유:

1. `alembic/env.py:7` 은 `import app.models` **만** 한다(서비스·라우터 미로드). 따라서
   autogenerate 메타데이터에 들어오는 모델은 `__init__.py` 가 import 하는 모듈뿐이다.
   런타임 `Base.metadata` 스냅샷으로 판정하면, 테스트 환경(conftest 가 앱 전체 로드 →
   서비스 체인이 미등록 모델까지 import)에서 **거짓 통과**한다.
2. 런타임 force-import 로 클래스를 찾는 방식은 다른 테스트가 남긴 import/네임스페이스
   상태에 오염돼(테스트 순서 의존) 거짓 양성/음성을 낸다. 소스만 파싱하면 순서와 무관하다.

DB·앱 로드를 타지 않으므로 기본 sqlite 경로에서 통과한다.
"""

from __future__ import annotations

import ast
from pathlib import Path

_MODELS_DIR = Path(__file__).resolve().parents[1] / "app" / "models"
_PREFIX = "app.models."


def _imported_modules() -> set[str]:
    """`app/models/__init__.py` 소스에서 import 하는 `app.models.<module>` 이름 집합(정적)."""
    tree = ast.parse((_MODELS_DIR / "__init__.py").read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            # from app.models.<mod> import ...  (상대 import 제외: level == 0)
            if node.level == 0 and node.module and node.module.startswith(_PREFIX):
                modules.add(node.module[len(_PREFIX) :].split(".")[0])
        elif isinstance(node, ast.Import):
            # import app.models.<mod>
            for alias in node.names:
                if alias.name.startswith(_PREFIX):
                    modules.add(alias.name[len(_PREFIX) :].split(".")[0])
    return modules


def _tablenames_in_source(path: Path) -> set[str]:
    """모듈 소스에서 클래스 본문의 `__tablename__` 값을 정적으로 수집한다.

    `__tablename__` 을 가진 클래스 = 구체 모델(테이블). 상수 문자열이면 그 값을, 아니면
    플레이스홀더('?')를 담는다(존재 자체가 판정에 쓰이고, 값은 실패 메시지 가독성용)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tablenames: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            targets: list[ast.expr] = []
            value: ast.expr | None = None
            if isinstance(stmt, ast.Assign):
                targets, value = stmt.targets, stmt.value
            elif isinstance(stmt, ast.AnnAssign):
                targets, value = [stmt.target], stmt.value
            for target in targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        tablenames.add(value.value)
                    else:
                        tablenames.add("?")
    return tablenames


def test_all_model_modules_registered_in_init() -> None:
    """모델(테이블)을 정의한 모든 모듈이 __init__.py 의 import 문에 존재한다(정적 대조)."""
    imported = _imported_modules()

    missing: dict[str, set[str]] = {}
    for path in sorted(_MODELS_DIR.glob("*.py")):
        module_name = path.stem
        if module_name.startswith("_"):
            continue
        tablenames = _tablenames_in_source(path)
        if tablenames and module_name not in imported:
            missing[module_name] = tablenames

    assert not missing, (
        "app/models/__init__.py 가 import 하지 않는 모델 모듈이 있습니다 "
        "(alembic/env.py 는 `import app.models` 만 하므로 autogenerate 가 drop_table 을 "
        f"생성한다 — CE-370): {missing}"
    )
