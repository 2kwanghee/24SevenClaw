"""contract.sync 메시지 핸들러 — 중앙 계약 동기화"""

import json
from pathlib import Path
from typing import Any

import structlog

from agent.handlers.base import BaseHandler

logger = structlog.get_logger()


class ContractHandler(BaseHandler):
    """Cloud에서 수신한 계약을 로컬에 머지·저장한다."""

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        project_id: str = payload.get("project_id", "")
        contracts: list[dict[str, Any]] = payload.get("contracts", [])

        if not project_id:
            logger.warning("contract.sync: project_id 누락")
            return {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "project_id가 필요합니다",
                    "recoverable": True,
                },
            }

        contracts_dir = Path(self.config.data_dir) / "contracts"
        contracts_dir.mkdir(parents=True, exist_ok=True)

        synced: list[str] = []
        errors: list[dict[str, str]] = []

        for item in contracts:
            slug = item.get("slug", "")
            if not slug:
                errors.append({"slug": "", "error": "slug 누락"})
                continue

            try:
                merged = self._merge_contract(item)
                dest = contracts_dir / f"{slug}.json"
                dest.write_text(
                    json.dumps(merged, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                synced.append(slug)
                logger.info("계약 동기화 완료", slug=slug, version=item.get("version"))
            except Exception as exc:
                logger.exception("계약 동기화 실패", slug=slug)
                errors.append({"slug": slug, "error": str(exc)})

        logger.info(
            "contract.sync 처리 완료",
            project_id=project_id,
            synced=len(synced),
            errors=len(errors),
        )

        return {
            "type": "agent.result",
            "payload": {
                "task_id": project_id,
                "status": "completed" if not errors else "partial",
                "summary": f"계약 동기화: {len(synced)}건 성공, {len(errors)}건 실패",
                "synced": synced,
                "errors": errors,
            },
        }

    @staticmethod
    def _merge_contract(item: dict[str, Any]) -> dict[str, Any]:
        """base content 위에 overrides를 우선 적용하여 머지한다."""
        content: dict[str, Any] = dict(item.get("content", {}))
        overrides: dict[str, Any] = item.get("overrides", {})

        # overrides 키가 content에 우선 적용
        content.update(overrides)

        return {
            "slug": item.get("slug", ""),
            "contract_type": item.get("contract_type", ""),
            "version": item.get("version", ""),
            "content": content,
        }
