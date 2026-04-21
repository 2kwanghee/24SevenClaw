"""로컬 SQLite 상태 관리"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite
import structlog

logger = structlog.get_logger()

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class LocalStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.executescript(_SCHEMA_SQL)
        await self._db.commit()
        logger.info("LocalStore 초기화 완료", db_path=self._db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    # ── config CRUD ──────────────────────────────────────────

    async def put_config(self, key: str, value: Any) -> None:
        assert self._db is not None
        now = datetime.now(UTC).isoformat()
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        await self._db.execute(
            "INSERT INTO config (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (key, serialized, now),
        )
        await self._db.commit()

    async def get_config(self, key: str) -> Any | None:
        assert self._db is not None
        async with self._db.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    async def delete_config(self, key: str) -> None:
        assert self._db is not None
        await self._db.execute("DELETE FROM config WHERE key = ?", (key,))
        await self._db.commit()

    async def list_config(self, prefix: str = "") -> dict[str, Any]:
        assert self._db is not None
        query = "SELECT key, value FROM config WHERE key LIKE ?"
        async with self._db.execute(query, (f"{prefix}%",)) as cursor:
            rows = await cursor.fetchall()
        return {k: json.loads(v) for k, v in rows}
