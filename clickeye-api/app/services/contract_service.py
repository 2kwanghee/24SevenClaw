"""중앙 계약 관리 서비스.

CRUD (superadmin 전용), 고객 오버라이드, WebSocket 동기화, 감사 로그.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.agent_connection import AgentConnection
from app.models.central_contract import (
    CentralContract,
    ContractAuditLog,
    CustomerContractOverride,
)
from app.schemas.contract import (
    CentralContractCreate,
    CentralContractUpdate,
    CustomerContractOverrideCreate,
    CustomerContractOverrideUpdate,
)
from app.ws.hub import agent_hub

logger = structlog.get_logger(__name__)


class ContractService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 감사 로그 ────────────────────────────────────────────

    async def _log_audit(
        self,
        actor_id: UUID,
        change_type: str,
        *,
        contract_id: UUID | None = None,
        override_id: UUID | None = None,
        diff_snapshot: dict[str, Any] | None = None,
    ) -> None:
        audit = ContractAuditLog(
            contract_id=contract_id,
            override_id=override_id,
            actor_id=actor_id,
            change_type=change_type,
            diff_snapshot=diff_snapshot or {},
        )
        self.db.add(audit)

    # ── CentralContract CRUD ─────────────────────────────────

    async def create_contract(
        self, data: CentralContractCreate, actor_id: UUID
    ) -> CentralContract:
        """중앙 계약 생성."""
        existing = await self.db.execute(
            select(CentralContract).where(CentralContract.slug == data.slug)
        )
        if existing.scalar_one_or_none() is not None:
            raise AppError("CONTRACT_SLUG_EXISTS", "이미 존재하는 slug입니다", 409)

        contract = CentralContract(
            slug=data.slug,
            contract_type=data.contract_type,
            source=data.source,
            version=data.version,
            content=data.content,
            description=data.description,
            is_locked=data.is_locked,
            allowed_overrides=data.allowed_overrides,
        )
        self.db.add(contract)
        await self.db.flush()

        await self._log_audit(
            actor_id,
            "create_contract",
            contract_id=contract.id,  # type: ignore[arg-type]
            diff_snapshot={"content": data.content, "slug": data.slug},
        )
        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def get_contract(self, contract_id: UUID) -> CentralContract:
        """중앙 계약 단건 조회."""
        contract = await self.db.get(CentralContract, contract_id)
        if contract is None:
            raise AppError("CONTRACT_NOT_FOUND", "계약을 찾을 수 없습니다", 404)
        return contract

    async def list_contracts(
        self,
        offset: int = 0,
        limit: int = 20,
        contract_type: str | None = None,
    ) -> tuple[list[CentralContract], int]:
        """중앙 계약 목록 조회."""
        conditions: list[Any] = []
        if contract_type:
            conditions.append(CentralContract.contract_type == contract_type)

        count_stmt = select(func.count()).select_from(CentralContract)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = select(CentralContract).order_by(CentralContract.created_at.desc())
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.offset(offset).limit(limit)

        contracts = list((await self.db.execute(stmt)).scalars().all())
        return contracts, int(total)

    async def update_contract(
        self, contract_id: UUID, data: CentralContractUpdate, actor_id: UUID
    ) -> CentralContract:
        """중앙 계약 수정."""
        contract = await self.get_contract(contract_id)

        update_data = data.model_dump(exclude_unset=True)
        old_snapshot: dict[str, Any] = {}
        for key, value in update_data.items():
            old_snapshot[key] = getattr(contract, key)
            setattr(contract, key, value)

        contract.updated_at = datetime.now(UTC)  # type: ignore[assignment]

        await self._log_audit(
            actor_id,
            "update_contract",
            contract_id=contract_id,
            diff_snapshot={"old": old_snapshot, "new": update_data},
        )
        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def delete_contract(self, contract_id: UUID, actor_id: UUID) -> None:
        """중앙 계약 삭제."""
        contract = await self.get_contract(contract_id)

        await self._log_audit(
            actor_id,
            "delete_contract",
            contract_id=contract_id,
            diff_snapshot={"slug": contract.slug},
        )
        await self.db.delete(contract)
        await self.db.commit()

    # ── CustomerContractOverride ─────────────────────────────

    async def apply_contract_to_project(
        self,
        project_id: UUID,
        data: CustomerContractOverrideCreate,
        actor_id: UUID,
    ) -> CustomerContractOverride:
        """프로젝트에 중앙 계약 적용 (오버라이드 생성)."""
        contract = await self.get_contract(data.central_contract_id)

        # allowed_overrides 검증
        self._validate_override_fields(
            data.override_content, contract.allowed_overrides  # type: ignore[arg-type]
        )

        override = CustomerContractOverride(
            project_id=project_id,
            central_contract_id=data.central_contract_id,
            override_content=data.override_content,
            approved_by=actor_id,
            is_active=True,
        )
        self.db.add(override)
        await self.db.flush()

        await self._log_audit(
            actor_id,
            "apply_contract",
            contract_id=data.central_contract_id,
            override_id=override.id,  # type: ignore[arg-type]
            diff_snapshot={"override_content": data.override_content},
        )
        await self.db.commit()
        await self.db.refresh(override)
        return override

    async def get_project_overrides(
        self,
        project_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[CustomerContractOverride], int]:
        """프로젝트의 계약 오버라이드 목록 조회."""
        conditions = [
            CustomerContractOverride.project_id == project_id,
            CustomerContractOverride.is_active == True,  # noqa: E712
        ]

        count_stmt = (
            select(func.count())
            .select_from(CustomerContractOverride)
            .where(*conditions)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(CustomerContractOverride)
            .where(*conditions)
            .order_by(CustomerContractOverride.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        overrides = list((await self.db.execute(stmt)).scalars().all())
        return overrides, int(total)

    async def update_customer_override(
        self,
        project_id: UUID,
        override_id: UUID,
        data: CustomerContractOverrideUpdate,
        actor_id: UUID,
    ) -> CustomerContractOverride:
        """고객 오버라이드 수정 (allowed_overrides 필드만 허용)."""
        stmt = select(CustomerContractOverride).where(
            CustomerContractOverride.id == override_id,
            CustomerContractOverride.project_id == project_id,
            CustomerContractOverride.is_active == True,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        override = result.scalar_one_or_none()
        if override is None:
            raise AppError(
                "OVERRIDE_NOT_FOUND", "계약 오버라이드를 찾을 수 없습니다", 404
            )

        # 원본 계약의 allowed_overrides 확인
        contract = await self.get_contract(override.central_contract_id)  # type: ignore[arg-type]
        self._validate_override_fields(
            data.override_content, contract.allowed_overrides  # type: ignore[arg-type]
        )

        old_content = override.override_content
        override.override_content = data.override_content  # type: ignore[assignment]
        override.updated_at = datetime.now(UTC)  # type: ignore[assignment]

        await self._log_audit(
            actor_id,
            "update_override",
            contract_id=override.central_contract_id,  # type: ignore[arg-type]
            override_id=override_id,
            diff_snapshot={"old": old_content, "new": data.override_content},
        )
        await self.db.commit()
        await self.db.refresh(override)
        return override

    # ── WebSocket 동기화 ─────────────────────────────────────

    async def sync_contracts_to_agent(
        self, project_id: UUID, actor_id: UUID
    ) -> tuple[int, list[str]]:
        """프로젝트에 적용된 계약을 Agent에 WebSocket으로 동기화."""
        # 프로젝트의 활성 오버라이드 조회
        stmt = select(CustomerContractOverride).where(
            CustomerContractOverride.project_id == project_id,
            CustomerContractOverride.is_active == True,  # noqa: E712
        )
        overrides = list((await self.db.execute(stmt)).scalars().all())

        # 오버라이드별 원본 계약 병합
        contracts_payload: list[dict[str, Any]] = []
        for ov in overrides:
            contract = await self.db.get(CentralContract, ov.central_contract_id)
            if contract is None:
                continue
            merged = {**(contract.content or {}), **(ov.override_content or {})}
            contracts_payload.append(
                {
                    "contract_id": str(contract.id),
                    "slug": contract.slug,
                    "contract_type": contract.contract_type,
                    "version": contract.version,
                    "content": merged,
                }
            )

        # 프로젝트에 연결된 Agent 조회
        agent_stmt = select(AgentConnection).where(
            AgentConnection.project_id == project_id,
            AgentConnection.status == "connected",
        )
        connections = list((await self.db.execute(agent_stmt)).scalars().all())

        synced_agents: list[str] = []
        for conn in connections:
            sent = await agent_hub.send_to_agent(
                str(conn.agent_token),
                {
                    # 계약면(clickeye-contracts messages.ts CommandMessageType /
                    # python/protocol.py) canonical 값과 정합. 이전 'contract.sync'는 불일치였음.
                    # TODO: agent 측 command.contract_sync 핸들러 미구현 — 별도 작업
                    # (clickeye-agent/agent/main.py dispatcher 미등록).
                    "type": "command.contract_sync",
                    "payload": {
                        "project_id": str(project_id),
                        "contracts": contracts_payload,
                    },
                },
            )
            if sent:
                synced_agents.append(str(conn.agent_token))

        await self._log_audit(
            actor_id,
            "sync_contracts",
            diff_snapshot={
                "project_id": str(project_id),
                "contract_count": len(contracts_payload),
                "synced_agents": synced_agents,
            },
        )
        await self.db.commit()

        logger.info(
            "contracts_synced",
            project_id=str(project_id),
            contract_count=len(contracts_payload),
            agent_count=len(synced_agents),
        )
        return len(synced_agents), synced_agents

    # ── 감사 로그 조회 ───────────────────────────────────────

    async def list_audit_logs(
        self,
        contract_id: UUID | None = None,
        change_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ContractAuditLog], int]:
        """계약 감사 로그 조회."""
        conditions: list[Any] = []
        if contract_id:
            conditions.append(ContractAuditLog.contract_id == contract_id)
        if change_type:
            conditions.append(ContractAuditLog.change_type == change_type)

        count_stmt = select(func.count()).select_from(ContractAuditLog)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = select(ContractAuditLog).order_by(
            ContractAuditLog.created_at.desc()
        )
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.offset(offset).limit(limit)

        logs = list((await self.db.execute(stmt)).scalars().all())
        return logs, int(total)

    # ── 유틸 ─────────────────────────────────────────────────

    @staticmethod
    def _validate_override_fields(
        override_content: dict[str, Any],
        allowed_overrides: list[str],
    ) -> None:
        """오버라이드 필드가 allowed_overrides에 포함되는지 검증."""
        if not override_content:
            return
        disallowed = set(override_content.keys()) - set(allowed_overrides)
        if disallowed:
            raise AppError(
                "OVERRIDE_NOT_ALLOWED",
                f"허용되지 않는 오버라이드 필드입니다: {', '.join(sorted(disallowed))}",
                422,
            )
